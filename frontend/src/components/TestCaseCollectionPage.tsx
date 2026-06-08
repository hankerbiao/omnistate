import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../services/api';
import type { CollectionListItem, CollectionResponse } from '../types';
import PageToolbar, { StatPill } from './ui/PageToolbar';
import PageHero from './ui/PageHero';

const TestCaseCollectionPage: React.FC = () => {
  const [collections, setCollections] = useState<CollectionListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selected, setSelected] = useState<CollectionResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Create modal
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newTags, setNewTags] = useState('');
  const [creating, setCreating] = useState(false);

  // Edit modal
  const [editOpen, setEditOpen] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editTags, setEditTags] = useState('');
  const [editing, setEditing] = useState(false);

  // Add cases modal
  const [addOpen, setAddOpen] = useState(false);
  const [addCaseIds, setAddCaseIds] = useState('');
  const [addAutoCaseIds, setAddAutoCaseIds] = useState('');
  const [adding, setAdding] = useState(false);

  const fetchCollections = useCallback(async (q?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listCollections(q || undefined);
      setCollections(res.data || []);
    } catch (err) {
      setError('获取集合列表失败');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCollections(); }, [fetchCollections]);

  const fetchDetail = useCallback(async (id: string) => {
    setDetailLoading(true);
    try {
      const res = await api.getCollection(id);
      setSelected(res.data);
    } catch { setSelected(null); }
    finally { setDetailLoading(false); }
  }, []);

  // ── Search ──
  useEffect(() => {
    const timer = setTimeout(() => fetchCollections(searchQuery || undefined), 300);
    return () => clearTimeout(timer);
  }, [searchQuery, fetchCollections]);

  // ── Create ──
  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await api.createCollection({
        name: newName.trim(),
        description: newDesc.trim() || undefined,
        tags: newTags.trim() ? newTags.split(/[,，]/).map(t => t.trim()).filter(Boolean) : undefined,
      });
      setCreateOpen(false);
      setNewName('');
      setNewDesc('');
      setNewTags('');
      fetchCollections();
    } catch (err) {
      setError('创建集合失败');
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  // ── Edit ──
  const openEdit = () => {
    if (!selected) return;
    setEditName(selected.name);
    setEditDesc(selected.description || '');
    setEditTags((selected.tags || []).join(', '));
    setEditOpen(true);
  };

  const handleEdit = async () => {
    if (!selected || !editName.trim()) return;
    setEditing(true);
    setError(null);
    try {
      await api.updateCollection(selected.collection_id, {
        name: editName.trim(),
        description: editDesc.trim() || undefined,
        tags: editTags.trim() ? editTags.split(/[,，]/).map(t => t.trim()).filter(Boolean) : [],
      });
      setEditOpen(false);
      fetchCollections();
      fetchDetail(selected.collection_id);
    } catch (err) {
      setError('更新集合失败');
      console.error(err);
    } finally {
      setEditing(false);
    }
  };

  // ── Delete ──
  const handleDelete = async () => {
    if (!selected) return;
    if (!window.confirm(`确定删除集合「${selected.name}」吗？`)) return;
    setError(null);
    try {
      await api.deleteCollection(selected.collection_id);
      setSelected(null);
      fetchCollections();
    } catch (err) {
      setError('删除集合失败');
      console.error(err);
    }
  };

  // ── Add cases ──
  const handleAddCases = async () => {
    if (!selected) return;
    setAdding(true);
    setError(null);
    try {
      await api.addCasesToCollection(selected.collection_id, {
        case_ids: addCaseIds.trim() ? addCaseIds.split(/[,，]/).map(t => t.trim()).filter(Boolean) : [],
        auto_case_ids: addAutoCaseIds.trim() ? addAutoCaseIds.split(/[,，]/).map(t => t.trim()).filter(Boolean) : [],
      });
      setAddOpen(false);
      setAddCaseIds('');
      setAddAutoCaseIds('');
      fetchDetail(selected.collection_id);
    } catch (err) {
      setError('添加用例失败');
      console.error(err);
    } finally {
      setAdding(false);
    }
  };

  // ── Remove single case ──
  const handleRemoveCase = async (caseId: string) => {
    if (!selected) return;
    try {
      await api.removeCasesFromCollection(selected.collection_id, { case_ids: [caseId] });
      fetchDetail(selected.collection_id);
    } catch (err) {
      setError('移除用例失败');
      console.error(err);
    }
  };

  const handleRemoveAutoCase = async (autoCaseId: string) => {
    if (!selected) return;
    try {
      await api.removeCasesFromCollection(selected.collection_id, { auto_case_ids: [autoCaseId] });
      fetchDetail(selected.collection_id);
    } catch (err) {
      setError('移除用例失败');
      console.error(err);
    }
  };

  const tagsArray = useMemo(() => {
    if (!selected?.tags) return [];
    return selected.tags;
  }, [selected]);

  return (
    <div className="page-content">
      <PageHero
        badge="test case collection"
        description="创建和管理用例集合，用于在执行任务时快速批量选取测试用例。"
        accent="#6366f1"
        gradient={['#f0f0ff', '#e0e7ff', '#f0f0ff']}
      />

      <PageToolbar
        meta={(
          <>
            <StatPill label="集合数" value={collections.length} />
          </>
        )}
        actions={(
          <>
            <input
              type="search"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="搜索集合名称、描述…"
              className="form-input"
              style={{ width: 200, fontSize: 13 }}
              aria-label="搜索集合"
            />
            <button type="button" className="btn btn--primary btn--sm" onClick={() => setCreateOpen(true)}>
              + 新建集合
            </button>
          </>
        )}
      />

      {error && (
        <div className="error-banner" style={{ marginBottom: 16, justifyContent: 'space-between' }}>
          <span>⚠ {error}</span>
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div style={{ display: 'flex', gap: 16, minHeight: '60vh' }}>
        {/* ── Left: list ── */}
        <div style={{ width: 320, minWidth: 320 }}>
          {loading ? (
            <div className="loading-overlay"><div className="loading-spinner" /></div>
          ) : collections.length === 0 ? (
            <div className="empty-state" style={{ padding: '32px 16px' }}>
              <div className="empty-state__icon">📁</div>
              <p className="empty-state__text">{searchQuery ? '没有匹配的集合' : '暂无用例集合'}</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {collections.map(c => (
                <button
                  key={c.collection_id}
                  type="button"
                  onClick={() => fetchDetail(c.collection_id)}
                  style={{
                    display: 'block', width: '100%', textAlign: 'left', padding: '10px 14px',
                    borderRadius: 8, border: '1px solid var(--border-subtle)',
                    background: selected?.collection_id === c.collection_id
                      ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)'
                      : 'var(--surface-primary)',
                    cursor: 'pointer', transition: 'all 0.1s',
                    borderColor: selected?.collection_id === c.collection_id ? 'var(--accent-primary)' : 'var(--border-subtle)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>
                      {c.collection_id} · {c.name}
                    </span>
                    <span style={{ fontSize: 11, color: 'var(--text-tertiary)', fontFamily: 'monospace' }}>
                      {c.case_count + c.auto_case_count} 用例
                    </span>
                  </div>
                  {c.description && (
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2, lineHeight: 1.4 }}>
                      {c.description.slice(0, 60)}{c.description.length > 60 ? '…' : ''}
                    </div>
                  )}
                  {c.tags.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                      {c.tags.slice(0, 3).map(t => (
                        <span key={t} style={{ fontSize: 10, padding: '1px 6px', borderRadius: 999, backgroundColor: 'var(--surface-secondary)', color: 'var(--text-tertiary)' }}>{t}</span>
                      ))}
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* ── Right: detail ── */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {!selected ? (
            <div className="empty-state" style={{ height: '100%' }}>
              <div className="empty-state__icon">👈</div>
              <p className="empty-state__text">从左侧选择一个用例集合</p>
            </div>
          ) : detailLoading ? (
            <div className="loading-overlay"><div className="loading-spinner" /></div>
          ) : (
            <div className="surface-card" style={{ padding: '20px 24px' }}>
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--accent-primary)', fontWeight: 500 }}>
                      {selected.collection_id}
                    </span>
                    {tagsArray.map(t => (
                      <span key={t} style={{ fontSize: 10, padding: '1px 8px', borderRadius: 999, backgroundColor: 'color-mix(in srgb, var(--accent-primary) 10%, transparent)', color: 'var(--accent-primary)' }}>{t}</span>
                    ))}
                  </div>
                  <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>{selected.name}</h3>
                  {selected.description && (
                    <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{selected.description}</p>
                  )}
                  <span style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4, display: 'block' }}>
                    创建人: {selected.created_by} · 更新: {new Date(selected.updated_at).toLocaleString('zh-CN')}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button type="button" className="btn btn--secondary btn--sm" onClick={openEdit}>编辑</button>
                  <button type="button" className="btn btn--secondary btn--sm" onClick={() => setAddOpen(true)}>+ 添加用例</button>
                  <button type="button" className="btn btn--danger btn--sm" onClick={handleDelete}>删除</button>
                </div>
              </div>

              {/* Cases list */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {selected.case_ids.length > 0 && (
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>手工测试用例 ({selected.case_ids.length})</div>
                    {selected.case_ids.map(cid => (
                      <div key={cid} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', borderBottom: '0.5px solid var(--border-subtle)', fontSize: 13 }}>
                        <span style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--accent-cyan)', minWidth: 55 }}>{cid}</span>
                        <span style={{ flex: 1, color: 'var(--text-primary)' }}>{cid}</span>
                        <button type="button" className="btn btn--ghost btn--sm" onClick={() => handleRemoveCase(cid)} style={{ color: 'var(--status-error)', fontSize: 10, padding: '2px 6px' }}>移除</button>
                      </div>
                    ))}
                  </div>
                )}
                {selected.auto_case_ids.length > 0 && (
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>自动化测试用例 ({selected.auto_case_ids.length})</div>
                    {selected.auto_case_ids.map(aid => (
                      <div key={aid} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', borderBottom: '0.5px solid var(--border-subtle)', fontSize: 13 }}>
                        <span style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--accent-purple)', minWidth: 55 }}>{aid}</span>
                        <span style={{ flex: 1, color: 'var(--text-primary)' }}>{aid}</span>
                        <button type="button" className="btn btn--ghost btn--sm" onClick={() => handleRemoveAutoCase(aid)} style={{ color: 'var(--status-error)', fontSize: 10, padding: '2px 6px' }}>移除</button>
                      </div>
                    ))}
                  </div>
                )}
                {selected.case_ids.length === 0 && selected.auto_case_ids.length === 0 && (
                  <p style={{ fontSize: 13, color: 'var(--text-tertiary)', textAlign: 'center', padding: 24 }}>此集合暂无用例，点击「+ 添加用例」添加</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Create Modal ── */}
      {createOpen && (
        <div className="modal-overlay" onClick={() => setCreateOpen(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ width: 480 }}>
            <div className="modal__header">
              <h3 className="modal__title">新建用例集合</h3>
              <button className="modal__close" onClick={() => setCreateOpen(false)}>×</button>
            </div>
            <div className="modal__body">
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>集合名称 *</label>
                <input className="form-input" value={newName} onChange={e => setNewName(e.target.value)} placeholder="例如: 回归基线集合" autoFocus />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>描述</label>
                <textarea className="form-input" value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="说明此集合的用途" rows={3} />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>标签（逗号分隔）</label>
                <input className="form-input" value={newTags} onChange={e => setNewTags(e.target.value)} placeholder="回归, 冒烟, P0" />
              </div>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setCreateOpen(false)}>取消</button>
              <button className="btn btn--primary" onClick={handleCreate} disabled={creating || !newName.trim()}>{creating ? '创建中…' : '创建'}</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Edit Modal ── */}
      {editOpen && (
        <div className="modal-overlay" onClick={() => setEditOpen(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ width: 480 }}>
            <div className="modal__header">
              <h3 className="modal__title">编辑集合</h3>
              <button className="modal__close" onClick={() => setEditOpen(false)}>×</button>
            </div>
            <div className="modal__body">
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>集合名称 *</label>
                <input className="form-input" value={editName} onChange={e => setEditName(e.target.value)} autoFocus />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>描述</label>
                <textarea className="form-input" value={editDesc} onChange={e => setEditDesc(e.target.value)} rows={3} />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>标签（逗号分隔）</label>
                <input className="form-input" value={editTags} onChange={e => setEditTags(e.target.value)} />
              </div>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setEditOpen(false)}>取消</button>
              <button className="btn btn--primary" onClick={handleEdit} disabled={editing || !editName.trim()}>{editing ? '保存中…' : '保存'}</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Add Cases Modal ── */}
      {addOpen && (
        <div className="modal-overlay" onClick={() => setAddOpen(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ width: 480 }}>
            <div className="modal__header">
              <h3 className="modal__title">添加用例到集合</h3>
              <button className="modal__close" onClick={() => setAddOpen(false)}>×</button>
            </div>
            <div className="modal__body">
              <p style={{ fontSize: 12, color: 'var(--text-tertiary)', margin: '0 0 12px' }}>输入用例 ID，多个用逗号分隔。已有用例会自动去重。</p>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>手工用例 ID</label>
                <input className="form-input" value={addCaseIds} onChange={e => setAddCaseIds(e.target.value)} placeholder="TC-001, TC-002" />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>自动化用例 ID</label>
                <input className="form-input" value={addAutoCaseIds} onChange={e => setAddAutoCaseIds(e.target.value)} placeholder="AC-001, AC-002" />
              </div>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setAddOpen(false)}>取消</button>
              <button className="btn btn--primary" onClick={handleAddCases} disabled={adding}>{adding ? '添加中…' : '添加'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TestCaseCollectionPage;
