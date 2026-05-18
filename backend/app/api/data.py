"""Data analysis router - HTTP endpoints for dataframe querying and analysis."""

import logging
from typing import Optional
from io import BytesIO

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user_email
from app.core.settings import settings
from app.schemas.data import (
    DatasetUploadResponse,
    GoogleSheetConnectRequest,
    GoogleSheetConnectResponse,
    DataQueryRequest,
    DataQueryResponse,
    DatasetListResponse,
    DatasetInfoResponse,
    ErrorResponse,
)
from app.services.pandas_agent_service import get_pandas_agent_service
from app.services.dataframe_session_service import get_dataframe_session_service
from app.services.dataframe_qa_service import DataframeQAService
from app.services.url_service import URLService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("/upload", response_model=DatasetUploadResponse)
async def upload_spreadsheet(
    file: UploadFile = File(...),
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> DatasetUploadResponse:
    """
    Upload a CSV or Excel file for analysis.

    Args:
        file: CSV or Excel (.xlsx, .xls) file
        user_email: Current authenticated user email
        db: Database session

    Returns:
        DatasetUploadResponse with dataset metadata

    Raises:
        HTTPException: If file format is invalid or upload fails
    """
    try:
        logger.info(f"[Data API] Uploading file: {file.filename}")

        # Validate file type
        filename_lower = file.filename.lower()
        if not filename_lower.endswith((".csv", ".xlsx", ".xls")):
            logger.error(f"[Data API] Invalid file type: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be CSV or Excel (.xlsx, .xls)",
            )

        # Read file content
        content = await file.read()

        # Check file size
        max_size_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
        if len(content) > max_size_bytes:
            logger.error(
                f"[Data API] File too large: {len(content)} bytes > {max_size_bytes}"
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds {settings.MAX_UPLOAD_MB}MB limit",
            )

        # Load dataframe using existing service
        qa_service = DataframeQAService()
        df = qa_service.load_dataframe_from_file(content, file.filename)

        # Create session
        session_service = get_dataframe_session_service()
        dataset_id = session_service.create_session(
            filename=file.filename, df=df, source="file"
        )

        logger.info(
            f"[Data API] File uploaded successfully - {dataset_id}: {file.filename}"
        )

        # Get sample data
        sample_data = df.head(3).to_dict(orient="records")

        return DatasetUploadResponse(
            dataset_id=dataset_id,
            filename=file.filename,
            source="file",
            rows=len(df),
            columns=len(df.columns),
            column_names=list(df.columns),
            sample_data=sample_data,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[Data API] Error uploading file: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(exc)}",
        )


@router.post("/google-sheet", response_model=GoogleSheetConnectResponse)
async def connect_google_sheet(
    request: GoogleSheetConnectRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> GoogleSheetConnectResponse:
    """
    Connect to a Google Sheet for analysis.

    Args:
        request: GoogleSheetConnectRequest with sheet URL or ID
        user_email: Current authenticated user email
        db: Database session

    Returns:
        GoogleSheetConnectResponse with dataset metadata

    Raises:
        HTTPException: If sheet cannot be accessed
    """
    try:
        logger.info("[Data API] Connecting to Google Sheet")

        # Validate that either URL or ID is provided
        if not request.google_sheet_url and not request.google_sheet_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either google_sheet_url or google_sheet_id must be provided",
            )

        # Determine sheet identifier
        sheet_identifier = request.google_sheet_url or request.google_sheet_id

        logger.info(f"[Data API] Loading Google Sheet: {sheet_identifier}")

        # Load dataframe from Google Sheet
        qa_service = DataframeQAService()
        df = qa_service.load_dataframe_from_google_sheet(
            sheet_id_or_url=sheet_identifier,
            worksheet_name=request.worksheet_name or "Sheet1",
        )

        # Extract sheet ID for response
        sheet_id = sheet_identifier
        if "docs.google.com" in sheet_identifier:
            parts = sheet_identifier.split("/d/")
            if len(parts) > 1:
                sheet_id = parts[1].split("/")[0]

        # Create session
        session_service = get_dataframe_session_service()
        dataset_id = session_service.create_session(
            filename=f"Google Sheet: {sheet_id}",
            df=df,
            source="google_sheet",
        )

        logger.info(
            f"[Data API] Google Sheet connected - {dataset_id}: {sheet_id}"
        )

        return GoogleSheetConnectResponse(
            dataset_id=dataset_id,
            filename=f"Google Sheet: {sheet_id}",
            source="google_sheet",
            rows=len(df),
            columns=len(df.columns),
            column_names=list(df.columns),
            sheet_id=sheet_id,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"[Data API] Error connecting to Google Sheet: {str(exc)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to Google Sheet: {str(exc)}",
        )


@router.post("/query", response_model=DataQueryResponse)
async def query_dataset(
    request: DataQueryRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> DataQueryResponse:
    """
    Query a dataset with a natural language question using LangChain Pandas Agent.

    Args:
        request: DataQueryRequest with dataset_id and question
        user_email: Current authenticated user email
        db: Database session

    Returns:
        DataQueryResponse with AI-generated answer

    Raises:
        HTTPException: If dataset not found or query fails
    """
    try:
        logger.info(
            f"[Data API] Query request - Dataset: {request.dataset_id}, "
            f"Question: {request.question[:50]}..."
        )

        # Get session
        session_service = get_dataframe_session_service()
        session = session_service.get_session(request.dataset_id)

        if not session:
            logger.warning(f"[Data API] Dataset not found: {request.dataset_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset not found: {request.dataset_id}",
            )

        logger.info(
            f"[Data API] Found session for {request.dataset_id}: {session.filename}"
        )

        # Get optional context from conversation history
        context = None
        if request.include_context:
            context = session_service.get_context(request.dataset_id, max_entries=5)
            logger.info(f"[Data API] Using conversation context")

        # Query with pandas agent
        agent_service = get_pandas_agent_service()
        result = agent_service.query_with_context(
            df=session.df,
            question=request.question,
            context=context,
            source=session.filename,
        )

        if not result["success"]:
            logger.error(f"[Data API] Query failed: {result.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query failed: {result.get('error')}",
            )

        # Add to session history
        session_service.add_to_history(
            request.dataset_id, request.question, result["answer"]
        )

        logger.info(
            f"[Data API] Query completed successfully for {request.dataset_id}"
        )

        return DataQueryResponse(
            success=True,
            question=request.question,
            answer=result["answer"],
            source=session.filename,
            row_count=result["row_count"],
            column_count=result["column_count"],
            columns=result["columns"],
            has_context=request.include_context,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[Data API] Error processing query: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(exc)}",
        )


@router.get("/datasets", response_model=DatasetListResponse)
async def list_datasets(
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> DatasetListResponse:
    """
    List all active datasets for the current session.

    Args:
        user_email: Current authenticated user email
        db: Database session

    Returns:
        DatasetListResponse with list of active datasets
    """
    try:
        logger.info("[Data API] Listing active datasets")

        session_service = get_dataframe_session_service()
        datasets_data = session_service.list_sessions()

        # Convert to DatasetInfoResponse objects
        datasets = [DatasetInfoResponse(**d) for d in datasets_data]

        logger.info(f"[Data API] Found {len(datasets)} active datasets")

        return DatasetListResponse(datasets=datasets, total=len(datasets))

    except Exception as exc:
        logger.error(f"[Data API] Error listing datasets: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list datasets: {str(exc)}",
        )


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> dict:
    """
    Delete a dataset session.

    Args:
        dataset_id: The dataset ID to delete
        user_email: Current authenticated user email
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If dataset not found
    """
    try:
        logger.info(f"[Data API] Deleting dataset: {dataset_id}")

        session_service = get_dataframe_session_service()
        deleted = session_service.delete_session(dataset_id)

        if not deleted:
            logger.warning(f"[Data API] Dataset not found for deletion: {dataset_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset not found: {dataset_id}",
            )

        logger.info(f"[Data API] Dataset deleted: {dataset_id}")

        return {"success": True, "message": f"Dataset {dataset_id} deleted"}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[Data API] Error deleting dataset: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete dataset: {str(exc)}",
        )


@router.get("/datasets/{dataset_id}")
async def get_dataset_info(
    dataset_id: str,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> DatasetInfoResponse:
    """
    Get information about a specific dataset.

    Args:
        dataset_id: The dataset ID
        user_email: Current authenticated user email
        db: Database session

    Returns:
        DatasetInfoResponse with metadata

    Raises:
        HTTPException: If dataset not found
    """
    try:
        logger.info(f"[Data API] Getting info for dataset: {dataset_id}")

        session_service = get_dataframe_session_service()
        session = session_service.get_session(dataset_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset not found: {dataset_id}",
            )

        # Get agent service for summary
        agent_service = get_pandas_agent_service()
        summary = agent_service.get_dataframe_summary(session.df)

        info = DatasetInfoResponse(
            dataset_id=dataset_id,
            filename=session.filename,
            source=session.source,
            shape=summary["shape"],
            columns=summary["columns"],
            created_at=session.created_at.isoformat(),
            last_accessed=session.last_accessed.isoformat(),
            query_count=session.query_count,
            column_info=summary["dtypes"],
            missing_values=summary["missing_values"],
        )

        logger.info(f"[Data API] Retrieved info for {dataset_id}")
        return info

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[Data API] Error getting dataset info: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dataset info: {str(exc)}",
        )
