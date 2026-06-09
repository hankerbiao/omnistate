import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import { api } from '../services/api';
import { getCatalogLabs, invalidateCatalogLabsCache } from '../services/catalogLabsCache';
import type { CatalogLab, CreateCatalogLabRequest } from '../types';
import PageToolbar, { StatPill } from './ui/PageToolbar';
import {
  DetailHeader,
  DetailStatGrid,
  DetailSection,
  DetailEmpty,
  DetailMetaRow,
} from './ui/SplitDetailPanel';

const emptyForm: CreateCatalogLabRequest = { code: '', name: '', description: '', sort_order: 0 };

function suggestCode(name: string): string {
  return name.trim().replace(/[\s-]+/g, '_').replace(/[^a-zA-Z0-9_]/g, '').toUpperCase().slice(0, 32);
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days < 1) return '今天';
  if (days < 7) return `${days} 天前`;
  if (days < 30) return `${Math.floor(days / 7)} 周前`;
  return new Date(iso).toLocaleDateString('zh-CN');
}

type StatusFilter = 'all' | 'active' | 'inactive';

const CatalogLabsPage: React.FC = () => {
  const [labs, setLabs] = useState<CatalogLab[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const [selectedLab, setSelectedLab] = useState<CatalogLab | null>(null);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editOrder, setEditOrder] = useState(0);
  const [saving, setSaving] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [codeTouched, setCodeTouched] = useState(false);
  const [creating, setCreating] = useState(false);

  const [deactivateLab, setDeactivateLab] = useState<CatalogLab | null>(null);
  const [targetLabId, setTargetLabId] = useState('');
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const selectedLabRef = useRef(selectedLab);
  selectedLabRef.current = selectedLab;
  const initialSelectedRef = useRef(false);

  const fetchLabs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await getCatalogLabs();
      setLabs(items);
      const current = selectedLabRef.current;
      if (current) {
        const updated = items.find(l => l.lab_id === current.lab_id);
        if (updated) {
          setSelectedLab(updated);
          setEditName(updated.name);
          setEditDesc(updated.description || '');
          setEditOrder(updated.sort_order);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载 Lab 失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchLabs(); }, [fetchLabs]);

  useEffect(() => {
    if (!initialSelectedRef.current && labs.length > 0 && !selectedLab) {
      initialSelectedRef.current = true;
      openLab(labs[0]);
    }
  }, [labs, selectedLab]);

  const activeLabs = useMemo(() => labs.filter(l => l.is_active), [labs]);

  const filteredLabs = useMemo(() => {
    const q = search.trim().toLowerCase();
    return labs.filter(l => {
      if (statusFilter === 'active' && !l.is_active) return false;
      if (statusFilter === 'inactive' && l.is_active) return false;
      if (!q) return true;
      return l.code.toLowerCase().includes(q) || l.name.toLowerCase().includes(q);
    }).sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name));
  }, [labs, search, statusFilter]);

  const stats = useMemo(() => ({
    total: labs.length,
    active: activeLabs.length,
    inactive: labs.length - activeLabs.length,
    totalCases: labs.reduce((s, l) => s + (l.case_count ?? 0), 0),
  }), [labs, activeLabs]);

  const suggestedCode = useMemo(() => suggestCode(form.name), [form.name]);

  const caseSharePct = (lab: CatalogLab) => (
    stats.totalCases > 0 ? Math.round(((lab.case_count ?? 0) / stats.totalCases) * 100) : 0
  );

  const openLab = (lab: CatalogLab) => {
    setSelectedLab(lab);
    setEditName(lab.name);
    setEditDesc(lab.description || '');
    setEditOrder(lab.sort_order);
    setError(null);
  };

  const closeLab = () => setSelectedLab(null);

  const handleSave = async () => {
    if (!selectedLab || !editName.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateCatalogLab(selectedLab.lab_id, {
        name: editName.trim(),
        description: editDesc.trim() || undefined,
        sort_order: editOrder,
      });
      invalidateCatalogLabsCache();
      await fetchLabs();
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedLab) return;
    setDeleting(true);
    setError(null);
    try {
      await api.deleteCatalogLab(selectedLab.lab_id);
      setDeleteModalOpen(false);
      closeLab();
      invalidateCatalogLabsCache();
      await fetchLabs();
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败');
    } finally {
      setDeleting(false);
    }
  };

  const handleDeactivate = async () => {
    if (!deactivateLab || !targetLabId) return;
    setSaving(true);
    try {
      await api.deactivateCatalogLab(deactivateLab.lab_id, targetLabId);
      setDeactivateLab(null);
      setTargetLabId('');
      invalidateCatalogLabsCache();
      await fetchLabs();
    } catch (err) {
      setError(err instanceof Error ? err.message : '停用失败');
    } finally {
      setSaving(false);
    }
  };

  const handleCreate = async () => {
    setCreating(true);
    try {
      await api.createCatalogLab({ ...form, code: form.code || suggestedCode });
      setCreateOpen(false);
      setForm(emptyForm);
      setCodeTouched(false);
      invalidateCatalogLabsCache();
      await fetchLabs();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setCreating(false);
    }
  };

  const hasChanges = selectedLab && (
    editName.trim() !== selectedLab.name
    || editDesc.trim() !== (selectedLab.description || '')
    || editOrder !== selectedLab.sort_order
  );

  return (
    <>
      <div className={`split-workspace${selectedLab ? ' split-workspace--has-selection' : ''}`}>
        <aside className="split-workspace__list">
          <div className="split-panel-toolbar">
            <PageToolbar
              meta={(
                <>
                  <StatPill label="Lab" value={stats.total} />
                  <StatPill label="启用" value={stats.active} tone="success" />
                  <StatPill label="用例" value={stats.totalCases} tone="info" />
                </>
              )}
              actions={(
                <button
                  type="button"
                  className="btn btn--primary btn--sm"
                  onClick={() => { setForm(emptyForm); setCodeTouched(false); setCreateOpen(true); }}
                >
                  + 新建 Lab
                </button>
              )}
            />
          </div>

          <div className="filter-strip">
            <input
              className="form-input"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="搜索 Code 或名称…"
              aria-label="搜索 Lab"
            />
            <select
              className="form-input form-select"
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value as StatusFilter)}
              aria-label="状态筛选"
            >
              <option value="all">全部</option>
              <option value="active">启用</option>
              <option value="inactive">停用</option>
            </select>
            <button type="button" className="btn btn--secondary btn--sm" onClick={fetchLabs} disabled={loading}>
              刷新
            </button>
          </div>

          {error && !selectedLab && (
            <div className="error-banner" style={{ margin: '0 var(--space-4) var(--space-3)' }}>
              <span>⚠</span> {error}
              <button type="button" style={s.errorClose} onClick={() => setError(null)}>×</button>
            </div>
          )}

          <div className="split-list-scroll" style={{ padding: 0 }}>
            {loading && labs.length === 0 ? (
              <div className="loading-overlay"><div className="loading-spinner" /></div>
            ) : filteredLabs.length === 0 ? (
              <div className="empty-state"><div className="empty-state__icon">📁</div><p className="empty-state__text">{search || statusFilter !== 'all' ? '没有匹配的 Lab' : '暂无 Lab 数据'}</p></div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>名称</th>
                    <th>Code</th>
                    <th style={{ width: 64 }}>排序</th>
                    <th style={{ width: 72 }}>状态</th>
                    <th style={{ width: 64 }}>用例</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLabs.map(lab => (
                    <tr
                      key={lab.lab_id}
                      className={selectedLab?.lab_id === lab.lab_id ? 'selected' : ''}
                      onClick={() => openLab(lab)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td style={{ fontWeight: 600 }}>{lab.name}</td>
                      <td><code style={s.codeTag}>{lab.code}</code></td>
                      <td style={{ fontFamily: 'monospace' }}>{lab.sort_order}</td>
                      <td>
                        <span className={`status-badge ${lab.is_active ? 'status-badge--success' : 'status-badge--neutral'}`}>
                          {lab.is_active ? '启用' : '停用'}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{lab.case_count ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </aside>

        <main className="split-workspace__main">
          {selectedLab ? (
            <div className="split-detail-scroll">
              <button type="button" className="split-workspace__back" onClick={closeLab}>
                ← 返回列表
              </button>

              <DetailHeader
                id={selectedLab.code}
                title={selectedLab.name}
                subtitle={selectedLab.description || undefined}
                badges={(
                  <span className={`status-badge ${selectedLab.is_active ? 'status-badge--success' : 'status-badge--neutral'}`}>
                    {selectedLab.is_active ? '启用' : '停用'}
                  </span>
                )}
                actions={(
                  <>
                    {selectedLab.is_active && (
                      <button type="button" className="btn btn--secondary btn--sm" onClick={() => setDeactivateLab(selectedLab)}>
                        停用
                      </button>
                    )}
                    <button type="button" className="btn btn--danger btn--sm" onClick={() => setDeleteModalOpen(true)}>
                      删除
                    </button>
                  </>
                )}
              />

              {error && (
                <div className="error-banner" style={{ margin: '0 var(--space-5) var(--space-3)' }}>
                  <span>⚠</span> {error}
                  <button type="button" style={s.errorClose} onClick={() => setError(null)}>×</button>
                </div>
              )}

              <div className="split-detail-content">
                <div className="split-detail-form-grid">
                  <div className="split-detail-form-grid__fields">
                    <div>
                      <label style={s.label}>显示名称</label>
                      <input className="form-input" value={editName} onChange={e => setEditName(e.target.value)} placeholder="输入 Lab 名称" />
                    </div>
                    <div>
                      <label style={s.label}>描述</label>
                      <textarea className="form-input" value={editDesc} onChange={e => setEditDesc(e.target.value)} placeholder="输入描述（可选）" rows={2} style={{ resize: 'vertical', fontFamily: 'inherit' }} />
                    </div>
                    <div>
                      <label style={s.label}>排序权重</label>
                      <input type="number" className="form-input" value={editOrder} onChange={e => setEditOrder(Number(e.target.value))} style={{ width: 120 }} />
                    </div>
                    <div className="split-detail-form-actions">
                      <button type="button" className="btn btn--primary btn--sm" onClick={handleSave} disabled={saving || !editName.trim() || !hasChanges}>
                        {saving ? '保存中...' : '保存'}
                      </button>
                      {hasChanges && (
                        <button type="button" className="btn btn--secondary btn--sm" onClick={() => { setEditName(selectedLab.name); setEditDesc(selectedLab.description || ''); setEditOrder(selectedLab.sort_order); }}>
                          重置
                        </button>
                      )}
                    </div>
                  </div>
                  <DetailStatGrid stats={[
                    { label: '用例数', value: selectedLab.case_count ?? 0 },
                    { label: '排序', value: selectedLab.sort_order },
                    { label: '用例占比', value: `${caseSharePct(selectedLab)}%`, hint: `共 ${stats.totalCases} 条` },
                  ]} />
                </div>

                <DetailSection title="用例分布" hint="各 Lab 用例数量占比">
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {labs.map(lab => {
                      const pct = caseSharePct(lab);
                      const isCurrent = lab.lab_id === selectedLab.lab_id;
                      return (
                        <div key={lab.lab_id}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                            <span style={{ fontWeight: isCurrent ? 600 : 400 }}>{lab.name}</span>
                            <span style={{ color: 'var(--text-tertiary)' }}>{lab.case_count ?? 0} · {pct}%</span>
                          </div>
                          <div style={{ height: 8, borderRadius: 4, background: 'var(--surface-secondary)', overflow: 'hidden' }}>
                            <div style={{ width: `${pct}%`, height: '100%', background: isCurrent ? 'var(--accent-primary)' : 'color-mix(in srgb, var(--accent-primary) 45%, transparent)' }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </DetailSection>

                <DetailSection title="元数据">
                  <DetailMetaRow label="创建时间" value={new Date(selectedLab.created_at).toLocaleString('zh-CN')} />
                  <DetailMetaRow label="更新时间" value={`${formatRelativeTime(selectedLab.updated_at)}（${new Date(selectedLab.updated_at).toLocaleString('zh-CN')}）`} />
                  <DetailMetaRow label="Lab ID" value={selectedLab.lab_id} />
                </DetailSection>
              </div>
            </div>
          ) : (
            <DetailEmpty icon="📁" text="从左侧选择一个 Lab 查看详情" />
          )}
        </main>
      </div>

      {createOpen && (
        <div className="modal-overlay" onClick={() => setCreateOpen(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <div>
                <h3 className="modal__title">新建 Lab</h3>
                <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-tertiary)' }}>Lab Code 创建后不可修改</p>
              </div>
              <button type="button" className="modal__close" onClick={() => setCreateOpen(false)}>×</button>
            </div>
            <div className="modal__body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={s.label}>显示名称</label>
                <input className="form-input" placeholder="例如：DDR5 验证实验室" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} autoFocus />
              </div>
              <div>
                <label style={s.label}>Code（创建后不可改）</label>
                <input className="form-input" placeholder={suggestedCode || 'LAB_CODE'} value={form.code}
                  onChange={e => { setForm({ ...form, code: e.target.value.toUpperCase() }); setCodeTouched(true); }}
                  style={{ fontFamily: 'monospace' }}
                />
                {!codeTouched && suggestedCode && form.name && (
                  <button type="button" className="btn btn--ghost btn--sm" style={{ marginTop: 8 }} onClick={() => setForm({ ...form, code: suggestedCode })}>
                    使用建议 Code：{suggestedCode}
                  </button>
                )}
              </div>
              <div>
                <label style={s.label}>描述（可选）</label>
                <textarea className="form-input" value={form.description || ''} onChange={e => setForm({ ...form, description: e.target.value })} rows={2} style={{ resize: 'vertical', fontFamily: 'inherit' }} />
              </div>
              <div>
                <label style={s.label}>排序权重</label>
                <input type="number" className="form-input" value={form.sort_order ?? 0} onChange={e => setForm({ ...form, sort_order: Number(e.target.value) })} style={{ width: 120 }} />
              </div>
            </div>
            <div className="modal__footer">
              <button type="button" className="btn btn--secondary" onClick={() => setCreateOpen(false)}>取消</button>
              <button type="button" className="btn btn--primary" onClick={handleCreate} disabled={creating || !form.name.trim()}>
                {creating ? '创建中...' : '创建 Lab'}
              </button>
            </div>
          </div>
        </div>
      )}

      {deactivateLab && (
        <div className="modal-overlay" onClick={() => { setDeactivateLab(null); setTargetLabId(''); }}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">停用 Lab：{deactivateLab.name}</h3>
              <button type="button" className="modal__close" onClick={() => { setDeactivateLab(null); setTargetLabId(''); }}>×</button>
            </div>
            <div className="modal__body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)' }}>
                停用前需将下属 {deactivateLab.case_count ?? 0} 条用例迁移至目标 Lab。
              </p>
              <div>
                <label style={s.label}>目标 Lab</label>
                <select className="form-input form-select" value={targetLabId} onChange={e => setTargetLabId(e.target.value)}>
                  <option value="">选择接收用例的 Lab…</option>
                  {activeLabs.filter(l => l.lab_id !== deactivateLab.lab_id).map(l => (
                    <option key={l.lab_id} value={l.lab_id}>{l.name} ({l.code}) · {l.case_count ?? 0} 用例</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="modal__footer">
              <button type="button" className="btn btn--secondary" onClick={() => { setDeactivateLab(null); setTargetLabId(''); }}>取消</button>
              <button type="button" className="btn btn--primary" onClick={handleDeactivate} disabled={saving || !targetLabId}>
                {saving ? '处理中...' : '确认停用并迁移'}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteModalOpen && selectedLab && (
        <div className="modal-overlay" onClick={() => setDeleteModalOpen(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">删除 Lab</h3>
              <button type="button" className="modal__close" onClick={() => setDeleteModalOpen(false)}>×</button>
            </div>
            <div className="modal__body">
              <p style={{ margin: 0, fontSize: 14 }}>
                确认删除 Lab <strong>{selectedLab.name}</strong>？仅当无下属用例时可删。
              </p>
            </div>
            <div className="modal__footer">
              <button type="button" className="btn btn--secondary" onClick={() => setDeleteModalOpen(false)}>取消</button>
              <button type="button" className="btn btn--danger" onClick={handleDelete} disabled={deleting}>
                {deleting ? '删除中...' : '确认删除'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

const s = {
  errorClose: { background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: 'var(--text-tertiary)', padding: '0 4px', lineHeight: 1 },
  codeTag: { fontFamily: "'JetBrains Mono', monospace", fontSize: 12, padding: '2px 8px', borderRadius: 4, background: 'var(--status-info-bg)', color: 'var(--accent-primary)' } as const,
  label: { fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase' as const, letterSpacing: '0.4px', display: 'block', marginBottom: 4 },
};

export default CatalogLabsPage;
