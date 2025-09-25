"""
Gcore API client for report generation and management.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class GcoreClient:
    """Client for interacting with Gcore API."""
    
    def __init__(self, 
                 features_url: str,
                 generate_url: str,
                 status_url_template: str,
                 download_url_template: str,
                 token_manager):
        self.features_url = features_url
        self.generate_url = generate_url
        self.status_url_template = status_url_template
        self.download_url_template = download_url_template
        self.token_manager = token_manager
    
    def _bearer_header(self, token: str) -> Dict[str, str]:
        """Create Bearer authorization header."""
        return {"Authorization": f"Bearer {token}"}
    
    async def get_features(self) -> List[Dict[str, Any]]:
        """Get available report features from Gcore API."""
        token = await self.token_manager.get_token()
        headers = self._bearer_header(token)
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            try:
                response = await client.get(self.features_url, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to get features: {e.response.status_code} - {e.response.text}")
                raise HTTPException(502, f"Failed to get features: {e.response.status_code}")
    
    async def get_features_for_product(self, product_name: str) -> List[int]:
        """Get feature IDs for a specific product."""
        features_data = await self.get_features()
        feature_ids = []
        
        targets = {product_name.upper()}
        logger.info(f"Looking for features matching: {targets}")
        
        for feature in features_data or []:
            # Check multiple possible field names for product name
            pname = (feature.get("product_name_en") or 
                    feature.get("productNameEn") or 
                    feature.get("product") or "").strip().upper()
            fid = feature.get("id")
            
            if pname in targets and isinstance(fid, int):
                feature_ids.append(fid)
                logger.info(f"Found feature {fid} for product {pname}")
        
        logger.info(f"Total feature IDs found for {product_name}: {len(feature_ids)}")
        if not feature_ids:
            logger.warning(f"No features found for product: {product_name}")
            # Return first 10 features as fallback
            feature_ids = [f.get("id") for f in features_data[:10] if f.get("id")]
            logger.info(f"Using fallback features: {feature_ids}")
        
        return feature_ids
    
    async def start_report(self, product_name: str, features: List[int], 
                          start_date: str, end_date: str) -> str:
        """Start a new report generation."""
        token = await self.token_manager.get_token()
        headers = self._bearer_header(token)
        
        payload = {
            "template_code": "ResellerStatistics",
            "parameters": {
                "date_from": start_date,
                "date_to": end_date,
                "features": features,
                "group_by": ["client"]
            }
        }
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            try:
                response = await client.post(self.generate_url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                uuid = result.get("uuid")
                if not uuid:
                    raise HTTPException(502, "No UUID returned from report generation")
                return uuid
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to start report: {e.response.status_code} - {e.response.text}")
                raise HTTPException(502, f"Failed to start report: {e.response.status_code}")
    
    async def check_status(self, uuid: str) -> Dict[str, Any]:
        """Check report generation status."""
        token = await self.token_manager.get_token()
        headers = self._bearer_header(token)
        status_url = self.status_url_template.format(uuid=uuid)
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            try:
                response = await client.get(status_url, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to check status: {e.response.status_code} - {e.response.text}")
                raise HTTPException(502, f"Failed to check status: {e.response.status_code}")
    
    async def download_report(self, uuid: str, format: str = "json") -> Any:
        """Download completed report."""
        token = await self.token_manager.get_token()
        download_url = self.download_url_template.format(uuid=uuid)
        
        format_headers = {
            "json": "application/json",
            "csv": "text/csv", 
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        accept_header = format_headers.get(format, "application/json")
        headers = self._bearer_header(token) | {"Accept": accept_header}
        
        logger.info(f"Downloading report from: {download_url} (format: {format})")
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            try:
                response = await client.get(download_url, headers=headers)
                response.raise_for_status()
                
                content_type = (response.headers.get("content-type") or "").lower()
                
                if format == "csv" or "text/csv" in content_type:
                    import csv
                    rows: List[Dict[str, Any]] = []
                    reader = csv.DictReader(response.text.splitlines())
                    for row in reader:
                        rows.append(row)
                    return rows
                elif format == "excel" or "spreadsheetml" in content_type:
                    import base64
                    return {
                        "content_type": content_type,
                        "data": base64.b64encode(response.content).decode('utf-8'),
                        "size_bytes": len(response.content),
                        "format": "excel"
                    }
                else:
                    try:
                        return response.json()
                    except Exception:
                        import json
                        return json.loads(response.text)
                        
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to download report: {e.response.status_code} - {e.response.text}")
                raise HTTPException(502, f"Failed to download report: {e.response.status_code}")
    
    async def wait_for_completion(self, uuid: str, timeout: int = 600, poll_interval: int = 10) -> str:
        """Wait for report generation to complete."""
        logger.info(f"Starting to poll report status for UUID: {uuid}")
        status_url = self.status_url_template.format(uuid=uuid)
        logger.info(f"Status URL: {status_url}")
        logger.info(f"Timeout: {timeout}s, Poll interval: {poll_interval}s")
        
        start_time = asyncio.get_event_loop().time()
        poll_count = 0
        
        while True:
            poll_count += 1
            logger.info(f"Poll #{poll_count} - Checking status...")
            
            status_data = await self.check_status(uuid)
            current_status = status_data.get("status", "").lower()
            
            logger.info(f"Current status: '{current_status}'")
            
            if current_status == "completed":
                logger.info("Report is ready! Status: completed")
                return "completed"
            elif current_status == "failed":
                logger.error("Report generation failed!")
                raise HTTPException(502, "Report generation failed")
            elif current_status in ["inprogress", "pending"]:
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    logger.error(f"Report generation timed out after {timeout}s")
                    raise HTTPException(504, f"Report generation timed out after {timeout}s")
                
                logger.info(f"Report not ready yet, waiting {poll_interval}s before next check...")
                await asyncio.sleep(poll_interval)
            else:
                logger.warning(f"Unknown status: {current_status}")
                await asyncio.sleep(poll_interval)
