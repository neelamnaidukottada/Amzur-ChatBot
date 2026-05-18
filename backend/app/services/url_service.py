"""Service for fetching and extracting content from URLs, including YouTube videos."""

import logging
from typing import Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
import re

from app.services.sheets_service import load_sheet_as_dataframe

logger = logging.getLogger(__name__)


class URLService:
    """Service for extracting content from URLs and YouTube videos."""

    @staticmethod
    def extract_youtube_video_id(url: str) -> Optional[str]:
        """
        Extract YouTube video ID from various YouTube URL formats.
        
        Args:
            url: YouTube URL in various formats
            
        Returns:
            Video ID or None if not a YouTube URL
        """
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
            r'youtube\.com\/embed\/([^&\n?#]+)',
            r'youtube\.com\/v\/([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None

    @staticmethod
    def fetch_youtube_transcript(video_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch transcript from YouTube video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dict with transcript text and metadata, or None if not available
        """
        try:
            logger.info(f"[URLService] Fetching transcript for YouTube video: {video_id}")
            
            transcript = None
            transcript_language = 'unknown'
            
            # Try to get transcript (English first, then any language)
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                transcript_language = 'English'
                logger.info(f"[URLService] ✅ Got English transcript")
            except Exception as e:
                logger.warning(f"[URLService] Could not get English transcript: {str(e)}")
                try:
                    # Try to get any available transcript (manually created or auto-generated)
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    
                    # Try manually created transcripts first
                    if hasattr(transcript_list, 'manually_created_transcripts') and transcript_list.manually_created_transcripts:
                        transcript = transcript_list.manually_created_transcripts[0].fetch()
                        transcript_language = transcript_list.manually_created_transcripts[0].language
                        logger.info(f"[URLService] ✅ Got manually created transcript in {transcript_language}")
                    # Then try auto-generated transcripts
                    elif hasattr(transcript_list, 'generated_transcripts') and transcript_list.generated_transcripts:
                        transcript = transcript_list.generated_transcripts[0].fetch()
                        transcript_language = transcript_list.generated_transcripts[0].language
                        logger.info(f"[URLService] ✅ Got auto-generated transcript in {transcript_language}")
                except Exception as e2:
                    logger.warning(f"[URLService] Could not get any transcript: {str(e2)}")
            
            if not transcript:
                logger.warning(f"[URLService] No transcripts available for video {video_id}")
                return None
            
            # Format transcript
            formatted_transcript = "\n".join([item['text'] for item in transcript])
            logger.info(f"[URLService] ✅ Successfully fetched {transcript_language} transcript: {len(formatted_transcript)} chars")
            
            return {
                'transcript': formatted_transcript,
                'language': transcript_language,
                'length': len(formatted_transcript)
            }
        except Exception as e:
            logger.error(f"[URLService] ❌ Error fetching YouTube transcript: {str(e)}")
            return None

    @staticmethod
    def extract_sheet_id(url: str) -> Optional[str]:
        """
        Extract Google Sheets ID from URL.
        
        Args:
            url: Google Sheets URL
            
        Returns:
            Sheet ID or None
        """
        # Pattern: https://docs.google.com/spreadsheets/d/{SHEET_ID}/...
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        return match.group(1) if match else None

    @staticmethod
    def fetch_google_sheets(url: str, max_length: int = 5000) -> Optional[str]:
        """
        Fetch content from Google Sheets using service account credentials.
        
        Args:
            url: Google Sheets URL
            max_length: Maximum character length to return
            
        Returns:
            Formatted sheet content or None if error
        """
        try:
            logger.info(f"[URLService] 📊 Attempting to fetch Google Sheets data from: {url[:80]}...")

            # Extract sheet ID from URL for diagnostics.
            sheet_id = URLService.extract_sheet_id(url)
            if not sheet_id:
                logger.error(f"[URLService] ❌ Could not extract sheet ID from URL")
                return URLService._fetch_google_sheets_csv(url, max_length)

            logger.info(f"[URLService] 📋 Opening spreadsheet with ID: {sheet_id}")

            # Use the shared Sheets API loader so URL analysis and dataframe endpoints behave the same.
            df = load_sheet_as_dataframe(
                sheet_id_or_url=url,
                worksheet_name="Sheet1",
                cell_range="A1:Z1000",
            )

            if df.empty and len(df.columns) == 0:
                logger.warning("[URLService] ⚠️ Spreadsheet returned no rows/columns")
                return None

            logger.info(
                "[URLService] ✅ Sheets API load succeeded: sheet_id=%s rows=%s cols=%s",
                sheet_id,
                len(df),
                len(df.columns),
            )

            # Keep output compact for LLM context.
            content = df.head(200).to_string(index=False)

            # Truncate if necessary
            if len(content) > max_length:
                content = content[:max_length] + f"\n\n[Truncated - showing first {max_length} characters]"

            logger.info(f"[URLService] ✅ Successfully extracted Google Sheets content: {len(content)} chars")
            return content

        except Exception as e:
            logger.warning(
                "[URLService] ⚠️ Sheets API access failed (%s: %s), trying CSV export fallback...",
                type(e).__name__,
                str(e),
            )
            return URLService._fetch_google_sheets_csv(url, max_length)

    @staticmethod
    def _fetch_google_sheets_csv(url: str, max_length: int = 5000) -> Optional[str]:
        """
        Fetch Google Sheets data by converting to CSV export URL.
        This works for public sheets without requiring authentication.
        
        Args:
            url: Google Sheets URL
            max_length: Maximum character length to return
            
        Returns:
            Formatted sheet content or None if error
        """
        try:
            logger.info(f"[URLService] 📊 Attempting CSV export fallback for Google Sheets...")
            
            # Extract sheet ID from URL
            sheet_id = URLService.extract_sheet_id(url)
            if not sheet_id:
                logger.error(f"[URLService] ❌ Could not extract sheet ID from URL")
                return None
            
            # Convert to CSV export URL (gid=0 is the first sheet)
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
            logger.info(f"[URLService] 📥 CSV Export URL: {csv_url}")
            
            # Fetch CSV
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(csv_url, timeout=10, headers=headers)
            response.raise_for_status()
            
            logger.info(f"[URLService] ✅ CSV fetched successfully ({len(response.content)} bytes)")
            
            # Parse CSV into formatted text
            csv_lines = response.text.strip().split('\n')
            content_lines = []
            
            for row_text in csv_lines:
                # Split by comma, handling quoted fields
                cells = [cell.strip().strip('"') for cell in row_text.split(',')]
                if any(cell for cell in cells):  # Skip empty rows
                    formatted_row = " | ".join(cells)
                    content_lines.append(formatted_row)
            
            content = "\n".join(content_lines)
            
            # Truncate if necessary
            if len(content) > max_length:
                content = content[:max_length] + f"\n\n[Truncated - showing first {max_length} characters]"
            
            logger.info(f"[URLService] ✅ Successfully extracted Google Sheets CSV content: {len(content)} chars, {len(content_lines)} rows")
            return content
            
        except Exception as e:
            logger.error(f"[URLService] ❌ Error fetching Google Sheets CSV: {str(e)}")
            return None

    @staticmethod
    def fetch_url_content(url: str, timeout: int = 10, max_length: int = 5000) -> Optional[str]:
        """
        Fetch and extract text content from a URL.
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            max_length: Maximum character length to return
            
        Returns:
            Extracted text content or None if error
        """
        try:
            logger.info(f"[URLService] Fetching content from URL: {url}")
            
            # Check if it's a Google Sheets URL
            if 'docs.google.com/spreadsheets' in url:
                logger.info(f"[URLService] 📊 Detected Google Sheets URL")
                sheets_content = URLService.fetch_google_sheets(url, max_length)
                if sheets_content:
                    logger.info(f"[URLService] ✅ Successfully fetched Google Sheets content")
                    return sheets_content
                else:
                    logger.warning(f"[URLService] ⚠️ Failed to fetch Google Sheets content, trying alternative method...")
            
            # Add headers to mimic browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            
            logger.info(f"[URLService] Status code: {response.status_code}")
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style tags
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean up whitespace
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            content = '\n'.join(lines[:max_length])
            
            logger.info(f"[URLService] ✅ Successfully extracted content: {len(content)} chars")
            
            return content
        except requests.exceptions.Timeout:
            logger.error(f"[URLService] ❌ Request timeout for URL: {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[URLService] ❌ Error fetching URL: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"[URLService] ❌ Unexpected error: {str(e)}")
            return None

    @staticmethod
    def process_url_or_video(url: str) -> Dict[str, Any]:
        """
        Process a URL or YouTube video and extract content.
        
        Args:
            url: URL to process
            
        Returns:
            Dict with content and metadata
        """
        logger.info(f"[URLService] Processing URL/video: {url}")
        
        result = {
            "success": False,
            "content": None,
            "source_type": None,
            "error": None,
            "metadata": {},
        }
        
        # Check if it's a YouTube URL
        video_id = URLService.extract_youtube_video_id(url)
        if video_id:
            logger.info(f"[URLService] Detected YouTube video: {video_id}")
            result["source_type"] = "youtube"
            result["metadata"]["video_id"] = video_id
            result["metadata"]["video_url"] = url
            
            transcript_data = URLService.fetch_youtube_transcript(video_id)
            if transcript_data and transcript_data.get('transcript'):
                result["content"] = f"[YouTube Video Transcript - {transcript_data.get('language', 'Unknown')} Language]\n\nVideo URL: {url}\n\n{transcript_data['transcript']}"
                result["metadata"]["transcript_language"] = transcript_data.get('language')
                result["metadata"]["transcript_length"] = transcript_data.get('length')
                result["success"] = True
                logger.info(f"[URLService] ✅ Successfully processed YouTube video")
            else:
                # Video doesn't have captions - provide helpful message
                result["error"] = "This YouTube video doesn't have captions/subtitles available. Try: 1) Sharing key points from the video, 2) Asking specific questions about it, or 3) Providing a summary you'd like me to discuss."
                result["metadata"]["reason"] = "no_captions"
                logger.warning(f"[URLService] Video {video_id} has no available captions")
        else:
            # Try as regular URL
            logger.info(f"[URLService] Processing as regular URL")
            result["source_type"] = "google_sheet" if 'docs.google.com/spreadsheets' in url else "webpage"
            result["metadata"]["url"] = url
            if result["source_type"] == "google_sheet":
                result["metadata"]["sheet_id"] = URLService.extract_sheet_id(url)
            
            content = URLService.fetch_url_content(url)
            if content:
                result["content"] = f"[Webpage Content]\n\nURL: {url}\n\n{content}"
                result["success"] = True
                logger.info(f"[URLService] ✅ Successfully processed webpage")
            else:
                result["error"] = "Could not fetch content from the URL. The page may not be accessible or may require authentication."
                if result["source_type"] == "google_sheet":
                    result["metadata"]["reason"] = "google_sheet_fetch_failed"
                logger.error(f"[URLService] Failed to fetch content from {url}")
        
        logger.info(f"[URLService] Processing result: success={result['success']}, type={result.get('source_type')}")
        return result
