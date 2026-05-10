import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Badge from '../components/Badge';

function SectionTitle({ children }) {
  return <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">{children}</h3>;
}

// Drag handle icon
function DragHandle() {
  return (
    <svg className="w-4 h-4 text-gray-300 cursor-grab active:cursor-grabbing flex-shrink-0"
      viewBox="0 0 20 20" fill="currentColor">
      <circle cx="7" cy="6"  r="1.5" /><circle cx="13" cy="6"  r="1.5" />
      <circle cx="7" cy="10" r="1.5" /><circle cx="13" cy="10" r="1.5" />
      <circle cx="7" cy="14" r="1.5" /><circle cx="13" cy="14" r="1.5" />
    </svg>
  );
}

export default function Knowledge() {
  const { api, orgId } = useAuth();

  const [chatbotId, setChatbotId] = useState(null);
  const [kbs, setKbs]             = useState([]);
  const [kbLoading, setKbLoading] = useState(true);
  const [kbError, setKbError]     = useState('');
  const [selectedKb, setSelectedKb] = useState(null);

  // Create KB
  const [showCreateKb, setShowCreateKb] = useState(false);
  const [newKbName, setNewKbName]       = useState('');
  const [newKbDesc, setNewKbDesc]       = useState('');
  const [creatingKb, setCreatingKb]     = useState(false);
  const [createKbError, setCreateKbError] = useState('');

  // Q&A state
  const [qaPairs, setQaPairs]       = useState([]);
  const [qaLoading, setQaLoading]   = useState(false);
  const [qaError, setQaError]       = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');

  // Add Q&A form
  const [showAddQa, setShowAddQa]   = useState(false);
  const [newQ, setNewQ]             = useState('');
  const [newA, setNewA]             = useState('');
  const [newCat, setNewCat]         = useState('');
  const [addingQa, setAddingQa]     = useState(false);
  const [addQaError, setAddQaError] = useState('');

  // Edit Q&A
  const [editingId, setEditingId]   = useState(null);
  const [editForm, setEditForm]     = useState({});
  const [savingEdit, setSavingEdit] = useState(false);

  // Drag-to-reorder
  const dragItem    = useRef(null);
  const dragOver    = useRef(null);
  const [reordering, setReordering] = useState(false);

  // Bulk upload
  const uploadInputRef              = useRef(null);
  const [showUpload, setShowUpload] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadClear, setUploadClear] = useState(false);
  const [uploading, setUploading]   = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError]   = useState('');

  // Fetch chatbot ID
  useEffect(() => {
    if (!api || !orgId) return;
    api.get(`/organizations/${orgId}/chatbots`).then(bots => {
      if (bots?.length > 0) setChatbotId(bots[0].id);
    }).catch(() => {});
  }, [api, orgId]);

  // Load KBs
  function loadKbs() {
    if (!api || !orgId || !chatbotId) return;
    setKbLoading(true);
    api.get(`/organizations/${orgId}/chatbots/${chatbotId}/knowledge-bases`)
      .then(data => setKbs(Array.isArray(data) ? data : data?.items || []))
      .catch(e => setKbError(e.message))
      .finally(() => setKbLoading(false));
  }
  useEffect(() => { loadKbs(); }, [api, orgId, chatbotId]);

  // Load Q&A pairs
  function loadQaPairs(kbId) {
    if (!kbId || !api || !orgId) return;
    setQaLoading(true);
    const catParam = categoryFilter ? `&category=${encodeURIComponent(categoryFilter)}` : '';
    api.get(`/organizations/${orgId}/knowledge-bases/${kbId}/qa-pairs?limit=500${catParam}`)
      .then(data => setQaPairs(Array.isArray(data) ? data : data?.items || []))
      .catch(e => setQaError(e.message))
      .finally(() => setQaLoading(false));
  }
  useEffect(() => { if (selectedKb) loadQaPairs(selectedKb.id); }, [selectedKb, api, orgId, categoryFilter]);

  async function createKb(e) {
    e.preventDefault();
    if (!newKbName.trim()) return;
    setCreatingKb(true);
    setCreateKbError('');
    try {
      const kb = await api.post(
        `/organizations/${orgId}/chatbots/${chatbotId}/knowledge-bases`,
        { name: newKbName.trim(), description: newKbDesc.trim() }
      );
      setKbs(prev => [...prev, kb]);
      setNewKbName(''); setNewKbDesc(''); setShowCreateKb(false);
    } catch (e) {
      setCreateKbError(e.message);
    } finally {
      setCreatingKb(false);
    }
  }

  async function addQaPair(e) {
    e.preventDefault();
    if (!newQ.trim() || !newA.trim() || !selectedKb) return;
    setAddingQa(true);
    setAddQaError('');
    try {
      const pair = await api.post(
        `/organizations/${orgId}/knowledge-bases/${selectedKb.id}/qa-pairs`,
        {
          question: newQ.trim(), answer: newA.trim(),
          category: newCat.trim() || undefined,
          sort_order: qaPairs.length,
        }
      );
      setQaPairs(prev => [...prev, pair]);
      setNewQ(''); setNewA(''); setNewCat(''); setShowAddQa(false);
    } catch (e) {
      setAddQaError(e.message);
    } finally {
      setAddingQa(false);
    }
  }

  function startEdit(pair) {
    setEditingId(pair.id);
    setEditForm({ question: pair.question, answer: pair.answer, category: pair.category || '', is_active: pair.is_active });
  }

  async function saveEdit(pairId) {
    setSavingEdit(true);
    try {
      const updated = await api.patch(
        `/organizations/${orgId}/knowledge-bases/${selectedKb.id}/qa-pairs/${pairId}`,
        editForm
      );
      setQaPairs(prev => prev.map(p => p.id === pairId ? { ...p, ...updated } : p));
      setEditingId(null);
    } catch (err) {
      alert(`Update failed: ${err.message}`);
    } finally {
      setSavingEdit(false);
    }
  }

  async function deleteQaPair(pairId) {
    if (!window.confirm('Delete this Q&A pair?')) return;
    try {
      await api.delete(`/organizations/${orgId}/knowledge-bases/${selectedKb.id}/qa-pairs/${pairId}`);
      setQaPairs(prev => prev.filter(p => p.id !== pairId));
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  }

  // ── Drag-to-reorder ──────────────────────────────────────────────────────────
  function onDragStart(i) { dragItem.current = i; }
  function onDragEnter(i) { dragOver.current = i; }

  async function onDragEnd() {
    if (dragItem.current === null || dragOver.current === null) return;
    const from = dragItem.current;
    const to   = dragOver.current;
    dragItem.current = null;
    dragOver.current = null;
    if (from === to) return;

    const reordered = [...qaPairs];
    const [moved]   = reordered.splice(from, 1);
    reordered.splice(to, 0, moved);
    // Assign sequential sort_order
    const withOrder = reordered.map((p, idx) => ({ ...p, sort_order: idx }));
    setQaPairs(withOrder);

    // Persist
    setReordering(true);
    try {
      await api.patch(
        `/organizations/${orgId}/knowledge-bases/${selectedKb.id}/qa-pairs/reorder`,
        { items: withOrder.map(p => ({ id: p.id, sort_order: p.sort_order })) }
      );
    } catch (err) {
      // Silently revert on failure
      loadQaPairs(selectedKb.id);
    } finally {
      setReordering(false);
    }
  }

  // ── Bulk upload handler ──────────────────────────────────────────────────────
  async function handleBulkUpload(e) {
    e.preventDefault();
    if (!uploadFile || !selectedKb) return;
    setUploading(true);
    setUploadError('');
    setUploadResult(null);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('clear_existing', uploadClear ? 'true' : 'false');
      const token = localStorage.getItem('token');
      const resp = await fetch(
        `/api/v1/organizations/${orgId}/knowledge-bases/${selectedKb.id}/training-data/upload`,
        { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: formData }
      );
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Upload failed');
      setUploadResult(data);
      setUploadFile(null);
      if (uploadInputRef.current) uploadInputRef.current.value = '';
      loadQaPairs(selectedKb.id);
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  }

  // ── Category grouping ────────────────────────────────────────────────────────
  const allCategories = [...new Set(qaPairs.map(p => p.category || 'Uncategorized'))];
  const grouped = allCategories.map(cat => ({
    cat,
    pairs: qaPairs.filter(p => (p.category || 'Uncategorized') === cat),
  }));

  return (
    <div>
      <Header title="Knowledge Base" subtitle="Manage knowledge bases and Q&A pairs for your chatbot" />
      <div className="p-6 lg:p-8">
        <div className="flex gap-6 min-h-[500px]">

          {/* ── Left: KB list ── */}
          <div className="w-64 flex-shrink-0">
            <div className="flex items-center justify-between mb-3">
              <SectionTitle>Knowledge Bases</SectionTitle>
              <button onClick={() => setShowCreateKb(v => !v)}
                className="text-xs text-blue-600 font-semibold hover:underline">
                + New
              </button>
            </div>

            {showCreateKb && (
              <form onSubmit={createKb} className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4 space-y-2">
                <p className="text-xs font-semibold text-blue-800 mb-1">New Knowledge Base</p>
                <input value={newKbName} onChange={e => setNewKbName(e.target.value)}
                  placeholder="Name *" required
                  className="w-full px-3 py-2 text-sm border border-blue-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white" />
                <textarea value={newKbDesc} onChange={e => setNewKbDesc(e.target.value)}
                  placeholder="Description (optional)" rows={2}
                  className="w-full px-3 py-2 text-sm border border-blue-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white resize-none" />
                {createKbError && <p className="text-xs text-red-600">{createKbError}</p>}
                <div className="flex gap-2">
                  <button type="submit" disabled={creatingKb || !newKbName.trim()}
                    className="flex-1 py-1.5 bg-blue-600 text-white text-xs rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50">
                    {creatingKb ? 'Creating…' : 'Create'}
                  </button>
                  <button type="button" onClick={() => setShowCreateKb(false)}
                    className="flex-1 py-1.5 bg-white text-gray-600 text-xs rounded-lg font-semibold border border-gray-200 hover:bg-gray-50">
                    Cancel
                  </button>
                </div>
              </form>
            )}

            {kbError && <p className="text-xs text-red-600 mb-3">{kbError}</p>}
            {kbLoading ? (
              <p className="text-sm text-gray-400">Loading…</p>
            ) : kbs.length === 0 ? (
              <p className="text-sm text-gray-400">No knowledge bases yet.</p>
            ) : (
              <div className="space-y-1">
                {kbs.map(kb => (
                  <button key={kb.id} onClick={() => { setSelectedKb(kb); setCategoryFilter(''); }}
                    className={`w-full text-left px-3 py-3 rounded-xl transition-colors text-sm border
                      ${selectedKb?.id === kb.id
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'}`}>
                    <p className="font-medium truncate">{kb.name}</p>
                    {kb.description && (
                      <p className={`text-xs mt-0.5 truncate ${selectedKb?.id === kb.id ? 'text-blue-200' : 'text-gray-400'}`}>
                        {kb.description}
                      </p>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* ── Right: Q&A pairs ── */}
          <div className="flex-1 bg-white rounded-xl border border-gray-200 p-5 min-w-0">
            {!selectedKb ? (
              <div className="h-full flex items-center justify-center text-gray-300">
                <div className="text-center">
                  <svg className="w-12 h-12 mx-auto mb-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  <p className="text-sm">Select a knowledge base to manage Q&amp;A pairs</p>
                </div>
              </div>
            ) : (
              <>
                {/* Toolbar */}
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                  <div>
                    <h3 className="font-semibold text-gray-900">{selectedKb.name}</h3>
                    <p className="text-xs text-gray-400">
                      {qaPairs.length} Q&amp;A pair{qaPairs.length !== 1 ? 's' : ''}
                      {reordering && <span className="ml-2 text-blue-500">Saving order…</span>}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {allCategories.length > 1 && (
                      <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}
                        className="px-3 py-1.5 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <option value="">All Categories</option>
                        {allCategories.map(c => <option key={c} value={c === 'Uncategorized' ? '' : c}>{c}</option>)}
                      </select>
                    )}
                    <button onClick={() => { setShowAddQa(v => !v); setShowUpload(false); }}
                      className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg font-semibold hover:bg-blue-700">
                      + Add Q&amp;A
                    </button>
                    <button onClick={() => { setShowUpload(v => !v); setShowAddQa(false); setUploadResult(null); setUploadError(''); }}
                      className="px-3 py-1.5 bg-green-600 text-white text-xs rounded-lg font-semibold hover:bg-green-700 flex items-center gap-1">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
                      </svg>
                      Bulk Upload
                    </button>
                  </div>
                </div>

                {/* Bulk upload form */}
                {showUpload && (
                  <form onSubmit={handleBulkUpload}
                    className="bg-green-50 border border-green-200 rounded-xl p-4 mb-5 space-y-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-xs font-semibold text-green-900">Bulk Upload Training Data</p>
                        <p className="text-xs text-green-700 mt-0.5">
                          Upload an Excel (.xlsx) or CSV file. Required columns: <strong>question</strong> + <strong>answer</strong>.
                          Optional: category, sub-category, relevant questions, linkable suggestion.
                        </p>
                      </div>
                      <a href="/training_template.xlsx" download
                        className="text-xs text-green-700 underline whitespace-nowrap ml-4 hidden">
                        Download template
                      </a>
                    </div>
                    <input ref={uploadInputRef} type="file" accept=".xlsx,.xls,.csv"
                      onChange={e => { setUploadFile(e.target.files[0] || null); setUploadResult(null); }}
                      className="block w-full text-xs text-gray-700 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-green-100 file:text-green-800 hover:file:bg-green-200 cursor-pointer" />
                    <label className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer select-none">
                      <input type="checkbox" checked={uploadClear} onChange={e => setUploadClear(e.target.checked)}
                        className="rounded" />
                      <span>Clear all existing Q&amp;A pairs before uploading</span>
                    </label>
                    {uploadError && <p className="text-xs text-red-600">{uploadError}</p>}
                    {uploadResult && (
                      <div className="bg-green-100 border border-green-300 rounded-lg p-3 text-xs text-green-800">
                        ✅ <strong>{uploadResult.inserted}</strong> rows inserted,{' '}
                        <strong>{uploadResult.embedded}</strong> embedded
                        {uploadResult.skipped > 0 && `, ${uploadResult.skipped} skipped`}.
                      </div>
                    )}
                    <div className="flex gap-2">
                      <button type="submit" disabled={uploading || !uploadFile}
                        className="px-4 py-1.5 bg-green-600 text-white text-xs rounded-lg font-semibold hover:bg-green-700 disabled:opacity-50">
                        {uploading ? 'Uploading & embedding…' : 'Upload'}
                      </button>
                      <button type="button" onClick={() => { setShowUpload(false); setUploadFile(null); setUploadResult(null); }}
                        className="px-4 py-1.5 border border-gray-200 text-gray-600 text-xs rounded-lg hover:bg-gray-50">
                        Cancel
                      </button>
                    </div>
                  </form>
                )}

                {/* Add form */}
                {showAddQa && (
                  <form onSubmit={addQaPair} className="bg-gray-50 border border-gray-200 rounded-xl p-4 mb-5 space-y-3">
                    <p className="text-xs font-semibold text-gray-700">New Q&amp;A Pair</p>
                    <input value={newQ} onChange={e => setNewQ(e.target.value)}
                      placeholder="Question *" required
                      className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white" />
                    <textarea value={newA} onChange={e => setNewA(e.target.value)}
                      placeholder="Answer *" required rows={3}
                      className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white resize-y" />
                    <input value={newCat} onChange={e => setNewCat(e.target.value)}
                      placeholder="Category (optional, e.g. Enrollment, Pricing)"
                      className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white" />
                    {addQaError && <p className="text-xs text-red-600">{addQaError}</p>}
                    <div className="flex gap-2">
                      <button type="submit" disabled={addingQa || !newQ.trim() || !newA.trim()}
                        className="px-4 py-1.5 bg-blue-600 text-white text-xs rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50">
                        {addingQa ? 'Adding…' : 'Add Pair'}
                      </button>
                      <button type="button" onClick={() => setShowAddQa(false)}
                        className="px-4 py-1.5 bg-white text-gray-600 text-xs rounded-lg font-semibold border border-gray-200 hover:bg-gray-50">
                        Cancel
                      </button>
                    </div>
                  </form>
                )}

                {qaError && <p className="text-sm text-red-600 mb-3">{qaError}</p>}

                {qaLoading ? (
                  <p className="text-sm text-gray-400">Loading Q&amp;A pairs…</p>
                ) : qaPairs.length === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-8">No Q&amp;A pairs yet. Add one above.</p>
                ) : (
                  <div className="space-y-5 overflow-y-auto max-h-[60vh]">
                    {grouped.map(({ cat, pairs }) => (
                      <div key={cat}>
                        {/* Category header */}
                        {allCategories.length > 1 && (
                          <div className="flex items-center gap-2 mb-2 sticky top-0 bg-white py-1">
                            <span className="px-2.5 py-0.5 bg-blue-100 text-blue-700 text-xs font-semibold rounded-full">
                              {cat}
                            </span>
                            <span className="text-xs text-gray-400">{pairs.length} pair{pairs.length !== 1 ? 's' : ''}</span>
                          </div>
                        )}

                        <div className="space-y-2">
                          {pairs.map((pair, i) => {
                            const globalIdx = qaPairs.findIndex(p => p.id === pair.id);
                            const isEditing = editingId === pair.id;
                            return (
                              <div
                                key={pair.id}
                                draggable
                                onDragStart={() => onDragStart(globalIdx)}
                                onDragEnter={() => onDragEnter(globalIdx)}
                                onDragEnd={onDragEnd}
                                onDragOver={e => e.preventDefault()}
                                className={`border rounded-xl p-4 transition-all ${
                                  isEditing ? 'border-blue-400 bg-blue-50' : 'border-gray-200 hover:border-gray-300 bg-white'
                                }`}
                              >
                                {isEditing ? (
                                  /* Edit mode */
                                  <div className="space-y-2">
                                    <input
                                      value={editForm.question}
                                      onChange={e => setEditForm(f => ({ ...f, question: e.target.value }))}
                                      className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                                    />
                                    <textarea
                                      value={editForm.answer}
                                      onChange={e => setEditForm(f => ({ ...f, answer: e.target.value }))}
                                      rows={3}
                                      className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 resize-y"
                                    />
                                    <input
                                      value={editForm.category}
                                      onChange={e => setEditForm(f => ({ ...f, category: e.target.value }))}
                                      placeholder="Category"
                                      className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                                    />
                                    <div className="flex gap-2 pt-1">
                                      <button onClick={() => saveEdit(pair.id)} disabled={savingEdit}
                                        className="px-3 py-1 bg-blue-600 text-white text-xs rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50">
                                        {savingEdit ? 'Saving…' : 'Save'}
                                      </button>
                                      <button onClick={() => setEditingId(null)}
                                        className="px-3 py-1 bg-white text-gray-600 text-xs rounded-lg font-semibold border border-gray-200 hover:bg-gray-50">
                                        Cancel
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  /* View mode */
                                  <div className="flex gap-3">
                                    <DragHandle />
                                    <div className="flex-1 min-w-0">
                                      <div className="flex items-start justify-between gap-2">
                                        <p className="text-sm font-medium text-gray-800 leading-snug">
                                          Q: {pair.question}
                                        </p>
                                        <div className="flex gap-1 flex-shrink-0 ml-2">
                                          {!pair.is_active && (
                                            <span className="px-1.5 py-0.5 bg-gray-100 text-gray-500 text-xs rounded">inactive</span>
                                          )}
                                          <button onClick={() => startEdit(pair)}
                                            className="p-1 text-gray-400 hover:text-blue-600 rounded transition-colors"
                                            title="Edit">
                                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                                d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                            </svg>
                                          </button>
                                          <button onClick={() => deleteQaPair(pair.id)}
                                            className="p-1 text-gray-400 hover:text-red-500 rounded transition-colors"
                                            title="Delete">
                                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                          </button>
                                        </div>
                                      </div>
                                      <p className="text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2 mt-1.5">
                                        A: {pair.answer}
                                      </p>
                                      {pair.tags && pair.tags.length > 0 && (
                                        <div className="flex gap-1 flex-wrap mt-1.5">
                                          {pair.tags.map(t => (
                                            <span key={t} className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded-full">{t}</span>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
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
