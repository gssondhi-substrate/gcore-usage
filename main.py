
from __future__ import annotations

import asyncio
import logging
import os
from typing import List, Optional, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException, Header, Body
from pydantic import BaseModel, Field, validator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gcore API configuration via environment variables (with safe defaults)
API_BASE = os.getenv("GCORE_API_BASE", "https://api.gcore.com").rstrip("/")
FEATURES_PATH = os.getenv("GCORE_FEATURES_PATH", "/billing/v3/report_features")
GENERATE_PATH = os.getenv("GCORE_GENERATE_PATH", "/billing/v1/org/files/report")
STATUS_PATH = os.getenv("GCORE_STATUS_PATH", "/billing/v1/org/files/{uuid}")
DOWNLOAD_PATH = os.getenv("GCORE_DOWNLOAD_PATH", "/billing/v1/org/files/{uuid}/download")

FEATURES_URL = f"{API_BASE}{FEATURES_PATH}"
GENERATE_URL = f"{API_BASE}{GENERATE_PATH}"
STATUS_URL_TPL = f"{API_BASE}{STATUS_PATH}"
DOWNLOAD_URL_TPL = f"{API_BASE}{DOWNLOAD_PATH}"

app = FastAPI(title="Gcore Statistics Report API", version="1.0.0")


# ---------- Pydantic models ----------

class SimpleReportRequest(BaseModel):
    gcore_token: str = Field(..., description="Gcore API token")
    gcore_user_id: str = Field(..., description="Target Gcore Client/User ID to filter (string or numeric).")
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="End date in YYYY-MM-DD format")


class ReportResponse(BaseModel):
    uuid: str
    status: str
    count: int
    data: List[Dict[str, Any]]


# Dynamic aggregate response for /reports/all
# Keyed by product: "cdn", "waap", "cloud"


# ---------- Utilities ----------

def _bearer_header(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

def _strip_nulls(obj: Any) -> Any:
    """Recursively remove None, null-like, and empty containers."""
    null_like = (None, "", [], {})
    if isinstance(obj, dict):
        return {k: _strip_nulls(v) for k, v in obj.items() if v not in null_like}
    if isinstance(obj, list):
        cleaned = [_strip_nulls(x) for x in obj]
        return [x for x in cleaned if x not in null_like]
    return obj

def _matches_client(row: Dict[str, Any], target: str) -> bool:
    """Try several common keys to match the client/user id."""
    t = str(target).strip()
    for key in (
        "client_id",
        "clientId",
        "client",
        "client_code",
        "clientCode",
        "user_id",
        "userId",
        "Client ID",  # CSV header variant
        "client id",  # defensive variant
    ):
        if key in row and row[key] is not None and str(row[key]).strip() == t:
            return True
    # fallback: nested "client": {"id": "..."}
    c = row.get("client")
    if isinstance(c, dict):
        for k in ("id", "code"):
            if k in c and c[k] is not None and str(c[k]).strip() == t:
                return True
    return False


def _normalize_rows(raw: Any) -> List[Dict[str, Any]]:
    """Normalize various Gcore report payload shapes into a list of row dicts.

    Supports:
    - list[dict]
    - {"data": list[dict]}
    - {"headers": list[str], "rows": list[list[Any]]}
    - {k: list[dict]|list[list]} (flattens first level)
    """
    rows: List[Dict[str, Any]] = []

    # Already a list of dicts
    if isinstance(raw, list) and all(isinstance(x, dict) for x in raw):
        return raw

    # Common wrapper with data
    if isinstance(raw, dict) and isinstance(raw.get("data"), list):
        data_list = raw.get("data")
        if all(isinstance(x, dict) for x in data_list):
            return data_list  # type: ignore

    # headers + rows (tabular)
    if (
        isinstance(raw, dict)
        and isinstance(raw.get("headers"), list)
        and isinstance(raw.get("rows"), list)
    ):
        headers = [str(h) for h in raw.get("headers", [])]
        for row in raw.get("rows", []):
            if isinstance(row, list):
                obj: Dict[str, Any] = {}
                for idx, val in enumerate(row):
                    if idx < len(headers):
                        obj[headers[idx]] = val
                rows.append(obj)
            elif isinstance(row, dict):
                rows.append(row)
        return rows

    # Fallback: flatten dict-of-lists
    if isinstance(raw, dict):
        for v in raw.values():
            if isinstance(v, list):
                # If list of dicts, extend directly
                if all(isinstance(x, dict) for x in v):
                    rows.extend(v)  # type: ignore
                # If list of lists and we also have headers available somewhere
                elif isinstance(raw.get("headers"), list):
                    headers = [str(h) for h in raw.get("headers", [])]
                    for r in v:
                        if isinstance(r, list):
                            obj = {headers[i]: r[i] for i in range(min(len(headers), len(r)))}
                            rows.append(obj)
    return rows


def _has_nonzero_metric(row: Dict[str, Any]) -> bool:
    """Return True if the row contains at least one numeric metric > 0.

    Heuristic: consider numeric fields that aren't obvious identifiers/labels.
    Exclude fields whose names suggest ids, names, dates, grouping, or units.
    """
    if not isinstance(row, dict):
        return False

    excluded_substrings = (
        "id", "code", "name", "title", "client", "user", "product",
        "feature", "date", "from", "to", "group", "unit", "currency",
        "status", "uuid", "type", "region", "zone", "country"
    )

    for key, value in row.items():
        key_l = str(key).lower()
        if any(sub in key_l for sub in excluded_substrings):
            continue
        # Accept ints/floats that are finite
        if isinstance(value, (int, float)):
            if value is not None and value != 0:
                return True
        # Handle numeric strings
        if isinstance(value, str):
            try:
                num = float(value.strip())
                if num != 0:
                    return True
            except Exception:
                pass
    return False


def _metric_value_nonzero(row: Dict[str, Any]) -> bool:
    """Check that the specific column 'Metric value' (and common variants) is non-zero."""
    if not isinstance(row, dict):
        return False
    candidate_keys = [
        "Metric value",
        "metric value",
        "metric_value",
        "metricValue",
        "Metric Value",
    ]
    for key in candidate_keys:
        if key in row:
            val = row[key]
            # numeric or numeric-like string
            if isinstance(val, (int, float)):
                return val != 0
            if isinstance(val, str):
                s = val.strip().replace(",", "")
                try:
                    return float(s) != 0.0
                except Exception:
                    return False
            return False
    # If the exact column isn't present, fall back to heuristic
    return _has_nonzero_metric(row)


def _filter_by_client_and_metric(rows: List[Dict[str, Any]], target_client_id: str) -> List[Dict[str, Any]]:
    """Filter rows to those matching the client id and non-zero Metric value.

    Detects the best matching client and metric keys from candidates present in the rows.
    """
    if not rows:
        return []

    client_candidates = [
        "Client ID", "client_id", "clientId", "client id",
    ]
    metric_candidates = [
        "Metric value", "metric value", "metric_value", "metricValue", "Metric Value",
    ]

    # Determine keys by scanning the first few rows
    client_key = None
    metric_key = None
    for sample in rows[:10]:
        if not isinstance(sample, dict):
            continue
        for c in client_candidates:
            if c in sample:
                client_key = c if client_key is None else client_key
        for m in metric_candidates:
            if m in sample:
                metric_key = m if metric_key is None else metric_key
        if client_key and metric_key:
            break

    logger.info(f"Detected client key: {client_key}, metric key: {metric_key}")

    # Fallback to matcher/heuristic if keys not found
    filtered: List[Dict[str, Any]] = []
    if client_key and metric_key:
        dropped_client = 0
        dropped_zero = 0
        for r in rows:
            if not isinstance(r, dict):
                continue
            cid = r.get(client_key)
            if cid is None:
                continue
            if str(cid).strip() != str(target_client_id).strip():
                dropped_client += 1
                continue
            if not _metric_value_nonzero({metric_key: r.get(metric_key)}):
                dropped_zero += 1
                continue
            filtered.append(r)
        logger.info(f"Filter summary - total: {len(rows)}, matched client: {len(rows)-dropped_client}, non-zero metric kept: {len(filtered)}, zero-metric dropped: {dropped_zero}")
        return filtered

    # If we cannot detect keys, use generic helpers
    for r in rows:
        if not isinstance(r, dict):
            continue
        if not _matches_client(r, target_client_id):
            continue
        if not _metric_value_nonzero(r):
            continue
        filtered.append(r)
    return filtered

def _remove_zero_numeric_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys whose values are numeric zeros (0, 0.0, "0").

    Keeps non-numeric fields and nested structures, but prunes zero numerics.
    """
    if not isinstance(row, dict):
        return row

    def is_zero_numeric(val: Any) -> bool:
        if isinstance(val, (int, float)):
            return val == 0
        if isinstance(val, str):
            s = val.strip().replace(",", "")
            try:
                return float(s) == 0
            except Exception:
                return False
        return False

    cleaned: Dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, dict):
            nv = _remove_zero_numeric_fields(v)
            if nv not in (None, {}, [], ""):
                cleaned[k] = nv
        elif isinstance(v, list):
            nv_list = []
            for item in v:
                if isinstance(item, dict):
                    sub = _remove_zero_numeric_fields(item)
                    if sub not in (None, {}, [], ""):
                        nv_list.append(sub)
                elif not is_zero_numeric(item):
                    nv_list.append(item)
            if nv_list:
                cleaned[k] = nv_list
        else:
            if not is_zero_numeric(v):
                cleaned[k] = v
    return cleaned

async def _get_features(client: httpx.AsyncClient, token: str, product_names: List[str]) -> List[int]:
    logger.info(f"Fetching features for products: {product_names}")
    logger.info(f"Making request to: {FEATURES_URL}")
    
    r = await client.get(FEATURES_URL, headers=_bearer_header(token))
    logger.info(f"Features API response status: {r.status_code}")
    
    if r.status_code == 401:
        logger.error("Invalid Gcore token - 401 Unauthorized")
        raise HTTPException(401, "Invalid Gcore token.")
    r.raise_for_status()
    
    items = r.json()  # expected to be a list of feature objects
    logger.info(f"Retrieved {len(items) if items else 0} features from API")
    
    feature_ids: List[int] = []
    targets = set(product_names)  # e.g., {"CDN", "Cloud"}
    logger.info(f"Looking for features matching: {targets}")

    for it in items or []:
        # Defensive: tolerate variations in field names/casing
        pname = (it.get("product_name_en") or it.get("productNameEn") or "").strip()
        fid = it.get("id")
        if pname in targets and isinstance(fid, int):
            feature_ids.append(fid)
            logger.info(f"Found feature {fid} for product {pname}")

    logger.info(f"Total feature IDs found: {feature_ids}")
    if not feature_ids:
        logger.error(f"No feature IDs found for products: {product_names}")
        raise HTTPException(400, "No feature IDs found for the requested products (CDN/CLOUD/WAAP).")
    return sorted(set(feature_ids))


async def _start_report(client: httpx.AsyncClient, token: str, date_from: str, date_to: str, feature_ids: List[int]) -> str:
    payload = {
        "template_code": "ResellerStatistics",
        "parameters": {
            "date_from": date_from,
            "date_to": date_to,
            # group by client so we can filter to the exact Gcore user ID;
            # product/feature groups make the output richer but are optional
            "group_by": ["client"],
            "features": feature_ids
        }
    }
    
    logger.info(f"Starting report generation with payload: {payload}")
    logger.info(f"Making request to: {GENERATE_URL}")
    
    r = await client.post(GENERATE_URL, json=payload, headers=_bearer_header(token))
    logger.info(f"Report generation API response status: {r.status_code}")
    
    if r.status_code == 401:
        logger.error("Invalid Gcore token - 401 Unauthorized")
        raise HTTPException(401, "Invalid Gcore token.")
    
    if r.status_code not in [200, 201]:
        logger.error(f"Report generation failed with status {r.status_code}: {r.text}")
        r.raise_for_status()
    
    js = r.json() or {}
    logger.info(f"Report generation response: {js}")
    
    # Common response shape: { "uuid": "...", ... }
    uuid = js.get("uuid") or js.get("id") or js.get("file_uuid")
    if not uuid:
        logger.error(f"No UUID found in response: {js}")
        raise HTTPException(502, "Gcore did not return a report UUID.")
    
    logger.info(f"Report generation started with UUID: {uuid}")
    return uuid


async def _wait_until_ready(client: httpx.AsyncClient, token: str, uuid: str, timeout_s: int, poll_s: int) -> str:
    status_url = STATUS_URL_TPL.format(uuid=uuid)
    deadline = asyncio.get_event_loop().time() + timeout_s
    last_status = "unknown"
    poll_count = 0

    logger.info(f"Starting to poll report status for UUID: {uuid}")
    logger.info(f"Status URL: {status_url}")
    logger.info(f"Timeout: {timeout_s}s, Poll interval: {poll_s}s")

    while True:
        poll_count += 1
        logger.info(f"Poll #{poll_count} - Checking status...")
        
        r = await client.get(status_url, headers=_bearer_header(token))
        logger.info(f"Status check response: {r.status_code}")
        
        if r.status_code == 401:
            logger.error("Invalid Gcore token - 401 Unauthorized")
            raise HTTPException(401, "Invalid Gcore token.")
        r.raise_for_status()
        
        js = r.json() or {}
        logger.info(f"Status response: {js}")
        
        # status can be: ready / finished / done; failure: failed / error
        status = (js.get("status") or js.get("state") or "").lower()
        last_status = status or last_status
        logger.info(f"Current status: '{status}' (last: '{last_status}')")

        if status in {"ready", "finished", "done", "success", "succeeded", "available", "completed", "complete"}:
            logger.info(f"Report is ready! Status: {status}")
            return status
        if status in {"failed", "error"}:
            msg = js.get("message") or "Report generation failed."
            logger.error(f"Report generation failed: {msg}")
            raise HTTPException(502, f"Gcore report failed: {msg}")

        elapsed = asyncio.get_event_loop().time() - (deadline - timeout_s)
        if asyncio.get_event_loop().time() >= deadline:
            logger.error(f"Timeout reached after {elapsed:.1f}s. Last status: {last_status}")
            raise HTTPException(504, f"Timed out waiting for report (last status: {last_status}).")

        logger.info(f"Report not ready yet, waiting {poll_s}s before next check...")
        await asyncio.sleep(poll_s)


async def _download_json(client: httpx.AsyncClient, token: str, uuid: str) -> Any:
    url = DOWNLOAD_URL_TPL.format(uuid=uuid)
    headers = _bearer_header(token) | {"Accept": "application/json, text/csv; q=0.9, */*; q=0.1"}
    
    logger.info(f"Downloading report from: {url}")
    r = await client.get(url, headers=headers)
    logger.info(f"Download response status: {r.status_code}; content-type: {r.headers.get('content-type')} ")
    
    if r.status_code == 401:
        logger.error("Invalid Gcore token - 401 Unauthorized")
        raise HTTPException(401, "Invalid Gcore token.")
    r.raise_for_status()

    content_type = (r.headers.get("content-type") or "").lower()
    text_body = None

    # Handle CSV payloads
    if "text/csv" in content_type or content_type.endswith("/csv"):
        import csv
        text_body = r.text
        logger.info("Parsing CSV payload returned by Gcore")
        rows: List[Dict[str, Any]] = []
        reader = csv.DictReader(text_body.splitlines())
        for row in reader:
            rows.append(row)
        logger.info(f"Parsed CSV rows: {len(rows)}")
        return rows

    # Try JSON first
    try:
        data = r.json()
        logger.info(f"Successfully downloaded JSON data with {len(data) if isinstance(data, (list, dict)) else 'unknown'} items")
        return data
    except Exception as e:
        logger.warning(f"Failed to parse as JSON, trying text parsing: {e}")
        # Attempt text->json if mislabelled
        import json
        text_body = text_body or r.text
        data = json.loads(text_body)
        logger.info(f"Successfully parsed text as JSON with {len(data) if isinstance(data, (list, dict)) else 'unknown'} items")
        return data


# ---------- API endpoints ----------

async def _generate_report_for_product(product_name: str, body: SimpleReportRequest) -> ReportResponse:
    """Common logic for generating reports for a specific product."""
    logger.info(f"Starting report generation for product: {product_name}")
    logger.info(f"Request details - User ID: {body.gcore_user_id}, Date range: {body.start_date} to {body.end_date}")
    
    # Use Gcore token from request body
    token = body.gcore_token
    logger.info(f"Using Gcore token: {token[:20]}...")

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, read=300.0, write=60.0, connect=30.0)) as client:
        # 1) Get features for this specific product
        logger.info("Step 1: Getting feature IDs...")
        feature_ids = await _get_features(client, token, [product_name])
        
        # 2) Start report
        logger.info("Step 2: Starting report generation...")
        uuid = await _start_report(client, token, body.start_date, body.end_date, feature_ids)
        
        # 3) Poll status (with longer timeout for report generation)
        logger.info("Step 3: Waiting for report to be ready...")
        status = await _wait_until_ready(client, token, uuid, 600, 10)
        
        # 4) Download JSON
        logger.info("Step 4: Downloading report data...")
        raw = await _download_json(client, token, uuid)

    # Defensive: normalize the payload to a list of rows
    logger.info("Step 5: Processing and filtering data...")
    rows: List[Dict[str, Any]] = _normalize_rows(raw)
    logger.info(f"Total rows before filtering: {len(rows)}")

    # Filter to the target user/client id and non-zero Metric value (CSV-aware)
    filtered = _filter_by_client_and_metric(rows, body.gcore_user_id)
    logger.info(f"Rows after filtering for user {body.gcore_user_id} with non-zero 'Metric value': {len(filtered)}")

    # Remove numeric-zero fields, then strip null/empty recursively
    without_zeros = [_remove_zero_numeric_fields(r) for r in filtered]
    cleaned = [_strip_nulls(r) for r in without_zeros]
    logger.info(f"Final cleaned data count: {len(cleaned)}")

    result = ReportResponse(uuid=uuid, status=status, count=len(cleaned), data=cleaned)
    logger.info(f"Report generation completed successfully! UUID: {uuid}, Status: {status}, Count: {len(cleaned)}")
    return result


@app.post("/reports/cdn", response_model=ReportResponse, summary="Generate CDN statistics report for a Gcore user")
async def generate_cdn_report(
    body: SimpleReportRequest = Body(...),
):
    """Generate a CDN statistics report for the specified Gcore user and date range."""
    logger.info("=== CDN Report Request Received ===")
    try:
        result = await _generate_report_for_product("CDN", body)
        logger.info("=== CDN Report Request Completed Successfully ===")
        return result
    except Exception as e:
        logger.error(f"=== CDN Report Request Failed: {str(e)} ===")
        raise


@app.post("/reports/waap", response_model=ReportResponse, summary="Generate WAAP statistics report for a Gcore user")
async def generate_waap_report(
    body: SimpleReportRequest = Body(...),
):
    """Generate a WAAP statistics report for the specified Gcore user and date range."""
    return await _generate_report_for_product("WAAP", body)


@app.post("/reports/cloud", response_model=ReportResponse, summary="Generate CLOUD statistics report for a Gcore user")
async def generate_cloud_report(
    body: SimpleReportRequest = Body(...),
):
    """Generate a CLOUD statistics report for the specified Gcore user and date range."""
    return await _generate_report_for_product("Cloud", body)


@app.post("/reports/all", response_model=dict, summary="Generate reports for CDN, WAAP and CLOUD for a Gcore user")
async def generate_all_reports(
    body: SimpleReportRequest = Body(...),
):
    """Generate and return reports for CDN, WAAP, and CLOUD in one call."""
    logger.info("=== ALL Reports Request Received ===")
    result: Dict[str, Any] = {"cdn": {}, "waap": {}, "cloud": {}}
    try:
        cdn = await _generate_report_for_product("CDN", body)
        if cdn.count > 0:
            result["cdn"] = cdn.dict()
    except HTTPException as e:
        logger.info(f"CDN skipped due to error: {e.detail}")
    
    try:
        waap = await _generate_report_for_product("WAAP", body)
        if waap.count > 0:
            result["waap"] = waap.dict()
    except HTTPException as e:
        logger.info(f"WAAP skipped due to error: {e.detail}")
    
    try:
        cloud = await _generate_report_for_product("Cloud", body)
        if cloud.count > 0:
            result["cloud"] = cloud.dict()
    except HTTPException as e:
        logger.info(f"Cloud skipped due to error: {e.detail}")
    
    logger.info("=== ALL Reports Request Completed ===")
    return result


class StatusRequest(BaseModel):
    gcore_token: str = Field(..., description="Gcore API token")

@app.post("/reports/gcore/{uuid}", summary="Check report status or fetch raw JSON (no cleaning)", response_model=dict)
async def get_report_or_json(
    uuid: str,
    body: StatusRequest = Body(...),
    mode: str = "status",  # "status" or "download"
):
    # Use Gcore token from request body
    token = body.gcore_token

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, read=300.0, write=60.0, connect=30.0)) as client:
        if mode == "status":
            r = await client.get(STATUS_URL_TPL.format(uuid=uuid), headers=_bearer_header(token))
            if r.status_code == 401:
                raise HTTPException(401, "Invalid Gcore token.")
            r.raise_for_status()
            return r.json()
        elif mode == "download":
            data = await _download_json(client, token, uuid)
            return {"uuid": uuid, "data": data}
        else:
            raise HTTPException(400, "mode must be 'status' or 'download'.")


@app.get("/", summary="Health check")
async def health_check():
    logger.info("Health check requested")
    return {"status": "healthy", "service": "Gcore Statistics Report API", "version": "1.0.0"}

@app.get("/health", summary="Detailed health check")
async def detailed_health_check():
    logger.info("Detailed health check requested")
    return {
        "status": "healthy", 
        "service": "Gcore Statistics Report API",
        "version": "1.0.0",
        "endpoints": ["/reports/cdn", "/reports/waap", "/reports/cloud"],
        "features": "CDN, WAAP, CLOUD report generation with Gcore API integration"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
