import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Badge from '../components/Badge';

const API_BASE = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace('/api/v1', '')
  : 'http://localhost:9000';

const TABS = [
  { id: 'general',    label: 'General',         icon: '🤖' },
  { id: 'persona',    label: 'Persona & Chat',  icon: '💬' },
  { id: 'appearance', label: 'Appearance',      icon: '🎨' },
  { id: 'fallback',   label: 'Fallback Contacts', icon: '📞' },
  { id: 'ai',         label: 'AI Model',        icon: '⚡' },
  { id: 'tokens',     label: 'Tokens & Usage',  icon: '🔢' },
  { id: 'account',    label: 'Account',         icon: '👤' },
];

function FieldGroup({ title, children }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      {title && <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wide">{title}</h3>}
      {children}
    </div>
  );
}

function Field({ label, hint, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {hint && <p className="text-xs text-gray-400 mb-1.5">{hint}</p>}
      {children}
    </div>
  );
}

function Input({ value, onChange, placeholder, type = 'text', mono = false, className = '' }) {
  return (
    <input
      type={type}
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className={`w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none
        focus:ring-2 focus:ring-blue-500 ${mono ? 'font-mono' : ''} ${className}`}
    />
  );
}

function Textarea({ value, onChange, rows = 3, placeholder }) {
  return (
    <textarea
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      rows={rows}
      placeholder={placeholder}
      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none
        focus:ring-2 focus:ring-blue-500 resize-y"
    />
  );
}

function Toggle({ checked, onChange, label }) {
  return (
    <label className="flex items-center gap-3 cursor-pointer select-none">
      <div
        onClick={() => onChange(!checked)}
        className={`relative w-10 h-5 rounded-full transition-colors ${
          checked ? 'bg-blue-600' : 'bg-gray-300'
        }`}
      >
        <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
          checked ? 'translate-x-5' : 'translate-x-0.5'
        }`} />
      </div>
      {label && <span className="text-sm text-gray-700">{label}</span>}
    </label>
  );
}

function SaveButton({ saving, saved, onClick }) {
  return (
    <button
      onClick={onClick}
      disabled={saving}
      className="px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg
        hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-2"
    >
      {saving ? (
        <>
          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          Saving…
        </>
      ) : saved ? (
        <>✅ Saved!</>
      ) : (
        'Save Changes'
      )}
    </button>
  );
}

export default function Settings() {
  const { api, orgId, user } = useAuth();

  const [activeTab, setActiveTab] = useState('general');
  const [chatbotId, setChatbotId] = useState(null);
  const [chatbot, setChatbot]     = useState(null);
  const [theme, setTheme]         = useState(null);
  const [persona, setPersona]     = useState(null);
  const [balance, setBalance]     = useState(null);
  const [tokenUsage, setTokenUsage] = useState(null);
  const [modelConfigs, setModelConfigs] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState('');

  // Editable form state
  const [genForm,    setGenForm]    = useState({});
  const [personaForm, setPersonaForm] = useState({});
  const [themeForm,  setThemeForm]  = useState({});
  const [fallbackForm, setFallbackForm] = useState({});

  const [saving, setSaving] = useState('');
  const [saved,  setSaved]  = useState('');

  // Load chatbots
  useEffect(() => {
    if (!api || !orgId) return;
    api.get(`/organizations/${orgId}/chatbots`).then(bots => {
      if (bots?.length > 0) setChatbotId(bots[0].id);
    }).catch(() => {});
  }, [api, orgId]);

  // Load all settings
  useEffect(() => {
    if (!api || !orgId || !chatbotId) return;
    setLoading(true);
    const now   = new Date();
    const year  = now.getFullYear();
    const month = now.getMonth() + 1;

    Promise.all([
      api.get(`/organizations/${orgId}/chatbots/${chatbotId}`).catch(() => null),
      api.get(`/organizations/${orgId}/chatbots/${chatbotId}/theme`).catch(() => null),
      api.get(`/organizations/${orgId}/chatbots/${chatbotId}/persona`).catch(() => null),
      api.get(`/organizations/${orgId}/tokens/balance`).catch(() => null),
      api.get(`/organizations/${orgId}/analytics/token-usage?year=${year}&month=${month}`).catch(() => null),
      api.get(`/organizations/${orgId}/chatbots/${chatbotId}/model-configs`).catch(() => []),
      api.get(`/organizations/${orgId}/chatbots/${chatbotId}/prompts`).catch(() => []),
    ]).then(([bot, th, pers, bal, usage, configs, prompts]) => {
      setChatbot(bot);
      setTheme(th);
      setPersona(pers);
      setBalance(bal);
      setTokenUsage(usage);
      setModelConfigs(Array.isArray(configs) ? configs : []);

      // Seed form state
      setGenForm({
        name:        bot?.name        || '',
        description: bot?.description || '',
        is_active:   bot?.is_active   ?? true,
        channel:     bot?.channel     || 'web',
      });
      const tenantPrompt = Array.isArray(prompts)
        ? prompts.find(p => p.layer === 'tenant')
        : null;
      setPersonaForm({
        persona_name:     pers?.persona_name       || '',
        greeting_message: pers?.greeting_message   || '',
        farewell_message: pers?.farewell_message   || '',
        offline_message:  pers?.offline_message    || '',
        default_language: pers?.default_language   || 'en',
        personality:      pers?.personality        || 'professional',
        system_prompt:    tenantPrompt?.content    || '',
      });
      setThemeForm({
        color_primary:      th?.color_primary      || '#2563EB',
        color_user_bubble:  th?.color_user_bubble  || '#2563EB',
        color_bot_bubble:   th?.color_bot_bubble   || '#F3F4F6',
        color_background:   th?.color_background   || '#FFFFFF',
        color_text:         th?.color_text         || '#111827',
        logo_url:           th?.logo_url           || '',
        welcome_message:    th?.welcome_message    || 'Hello! How can I help you today?',
        position:           th?.position           || 'bottom-right',
        border_radius:      th?.border_radius      ?? 12,
        widget_width:       th?.widget_width       ?? 380,
        widget_height:      th?.widget_height      ?? 600,
        font_family:        th?.font_family        || 'Inter',
      });
      setFallbackForm({
        fallback_whatsapp: th?.fallback_whatsapp || '',
        fallback_email:    th?.fallback_email    || '',
        fallback_phone:    th?.fallback_phone    || '',
        fallback_message:  th?.fallback_message  || 'Our team is here to help. Reach us via:',
      });
    })
    .catch(e => setError(e.message))
    .finally(() => setLoading(false));
  }, [api, orgId, chatbotId]);

  // Generic save helper
  async function saveSection(section) {
    setSaving(section);
    setSaved('');
    try {
      if (section === 'general') {
        await api.patch(`/organizations/${orgId}/chatbots/${chatbotId}`, genForm);
      } else if (section === 'persona') {
        // 1. Save persona fields
        const { system_prompt, ...personaOnly } = personaForm;
        await api.patch(`/organizations/${orgId}/chatbots/${chatbotId}/persona`, personaOnly);
        // 2. Save system prompt as tenant prompt layer if provided
        if (system_prompt && system_prompt.trim()) {
          const existingPrompts = await api.get(`/organizations/${orgId}/chatbots/${chatbotId}/prompts`).catch(() => []);
          const tenantPrompt = Array.isArray(existingPrompts)
            ? existingPrompts.find(p => p.layer === 'tenant')
            : null;
          if (tenantPrompt) {
            await api.patch(`/organizations/${orgId}/chatbots/${chatbotId}/prompts/${tenantPrompt.id}`,
              { content: system_prompt });
          } else {
            await api.post(`/organizations/${orgId}/chatbots/${chatbotId}/prompts`,
              { layer: 'tenant', content: system_prompt, is_active: true });
          }
        }
      } else if (section === 'appearance') {
        await api.patch(`/organizations/${orgId}/chatbots/${chatbotId}/theme`, themeForm);
      } else if (section === 'fallback') {
        await api.patch(`/organizations/${orgId}/chatbots/${chatbotId}/theme`, fallbackForm);
      }
      setSaved(section);
      setTimeout(() => setSaved(''), 3000);
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setSaving('');
    }
  }

  const chatCfg  = modelConfigs.find(c => c.task === 'chat') || {};
  const embedCfg = modelConfigs.find(c => c.task === 'embedding') || {};

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div>
      <Header title="Settings" subtitle="Manage your chatbot configuration" />
      <div className="p-6 lg:p-8 max-w-4xl">
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Tab bar */}
        <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-6 overflow-x-auto">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'bg-white text-blue-700 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <span>{tab.icon}</span> {tab.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-center py-16 text-gray-400">
            <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            Loading settings…
          </div>
        ) : (
          <>
            {/* ── GENERAL ── */}
            {activeTab === 'general' && (
              <div className="space-y-4">
                <FieldGroup title="Chatbot Details">
                  <Field label="Name">
                    <Input value={genForm.name} onChange={v => setGenForm(f => ({ ...f, name: v }))} placeholder="My Chatbot" />
                  </Field>
                  <Field label="Description">
                    <Textarea value={genForm.description} onChange={v => setGenForm(f => ({ ...f, description: v }))} placeholder="What does this chatbot do?" />
                  </Field>
                  <Field label="Status">
                    <Toggle checked={genForm.is_active} onChange={v => setGenForm(f => ({ ...f, is_active: v }))} label={genForm.is_active ? 'Active — chatbot is live' : 'Inactive — chatbot is offline'} />
                  </Field>
                  <Field label="Chatbot ID" hint="Read-only. Use in API calls.">
                    <Input value={chatbotId} onChange={() => {}} mono />
                  </Field>
                </FieldGroup>
                <div className="flex justify-end">
                  <SaveButton saving={saving === 'general'} saved={saved === 'general'} onClick={() => saveSection('general')} />
                </div>
              </div>
            )}

            {/* ── PERSONA ── */}
            {activeTab === 'persona' && (
              <div className="space-y-4">
                <FieldGroup title="Persona Settings">
                  <Field label="Display Name" hint="Name shown to users in the chat widget">
                    <Input value={personaForm.persona_name} onChange={v => setPersonaForm(f => ({ ...f, persona_name: v }))} placeholder="Aisha" />
                  </Field>
                  <Field label="Greeting Message" hint="First message shown when the chat widget opens">
                    <Textarea value={personaForm.greeting_message} onChange={v => setPersonaForm(f => ({ ...f, greeting_message: v }))} rows={2} placeholder="Hi! I'm Aisha. How can I help you today?" />
                  </Field>
                  <Field label="Farewell Message" hint="Shown when the conversation is resolved">
                    <Textarea value={personaForm.farewell_message} onChange={v => setPersonaForm(f => ({ ...f, farewell_message: v }))} rows={2} placeholder="Thank you for chatting! Have a great day." />
                  </Field>
                  <Field label="Offline Message" hint="Shown outside business hours">
                    <Textarea value={personaForm.offline_message} onChange={v => setPersonaForm(f => ({ ...f, offline_message: v }))} rows={2} placeholder="We're currently offline. Please leave a message." />
                  </Field>
                  <Field label="Default Language">
                    <select
                      value={personaForm.default_language || 'en'}
                      onChange={e => setPersonaForm(f => ({ ...f, default_language: e.target.value }))}
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="en">English</option>
                      <option value="bn">Bengali (বাংলা)</option>
                      <option value="ar">Arabic (العربية)</option>
                      <option value="hi">Hindi (हिन्दी)</option>
                      <option value="fr">French</option>
                      <option value="de">German</option>
                      <option value="es">Spanish</option>
                    </select>
                  </Field>
                  <Field label="Personality">
                    <select
                      value={personaForm.personality || 'professional'}
                      onChange={e => setPersonaForm(f => ({ ...f, personality: e.target.value }))}
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="professional">Professional</option>
                      <option value="friendly">Friendly</option>
                      <option value="formal">Formal</option>
                      <option value="playful">Playful</option>
                      <option value="empathetic">Empathetic</option>
                    </select>
                  </Field>
                </FieldGroup>

                <FieldGroup title="System Prompt">
                  <Field
                    label="System Prompt (Tenant Layer)"
                    hint="Custom instructions injected into the AI prompt after the foundation layer. Define what the bot should focus on, what it must never do, and any business-specific rules."
                  >
                    <Textarea
                      value={personaForm.system_prompt || ''}
                      onChange={v => setPersonaForm(f => ({ ...f, system_prompt: v }))}
                      rows={10}
                      placeholder={`Example:\n- Only answer questions about ICT Bangladesh courses and enrollment.\n- Never discuss competitor platforms.\n- Always end responses with the support contact if the user seems frustrated.`}
                    />
                  </Field>
                  <p className="text-xs text-gray-400">
                    This is stored as a <strong>tenant</strong> prompt layer and merged with the AI foundation rules at runtime.
                  </p>
                </FieldGroup>

                <div className="flex justify-end">
                  <SaveButton saving={saving === 'persona'} saved={saved === 'persona'} onClick={() => saveSection('persona')} />
                </div>
              </div>
            )}

            {/* ── APPEARANCE ── */}
            {activeTab === 'appearance' && (
              <div className="space-y-4">
                <FieldGroup title="Branding">
                  <Field label="Logo URL" hint="HTTPS URL to your logo image (PNG/SVG, recommended 48×48px)">
                    <Input value={themeForm.logo_url} onChange={v => setThemeForm(f => ({ ...f, logo_url: v }))} placeholder="https://example.com/logo.png" />
                  </Field>
                  <Field label="Welcome Message" hint="First message the bot sends when chat opens">
                    <Textarea value={themeForm.welcome_message} onChange={v => setThemeForm(f => ({ ...f, welcome_message: v }))} rows={2} placeholder="Hello! How can I help you today?" />
                  </Field>
                </FieldGroup>
                <FieldGroup title="Colors">
                  <div className="grid grid-cols-2 gap-4">
                    {[
                      { key: 'color_primary',     label: 'Primary / Header'   },
                      { key: 'color_user_bubble',  label: 'User Bubble'       },
                      { key: 'color_bot_bubble',   label: 'Bot Bubble'        },
                      { key: 'color_background',   label: 'Background'        },
                      { key: 'color_text',         label: 'Text'              },
                    ].map(({ key, label }) => (
                      <div key={key} className="flex items-center gap-3">
                        <input
                          type="color"
                          value={themeForm[key] || '#000000'}
                          onChange={e => setThemeForm(f => ({ ...f, [key]: e.target.value }))}
                          className="w-10 h-10 rounded-lg border border-gray-200 cursor-pointer p-0.5"
                        />
                        <div>
                          <p className="text-sm text-gray-700">{label}</p>
                          <p className="text-xs font-mono text-gray-400">{themeForm[key]}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </FieldGroup>
                <FieldGroup title="Widget Dimensions">
                  <div className="grid grid-cols-2 gap-4">
                    <Field label="Width (px)">
                      <Input value={themeForm.widget_width} onChange={v => setThemeForm(f => ({ ...f, widget_width: Number(v) }))} type="number" />
                    </Field>
                    <Field label="Height (px)">
                      <Input value={themeForm.widget_height} onChange={v => setThemeForm(f => ({ ...f, widget_height: Number(v) }))} type="number" />
                    </Field>
                    <Field label="Border Radius (px)">
                      <Input value={themeForm.border_radius} onChange={v => setThemeForm(f => ({ ...f, border_radius: Number(v) }))} type="number" />
                    </Field>
                    <Field label="Position">
                      <select
                        value={themeForm.position || 'bottom-right'}
                        onChange={e => setThemeForm(f => ({ ...f, position: e.target.value }))}
                        className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="bottom-right">Bottom Right</option>
                        <option value="bottom-left">Bottom Left</option>
                        <option value="top-right">Top Right</option>
                        <option value="top-left">Top Left</option>
                      </select>
                    </Field>
                  </div>
                </FieldGroup>
                <div className="flex justify-end">
                  <SaveButton saving={saving === 'appearance'} saved={saved === 'appearance'} onClick={() => saveSection('appearance')} />
                </div>
              </div>
            )}

            {/* ── FALLBACK CONTACTS ── */}
            {activeTab === 'fallback' && (
              <div className="space-y-4">
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
                  <strong>Fallback Contacts</strong> — When the AI escalates a conversation or fails to answer (e.g. low confidence), the widget shows a contact card so the user can reach a human directly.
                </div>
                <FieldGroup title="Contact Details">
                  <Field label="WhatsApp Number" hint="Include country code, e.g. +8801XXXXXXXXX">
                    <Input value={fallbackForm.fallback_whatsapp} onChange={v => setFallbackForm(f => ({ ...f, fallback_whatsapp: v }))} placeholder="+8801700000000" />
                  </Field>
                  <Field label="Email Address">
                    <Input value={fallbackForm.fallback_email} onChange={v => setFallbackForm(f => ({ ...f, fallback_email: v }))} placeholder="support@yourcompany.com" />
                  </Field>
                  <Field label="Phone Number">
                    <Input value={fallbackForm.fallback_phone} onChange={v => setFallbackForm(f => ({ ...f, fallback_phone: v }))} placeholder="+8809613XXXXXX" />
                  </Field>
                  <Field label="Message shown to user" hint="Short line displayed above the contact options">
                    <Textarea value={fallbackForm.fallback_message} onChange={v => setFallbackForm(f => ({ ...f, fallback_message: v }))} rows={2} placeholder="Our team is here to help. Reach us via:" />
                  </Field>
                </FieldGroup>
                {/* Preview card */}
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-3">Preview (what users see)</p>
                  <div className="border border-dashed border-amber-300 rounded-xl p-4 bg-amber-50 max-w-xs">
                    <p className="text-sm text-amber-800 font-medium mb-3">
                      {fallbackForm.fallback_message || 'Our team is here to help. Reach us via:'}
                    </p>
                    {fallbackForm.fallback_whatsapp && (
                      <a href={`https://wa.me/${fallbackForm.fallback_whatsapp.replace(/[^0-9]/g,'')}`}
                         className="flex items-center gap-2 mb-2 px-3 py-2 bg-green-600 text-white rounded-lg text-sm font-medium">
                        💬 WhatsApp: {fallbackForm.fallback_whatsapp}
                      </a>
                    )}
                    {fallbackForm.fallback_email && (
                      <a href={`mailto:${fallbackForm.fallback_email}`}
                         className="flex items-center gap-2 mb-2 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">
                        ✉️ {fallbackForm.fallback_email}
                      </a>
                    )}
                    {fallbackForm.fallback_phone && (
                      <a href={`tel:${fallbackForm.fallback_phone}`}
                         className="flex items-center gap-2 px-3 py-2 bg-gray-700 text-white rounded-lg text-sm font-medium">
                        📞 {fallbackForm.fallback_phone}
                      </a>
                    )}
                    {!fallbackForm.fallback_whatsapp && !fallbackForm.fallback_email && !fallbackForm.fallback_phone && (
                      <p className="text-xs text-gray-400 italic">No contacts configured yet.</p>
                    )}
                  </div>
                </div>
                <div className="flex justify-end">
                  <SaveButton saving={saving === 'fallback'} saved={saved === 'fallback'} onClick={() => saveSection('fallback')} />
                </div>
              </div>
            )}

            {/* ── AI MODEL ── */}
            {activeTab === 'ai' && (
              <div className="space-y-4">
                <FieldGroup title="AI Model Configuration">
                  {modelConfigs.length === 0 ? (
                    <p className="text-sm text-gray-400">No model configs found. Configure via API or contact support.</p>
                  ) : (
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Provider</p>
                          <p className="text-sm text-gray-800">
                            {chatCfg.provider_source === 'org_custom' ? 'Ollama (Self-hosted)' : chatCfg.provider_source || '—'}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Chat Model</p>
                          <p className="text-sm font-mono text-gray-800">{chatCfg.model_id || '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Embedding Model</p>
                          <p className="text-sm font-mono text-gray-800">{embedCfg.model_id || '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Temperature</p>
                          <p className="text-sm text-gray-800">{chatCfg.parameters?.temperature ?? '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Max Tokens</p>
                          <p className="text-sm text-gray-800">{chatCfg.parameters?.max_tokens ?? '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Vision Model</p>
                          <p className="text-sm font-mono text-gray-800">qwen2.5vl:latest</p>
                        </div>
                      </div>
                      <div className="mt-4 pt-4 border-t border-gray-100">
                        <p className="text-xs text-gray-400">To change model configurations, use the API endpoint:</p>
                        <code className="text-xs font-mono bg-gray-50 px-3 py-2 rounded-lg block mt-1 text-gray-600">
                          PATCH /organizations/{'{org_id}'}/chatbots/{'{chatbot_id}'}/model-configs/{'{config_id}'}
                        </code>
                      </div>
                    </>
                  )}
                </FieldGroup>
              </div>
            )}

            {/* ── TOKENS & USAGE ── */}
            {activeTab === 'tokens' && (
              <div className="space-y-4">
                <FieldGroup title="Token Balance">
                  {!balance ? (
                    <p className="text-sm text-gray-400">No balance information available.</p>
                  ) : (
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                      <div className="bg-blue-50 rounded-xl p-4 text-center col-span-2 sm:col-span-1">
                        <p className="text-3xl font-bold text-blue-700">{balance.balance?.toLocaleString() ?? '—'}</p>
                        <p className="text-xs text-blue-600 mt-1">Available Tokens</p>
                      </div>
                      {balance.plan && (
                        <div className="bg-purple-50 rounded-xl p-4 text-center">
                          <p className="text-lg font-bold text-purple-700 capitalize">{balance.plan}</p>
                          <p className="text-xs text-purple-600 mt-1">Current Plan</p>
                        </div>
                      )}
                      {balance.expires_at && (
                        <div className="bg-gray-50 rounded-xl p-4 text-center">
                          <p className="text-sm font-bold text-gray-700">
                            {new Date(balance.expires_at).toLocaleDateString()}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">Expires</p>
                        </div>
                      )}
                    </div>
                  )}
                </FieldGroup>
                <FieldGroup title="Usage This Month">
                  {!tokenUsage ? (
                    <p className="text-sm text-gray-400">No usage data available.</p>
                  ) : (
                    <>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                        {[
                          { label: 'Total Tokens',      value: tokenUsage.total_tokens },
                          { label: 'Estimated Cost',     value: tokenUsage.estimated_cost_usd != null ? `$${Number(tokenUsage.estimated_cost_usd).toFixed(4)}` : null, raw: true },
                        ].map(({ label, value, raw }) => value != null && (
                          <div key={label} className="bg-gray-50 rounded-xl p-4">
                            <p className="text-xl font-bold text-gray-800">{raw ? value : Number(value).toLocaleString()}</p>
                            <p className="text-xs text-gray-500 mt-1">{label}</p>
                          </div>
                        ))}
                      </div>
                      {tokenUsage.by_action && Object.keys(tokenUsage.by_action).length > 0 && (
                        <div className="mt-4">
                          <p className="text-xs font-semibold text-gray-500 uppercase mb-2">By Action</p>
                          <div className="space-y-1">
                            {Object.entries(tokenUsage.by_action).map(([action, count]) => (
                              <div key={action} className="flex justify-between items-center py-1.5 border-b border-gray-50">
                                <span className="text-sm text-gray-600 capitalize">{action.replace(/_/g, ' ')}</span>
                                <span className="text-sm font-semibold text-gray-800">{Number(count).toLocaleString()}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </FieldGroup>
              </div>
            )}

            {/* ── ACCOUNT ── */}
            {activeTab === 'account' && (
              <div className="space-y-4">
                <FieldGroup title="Your Account">
                  <div className="space-y-3">
                    {[
                      { label: 'Full Name', value: user?.full_name },
                      { label: 'Email',     value: user?.email, mono: true },
                      { label: 'Role',      value: user?.role },
                      { label: 'Org ID',    value: orgId, mono: true },
                    ].map(({ label, value, mono }) => (
                      <div key={label} className="flex flex-col sm:flex-row sm:items-center py-3 border-b border-gray-100 last:border-0">
                        <p className="text-sm text-gray-500 sm:w-32 flex-shrink-0">{label}</p>
                        <p className={`text-sm font-medium text-gray-800 ${mono ? 'font-mono break-all' : ''}`}>{value ?? '—'}</p>
                      </div>
                    ))}
                  </div>
                </FieldGroup>
                <FieldGroup title="API Documentation">
                  <div className="flex flex-wrap gap-3">
                    <a href={`${API_BASE}/docs`} target="_blank" rel="noopener noreferrer"
                       className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg font-semibold hover:bg-green-700 transition-colors">
                      Swagger UI
                    </a>
                    <a href={`${API_BASE}/redoc`} target="_blank" rel="noopener noreferrer"
                       className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg font-semibold hover:bg-blue-700 transition-colors">
                      ReDoc
                    </a>
                  </div>
                </FieldGroup>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
