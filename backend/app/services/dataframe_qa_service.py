"""Dataframe Question Answering Service for CSV/Excel and Google Sheets data."""

import logging
from typing import Optional
from io import BytesIO
import pandas as pd
from pydantic import BaseModel

from app.ai.llm import get_chat_llm
from app.services.sheets_service import load_sheet_as_dataframe

logger = logging.getLogger(__name__)


class DataframeQueryResult(BaseModel):
    """Result of a dataframe query."""
    question: str
    answer: str
    source: str
    row_count: int
    columns: list[str]


class DataframeQAService:
    """Service for answering questions about dataframes."""
    
    def __init__(self):
        """Initialize the dataframe QA service."""
        self.llm = get_chat_llm()
        logger.info("[DataframeQAService] Initialized")
    
    def load_dataframe_from_file(self, file_bytes: bytes, filename: str) -> pd.DataFrame:
        """
        Load a dataframe from uploaded file bytes.
        
        Args:
            file_bytes: The file content as bytes
            filename: The original filename (used to determine format)
            
        Returns:
            Loaded pandas DataFrame
            
        Raises:
            ValueError: If file format is not supported
        """
        filename_lower = filename.lower()
        
        try:
            if filename_lower.endswith('.csv'):
                logger.info(f"[DataframeQAService] Loading CSV: {filename}")
                df = pd.read_csv(BytesIO(file_bytes))
            elif filename_lower.endswith(('.xlsx', '.xls')):
                logger.info(f"[DataframeQAService] Loading Excel: {filename}")
                df = pd.read_excel(BytesIO(file_bytes))
            else:
                raise ValueError(
                    f"Unsupported file format: {filename}. "
                    "Please upload a CSV or Excel file (.xlsx, .xls)"
                )
            
            logger.info(
                f"[DataframeQAService] Loaded dataframe from {filename}: "
                f"{len(df)} rows, {len(df.columns)} columns"
            )
            return df
        
        except Exception as exc:
            logger.error(f"[DataframeQAService] Error loading file {filename}: {str(exc)}")
            raise ValueError(f"Failed to load file {filename}: {str(exc)}")
    
    def load_dataframe_from_google_sheet(
        self,
        sheet_id_or_url: str,
        worksheet_name: str = "Sheet1",
        cell_range: str = "A1:Z1000",
    ) -> pd.DataFrame:
        """
        Load a dataframe from a Google Sheet.
        
        Args:
            sheet_id_or_url: Google Sheet ID or full URL
            worksheet_name: Name of the worksheet/tab
            cell_range: Cell range to load (e.g., A1:Z1000)
            
        Returns:
            Loaded pandas DataFrame
            
        Raises:
            ValueError: If sheet cannot be accessed
        """
        try:
            logger.info(f"[DataframeQAService] Loading Google Sheet via API: {sheet_id_or_url}")
            df = load_sheet_as_dataframe(
                sheet_id_or_url=sheet_id_or_url,
                worksheet_name=worksheet_name,
                cell_range=cell_range,
            )

            logger.info(
                f"[DataframeQAService] Loaded Google Sheet: "
                f"{len(df)} rows, {len(df.columns)} columns"
            )
            return df
        
        except Exception as exc:
            logger.error(
                f"[DataframeQAService] Error loading Google Sheet {sheet_id_or_url}: {str(exc)}"
            )
            raise ValueError(
                f"Failed to load Google Sheet: {str(exc)}. "
                "Ensure the sheet is shared and the URL/ID is correct."
            )
    
    def answer_question(
        self,
        df: pd.DataFrame,
        question: str,
        source: str = "unknown",
    ) -> DataframeQueryResult:
        """
        Answer a natural language question about the dataframe.
        
        Args:
            df: The pandas DataFrame
            question: The natural language question
            source: Source identifier (file name, sheet name, etc.)
            
        Returns:
            DataframeQueryResult with the answer
        """
        try:
            logger.info(f"[DataframeQAService] Processing question: {question}")
            
            # Create a summary of the dataframe for the LLM
            df_summary = self._create_dataframe_summary(df)
            
            # Build the prompt for the LLM
            prompt = f"""You are a data analysis assistant. A user has uploaded data and has a question about it.

DATA SUMMARY:
{df_summary}

USER QUESTION: {question}

Based on the data structure provided, answer the question directly and helpfully. 
If the question requires filtering or calculations, describe what you would do with the data.
Keep your answer concise and focused on answering the specific question."""
            
            # Get response from LLM
            response = self.llm.invoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(
                f"[DataframeQAService] Generated answer ({len(answer)} chars): "
                f"Question about {len(df)} rows"
            )
            
            return DataframeQueryResult(
                question=question,
                answer=answer,
                source=source,
                row_count=len(df),
                columns=list(df.columns),
            )
        
        except Exception as exc:
            logger.error(
                f"[DataframeQAService] Error processing question: {str(exc)}", exc_info=True
            )
            raise ValueError(f"Failed to process question: {str(exc)}")
    
    def _create_dataframe_summary(self, df: pd.DataFrame) -> str:
        """
        Create a concise summary of the dataframe for the LLM.
        
        Args:
            df: The pandas DataFrame
            
        Returns:
            String summary of the dataframe structure and content
        """
        summary_lines = []
        
        # Basic info
        summary_lines.append(f"Rows: {len(df)}")
        summary_lines.append(f"Columns: {len(df.columns)}")
        
        # Column information
        summary_lines.append("\nColumns and Types:")
        for col in df.columns:
            dtype = str(df[col].dtype)
            non_null = df[col].notna().sum()
            summary_lines.append(f"  - {col} ({dtype}, {non_null} non-null values)")
        
        # First few rows as example
        summary_lines.append("\nFirst 5 rows:")
        summary_lines.append(df.head().to_string())
        
        # Basic statistics for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            summary_lines.append("\nNumeric Column Statistics:")
            summary_lines.append(df[numeric_cols].describe().to_string())
        
        return "\n".join(summary_lines)


# Global singleton instance
_dataframe_qa_service: Optional[DataframeQAService] = None


def get_dataframe_qa_service() -> DataframeQAService:
    """Get the global dataframe QA service instance."""
    global _dataframe_qa_service
    if _dataframe_qa_service is None:
        _dataframe_qa_service = DataframeQAService()
    return _dataframe_qa_service
