import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';

const PERIOD_PRESETS = [
  { label: 'Last 7 days',  days: 7  },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 90 days', days: 90 },
];

function StatCard({ label, value, sub, color = 'blue' }) {
  const colors = {
    blue:   'bg-blue-50  border-blue-100  text-blue-700',
    green:  'bg-green-50 border-green-100 text-green-700',
    amber:  'bg-amber-50 border-amber-100 text-amber-700',
    purple: 'bg-purple-50 border-purple-100 text-purple-700',
    red:    'bg-red-50   border-red-100   text-red-700',
    gray:   'bg-gray-50  border-gray-200  text-gray-700',
  };
  return (
    <div className={`rounded-xl border p-5 ${colors[color]}`}>
      <p className="text-xs font-semibold uppercase tracking-wide opacity-70">{label}</p>
      <p className="text-3xl font-bold mt-1">{value ?? '—'}</p>
      {sub && <p className="text-xs mt-1 opacity-70">{sub}</p>}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="font-semibold text-gray-800 mb-4 text-sm uppercase tracking-wide">{title}</h3>
      {children}
    </div>
  );
}

export default function Analytics() {
  const { api, orgId } = useAuth();

  const [chatbotId, setChatbotId] = useState(null);
  const [chatbots, setChatbots]   = useState([]);

  // Date range
  const [presetDays, setPresetDays] = useState(30);
  const today = new Date();
  const startDate = new Date(today); startDate.setDate(today.getDate() - (presetDays - 1));
  const fmtDate = d => d.toISOString().split('T')[0];

  // Dashboard stats
  const [dash, setDash]     = useState(null);
  const [daily, setDaily]   = useState([]);
  const [loadingDash, setLoadingDash] = useState(false);

  // AI reports
  const [reports, setReports]   = useState([]);
  const [loadingRep, setLoadingRep] = useState(false);
  const [genPeriod, setGenPeriod]   = useState({ type: 'monthly', label: '' });
  const [generating, setGenerating] = useState(false);

  // Load chatbots
  useEffect(() => {
    if (!api || !orgId) return;
    api.get(`/organizations/${orgId}/chatbots`).then(bots => {
      if (Array.isArray(bots) && bots.length > 0) {
        setChatbots(bots);
        setChatbotId(bots[0].id);
      }
    }).catch(() => {});
  }, [api, orgId]);

  // Default period label
  useEffect(() => {
    const now = new Date();
    const ym  = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    setGenPeriod(p => ({ ...p, label: p.type === 'monthly' ? ym : String(now.getFullYear()) }));
  }, []);

  // Load dashboard stats
  const loadDash = useCallback(async () => {
    if (!api || !orgId) return;
    setLoadingDash(true);
    try {
      const start = fmtDate(startDate);
      const end   = fmtDate(today);
      const params = `start=${start}&end=${end}${chatbotId ? `&chatbot_id=${chatbotId}` : ''}`;
      const d = await api.get(`/organizations/${orgId}/analytics/dashboard?${params}`);
      setDash(d);
      if (chatbotId) {
        const dl = await api.get(
          `/organizations/${orgId}/analytics/daily/${chatbotId}?start=${start}&end=${end}`
        ).catch(() => []);
        setDaily(Array.isArray(dl) ? dl : []);
      }
    } catch (e) {
      console.error('analytics load error', e);
    } finally {
      setLoadingDash(false);
    }
  }, [api, orgId, chatbotId, presetDays]);

  useEffect(() => { loadDash(); }, [loadDash]);

  // Load reports
  const loadReports = useCallback(async () => {
    if (!api || !orgId) return;
    setLoadingRep(true);
    try {
      const reps = await api.get(
        `/organizations/${orgId}/analytics/reports?limit=12`
      ).catch(() => []);
      setReports(Array.isArray(reps) ? reps : []);
    } finally {
      setLoadingRep(false);
    }
  }, [api, orgId]);

  useEffect(() => { loadReports(); }, [loadReports]);

  async function generateReport() {
    if (!genPeriod.label.trim()) return alert('Enter a period label first');
    setGenerating(true);
    try {
      const params = `period_type=${genPeriod.type}&period_label=${encodeURIComponent(genPeriod.label)}${chatbotId ? `&chatbot_id=${chatbotId}` : ''}`;
      const rep = await api.post(`/organizations/${orgId}/analytics/reports/generate?${params}`, {});
      setReports(prev => [rep, ...prev.filter(r => r.id !== rep.id)]);
    } catch (err) {
      alert(`Report generation failed: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  }

  // Simple bar chart using divs
  function MiniBar({ rows, xKey, yKey, color = '#3B82F6' }) {
    if (!rows || rows.length === 0) return <p className="text-xs text-gray-400 py-4 text-center">No data</p>;
    const max = Math.max(...rows.map(r => r[yKey] || 0), 1);
    return (
      <div className="flex items-end gap-1 h-28 mt-2">
        {rows.map((r, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-0.5 min-w-0">
            <div
              className="w-full rounded-t-sm transition-all"
              style={{ height: `${Math.max(2, (r[yKey] / max) * 100)}%`, backgroundColor: color }}
              title={`${r[xKey]}: ${r[yKey]}`}
            />
          </div>
        ))}
      </div>
    );
  }

  const pct = (n, d) => (d ? ((n / d) * 100).toFixed(1) : '0') + '%';

  return (
    <div>
      <Header
        title="Analytics"
        subtitle="Chatbot performance insights and AI-generated reports"
      />
      <div className="p-6 lg:p-8 space-y-6">

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={chatbotId || ''}
            onChange={e => setChatbotId(e.target.value || null)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Chatbots</option>
            {chatbots.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {PERIOD_PRESETS.map(p => (
              <button
                key={p.days}
                onClick={() => setPresetDays(p.days)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  presetDays === p.days ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <button
            onClick={loadDash}
            disabled={loadingDash}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50"
          >
            {loadingDash ? 'Loading…' : 'Refresh'}
          </button>
        </div>

        {/* KPI grid */}
        {dash && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            <StatCard label="Total Conversations" value={dash.total_conversations?.toLocaleString()} color="blue" />
            <StatCard label="Total Messages"      value={dash.total_messages?.toLocaleString()} color="purple" />
            <StatCard label="Unique Users"        value={dash.total_unique_users?.toLocaleString()} color="green" />
            <StatCard label="Escalated"
              value={dash.escalated_conversations?.toLocaleString()}
              sub={pct(dash.escalated_conversations, dash.total_conversations) + ' of convs'}
              color="amber" />
            <StatCard label="Resolved"
              value={dash.resolved_conversations?.toLocaleString()}
              sub={pct(dash.resolved_conversations, dash.total_conversations) + ' of convs'}
              color="green" />
            <StatCard label="Avg Confidence"
              value={dash.avg_confidence != null ? (dash.avg_confidence * 100).toFixed(1) + '%' : '—'}
              color={dash.avg_confidence > 0.75 ? 'green' : 'amber'} />
            <StatCard label="Avg Response"
              value={dash.avg_response_ms != null ? `${dash.avg_response_ms}ms` : '—'}
              color="gray" />
            <StatCard label="Tokens Used"
              value={dash.total_tokens_used?.toLocaleString()}
              sub={`~$${(dash.estimated_cost_usd || 0).toFixed(4)}`}
              color="gray" />
          </div>
        )}

        {/* Daily trend charts */}
        {daily.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Section title="Daily Conversations">
              <MiniBar rows={daily} xKey="date" yKey="total_conversations" color="#3B82F6" />
              <div className="flex justify-between mt-1">
                <span className="text-xs text-gray-400">{daily[0]?.date}</span>
                <span className="text-xs text-gray-400">{daily[daily.length - 1]?.date}</span>
              </div>
            </Section>
            <Section title="Daily Messages">
              <MiniBar rows={daily} xKey="date" yKey="total_messages" color="#8B5CF6" />
              <div className="flex justify-between mt-1">
                <span className="text-xs text-gray-400">{daily[0]?.date}</span>
                <span className="text-xs text-gray-400">{daily[daily.length - 1]?.date}</span>
              </div>
            </Section>
            <Section title="Daily Escalations">
              <MiniBar rows={daily} xKey="date" yKey="escalated_count" color="#F59E0B" />
            </Section>
            <Section title="Daily Tokens Used">
              <MiniBar rows={daily} xKey="date" yKey="tokens_used" color="#10B981" />
            </Section>
          </div>
        )}

        {/* Pending escalations alert */}
        {dash && dash.pending_escalations > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
            <span className="text-2xl">🚨</span>
            <div>
              <p className="font-semibold text-red-800 text-sm">
                {dash.pending_escalations} pending escalation{dash.pending_escalations !== 1 ? 's' : ''}
              </p>
              {dash.overdue_escalations > 0 && (
                <p className="text-xs text-red-600">
                  {dash.overdue_escalations} overdue — requires immediate attention
                </p>
              )}
            </div>
            <a href="/escalated" className="ml-auto px-3 py-1.5 bg-red-600 text-white text-xs font-semibold rounded-lg hover:bg-red-700">
              View Now
            </a>
          </div>
        )}

        {/* AI Report Generator */}
        <Section title="AI-Generated Period Reports">
          <div className="flex flex-wrap items-end gap-3 mb-5 pb-5 border-b border-gray-100">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Period Type</label>
              <select
                value={genPeriod.type}
                onChange={e => {
                  const t = e.target.value;
                  const now = new Date();
                  let lbl = '';
                  if (t === 'monthly') lbl = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
                  else if (t === 'yearly') lbl = String(now.getFullYear());
                  else {
                    const yr = now.getFullYear();
                    const wk = Math.ceil(((now - new Date(yr, 0, 1)) / 86400000 + new Date(yr, 0, 1).getDay() + 1) / 7);
                    lbl = `${yr}-W${String(wk).padStart(2, '0')}`;
                  }
                  setGenPeriod({ type: t, label: lbl });
                }}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="yearly">Yearly</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Period Label</label>
              <input
                value={genPeriod.label}
                onChange={e => setGenPeriod(p => ({ ...p, label: e.target.value }))}
                placeholder={genPeriod.type === 'weekly' ? '2026-W15' : genPeriod.type === 'monthly' ? '2026-04' : '2026'}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-32"
              />
            </div>
            <button
              onClick={generateReport}
              disabled={generating}
              className="px-5 py-2 bg-purple-600 text-white text-sm font-semibold rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
            >
              {generating ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Generating…
                </>
              ) : (
                '✨ Generate Report'
              )}
            </button>
          </div>

          {/* Reports list */}
          {loadingRep ? (
            <p className="text-sm text-gray-400 py-4 text-center">Loading reports…</p>
          ) : reports.length === 0 ? (
            <p className="text-sm text-gray-400 py-4 text-center">No reports yet. Generate your first one above.</p>
          ) : (
            <div className="space-y-4">
              {reports.map(rep => (
                <div key={rep.id} className="border border-gray-100 rounded-xl p-5 hover:border-gray-200 transition-colors">
                  <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                          rep.period_type === 'weekly'  ? 'bg-blue-100 text-blue-700' :
                          rep.period_type === 'monthly' ? 'bg-purple-100 text-purple-700' :
                                                          'bg-amber-100 text-amber-700'
                        }`}>
                          {rep.period_type}
                        </span>
                        <h4 className="font-semibold text-gray-800">{rep.period_label}</h4>
                      </div>
                      <p className="text-xs text-gray-400">
                        {rep.period_start} → {rep.period_end} &nbsp;·&nbsp; Generated {new Date(rep.generated_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex gap-4">
                      <div className="text-center">
                        <p className="text-lg font-bold text-gray-800">{rep.total_conversations?.toLocaleString()}</p>
                        <p className="text-xs text-gray-400">Conversations</p>
                      </div>
                      <div className="text-center">
                        <p className="text-lg font-bold text-gray-800">{rep.unique_users?.toLocaleString()}</p>
                        <p className="text-xs text-gray-400">Users</p>
                      </div>
                      <div className="text-center">
                        <p className="text-lg font-bold text-amber-600">
                          {rep.escalation_count} ({(rep.escalation_rate * 100).toFixed(1)}%)
                        </p>
                        <p className="text-xs text-gray-400">Escalated</p>
                      </div>
                    </div>
                  </div>

                  {rep.ai_summary && (
                    <div className="bg-purple-50 rounded-lg p-4 text-sm text-purple-900 leading-relaxed mb-3">
                      <p className="text-xs font-semibold text-purple-600 uppercase mb-1">✨ AI Summary</p>
                      {rep.ai_summary}
                    </div>
                  )}

                  {rep.top_questions && rep.top_questions.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Top Questions</p>
                      <div className="space-y-1">
                        {rep.top_questions.slice(0, 5).map((q, i) => (
                          <div key={i} className="flex items-center justify-between text-sm py-1 border-b border-gray-50">
                            <span className="text-gray-700 truncate mr-4">{q.question}</span>
                            <span className="text-xs text-gray-400 flex-shrink-0">{q.count}×</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {rep.staff_stats && rep.staff_stats.length > 0 && (
                    <div className="mt-3">
                      <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Staff Activity</p>
                      <div className="space-y-1">
                        {rep.staff_stats.map((s, i) => (
                          <div key={i} className="flex items-center justify-between text-sm py-1 border-b border-gray-50">
                            <span className="text-gray-700">{s.name || s.email}</span>
                            <span className="text-xs text-gray-400">{s.messages_sent} messages sent</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Section>
      </div>
    </div>
  );
}
