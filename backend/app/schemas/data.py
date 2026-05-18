"""Schemas for data analysis endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class DatasetUploadResponse(BaseModel):
    """Response from file upload endpoint."""

    dataset_id: str = Field(..., description="Unique identifier for the dataset")
    filename: str = Field(..., description="Original filename")
    source: str = Field(default="file", description="Source type: 'file' or 'google_sheet'")
    rows: int = Field(..., description="Number of rows in the dataframe")
    columns: int = Field(..., description="Number of columns in the dataframe")
    column_names: List[str] = Field(..., description="List of column names")
    sample_data: Optional[Dict[str, Any]] = Field(
        None, description="First few rows of data"
    )


class GoogleSheetConnectRequest(BaseModel):
    """Request to connect a Google Sheet."""

    google_sheet_url: Optional[str] = Field(
        None, description="Full URL to the Google Sheet"
    )
    google_sheet_id: Optional[str] = Field(
        None, description="Google Sheet ID (alternative to URL)"
    )
    worksheet_name: Optional[str] = Field(
        default="Sheet1", description="Name of the worksheet/tab to load"
    )


class GoogleSheetConnectResponse(BaseModel):
    """Response from Google Sheet connection endpoint."""

    dataset_id: str = Field(..., description="Unique identifier for the dataset")
    filename: str = Field(..., description="Sheet name or URL")
    source: str = Field(default="google_sheet", description="Source type")
    rows: int = Field(..., description="Number of rows in the sheet")
    columns: int = Field(..., description="Number of columns in the sheet")
    column_names: List[str] = Field(..., description="List of column names")
    sheet_id: str = Field(..., description="Google Sheet ID")


class DataQueryRequest(BaseModel):
    """Request to query a dataset."""

    dataset_id: str = Field(..., description="Dataset ID from upload/connect")
    question: str = Field(..., description="Natural language question about the data")
    include_context: bool = Field(
        default=True,
        description="Include previous conversation context in the query"
    )


class DataQueryResponse(BaseModel):
    """Response from query endpoint."""

    success: bool = Field(..., description="Whether the query was successful")
    question: str = Field(..., description="The question that was asked")
    answer: str = Field(..., description="The AI-generated answer")
    source: str = Field(..., description="Source identifier")
    row_count: int = Field(..., description="Number of rows in the dataset")
    column_count: int = Field(..., description="Number of columns in the dataset")
    columns: List[str] = Field(..., description="Column names")
    reasoning: Optional[str] = Field(
        None, description="Optional reasoning/explanation from the agent"
    )
    error: Optional[str] = Field(None, description="Error message if query failed")
    has_context: bool = Field(
        default=False, description="Whether previous context was used"
    )


class DatasetInfoResponse(BaseModel):
    """Information about a dataset."""

    dataset_id: str
    filename: str
    source: str
    shape: Dict[str, int] = Field(..., description="{'rows': N, 'columns': N}")
    columns: List[str]
    created_at: str
    last_accessed: str
    query_count: int
    column_info: Optional[Dict[str, str]] = Field(
        None, description="Data types for each column"
    )
    missing_values: Optional[Dict[str, int]] = Field(
        None, description="Count of missing values per column"
    )


class DatasetListResponse(BaseModel):
    """List of active datasets."""

    datasets: List[DatasetInfoResponse] = Field(
        ..., description="List of active dataset sessions"
    )
    total: int = Field(..., description="Total number of active datasets")


class ErrorResponse(BaseModel):
    """Error response."""

    success: bool = Field(default=False)
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")
