import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../lib/api';
import type { ResearchDigestHistoryItem, ResearchDigestResult, ResearchStreamEvent } from '../types/chat';
import { MarkdownRenderer } from './MarkdownRenderer';

export function Project10Page() {
  const navigate = useNavigate();

  const [query, setQuery] = useState('');
  const [categories, setCategories] = useState('');
  const [conversationId, setConversationId] = useState<number | undefined>(undefined);

  const [events, setEvents] = useState<string[]>([]);
  const [result, setResult] = useState<ResearchDigestResult | null>(null);
  const [running, setRunning] = useState(false);
  const [history, setHistory] = useState<ResearchDigestHistoryItem[]>([]);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [selectedDigest, setSelectedDigest] = useState<ResearchDigestHistoryItem | null>(null);
  const historyPageSize = 5;

  const handleCopyDigest = async (digest: ResearchDigestHistoryItem) => {
    const content = digest.rendered_digest_text || 'No rendered digest text stored.';
    await navigator.clipboard.writeText(content);
  };

  const handleExportDigest = (digest: ResearchDigestHistoryItem) => {
    const content = digest.rendered_digest_text || 'No rendered digest text stored.';
    const safeQuery = digest.query.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'research-digest';
    const fileName = `digest-${digest.id}-${safeQuery}.md`;
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const loadHistory = async (targetPage: number) => {
    const payload = await apiClient.getResearchDigestHistory(targetPage, historyPageSize);
    setHistory(payload.items || []);
    setHistoryTotal(payload.total || 0);
    setHistoryPage(payload.page || targetPage);
  };

  useEffect(() => {
    loadHistory(1).catch((err) => {
      const message = err instanceof Error ? err.message : 'Failed to load digest history';
      setEvents((prev) => [...prev, '[error] ' + message]);
    });
  }, []);

  const runDigest = async () => {
    const normalized = query.trim();
    if (!normalized || running) return;

    setRunning(true);
    setEvents([]);
    setResult(null);

    try {
      const finalResult = await apiClient.streamResearchDigest(
        {
          query: normalized,
          conversation_id: conversationId,
          categories: categories
            .split(',')
            .map((c) => c.trim())
            .filter(Boolean),
        },
        (event: ResearchStreamEvent) => {
          if (event.type === 'status') {
            const stage = event.stage || 'status';
            const message = event.message || 'Working...';
            setEvents((prev) => [...prev, '[' + stage + '] ' + message]);
            return;
          }

          if (event.type === 'paper_analysis') {
            const data = (event.data || {}) as {
              title?: string;
              relevance_score?: number;
              quality_score?: number;
            };
            const title = data.title || 'Paper';
            const relevance = data.relevance_score ?? '-';
            const quality = data.quality_score ?? '-';
            setEvents((prev) => [...prev, '[analyze] ' + title + ' | rel=' + relevance + ' | quality=' + quality]);
            return;
          }

          if (event.type === 'error') {
            const message = event.message || 'Research digest failed.';
            setEvents((prev) => [...prev, '[error] ' + message]);
          }
        }
      );

      setResult(finalResult);
      if (finalResult.conversation_id) {
        setConversationId(finalResult.conversation_id);
      }
      await loadHistory(1);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Research digest failed';
      setEvents((prev) => [...prev, '[error] ' + message]);
    } finally {
      setRunning(false);
    }
  };

  const modeButton = (label: string, onClick: () => void, active = false, palette: 'dark' | 'blue' | 'green' | 'amber' | 'purple' = 'dark') => {
    const classes: Record<typeof palette, string> = {
      dark: active ? 'bg-gray-900 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300',
      blue: active ? 'bg-blue-700 text-white' : 'bg-blue-100 text-blue-800 hover:bg-blue-200',
      green: active ? 'bg-emerald-700 text-white' : 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200',
      amber: active ? 'bg-amber-700 text-white' : 'bg-amber-100 text-amber-900 hover:bg-amber-200',
      purple: active ? 'bg-purple-700 text-white' : 'bg-purple-100 text-purple-900 hover:bg-purple-200',
    };

    return (
      <button
        type="button"
        onClick={onClick}
        className={'px-3 py-1.5 rounded-full text-sm font-medium transition ' + classes[palette]}
      >
        {label}
      </button>
    );
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-5xl mx-auto p-6 space-y-4">
        <div className="flex items-center gap-2 px-1">
          {modeButton('General Chat', () => navigate('/'), false, 'dark')}
          {modeButton('Database Chat', () => navigate('/'), false, 'blue')}
          {modeButton('Image Generation', () => navigate('/'), false, 'green')}
          {modeButton('Research Digest Agent', () => navigate('/research-digest-agent'), true, 'amber')}
          {modeButton('🎮 Tic Tac Toe', () => navigate('/tictactoe'), false, 'purple')}
        </div>

        <div className="rounded-2xl border border-gray-200 bg-gray-50 p-5">
          <div className="mb-4">
            <h1 className="text-xl font-semibold text-gray-900">Research Digest Agent</h1>
            <p className="text-sm text-gray-600 mt-1">
              Autonomous arXiv analysis with evidence thresholds, embeddings relevance, clustering, cache, and per-conversation DB persistence.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Research query"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
            <input
              value={categories}
              onChange={(e) => setCategories(e.target.value)}
              placeholder="Categories (comma-separated, e.g. cs.AI, cs.CL)"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          <div className="flex items-center justify-between">
            <span />
            <button
              onClick={runDigest}
              disabled={running || !query.trim()}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {running ? 'Running...' : 'Run Research Digest'}
            </button>
          </div>
        </div>

        {events.length > 0 && (
          <div className="rounded-2xl border border-gray-200 bg-white p-4">
            <p className="text-sm font-semibold text-gray-800 mb-2">Live Stream</p>
            <div className="space-y-1 max-h-56 overflow-y-auto">
              {events.map((evt, idx) => (
                <p key={evt + '-' + idx} className="text-xs text-gray-700">{evt}</p>
              ))}
            </div>
          </div>
        )}

        {result && (
          <div className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-gray-800">Decision: {result.decision}</span>
              <span className="text-xs text-gray-600">HQ Papers: {result.high_quality_papers_found}/{result.min_required_high_quality_papers}</span>
              <span className="text-xs text-gray-600">Conversation: {result.conversation_id ?? '-'}</span>
              <span className="text-xs text-gray-600">Digest ID: {result.digest_id ?? '-'}</span>
              {result.cached && <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">cached</span>}
            </div>
            <div className="text-sm text-gray-800 break-words max-h-[28rem] overflow-y-auto leading-6">
              <MarkdownRenderer content={result.rendered_digest_text || result.consolidated_research_digest} />
            </div>
          </div>
        )}

        <div className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-800">View Previous Digests</p>
            <button
              type="button"
              onClick={() => loadHistory(historyPage)}
              className="text-xs px-3 py-1.5 rounded-md bg-gray-100 hover:bg-gray-200 text-gray-700"
            >
              Refresh
            </button>
          </div>

          {history.length === 0 ? (
            <p className="text-sm text-gray-500">No persisted digests yet.</p>
          ) : (
            <div className="space-y-3">
              {history.map((item) => (
                <div key={item.id} className="border border-gray-200 rounded-lg p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-semibold text-gray-800">{item.query}</span>
                      <span className="text-xs text-gray-600">Digest #{item.id}</span>
                      <span className="text-xs text-gray-600">Conversation #{item.conversation_id}</span>
                      <span className="text-xs text-gray-600">HQ {item.high_quality_papers_found}</span>
                      <span className="text-xs text-gray-600">Scanned {item.total_unique_papers_scanned}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSelectedDigest(item)}
                      className="text-xs px-2 py-1 rounded border border-gray-300 bg-white hover:bg-gray-100 text-gray-700"
                    >
                      Open Full View
                    </button>
                  </div>
                  <div className="text-sm text-gray-700 whitespace-pre-wrap line-clamp-4">
                    {item.rendered_digest_text || 'No rendered digest text stored.'}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center justify-between">
            <button
              type="button"
              disabled={historyPage <= 1}
              onClick={() => loadHistory(historyPage - 1)}
              className="text-xs px-3 py-1.5 rounded-md bg-gray-100 hover:bg-gray-200 text-gray-700 disabled:opacity-40"
            >
              Prev
            </button>
            <p className="text-xs text-gray-500">Page {historyPage} · Total {historyTotal}</p>
            <button
              type="button"
              disabled={historyPage * historyPageSize >= historyTotal}
              onClick={() => loadHistory(historyPage + 1)}
              className="text-xs px-3 py-1.5 rounded-md bg-gray-100 hover:bg-gray-200 text-gray-700 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>

        {selectedDigest && (
          <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
            <div className="bg-white w-full max-w-5xl h-[90vh] rounded-2xl shadow-2xl border border-gray-200 flex flex-col">
              <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold text-gray-900 truncate">{selectedDigest.query}</h2>
                  <p className="text-xs text-gray-600">
                    Digest #{selectedDigest.id} · Conversation #{selectedDigest.conversation_id} · HQ {selectedDigest.high_quality_papers_found} · Scanned {selectedDigest.total_unique_papers_scanned}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleCopyDigest(selectedDigest)}
                    className="text-xs px-3 py-1.5 rounded-md border border-gray-300 bg-white hover:bg-gray-100 text-gray-700"
                  >
                    Copy
                  </button>
                  <button
                    type="button"
                    onClick={() => handleExportDigest(selectedDigest)}
                    className="text-xs px-3 py-1.5 rounded-md border border-gray-300 bg-white hover:bg-gray-100 text-gray-700"
                  >
                    Export
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedDigest(null)}
                    className="text-xs px-3 py-1.5 rounded-md bg-gray-900 text-white hover:bg-gray-800"
                  >
                    Close
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-5">
                <MarkdownRenderer content={selectedDigest.rendered_digest_text || 'No rendered digest text stored.'} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
