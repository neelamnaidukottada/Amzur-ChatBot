/**
 * API response types from backend
 */

export interface ChatMessage {
  user_message: string;
  assistant_response: string;
  response?: string;
  content?: string;
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
  dbRows?: Record<string, unknown>[];
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

export interface ResearchDigestRequest {
  query: string;
  conversation_id?: number;
  batch_size?: number;
  max_rounds?: number;
  categories?: string[];
  date_from?: string;
  date_to?: string;
  min_relevance_score?: number;
  min_quality_score?: number;
}

export interface ResearchPaperDigest {
  title: string;
  paper_url: string;
  published?: string;
  authors: string[];
  relevance_score: number;
  quality_score: number;
  high_quality: boolean;
  problem_statement: string;
  key_contributions: string[];
  methodology: string;
  results: string;
  limitations: string;
  summary: string;
}

export interface ResearchKeywordCluster {
  cluster_label: string;
  keywords: string[];
  paper_count: number;
}

export interface ResearchDigestResult {
  digest_id?: number;
  conversation_id?: number;
  query: string;
  generated_at: string;
  decision: 'sufficient_evidence' | 'need_more_evidence';
  reason: string;
  rounds_completed: number;
  min_required_high_quality_papers: number;
  high_quality_papers_found: number;
  total_unique_papers_scanned: number;
  filters?: {
    categories?: string[];
    date_from?: string | null;
    date_to?: string | null;
    min_relevance_score?: number;
    min_quality_score?: number;
  };
  papers: ResearchPaperDigest[];
  keyword_clusters: ResearchKeywordCluster[];
  consolidated_research_digest: string;
  trends: string[];
  conflicting_ideas: string[];
  next_action: string;
  rendered_digest_text?: string;
  cached?: boolean;
}

export interface ResearchDigestHistoryItem {
  id: number;
  conversation_id: number;
  query: string;
  decision: string;
  high_quality_papers_found: number;
  total_unique_papers_scanned: number;
  created_at: string;
  rendered_digest_text?: string | null;
}

export interface ResearchDigestHistoryResponse {
  page: number;
  page_size: number;
  total: number;
  items: ResearchDigestHistoryItem[];
}

export interface ResearchStreamEvent {
  type: 'status' | 'paper_analysis' | 'final' | 'error';
  stage?: string;
  message?: string;
  data?: unknown;
}
