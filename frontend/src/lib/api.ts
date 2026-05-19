import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  ChatMessage,
  Conversation,
  ConversationSummary,
  DatabaseQuestionResponse,
  ResearchDigestRequest,
  ResearchDigestResult,
  ResearchDigestHistoryResponse,
  ResearchStreamEvent,
} from '../types/chat';
import type {
  GameState,
  MoveResponse,
  NewGameResponse,
} from '../types/tictactoe';

const CHAT_API_BASE_URL = import.meta.env.VITE_CHAT_API_URL || 'http://127.0.0.1:8000';
const GAME_API_BASE_URL = import.meta.env.VITE_GAME_API_URL || CHAT_API_BASE_URL;

console.log('[API] Chat backend:', CHAT_API_BASE_URL);
console.log('[API] Game backend:', GAME_API_BASE_URL);

class ApiClient {
  private client: AxiosInstance;
  private gameClient: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: CHAT_API_BASE_URL,
      withCredentials: true,
      timeout: 30000,
    });

    this.gameClient = axios.create({
      baseURL: GAME_API_BASE_URL,
      withCredentials: true,
      timeout: 30000,
    });

    // Load token from localStorage
    this.token = localStorage.getItem('auth_token');

    // Request interceptor to add auth header
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });

    this.gameClient.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });

    // Response interceptor for game client with better error handling
    this.gameClient.interceptors.response.use(
      (response) => {
        console.log('[API] Game Response received:', response.status, response.config.url);
        return response;
      },
      (error: AxiosError) => {
        console.error('[API] Game Error Response:', {
          status: error.response?.status,
          url: error.config?.url,
          data: error.response?.data,
        });

        if (error.response) {
          console.error('[API] Game server error:', error.response.status, error.response.data);
        } else if (error.request) {
          console.error('[API] ❌ No response from game backend. Is backend running on ' + GAME_API_BASE_URL + '?');
          console.error('[API] Frontend URL:', window.location.href);
          console.error('[API] Expected backend:', GAME_API_BASE_URL);
        } else {
          console.error('[API] Game request error:', error.message);
        }
        return Promise.reject(error);
      }
    );

    // Response interceptor for better error handling
    this.client.interceptors.response.use(
      (response) => {
        console.log('[API] Response received:', response.status, response.config.url);
        return response;
      },
      (error: AxiosError) => {
        console.error('[API] Error Response:', {
          status: error.response?.status,
          url: error.config?.url,
          data: error.response?.data,
        });

        if (error.response?.status === 401) {
          // Clear token on 401 after a brief delay to allow components to handle the error
          console.warn('[API] 401 Unauthorized - Session may have expired');
          this.setToken(null);
          // Redirect after a brief delay to allow error message to display
          setTimeout(() => {
            window.location.href = '/login';
          }, 2000);
        }
        
        if (error.response) {
          console.error('[API] Server error:', error.response.status, error.response.data);
        } else if (error.request) {
          console.error('[API] No response from server. Is chat backend running on ' + CHAT_API_BASE_URL + '?');
        } else {
          console.error('[API] Request error:', error.message);
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * Set authentication token
   */
  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  }

  /**
   * Register a new user
   */
  async register(email: string, password: string, fullName: string) {
    try {
      const response = await this.client.post('/api/auth/register', {
        email,
        password,
        full_name: fullName,
      });
      this.setToken(response.data.access_token);
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        throw new Error(error.response?.data?.detail || 'Registration failed');
      }
      throw error;
    }
  }

  /**
   * Login user
   */
  async login(email: string, password: string) {
    try {
      const response = await this.client.post('/api/auth/login', {
        email,
        password,
      });
      this.setToken(response.data.access_token);
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        throw new Error(error.response?.data?.detail || 'Login failed');
      }
      throw error;
    }
  }

  /**
   * Logout user
   */
  logout() {
    this.setToken(null);
  }

  /**
   * Login with Google OAuth
   */
  async googleLogin(token: string) {
    try {
      const response = await this.client.post('/api/auth/google', {
        token,
      });
      this.setToken(response.data.access_token);
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        throw new Error(error.response?.data?.detail || 'Google login failed');
      }
      throw error;
    }
  }

  /**
   * Send a chat message and get AI response
   */
  async sendChatMessage(userMessage: string, conversationId?: number): Promise<ChatMessage> {
    try {
      console.log('[API] 📤 Sending message:', userMessage);
      const params = conversationId ? { conversation_id: conversationId } : {};
      const response = await this.client.post<ChatMessage>('/api/chat/message', {
        user_message: userMessage,
      }, { params });
      
      console.log('[API] ✅ Chat response received!');
      console.log('[API] Response object:', response.data);
      console.log('[API] Response keys:', Object.keys(response.data));
      console.log('[API] Status:', response.status);
      console.log('[API] Has assistant_response field:', !!response.data.assistant_response);
      console.log('[API] assistant_response type:', typeof response.data.assistant_response);
      console.log('[API] assistant_response length:', response.data.assistant_response?.length || 'UNDEFINED');
      console.log('[API] assistant_response value:', response.data.assistant_response);
      console.log('[API] Is assistant_response empty string:', response.data.assistant_response === '');
      console.log('[API] Is assistant_response null:', response.data.assistant_response === null);
      console.log('[API] Is assistant_response undefined:', response.data.assistant_response === undefined);
      
      if (response.data.assistant_response && response.data.assistant_response.length > 0) {
        console.log('[API] ✅ Content preview (first 200 chars):', response.data.assistant_response.substring(0, 200));
      } else {
        console.error('[API] ❌ ASSISTANT_RESPONSE IS EMPTY OR MISSING!');
      }
      
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        if (!error.response) {
          throw new Error(
            `Cannot connect to backend at ${CHAT_API_BASE_URL}. Make sure the chat backend is running.`
          );
        }
        throw new Error(error.response?.data?.detail?.message || 'Failed to get response from AI');
      }
      throw error;
    }
  }

  /**
   * Send a chat message with file attachments
   */
  async sendChatMessageWithFiles(formData: FormData, conversationId?: number): Promise<ChatMessage> {
    try {
      console.log('[API] Sending message with files');
      console.log('[API] FormData entries:', Array.from(formData.entries()));
      
      const params = conversationId ? { conversation_id: conversationId } : {};
      
      // Send FormData directly - axios will auto-detect and set proper multipart/form-data boundary
      const response = await this.client.post<ChatMessage>('/api/chat/message', formData, {
        params,
      });
      console.log('[API] Chat response with files received:', response.data);
      return response.data;
    } catch (error) {
      console.error('[API] Error sending files:', error);
      if (error instanceof AxiosError) {
        if (!error.response) {
          throw new Error(
            `Cannot connect to backend at ${CHAT_API_BASE_URL}. Make sure the chat backend is running.`
          );
        }
        console.error('[API] Server response error:', error.response?.data);
        throw new Error(error.response?.data?.detail?.message || error.response?.data?.detail || 'Failed to send files');
      }
      throw error;
    }
  }

  /**
   * Create a new conversation
   */
  async createConversation(title?: string): Promise<Conversation> {
    try {
      const response = await this.client.post<Conversation>('/api/chat/conversations', {
        title: title || 'New Chat',
      });
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        throw new Error(error.response?.data?.detail || 'Failed to create conversation');
      }
      throw error;
    }
  }

  /**
   * Get all conversations for current user
   */
  async getConversations(): Promise<ConversationSummary[]> {
    try {
      const response = await this.client.get<ConversationSummary[]>('/api/chat/conversations');
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        throw new Error(error.response?.data?.detail || 'Failed to load conversations');
      }
      throw error;
    }
  }

  /**
   * Get a specific conversation with messages
   */
  async getConversation(conversationId: number): Promise<Conversation> {
    try {
      const response = await this.client.get<Conversation>(`/api/chat/conversations/${conversationId}`);
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        throw new Error(error.response?.data?.detail || 'Failed to load conversation');
      }
      throw error;
    }
  }

  /**
   * Update a conversation (e.g., rename)
   */
  async updateConversation(conversationId: number, title: string): Promise<Conversation> {
    try {
      const response = await this.client.put<Conversation>(
        `/api/chat/conversations/${conversationId}`,
        { title }
      );
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        throw new Error(error.response?.data?.detail || 'Failed to update conversation');
      }
      throw error;
    }
  }

  /**
   * Delete a conversation
   */
  async deleteConversation(conversationId: number): Promise<void> {
    try {
      await this.client.delete(`/api/chat/conversations/${conversationId}`);
    } catch (error) {
      if (error instanceof AxiosError) {
        throw new Error(error.response?.data?.detail || 'Failed to delete conversation');
      }
      throw error;
    }
  }

  /**
   * Generate an image using DALL-E
   */
  async generateImage(prompt: string, size: string = '1024x1024'): Promise<{ url: string; revised_prompt: string; prompt?: string; model?: string; source?: string }> {
    try {
      console.log('[API] Generating image with prompt:', prompt);
      console.log('[API] Using Google Gemini 2.0 Flash');
      const response = await this.client.post('/api/chat/generate-image', {
        prompt,
        size,
      });

      const payload = response.data as {
        url?: string;
        revised_prompt?: string;
        prompt?: string;
        model?: string;
        source?: string;
        data?: Array<{ url?: string; b64_json?: string; revised_prompt?: string }>;
      };

      let normalizedUrl = payload.url;
      if (!normalizedUrl && payload.data?.[0]?.url) {
        normalizedUrl = payload.data[0].url;
      }
      if (!normalizedUrl && payload.data?.[0]?.b64_json) {
        normalizedUrl = `data:image/png;base64,${payload.data[0].b64_json}`;
      }

      // Normalize relative/backend URLs so <img> can resolve them from frontend origin.
      if (normalizedUrl && !normalizedUrl.startsWith('data:') && !normalizedUrl.startsWith('blob:')) {
        if (normalizedUrl.startsWith('/')) {
          normalizedUrl = `${CHAT_API_BASE_URL}${normalizedUrl}`;
        } else if (!/^https?:\/\//i.test(normalizedUrl)) {
          try {
            normalizedUrl = new URL(normalizedUrl, CHAT_API_BASE_URL).toString();
          } catch {
            // Keep original string if URL construction fails.
          }
        }
      }

      if (!normalizedUrl) {
        throw new Error('Image API returned success but no image URL was found in response payload');
      }

      const normalizedPrompt = payload.revised_prompt || payload.data?.[0]?.revised_prompt || payload.prompt || prompt;

      console.log('[API] ✅ Image generated successfully');
      console.log('[API] Model:', payload.model || 'gemini-2.0-flash');
      console.log('[API] Response:', payload);
      return {
        url: normalizedUrl,
        revised_prompt: normalizedPrompt,
        prompt: payload.prompt,
        model: payload.model,
        source: payload.source,
      };
    } catch (error) {
      if (error instanceof AxiosError) {
        console.error('[API] ❌ Image generation error:', error.response?.data);
        const errorMsg = error.response?.data?.detail?.message 
          || error.response?.data?.detail 
          || 'Failed to generate image';
        throw new Error(errorMsg);
      }
      throw error;
    }
  }

  /**
   * Analyze content from a URL or YouTube video
   */
  async analyzeURL(url: string, userMessage: string = 'Analyze this content', conversationId?: number): Promise<ChatMessage> {
    try {
      console.log('[API] Analyzing URL:', url);
      const params = conversationId ? { conversation_id: conversationId } : {};
      const response = await this.client.post<ChatMessage>('/api/chat/analyze-url', {
        url,
        user_message: userMessage,
        conversation_id: conversationId,
      }, { params });
      console.log('[API] URL analysis response received');
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        const errorMsg = error.response?.data?.detail || 'Failed to analyze URL';
        throw new Error(errorMsg);
      }
      throw error;
    }
  }

  /**
   * Ask a natural-language question against a SQL database.
   */
  async askDatabaseQuestion(
    question: string,
    databaseUrl?: string,
    conversationId?: number
  ): Promise<DatabaseQuestionResponse> {
    try {
      const response = await this.client.post<DatabaseQuestionResponse>('/api/chat/database-question', {
        database_url: databaseUrl,
        question,
        conversation_id: conversationId,
      });
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        const errorMsg = error.response?.data?.detail?.message
          || error.response?.data?.detail
          || 'Failed to run database question';
        throw new Error(errorMsg);
      }
      throw error;
    }
  }

  /**
   * Upload and analyze an image
   */
  async uploadImage(file: File): Promise<{ url: string; filename: string }> {
    try {
      // Convert file to data URL
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          const dataUrl = e.target?.result as string;
          resolve({
            url: dataUrl,
            filename: file.name,
          });
        };
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsDataURL(file);
      });
    } catch (error) {
      if (error instanceof AxiosError) {
        throw new Error(error.response?.data?.detail || 'Failed to upload image');
      }
      throw error;
    }
  }

  /**
   * Analyze an image with specified mode
   */
  async analyzeImage(formData: FormData, conversationId?: number): Promise<{ analysis: string }> {
    try {
      console.log('[API] Starting image analysis');
      
      // Extract data from formData
      const file = formData.get('file') as File;
      const analysisMode = formData.get('analysis_mode') as string;
      const question = formData.get('question') as string || '';
      
      if (!file) {
        throw new Error('No file provided');
      }

      // Convert file to data URL
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target?.result as string);
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsDataURL(file);
      });

      // Build the image analysis message with proper markers
      const modeHints = {
        structured: 'Provide a structured analysis with title, description, objects, colors, mood, and lighting.',
        detailed: 'Provide a technical analysis including composition, perspective, balance, and artistic merit.',
        creative: 'Provide a creative interpretation including narrative, symbolism, emotions, and artistic inspiration.',
        comparison: 'Compare this image with similar styles and provide alternative perspectives.',
        accessibility: 'Provide a detailed accessibility description suitable for visually impaired users.',
      };

      const modeHint = modeHints[analysisMode as keyof typeof modeHints] || modeHints.structured;
      
      let imageMessage = `[IMAGE ANALYSIS REQUEST]\nimage file: ${file.name}\n${dataUrl}\n\nAnalysis Mode: ${analysisMode}\n${modeHint}`;
      
      if (question && question.trim()) {
        imageMessage += `\n\nUSER QUESTION: ${question}`;
      }
      
      imageMessage += '\n[END IMAGE ANALYSIS REQUEST]';

      // Send to the regular message endpoint with the image markers
      const params = conversationId ? { conversation_id: conversationId } : {};
      const response = await this.client.post<ChatMessage>(
        '/api/chat/message',
        { user_message: imageMessage },
        { params }
      );

      console.log('[API] Image analysis completed successfully');
      return {
        analysis: response.data.assistant_response || 'Analysis completed',
      };
    } catch (error) {
      if (error instanceof AxiosError) {
        const errorMsg = error.response?.data?.detail?.message 
          || error.response?.data?.detail 
          || 'Failed to analyze image';
        throw new Error(errorMsg);
      }
      throw error;
    }
  }

  /**
   * Stream autonomous research digest events as NDJSON.
   */
  async streamResearchDigest(
    request: ResearchDigestRequest,
    onEvent: (event: ResearchStreamEvent) => void
  ): Promise<ResearchDigestResult> {
    const token = this.token || localStorage.getItem('auth_token');
    const response = await fetch(`${CHAT_API_BASE_URL}/api/research/digest/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(request),
      credentials: 'include',
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Research digest request failed (${response.status}): ${text}`);
    }

    if (!response.body) {
      throw new Error('Streaming is not supported by this browser response.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finalResult: ResearchDigestResult | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        try {
          const event = JSON.parse(trimmed) as ResearchStreamEvent;
          onEvent(event);
          if (event.type === 'final' && event.data) {
            finalResult = event.data as ResearchDigestResult;
          }
        } catch (error) {
          console.warn('[API] Failed to parse NDJSON event line:', error, trimmed);
        }
      }
    }

    if (!finalResult) {
      throw new Error('Stream completed without a final digest payload.');
    }

    return finalResult;
  }

  async getResearchDigestHistory(
    page: number = 1,
    pageSize: number = 10,
    conversationId?: number
  ): Promise<ResearchDigestHistoryResponse> {
    const params: Record<string, number> = {
      page,
      page_size: pageSize,
    };
    if (conversationId) {
      params.conversation_id = conversationId;
    }

    const response = await this.client.get<ResearchDigestHistoryResponse>('/api/research/digests', {
      params,
    });
    return response.data;
  }

  /**
   * Health check endpoint
   */
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get<{ status: string }>('/health');
    return response.data;
  }

  // ==================== TIC TAC TOE GAME ENDPOINTS ====================

  /**
   * Create a new Tic Tac Toe game
   */
  async createTicTacToeGame(): Promise<NewGameResponse> {
    try {
      console.log('[API] Creating new Tic Tac Toe game');
      const response = await this.gameClient.post<NewGameResponse>('/api/games/tictactoe/new');
      console.log('[API] Game created:', response.data.game_id);
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        const errorMsg = error.response?.data?.detail || 'Failed to create game';
        throw new Error(errorMsg);
      }
      throw error;
    }
  }

  /**
   * Get current game state
   */
  async getTicTacToeGameState(gameId: string): Promise<GameState> {
    try {
      const response = await this.gameClient.get<GameState>(`/api/games/tictactoe/${gameId}/state`);
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        const errorMsg = error.response?.data?.detail || 'Failed to get game state';
        throw new Error(errorMsg);
      }
      throw error;
    }
  }

  /**
   * Make a move in Tic Tac Toe
   * 
   * Backend validates:
   * - Move is 1-9 ✓
   * - Cell is empty ✓
   * - AI move is valid ✓
   */
  async makeMove(gameId: string, position: number): Promise<MoveResponse> {
    try {
      console.log(`[API] Making move at position ${position} in game ${gameId}`);
      const response = await this.gameClient.post<MoveResponse>(`/api/games/tictactoe/${gameId}/move`, {
        game_id: gameId,
        position,
      });
      console.log('[API] Move successful:', {
        human: response.data.human_move,
        ai: response.data.ai_move,
        status: response.data.status,
      });
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        const errorMsg = error.response?.data?.detail || 'Failed to make move';
        throw new Error(errorMsg);
      }
      throw error;
    }
  }

  /**
   * Reset the game
   */
  async resetTicTacToeGame(gameId: string): Promise<{ message: string; board: string[] }> {
    try {
      const response = await this.gameClient.post(`/api/games/tictactoe/${gameId}/reset`);
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        const errorMsg = error.response?.data?.detail || 'Failed to reset game';
        throw new Error(errorMsg);
      }
      throw error;
    }
  }

  /**
   * Delete a game
   */
  async deleteTicTacToeGame(gameId: string): Promise<{ message: string }> {
    try {
      const response = await this.gameClient.delete(`/api/games/tictactoe/${gameId}`);
      return response.data;
    } catch (error) {
      if (error instanceof AxiosError) {
        const errorMsg = error.response?.data?.detail || 'Failed to delete game';
        throw new Error(errorMsg);
      }
      throw error;
    }
  }
}

export const apiClient = new ApiClient();

// Export standalone functions for convenience
export const uploadImage = (file: File) => apiClient.uploadImage(file);
export const analyzeImage = (formData: FormData, conversationId?: number) => 
  apiClient.analyzeImage(formData, conversationId);
