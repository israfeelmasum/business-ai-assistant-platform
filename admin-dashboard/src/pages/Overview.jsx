import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Badge from '../components/Badge';

function StatCard({ icon, label, value, sub, color = 'blue' }) {
  const colors = {
    blue:   'bg-blue-50 text-blue-600',
    green:  'bg-green-50 text-green-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    red:    'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
  };
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-start gap-4">
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center text-xl flex-shrink-0 ${colors[color]}`}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value ?? '—'}</p>
        <p className="text-sm font-medium text-gray-600 mt-0.5">{label}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

function today() {
  return new Date().toISOString().slice(0, 10);
}
function thirtyDaysAgo() {
  const d = new Date();
  d.setDate(d.getDate() - 30);
  return d.toISOString().slice(0, 10);
}

// ── Create Chatbot Wizard ──────────────────────────────────────────────────────
function CreateChatbotWizard({ api, orgId, onClose, onCreated }) {
  const [step, setStep]         = useState(1);
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState('');
  const [form, setForm]         = useState({
    name: '', description: '', slug: '',
    persona_name: 'Assistant', greeting_message: 'Hello! How can I help you today?',
    default_language: 'en', personality: 'professional',
  });
  const [createdChatbot, setCreatedChatbot] = useState(null);

  function setF(k, v) { setForm(f => ({ ...f, [k]: v })); }

  function autoSlug(name) {
    return name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
  }

  async function finish() {
    setSaving(true); setError('');
    try {
      // Step 1: Create chatbot
      const bot = await api.post(`/organizations/${orgId}/chatbots`, {
        name: form.name, description: form.description,
        slug: form.slug || autoSlug(form.name),
      });
      // Step 2: Set persona
      await api.put(`/organizations/${orgId}/chatbots/${bot.id}/persona`, {
        persona_name: form.persona_name,
        greeting_message: form.greeting_message,
        default_language: form.default_language,
        personality: form.personality,
      }).catch(() => {});
      setCreatedChatbot(bot);
      setStep(4);
      if (onCreated) onCreated(bot);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  const inputCls = 'w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-bold text-gray-900">Create New Chatbot</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        {/* Step indicators */}
        <div className="flex items-center gap-0 px-6 pt-4">
          {['Basics', 'Persona', 'Review', 'Done'].map((label, i) => (
            <div key={i} className="flex items-center flex-1 last:flex-none">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                step > i + 1 ? 'bg-green-500 text-white' :
                step === i + 1 ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-400'
              }`}>{step > i + 1 ? '✓' : i + 1}</div>
              <div className="flex-1 h-0.5 mx-1 bg-gray-100 last:hidden">
                <div className={`h-full transition-all ${step > i + 1 ? 'bg-green-400' : 'bg-gray-100'}`} />
              </div>
              <span className={`text-xs mr-2 hidden sm:block ${step === i + 1 ? 'text-blue-600 font-semibold' : 'text-gray-400'}`}>{label}</span>
            </div>
          ))}
        </div>

        <div className="px-6 py-5 space-y-4">
          {error && <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-2 text-sm text-red-700">{error}</div>}

          {step === 1 && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Chatbot Name <span className="text-red-500">*</span></label>
                <input className={inputCls} value={form.name}
                  onChange={e => { setF('name', e.target.value); setF('slug', autoSlug(e.target.value)); }}
                  placeholder="ICT Bangladesh AI Assistant" autoFocus />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Description</label>
                <textarea className={inputCls} rows={2} value={form.description}
                  onChange={e => setF('description', e.target.value)}
                  placeholder="Helps users with course inquiries, enrollment, and support." />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Slug <span className="text-xs text-gray-400 font-normal">(URL identifier)</span>
                </label>
                <input className={`${inputCls} font-mono`} value={form.slug}
                  onChange={e => setF('slug', e.target.value)} placeholder="ict-assistant" />
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Bot Display Name</label>
                <input className={inputCls} value={form.persona_name}
                  onChange={e => setF('persona_name', e.target.value)} placeholder="Aisha" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Greeting Message</label>
                <textarea className={inputCls} rows={3} value={form.greeting_message}
                  onChange={e => setF('greeting_message', e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Language</label>
                  <select className={inputCls} value={form.default_language}
                    onChange={e => setF('default_language', e.target.value)}>
                    <option value="en">English</option>
                    <option value="bn">Bengali</option>
                    <option value="ar">Arabic</option>
                    <option value="hi">Hindi</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Personality</label>
                  <select className={inputCls} value={form.personality}
                    onChange={e => setF('personality', e.target.value)}>
                    <option value="professional">Professional</option>
                    <option value="friendly">Friendly</option>
                    <option value="formal">Formal</option>
                    <option value="empathetic">Empathetic</option>
                  </select>
                </div>
              </div>
            </>
          )}

          {step === 3 && (
            <div className="space-y-2 text-sm">
              <p className="text-gray-500 mb-3">Review before creating:</p>
              {[
                ['Name', form.name], ['Slug', form.slug || autoSlug(form.name)],
                ['Bot Name', form.persona_name], ['Language', form.default_language],
                ['Personality', form.personality],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between py-2 border-b border-gray-50">
                  <span className="text-gray-500">{k}</span>
                  <span className="font-medium text-gray-800">{v || '—'}</span>
                </div>
              ))}
            </div>
          )}

          {step === 4 && (
            <div className="text-center py-4">
              <div className="text-5xl mb-3">🎉</div>
              <h3 className="text-lg font-bold text-gray-900 mb-1">Chatbot Created!</h3>
              <p className="text-sm text-gray-500 mb-4">{createdChatbot?.name} is ready. Go to Settings to configure the AI model and Knowledge Base.</p>
              <code className="block text-xs font-mono bg-gray-50 rounded-lg px-3 py-2 text-gray-600 break-all">
                ID: {createdChatbot?.id}
              </code>
            </div>
          )}
        </div>

        <div className="flex justify-between items-center px-6 py-4 border-t border-gray-100">
          <button onClick={step > 1 && step < 4 ? () => setStep(s => s - 1) : onClose}
            className="px-4 py-2.5 border border-gray-200 text-gray-600 rounded-xl text-sm hover:bg-gray-50 transition-colors">
            {step === 4 ? 'Close' : step === 1 ? 'Cancel' : 'Back'}
          </button>
          {step < 3 && (
            <button onClick={() => setStep(s => s + 1)} disabled={step === 1 && !form.name.trim()}
              className="px-5 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors">
              Next →
            </button>
          )}
          {step === 3 && (
            <button onClick={finish} disabled={saving}
              className="px-5 py-2.5 bg-green-600 text-white rounded-xl text-sm font-semibold hover:bg-green-700 disabled:opacity-50 transition-colors flex items-center gap-2">
              {saving ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> Creating…</> : '✓ Create Chatbot'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Overview() {
  const { api, orgId, user } = useAuth();
  const [chatbotId, setChatbotId]   = useState(null);
  const [analytics, setAnalytics]   = useState(null);
  const [balance, setBalance]       = useState(null);
  const [convos, setConvos]         = useState([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState('');
  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    if (!api || !orgId) return;
    api.get(`/organizations/${orgId}/chatbots`).then(bots => {
      if (bots && bots.length > 0) setChatbotId(bots[0].id);
    }).catch(() => {});
  }, [api, orgId]);

  useEffect(() => {
    if (!api || !orgId) return;
    setLoading(true);
    setError('');

    const start = thirtyDaysAgo();
    const end   = today();

    Promise.all([
      api.get(`/organizations/${orgId}/analytics/dashboard?start=${start}&end=${end}`).catch(() => null),
      api.get(`/organizations/${orgId}/tokens/balance`).catch(() => null),
      api.get(`/organizations/${orgId}/conversations?limit=5`).catch(() => []),
    ]).then(([anal, bal, cv]) => {
      setAnalytics(anal);
      setBalance(bal);
      const list = Array.isArray(cv) ? cv : cv?.conversations || cv?.items || [];
      setConvos(list.slice(0, 5));
    }).catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [api, orgId]);

  const a = analytics || {};

  return (
    <div>
      <Header
        title="Overview"
        subtitle={`Welcome back, ${user?.full_name || user?.email || 'Admin'} — last 30 days`}
      />
      {showWizard && (
        <CreateChatbotWizard
          api={api} orgId={orgId}
          onClose={() => setShowWizard(false)}
          onCreated={() => setTimeout(() => setShowWizard(false), 3000)}
        />
      )}
      <div className="p-6 lg:p-8">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Quick action bar */}
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => setShowWizard(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl
                       text-sm font-semibold hover:bg-blue-700 transition-colors shadow-sm"
          >
            <span className="text-base">🤖</span> Create Chatbot
          </button>
          <a href="#/knowledge"
            className="flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 text-gray-700
                       rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors">
            <span>📚</span> Add Knowledge
          </a>
          <a href="#/settings"
            className="flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 text-gray-700
                       rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors">
            <span>⚙️</span> Settings
          </a>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
          <StatCard
            icon="💬"
            label="Total Conversations"
            value={loading ? '…' : a.total_conversations ?? 0}
            color="blue"
          />
          <StatCard
            icon="✅"
            label="Resolved"
            value={loading ? '…' : a.resolved_conversations ?? 0}
            color="green"
          />
          <StatCard
            icon="🚨"
            label="Escalated"
            value={loading ? '…' : a.escalated_conversations ?? 0}
            color={a.escalated_conversations > 0 ? 'red' : 'green'}
          />
          <StatCard
            icon="🪙"
            label="Token Balance"
            value={loading ? '…' : balance?.balance?.toLocaleString() ?? '—'}
            sub={balance?.plan ? `Plan: ${balance.plan}` : undefined}
            color="purple"
          />
        </div>

        {/* Second row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-8">
          <StatCard
            icon="🔄"
            label="Active Conversations"
            value={loading ? '…' : a.active_conversations ?? 0}
            color="yellow"
          />
          <StatCard
            icon="📊"
            label="Avg Messages / Conversation"
            value={loading ? '…' : a.avg_messages_per_conversation != null
              ? Number(a.avg_messages_per_conversation).toFixed(1)
              : '—'}
            color="blue"
          />
        </div>

        {/* Recent conversations */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-4 text-sm uppercase tracking-wide">
            Recent Conversations
          </h3>
          {loading ? (
            <p className="text-sm text-gray-400">Loading…</p>
          ) : convos.length === 0 ? (
            <p className="text-sm text-gray-400">No conversations yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                    <th className="pb-2 font-medium">Session</th>
                    <th className="pb-2 font-medium">Channel</th>
                    <th className="pb-2 font-medium">Messages</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {convos.map(c => (
                    <tr key={c.id || c.session_id} className="hover:bg-gray-50 transition-colors">
                      <td className="py-2.5 text-gray-700 font-mono text-xs">
                        {(c.session_id || c.id || '').slice(0, 20)}…
                      </td>
                      <td className="py-2.5 text-gray-500">{c.channel || '—'}</td>
                      <td className="py-2.5 text-gray-700">{c.message_count ?? c.messages?.length ?? '—'}</td>
                      <td className="py-2.5">
                        <Badge variant={
                          c.status === 'active' ? 'success' :
                          c.status === 'escalated' ? 'error' : 'neutral'
                        }>
                          {c.status || 'unknown'}
                        </Badge>
                      </td>
                      <td className="py-2.5 text-gray-400 text-xs">
                        {c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
