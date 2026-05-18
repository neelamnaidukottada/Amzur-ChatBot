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

interface Folder {
  id: string;
  name: string;
  isOpen: boolean;
  conversationIds: number[]; // Track conversations in this folder
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
  const [selectedFolderId, setSelectedFolderId] = useState<string>('1'); // Track selected folder
  const [isDraftMode, setIsDraftMode] = useState(false); // Track if current chat is a draft (not yet saved)
  const [draftFolderId, setDraftFolderId] = useState<string>('1'); // Track which folder the draft belongs to
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
  const [folders, setFolders] = useState<Folder[]>(() => {
    // Initialize folders with all existing conversations
    const defaultFolders: Folder[] = [
      { id: '1', name: 'Projects', isOpen: true, conversationIds: [] },
      { id: '2', name: 'Personal', isOpen: false, conversationIds: [] },
      { id: '3', name: 'Work', isOpen: false, conversationIds: [] },
    ];
    
    // If there are conversations, add them to Projects folder
    if (conversations && conversations.length > 0) {
      const convIds = conversations.map(c => c.id);
      defaultFolders[0].conversationIds = convIds;
    }
    
    return defaultFolders;
  });
  const [renamingFolder, setRenamingFolder] = useState<string | null>(null);
  const [renameFolderText, setRenameFolderText] = useState('');
  const [showNewFolderInput, setShowNewFolderInput] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');

  // Sync conversations to folders - REMOVED (conversations now show in Recents, not folders)
  // Only show conversations in folders if explicitly added to that folder


  const handleLogout = () => {
    apiClient.logout();
    window.location.href = '/login';
  };

  const handleNewChatInFolder = async (folderId: string) => {
    // If already in draft mode with no messages, just reuse the same draft
    if (isDraftMode && messages.length === 0) {
      console.log(`[ChatPage] Already in draft mode, reusing existing draft`);
      setSelectedFolderId(folderId);
      setDraftFolderId(folderId);
      return;
    }
    
    // Otherwise, enter new draft mode
    console.log(`[ChatPage] Starting new draft chat in folder ${folderId}`);
    setSelectedFolderId(folderId);
    setDraftFolderId(folderId);
    setIsDraftMode(true);
    clearMessages();
    clearConversation(); // Clear currentConversation to show blank chat
  };

  const handleSelectConversation = async (conversationId: number) => {
    setRenamingId(null);
    await loadConversation(conversationId);
  };

  const handleDeleteConversation = async (e: React.MouseEvent, conversationId: number, folderId: string) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this conversation?')) {
      await deleteConversation(conversationId);
      
      // Remove from folder
      setFolders((prev) =>
        prev.map((folder) =>
          folder.id === folderId
            ? { ...folder, conversationIds: folder.conversationIds.filter((id) => id !== conversationId) }
            : folder
        )
      );
    }
  };

  const handleStartRename = (e: React.MouseEvent, conv: any) => {
    e.stopPropagation();
    setRenamingId(conv.id);
    setRenameText(conv.title);
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
      console.log(`[ChatPage] Creating new conversation in draft folder ${draftFolderId}`);
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

  const handleMoveToProject = (convId: number, folderId: string) => {
    setFolders((prev) =>
      prev.map((folder) =>
        folder.id === folderId
          ? { ...folder, conversationIds: Array.from(new Set([...folder.conversationIds, convId])) }
          : folder
      )
    );
    setContextMenuConvId(null);
    console.log(`[ChatPage] Moved conversation ${convId} to folder ${folderId}`);
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

  // Folder management functions
  const toggleFolder = (folderId: string) => {
    setFolders((prev) =>
      prev.map((folder) =>
        folder.id === folderId ? { ...folder, isOpen: !folder.isOpen } : folder
      )
    );
  };

  const startRenameFolderFolder = (e: React.MouseEvent, folderId: string, folderName: string) => {
    e.stopPropagation();
    setRenamingFolder(folderId);
    setRenameFolderText(folderName);
  };

  const saveRenameFolder = (e: React.MouseEvent, folderId: string) => {
    e.stopPropagation();
    if (renameFolderText.trim()) {
      setFolders((prev) =>
        prev.map((folder) =>
          folder.id === folderId ? { ...folder, name: renameFolderText } : folder
        )
      );
    }
    setRenamingFolder(null);
  };

  const cancelRenameFolder = (e: React.MouseEvent) => {
    e.stopPropagation();
    setRenamingFolder(null);
  };

  const deleteFolder = (e: React.MouseEvent, folderId: string) => {
    e.stopPropagation();
    if (confirm('Delete this folder and all its conversations?')) {
      setFolders((prev) => prev.filter((folder) => folder.id !== folderId));
    }
  };

  const createNewFolder = () => {
    if (newFolderName.trim()) {
      const newFolder: Folder = {
        id: Date.now().toString(),
        name: newFolderName,
        isOpen: true,
        conversationIds: [],
      };
      setFolders((prev) => [...prev, newFolder]);
      setNewFolderName('');
      setShowNewFolderInput(false);
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
            onClick={() => handleNewChatInFolder(selectedFolderId)}
            className="w-full bg-gradient-to-r from-green-600 to-green-700 hover:from-green-500 hover:to-green-600 px-4 py-2 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2"
          >
            <span className="text-lg">+</span> New Chat
          </button>
        </div>

        {/* PINNED PROJECTS/FOLDERS SECTION - Always visible */}
        <div className="bg-gray-850 border-y border-gray-700 p-2">
          <div className="text-xs font-semibold text-gray-400 uppercase px-2 py-2 mb-2">
            📁 Projects
          </div>
          <div className="space-y-1">
            {folders.map((folder) => (
              <div key={folder.id} className="mb-1">
                {/* Folder Header */}
                <div className="flex items-center justify-between px-3 py-2 hover:bg-gray-800 rounded-lg transition group">
                  <div
                    className="flex items-center gap-2 flex-1 cursor-pointer"
                    onClick={() => toggleFolder(folder.id)}
                  >
                    <span className="text-lg">{folder.isOpen ? '📂' : '📁'}</span>
                    {renamingFolder === folder.id ? (
                      <input
                        autoFocus
                        type="text"
                        value={renameFolderText}
                        onChange={(e) => setRenameFolderText(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        className="px-2 py-1 rounded bg-gray-700 text-white text-sm border border-gray-600 focus:border-blue-500 outline-none flex-1"
                        placeholder="Folder name"
                      />
                    ) : (
                      <span 
                        className="text-sm font-medium text-gray-200 flex-1 truncate cursor-pointer hover:text-white"
                        onClick={() => {
                          setSelectedFolderId(folder.id);
                          if (!folder.isOpen) toggleFolder(folder.id);
                        }}
                      >
                        {folder.name}
                      </span>
                    )}
                  </div>
                  
                  {/* Folder Actions */}
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                    {renamingFolder === folder.id ? (
                      <>
                        <button
                          onClick={(e) => saveRenameFolder(e, folder.id)}
                          className="text-green-400 hover:text-green-300 text-xs"
                          title="Save"
                        >
                          ✓
                        </button>
                        <button
                          onClick={cancelRenameFolder}
                          className="text-gray-400 hover:text-red-500 text-xs"
                          title="Cancel"
                        >
                          ✕
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleNewChatInFolder(folder.id);
                          }}
                          className="text-gray-400 hover:text-green-400 text-xs"
                          title="New chat in this folder"
                        >
                          +
                        </button>
                        <button
                          onClick={(e) => startRenameFolderFolder(e, folder.id, folder.name)}
                          className="text-gray-400 hover:text-yellow-500 text-xs"
                          title="Rename"
                        >
                          ✎
                        </button>
                        <button
                          onClick={(e) => deleteFolder(e, folder.id)}
                          className="text-gray-400 hover:text-red-500 text-xs"
                          title="Delete"
                        >
                          ✕
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* New Folder Button - In pinned section */}
          <div className="mt-3 px-2">
            {showNewFolderInput ? (
              <div className="flex gap-2">
                <input
                  autoFocus
                  type="text"
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && createNewFolder()}
                  placeholder="New folder name"
                  className="flex-1 px-2 py-1 rounded bg-gray-700 text-white text-sm border border-gray-600 focus:border-blue-500 outline-none"
                />
                <button
                  onClick={createNewFolder}
                  className="text-green-400 hover:text-green-300 transition text-xs"
                >
                  ✓
                </button>
                <button
                  onClick={() => {
                    setShowNewFolderInput(false);
                    setNewFolderName('');
                  }}
                  className="text-gray-400 hover:text-red-500 transition text-xs"
                >
                  ✕
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowNewFolderInput(true)}
                className="w-full flex items-center justify-center gap-2 px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300 hover:text-white text-xs font-medium transition"
              >
                <span>+</span> New Folder
              </button>
            )}
          </div>
        </div>

        {/* Folders & Conversations List */}
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 && folders.length === 0 ? (
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

                                      {/* Move to Project Submenu */}
                                      <div className="border-t border-gray-200">
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation();
                                          }}
                                          className="w-full flex items-center gap-2 px-4 py-2 hover:bg-gray-100 text-gray-700 text-sm transition justify-between"
                                        >
                                          <span>📁 Move to project</span>
                                          <span>→</span>
                                        </button>
                                        <div className="bg-gray-50 py-1">
                                          {folders.map((folder) => (
                                            <button
                                              key={folder.id}
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                handleMoveToProject(conv.id, folder.id);
                                              }}
                                              className="w-full text-left px-6 py-1.5 hover:bg-gray-100 text-gray-700 text-xs transition"
                                            >
                                              {folder.name}
                                            </button>
                                          ))}
                                        </div>
                                      </div>

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
      <div className="flex-1 flex flex-col bg-white">
        {/* Chat Content */}
        <div className="flex-1 overflow-y-auto flex flex-col">
          {!currentConversation || messages.length === 0 ? (
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
        <div className="p-4 bg-white">
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
