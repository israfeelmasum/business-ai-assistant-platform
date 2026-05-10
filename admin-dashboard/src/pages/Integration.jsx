import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';

const API_BASE   = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace('/api/v1', '')
  : 'http://localhost:9000';
const WIDGET_URL = `${API_BASE}/chatbot-widget.js`;

function CodeBlock({ code, label, copyKey, copied, onCopy }) {
  return (
    <div className="relative">
      <pre className="bg-gray-900 text-green-300 p-4 rounded-xl text-xs overflow-x-auto leading-relaxed">
        {code}
      </pre>
      <button
        onClick={() => onCopy(code, copyKey)}
        className="absolute top-3 right-3 px-2.5 py-1 bg-white/10 hover:bg-white/20 text-white text-xs rounded-lg transition-colors"
      >
        {copied === copyKey ? 'Copied!' : 'Copy'}
      </button>
    </div>
  );
}

export default function Integration() {
  const { api, orgId } = useAuth();
  const [chatbotId, setChatbotId] = useState(null);
  const [copied, setCopied] = useState('');

  useEffect(() => {
    if (!api || !orgId) return;
    api.get(`/organizations/${orgId}/chatbots`).then(bots => {
      if (bots && bots.length > 0) setChatbotId(bots[0].id);
    }).catch(() => {});
  }, [api, orgId]);

  function copy(text, key) {
    navigator.clipboard.writeText(text).catch(() => {});
    setCopied(key);
    setTimeout(() => setCopied(''), 2000);
  }

  const displayId = chatbotId || 'loading…';

  // Widget embed codes
  const htmlSnippet =
`<script
  src="${WIDGET_URL}"
  data-chatbot-id="${displayId}"
  data-api-url="${API_BASE}/api/v1"
  data-theme="#3B82F6"
  data-title="AI Assistant"
></script>`;

  const reactSnippet =
`import { useEffect } from 'react';

export function ChatWidget() {
  useEffect(() => {
    const script = document.createElement('script');
    script.src = '${WIDGET_URL}';
    script.dataset.chatbotId  = '${displayId}';
    script.dataset.apiUrl     = '${API_BASE}/api/v1';
    script.dataset.theme      = '#3B82F6';
    document.body.appendChild(script);
    return () => document.body.removeChild(script);
  }, []);
  return null;
}`;

  const curlSnippet =
`# Send a chat message via REST API
curl -X POST "${API_BASE}/api/v1/widget/chat" \\
  -H "Content-Type: application/json" \\
  -d '{
    "chatbot_id": "${displayId}",
    "session_id": "unique-session-id",
    "message": "Hello!"
  }'`;

  const widgetConfigSnippet =
`# Get widget configuration
curl "${API_BASE}/api/v1/widget/config?chatbot_id=${displayId}"`;

  return (
    <div>
      <Header
        title="Integration"
        subtitle="Embed the chatbot widget in any website or app"
      />
      <div className="p-6 lg:p-8 max-w-3xl space-y-6">

        {/* Chatbot ID */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-1">Chatbot ID</h3>
          <p className="text-xs text-gray-400 mb-3">Use this ID when embedding the widget or making API calls.</p>
          <div className="flex items-center gap-3">
            <code className="flex-1 bg-gray-100 px-4 py-3 rounded-lg text-sm font-mono text-gray-700 break-all">
              {chatbotId || <span className="text-gray-400 italic">Loading…</span>}
            </code>
            <button
              onClick={() => chatbotId && copy(chatbotId, 'id')}
              disabled={!chatbotId}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
            >
              {copied === 'id' ? 'Copied!' : 'Copy'}
            </button>
          </div>
        </div>

        {/* HTML / Script embed */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-1">HTML Widget Embed</h3>
          <p className="text-sm text-gray-500 mb-4">
            Paste this script tag before the closing <code className="bg-gray-100 px-1 rounded">&lt;/body&gt;</code> tag.
            Works on any HTML page, WordPress, or Shopify site.
          </p>
          <CodeBlock code={htmlSnippet} copyKey="html" copied={copied} onCopy={copy} />
        </div>

        {/* React embed */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-1">React Integration</h3>
          <p className="text-sm text-gray-500 mb-4">
            Drop the <code className="bg-gray-100 px-1 rounded">ChatWidget</code> component anywhere in your React app.
          </p>
          <CodeBlock code={reactSnippet} copyKey="react" copied={copied} onCopy={copy} />
        </div>

        {/* Quick start guide */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Quick Start — REST API</h3>
          <div className="space-y-4">
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">1. Send a chat message</p>
              <CodeBlock code={curlSnippet} copyKey="curl" copied={copied} onCopy={copy} />
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">2. Fetch widget config</p>
              <CodeBlock code={widgetConfigSnippet} copyKey="cfg" copied={copied} onCopy={copy} />
            </div>
          </div>
        </div>

        {/* API documentation links */}
        <div className="bg-blue-50 rounded-xl border border-blue-200 p-5">
          <h3 className="font-semibold text-blue-900 mb-2">Full API Documentation</h3>
          <p className="text-sm text-blue-700 mb-4">
            Explore all endpoints — authentication, conversations, knowledge base, analytics, and more.
          </p>
          <div className="flex flex-wrap gap-3">
            <a
              href={`${API_BASE}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-semibold hover:bg-green-700 transition-colors"
            >
              Swagger UI (/docs)
            </a>
            <a
              href={`${API_BASE}/redoc`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors"
            >
              ReDoc (/redoc)
            </a>
          </div>
        </div>

        {/* Integration checklist */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Integration Checklist</h3>
          <ul className="space-y-2.5 text-sm text-gray-700">
            {[
              'Add Q&A pairs or documents in the Knowledge Base page',
              'Paste the HTML embed snippet into your website',
              'Test by opening your website and sending a message',
              'Monitor conversations in the Conversations page',
              'Handle escalations in the Escalated Chats page',
              'Monitor token usage in Settings',
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-green-100 text-green-600 flex-shrink-0 flex items-center justify-center text-xs font-bold mt-0.5">
                  {i + 1}
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
