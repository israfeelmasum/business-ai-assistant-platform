import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Badge from '../components/Badge';

export default function DataSources() {
  const { api, orgId } = useAuth();

  const [chatbotId, setChatbotId]   = useState(null);

  // Knowledge bases list
  const [kbs, setKbs]             = useState([]);
  const [kbLoading, setKbLoading] = useState(true);
  const [kbError, setKbError]     = useState('');

  // Selected KB to add document to
  const [selectedKbId, setSelectedKbId] = useState('');

  // Add document form
  const [docTitle, setDocTitle]     = useState('');
  const [docContent, setDocContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [submitSuccess, setSubmitSuccess] = useState('');

  // Fetch chatbot list first
  useEffect(() => {
    if (!api || !orgId) return;
    api.get(`/organizations/${orgId}/chatbots`).then(bots => {
      if (bots && bots.length > 0) setChatbotId(bots[0].id);
    }).catch(() => {});
  }, [api, orgId]);

  const loadKbs = useCallback(() => {
    if (!api || !orgId || !chatbotId) return;
    setKbLoading(true);
    setKbError('');
    api.get(`/organizations/${orgId}/chatbots/${chatbotId}/knowledge-bases`)
      .then(data => {
        const list = Array.isArray(data) ? data : data?.knowledge_bases || data?.items || [];
        setKbs(list);
        if (list.length > 0 && !selectedKbId) setSelectedKbId(list[0].id);
      })
      .catch(e => setKbError(e.message))
      .finally(() => setKbLoading(false));
  }, [api, orgId, chatbotId]);

  useEffect(() => { loadKbs(); }, [loadKbs]);

  async function handleAddDocument(e) {
    e.preventDefault();
    if (!docTitle.trim() || !docContent.trim() || !selectedKbId) return;
    setSubmitting(true);
    setSubmitError('');
    setSubmitSuccess('');

    try {
      const formData = new FormData();
      formData.append('title',   docTitle.trim());
      formData.append('content', docContent.trim());

      await api.postForm(
        `/organizations/${orgId}/knowledge-bases/${selectedKbId}/documents/manual`,
        formData
      );

      setDocTitle('');
      setDocContent('');
      setSubmitSuccess('Document added successfully!');
      // Refresh KB list to update document counts
      loadKbs();
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <Header
        title="Data Sources"
        subtitle="Manage knowledge base documents"
      />
      <div className="p-6 lg:p-8 max-w-4xl">
        {kbError && (
          <div className="mb-5 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            {kbError}
          </div>
        )}

        {/* Knowledge bases overview */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
          <h3 className="font-semibold text-gray-900 mb-4">Knowledge Bases</h3>
          {kbLoading ? (
            <p className="text-sm text-gray-400">Loading…</p>
          ) : kbs.length === 0 ? (
            <div className="text-center py-8 text-gray-400 text-sm">
              No knowledge bases found. Create one in the Knowledge page first.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {kbs.map(kb => (
                <div
                  key={kb.id}
                  onClick={() => setSelectedKbId(kb.id)}
                  className={`border rounded-xl p-4 cursor-pointer transition-all
                    ${selectedKbId === kb.id
                      ? 'border-blue-500 bg-blue-50 shadow-sm'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="font-medium text-sm text-gray-800 leading-snug">{kb.name}</h4>
                    {selectedKbId === kb.id && (
                      <span className="w-2 h-2 rounded-full bg-blue-600 flex-shrink-0 mt-1 ml-2" />
                    )}
                  </div>
                  {kb.description && (
                    <p className="text-xs text-gray-400 mb-2 line-clamp-2">{kb.description}</p>
                  )}
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-xs text-gray-500">
                      {kb.document_count ?? kb.documents_count ?? '?'} document(s)
                    </span>
                    <Badge variant={kb.is_active !== false ? 'success' : 'neutral'}>
                      {kb.is_active !== false ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Add document form */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-1">Add Document</h3>
          <p className="text-xs text-gray-400 mb-5">
            Add a new manual document to the selected knowledge base.
          </p>

          {/* KB selector */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Target Knowledge Base
            </label>
            {kbLoading ? (
              <p className="text-sm text-gray-400">Loading…</p>
            ) : kbs.length === 0 ? (
              <p className="text-sm text-gray-400">No knowledge bases available.</p>
            ) : (
              <select
                value={selectedKbId}
                onChange={e => setSelectedKbId(e.target.value)}
                className="w-full max-w-sm px-3 py-2.5 border border-gray-200 rounded-xl text-sm
                           focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                {kbs.map(kb => (
                  <option key={kb.id} value={kb.id}>{kb.name}</option>
                ))}
              </select>
            )}
          </div>

          <form onSubmit={handleAddDocument} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Document Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={docTitle}
                onChange={e => setDocTitle(e.target.value)}
                placeholder="e.g. Refund Policy, Product FAQ…"
                required
                className="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm
                           focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Content <span className="text-red-500">*</span>
              </label>
              <textarea
                value={docContent}
                onChange={e => setDocContent(e.target.value)}
                placeholder="Paste or type the full document text here…"
                required
                rows={10}
                className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm
                           focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y font-mono"
              />
              <p className="text-xs text-gray-400 mt-1">
                {docContent.length} characters
              </p>
            </div>

            {submitError && (
              <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
                {submitError}
              </div>
            )}
            {submitSuccess && (
              <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm text-green-700">
                {submitSuccess}
              </div>
            )}

            <div className="flex items-center gap-3 pt-1">
              <button
                type="submit"
                disabled={submitting || !docTitle.trim() || !docContent.trim() || !selectedKbId}
                className="px-5 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold
                           hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {submitting ? (
                  <span className="flex items-center gap-2">
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Adding…
                  </span>
                ) : 'Add Document'}
              </button>
              <button
                type="button"
                onClick={() => { setDocTitle(''); setDocContent(''); setSubmitError(''); setSubmitSuccess(''); }}
                className="px-4 py-2.5 text-gray-600 border border-gray-200 rounded-xl text-sm hover:bg-gray-50 transition-colors"
              >
                Clear
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
