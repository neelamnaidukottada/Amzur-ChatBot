"""Chat router - HTTP endpoints for chat functionality."""

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging
import re
from typing import Optional, List
import json

from app.core.database import get_db
from app.core.auth import get_current_user_email
from app.core.settings import settings
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    DatabaseQuestionRequest,
    DatabaseQuestionResponse,
    DataframeQuestionResponse,
)
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationSummaryResponse,
)
from app.services.chat_service import get_chat_service
from app.services.conversation_service import ConversationService
from app.services.auth_service import AuthService
from app.services.image_service import get_image_service
from app.services.file_service import FileService
from app.services.rag_service import get_rag_service
from app.services.url_service import URLService
from app.services.sql_qa_service import get_sql_qa_service
from app.services.dataframe_qa_service import get_dataframe_qa_service
from app.services.dataframe_cache import get_dataframe_cache
from app.services.pandas_agent_service import get_pandas_agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _should_route_to_dataframe_followup(message: str, columns: List[str]) -> bool:
    """Decide if a follow-up message should use cached dataframe QA."""
    text = (message or "").strip().lower()
    if not text:
        return False

    # Questions asking for conceptual explanation should stay in general chat.
    conceptual_patterns = [
        r"\bbrief theory\b",
        r"\bexplain\b",
        r"\bwhat is the above query\b",
        r"\bmeaning\b",
        r"\bdefinition\b",
        r"\bhow does (this|that|it) work\b",
    ]
    if any(re.search(pattern, text) for pattern in conceptual_patterns):
        # Let this fall through to normal LLM chat unless clearly analytical.
        has_math_intent = any(
            token in text
            for token in ["sum", "average", "mean", "count", "max", "min", "total", "calculate"]
        )
        if not has_math_intent:
            return False

    analytical_keywords = [
        "sum", "total", "average", "avg", "mean", "count", "max", "min",
        "highest", "lowest", "top", "bottom", "group by", "filter", "where",
        "calculate", "compute", "compare", "percentage", "distribution",
        "how many", "list", "show", "find", "column", "rows", "dataset", "sheet",
    ]
    if any(keyword in text for keyword in analytical_keywords):
        return True

    # If the message references any known dataframe column, route to dataframe QA.
    normalized_text = re.sub(r"[^a-z0-9]", "", text)
    for col in columns:
        col_norm = re.sub(r"[^a-z0-9]", "", str(col).lower())
        if col_norm and col_norm in normalized_text:
            return True

    return False


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: Request,
    user_email: str = Depends(get_current_user_email),
    conversation_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    """
    Send a message and get an AI response. Supports both JSON and multipart/form-data.
    
    Accepts either:
    - JSON: {"user_message": "text"}
    - FormData: user_message + optional files
    
    Args:
        request: FastAPI request object to handle different content types.
        user_email: Current authenticated user email.
        conversation_id: Conversation ID (optional).
        db: Database session.
        
    Returns:
        ChatMessageResponse with assistant response.
    """
    try:
        logger.info(f"[Chat] ========== NEW MESSAGE REQUEST ==========")
        logger.info(f"[Chat] Request content-type: {request.headers.get('content-type', 'UNKNOWN')}")
        
        # Get user
        user = AuthService.get_user_by_email(db, user_email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        user_message = None
        files = []
        
        # Determine if request is JSON or FormData
        content_type = request.headers.get("content-type", "")
        logger.info(f"[Chat] Content-Type header value: '{content_type}'")
        
        if "application/json" in content_type:
            # Handle JSON request (text-only message)
            body = await request.json()
            user_message = body.get("user_message", "")
            logger.info("[Chat] ✅ Received JSON request - TEXT ONLY")
            
        elif "multipart/form-data" in content_type:
            # Handle FormData request (with or without files)
            form_data = await request.form()
            user_message = form_data.get("user_message", "")
            
            # Get files if any - check both uppercase and lowercase
            files_list = form_data.getlist("files") or form_data.getlist("file") or []
            logger.info(f"[Chat] ✅ Received FormData request - Detected {len(files_list)} files")
            if files_list:
                files = [f for f in files_list if hasattr(f, 'filename')]
                logger.info(f"[Chat] ✅ Valid file objects: {len(files)}")
                for f in files:
                    logger.info(f"[Chat]   - File: {f.filename} (type: {f.content_type})")
            else:
                logger.info("[Chat] ℹ️ FormData request but NO FILES detected")
        else:
            logger.warning(f"[Chat] ⚠️ Unsupported content-type: {content_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid content type. Expected application/json or multipart/form-data",
            )
        
        if not user_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_message is required",
            )
        
        logger.info(f"[Chat] CHECKING FILES: received {len(files)} files")

        # Create conversation early so uploaded files can be indexed per conversation
        if not conversation_id:
            conversation = ConversationService.create_conversation(db, user.id)
            conversation_id = conversation.id
        
        # Process message with files if any
        message_content = user_message
        
        if files and len(files) > 0:
            logger.info(f"[Chat] ⭐ ENTERING FILE PROCESSING BLOCK - {len(files)} file(s) detected")
            file_contents = []
            
            for file in files:
                try:
                    file_content = await file.read()
                    logger.info(f"[Chat] ✅ READ FILE: {file.filename} - {len(file_content)} bytes")
                    
                    content_type_value = file.content_type or "application/octet-stream"
                    extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''

                    # Use RAG path for PDFs: index in ChromaDB and provide an indexing note in prompt.
                    if extension == "pdf" or "pdf" in content_type_value.lower():
                        rag_service = get_rag_service()
                        chunk_count = rag_service.ingest_pdf(
                            file_content=file_content,
                            filename=file.filename,
                            user_id=user.id,
                            conversation_id=conversation_id,
                        )
                        extracted_text = (
                            f"[PDF indexed for retrieval with ChromaDB. "
                            f"Indexed chunks: {chunk_count}. "
                            "Ask questions and I will use RAG context from this file.]"
                        )
                        logger.info(
                            f"[Chat] ✅ PDF indexed in RAG store: {file.filename}, chunks={chunk_count}"
                        )
                    else:
                        # Extract text from non-PDF files directly into the prompt.
                        logger.info(f"[Chat] 🔄 CALLING FileService.extract_text_from_file() for {file.filename}")
                        extracted_text = FileService.extract_text_from_file(
                            file_content,
                            file.filename,
                            content_type_value,
                        )
                        logger.info(f"[Chat] EXTRACTED: {len(str(extracted_text)) if extracted_text else 0} chars from {file.filename}")
                    
                    # ALWAYS append file content to message (with or without extraction)
                    if extracted_text and len(str(extracted_text).strip()) > 0:
                        file_content_str = str(extracted_text)
                        logger.info(f"[Chat] ✅ Using extracted content: {len(file_content_str)} chars")
                    else:
                        # Even if extraction failed, include a placeholder
                        file_content_str = f"[File could not be read: {file.filename}]"
                        logger.warning(f"[Chat] ⚠️ Extraction empty for {file.filename}")
                    
                    # ALWAYS append with proper formatting
                    formatted_content = f"\n\n===== FILE START: {file.filename} =====\n{file_content_str}\n===== FILE END: {file.filename} ====="
                    file_contents.append(formatted_content)
                    logger.info(f"[Chat] ✅ APPENDED file block: {len(formatted_content)} chars")
                    
                except Exception as e:
                    logger.error(f"[Chat] ❌ ERROR processing file {file.filename}: {str(e)}", exc_info=True)
                    # Still append error message
                    error_block = f"\n\n===== FILE ERROR: {file.filename} =====\nError reading file: {str(e)}\n===== FILE ERROR END ====="
                    file_contents.append(error_block)
                    logger.warning(f"[Chat] ⚠️ Appended error block for {file.filename}")
            
            # CRITICAL: Always append file contents if files were processed
            if file_contents:
                message_content = user_message + "".join(file_contents)
                logger.info(f"[Chat] ✅✅✅ FINAL MESSAGE - Total length: {len(message_content)} chars")
                logger.info(f"[Chat] ✅✅✅ Message preview (first 300 chars): {message_content[:300]}")
            else:
                logger.error(f"[Chat] ❌❌❌ FILES WERE PROCESSED BUT file_contents is EMPTY!")
        else:
            logger.info(f"[Chat] No files - text only message")

            # If tabular data is cached for this conversation, answer follow-up questions from that dataframe.
            df_cache = get_dataframe_cache()
            cached_data = df_cache.retrieve(conversation_id)
            if cached_data:
                if _should_route_to_dataframe_followup(user_message, cached_data.columns):
                    logger.info(
                        "[Chat][DATAFRAME_FOLLOWUP] Using cached %s for conv_id=%s (%s rows, %s cols)",
                        cached_data.source,
                        conversation_id,
                        cached_data.row_count,
                        len(cached_data.columns),
                    )

                    pandas_agent_service = get_pandas_agent_service()
                    agent_result = pandas_agent_service.query(
                        df=cached_data.df,
                        question=user_message,
                        source=f"cached:{cached_data.display_name}",
                    )

                    if agent_result.get("success"):
                        assistant_response = agent_result.get("answer", "")
                        ConversationService.add_message(db, conversation_id, user.id, "user", user_message)
                        ConversationService.add_message(db, conversation_id, user.id, "assistant", assistant_response)
                        logger.info(
                            "[Chat][DATAFRAME_FOLLOWUP] Answered from cache, len=%s",
                            len(assistant_response),
                        )
                        return ChatMessageResponse(
                            user_message=user_message,
                            assistant_response=assistant_response,
                        )

                    logger.warning(
                        "[Chat][DATAFRAME_FOLLOWUP] Cached dataframe query failed, falling back to normal chat: %s",
                        agent_result.get("error"),
                    )
                else:
                    logger.info(
                        "[Chat][DATAFRAME_FOLLOWUP] Cached dataframe exists but prompt is conceptual; using normal chat flow"
                    )

            # Dynamic meta-followup handling: explain the immediately previous query/answer in this chat.
            meta_followup_patterns = [
                r"\babove\s+query\b",
                r"\bprevious\s+query\b",
                r"\bwhat\s+did\s+i\s+ask\b",
                r"\bexplain\s+the\s+query\b",
            ]
            if any(re.search(pattern, user_message.lower()) for pattern in meta_followup_patterns):
                current_conv = ConversationService.get_conversation(db, conversation_id, user.id)
                if current_conv and current_conv.messages:
                    ordered = sorted(current_conv.messages, key=lambda m: m.created_at)
                    previous_user = None
                    previous_assistant = None

                    # Walk backward to find latest assistant and user messages before current turn.
                    for msg in reversed(ordered):
                        if previous_assistant is None and msg.sender == "assistant":
                            previous_assistant = msg.content
                        elif previous_user is None and msg.sender == "user":
                            previous_user = msg.content
                        if previous_user and previous_assistant:
                            break

                    if previous_user or previous_assistant:
                        context_parts = []
                        if previous_user:
                            context_parts.append(f"Previous user query: {previous_user}")
                        if previous_assistant:
                            context_parts.append(f"Previous assistant answer: {previous_assistant}")

                        message_content = (
                            f"{user_message}\n\n"
                            "[FOLLOW_UP_CONTEXT]\n"
                            + "\n".join(context_parts)
                            + "\n\n"
                            "Explain the previous query in simple, concise language. "
                            "Do not fabricate data and do not output code unless requested."
                        )
                        logger.info("[Chat][META_FOLLOWUP] Injected previous query/answer context")
            
            # ✨ NEW: For follow-up questions, retrieve file context from previous messages
            logger.info(f"[Chat] 🔍 Checking for file context from previous messages in conversation {conversation_id}")
            previous_file_context = ConversationService.get_file_context_from_conversation(db, conversation_id)
            
            if previous_file_context:
                logger.info(f"[Chat] ✅ Found previous file context ({len(previous_file_context)} chars)")
                message_content = user_message + previous_file_context
                logger.info(f"[Chat] ✅ APPENDED previous file context to message for follow-up analysis")
            else:
                logger.info(f"[Chat] ℹ️ No previous file context found in conversation")
        
        logger.info(f"[Chat] BEFORE LLM - Message length: {len(message_content)} chars")
        
        # Check for all types of markers
        has_file_markers = "[File" in message_content or "=====" in message_content
        has_image_marker = "[IMAGE ANALYSIS REQUEST]" in message_content
        
        if has_file_markers or has_image_marker:
            logger.info(f"[Chat] ✅ Confirmed: Content markers present in message!")
            if has_image_marker:
                logger.info(f"[Chat] ✅ IMAGE MARKER DETECTED - Will trigger vision LLM")
            if has_file_markers:
                logger.info(f"[Chat] ✅ FILE MARKERS DETECTED - Will include file content")
        else:
            logger.warning(f"[Chat] ⚠️ Warning: No content markers in message!")
        
        # ✨ NEW: Fetch CURRENT conversation messages for context
        logger.info(f"[Chat] 📚 Fetching current conversation messages")
        current_conversation = ConversationService.get_conversation(db, conversation_id, user.id)
        logger.info(f"[Chat] 📚 Current conversation has {len(current_conversation.messages) if current_conversation else 0} messages")
        
        # Fetch previous conversations for context (last 5 conversations excluding current one)
        logger.info(f"[Chat] 📚 Fetching previous conversations for context")
        previous_conversations = ConversationService.get_previous_conversations(
            db,
            user.id,
            current_conversation_id=conversation_id,
            limit=5,
        )
        logger.info(f"[Chat] 📚 Retrieved {len(previous_conversations)} previous conversations")
        
        # Generate response with conversation context
        chat_service = get_chat_service(db=db)
        logger.info(f"[Chat] 📨 About to call chat_service.generate_response()")
        logger.info(f"[Chat]   - message_content length: {len(message_content)}")
        logger.info(f"[Chat]   - conversation_id: {conversation_id}")
        logger.info(f"[Chat]   - user_id: {user.id}")
        
        assistant_response = chat_service.generate_response(
            user_message=message_content,
            retrieval_query=user_message,
            user_email=user_email,
            conversation_id=conversation_id,
            user_id=user.id,
            current_conversation=current_conversation,
            previous_conversations=previous_conversations,
        )
        
        # Verify response
        logger.info(f"[Chat] 📤 Response received from chat_service")
        logger.info(f"[Chat]   - Response type: {type(assistant_response)}")
        logger.info(f"[Chat]   - Response is None: {assistant_response is None}")
        logger.info(f"[Chat]   - Response length: {len(assistant_response) if assistant_response else 0}")
        logger.info(f"[Chat]   - Response is empty string: {assistant_response == ''}")
        logger.info(f"[Chat]   - Response stripped: '{assistant_response.strip() if assistant_response else ''}'")
        
        if not assistant_response:
            logger.error(f"[Chat] ❌ EMPTY RESPONSE FROM CHAT SERVICE!")
            assistant_response = "I apologize, but I'm unable to generate a response at this time. Please try again."
        
        logger.info(f"[Chat] ✅ Response preview (first 200 chars): {assistant_response[:200]}...")
        
        return ChatMessageResponse(
            user_message=user_message,
            assistant_response=assistant_response,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Chat] Error processing message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "llm_error", "message": str(e)},
        )


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """
    Create a new conversation.
    
    Args:
        data: Conversation creation data.
        user_email: Current authenticated user email.
        db: Database session.
        
    Returns:
        Created conversation.
    """
    user = AuthService.get_user_by_email(db, user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    conversation = ConversationService.create_conversation(db, user.id, data.title)
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[],
    )


@router.get("/conversations", response_model=list[ConversationSummaryResponse])
async def get_conversations(
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> list[ConversationSummaryResponse]:
    """
    Get all conversations for the current user.
    
    Args:
        user_email: Current authenticated user email.
        db: Database session.
        
    Returns:
        List of conversation summaries.
    """
    user = AuthService.get_user_by_email(db, user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return ConversationService.get_user_conversations(db, user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """
    Get a specific conversation with all messages.
    
    Args:
        conversation_id: Conversation ID.
        user_email: Current authenticated user email.
        db: Database session.
        
    Returns:
        Conversation with messages.
    """
    user = AuthService.get_user_by_email(db, user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    try:
        conversation = ConversationService.get_conversation(db, conversation_id, user.id)
        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[
                {
                    "id": msg.id,
                    "sender": msg.sender,
                    "content": msg.content,
                    "created_at": msg.created_at,
                }
                for msg in conversation.messages
            ],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Delete a conversation.
    
    Args:
        conversation_id: Conversation ID.
        user_email: Current authenticated user email.
        db: Database session.
    """
    user = AuthService.get_user_by_email(db, user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    try:
        ConversationService.delete_conversation(db, conversation_id, user.id)
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    data: ConversationCreate,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """
    Update a conversation (e.g., rename).
    
    Args:
        conversation_id: Conversation ID.
        data: Updated conversation data.
        user_email: Current authenticated user email.
        db: Database session.
        
    Returns:
        Updated conversation.
    """
    user = AuthService.get_user_by_email(db, user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    try:
        if data.title:
            conversation = ConversationService.update_conversation_title(
                db, conversation_id, user.id, data.title
            )
        else:
            conversation = ConversationService.get_conversation(db, conversation_id, user.id)
        
        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[
                {
                    "id": msg.id,
                    "sender": msg.sender,
                    "content": msg.content,
                    "created_at": msg.created_at,
                }
                for msg in conversation.messages
            ],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ============ Image Generation Schemas ============

class GenerateImageRequest(BaseModel):
    """Request to generate an image."""
    prompt: str
    size: str = "1024x1024"


class GenerateImageResponse(BaseModel):
    """Response with generated image."""
    url: str
    prompt: str
    revised_prompt: str
    model: str = "gemini-2.0-flash"
    source: str = "google-gemini"


# ============ Image Generation Endpoint ============

@router.post("/generate-image", response_model=GenerateImageResponse)
async def generate_image(
    request: GenerateImageRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> GenerateImageResponse:
    """
    Generate an image using Google Gemini 2.0 Flash.
    
    Args:
        request: Image generation request with prompt and optional size.
        user_email: Current authenticated user email.
        db: Database session.
        
    Returns:
        GenerateImageResponse with image URL and metadata.
    """
    logger.info(f"[ImageGeneration] Image generation request received from {user_email}")
    logger.info(f"[ImageGeneration] Prompt: {request.prompt[:60]}...")
    
    try:
        # Verify user exists
        user = AuthService.get_user_by_email(db, user_email)
        if not user:
            logger.warning(f"[ImageGeneration] User not found: {user_email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        logger.info(f"[ImageGeneration] 🎨 Generating image for user: {user.email}")
        # Generate image
        image_service = get_image_service()
        image_data = await image_service.generate_image(
            prompt=request.prompt,
            size=request.size,
        )

        revised_prompt = image_data.get("revised_prompt")
        if not isinstance(revised_prompt, str) or not revised_prompt.strip():
            revised_prompt = request.prompt

        generated_url = image_data.get("url", "")
        if isinstance(generated_url, str):
            logger.info(
                "[ImageGeneration] URL format=%s length=%s",
                "data-url" if generated_url.startswith("data:") else "remote-url",
                len(generated_url),
            )
        
        logger.info(f"[ImageGeneration] ✅ Image generated successfully for user: {user.email}")
        return GenerateImageResponse(
            url=generated_url,
            prompt=request.prompt,
            revised_prompt=revised_prompt,
            model=image_data.get("model", "gemini-2.0-flash"),
            source=image_data.get("source", "google-gemini"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ImageGeneration] ❌ Image generation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "image_generation_error", "message": str(e)},
        )


# ============ URL Analysis Schemas ============

class URLAnalysisRequest(BaseModel):
    """Request to analyze a URL or video."""
    url: str
    user_message: str = "Analyze this content"
    conversation_id: Optional[int] = None


class URLAnalysisResponse(BaseModel):
    """Response with analyzed URL content."""
    user_message: str
    assistant_response: str
    conversation_id: Optional[int] = None


# ============ Database Q&A Endpoint ============

@router.post("/database-question", response_model=DatabaseQuestionResponse)
async def ask_database_question(
    request: DatabaseQuestionRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> DatabaseQuestionResponse:
    """Answer natural-language questions by generating and executing safe SQL."""
    logger.info("[DBQA] ========== NEW DATABASE QUESTION REQUEST ==========")
    logger.info("[DBQA] Question: %s", request.question)

    try:
        user = AuthService.get_user_by_email(db, user_email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        conversation_id = request.conversation_id
        if not conversation_id:
            conversation = ConversationService.create_conversation(db, user.id, "Database Q&A")
            conversation_id = conversation.id

        sql_qa_service = get_sql_qa_service()
        database_url = (request.database_url or settings.DATABASE_URL or "").strip()
        if not database_url:
            raise ValueError("DATABASE_URL is not configured")

        result = sql_qa_service.answer_question(
            database_url=database_url,
            question=request.question,
        )

        if conversation_id:
            ConversationService.add_message(
                db,
                conversation_id,
                user.id,
                "user",
                request.question,
            )
            rows_json = json.dumps(result.rows, ensure_ascii=False)
            assistant_content = (
                f"[DB_SQL]\n{result.sql}\n[/DB_SQL]\n"
                f"[DB_ROWS_JSON]\n{rows_json}\n[/DB_ROWS_JSON]\n\n"
                f"{result.answer}"
            )
            ConversationService.add_message(
                db,
                conversation_id,
                user.id,
                "assistant",
                assistant_content,
            )

        return DatabaseQuestionResponse(
            user_message=request.question,
            assistant_response=result.answer,
            generated_sql=result.sql,
            result_rows=result.rows,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "database_query_validation_error", "message": str(exc)},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[DBQA] Error processing database question: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "database_query_error", "message": str(exc)},
        )


@router.post("/dataframe-question", response_model=DataframeQuestionResponse)
async def ask_dataframe_question(
    question: str = Form(...),
    file: Optional[UploadFile] = File(default=None),
    google_sheet_id_or_url: Optional[str] = Form(default=None),
    worksheet_name: Optional[str] = Form(default="Sheet1"),
    cell_range: Optional[str] = Form(default="A1:Z1000"),
    conversation_id: Optional[int] = Form(default=None),
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> DataframeQuestionResponse:
    """Answer natural-language questions over CSV/XLSX files or Google Sheets.
    
    Supports three modes:
    1. New file upload (with file attachment)
    2. Google Sheet reference (with sheet URL)
    3. Follow-up question on same file (reuses cached dataframe from conversation)
    """
    try:
        user = AuthService.get_user_by_email(db, user_email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        has_file = file is not None
        has_sheet = bool((google_sheet_id_or_url or "").strip())
        
        # Get cache service
        df_cache = get_dataframe_cache()
        cached_data = None
        
        # IMPORTANT: If a new file is being uploaded, clear the old cache for this conversation
        if has_file and conversation_id:
            df_cache.clear(conversation_id)
            logger.info("[DATAFRAME_QA] Cleared cache for conv_id=%s (new file upload)", conversation_id)
        
        # Only check cache if no new file or sheet is being uploaded
        if not has_file and not has_sheet and conversation_id:
            cached_data = df_cache.retrieve(conversation_id)
        
        # Validate that we have exactly one source (file, sheet, or cached)
        source_count = sum([has_file, has_sheet, cached_data is not None])
        if source_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Provide a CSV/XLSX file, google_sheet_id_or_url, "
                    "or ask a follow-up question in an existing conversation"
                ),
            )
        if source_count > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Provide exactly one source: either a CSV/XLSX file or google_sheet_id_or_url"
                ),
            )

        dataframe_service = get_dataframe_qa_service()
        
        # Load dataframe from appropriate source
        if has_file:
            file_bytes = await file.read()
            if not file_bytes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file is empty",
                )
            df = dataframe_service.load_dataframe_from_file(file_bytes, file.filename or "uploaded_file")
            source = f"file:{file.filename}"
            
            # Cache the dataframe for follow-up questions
            if conversation_id:
                df_cache.store(conversation_id, df, file.filename or "uploaded_file", source="file")
        elif has_sheet:
            df = dataframe_service.load_dataframe_from_google_sheet(
                sheet_id_or_url=google_sheet_id_or_url or "",
                worksheet_name=worksheet_name or "Sheet1",
                cell_range=cell_range or "A1:Z1000",
            )
            source = "google_sheet"
            
            # Cache the dataframe for follow-up questions
            if conversation_id:
                df_cache.store(conversation_id, df, google_sheet_id_or_url or "sheet", source="google_sheet")
        else:
            # Use cached dataframe from previous request
            df = cached_data.df
            source = f"cached:{cached_data.display_name}"
            logger.info(
                "[DATAFRAME_QA] Using cached dataframe for follow-up question in conv_id=%s",
                conversation_id
            )

        pandas_agent_service = get_pandas_agent_service()
        agent_result = pandas_agent_service.query(
            df=df,
            question=question,
            source=source,
        )

        if not agent_result.get("success"):
            raise ValueError(agent_result.get("error") or "Pandas agent failed to answer the question")

        conv_id = conversation_id
        if not conv_id:
            conversation = ConversationService.create_conversation(db, user.id, "CSV/Sheets Q&A")
            conv_id = conversation.id

        ConversationService.add_message(db, conv_id, user.id, "user", question)
        ConversationService.add_message(
            db,
            conv_id,
            user.id,
            "assistant",
            agent_result["answer"],
        )

        return DataframeQuestionResponse(
            user_message=question,
            assistant_response=agent_result["answer"],
            source=agent_result.get("source"),
            row_count=agent_result.get("row_count"),
            columns=agent_result.get("columns"),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "dataframe_query_validation_error", "message": str(exc)},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[DATAFRAME_QA] Error processing question: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "dataframe_query_error", "message": str(exc)},
        )


# ============ URL Analysis Endpoint ============

@router.post("/analyze-url", response_model=URLAnalysisResponse)
async def analyze_url(
    request: URLAnalysisRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> URLAnalysisResponse:
    """
    Analyze content from a URL or YouTube video.
    
    Args:
        request: URL analysis request with URL and optional message.
        user_email: Current authenticated user email.
        db: Database session.
        
    Returns:
        URLAnalysisResponse with assistant analysis.
    """
    logger.info("[URLAnalysis] ========== NEW URL ANALYSIS REQUEST ==========")
    logger.info("[URLAnalysis] URL: %s", request.url)
    logger.info("[URLAnalysis] User message: %s", request.user_message)
    logger.info("[URLAnalysis] conversation_id=%s", request.conversation_id)
    
    try:
        # Verify user exists
        user = AuthService.get_user_by_email(db, user_email)
        if not user:
            logger.warning(f"User not found: {user_email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        # Process URL/video and extract content
        logger.info(f"[URLAnalysis] Processing URL: {request.url}")
        url_result = URLService.process_url_or_video(request.url)
        logger.info(
            "[URLAnalysis] URLService result => success=%s source_type=%s error=%s metadata=%s",
            url_result.get("success"),
            url_result.get("source_type"),
            url_result.get("error"),
            url_result.get("metadata"),
        )

        # Create conversation if not provided
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation = ConversationService.create_conversation(db, user.id)
            conversation_id = conversation.id
            logger.info(f"[URLAnalysis] Created new conversation: {conversation_id}")

        # Special handling: Google Sheets URLs should be answered via dataframe agent.
        if url_result.get("success") and url_result.get("source_type") == "google_sheet":
            logger.info("[URLAnalysis][SHEET_QA] Routing request to pandas dataframe agent")

            # Extract user intent by removing the URL itself from the message.
            question = (request.user_message or "").replace(request.url, "").strip()
            used_default_overview_prompt = False
            if not question:
                used_default_overview_prompt = True
                question = (
                    "Analyze this dataset and provide a rich overview. "
                    "Describe: (1) what this data is about and how many rows/columns it has, "
                    "(2) the important columns in plain language (no technical dtype labels), "
                    "(3) notable highlights such as the highest values, distributions, or outliers, "
                    "(4) any interesting patterns or business insights you can derive. "
                    "Be specific with actual values from the data. "
                    "Do not output lines like 'ColumnName : str' or raw pandas dtype mappings."
                )

            dataframe_service = get_dataframe_qa_service()
            df = dataframe_service.load_dataframe_from_google_sheet(
                sheet_id_or_url=request.url,
                worksheet_name="Sheet1",
                cell_range="A1:Z1000",
            )

            # Cache dataframe for same-conversation follow-up prompts.
            df_cache = get_dataframe_cache()
            df_cache.store(conversation_id, df, request.url, source="google_sheet")
            logger.info(
                "[URLAnalysis][SHEET_QA] Cached dataframe conv_id=%s rows=%s cols=%s",
                conversation_id,
                len(df),
                len(df.columns),
            )

            pandas_agent_service = get_pandas_agent_service()
            agent_result = pandas_agent_service.query(
                df=df,
                question=question,
                source="google_sheet",
            )

            if not agent_result.get("success"):
                raise ValueError(agent_result.get("error") or "Pandas agent failed for Google Sheet")

            assistant_response = agent_result.get("answer", "")
            if used_default_overview_prompt and assistant_response:
                # Safety cleanup for URL-only auto-analyze: remove raw dtype list lines
                # such as "CustomerID : str" or "Amount : float64".
                assistant_response = re.sub(
                    r"(?im)^\s*[-*]?\s*`?([A-Za-z_][\w\s-]*)`?\s*:\s*(str|string|int|int64|float|float64|bool|boolean|object|datetime|datetime64(?:\[ns\])?)\s*$",
                    "",
                    assistant_response,
                )
                assistant_response = re.sub(r"\n{3,}", "\n\n", assistant_response).strip()

            logger.info(
                "[URLAnalysis][SHEET_QA] Answer generated len=%s rows=%s cols=%s",
                len(assistant_response),
                len(df),
                len(df.columns),
            )

            ConversationService.add_message(db, conversation_id, user.id, "user", request.user_message)
            ConversationService.add_message(db, conversation_id, user.id, "assistant", assistant_response)

            return URLAnalysisResponse(
                user_message=request.user_message,
                assistant_response=assistant_response,
                conversation_id=conversation_id,
            )
        
        # Prepare message content - handle both success and failure cases
        if url_result["success"] and url_result["content"]:
            # Content was successfully extracted
            source_type = url_result.get("source_type", "unknown")
            message_content = (
                "[SYSTEM INSTRUCTION]\n"
                "The URL content has already been extracted by the backend. "
                "You must analyze only the extracted content below and answer the user request. "
                "Do not say that you cannot access the URL.\n\n"
                f"[USER REQUEST]\n{request.user_message}\n\n"
                f"[EXTRACTED_URL_SOURCE:{source_type}]\n"
                f"{url_result['content']}"
            )
            logger.info(f"[URLAnalysis] ✅ Content extracted: {len(message_content)} chars")
        else:
            # No content available - send error message to LLM
            error_msg = url_result.get("error", "Unable to fetch content from this URL.")
            metadata_reason = url_result.get("metadata", {}).get("reason", "unknown")
            
            if metadata_reason == "no_captions":
                # YouTube video without captions - ask user for help
                message_content = f"{request.user_message}\n\n[SYSTEM NOTICE: URL Analysis Failed]\nURL: {request.url}\nReason: {error_msg}\n\nPlease provide the video summary, key points, or specific questions about it instead."
            else:
                # Other failures
                message_content = f"{request.user_message}\n\n[SYSTEM NOTICE: URL Analysis Failed]\nURL: {request.url}\nError: {error_msg}\n\nPlease try another URL or provide the content directly."
            
            logger.warning(f"[URLAnalysis] Content unavailable: {error_msg}")

        logger.info(
            "[URLAnalysis] message_content length=%s preview=%s",
            len(message_content),
            message_content[:300].replace("\n", "\\n"),
        )
        
        # Fetch previous conversations for context
        previous_conversations = ConversationService.get_previous_conversations(
            db,
            user.id,
            current_conversation_id=conversation_id,
            limit=5,
        )
        
        # Generate response
        chat_service = get_chat_service(db=db)
        assistant_response = chat_service.generate_response(
            user_message=message_content,
            user_email=user_email,
            conversation_id=conversation_id,
            user_id=user.id,
            previous_conversations=previous_conversations,
        )

        logger.info(
            "[URLAnalysis] assistant_response length=%s preview=%s",
            len(assistant_response or ""),
            (assistant_response or "")[:300].replace("\n", "\\n"),
        )
        
        logger.info(f"[URLAnalysis] ✅ Analysis complete")
        return URLAnalysisResponse(
            user_message=request.user_message,
            assistant_response=assistant_response,
            conversation_id=conversation_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[URLAnalysis] Error analyzing URL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "url_analysis_error", "message": str(e)},
        )
