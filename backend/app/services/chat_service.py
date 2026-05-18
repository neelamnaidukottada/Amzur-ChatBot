"""Chat service containing all business logic for conversation handling."""

from sqlalchemy.orm import Session
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage
import logging
import re
from typing import List, Optional
from io import BytesIO
import base64

from app.ai.llm import get_chat_llm, get_vision_llm
from app.services.conversation_service import ConversationService
from app.services.rag_service import get_rag_service
from app.services.image_context_manager import ImageContextManager

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling chat interactions with LLM."""

    def __init__(self, db: Session = None):
        """Initialize the chat service with LLM and chain."""
        self.llm = get_chat_llm()
        self.db = db
        self.conversation_history_context = ""

    def _build_system_prompt(self, conversation_history: str = "") -> str:
        """
        Build the system prompt with optional conversation history context.
        
        Args:
            conversation_history: Formatted string of previous conversation context.
            
        Returns:
            Complete system prompt.
        """
        base_prompt = (
            "You are a highly intelligent AI assistant. Your role is to:\n"
            "1. Answer questions accurately and thoroughly\n"
            "2. For math/science questions: Provide clear formulas using LaTeX notation (e.g., $formula$ for inline, $$formula$$ for block)\n"
            "3. For code questions: Provide working code examples with proper syntax highlighting\n"
            "4. For data analysis: When files are provided, analyze them directly and answer based on actual data\n"
            "5. Always be helpful, accurate, and thorough\n"
            "6. REMEMBER: When users ask about previous messages or topics in THIS CHAT, refer to the [CURRENT CONVERSATION] section below\n\n"
            "URL HANDLING RULES:\n"
            "- If extracted URL content is already present in the message context, analyze that content directly\n"
            "- If Google Sheet content is provided in the message context, treat it like tabular data and answer from it\n"
            "- Only suggest alternatives (CSV/XLSX upload or dataframe endpoint) when no extractable content is available\n"
            "- Avoid generic refusal messages when usable content is present\n\n"
            "FILE HANDLING RULES:\n"
            "- Files appear between markers: ===== FILE START: [filename] ===== and ===== FILE END: [filename] =====\n"
            "- ALWAYS read and analyze file content between these markers\n"
            "- NEVER ask the user to re-upload files - they're already provided\n"
            "- Directly answer questions using the file content\n"
            "- If a file is marked as error, inform the user about the specific error\n\n"
            "RAG CONTEXT RULES:\n"
            "- RAG context from uploaded PDFs is optional support context, not mandatory output\n"
            "- Use RAG context only when it is clearly relevant to the user's current prompt\n"
            "- If current prompt is unrelated, ignore RAG context and answer the prompt directly\n\n"
            "MATH/FORMULA RULES:\n"
            "- For formulas, always provide the mathematical expression clearly\n"
            "- Use proper notation: $E = mc^2$ for inline, $$\\\\frac{a}{b}$$ for block formulas\n"
            "- Explain what each variable means\n"
            "- Provide examples when helpful\n\n"
            "CONVERSATION HISTORY RULES:\n"
            "- You have access to the CURRENT conversation history below\n"
            "- Use it to answer questions like 'what was my first message' or 'what did you say earlier'\n"
            "- Never proactively list or suggest old topics from history unless the user explicitly asks for past topics/history\n"
            "- Reference previous messages accurately\n"
            "- Prioritize the user's latest intent; do not reuse old answer templates when the user asks a new kind of question\n"
            "- If the user says 'my topic' or 'this topic' without naming one, ask a short clarification instead of guessing from old history\n"
            "- For prompts like 'what is the above query' or 'brief theory', explain the prior query in plain language (2-5 concise lines)\n"
            "- Be direct and concise. If asked for a formula, provide it immediately."
        )
        
        if conversation_history:
            base_prompt += (
                "\n\n--- CONVERSATION HISTORY ---\n"
                "This is the conversation history for context. Use it only when the user asks about prior messages/topics:\n\n"
                f"{conversation_history}\n"
                "--- END CONVERSATION HISTORY ---\n"
                "Do not proactively enumerate old topics from this history."
            )
        
        return base_prompt

    def _wants_document_context(self, message: str) -> bool:
        """Return True when the user prompt likely refers to uploaded files/PDF context."""
        text = (message or "").strip().lower()
        if not text:
            return False

        if "===== file start:" in text or "===== rag context start =====" in text:
            return True

        direct_terms = [
            "pdf", "document", "file", "attachment", "uploaded", "report", "paper",
            "from the doc", "from the pdf", "from the file", "in the document",
            "according to the document", "based on the uploaded", "from the attachment",
        ]
        if any(term in text for term in direct_terms):
            return True

        follow_up_patterns = [
            r"\bsummarize\s+(it|this|that)\b",
            r"\bexplain\s+(it|this|that)\b",
            r"\bwhat\s+does\s+(it|this|that)\s+say\b",
            r"\bfrom\s+above\b",
            r"\bin\s+the\s+above\b",
        ]
        return any(re.search(pattern, text) for pattern in follow_up_patterns)

    def _wants_cross_conversation_history(self, message: str) -> bool:
        """Return True only when user explicitly asks to recall earlier chat history/topics."""
        text = (message or "").strip().lower()
        if not text:
            return False

        explicit_patterns = [
            r"\bprevious\s+(chat|conversation|topic|message|messages)\b",
            r"\bearlier\s+(chat|conversation|topic|message|messages)\b",
            r"\bwhat\s+did\s+i\s+ask\b",
            r"\bwhat\s+was\s+my\s+first\s+message\b",
            r"\bwe\s+discussed\b",
            r"\bfrom\s+our\s+last\s+conversation\b",
            r"\bchat\s+history\b",
            r"\bconversation\s+history\b",
            r"\brecap\b",
            r"\babove\s+query\b",
            r"\bprevious\s+query\b",
        ]
        return any(re.search(pattern, text) for pattern in explicit_patterns)

    def _format_conversation_history(self, conversations: List) -> str:
        """
        Format previous conversations into a readable context string.
        
        Args:
            conversations: List of Conversation objects (in reverse chronological order).
            
        Returns:
            Formatted conversation history string.
        """
        if not conversations:
            return ""
        
        formatted_parts = []
        
        for i, conversation in enumerate(conversations, 1):
            # Reverse to show chronological order within each conversation
            messages = sorted(conversation.messages, key=lambda m: m.created_at)
            
            formatted_parts.append(f"[Previous Conversation {i}: {conversation.title}]")
            for msg in messages:
                sender = "You" if msg.sender == "user" else "Assistant"
                # Truncate long messages to 200 chars in context
                content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                formatted_parts.append(f"{sender}: {content}")
            formatted_parts.append("")
        
        return "\n".join(formatted_parts)

    def generate_response(
        self,
        user_message: str,
        retrieval_query: Optional[str] = None,
        user_email: str = "anonymous@example.com",
        conversation_id: int = None,
        user_id: int = None,
        current_conversation = None,
        previous_conversations: Optional[List] = None,
    ) -> str:
        """
        Generate an AI response to a user message with optional previous conversation context.
        
        Uses vision LLM for images, text LLM for regular messages.
        
        Args:
            user_message: The user's input message (may include file content or image data).
            user_email: Email for usage tracking with LiteLLM.
            conversation_id: Conversation ID for storing message (optional).
            user_id: User ID for authorization (optional).
            current_conversation: Current conversation object (optional) - used to include current chat history.
            previous_conversations: List of previous conversation objects for context (optional).
            
        Returns:
            The AI-generated response.
        """
        try:
            logger.info(f"[ChatService] Generating response for user: {user_email}")
            logger.info(f"[ChatService] Message length: {len(user_message)} characters")
            
            # Check if message contains image data (for vision analysis)
            is_image_message = "[IMAGE ANALYSIS REQUEST]" in user_message
            
            # Check for follow-up questions about previous images
            is_followup_question = (
                not is_image_message and 
                conversation_id and 
                ImageContextManager.is_followup_question(user_message)
            )
            
            if is_followup_question:
                logger.info(f"[ChatService] 🔄 FOLLOW-UP QUESTION detected - checking for previous image context")
                previous_image = ImageContextManager.get_image_context(conversation_id)
                
                if previous_image:
                    logger.info(f"[ChatService] 🖼️ Found previous image in conversation - using it for follow-up")
                    # Build message with previous image included
                    message_with_image = ImageContextManager.build_followup_message_with_image(
                        user_question=user_message,
                        image_data=previous_image["image_data"],
                        filename=previous_image["filename"],
                    )
                    is_image_message = True
                    user_message = message_with_image
                else:
                    logger.info(f"[ChatService] ℹ️ Follow-up question but no previous image found")
            
            if is_image_message:
                logger.info(f"[ChatService] ✅ IMAGE detected in message - using Vision LLM")
                return self._handle_image_message(user_message, user_email, conversation_id, user_id)
            else:
                logger.info(f"[ChatService] ℹ️ Regular text message - using Text LLM")
                return self._handle_text_message(
                    user_message,
                    user_email,
                    conversation_id,
                    user_id,
                    current_conversation,
                    previous_conversations,
                    retrieval_query,
                )
            
        except Exception as e:
            logger.error(f"[ChatService] Error generating response: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to generate response: {str(e)}")
    
    def _handle_image_message(
        self,
        user_message: str,
        user_email: str,
        conversation_id: int,
        user_id: int,
    ) -> str:
        """Handle image analysis using gpt-4o vision via LiteLLM proxy."""
        try:
            logger.info("[ChatService] 🖼️ Processing image message for vision analysis")
            
            # Extract base64 image data from the [IMAGE ANALYSIS REQUEST] block
            start_marker = "[IMAGE ANALYSIS REQUEST]"
            end_marker = "[END IMAGE ANALYSIS REQUEST]"
            
            start = user_message.find(start_marker)
            end = user_message.find(end_marker)
            
            if start == -1 or end == -1:
                logger.warning("[ChatService] Could not find image markers")
                return self._handle_text_message(user_message, user_email, conversation_id, user_id, previous_conversations=None)
            
            image_block = user_message[start:end + len(end_marker)]
            logger.info(f"[ChatService] 🖼️ Extracted image block: {len(image_block)} chars")
            
            # Extract filename for context
            filename_search = image_block.find("image file:")
            if filename_search != -1:
                filename_end = image_block.find("\n", filename_search)
                filename = image_block[filename_search + 11:filename_end].strip()
            else:
                filename = "unknown"
            
            # Extract the data URL
            data_url_start = image_block.find("data:image/")
            data_url_end = image_block.find("\n\nProvide", data_url_start)
            if data_url_end == -1:
                data_url_end = image_block.find("[END IMAGE", data_url_start)
            
            data_url = image_block[data_url_start:data_url_end].strip()
            logger.info(f"[ChatService] 🖼️ Data URL length: {len(data_url)} chars")
            
            # Get the LLM
            llm = get_chat_llm()
            
            # Get user's specific question if included in the message
            question_marker = "USER QUESTION:"
            user_question = ""
            if question_marker in user_message:
                question_start = user_message.find(question_marker) + len(question_marker)
                question_end = user_message.find("\n", question_start)
                if question_end == -1:
                    question_end = user_message.find("[END IMAGE", question_start)
                user_question = user_message[question_start:question_end].strip()
                logger.info(f"[ChatService] 🖼️ User question extracted: {user_question}")
            
            # Detect if it's a yes/no question for smart response scaling
            question_lower = user_question.lower() if user_question else ""
            yes_no_patterns = [
                "is there", "are there", "is it", "are they", "is the", "are the",
                "does it", "do they", "does the", "do the",
                "can you count", "how many", "how much",
                "is there any", "are there any", "is there a", "are there a",
                "did you", "have you", "have they", "has the",
                "was there", "were there", "was it", "were they",
                "could there", "would there", "should there",
                "could it", "would it", "should it",
                "any sun", "any tree", "any person", "any object", "any text",
                "any color", "any people", "any animals", "any water", "any building",
                "can i see", "can you see", "do you see", "did you see",
                "count the",
            ]
            is_yes_no_question = any(pattern in question_lower for pattern in yes_no_patterns)
            
            # Import the analysis service for better prompts
            from app.services.image_analysis_service import get_image_analysis_service
            analysis_service = get_image_analysis_service()
            
            # Choose analysis depth based on question type
            if is_yes_no_question:
                # For yes/no questions, use concise answer approach
                analysis_prompt = (
                    "You are answering a specific question about the image. "
                    "Answer the question directly and concisely. "
                    "Provide only the essential information needed - just 1-2 sentences. "
                    "Do NOT provide detailed structured analysis. "
                    "Focus solely on answering what is being asked."
                )
                logger.info("[ChatService] 🖼️ YES/NO question detected - using CONCISE response approach")
            elif user_question:
                # Specific question - provide detailed targeted analysis
                if any(keyword in question_lower for keyword in ["compare", "similar", "different"]):
                    analysis_prompt = analysis_service.get_comparison_prompt()
                    logger.info("[ChatService] 🖼️ COMPARISON question detected")
                elif any(keyword in question_lower for keyword in ["story", "narrative", "meaning", "symbolism"]):
                    analysis_prompt = analysis_service.get_creative_prompt()
                    logger.info("[ChatService] 🖼️ CREATIVE question detected")
                elif any(keyword in question_lower for keyword in ["accessibility", "describe", "blind", "visually impaired"]):
                    analysis_prompt = analysis_service.get_accessibility_description()
                    logger.info("[ChatService] 🖼️ ACCESSIBILITY question detected")
                else:
                    # Default structured analysis + user's specific question
                    analysis_prompt = analysis_service.get_structured_analysis_prompt() + f"\n\nALSO ANSWER THIS SPECIFIC QUESTION: {user_question}"
                    logger.info("[ChatService] 🖼️ DETAILED question detected")
            else:
                # No specific question - provide comprehensive structured analysis
                analysis_prompt = analysis_service.get_structured_analysis_prompt()
                logger.info("[ChatService] 🖼️ NO QUESTION - providing full STRUCTURED analysis")
            
            logger.info(f"[ChatService] 🖼️ Using analysis prompt ({len(analysis_prompt)} chars)")
            
            # Build the complete prompt with question
            if user_question:
                complete_prompt = f"{analysis_prompt}\n\nQUESTION: {user_question}"
            else:
                complete_prompt = analysis_prompt
            
            # Use HumanMessage with image_url - gpt-4o/LiteLLM should understand this
            response = llm.invoke([
                HumanMessage(
                    content=[
                        {"type": "text", "text": complete_prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ]
                )
            ])
            
            logger.info(f"[ChatService] 🖼️ ✅ Response received: {len(response.content)} chars")
            
            # Store image context for follow-up questions
            if conversation_id:
                ImageContextManager.store_image_context(
                    conversation_id=conversation_id,
                    image_data=data_url,
                    filename=filename,
                    initial_analysis=response.content,
                )
                logger.info(f"[ChatService] 💾 Stored image context for conversation {conversation_id}")
            
            # Store in database
            if conversation_id and user_id and self.db:
                ConversationService.add_message(self.db, conversation_id, user_id, "user", f"[Uploaded image: {filename}]")
                ConversationService.add_message(self.db, conversation_id, user_id, "assistant", response.content)
            
            return response.content
            
        except Exception as e:
            logger.error(f"[ChatService] 🖼️ Error in image analysis: {str(e)}", exc_info=True)
            # Fallback to text message handling
            logger.info("[ChatService] 🖼️ Falling back to text message handling")
            return self._handle_text_message(user_message, user_email, conversation_id, user_id, previous_conversations=None)
    
    def _handle_text_message(
        self,
        user_message: str,
        user_email: str,
        conversation_id: int,
        user_id: int,
        current_conversation = None,
        previous_conversations: Optional[List] = None,
        retrieval_query: Optional[str] = None,
    ) -> str:
        """Handle regular text messages using Text LLM."""
        try:
            llm_input = user_message

            # Check for file content in message
            has_file_content = "===== FILE START:" in user_message or "===== FILE ERROR:" in user_message

            # Add retrieval context from ChromaDB for this user/conversation.
            if user_id and conversation_id and self._wants_document_context(retrieval_query or user_message):
                query = retrieval_query or user_message
                rag_context = get_rag_service().retrieve_context(
                    query=query,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    k=5,
                    min_relevance_score=0.35,
                    include_user_fallback=False,
                )
                if rag_context:
                    llm_input += (
                        "\n\n===== RAG CONTEXT START =====\n"
                        "The following context was retrieved from uploaded PDFs in ChromaDB. "
                        "Use it to answer accurately.\n\n"
                        f"{rag_context}\n"
                        "===== RAG CONTEXT END ====="
                    )
                    logger.info("[ChatService] 🔎 Added retrieved RAG context to LLM input")
                else:
                    logger.info("[ChatService] 🔎 RAG skipped: no relevant chunks for current prompt")
            elif user_id and conversation_id:
                logger.info("[ChatService] 🔎 RAG skipped: prompt does not request document context")

            if has_file_content:
                logger.info(f"[ChatService] ✅ FILE CONTENT detected in message")
                # Extract and log file information
                import re
                file_markers = re.findall(r'===== FILE (START|ERROR): (.*?) =====', user_message)
                for marker_type, filename in file_markers:
                    logger.info(f"[ChatService]   📎 File: {filename} ({marker_type})")
            
            # Format current and previous conversation context
            conversation_history = ""
            
            # ✨ NEW: Add CURRENT conversation messages to context
            if current_conversation and current_conversation.messages:
                logger.info(f"[ChatService] 📚 Adding current conversation history: {len(current_conversation.messages)} messages")
                current_messages = sorted(current_conversation.messages, key=lambda m: m.created_at)
                
                # Format current conversation for context
                current_context_parts = ["[CURRENT CONVERSATION]"]
                for msg in current_messages:
                    sender = "You" if msg.sender == "user" else "Assistant"
                    # Truncate long messages to 200 chars in context
                    content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                    current_context_parts.append(f"{sender}: {content}")
                
                conversation_history = "\n".join(current_context_parts) + "\n\n"
                logger.info(f"[ChatService] ✅ Current conversation context added: {len(conversation_history)} chars")
            
            # Add previous conversations only when explicitly requested by user intent.
            if previous_conversations and self._wants_cross_conversation_history(retrieval_query or user_message):
                logger.info(f"[ChatService] 📚 Processing {len(previous_conversations)} previous conversations for context")
                previous_context = self._format_conversation_history(previous_conversations)
                conversation_history += previous_context
            elif previous_conversations:
                logger.info("[ChatService] 📚 Skipping previous-conversation context for non-history prompt")
            
            # Build system prompt
            system_prompt = self._build_system_prompt(conversation_history)
            logger.info(f"[ChatService] 📋 System prompt built: {len(system_prompt)} characters")
            
            # Escape curly braces in system prompt to avoid LangChain template parsing errors
            system_prompt_escaped = system_prompt.replace("{", "{{").replace("}", "}}")
            
            # Log the message being sent (first 500 chars)
            message_preview = llm_input[:500] + "..." if len(llm_input) > 500 else llm_input
            logger.info(f"[ChatService] 📤 Sending to LLM - Message preview: {message_preview}")
            
            # Initialize chain with text LLM
            llm = get_chat_llm()
            logger.info(f"[ChatService] ℹ️ LLM initialized: {llm.model_name}, temp={llm.temperature}")
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt_escaped),
                ("human", "{input}"),
            ])
            
            # Use explicit string output parser
            output_parser = StrOutputParser()
            chain = prompt | llm | output_parser
            logger.info(f"[ChatService] ✅ Chain created successfully with StrOutputParser")
            
            # Invoke chain with error handling
            logger.info(f"[ChatService] ⚙️ Invoking LLM chain...")
            logger.info(f"[ChatService] LLM Input length: {len(llm_input)} chars")
            logger.info(f"[ChatService] First 300 chars of input: {llm_input[:300]}")
            
            try:
                response = chain.invoke(
                    {"input": llm_input},
                    config={"metadata": {"user_email": user_email}}
                )
                # Ensure response is a string
                if not isinstance(response, str):
                    logger.warning(f"[ChatService] ⚠️ Response is not string, converting from {type(response)}")
                    response = str(response)
                    
            except Exception as llm_error:
                logger.error(f"[ChatService] ❌ LLM invoke error: {str(llm_error)}", exc_info=True)
                raise
            
            # Debug logging
            logger.info(f"[ChatService] ✅ LLM response received")
            logger.info(f"[ChatService] Response type: {type(response)}")
            logger.info(f"[ChatService] Response length: {len(response)} characters")
            logger.info(f"[ChatService] Response is empty: {len(response) == 0}")
            
            if response and len(response) > 0:
                logger.info(f"[ChatService] 📄 Response preview (first 500 chars): {response[:500]}")
            else:
                logger.error(f"[ChatService] ❌ EMPTY/NULL RESPONSE FROM LLM!")
                logger.error(f"[ChatService] Input was {len(llm_input)} chars")
                logger.error(f"[ChatService] Input preview: {llm_input[:500]}")
                # Return a fallback error message
                response = "I apologize, but I'm having trouble generating a response right now. Please try again."
            
            # Store messages in database
            if conversation_id and user_id and self.db:
                ConversationService.add_message(self.db, conversation_id, user_id, "user", user_message)
                ConversationService.add_message(self.db, conversation_id, user_id, "assistant", response)
            
            return response
        
        except Exception as e:
            logger.error(f"[ChatService] Error in text message handling: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to handle text message: {str(e)}")
            
        except Exception as e:
            logger.error(f"[ChatService] ❌ Error in text message handling: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to generate response: {str(e)}")


# Singleton instance
_chat_service: ChatService | None = None


def get_chat_service(db: Session = None) -> ChatService:
    """Get or create the chat service instance."""
    return ChatService(db=db)
