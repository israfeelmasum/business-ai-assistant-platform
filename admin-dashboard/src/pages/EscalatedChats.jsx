import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Badge from '../components/Badge';

export default function EscalatedChats() {
  const { api, orgId } = useAuth();
  const [escalations, setEscalations] = useState([]);
  const [selected, setSelected]       = useState(null);
  const [convMessages, setConvMessages] = useState([]);  // full conversation messages
  const [reply, setReply]             = useState('');
  const [sending, setSending]         = useState(false);
  const [resolving, setResolving]     = useState(false);
  const [takingOver, setTakingOver]   = useState(false);
  const [loadError, setLoadError]     = useState('');
  const messagesEnd = useRef(null);

  const loadEscalations = useCallback(async () => {
    if (!api || !orgId) return;
    try {
      const data = await api.get(`/organizations/${orgId}/escalations`);
      const list = Array.isArray(data) ? data : data?.escalations || data?.items || [];
      setEscalations(list);
      setLoadError('');
      // Keep selected in sync
      if (selected) {
        const updated = list.find(e => e.id === selected.id);
        if (updated) setSelected(updated);
      }
    } catch (e) {
      setLoadError(e.message);
    }
  }, [api, orgId, selected?.id]);

  // Load full conversation messages when a selection changes
  useEffect(() => {
    if (!selected || !api || !orgId) return;
    const convId = selected.conversation_id || selected.id;
    api.get(`/organizations/${orgId}/conversations/${convId}/messages`)
      .then(msgs => {
        const list = Array.isArray(msgs) ? msgs : msgs?.messages || msgs?.items || [];
        setConvMessages(list);
      })
      .catch(() => setConvMessages([]));
  }, [selected?.id, api, orgId]);

  // Initial load + 5-second refresh
  useEffect(() => {
    loadEscalations();
    const interval = setInterval(loadEscalations, 5000);
    return () => clearInterval(interval);
  }, [api, orgId]); // re-create interval if api/orgId changes

  // Auto-scroll to newest message
  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [convMessages]);

  async function sendReply() {
    if (!reply.trim() || !selected) return;
    setSending(true);
    try {
      await api.post(
        `/organizations/${orgId}/escalations/${selected.id}/message`,
        { content: reply.trim() }
      );
      setReply('');
      await loadEscalations();
    } catch (err) {
      alert(`Failed to send: ${err.message}`);
    } finally {
      setSending(false);
    }
  }

  async function takeOver() {
    if (!selected) return;
    setTakingOver(true);
    try {
      await api.post(`/organizations/${orgId}/escalations/${selected.id}/take-over`, {});
      await loadEscalations();
    } catch (err) {
      alert(`Take-over failed: ${err.message}`);
    } finally {
      setTakingOver(false);
    }
  }

  async function resolveEscalation() {
    if (!selected) return;
    if (!window.confirm('Mark this escalation as resolved?')) return;
    setResolving(true);
    try {
      await api.post(`/organizations/${orgId}/escalations/${selected.id}/resolve`, {});
      setSelected(null);
      await loadEscalations();
    } catch (err) {
      alert(`Failed to resolve: ${err.message}`);
    } finally {
      setResolving(false);
    }
  }

  // Derive messages — prefer freshly fetched conversation messages, fallback to escalation-embedded
  const messages = convMessages.length > 0
    ? convMessages
    : (selected?.messages || selected?.conversation?.messages || []);

  return (
    <div>
      <Header
        title="Escalated Chats"
        subtitle={`${escalations.length} escalation${escalations.length !== 1 ? 's' : ''} need attention`}
      />
      <div className="p-6 lg:p-8">
        {loadError && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            {loadError}
          </div>
        )}

        <div className="flex gap-5 h-[calc(100vh-200px)] min-h-[400px]">
          {/* ── Left panel: escalation list ── */}
          <div className="w-72 bg-white rounded-xl border border-gray-200 flex flex-col flex-shrink-0 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
              <h3 className="font-semibold text-gray-800 text-sm">
                Pending ({escalations.filter(e => e.status !== 'resolved').length})
              </h3>
              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" title="Auto-refreshing every 5s" />
            </div>

            <div className="overflow-y-auto flex-1">
              {escalations.length === 0 ? (
                <div className="text-center py-12 text-gray-400 text-sm px-4">
                  No escalations — great!
                </div>
              ) : (
                escalations.map(esc => (
                  <button
                    key={esc.id}
                    onClick={() => setSelected(esc)}
                    className={`w-full text-left px-4 py-3.5 border-b border-gray-100 transition-colors
                      ${selected?.id === esc.id
                        ? 'bg-blue-50 border-l-4 border-l-blue-600'
                        : 'hover:bg-gray-50'
                      }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <p className="font-medium text-sm text-gray-800 truncate mr-2">
                        {esc.user_name || esc.user_id || esc.session_id?.slice(0, 14) || 'Anonymous'}
                      </p>
                      <Badge variant={esc.status === 'resolved' ? 'neutral' : 'error'}>
                        {esc.status || 'open'}
                      </Badge>
                    </div>
                    <p className="text-xs text-gray-400 truncate">
                      {esc.reason || esc.subject || 'No reason provided'}
                    </p>
                    <p className="text-xs text-gray-300 mt-0.5">
                      {esc.created_at ? new Date(esc.created_at).toLocaleString() : ''}
                    </p>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* ── Right panel: chat detail ── */}
          <div className="flex-1 bg-white rounded-xl border border-gray-200 flex flex-col overflow-hidden">
            {!selected ? (
              <div className="flex-1 flex items-center justify-center text-gray-300">
                <div className="text-center">
                  <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                  <p className="text-sm">Select an escalation to view the conversation</p>
                </div>
              </div>
            ) : (
              <>
                {/* Chat header */}
                <div className="px-5 py-4 border-b border-gray-200 flex items-start justify-between gap-4">
                  <div>
                    <h3 className="font-semibold text-gray-800">
                      {selected.user_name || selected.user_id || 'Anonymous'}
                    </h3>
                    <p className="text-xs text-gray-400 mt-0.5 font-mono">
                      {selected.session_id || selected.id}
                    </p>
                    {selected.reason && (
                      <p className="text-xs text-amber-600 mt-1">
                        Reason: {selected.reason}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    {selected.status !== 'resolved' && selected.agent_id == null && (
                      <button
                        onClick={takeOver}
                        disabled={takingOver}
                        title="Stop AI replies and take over this conversation as a human agent"
                        className="px-3 py-1.5 bg-amber-500 text-white rounded-lg text-xs font-semibold
                                   hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {takingOver ? 'Taking over…' : '🙋 Take Over from AI'}
                      </button>
                    )}
                    {selected.agent_id && selected.status !== 'resolved' && (
                      <span className="px-3 py-1.5 bg-amber-100 text-amber-800 rounded-lg text-xs font-semibold">
                        👤 Human Active
                      </span>
                    )}
                    <button
                      onClick={resolveEscalation}
                      disabled={resolving || selected.status === 'resolved'}
                      className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-semibold
                                 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {resolving ? 'Resolving…' : selected.status === 'resolved' ? '✅ Resolved' : 'Mark Resolved'}
                    </button>
                  </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-5 space-y-3 bg-gray-50">
                  {messages.length === 0 ? (
                    <p className="text-center text-sm text-gray-400 py-8">No messages in this escalation.</p>
                  ) : (
                    messages.map((msg, i) => {
                      const isUser  = msg.role === 'user'  || msg.sender === 'user';
                      const isAgent = msg.role === 'agent' || msg.sender === 'agent';
                      return (
                        <div key={i} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-[72%] px-4 py-2.5 rounded-2xl text-sm shadow-sm ${
                            isUser  ? 'bg-blue-600 text-white rounded-br-sm' :
                            isAgent ? 'bg-green-600 text-white rounded-bl-sm' :
                                      'bg-white text-gray-800 rounded-bl-sm border border-gray-200'
                          }`}>
                            {isAgent && (
                              <p className="text-[10px] font-semibold opacity-80 mb-0.5 uppercase tracking-wide">Agent</p>
                            )}
                            <p className="whitespace-pre-wrap">{msg.content || msg.text || msg.message}</p>
                            {msg.created_at && (
                              <p className="text-[10px] opacity-60 mt-1">
                                {new Date(msg.created_at).toLocaleTimeString()}
                              </p>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                  <div ref={messagesEnd} />
                </div>

                {/* Reply input */}
                {selected.status !== 'resolved' && (
                  <div className="p-4 border-t border-gray-200 flex gap-3 bg-white">
                    <input
                      value={reply}
                      onChange={e => setReply(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendReply()}
                      placeholder="Type your reply and press Enter…"
                      className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm
                                 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={sendReply}
                      disabled={sending || !reply.trim()}
                      className="px-5 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold
                                 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
                    >
                      {sending ? 'Sending…' : 'Send'}
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
