import { useCallback, useState } from 'react';
import { apiClient } from '../lib/api';
import type { Message } from '../types/chat';

/**
 * Hook for managing chat messages and interactions
 */
export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      // Add user message to chat
      const userMessage: Message = {
        id: Date.now().toString(),
        content: content.trim(),
        sender: 'user',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setError(null);

      try {
        // Call API to get response
        const response = await apiClient.sendChatMessage(content);

        // Add assistant response to chat
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: response.assistant_response,
          sender: 'assistant',
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err) {
        let errorMessage = 'Failed to send message';
        
        if (err instanceof Error) {
          errorMessage = err.message;
          console.error('Chat error details:', err);
        } else {
          console.error('Unknown error:', err);
        }

        setError(errorMessage);
        
        // Remove the user message from chat on error
        setMessages((prev) => prev.slice(0, -1));
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
  };
}
