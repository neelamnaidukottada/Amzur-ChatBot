import { useState, useEffect } from 'react';
import { MessageList } from './MessageList';
import { InputBar } from './InputBar';
import { useAuthenticatedChat } from '../lib/useAuthenticatedChat';
import { apiClient } from '../lib/api';
import { formatDistanceToNow } from 'date-fns';

interface AttachedFile {
  file: File;
  name: string;
  type: string;
}

interface ConversationMeta {
  [key: number]: {
    isPinned?: boolean;
    isArchived?: boolean;
  };
}

export function ChatPage() {
  const {
    messages,
    conversations,
    currentConversation,
    isLoading,
    error,
    sendMessage,
    editMessage,
    regenerateMessage,
    addAnalyzedResponse,
    addDatabaseResponse,
    loadConversation,
    createNewConversation,
    deleteConversation,
    renameConversation,
    clearMessages,
    clearConversation,
    addImageMessage,
  } = useAuthenticatedChat();

  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameText, setRenameText] = useState('');
  const [isDraftMode, setIsDraftMode] = useState(false); // Track if current chat is a draft (not yet saved)
  const [contextMenuConvId, setContextMenuConvId] = useState<number | null>(null);
  
  // Load pin/archive states from localStorage on mount
  const [conversationMeta, setConversationMeta] = useState<ConversationMeta>(() => {
    try {
      const saved = localStorage.getItem('conversationMeta');
      return saved ? JSON.parse(saved) : {};
    } catch (e) {
      console.error('Failed to load conversationMeta from localStorage:', e);
      return {};
    }
  });
  
  // Save conversationMeta to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem('conversationMeta', JSON.stringify(conversationMeta));
    } catch (e) {
      console.error('Failed to save conversationMeta to localStorage:', e);
    }
  }, [conversationMeta]);

  const handleLogout = () => {
    apiClient.logout();
    window.location.href = '/login';
  };

  const handleNewChat = async () => {
    // If already in draft mode with no messages, just reuse the same draft
    if (isDraftMode && messages.length === 0) {
      console.log(`[ChatPage] Already in draft mode, reusing existing draft`);
      return;
    }
    
    // Otherwise, enter new draft mode
    console.log('[ChatPage] Starting new draft chat');
    setIsDraftMode(true);
    clearMessages();
    clearConversation(); // Clear currentConversation to show blank chat
  };

  const handleSelectConversation = async (conversationId: number) => {
    setRenamingId(null);
    await loadConversation(conversationId);
  };

  const handleSaveRename = async (e: React.MouseEvent, conversationId: number) => {
    e.stopPropagation();
    if (renameText.trim()) {
      await renameConversation(conversationId, renameText);
    }
    setRenamingId(null);
  };

  const handleCancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setRenamingId(null);
  };

  const handleImageGenerated = (imageUrl: string, prompt: string) => {
    addImageMessage(imageUrl, prompt);
  };

  const handleEditMessage = (messageId: string, newContent: string) => {
    editMessage(messageId, newContent);
  };

  const handleRegenerateMessage = (messageId: string) => {
    regenerateMessage(messageId);
  };

  const handleSendMessageWithFiles = async (message: string, files?: AttachedFile[]) => {
    console.log('[ChatPage] Sending message with files:', { message, filesCount: files?.length, isDraftMode });
    
    let conversationIdToUse: number | undefined = currentConversation?.id;
    
    // If in draft mode, create the conversation first
    if (isDraftMode) {
      console.log(`[ChatPage] Creating new conversation from draft mode`);
      const newConversation = await createNewConversation();
      
      if (newConversation?.id) {
        console.log(`[ChatPage] New conversation created: ${newConversation.id}`);
        conversationIdToUse = newConversation.id;
        // Exit draft mode - conversation will appear in Recents
        setIsDraftMode(false);
      } else {
        console.error('[ChatPage] Failed to create new conversation');
        return;
      }
    }

    // If no conversation is active (fresh page or cleared state), create one automatically.
    if (!conversationIdToUse) {
      console.log('[ChatPage] No active conversation, creating one before send');
      const newConversation = await createNewConversation();
      if (newConversation?.id) {
        conversationIdToUse = newConversation.id;
      } else {
        console.error('[ChatPage] Failed to auto-create conversation');
        return;
      }
    }
    
    // Send the message with the conversation ID
    // Pass the conversation ID directly to avoid timing issues with state updates
    if (conversationIdToUse) {
      await sendMessage(message, files, conversationIdToUse);
    } else {
      console.error('[ChatPage] No conversation available to send message');
    }
  };

  const handleUrlAnalyzed = (userMessage: string, assistantResponse: string, conversationId?: number) => {
    console.log('[ChatPage] Adding URL analysis response to chat, conversationId:', conversationId);
    addAnalyzedResponse(userMessage, assistantResponse);
    // If a conversationId came back and we don't have a current conversation, load it so
    // follow-up messages stay in the same thread.
    if (conversationId && !currentConversation?.id) {
      loadConversation(conversationId);
    }
  };

  const handleDatabaseAnswered = (
    userMessage: string,
    assistantResponse: string,
    generatedSql?: string
  ) => {
    addDatabaseResponse(userMessage, assistantResponse, generatedSql);
  };

  /**
   * Guarantees a conversation exists before InputBar makes an API-level call
   * (URL analyze, DB question). Creates one if in draft mode or no conversation
   * is active, then exits draft mode so follow-up messages land in the same thread.
   */
  const handleEnsureConversation = async (): Promise<number | undefined> => {
    if (currentConversation?.id) return currentConversation.id;
    console.log('[ChatPage] handleEnsureConversation: creating new conversation');
    const newConversation = await createNewConversation();
    if (newConversation?.id) {
      setIsDraftMode(false);
      return newConversation.id;
    }
    return undefined;
  };

  // Context Menu Handlers for Conversations
  const handleShareConversation = (convId: number) => {
    const shareLink = `${window.location.origin}?chat=${convId}`;
    navigator.clipboard.writeText(shareLink);
    alert(`Link copied to clipboard! Share this: ${shareLink}`);
    setContextMenuConvId(null);
  };

  const handlePinConversation = (convId: number) => {
    setConversationMeta((prev) => ({
      ...prev,
      [convId]: {
        ...prev[convId],
        isPinned: !prev[convId]?.isPinned,
      },
    }));
    setContextMenuConvId(null);
  };

  const handleArchiveConversation = (convId: number) => {
    setConversationMeta((prev) => ({
      ...prev,
      [convId]: {
        ...prev[convId],
        isArchived: !prev[convId]?.isArchived,
      },
    }));
    setContextMenuConvId(null);
    console.log(`[ChatPage] Conversation ${convId} archived`);
  };

  const handleDeleteConvFromMenu = async (convId: number) => {
    if (confirm('Are you sure you want to delete this conversation?')) {
      await deleteConversation(convId);
      setContextMenuConvId(null);
      console.log(`[ChatPage] Conversation ${convId} deleted`);
    }
  };

  return (
    <div className="flex h-screen bg-white">
      {/* Sidebar */}
      <div className="w-64 bg-gray-950 text-white flex flex-col border-r border-gray-700">
        {/* Sidebar Logo/Header */}
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-2xl">🤖</span>
            <div>
              <h1 className="font-bold text-lg">Amzur Bot</h1>
              <p className="text-xs text-gray-400">AI Assistant</p>
            </div>
          </div>
          <button
            onClick={handleNewChat}
            className="w-full bg-gradient-to-r from-green-600 to-green-700 hover:from-green-500 hover:to-green-600 px-4 py-2 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2"
          >
            <span className="text-lg">+</span> New Chat
          </button>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <div className="p-4 text-gray-400 text-sm">
              No conversations yet. Start a new chat!
            </div>
          ) : (
            <div className="space-y-1 p-2">
              {/* RECENTS SECTION - All conversations sorted by recent */}
              {conversations.length > 0 && (
                <div className="mb-4">
                  <div className="text-xs font-semibold text-gray-400 uppercase px-2 py-2 mb-2">
                    💬 Recents
                  </div>
                  <div className="space-y-1">
                    {/* Pinned Conversations First */}
                    {[...conversations]
                      .filter((conv) => conversationMeta[conv.id]?.isPinned && !conversationMeta[conv.id]?.isArchived)
                      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
                      .map((conv) => (
                        <div key={conv.id} className="bg-yellow-50 rounded-lg">
                          <div
                            onClick={() => handleSelectConversation(conv.id)}
                            className={`p-2 rounded-lg cursor-pointer transition text-sm ${
                              currentConversation?.id === conv.id
                                ? 'bg-green-600 bg-opacity-30 border-l-2 border-green-500'
                                : 'hover:bg-yellow-100'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex-1 min-w-0">
                                <p className="font-medium truncate text-gray-200">
                                  📍 {conv.title}
                                </p>
                                <p className="text-xs text-gray-500">
                                  {formatDistanceToNow(new Date(conv.updated_at), {
                                    addSuffix: true,
                                  })}
                                </p>
                              </div>
                              <div className="flex gap-0.5 items-center opacity-0 hover:opacity-100 transition relative">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setContextMenuConvId(contextMenuConvId === conv.id ? null : conv.id);
                                  }}
                                  className="text-gray-400 hover:text-gray-200 transition text-xs px-1"
                                  title="Options"
                                >
                                  ⋮
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}

                    {/* Regular Conversations */}
                    {[...conversations]
                      .filter((conv) => !conversationMeta[conv.id]?.isPinned && !conversationMeta[conv.id]?.isArchived)
                      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
                      .map((conv) => (
                        <div
                          key={conv.id}
                          onClick={() => handleSelectConversation(conv.id)}
                          className={`p-2 rounded-lg cursor-pointer transition text-sm ${
                            currentConversation?.id === conv.id
                              ? 'bg-green-600 bg-opacity-30 border-l-2 border-green-500'
                              : 'hover:bg-gray-800'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              {renamingId === conv.id ? (
                                <input
                                  autoFocus
                                  type="text"
                                  value={renameText}
                                  onChange={(e) => setRenameText(e.target.value)}
                                  onClick={(e) => e.stopPropagation()}
                                  className="w-full px-2 py-1 rounded bg-gray-700 text-white text-xs border border-gray-600 focus:border-blue-500 outline-none"
                                  placeholder="Enter new title"
                                />
                              ) : (
                                <>
                                  <p className="font-medium truncate text-gray-200">
                                    {conv.title}
                                  </p>
                                  <p className="text-xs text-gray-500">
                                    {formatDistanceToNow(new Date(conv.updated_at), {
                                      addSuffix: true,
                                    })}
                                  </p>
                                </>
                              )}
                            </div>
                            <div className="flex gap-0.5 items-center opacity-0 hover:opacity-100 transition relative">
                              {renamingId === conv.id ? (
                                <>
                                  <button
                                    onClick={(e) => handleSaveRename(e, conv.id)}
                                    className="text-green-400 hover:text-green-300 transition text-xs"
                                    title="Save"
                                  >
                                    ✓
                                  </button>
                                  <button
                                    onClick={handleCancelRename}
                                    className="text-gray-400 hover:text-red-500 transition text-xs"
                                    title="Cancel"
                                  >
                                    ✕
                                  </button>
                                </>
                              ) : (
                                <>
                                  {/* Three-dot Menu Button */}
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setContextMenuConvId(contextMenuConvId === conv.id ? null : conv.id);
                                    }}
                                    className="text-gray-400 hover:text-gray-200 transition text-xs px-1"
                                    title="Options"
                                  >
                                    ⋮
                                  </button>

                                  {/* Context Menu */}
                                  {contextMenuConvId === conv.id && (
                                    <div className="absolute -right-2 top-6 bg-white border border-gray-200 rounded-lg shadow-xl z-50 min-w-max">
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          handleShareConversation(conv.id);
                                        }}
                                        className="w-full flex items-center gap-2 px-4 py-2 hover:bg-gray-100 text-gray-700 text-sm transition"
                                      >
                                        <span>📤</span> Share
                                      </button>

                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          setRenamingId(conv.id);
                                          setRenameText(conv.title);
                                          setContextMenuConvId(null);
                                        }}
                                        className="w-full flex items-center gap-2 px-4 py-2 hover:bg-gray-100 text-gray-700 text-sm transition"
                                      >
                                        <span>✏️</span> Rename
                                      </button>

                                      {/* Menu Options */}
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          handlePinConversation(conv.id);
                                        }}
                                        className="w-full flex items-center gap-2 px-4 py-2 hover:bg-gray-100 text-gray-700 text-sm transition"
                                      >
                                        <span>{conversationMeta[conv.id]?.isPinned ? '📍' : '📌'}</span>
                                        {conversationMeta[conv.id]?.isPinned ? 'Unpin' : 'Pin'} chat
                                      </button>

                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          handleArchiveConversation(conv.id);
                                        }}
                                        className="w-full flex items-center gap-2 px-4 py-2 hover:bg-gray-100 text-gray-700 text-sm transition"
                                      >
                                        <span>📦</span> {conversationMeta[conv.id]?.isArchived ? 'Unarchive' : 'Archive'}
                                      </button>

                                      <div className="border-t border-gray-200">
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            handleDeleteConvFromMenu(conv.id);
                                          }}
                                          className="w-full flex items-center gap-2 px-4 py-2 hover:bg-red-50 text-red-600 text-sm transition"
                                        >
                                          <span>🗑️</span> Delete
                                        </button>
                                      </div>
                                    </div>
                                  )}
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}

                    {/* Archived Conversations */}
                    {conversations.some((conv) => conversationMeta[conv.id]?.isArchived) && (
                      <>
                        <div className="px-2 py-2 mt-2 border-t border-gray-700">
                          <p className="text-xs font-semibold text-gray-500 uppercase">📦 Archived</p>
                        </div>
                        {[...conversations]
                          .filter((conv) => conversationMeta[conv.id]?.isArchived)
                          .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
                          .map((conv) => (
                            <div
                              key={conv.id}
                              onClick={() => handleSelectConversation(conv.id)}
                              className={`p-2 rounded-lg cursor-pointer transition text-sm opacity-60 ${
                                currentConversation?.id === conv.id
                                  ? 'bg-green-600 bg-opacity-30 border-l-2 border-green-500'
                                  : 'hover:bg-gray-800'
                              }`}
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex-1 min-w-0">
                                  <p className="font-medium truncate text-gray-400">
                                    {conv.title}
                                  </p>
                                  <p className="text-xs text-gray-600">
                                    {formatDistanceToNow(new Date(conv.updated_at), {
                                      addSuffix: true,
                                    })}
                                  </p>
                                </div>
                                <div className="flex gap-0.5 items-center opacity-0 hover:opacity-100 transition relative">
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setContextMenuConvId(contextMenuConvId === conv.id ? null : conv.id);
                                    }}
                                    className="text-gray-500 hover:text-gray-300 transition text-xs px-1"
                                    title="Options"
                                  >
                                    ⋮
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))}
                      </>
                    )}
                  </div>
                </div>
              )}

            </div>
          )}
        </div>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-gray-700">
          <button
            onClick={handleLogout}
            className="w-full bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded-lg text-sm font-medium transition"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-gradient-to-b from-blue-100 via-blue-50 to-blue-100">
        {/* Chat Content */}
        <div className="flex-1 overflow-y-auto flex flex-col">
          {messages.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center max-w-2xl w-full px-4">
                <h2 className="text-4xl font-light text-gray-800 mb-8">
                  What's on the agenda today?
                </h2>
                
                {/* Suggestion Cards */}
                <div className="grid grid-cols-2 gap-4 mb-8">
                  <button 
                    onClick={() => sendMessage("Create a summary")}
                    className="bg-gray-100 hover:bg-gray-200 p-4 rounded-lg text-left transition group"
                  >
                    <div className="text-2xl mb-2 group-hover:scale-110 transition">✨</div>
                    <p className="text-sm font-medium text-gray-800">Create something new</p>
                    <p className="text-xs text-gray-600 mt-1">Ideas, plans, creative content</p>
                  </button>
                  
                  <button 
                    onClick={() => sendMessage("Analyze this")}
                    className="bg-gray-100 hover:bg-gray-200 p-4 rounded-lg text-left transition group"
                  >
                    <div className="text-2xl mb-2 group-hover:scale-110 transition">🔍</div>
                    <p className="text-sm font-medium text-gray-800">Analyze</p>
                    <p className="text-xs text-gray-600 mt-1">Data, trends, patterns</p>
                  </button>
                  
                  <button 
                    onClick={() => sendMessage("Write or edit")}
                    className="bg-gray-100 hover:bg-gray-200 p-4 rounded-lg text-left transition group"
                  >
                    <div className="text-2xl mb-2 group-hover:scale-110 transition">✏️</div>
                    <p className="text-sm font-medium text-gray-800">Write or edit</p>
                    <p className="text-xs text-gray-600 mt-1">Improve your writing</p>
                  </button>
                  
                  <button 
                    onClick={() => sendMessage("Look something up")}
                    className="bg-gray-100 hover:bg-gray-200 p-4 rounded-lg text-left transition group"
                  >
                    <div className="text-2xl mb-2 group-hover:scale-110 transition">🔎</div>
                    <p className="text-sm font-medium text-gray-800">Look something up</p>
                    <p className="text-xs text-gray-600 mt-1">Search for information</p>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1">
              <MessageList 
                messages={messages} 
                isLoading={isLoading} 
                onEditMessage={handleEditMessage}
                onRegenerateMessage={handleRegenerateMessage}
              />
            </div>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="mx-4 mb-4 p-4 bg-red-100 text-red-700 rounded-lg border border-red-400">
            <p className="font-semibold mb-2">⚠️ Error:</p>
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Input area */}
        <div className="p-4 bg-gradient-to-b from-blue-50 to-blue-100">
          <div className="max-w-4xl mx-auto">
            <InputBar 
              onSendMessage={handleSendMessageWithFiles}
              onUrlAnalyzed={handleUrlAnalyzed}
              onDatabaseAnswered={handleDatabaseAnswered}
              isLoading={isLoading}
              onImageGenerated={handleImageGenerated}
              currentConversationId={currentConversation?.id}
              onEnsureConversation={handleEnsureConversation}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
