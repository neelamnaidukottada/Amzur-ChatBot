"""Google Sheets loading service backed by Google Sheets API."""

import json
import logging
from pathlib import Path
from typing import Any

import gspread
import pandas as pd

from app.core.settings import settings

logger = logging.getLogger(__name__)

GOOGLE_SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _parse_service_account_info(raw_value: str) -> dict[str, Any]:
    """Parse service account value from env as JSON string or JSON file path."""
    value = (raw_value or "").strip()
    if not value:
        value = (settings.GOOGLE_SERVICE_ACCOUNT_FILE or "").strip()

    if not value:
        raise ValueError(
            "Google service account is not configured. "
            "Set GOOGLE_SERVICE_ACCOUNT_JSON to full JSON content (preferred) or a JSON key file path."
        )

    # Preferred mode: full JSON content in env.
    if value.startswith("{"):
        service_account = json.loads(value)
    else:
        key_path = Path(value)
        if not key_path.exists():
            raise ValueError(
                "GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON and does not point to an existing file path"
            )
        with key_path.open("r", encoding="utf-8") as f:
            service_account = json.load(f)

    # When env values contain escaped newlines, normalize the private key.
    private_key = service_account.get("private_key")
    if isinstance(private_key, str) and "\\n" in private_key:
        service_account["private_key"] = private_key.replace("\\n", "\n")

    required_keys = {"client_email", "private_key", "project_id"}
    missing = [k for k in required_keys if not service_account.get(k)]
    if missing:
        raise ValueError(f"Service account JSON is missing required keys: {', '.join(missing)}")

    return service_account


def _extract_sheet_key(sheet_id_or_url: str) -> str:
    """Extract Google Sheet key from URL or return raw id."""
    identifier = (sheet_id_or_url or "").strip()
    if not identifier:
        raise ValueError("Google Sheet ID or URL is required")

    if "docs.google.com/spreadsheets" in identifier and "/d/" in identifier:
        return identifier.split("/d/")[1].split("/")[0]

    return identifier


def _coerce_dataframe_types(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort dtype coercion for sheet data loaded as strings."""
    if df.empty:
        return df

    for column in df.columns:
        series = df[column]
        if not pd.api.types.is_object_dtype(series):
            continue

        cleaned = (
            series.astype(str)
            .str.strip()
            .replace({"": pd.NA, "None": pd.NA, "nan": pd.NA, "NaN": pd.NA})
        )

        # Parse numeric-looking values (supports commas/currency symbols).
        numeric_candidate = cleaned.str.replace(r"[^0-9.\-]", "", regex=True)
        numeric = pd.to_numeric(numeric_candidate, errors="coerce")

        valid_original = cleaned.notna().sum()
        valid_numeric = numeric.notna().sum()
        if valid_original > 0 and (valid_numeric / valid_original) >= 0.8:
            df[column] = numeric
            continue

        # Parse datetime-like values when majority can be parsed.
        dates = pd.to_datetime(cleaned, errors="coerce", dayfirst=True)
        valid_dates = dates.notna().sum()
        if valid_original > 0 and (valid_dates / valid_original) >= 0.8:
            df[column] = dates

    return df


def load_sheet_as_dataframe(
    sheet_id_or_url: str,
    worksheet_name: str = "Sheet1",
    cell_range: str = "A1:Z1000",
) -> pd.DataFrame:
    """Load a Google Sheet worksheet range into a Pandas DataFrame."""
    try:
        service_account_info = _parse_service_account_info(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
        client = gspread.service_account_from_dict(
            service_account_info,
            scopes=GOOGLE_SHEETS_SCOPES,
        )

        sheet_key = _extract_sheet_key(sheet_id_or_url)
        spreadsheet = client.open_by_key(sheet_key)

        worksheet = (
            spreadsheet.worksheet(worksheet_name)
            if worksheet_name
            else spreadsheet.get_worksheet(0)
        )

        values = worksheet.get(cell_range) if cell_range else worksheet.get_all_values()

        if not values:
            raise ValueError("Worksheet range returned no data")

        header = values[0]
        rows = values[1:] if len(values) > 1 else []

        # Ensure every column has a non-empty header for robust DataFrame operations.
        normalized_header = [
            str(col).strip() if str(col).strip() else f"column_{idx + 1}"
            for idx, col in enumerate(header)
        ]

        df = pd.DataFrame(rows, columns=normalized_header)
        df = _coerce_dataframe_types(df)

        logger.info(
            "[SheetsService] Loaded Google Sheet key=%s worksheet=%s rows=%s cols=%s",
            sheet_key,
            worksheet.title,
            len(df),
            len(df.columns),
        )
        return df

    except Exception as exc:
        share_email = ""
        try:
            service_account_info = _parse_service_account_info(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
            share_email = str(service_account_info.get("client_email") or "")
        except Exception:
            share_email = ""

        logger.error("[SheetsService] Failed to load Google Sheet: %s", str(exc), exc_info=True)
        share_hint = (
            f" Share the sheet with service account: {share_email}." if share_email else ""
        )
        raise ValueError(
            "Failed to load Google Sheet via API. Ensure APIs are enabled, the sheet ID is correct, and the sheet is shared with the service account."
            f"{share_hint}"
            " "
            f"Details: {str(exc)}"
        )
