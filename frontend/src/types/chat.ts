/**
 * API response types from backend
 */

export interface ChatMessage {
  user_message: string;
  assistant_response: string;
}

export interface DatabaseQuestionResponse extends ChatMessage {
  generated_sql: string;
}

export interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
  imageUrl?: string;
  imagePrompt?: string;
  type?: 'text' | 'image';
  dbGeneratedSql?: string;
}

export interface ConversationMessage {
  id: number;
  sender: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
}

export interface ConversationSummary {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}
