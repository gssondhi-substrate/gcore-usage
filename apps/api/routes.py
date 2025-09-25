"""
API routes for Gcore Usage API.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Body
from fastapi.responses import JSONResponse

from apps.api.models import SimpleReportRequest, StatusRequest, ReportResponse, HealthResponse
from apps.core.gcore_client import GcoreClient
from apps.core.data_processor import DataProcessor
from apps.core.auth import TokenManager
from config.settings import settings

logger = logging.getLogger(__name__)

# Initialize core components
token_manager = TokenManager(
    auth_url=settings.auth_url,
    username=settings.GCORE_USERNAME,
    password=settings.GCORE_PASSWORD,
    cache_duration=settings.TOKEN_CACHE_DURATION
)

gcore_client = GcoreClient(
    features_url=settings.features_url,
    generate_url=settings.generate_url,
    status_url_template=settings.status_url_template,
    download_url_template=settings.download_url_template,
    token_manager=token_manager
)

data_processor = DataProcessor()

# Create router
router = APIRouter()


def _parse_accept_header(accept_header: Optional[str]) -> str:
    """Parse Accept header to determine format."""
    if not accept_header:
        return "json"
    
    accept_header = accept_header.lower().strip()
    
    if "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in accept_header:
        return "excel"
    elif "text/csv" in accept_header:
        return "csv"
    elif "application/json" in accept_header:
        return "json"
    else:
        return "json"


async def _generate_report_for_product(product_name: str, body: SimpleReportRequest, 
                                     accept_header: Optional[str] = None) -> ReportResponse:
    """Generate report for a specific product."""
    logger.info(f"Report generation started for product: {product_name}")
    
    # Parse format from Accept header or request body
    format_from_header = _parse_accept_header(accept_header)
    final_format = format_from_header if format_from_header != "json" or body.format == "json" else body.format
    
    logger.info(f"Final format: {final_format}")
    
    try:
        # Step 1: Get available features
        logger.info("Step 1: Getting available features...")
        product_features = await gcore_client.get_features_for_product(product_name)
        logger.info(f"Found {len(product_features)} features for product {product_name}")
        
        # Step 2: Start report generation
        logger.info("Step 2: Starting report generation...")
        uuid = await gcore_client.start_report(
            product_name=product_name,
            features=product_features,
            start_date=body.start_date,
            end_date=body.end_date
        )
        
        logger.info(f"Report generation started with UUID: {uuid}")
        
        # Step 3: Wait for completion
        logger.info("Step 3: Waiting for report to be ready...")
        status = await gcore_client.wait_for_completion(
            uuid=uuid,
            timeout=settings.REPORT_POLL_TIMEOUT,
            poll_interval=settings.REPORT_POLL_INTERVAL
        )
        
        # Step 4: Download report
        logger.info(f"Step 4: Downloading report data in {final_format} format...")
        # For Excel format, download as CSV first to apply filtering, then convert
        download_format = "csv" if final_format == "excel" else final_format
        raw_data = await gcore_client.download_report(uuid, download_format)
        
        # Process data based on format
        if final_format == "excel":
            # For Excel, we downloaded as CSV, so process it the same way as CSV
            logger.info("Excel format requested - processing filtered CSV data")
            rows = data_processor.normalize_rows(raw_data)
            logger.info(f"Total rows before filtering: {len(rows)}")
            
            # Filter to the target user/client id and non-zero Metric value
            filtered = data_processor.filter_by_client_and_metric(rows, body.gcore_user_id)
            logger.info(f"Rows after filtering for user {body.gcore_user_id} with non-zero 'Metric value': {len(filtered)}")
            
            # Convert filtered data to CSV format, then encode as Excel
            csv_content = data_processor.to_csv(filtered)
            
            # Encode as base64 for Excel format
            import base64
            excel_data = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
            
            result = ReportResponse(
                uuid=uuid,
                status=status,
                count=len(filtered),
                data={
                    "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "data": excel_data,
                    "size_bytes": len(csv_content),
                    "format": "excel",
                    "note": "Filtered data in Excel format"
                }
            )
            
            logger.info(f"Report generation completed successfully! UUID: {uuid}, Status: {status}, Count: {len(filtered)}, Format: Excel")
            return result
        
        elif final_format == "csv":
            # For CSV, apply filtering but preserve original column structure
            logger.info("CSV format requested - applying filtering while preserving column structure")
            rows = data_processor.normalize_rows(raw_data)
            logger.info(f"Total rows before filtering: {len(rows)}")
            
            # Filter to the target user/client id and non-zero Metric value
            filtered = data_processor.filter_by_client_and_metric(rows, body.gcore_user_id)
            logger.info(f"Rows after filtering for user {body.gcore_user_id} with non-zero 'Metric value': {len(filtered)}")
            
            # Convert to CSV format
            csv_content = data_processor.to_csv(filtered)
            
            result = ReportResponse(
                uuid=uuid,
                status=status,
                count=len(filtered),
                data=csv_content
            )
            logger.info(f"Report generation completed successfully! UUID: {uuid}, Status: {status}, Count: {len(filtered)}, Format: CSV")
            return result
        
        else:  # JSON format
            logger.info("JSON format requested - processing and filtering data...")
            rows = data_processor.normalize_rows(raw_data)
            logger.info(f"Total rows before filtering: {len(rows)}")
            
            # Filter to the target user/client id and non-zero Metric value
            filtered = data_processor.filter_by_client_and_metric(rows, body.gcore_user_id)
            logger.info(f"Rows after filtering for user {body.gcore_user_id} with non-zero 'Metric value': {len(filtered)}")
            
            # Clean data (remove zero values and nulls)
            without_zeros = [data_processor.remove_zero_numeric_fields(r) for r in filtered]
            cleaned = [data_processor.strip_nulls(r) for r in without_zeros]
            
            result = ReportResponse(
                uuid=uuid,
                status=status,
                count=len(cleaned),
                data=cleaned
            )
            logger.info(f"Report generation completed successfully! UUID: {uuid}, Status: {status}, Count: {len(cleaned)}, Format: JSON")
            return result
            
    except Exception as e:
        logger.error(f"Error generating report for {product_name}: {str(e)}")
        raise HTTPException(500, f"Failed to generate report: {str(e)}")


# Health check endpoint
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    import time
    return HealthResponse(
        status="healthy",
        service="gcore-usage-api",
        version="1.0.0",
        timestamp=time.time()
    )


# Report generation endpoints
@router.post("/reports/cdn", response_model=ReportResponse)
async def generate_cdn_report(
    body: SimpleReportRequest = Body(...),
    accept: Optional[str] = Header(None)
):
    """Generate CDN usage report."""
    return await _generate_report_for_product("CDN", body, accept)


@router.post("/reports/waap", response_model=ReportResponse)
async def generate_waap_report(
    body: SimpleReportRequest = Body(...),
    accept: Optional[str] = Header(None)
):
    """Generate WAAP usage report."""
    return await _generate_report_for_product("WAAP", body, accept)


@router.post("/reports/cloud", response_model=ReportResponse)
async def generate_cloud_report(
    body: SimpleReportRequest = Body(...),
    accept: Optional[str] = Header(None)
):
    """Generate Cloud usage report."""
    return await _generate_report_for_product("Cloud", body, accept)


@router.post("/reports/all", response_model=ReportResponse)
async def generate_all_reports(
    body: SimpleReportRequest = Body(...),
    accept: Optional[str] = Header(None)
):
    """Generate aggregated report for all products (CDN, WAAP, Cloud)."""
    logger.info("Generating aggregated report for all products")
    
    # Parse format from Accept header or request body
    format_from_header = _parse_accept_header(accept)
    final_format = format_from_header if format_from_header != "json" or body.format == "json" else body.format
    
    logger.info(f"Final format: {final_format}")
    
    try:
        # Generate reports for each product
        products = ["CDN", "WAAP", "Cloud"]
        all_data = []
        total_count = 0
        
        for product in products:
            logger.info(f"Generating report for product: {product}")
            try:
                # Get features for this product
                product_features = await gcore_client.get_features_for_product(product)
                logger.info(f"Found {len(product_features)} features for product {product}")
                
                # Start report generation
                uuid = await gcore_client.start_report(
                    product_name=product,
                    features=product_features,
                    start_date=body.start_date,
                    end_date=body.end_date
                )
                
                logger.info(f"Report generation started for {product} with UUID: {uuid}")
                
                # Wait for completion
                status = await gcore_client.wait_for_completion(
                    uuid=uuid,
                    timeout=settings.REPORT_POLL_TIMEOUT,
                    poll_interval=settings.REPORT_POLL_INTERVAL
                )
                
                # Download report data
                download_format = "csv" if final_format == "excel" else final_format
                raw_data = await gcore_client.download_report(uuid, download_format)
                
                # Process and filter data
                rows = data_processor.normalize_rows(raw_data)
                filtered = data_processor.filter_by_client_and_metric(rows, body.gcore_user_id)
                
                # Add product information to each row
                for row in filtered:
                    row["Product"] = product
                
                all_data.extend(filtered)
                total_count += len(filtered)
                
                logger.info(f"Product {product}: {len(filtered)} filtered rows added to aggregate")
                
            except Exception as e:
                logger.error(f"Error generating report for product {product}: {str(e)}")
                # Continue with other products even if one fails
                continue
        
        logger.info(f"Total aggregated rows: {total_count}")
        
        # Process aggregated data based on format
        if final_format == "excel":
            # Convert aggregated data to CSV format, then encode as Excel
            csv_content = data_processor.to_csv(all_data)
            
            # Encode as base64 for Excel format
            import base64
            excel_data = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
            
            result = ReportResponse(
                uuid="aggregated",  # No single UUID for aggregated data
                status="completed",
                count=total_count,
                data={
                    "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "data": excel_data,
                    "size_bytes": len(csv_content),
                    "format": "excel",
                    "note": f"Filtered aggregated data from {len(products)} products"
                }
            )
            
        elif final_format == "csv":
            # Convert aggregated data to CSV format
            csv_content = data_processor.to_csv(all_data)
            
            result = ReportResponse(
                uuid="aggregated",
                status="completed",
                count=total_count,
                data=csv_content
            )
            
        else:  # JSON format
            # Apply additional processing for JSON
            processed_data = []
            for row in all_data:
                # Remove zero numeric fields and nulls
                cleaned_row = data_processor.remove_zero_numeric_fields(row)
                cleaned_row = data_processor.strip_nulls(cleaned_row)
                processed_data.append(cleaned_row)
            
            result = ReportResponse(
                uuid="aggregated",
                status="completed",
                count=total_count,
                data=processed_data
            )
        
        logger.info(f"Aggregated report generation completed! Total count: {total_count}, Format: {final_format}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating aggregated report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating aggregated report: {str(e)}")


# Report status and download endpoints
@router.get("/reports/gcore/{uuid}", response_model=ReportResponse)
async def get_report_status(
    uuid: str,
    body: StatusRequest = Body(...),
    accept: Optional[str] = Header(None)
):
    """Get report status and download if ready."""
    try:
        # Check status
        status_data = await gcore_client.check_status(uuid)
        status = status_data.get("status", "").lower()
        
        if status != "completed":
            return ReportResponse(
                uuid=uuid,
                status=status,
                count=0,
                data=[]
            )
        
        # Download if completed
        format_from_header = _parse_accept_header(accept)
        final_format = format_from_header if format_from_header != "json" or body.format == "json" else body.format
        
        raw_data = await gcore_client.download_report(uuid, final_format)
        
        if final_format == "excel":
            return ReportResponse(
                uuid=uuid,
                status=status,
                count=raw_data.get("size_bytes", 0) if isinstance(raw_data, dict) else 0,
                data=raw_data
            )
        elif final_format == "csv":
            rows = data_processor.normalize_rows(raw_data)
            csv_content = data_processor.to_csv(rows)
            return ReportResponse(
                uuid=uuid,
                status=status,
                count=len(rows),
                data=csv_content
            )
        else:  # JSON
            rows = data_processor.normalize_rows(raw_data)
            return ReportResponse(
                uuid=uuid,
                status=status,
                count=len(rows),
                data=rows
            )
            
    except Exception as e:
        logger.error(f"Error getting report {uuid}: {str(e)}")
        raise HTTPException(500, f"Failed to get report: {str(e)}")


@router.post("/reports/gcore/{uuid}/download", response_model=ReportResponse)
async def download_report(
    uuid: str,
    body: StatusRequest = Body(...),
    accept: Optional[str] = Header(None)
):
    """Download a completed report."""
    try:
        format_from_header = _parse_accept_header(accept)
        final_format = format_from_header if format_from_header != "json" or body.format == "json" else body.format
        
        raw_data = await gcore_client.download_report(uuid, final_format)
        
        if final_format == "excel":
            return ReportResponse(
                uuid=uuid,
                status="completed",
                count=raw_data.get("size_bytes", 0) if isinstance(raw_data, dict) else 0,
                data=raw_data
            )
        elif final_format == "csv":
            rows = data_processor.normalize_rows(raw_data)
            csv_content = data_processor.to_csv(rows)
            return ReportResponse(
                uuid=uuid,
                status="completed",
                count=len(rows),
                data=csv_content
            )
        else:  # JSON
            rows = data_processor.normalize_rows(raw_data)
            return ReportResponse(
                uuid=uuid,
                status="completed",
                count=len(rows),
                data=rows
            )
            
    except Exception as e:
        logger.error(f"Error downloading report {uuid}: {str(e)}")
        raise HTTPException(500, f"Failed to download report: {str(e)}")
