import { useCallback, useState, useEffect } from 'react';
import { apiClient } from '../lib/api';
import type { Message, Conversation, ConversationSummary } from '../types/chat';

interface AttachedFile {
  file: File;
  name: string;
  type: string;
}

interface ParsedDbMessage {
  content: string;
  dbGeneratedSql?: string;
  dbRows?: Record<string, unknown>[];
}

function parseDbRows(jsonText: string): Record<string, unknown>[] | undefined {
  try {
    const parsed = JSON.parse(jsonText);
    if (Array.isArray(parsed)) {
      return parsed.filter((row) => row && typeof row === 'object') as Record<string, unknown>[];
    }
  } catch (error) {
    console.warn('[useAuthenticatedChat] Failed to parse DB rows JSON:', error);
  }
  return undefined;
}

function parseDatabaseMessage(content: string): ParsedDbMessage {
  const sqlMatch = content.match(/\[DB_SQL\]\s*([\s\S]*?)\s*\[\/DB_SQL\]/i);
  const rowsMatch = content.match(/\[DB_ROWS_JSON\]\s*([\s\S]*?)\s*\[\/DB_ROWS_JSON\]/i);

  const sql = sqlMatch?.[1]?.trim();
  const dbRows = rowsMatch?.[1] ? parseDbRows(rowsMatch[1].trim()) : undefined;

  if (sqlMatch || rowsMatch) {
    const cleaned = content
      .replace(/\[DB_SQL\][\s\S]*?\[\/DB_SQL\]/gi, '')
      .replace(/\[DB_ROWS_JSON\][\s\S]*?\[\/DB_ROWS_JSON\]/gi, '')
      .trim();
    return {
      content: cleaned,
      dbGeneratedSql: sql || undefined,
      dbRows,
    };
  }

  // Legacy fallback if SQL was embedded as plain text in old messages.
  const legacySqlMatch = content.match(/^\s*SQL Used:\s*(.*)$/im);
  if (legacySqlMatch) {
    const cleaned = content
      .replace(/(^|\n)\s*SQL Used:.*$/gim, '')
      .trim();
    return {
      content: cleaned,
      dbGeneratedSql: legacySqlMatch[1].trim() || undefined,
    };
  }

  console.log('[parseDatabaseMessage] Regular message, no DB markers:', {
    inputLength: content.length,
    hasSqlMarkers: !!sqlMatch,
    hasRowsMarkers: !!rowsMatch,
    hasLegacySql: !!legacySqlMatch,
  });

  return { content };
}

/**
 * Hook for managing authenticated chat with conversation history
 */
export function useAuthenticatedChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check if user is authenticated
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    setIsAuthenticated(!!token);
  }, []);

  // Load conversations on mount
  useEffect(() => {
    if (isAuthenticated) {
      loadConversations();
    }
  }, [isAuthenticated]);

  const loadConversations = useCallback(async () => {
    setError(null);
    try {
      const convos = await apiClient.getConversations();
      setConversations(convos);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations');
    }
  }, []);

  const loadConversation = useCallback(async (conversationId: number) => {
    console.log('[loadConversation] Loading conversation:', conversationId);
    setError(null);
    setIsLoading(true);
    try {
      console.log('[loadConversation] Fetching from API...');
      const convo = await apiClient.getConversation(conversationId);
      console.log('[loadConversation] Received conversation:', { id: convo.id, title: convo.title, messageCount: convo.messages?.length });
      setCurrentConversation(convo);
      
      // Convert to Message format for display
      const msgs: Message[] = convo.messages.map((msg) => {
        const isLegacyDbQuestion = msg.sender === 'user' && msg.content.startsWith('[DB QUESTION]');
        const normalizedUserContent = isLegacyDbQuestion
          ? msg.content.replace('[DB QUESTION]', '').trim()
          : msg.content;

        if (msg.sender === 'assistant') {
          const parsed = parseDatabaseMessage(msg.content);
          return {
            id: msg.id.toString(),
            content: parsed.content,
            sender: msg.sender,
            timestamp: new Date(msg.created_at),
            dbGeneratedSql: parsed.dbGeneratedSql,
            dbRows: parsed.dbRows,
          };
        }

        return {
          id: msg.id.toString(),
          content: normalizedUserContent,
          sender: msg.sender,
          timestamp: new Date(msg.created_at),
        };
      });
      
      console.log('[loadConversation] Loaded messages:', {
        count: msgs.length,
        lastMessage: msgs.length > 0 ? {
          sender: msgs[msgs.length - 1].sender,
          contentLength: msgs[msgs.length - 1].content.length,
          isEmpty: !msgs[msgs.length - 1].content,
        } : 'none',
      });

      setMessages(msgs);
      setError(null);
    } catch (err) {
      console.error('[loadConversation] Error loading conversation:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load conversation';
      setError(`Failed to load conversation: ${errorMessage}`);
      setMessages([]);
      setCurrentConversation(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createNewConversation = useCallback(async (title?: string) => {
    setError(null);
    try {
      const convo = await apiClient.createConversation(title);
      setCurrentConversation(convo);
      setMessages([]);
      
      // Reload conversations list
      await loadConversations();
      
      // Return the new conversation so caller can track it
      return convo;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create conversation');
      return null;
    }
  }, [loadConversations]);

  const sendMessage = useCallback(
    async (content: string, files?: AttachedFile[], conversationIdParam?: number) => {
      // Use provided conversation ID or fall back to currentConversation
      const conversationId = conversationIdParam || currentConversation?.id;
      
      if (!conversationId) {
        console.error('[useAuthenticatedChat] No conversation available - cannot send message');
        setError('No conversation available. Please create a new chat first.');
        return;
      }
      
      if ((!content.trim() && (!files || files.length === 0))) return;

      // Prepare user message content with file attachments
      let displayContent = content.trim();
      let imageUrl: string | undefined;
      
      if (files && files.length > 0) {
        const fileNames = files.map((f) => f.name).join(', ');
        displayContent = displayContent
          ? `${displayContent}\n\n📎 Files: ${fileNames}`
          : `📎 Files: ${fileNames}`;
        
        // If first file is an image, create preview URL
        if (files[0].type.startsWith('image/')) {
          imageUrl = URL.createObjectURL(files[0].file);
        }
      }

      // Add user message to UI
      const userMessage: Message = {
        id: Date.now().toString(),
        content: displayContent,
        sender: 'user',
        timestamp: new Date(),
        imageUrl: imageUrl,
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setError(null);

      try {
        // Send to API
        let response;
        
        if (files && files.length > 0) {
          // Use FormData for file uploads
          const formData = new FormData();
          formData.append('user_message', content.trim() || 'Please analyze these files');
          
          // Append each file
          files.forEach((file, index) => {
            console.log(`[useAuthenticatedChat] Appending file ${index}:`, file.name, file.type);
            formData.append('files', file.file);
          });
          
          console.log('[useAuthenticatedChat] Sending FormData with', files.length, 'files');
          response = await apiClient.sendChatMessageWithFiles(
            formData,
            conversationId
          );
          console.log('[useAuthenticatedChat] Response received:', response);
        } else {
          response = await apiClient.sendChatMessage(
            content.trim(),
            conversationId
          );
          console.log('[useAuthenticatedChat] Chat response received:', {
            hasAssistantResponse: !!response.assistant_response,
            responseLength: response.assistant_response?.length || 0,
            responsePreview: response.assistant_response?.substring(0, 100),
            responseKeys: Object.keys(response),
            fullResponse: response,
          });
        }

        // Add assistant response immediately with fallback
        const responseContent = response.assistant_response || response.response || 'Response received';
        console.log('[useAuthenticatedChat] Creating assistant message:', {
          contentLength: responseContent.length,
          isEmpty: responseContent === 'Response received',
          contentIsNulOrUndefined: responseContent == null,
          contentPreview: responseContent.substring(0, 100),
        });

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: responseContent,
          sender: 'assistant',
          timestamp: new Date(),
        };

        console.log('[useAuthenticatedChat] About to setMessages with assistant message:', assistantMessage);

        setMessages((prev) => {
          const updated = [...prev, assistantMessage];
          console.log('[useAuthenticatedChat] Messages state callback executed, count:', updated.length);
          console.log('[useAuthenticatedChat] Last message in state:', {
            id: updated[updated.length - 1]?.id,
            sender: updated[updated.length - 1]?.sender,
            contentLength: updated[updated.length - 1]?.content.length,
          });
          return updated;
        });
        
        // Reload full conversation to sync with database
        if (currentConversation) {
          console.log('[useAuthenticatedChat] Reloading conversation from database...');
          try {
            await loadConversation(currentConversation.id);
            console.log('[useAuthenticatedChat] Conversation reloaded successfully');
          } catch (err) {
            console.error('[useAuthenticatedChat] Error reloading conversation:', err);
          }
        } else {
          console.warn('[useAuthenticatedChat] currentConversation is null, will fetch from loadConversations instead');
        }
        
        // Reload conversations to update last modified time
        console.log('[useAuthenticatedChat] Reloading conversations list...');
        await loadConversations();
      } catch (err) {
        console.error('[useAuthenticatedChat] Error:', err);
        const errorMsg = err instanceof Error ? err.message : 'Failed to send message';
        setError(errorMsg);
        // Remove the user message if API call failed
        setMessages((prev) => prev.slice(0, -1));
      } finally {
        setIsLoading(false);
      }
    },
    [currentConversation, loadConversations]
  );

  const deleteConversation = useCallback(
    async (conversationId: number) => {
      setError(null);
      try {
        await apiClient.deleteConversation(conversationId);
        
        // If deleted conversation is current, clear it
        if (currentConversation?.id === conversationId) {
          setCurrentConversation(null);
          setMessages([]);
        }
        
        // Reload conversations list
        await loadConversations();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete conversation');
      }
    },
    [currentConversation, loadConversations]
  );

  const renameConversation = useCallback(
    async (conversationId: number, newTitle: string) => {
      if (!newTitle.trim()) return;
      
      setError(null);
      try {
        const updated = await apiClient.updateConversation(conversationId, newTitle);
        
        // Update current conversation if it's the one being renamed
        if (currentConversation?.id === conversationId) {
          setCurrentConversation(updated);
        }
        
        // Reload conversations list
        await loadConversations();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to rename conversation');
      }
    },
    [currentConversation, loadConversations]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const clearConversation = useCallback(() => {
    setCurrentConversation(null);
    setMessages([]);
  }, []);

  const addImageMessage = useCallback((imageUrl: string, prompt: string) => {
    const safePrompt = (prompt || '').trim() || 'Generated image';

    const userMessage: Message = {
      id: `user-img-${Date.now()}`,
      content: safePrompt,
      sender: 'user',
      timestamp: new Date(),
    };
    const imageMessage: Message = {
      id: `img-${Date.now() + 1}`,
      content: safePrompt,
      sender: 'assistant',
      timestamp: new Date(),
      imageUrl,
      imagePrompt: safePrompt,
      type: 'image',
    };
    setMessages((prev) => [...prev, userMessage, imageMessage]);
  }, []);

  const editMessage = useCallback(
    async (messageId: string, newContent: string) => {
      if (!newContent.trim() || !currentConversation) return;

      // Find the message index
      const messageIndex = messages.findIndex((m) => m.id === messageId);
      if (messageIndex === -1) return;

      // Update the message and remove all messages after it
      setMessages((prev) => {
        const updated = [...prev];
        updated[messageIndex].content = newContent.trim();
        // Remove all messages after the edited one (old responses)
        return updated.slice(0, messageIndex + 1);
      });

      setIsLoading(true);
      setError(null);

      try {
        // Send the edited message to API
        const response = await apiClient.sendChatMessage(
          newContent.trim(),
          currentConversation.id
        );

        // Add new assistant response
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: response.assistant_response,
          sender: 'assistant',
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);

        // Reload conversations to update last modified time
        await loadConversations();
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to send message';
        setError(errorMsg);
      } finally {
        setIsLoading(false);
      }
    },
    [currentConversation, messages, loadConversations]
  );

  const regenerateMessage = useCallback(
    async (assistantMessageId: string) => {
      // Find the assistant message index
      const assistantMessageIndex = messages.findIndex((m) => m.id === assistantMessageId);
      if (assistantMessageIndex <= 0) return;

      // Find the previous user message
      let userMessageIndex = -1;
      for (let i = assistantMessageIndex - 1; i >= 0; i--) {
        if (messages[i].sender === 'user') {
          userMessageIndex = i;
          break;
        }
      }

      if (userMessageIndex === -1) return;

      // Remove just the old assistant message - keep everything up to and including the user message
      setMessages((prev) => prev.slice(0, assistantMessageIndex));

      setIsLoading(true);
      setError(null);

      try {
        // Get the user message content (without any file markers)
        const userContent = messages[userMessageIndex].content;

        // Send the same user message again to get a fresh response
        const response = await apiClient.sendChatMessage(
          userContent,
          currentConversation?.id
        );

        // Add new assistant response
        const assistantMessage: Message = {
          id: `${Date.now()}-regenerated`,
          content: response.assistant_response,
          sender: 'assistant',
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);

        // Reload conversations to update last modified time
        await loadConversations();
      } catch (err) {
        // Re-add the old assistant message if regeneration fails
        const oldMessage = messages[assistantMessageIndex];
        setMessages((prev) => [...prev, oldMessage]);
        
        const errorMsg = err instanceof Error ? err.message : 'Failed to regenerate message';
        setError(errorMsg);
      } finally {
        setIsLoading(false);
      }
    },
    [messages, currentConversation, loadConversations]
  );

  const addAnalyzedResponse = useCallback(
    (userMessage: string, assistantResponse: string) => {
      console.log('[useAuthenticatedChat] Adding analyzed response');
      
      setIsLoading(true);
      setError(null);

      try {
        const timestamp = new Date();

        // Add user message
        const userMsg: Message = {
          id: `${Date.now()}-user`,
          content: userMessage,
          sender: 'user',
          timestamp,
        };

        // Add assistant response
        const assistantMsg: Message = {
          id: `${Date.now()}-assistant`,
          content: assistantResponse,
          sender: 'assistant',
          timestamp,
        };

        // Update messages with both
        setMessages((prev) => [...prev, userMsg, assistantMsg]);
        console.log('[useAuthenticatedChat] ✅ Analyzed response added to chat');

        // Reload conversations to sync state
        loadConversations();
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to add analyzed response';
        setError(errorMsg);
        console.error('[useAuthenticatedChat] Error adding analyzed response:', err);
      } finally {
        setIsLoading(false);
      }
    },
    [loadConversations]
  );

  const addDatabaseResponse = useCallback(
    (
      userMessage: string,
      assistantResponse: string,
      generatedSql?: string,
      rows?: Record<string, unknown>[]
    ) => {
      setIsLoading(true);
      setError(null);

      try {
        const timestamp = new Date();

        const userMsg: Message = {
          id: `${Date.now()}-db-user`,
          content: userMessage,
          sender: 'user',
          timestamp,
        };

        const assistantMsg: Message = {
          id: `${Date.now()}-db-assistant`,
          content: assistantResponse,
          sender: 'assistant',
          timestamp,
          dbGeneratedSql: generatedSql,
          dbRows: rows,
        };

        setMessages((prev) => [...prev, userMsg, assistantMsg]);
        loadConversations();
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to add database response';
        setError(errorMsg);
      } finally {
        setIsLoading(false);
      }
    },
    [loadConversations]
  );

  return {
    messages,
    conversations,
    currentConversation,
    isLoading,
    error,
    isAuthenticated,
    sendMessage,
    editMessage,
    regenerateMessage,
    addAnalyzedResponse,
    addDatabaseResponse,
    loadConversations,
    loadConversation,
    createNewConversation,
    deleteConversation,
    renameConversation,
    clearMessages,
    clearConversation,
    addImageMessage,
  };
}
