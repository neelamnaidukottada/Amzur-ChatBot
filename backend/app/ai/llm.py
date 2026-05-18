"""LiteLLM client singletons. All AI calls route through litellm.amzur.com."""

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import logging

from app.core.settings import settings

logger = logging.getLogger(__name__)


def get_chat_llm() -> ChatOpenAI:
    """
    Get LangChain ChatOpenAI client using LiteLLM proxy.
    
    Routes requests to https://litellm.amzur.com instead of OpenAI directly.
    Compatible with langchain-openai==1.2.1 and openai==2.36.0
    """
    try:
        # Initialize ChatOpenAI with LiteLLM proxy as the base URL
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.LITELLM_API_KEY,
            base_url=settings.LITELLM_PROXY_URL,
            temperature=0.7,
        )
        logger.info("✅ ChatOpenAI initialized successfully (via LiteLLM proxy)")
        return llm
    except Exception as e:
        logger.error(f"❌ ChatOpenAI initialization failed: {e}")
        raise


def get_vision_llm() -> ChatGoogleGenerativeAI:
    """
    Get LangChain Google Generative AI client for image analysis.
    
    Uses Google Gemini 2.0 Flash for vision/image analysis tasks.
    Has built-in support for image understanding and analysis.
    """
    try:
        # Initialize Google Generative AI with Gemini 2.0 Flash
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            api_key=settings.GOOGLE_GEMINI_API_KEY,
            temperature=0.7,
        )
        logger.info("✅ ChatGoogleGenerativeAI (Gemini 2.0 Flash) initialized successfully for vision")
        return llm
    except Exception as e:
        logger.error(f"❌ ChatGoogleGenerativeAI initialization failed: {e}")
        raise
