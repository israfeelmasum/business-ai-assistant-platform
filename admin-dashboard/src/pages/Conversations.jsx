import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Badge from '../components/Badge';

function statusVariant(status) {
  if (!status) return 'neutral';
  if (status === 'active')          return 'success';
  if (status === 'resolved')        return 'neutral';
  if (status.includes('escal'))     return 'error';
  return 'neutral';
}

export default function Conversations() {
  const { api, orgId } = useAuth();
  const [convos, setConvos]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');
  const [search, setSearch]   = useState('');

  useEffect(() => {
    if (!api || !orgId) return;
    setLoading(true);
    setError('');
    api.get(`/organizations/${orgId}/conversations?limit=50`)
      .then(data => {
        const list = Array.isArray(data) ? data : data?.conversations || data?.items || [];
        setConvos(list);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [api, orgId]);

  const filtered = convos.filter(c => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      (c.session_id || '').toLowerCase().includes(q) ||
      (c.channel    || '').toLowerCase().includes(q) ||
      (c.status     || '').toLowerCase().includes(q)
    );
  });

  return (
    <div>
      <Header
        title="Conversations"
        subtitle={`${convos.length} total conversation${convos.length !== 1 ? 's' : ''}`}
      />
      <div className="p-6 lg:p-8">
        {/* Search bar */}
        <div className="mb-5">
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by session ID, channel, or status…"
            className="w-full max-w-sm px-4 py-2.5 border border-gray-200 rounded-xl text-sm
                       focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          />
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16 text-gray-400 text-sm">
              <svg className="w-5 h-5 animate-spin mr-2" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Loading conversations…
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16 text-gray-400 text-sm">
              {search ? 'No conversations match your search.' : 'No conversations yet.'}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr className="text-left text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-5 py-3 font-medium">Session ID</th>
                    <th className="px-5 py-3 font-medium">Channel</th>
                    <th className="px-5 py-3 font-medium">Messages</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Created</th>
                    <th className="px-5 py-3 font-medium">Updated</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filtered.map(c => (
                    <tr key={c.id || c.session_id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-5 py-3 font-mono text-xs text-gray-700">
                        <span title={c.session_id}>
                          {(c.session_id || c.id || '').slice(0, 24)}…
                        </span>
                      </td>
                      <td className="px-5 py-3 text-gray-600 capitalize">
                        {c.channel || '—'}
                      </td>
                      <td className="px-5 py-3 text-gray-700 tabular-nums">
                        {c.message_count ?? c.messages?.length ?? '—'}
                      </td>
                      <td className="px-5 py-3">
                        <Badge variant={statusVariant(c.status)}>
                          {c.status || 'unknown'}
                        </Badge>
                      </td>
                      <td className="px-5 py-3 text-gray-400 text-xs whitespace-nowrap">
                        {c.created_at
                          ? new Date(c.created_at).toLocaleString()
                          : '—'}
                      </td>
                      <td className="px-5 py-3 text-gray-400 text-xs whitespace-nowrap">
                        {c.updated_at
                          ? new Date(c.updated_at).toLocaleString()
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {!loading && filtered.length > 0 && (
          <p className="text-xs text-gray-400 mt-3 text-right">
            Showing {filtered.length} of {convos.length} conversations
          </p>
        )}
      </div>
    </div>
  );
}
