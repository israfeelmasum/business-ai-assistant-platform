import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Badge from '../components/Badge';

function Spinner() {
  return (
    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  );
}

function AddOrgModal({ onClose, onCreated, api }) {
  const [name, setName]         = useState('');
  const [slug, setSlug]         = useState('');
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');

  // Auto-generate slug from name
  function handleNameChange(val) {
    setName(val);
    setSlug(val.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, ''));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError('');
    try {
      const org = await api.post('/organizations', { name: name.trim(), slug: slug.trim() || undefined });
      onCreated(org);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-gray-900">Add Company</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            &times;
          </button>
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Company Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={e => handleNameChange(e.target.value)}
              placeholder="Acme Corp"
              required
              autoFocus
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm
                         focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Slug <span className="text-xs text-gray-400 font-normal">(auto-generated)</span>
            </label>
            <input
              type="text"
              value={slug}
              onChange={e => setSlug(e.target.value)}
              placeholder="acme-corp"
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm font-mono
                         focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex gap-3 pt-1">
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="flex-1 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold
                         hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                         flex items-center justify-center gap-2 transition-colors"
            >
              {loading ? <><Spinner /> Creating…</> : 'Create Company'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 border border-gray-200 text-gray-600 rounded-xl text-sm
                         hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function SuperAdmin() {
  const { api, user } = useAuth();

  const [orgs, setOrgs]         = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');
  const [showModal, setShowModal] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [togglingId, setTogglingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  function loadOrgs() {
    if (!api) return;
    setLoading(true);
    setError('');
    api.get('/organizations/all')
      .then(data => {
        const list = Array.isArray(data) ? data : data?.organizations || data?.items || [];
        setOrgs(list);
      })
      .catch(err => {
        if (err.message.includes('403') || err.message.toLowerCase().includes('forbidden')) {
          setForbidden(true);
        } else {
          setError(err.message);
        }
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadOrgs(); }, [api]);

  function handleOrgCreated(org) {
    setShowModal(false);
    setOrgs(prev => [org, ...prev]);
  }

  async function toggleOrgStatus(org) {
    setTogglingId(org.id);
    try {
      const updated = await api.patch(`/organizations/${org.id}`, {
        is_active: !org.is_active,
      });
      setOrgs(prev => prev.map(o => o.id === org.id ? { ...o, is_active: !o.is_active } : o));
    } catch (err) {
      alert(`Failed to update status: ${err.message}`);
    } finally {
      setTogglingId(null);
    }
  }

  async function deleteOrg(org) {
    if (!window.confirm(`Permanently delete "${org.name}"? This cannot be undone.`)) return;
    setDeletingId(org.id);
    try {
      await api.del(`/organizations/${org.id}`);
      setOrgs(prev => prev.filter(o => o.id !== org.id));
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  }

  if (forbidden) {
    return (
      <div>
        <Header title="Super Admin" subtitle="Platform-wide organization management" />
        <div className="p-6 lg:p-8">
          <div className="max-w-md mx-auto mt-16 text-center">
            <div className="w-16 h-16 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">🔒</span>
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">Access Denied</h2>
            <p className="text-gray-500 text-sm">
              Super Admin access required. This area is restricted to platform administrators only.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const [topupOrg, setTopupOrg]       = useState(null); // org being topped up
  const [topupAmt, setTopupAmt]       = useState(500000);
  const [topupLoading, setTopupLoading] = useState(false);
  const [settingsOrg, setSettingsOrg] = useState(null); // org whose settings panel is open
  const [orgTokens, setOrgTokens]     = useState({});   // {orgId: balance}

  async function loadTokenBalance(org) {
    try {
      const bal = await api.get(`/organizations/${org.id}/tokens/balance`);
      setOrgTokens(prev => ({ ...prev, [org.id]: bal?.balance ?? '—' }));
    } catch { /* ignore */ }
  }

  async function handleTopup() {
    if (!topupOrg) return;
    setTopupLoading(true);
    try {
      await api.post(`/organizations/${topupOrg.id}/tokens/topup`, {
        tokens: Number(topupAmt),
        notes: `Super admin top-up by ${user?.email}`,
      });
      await loadTokenBalance(topupOrg);
      setTopupOrg(null);
      alert(`✅ ${Number(topupAmt).toLocaleString()} tokens added to ${topupOrg.name}`);
    } catch (err) {
      alert(`Top-up failed: ${err.message}`);
    } finally {
      setTopupLoading(false);
    }
  }

  return (
    <div>
      <Header title="Super Admin" subtitle="Platform-wide organization management" />

      {/* Add company modal */}
      {showModal && (
        <AddOrgModal api={api} onClose={() => setShowModal(false)} onCreated={handleOrgCreated} />
      )}

      {/* Token top-up modal */}
      {topupOrg && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-1">Top Up Tokens</h2>
            <p className="text-sm text-gray-500 mb-4">{topupOrg.name}</p>
            <p className="text-xs text-gray-400 mb-1">
              Current balance: <strong>{orgTokens[topupOrg.id] ?? '…'}</strong>
            </p>
            <label className="block text-sm font-medium text-gray-700 mb-1.5 mt-3">Tokens to add</label>
            <input
              type="number"
              value={topupAmt}
              onChange={e => setTopupAmt(e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm mb-4
                         focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <div className="flex gap-2">
              {[100000, 500000, 1000000].map(n => (
                <button key={n} onClick={() => setTopupAmt(n)}
                  className="flex-1 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors">
                  {(n/1000).toFixed(0)}K
                </button>
              ))}
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={handleTopup} disabled={topupLoading}
                className="flex-1 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold
                           hover:bg-blue-700 disabled:opacity-50 transition-colors">
                {topupLoading ? 'Adding…' : 'Add Tokens'}
              </button>
              <button onClick={() => setTopupOrg(null)}
                className="px-4 py-2.5 border border-gray-200 text-gray-600 rounded-xl text-sm hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Inline tenant settings panel */}
      {settingsOrg && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-gray-900">{settingsOrg.name}</h2>
                <p className="text-xs text-gray-400 font-mono">{settingsOrg.id}</p>
              </div>
              <button onClick={() => setSettingsOrg(null)}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs text-gray-400 mb-1">Slug</p>
                  <p className="font-mono text-gray-700">{settingsOrg.slug || '—'}</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs text-gray-400 mb-1">Status</p>
                  <Badge variant={settingsOrg.is_active !== false ? 'success' : 'neutral'}>
                    {settingsOrg.is_active !== false ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs text-gray-400 mb-1">Members</p>
                  <p className="font-semibold text-gray-800">{settingsOrg.member_count ?? '—'}</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-3">
                  <p className="text-xs text-gray-400 mb-1">Token Balance</p>
                  <p className="font-semibold text-gray-800">{orgTokens[settingsOrg.id] != null ? Number(orgTokens[settingsOrg.id]).toLocaleString() : '—'}</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2 pt-2">
                <button
                  onClick={() => { setTopupOrg(settingsOrg); setSettingsOrg(null); loadTokenBalance(settingsOrg); }}
                  className="px-3 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition-colors"
                >
                  🔋 Top Up Tokens
                </button>
                <button
                  onClick={() => toggleOrgStatus(settingsOrg)}
                  className={`px-3 py-2 rounded-lg text-xs font-semibold transition-colors ${
                    settingsOrg.is_active !== false
                      ? 'bg-amber-50 text-amber-700 hover:bg-amber-100'
                      : 'bg-green-50 text-green-700 hover:bg-green-100'
                  }`}
                >
                  {settingsOrg.is_active !== false ? '⏸ Suspend' : '▶ Activate'}
                </button>
                <a
                  href={`/admin/`}
                  target="_blank" rel="noopener noreferrer"
                  className="px-3 py-2 bg-purple-50 text-purple-700 rounded-lg text-xs font-semibold hover:bg-purple-100 transition-colors"
                >
                  ⚙️ Open Settings Panel
                </a>
              </div>
              <p className="text-xs text-gray-400 pt-1">
                Org ID: <span className="font-mono">{settingsOrg.id}</span> — copy this ID to access any org's API endpoints directly.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="p-6 lg:p-8">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="bg-purple-100 text-purple-700 text-xs font-semibold px-3 py-1 rounded-full">
              {loading ? '…' : `${orgs.length} Companies`}
            </div>
            <span className="text-sm text-gray-500">Registered on the platform</span>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl
                       text-sm font-semibold hover:bg-blue-700 transition-colors"
          >
            <span className="text-base leading-none">+</span> Add Company
          </button>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="p-12 text-center">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-gray-400">Loading organizations…</p>
            </div>
          ) : orgs.length === 0 ? (
            <div className="p-12 text-center text-gray-400 text-sm">No companies found. Add the first one.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr className="text-left text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-5 py-3.5 font-medium">Company</th>
                    <th className="px-5 py-3.5 font-medium">Slug</th>
                    <th className="px-5 py-3.5 font-medium">Members</th>
                    <th className="px-5 py-3.5 font-medium">Status</th>
                    <th className="px-5 py-3.5 font-medium">Created</th>
                    <th className="px-5 py-3.5 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {orgs.map(org => (
                    <tr key={org.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-5 py-4">
                        <p className="font-medium text-gray-900">{org.name}</p>
                        <p className="text-xs text-gray-400 font-mono mt-0.5 truncate max-w-[180px]">{org.id}</p>
                      </td>
                      <td className="px-5 py-4">
                        <code className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-xs">{org.slug || '—'}</code>
                      </td>
                      <td className="px-5 py-4 text-gray-700">{org.member_count ?? org.members_count ?? '—'}</td>
                      <td className="px-5 py-4">
                        <Badge variant={org.is_active !== false ? 'success' : 'neutral'}>
                          {org.is_active !== false ? 'Active' : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="px-5 py-4 text-gray-400 text-xs">
                        {org.created_at ? new Date(org.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2 flex-wrap">
                          {/* Settings / Details */}
                          <button
                            onClick={() => { setSettingsOrg(org); loadTokenBalance(org); }}
                            className="text-xs font-medium px-2.5 py-1 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors"
                          >
                            ⚙ Settings
                          </button>
                          {/* Top Up */}
                          <button
                            onClick={() => { setTopupOrg(org); loadTokenBalance(org); }}
                            className="text-xs font-medium px-2.5 py-1 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors"
                          >
                            🔋 Tokens
                          </button>
                          {/* Suspend / Activate */}
                          <button
                            onClick={() => toggleOrgStatus(org)}
                            disabled={togglingId === org.id}
                            className={`text-xs font-medium px-2.5 py-1 rounded-lg transition-colors disabled:opacity-50 ${
                              org.is_active !== false
                                ? 'bg-amber-50 text-amber-700 hover:bg-amber-100'
                                : 'bg-green-50 text-green-700 hover:bg-green-100'
                            }`}
                          >
                            {togglingId === org.id ? '…' : org.is_active !== false ? 'Suspend' : 'Activate'}
                          </button>
                          {/* Delete */}
                          <button
                            onClick={() => deleteOrg(org)}
                            disabled={deletingId === org.id}
                            className="text-red-400 hover:text-red-600 text-xs disabled:opacity-50"
                          >
                            {deletingId === org.id ? '…' : '🗑'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="mt-6 bg-purple-50 border border-purple-200 rounded-xl p-4">
          <p className="text-xs text-purple-700">
            <span className="font-semibold">Super Admin Panel</span> — Changes here affect all organizations on the
            Fellow BOT platform. Logged in as: <span className="font-mono">{user?.email}</span>
          </p>
        </div>
      </div>
    </div>
  );
}
