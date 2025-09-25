"""
Unit tests for data processor.
"""
import pytest
from apps.core.data_processor import DataProcessor


class TestDataProcessor:
    """Test cases for DataProcessor."""
    
    def test_normalize_rows_empty(self):
        """Test normalizing empty data."""
        processor = DataProcessor()
        result = processor.normalize_rows([])
        assert result == []
    
    def test_normalize_rows_list_of_dicts(self):
        """Test normalizing list of dictionaries."""
        processor = DataProcessor()
        data = [{"key": "value"}, {"key2": "value2"}]
        result = processor.normalize_rows(data)
        assert result == data
    
    def test_normalize_rows_single_dict(self):
        """Test normalizing single dictionary."""
        processor = DataProcessor()
        data = {"key": "value"}
        result = processor.normalize_rows(data)
        assert result == [data]
    
    def test_filter_by_client_and_metric(self):
        """Test filtering by client ID and metric value."""
        processor = DataProcessor()
        rows = [
            {"Client ID": "123", "Metric value": "100", "Other": "data"},
            {"Client ID": "123", "Metric value": "0", "Other": "data"},
            {"Client ID": "456", "Metric value": "200", "Other": "data"},
        ]
        result = processor.filter_by_client_and_metric(rows, "123")
        assert len(result) == 1
        assert result[0]["Client ID"] == "123"
        assert result[0]["Metric value"] == "100"
    
    def test_remove_zero_numeric_fields(self):
        """Test removing zero numeric fields."""
        processor = DataProcessor()
        row = {"key1": 100, "key2": 0, "key3": "text", "key4": 0.0}
        result = processor.remove_zero_numeric_fields(row)
        assert "key1" in result
        assert "key3" in result
        assert "key2" not in result
        assert "key4" not in result
    
    def test_strip_nulls(self):
        """Test stripping null values."""
        processor = DataProcessor()
        row = {"key1": "value", "key2": None, "key3": "", "key4": 0}
        result = processor.strip_nulls(row)
        assert "key1" in result
        assert "key4" in result
        assert "key2" not in result
        assert "key3" not in result
    
    def test_to_csv(self):
        """Test converting to CSV format."""
        processor = DataProcessor()
        rows = [
            {"Client ID": "123", "Metric value": "100"},
            {"Client ID": "456", "Metric value": "200"},
        ]
        result = processor.to_csv(rows)
        assert "Client ID,Metric value" in result
        assert "123,100" in result
        assert "456,200" in result
