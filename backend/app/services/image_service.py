"""Image generation service using Google Generative AI and fallback to LiteLLM proxy."""

import base64
import logging
import httpx
from app.core.settings import settings

logger = logging.getLogger(__name__)


def _normalize_image_mime(content_type: str | None, fallback_url: str) -> str:
    """Return a browser-renderable image mime type."""
    if isinstance(content_type, str):
        mime = content_type.split(";")[0].strip().lower()
        if mime.startswith("image/"):
            return mime

    lowered = (fallback_url or "").lower()
    if ".jpg" in lowered or ".jpeg" in lowered:
        return "image/jpeg"
    if ".webp" in lowered:
        return "image/webp"
    if ".gif" in lowered:
        return "image/gif"

    return "image/png"


class ImageService:
    """Service for generating images using Google Generative AI via LiteLLM proxy."""

    def __init__(self):
        logger.info(f"[ImageService] Initializing with model: {settings.IMAGE_GEN_MODEL}")

    async def generate_image(self, prompt: str, size: str = "1024x1024") -> dict:
        """
        Generate an image using Google Generative AI via LiteLLM proxy.

        Args:
            prompt: Image description/prompt.
            size: Image size (e.g. "1024x1024").

        Returns:
            Dictionary with url (data URI or remote URL), revised_prompt, model, source.
        """
        try:
            logger.info(f"[ImageService] 🎨 Generating image — model: {settings.IMAGE_GEN_MODEL}, prompt: {prompt[:80]}...")

            # Normalize model name for LiteLLM proxy
            model_name = settings.IMAGE_GEN_MODEL
            if not model_name.startswith("gemini/") and not model_name.startswith("openai/"):
                model_name = f"gemini/{model_name}"
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.LITELLM_PROXY_URL}/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {settings.LITELLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "n": 1,
                        "size": size,
                    },
                )

            if response.status_code != 200:
                error_body = response.text
                logger.error(f"[ImageService] ❌ Proxy returned {response.status_code}: {error_body}")
                raise Exception(f"LiteLLM proxy error {response.status_code}: {error_body}")

            data = response.json()
            logger.info(f"[ImageService] ✅ Proxy responded OK")

            image_data = data["data"][0]

            # Handle both URL and base64 formats
            if image_data.get("url"):
                image_url = image_data["url"]
                if isinstance(image_url, str) and image_url.startswith(("http://", "https://")):
                    # Some providers return signed/proxied URLs that fail in browser; convert to data URL for stability.
                    try:
                        async with httpx.AsyncClient(timeout=120.0) as client:
                            downloaded = await client.get(image_url)
                        if downloaded.status_code == 200 and downloaded.content:
                            content_type = _normalize_image_mime(
                                downloaded.headers.get("content-type"),
                                image_url,
                            )
                            encoded = base64.b64encode(downloaded.content).decode("utf-8")
                            image_url = f"data:{content_type};base64,{encoded}"
                            logger.info("[ImageService] Converted remote image URL to data URL for frontend compatibility")
                        else:
                            logger.warning(
                                "[ImageService] Could not download remote image URL (status=%s); returning original URL",
                                downloaded.status_code,
                            )
                    except Exception as dl_err:
                        logger.warning(
                            "[ImageService] Remote image download failed (%s); returning original URL",
                            dl_err,
                        )
            elif image_data.get("b64_json"):
                image_url = f"data:image/png;base64,{image_data['b64_json']}"
            else:
                raise ValueError(f"No image data in proxy response: {data}")

            revised_prompt = image_data.get("revised_prompt")
            if not isinstance(revised_prompt, str) or not revised_prompt.strip():
                revised_prompt = prompt

            return {
                "url": image_url,
                "revised_prompt": revised_prompt,
                "model": settings.IMAGE_GEN_MODEL,
                "source": "litellm-proxy",
            }

        except Exception as e:
            logger.error(f"[ImageService] ❌ Error: {str(e)}")
            raise Exception(f"Image generation failed: {str(e)}")


def get_image_service() -> ImageService:
    """Get ImageService instance."""
    return ImageService()
