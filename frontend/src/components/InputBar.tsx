import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../lib/api';

interface AttachedFile {
  file: File;
  name: string;
  type: string;
}

interface InputBarProps {
  onSendMessage: (message: string, files?: AttachedFile[]) => void;
  onUrlAnalyzed?: (userMessage: string, assistantResponse: string, conversationId?: number) => void;
  onDatabaseAnswered?: (userMessage: string, assistantResponse: string, generatedSql?: string) => void;
  isLoading: boolean;
  onImageGenerated?: (imageUrl: string, prompt: string) => void;
  currentConversationId?: number;
  /** Called before an API-level operation (URL analyze, DB question) to ensure a conversation exists.
   *  Creates one if needed. Returns the conversation ID to use. */
  onEnsureConversation?: () => Promise<number | undefined>;
}

type ChatMode = 'general' | 'database' | 'image';

export function InputBar({
  onSendMessage,
  onUrlAnalyzed,
  onDatabaseAnswered,
  isLoading,
  onImageGenerated,
  currentConversationId,
  onEnsureConversation,
}: InputBarProps) {
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [generatingImage, setGeneratingImage] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [recordingTime, setRecordingTime] = useState(0);
  const [detectedUrl, setDetectedUrl] = useState<string | null>(null);
  const [analyzingUrl, setAnalyzingUrl] = useState(false);
  const [chatMode, setChatMode] = useState<ChatMode>('general');
  const menuRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingIntervalRef = useRef<any>(null);

  // URL detection regex
  const urlRegex = /(https?:\/\/[^\s]+)/g;

  // Image generation intent detection
  const imageGenRegex = /^(generate|create|draw|make|render|paint|design|produce)\s+(an?\s+)?(image|picture|photo|illustration|artwork|drawing|painting|art|visual|graphic)\b/i;
  const dbQuestionRegex = /^\/db\s+(.+?)\s*\|\s*(.+)$/is;

  // Detect URLs in input
  const detectUrlsInInput = (text: string) => {
    const urls = text.match(urlRegex);
    if (urls && urls.length > 0) {
      setDetectedUrl(urls[0]);
    } else {
      setDetectedUrl(null);
    }
  };

  // Initialize Speech Recognition with fallback
  useEffect(() => {
    const SpeechRecognition = (window as any).webkitSpeechRecognition || 
                             (window as any).SpeechRecognition || 
                             (window as any).mozSpeechRecognition;
    
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onstart = () => {
        setIsRecording(true);
      };

      recognitionRef.current.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current.onresult = (event: any) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        if (transcript.trim()) {
          setInput((prev) => prev + (prev ? ' ' : '') + transcript);
        }
      };

      recognitionRef.current.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
      };
    }

    return () => {
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
      }
    };
  }, []);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
      }
    };

    if (showMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showMenu]);

  // Handle clipboard paste for images
  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      
      // Check if the pasted item is an image
      if (item.kind === 'file' && item.type.startsWith('image/')) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) {
          console.log('[InputBar] Image pasted from clipboard:', file.name, file.type);
          setAttachedFiles((prev) => [...prev, {
            file,
            name: `pasted-image-${Date.now()}.${item.type.split('/')[1]}`,
            type: item.type,
          }]);
        }
        return;
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if ((input.trim() || attachedFiles.length > 0) && !isLoading && !generatingImage && !analyzingUrl) {
      const dbMatch = input.trim().match(dbQuestionRegex);

      if (dbMatch) {
        const databaseUrl = dbMatch[1].trim();
        const question = dbMatch[2].trim();
        handleDatabaseQuestion(question, databaseUrl);
        return;
      }

      if (chatMode === 'database') {
        if (attachedFiles.length > 0) {
          alert('Database mode does not support file attachments. Switch to General Chat for files.');
          return;
        }

        handleDatabaseQuestion(input.trim());
        return;
      }

      if (chatMode === 'image') {
        if (attachedFiles.length > 0) {
          alert('Image mode does not support file attachments. Switch to General Chat for files.');
          return;
        }

        handleGenerateImage(input.trim());
        return;
      }

      // Check if message contains a URL - if so, analyze it instead of regular send
      if (detectedUrl && input.trim().includes(detectedUrl)) {
        console.log('[InputBar] URL detected in message - using analyze endpoint');
        handleAnalyzeUrl(detectedUrl);
      } else if (imageGenRegex.test(input.trim())) {
        console.log('[InputBar] Image generation intent detected - generating image');
        handleGenerateImage(input.trim());
      } else {
        onSendMessage(input, attachedFiles.length > 0 ? attachedFiles : undefined);
        setInput('');
        setAttachedFiles([]);
        setDetectedUrl(null);
      }
    }
  };

  const handleDatabaseQuestion = async (question: string, databaseUrl?: string) => {
    if (!question) return;

    setAnalyzingUrl(true);
    try {
      // Ensure a conversation exists before querying (important in new-chat / draft mode)
      let convId = currentConversationId;
      if (onEnsureConversation) {
        convId = await onEnsureConversation();
      }
      const response = await apiClient.askDatabaseQuestion(
        question,
        databaseUrl,
        convId
      );

      if (onDatabaseAnswered) {
        onDatabaseAnswered(question, response.assistant_response, response.generated_sql);
      }

      setInput('');
      setDetectedUrl(null);
      setAttachedFiles([]);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to query database';
      alert(`Database query failed: ${errorMessage}`);
    } finally {
      setAnalyzingUrl(false);
    }
  };

  const handleAnalyzeUrl = async (url: string) => {
    if (!url || analyzingUrl || isLoading) return;

    setAnalyzingUrl(true);
    setShowMenu(false);
    try {
      // Ensure a conversation exists BEFORE calling the API so draft mode is
      // exited and currentConversation is set before the response arrives.
      let convId = currentConversationId;
      if (onEnsureConversation) {
        convId = await onEnsureConversation();
      }

      console.log('[InputBar] Analyzing URL:', url);
      const response = await apiClient.analyzeURL(
        url,
        input.trim() || 'Analyze this content for me',
        convId
      );
      console.log('[InputBar] URL analysis response:', response);
      
      // Use the new callback to handle the response without duplicate message
      if (onUrlAnalyzed) {
        const userMsg = input.trim() || 'Analyze this content';
        const assistantMsg = response.assistant_response || response.content || '';
        onUrlAnalyzed(userMsg, assistantMsg, (response as any).conversation_id ?? convId);
      }
      
      setInput('');
      setDetectedUrl(null);
    } catch (error) {
      console.error('[InputBar] URL analysis failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to analyze URL';
      alert(`URL analysis failed: ${errorMessage}`);
    } finally {
      setAnalyzingUrl(false);
    }
  };

  const handleVoiceInput = async () => {
    // Try Web Speech API first
    if (recognitionRef.current) {
      if (isRecording) {
        recognitionRef.current.stop();
        setIsRecording(false);
      } else {
        try {
          recognitionRef.current.start();
        } catch (error) {
          console.error('Error starting speech recognition:', error);
          fallbackAudioRecording();
        }
      }
      return;
    }

    // Fallback to audio recording if Web Speech API not available
    if (!isRecording && !mediaRecorderRef.current) {
      fallbackAudioRecording();
    } else {
      stopAudioRecording();
    }
  };

  const fallbackAudioRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstart = () => {
        setIsRecording(true);
        setRecordingTime(0);
        recordingIntervalRef.current = setInterval(() => {
          setRecordingTime((prev) => prev + 1);
        }, 1000);
      };

      mediaRecorder.onstop = () => {
        setIsRecording(false);
        if (recordingIntervalRef.current) {
          clearInterval(recordingIntervalRef.current);
        }
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
    } catch (error) {
      console.error('Microphone access denied:', error);
      alert('Microphone access denied. Please allow access to use voice input.');
    }
  };

  const stopAudioRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
      setInput((prev) => prev + (prev ? ' ' : '') + '[Audio recorded - 🎙️ Audio message]');
    }
  };

  const handleGenerateImage = async (text?: string) => {
    const prompt = text || input || 'a beautiful landscape';
    if (!prompt.trim() || generatingImage || isLoading) return;

    setGeneratingImage(true);
    setShowMenu(false);
    try {
      console.log('Requesting image generation with prompt:', prompt);
      const result = await apiClient.generateImage(prompt);
      console.log('Image generation response:', result);
      const imageUrl = result.url;
      const imagePrompt = result.revised_prompt || result.prompt || prompt;

      if (!imageUrl) {
        throw new Error('No image URL found in API response');
      }

      if (onImageGenerated) {
        onImageGenerated(imageUrl, imagePrompt);
      }
      setInput('');
    } catch (error) {
      console.error('Image generation failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate image';
      alert(`Image generation failed: ${errorMessage}`);
    } finally {
      setGeneratingImage(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.currentTarget.files;
    if (files) {
      Array.from(files).forEach((file) => {
        setAttachedFiles((prev) => [...prev, {
          file,
          name: file.name,
          type: file.type,
        }]);
      });
    }
    setShowMenu(false);
    // Reset input so the same file can be selected again
    e.currentTarget.value = '';
  };

  const removeAttachedFile = (index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleMenuOption = (option: string) => {
    setShowMenu(false);
    switch (option) {
      case 'image':
        handleGenerateImage();
        break;
      case 'research':
        onSendMessage('Perform deep research on the following topic: ' + (input || 'your topic'));
        setInput('');
        break;
      case 'websearch':
        onSendMessage('Search the web for information about: ' + (input || 'your query'));
        setInput('');
        break;
      case 'write':
        onSendMessage('Help me write or edit: ' + (input || 'your content'));
        setInput('');
        break;
      case 'thinking':
        onSendMessage('Think about this: ' + (input || 'your question'));
        setInput('');
        break;
    }
  };

  return (
    <div className="space-y-3">
      {/* Explicit mode selector to keep routing deterministic. */}
      <div className="flex items-center gap-2 px-2">
        <button
          type="button"
          onClick={() => {
            setChatMode('general');
            setShowMenu(false);
          }}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition ${
            chatMode === 'general'
              ? 'bg-gray-900 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          General Chat
        </button>
        <button
          type="button"
          onClick={() => {
            setChatMode('database');
            setShowMenu(false);
            setAttachedFiles([]);
          }}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition ${
            chatMode === 'database'
              ? 'bg-blue-700 text-white'
              : 'bg-blue-100 text-blue-800 hover:bg-blue-200'
          }`}
        >
          Database Chat
        </button>
        <button
          type="button"
          onClick={() => {
            setChatMode('image');
            setShowMenu(false);
            setAttachedFiles([]);
          }}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition ${
            chatMode === 'image'
              ? 'bg-emerald-700 text-white'
              : 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200'
          }`}
        >
          Image Generation
        </button>
        <button
          type="button"
          onClick={() => navigate('/research-digest-agent')}
          className="px-3 py-1.5 rounded-full text-sm font-medium transition bg-amber-100 text-amber-900 hover:bg-amber-200"
        >
          Research Digest Agent
        </button>
        <button
          type="button"
          onClick={() => navigate('/tictactoe')}
          className="px-3 py-1.5 rounded-full text-sm font-medium transition bg-purple-100 text-purple-900 hover:bg-purple-200"
        >
          🎮 Tic Tac Toe
        </button>
      </div>

      {/* Attached Files Display */}
      {attachedFiles.length > 0 && (
        <div className="flex flex-wrap gap-2 px-2">
          {attachedFiles.map((attached, index) => (
            <div key={index} className="relative">
              {attached.type.startsWith('image/') ? (
                // Image preview
                <div className="relative group">
                  <img
                    src={URL.createObjectURL(attached.file)}
                    alt={attached.name}
                    className="h-20 w-20 object-cover rounded-lg border border-blue-200"
                  />
                  <button
                    type="button"
                    onClick={() => removeAttachedFile(index)}
                    className="absolute -top-2 -right-2 bg-red-500 hover:bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold transition opacity-0 group-hover:opacity-100"
                  >
                    ✕
                  </button>
                  <p className="text-xs text-gray-600 mt-1 max-w-xs truncate">
                    {attached.name}
                  </p>
                </div>
              ) : attached.type.startsWith('video/') ? (
                // Video preview
                <div className="relative group">
                  <div className="h-20 w-20 bg-gray-800 rounded-lg border border-blue-200 flex items-center justify-center">
                    <span className="text-2xl">🎬</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeAttachedFile(index)}
                    className="absolute -top-2 -right-2 bg-red-500 hover:bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold transition opacity-0 group-hover:opacity-100"
                  >
                    ✕
                  </button>
                  <p className="text-xs text-gray-600 mt-1 max-w-xs truncate">
                    {attached.name}
                  </p>
                </div>
              ) : (
                // File indicator for docs, code, tables, etc.
                <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg group relative">
                  <span className="text-lg">
                    {attached.type.includes('spreadsheet') || attached.name.endsWith('.xlsx') || attached.name.endsWith('.csv') ? '📊' :
                     attached.type.includes('pdf') ? '📕' :
                     attached.type.includes('word') || attached.type.includes('document') ? '📄' :
                     attached.type.includes('text') || attached.name.endsWith('.md') ? '📝' :
                     attached.name.endsWith('.json') || attached.name.endsWith('.xml') || attached.name.endsWith('.yaml') ? '⚙️' :
                     attached.name.endsWith('.py') || attached.name.endsWith('.js') || attached.name.endsWith('.ts') ? '💻' :
                     attached.name.endsWith('.html') || attached.name.endsWith('.css') ? '🌐' :
                     '📎'}
                  </span>
                  <span className="text-sm text-gray-700 truncate max-w-xs">
                    {attached.name}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeAttachedFile(index)}
                    className="ml-2 text-gray-400 hover:text-red-500 transition opacity-0 group-hover:opacity-100"
                  >
                    ✕
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Input Area with Menu */}
      <form onSubmit={handleSubmit} className="bg-gray-100 hover:bg-gray-200 transition rounded-2xl shadow-md p-2 flex items-center gap-2 relative">
        {/* Menu Button with Dropdown */}
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setShowMenu(!showMenu)}
            disabled={isLoading || generatingImage || chatMode === 'database'}
            className="p-2.5 hover:bg-gray-300 rounded-full transition disabled:opacity-50 disabled:cursor-not-allowed text-gray-600 flex items-center justify-center"
            title="More options"
          >
            <span className="text-lg font-bold">+</span>
          </button>

          {/* Dropdown Menu */}
          {showMenu && (
            <div className="absolute bottom-full left-0 mb-3 bg-white border border-gray-200 rounded-xl shadow-lg p-2 min-w-max z-50">
              <button
                type="button"
                onClick={() => document.getElementById('file-input')?.click()}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-100 rounded-lg transition text-left text-gray-700 text-sm"
              >
                <span className="text-lg">📎</span>
                <span>Add photos & files</span>
              </button>

              <button
                type="button"
                onClick={() => handleMenuOption('image')}
                disabled={generatingImage}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-100 rounded-lg transition text-left text-gray-700 text-sm disabled:opacity-50"
              >
                <span className="text-lg">🎨</span>
                <span>Create image</span>
              </button>

              <button
                type="button"
                onClick={() => handleMenuOption('thinking')}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-100 rounded-lg transition text-left text-gray-700 text-sm"
              >
                <span className="text-lg">💭</span>
                <span>Thinking</span>
              </button>

              <button
                type="button"
                onClick={() => handleMenuOption('research')}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-100 rounded-lg transition text-left text-gray-700 text-sm"
              >
                <span className="text-lg">🔬</span>
                <span>Deep research</span>
              </button>

              <button
                type="button"
                onClick={() => handleMenuOption('websearch')}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-100 rounded-lg transition text-left text-gray-700 text-sm"
              >
                <span className="text-lg">🌐</span>
                <span>Web search</span>
              </button>

              <button
                type="button"
                onClick={() => handleMenuOption('write')}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-100 rounded-lg transition text-left text-gray-700 text-sm"
              >
                <span className="text-lg">✍️</span>
                <span>Write or edit</span>
              </button>
            </div>
          )}
        </div>

        {/* Hidden File Input */}
        <input
          id="file-input"
          type="file"
          onChange={handleFileUpload}
          className="hidden"
          disabled={isLoading || generatingImage || chatMode === 'database' || chatMode === 'image'}
          multiple
          accept="image/*,video/*,.pdf,.doc,.docx,.txt,.xlsx,.csv,.json,.py,.js,.ts,.tsx,.jsx,.cpp,.c,.html,.css,.sql,.md,.xml,.yaml,.yml,.mp4,.webm,.mov,.avi"
        />

        {/* Text Input */}
        <input
          type="text"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            detectUrlsInInput(e.target.value);
          }}
          onPaste={handlePaste}
          placeholder={
            generatingImage
              ? 'Generating image...'
              : attachedFiles.length > 0
                ? 'Add a prompt for your files...'
                : chatMode === 'database'
                  ? 'Ask a SQL-style question in natural language (uses configured DATABASE_URL)'
                  : chatMode === 'image'
                    ? 'Describe the image you want to generate'
                  : "Ask anything, paste a URL, or use /db <database-url> | <question>"
          }
          disabled={isLoading || generatingImage || analyzingUrl}
          className="flex-1 bg-transparent px-4 py-3 focus:outline-none disabled:opacity-50 text-gray-800 placeholder-gray-500"
        />

        {/* Action Buttons */}
        <div className="flex items-center gap-1 pr-2">
          {/* Analyze URL Button - Show when URL is detected */}
          {detectedUrl && chatMode === 'general' && (
            <button
              type="button"
              onClick={() => handleAnalyzeUrl(detectedUrl)}
              disabled={analyzingUrl || isLoading}
              className="px-3 py-2.5 rounded-full transition flex items-center justify-center gap-2 text-sm font-medium bg-blue-500 hover:bg-blue-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
              title="Analyze this URL/video"
            >
              <span className="text-lg">🔗</span>
              {!analyzingUrl && <span>Analyze</span>}
              {analyzingUrl && <span>Analyzing...</span>}
            </button>
          )}

          <button
            type="button"
            onClick={handleVoiceInput}
            disabled={isLoading || generatingImage || analyzingUrl || chatMode === 'database' || chatMode === 'image'}
            className={`px-3 py-2.5 rounded-full transition flex items-center justify-center gap-2 text-sm font-medium ${
              isRecording
                ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse'
                : 'bg-gray-200 hover:bg-gray-300 text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed'
            }`}
            title={isRecording ? 'Stop recording' : 'Use voice to input'}
          >
            <span className="text-lg">{isRecording ? '⏹️' : '🎙️'}</span>
            {!isRecording && <span>Use Voice</span>}
          </button>

          <button
            type="submit"
            disabled={isLoading || generatingImage || analyzingUrl || (!input.trim() && attachedFiles.length === 0)}
            className="p-2.5 hover:bg-gray-300 rounded-full transition disabled:opacity-50 disabled:cursor-not-allowed text-gray-600 flex items-center justify-center"
            title="Send"
          >
            {isLoading || generatingImage || analyzingUrl ? '⏳' : '➤'}
          </button>
        </div>
      </form>

      {isRecording && (
        <div className="text-center text-sm text-red-600 font-medium animate-pulse">
          🎤 Recording... {recordingTime > 0 && `(${recordingTime}s)`} Click the mic button to stop
        </div>
      )}
    </div>
  );
}
