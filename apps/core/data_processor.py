"""
Data processing utilities for Gcore reports.
"""
import logging
from typing import List, Dict, Any, Optional
import csv
import io

logger = logging.getLogger(__name__)


class DataProcessor:
    """Handles data processing and filtering for reports."""
    
    @staticmethod
    def normalize_rows(raw_data: Any) -> List[Dict[str, Any]]:
        """Normalize various Gcore report payload shapes into a list of row dicts."""
        rows: List[Dict[str, Any]] = []
        
        # Already a list of dicts
        if isinstance(raw_data, list) and all(isinstance(x, dict) for x in raw_data):
            return raw_data
        
        # Common wrapper with data
        if isinstance(raw_data, dict) and isinstance(raw_data.get("data"), list):
            data_list = raw_data.get("data")
            if all(isinstance(x, dict) for x in data_list):
                return data_list
        
        # headers + rows (tabular) - convert to list of dicts
        if (isinstance(raw_data, dict) and 
            isinstance(raw_data.get("headers"), list) and 
            isinstance(raw_data.get("rows"), list)):
            headers = raw_data["headers"]
            rows_data = raw_data["rows"]
            
            for row in rows_data:
                if isinstance(row, list) and len(row) == len(headers):
                    row_dict = dict(zip(headers, row))
                    rows.append(row_dict)
            return rows
        
        # Flatten first level if it's a dict with list values
        if isinstance(raw_data, dict):
            for key, value in raw_data.items():
                if isinstance(value, list):
                    if all(isinstance(x, dict) for x in value):
                        rows.extend(value)
                    elif all(isinstance(x, list) for x in value):
                        # Convert list of lists to list of dicts
                        for row in value:
                            if isinstance(row, list):
                                row_dict = {f"col_{i}": val for i, val in enumerate(row)}
                                rows.append(row_dict)
        
        return rows
    
    @staticmethod
    def filter_by_client_and_metric(rows: List[Dict[str, Any]], target_client_id: str) -> List[Dict[str, Any]]:
        """Filter rows by client ID and non-zero metric values."""
        if not rows:
            return []
        
        # Find the client ID and metric value keys
        client_key = None
        metric_key = None
        
        # Check first few rows to find the correct column names
        for sample in rows[:5]:
            if not isinstance(sample, dict):
                continue
            for key in sample.keys():
                if "client" in key.lower() and "id" in key.lower():
                    client_key = key
                if "metric" in key.lower() and "value" in key.lower():
                    metric_key = key
            if client_key and metric_key:
                break
        
        if not client_key or not metric_key:
            logger.warning("Could not find client ID or metric value columns")
            return rows
        
        logger.info(f"Detected client key: {client_key}, metric key: {metric_key}")
        
        # Filter rows
        filtered = []
        total_rows = len(rows)
        matched_client = 0
        non_zero_metric = 0
        zero_metric = 0
        
        for row in rows:
            client_id = str(row.get(client_key, "")).strip()
            metric_value = row.get(metric_key, 0)
            
            # Check if client ID matches
            if client_id == str(target_client_id).strip():
                matched_client += 1
                # Check if metric value is non-zero
                try:
                    metric_float = float(metric_value) if metric_value else 0
                    if metric_float != 0:
                        filtered.append(row)
                        non_zero_metric += 1
                    else:
                        zero_metric += 1
                except (ValueError, TypeError):
                    # If metric value can't be converted to float, include the row
                    filtered.append(row)
                    non_zero_metric += 1
        
        logger.info(f"Filter summary - total: {total_rows}, matched client: {matched_client}, "
                   f"non-zero metric kept: {non_zero_metric}, zero-metric dropped: {zero_metric}")
        
        return filtered
    
    @staticmethod
    def remove_zero_numeric_fields(row: Dict[str, Any]) -> Dict[str, Any]:
        """Remove fields that contain only zero numeric values."""
        cleaned = {}
        for key, value in row.items():
            if isinstance(value, (int, float)) and value == 0:
                continue
            cleaned[key] = value
        return cleaned
    
    @staticmethod
    def strip_nulls(row: Dict[str, Any]) -> Dict[str, Any]:
        """Remove null/empty values from row."""
        return {k: v for k, v in row.items() if v is not None and v != ""}
    
    @staticmethod
    def to_csv(rows: List[Dict[str, Any]]) -> str:
        """Convert rows to CSV format."""
        if not rows:
            return ""
        
        # Get all unique keys from all rows
        all_keys = set()
        for row in rows:
            all_keys.update(row.keys())
        
        # Sort keys for consistent column order
        fieldnames = sorted(all_keys)
        
        # Create CSV string
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        csv_content = output.getvalue()
        output.close()
        
        return csv_content
