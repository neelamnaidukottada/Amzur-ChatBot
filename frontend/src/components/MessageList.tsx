import { useState, useEffect, useRef } from 'react';
import type { Message } from '../types/chat';
import { MarkdownRenderer } from './MarkdownRenderer';
import { ErrorBoundary } from './ErrorBoundary';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import 'katex/dist/katex.min.css';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  onEditMessage?: (messageId: string, newContent: string) => void;
  onRegenerateMessage?: (messageId: string) => void;
}

// Image display component with lightbox support
const ImageDisplay = ({ src, alt, prompt }: { src: string; alt: string; prompt?: string }) => {
  const [showFullscreen, setShowFullscreen] = useState(false);
  
  return (
    <>
      <div className="my-2 rounded-lg overflow-hidden bg-white border border-gray-200">
        <img 
          src={src} 
          alt={alt}
          className="rounded-lg max-w-md w-full cursor-pointer hover:opacity-90 transition"
          onClick={() => setShowFullscreen(true)}
          loading="lazy"
        />
        {prompt && (
          <p className="text-sm p-2 opacity-75 bg-gray-50 border-t border-gray-200">
            <strong>Prompt:</strong> {prompt}
          </p>
        )}
      </div>
      
      {/* Fullscreen image modal */}
      {showFullscreen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={() => setShowFullscreen(false)}
        >
          <div className="relative max-w-4xl max-h-[90vh] flex items-center justify-center">
            <img 
              src={src} 
              alt={alt}
              className="max-w-full max-h-[90vh] rounded-lg"
              onClick={(e) => e.stopPropagation()}
            />
            <button
              onClick={() => setShowFullscreen(false)}
              className="absolute top-4 right-4 bg-white rounded-full p-2 hover:bg-gray-200 transition text-gray-700"
              title="Close"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </>
  );
};

// Component to embed videos from various sources
const VideoEmbed = ({ url }: { url: string }) => {
  // YouTube
  if (url.includes('youtube.com') || url.includes('youtu.be')) {
    const videoId = url.includes('youtu.be') 
      ? url.split('youtu.be/')[1]?.split('?')[0]
      : url.split('v=')[1]?.split('&')[0];
    if (videoId) {
      return (
        <div className="mb-2 rounded-lg overflow-hidden">
          <iframe
            width="100%"
            height="400"
            src={`https://www.youtube.com/embed/${videoId}`}
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            title="YouTube video"
          />
        </div>
      );
    }
  }
  
  // Vimeo
  if (url.includes('vimeo.com')) {
    const videoId = url.split('vimeo.com/')[1]?.split('?')[0];
    if (videoId) {
      return (
        <div className="mb-2 rounded-lg overflow-hidden">
          <iframe
            src={`https://player.vimeo.com/video/${videoId}`}
            width="100%"
            height="400"
            frameBorder="0"
            allow="autoplay; fullscreen; picture-in-picture"
            allowFullScreen
            title="Vimeo video"
          />
        </div>
      );
    }
  }
  
  // Generic video file
  if (url.endsWith('.mp4') || url.endsWith('.webm') || url.endsWith('.ogg')) {
    return (
      <div className="mb-2 rounded-lg overflow-hidden bg-black">
        <video width="100%" height="400" controls className="rounded-lg w-full">
          <source src={url} />
          Your browser does not support the video tag.
        </video>
      </div>
    );
  }
  
  return null;
};

const normalizeCellValue = (value: unknown): string => {
  if (value === null || value === undefined) {
    return '-';
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
};

const DEFAULT_TABLE_PAGE_SIZE = 10;

const escapeCsvValue = (value: unknown): string => {
  const normalized = normalizeCellValue(value);
  return `"${normalized.replace(/"/g, '""')}"`;
};

export function MessageList({ messages, isLoading, onEditMessage, onRegenerateMessage }: MessageListProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [copiedSqlId, setCopiedSqlId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [pageByMessage, setPageByMessage] = useState<Record<string, number>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleEditStart = (message: Message) => {
    setEditingId(message.id);
    setEditingText(message.content);
  };

  const handleEditSave = (messageId: string) => {
    if (editingText.trim() && onEditMessage) {
      onEditMessage(messageId, editingText.trim());
    }
    setEditingId(null);
    setEditingText('');
  };

  const handleEditCancel = () => {
    setEditingId(null);
    setEditingText('');
  };

  const handleCopyMessage = (content: string, messageId: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(messageId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleRegenerate = (messageId: string) => {
    if (onRegenerateMessage) {
      onRegenerateMessage(messageId);
    }
  };

  const handleCopySql = (messageId: string, sql: string) => {
    navigator.clipboard.writeText(sql);
    setCopiedSqlId(messageId);
    setTimeout(() => setCopiedSqlId(null), 2000);
  };

  const handleExportCsv = (messageId: string, columns: string[], rows: Record<string, unknown>[]) => {
    if (!columns.length || !rows.length) {
      return;
    }

    const headerLine = columns.map((column) => escapeCsvValue(column)).join(',');
    const dataLines = rows.map((row) => columns.map((column) => escapeCsvValue(row[column])).join(','));
    const csvContent = [headerLine, ...dataLines].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    link.href = url;
    link.download = `db-results-${messageId}-${timestamp}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col space-y-4 p-4 max-w-4xl mx-auto w-full h-full overflow-y-auto">
      {messages.map((message, index) => {
        const dbRows = message.dbRows && message.dbRows.length > 0 ? message.dbRows : [];

        const dbColumns = dbRows.length > 0
          ? Array.from(
              dbRows.reduce((keys, row) => {
                Object.keys(row).forEach((key) => keys.add(key));
                return keys;
              }, new Set<string>())
            )
          : [];

        const totalPages = Math.max(1, Math.ceil(dbRows.length / DEFAULT_TABLE_PAGE_SIZE));
        const currentPage = Math.min(pageByMessage[message.id] || 1, totalPages);
        const startIndex = (currentPage - 1) * DEFAULT_TABLE_PAGE_SIZE;
        const paginatedRows = dbRows.slice(startIndex, startIndex + DEFAULT_TABLE_PAGE_SIZE);

        const assistantDisplayContent = message.dbGeneratedSql
          ? message.content
              .replace(/(^|\n)\s*SQL Used:.*$/gim, '')
              .replace(/\n{3,}/g, '\n\n')
              .trim()
          : message.content;
        
        // Debug logging for ALL assistant messages
        if (message.sender === 'assistant') {
          console.log('[MessageList] Rendering assistant message:', {
            messageId: message.id,
            messageContentLength: message.content.length,
            messageContentPreview: message.content.substring(0, 100),
            messageContentIsEmpty: message.content === '',
            messageContentIsNull: message.content === null,
            messageContentIsUndefined: message.content === undefined,
            displayContentLength: assistantDisplayContent.length,
            displayContentPreview: assistantDisplayContent.substring(0, 100),
            displayContentIsEmpty: assistantDisplayContent === '',
            dbGeneratedSql: message.dbGeneratedSql,
          });
          
          if (!assistantDisplayContent || assistantDisplayContent.trim() === '') {
            console.warn('[MessageList] ⚠️ EMPTY assistant content detected!');
          }
        }

        return (
        <div
          key={message.id}
          className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'} group`}
          onMouseEnter={() => setHoveredId(message.id)}
          onMouseLeave={() => setHoveredId(null)}
        >
          <div className={`flex gap-3 max-w-2xl ${message.sender === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
            {/* Avatar */}
            <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-lg mt-1">
              {message.sender === 'user' ? '👤' : '🤖'}
            </div>

            {/* Message Content */}
            <div className="flex flex-col gap-2">
              <div
                className={`px-4 py-3 rounded-lg ${
                  message.sender === 'user'
                    ? 'bg-gray-800 text-white rounded-br-none'
                    : 'bg-gray-100 text-gray-900 rounded-bl-none'
                }`}
              >
                {editingId === message.id ? (
                  <div className="space-y-2">
                    <textarea
                      value={editingText}
                      onChange={(e) => setEditingText(e.target.value)}
                      className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 outline-none resize-none"
                      rows={3}
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEditSave(message.id)}
                        className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition"
                      >
                        Save
                      </button>
                      <button
                        onClick={handleEditCancel}
                        className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded transition"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : message.imageUrl ? (
                  <div>
                    <ImageDisplay 
                      src={message.imageUrl} 
                      alt={message.imagePrompt || 'Generated image'}
                      prompt={message.imagePrompt}
                    />
                  </div>
                ) : message.sender === 'assistant' ? (
                  <div className="prose prose-sm max-w-none">
                    {message.dbGeneratedSql && (
                      <details className="mb-3 rounded-lg border border-blue-300 bg-blue-50/70 p-2">
                        <summary className="cursor-pointer select-none text-xs font-semibold text-blue-800">
                          SQL Query
                        </summary>
                        <div className="mt-2 mb-2 flex justify-end">
                          <button
                            type="button"
                            onClick={() => handleCopySql(message.id, message.dbGeneratedSql || '')}
                            className="rounded-md border border-blue-300 bg-white px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 transition"
                          >
                            {copiedSqlId === message.id ? 'Copied SQL' : 'Copy SQL'}
                          </button>
                        </div>
                        <div className="mt-2 rounded-lg overflow-hidden">
                          <SyntaxHighlighter
                            style={vscDarkPlus}
                            language="sql"
                            showLineNumbers={true}
                            wrapLongLines={true}
                            className="!m-0 !p-3 text-sm"
                          >
                            {message.dbGeneratedSql}
                          </SyntaxHighlighter>
                        </div>
                      </details>
                    )}

                    {dbRows.length > 0 && (
                      <details className="mb-3 rounded-lg border border-emerald-300 bg-emerald-50/70 p-2" open>
                        <summary className="cursor-pointer select-none text-xs font-semibold text-emerald-800">
                          Result Table ({dbRows.length} rows)
                        </summary>
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            onClick={() => handleExportCsv(message.id, dbColumns, dbRows)}
                            className="ml-auto rounded border border-emerald-300 bg-white px-2 py-1 text-xs font-medium text-emerald-800 hover:bg-emerald-100 transition"
                          >
                            Export CSV
                          </button>
                        </div>
                        <div className="mt-2 overflow-x-auto rounded-lg border border-emerald-200 bg-white">
                          <table className="min-w-full border-collapse">
                            <thead className="bg-emerald-100 text-emerald-900">
                              <tr>
                                <th className="px-3 py-2 text-left text-xs font-semibold">#</th>
                                {dbColumns.map((column) => (
                                  <th key={column} className="px-3 py-2 text-left text-xs font-semibold">
                                    {column}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-emerald-100">
                              {paginatedRows.map((row, rowIndex) => (
                                <tr key={`${message.id}-row-${rowIndex}`} className="odd:bg-white even:bg-emerald-50/30">
                                  <td className="px-3 py-2 text-xs text-gray-500">{startIndex + rowIndex + 1}</td>
                                  {dbColumns.map((column) => (
                                    <td key={`${message.id}-${rowIndex}-${column}`} className="px-3 py-2 text-sm text-gray-800 align-top">
                                      {normalizeCellValue(row[column])}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        {totalPages > 1 && (
                          <div className="mt-2 flex items-center justify-between gap-2">
                            <p className="text-xs text-emerald-900">
                              Page {currentPage} of {totalPages}
                            </p>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => setPageByMessage((prev) => ({
                                  ...prev,
                                  [message.id]: Math.max(1, currentPage - 1),
                                }))}
                                disabled={currentPage === 1}
                                className="rounded border border-emerald-300 bg-white px-2 py-1 text-xs font-medium text-emerald-800 hover:bg-emerald-100 transition disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                Previous
                              </button>
                              <button
                                type="button"
                                onClick={() => setPageByMessage((prev) => ({
                                  ...prev,
                                  [message.id]: Math.min(totalPages, currentPage + 1),
                                }))}
                                disabled={currentPage === totalPages}
                                className="rounded border border-emerald-300 bg-white px-2 py-1 text-xs font-medium text-emerald-800 hover:bg-emerald-100 transition disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                Next
                              </button>
                            </div>
                          </div>
                        )}
                      </details>
                    )}

                    <ErrorBoundary fallback={<p className="text-gray-700">Unable to render message formatting</p>}>
                      <MarkdownRenderer content={assistantDisplayContent} />
                    </ErrorBoundary>
                  </div>
                ) : (
                  <p className="text-justify break-words">{message.content}</p>
                )}

                {message.sender === 'assistant' && message.dbGeneratedSql && (
                  <div className="mt-2">
                    <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-1 text-[11px] font-semibold text-blue-800">
                      DB Response
                    </span>
                  </div>
                )}
                <span className={`text-xs mt-2 block opacity-60 ${
                  message.sender === 'user' ? 'text-gray-300' : 'text-gray-600'
                }`}>
                  {message.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>

              {/* Action Buttons - Show on hover */}
              {editingId !== message.id && (hoveredId === message.id || copiedId === message.id) && (
                <div className="flex gap-2 items-center px-1">
                  {/* Copy Button */}
                  <button
                    onClick={() => handleCopyMessage(message.content, message.id)}
                    className="p-2 hover:bg-gray-200 rounded transition text-gray-600 hover:text-gray-900"
                    title={copiedId === message.id ? "Copied!" : "Copy"}
                  >
                    {copiedId === message.id ? '✅' : '📋'}
                  </button>

                  {/* Edit Button - Only for user messages */}
                  {message.sender === 'user' && (
                    <button
                      onClick={() => handleEditStart(message)}
                      className="p-2 hover:bg-gray-200 rounded transition text-gray-600 hover:text-gray-900"
                      title="Edit message"
                    >
                      ✏️
                    </button>
                  )}

                  {/* Regenerate Button - Only for assistant messages and last message in conversation */}
                  {message.sender === 'assistant' && index === messages.length - 1 && (
                    <button
                      onClick={() => handleRegenerate(message.id)}
                      className="p-2 hover:bg-gray-200 rounded transition text-gray-600 hover:text-gray-900"
                      title="Regenerate response"
                    >
                      🔄
                    </button>
                  )}

                  {/* Thumbs Up - Only for assistant messages */}
                  {message.sender === 'assistant' && (
                    <button
                      className="p-2 hover:bg-gray-200 rounded transition text-gray-600 hover:text-green-600"
                      title="This is helpful"
                    >
                      👍
                    </button>
                  )}

                  {/* Thumbs Down - Only for assistant messages */}
                  {message.sender === 'assistant' && (
                    <button
                      className="p-2 hover:bg-gray-200 rounded transition text-gray-600 hover:text-red-600"
                      title="This is not helpful"
                    >
                      👎
                    </button>
                  )}

                  {/* Share Button - Only for assistant messages */}
                  {message.sender === 'assistant' && (
                    <button
                      onClick={() => {
                        const shareUrl = `${window.location.origin}?message=${encodeURIComponent(message.content.substring(0, 100))}`;
                        navigator.clipboard.writeText(shareUrl);
                        alert('Share link copied to clipboard! 📋');
                      }}
                      className="p-2 hover:bg-gray-200 rounded transition text-gray-600 hover:text-blue-600"
                      title="Share this response"
                    >
                      📤
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )})}
      
      {isLoading && (
        <div className="flex justify-start">
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-lg mt-1">
              🤖
            </div>
            <div className="bg-gray-100 text-gray-900 px-4 py-3 rounded-lg rounded-bl-none">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
    </div>
  );
}
