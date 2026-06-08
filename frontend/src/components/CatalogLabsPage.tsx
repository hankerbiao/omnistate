import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import { api } from '../services/api';
import { getCatalogLabs, invalidateCatalogLabsCache } from '../services/catalogLabsCache';
import type { CatalogLab, CreateCatalogLabRequest } from '../types';
import PageToolbar, { StatPill } from './ui/PageToolbar';

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
  const [deleteConfirm, setDeleteConfirm] = useState(false);
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
        if (updated) { setSelectedLab(updated); setEditName(updated.name); setEditDesc(updated.description || ''); setEditOrder(updated.sort_order); }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载 Lab 失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchLabs(); }, [fetchLabs]);

  // 默认选中第一项
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
    total: labs.length, active: activeLabs.length,
    inactive: labs.length - activeLabs.length,
    totalCases: labs.reduce((s, l) => s + (l.case_count ?? 0), 0),
  }), [labs, activeLabs]);

  const suggestedCode = useMemo(() => suggestCode(form.name), [form.name]);

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
      await api.updateCatalogLab(selectedLab.lab_id, { name: editName.trim(), description: editDesc.trim() || undefined, sort_order: editOrder });
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
      setDeleteConfirm(false);
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
    editName.trim() !== selectedLab.name || editDesc.trim() !== (selectedLab.description || '') || editOrder !== selectedLab.sort_order
  );

  return (
    <>
    {/* Hero */}
    <div style={{
      margin: '0 0 16px', borderRadius: 'var(--radius-xl)', padding: '16px 24px',
      background: 'linear-gradient(135deg, #eef2ff 0%, #f5f3ff 45%, #ecfeff 100%)',
      border: '1px solid color-mix(in srgb, #6366f1 18%, var(--border-subtle))',
      position: 'relative', overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute', top: -40, right: -20, width: 200, height: 200,
        borderRadius: '50%', background: 'radial-gradient(circle, rgba(99,102,241,0.25) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />
      <div style={{ position: 'relative', zIndex: 1 }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6, padding: '3px 12px', marginBottom: 8,
          fontSize: 12, fontWeight: 600, color: '#6366f1',
          background: 'rgba(99,102,241,0.12)', borderRadius: 999, border: '1px solid rgba(99,102,241,0.2)',
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z" />
            <path d="M19 13l1 3 3 1-3 1-1 3-1-3-3-1 3-1 1-3z" />
          </svg>
          <span>Catalog Intelligence</span>
        </div>
        <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)', maxWidth: 560, lineHeight: 1.6 }}>
          Lab 是测试用例目录的顶层命名空间。在此管理 Lab 生命周期、用例分布与目录健康度。
        </p>
      </div>
    </div>

    <div className={`split-workspace${selectedLab ? ' split-workspace--has-selection' : ''}`}>
      <aside className="split-workspace__list">
        <div className="split-panel-toolbar">
          <PageToolbar
            meta={<>
              <StatPill label="Lab" value={stats.total} />
              <StatPill label="启用" value={stats.active} tone="success" />
              <StatPill label="用例" value={stats.totalCases} tone="info" />
            </>}
            actions={<>
              <input className="form-input" style={{ width: 200, fontSize: 13 }} value={search} onChange={e => setSearch(e.target.value)} placeholder="搜索 Code 或名称…" />
              <div style={{ display: 'flex', gap: 2, padding: 3, background: 'var(--surface-secondary)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                {(['all', 'active', 'inactive'] as const).map(key => (
                  <button key={key} type="button" style={{
                    padding: '4px 12px', fontSize: 12, fontWeight: 500, border: 'none', borderRadius: 5,
                    background: statusFilter === key ? 'var(--surface-primary)' : 'transparent',
                    color: statusFilter === key ? 'var(--accent-primary)' : 'var(--text-secondary)',
                    cursor: 'pointer', boxShadow: statusFilter === key ? 'var(--shadow-xs)' : 'none',
                  }} onClick={() => setStatusFilter(key)}>
                    {key === 'all' ? '全部' : key === 'active' ? '启用' : '停用'}
                  </button>
                ))}
              </div>
              <button className="btn btn--ghost btn--sm" onClick={fetchLabs} disabled={loading} title="刷新">↻</button>
              <button className="btn btn--primary btn--sm" onClick={() => { setForm(emptyForm); setCodeTouched(false); setCreateOpen(true); }}>+ 新建 Lab</button>
            </>}
          />
        </div>

        {error && !selectedLab && <div className="error-banner" style={{ margin: '0 var(--space-4) var(--space-3)' }}><span>⚠</span> {error}<button style={s.errorClose} onClick={() => setError(null)}>×</button></div>}

        <div className="split-list-scroll" style={{ padding: 0 }}>
          {loading && labs.length === 0 ? (
            <div className="loading-overlay"><div className="loading-spinner" /></div>
          ) : filteredLabs.length === 0 ? (
            <div className="empty-state"><div className="empty-state__icon">📁</div><p className="empty-state__text">{search || statusFilter !== 'all' ? '没有匹配的 Lab' : '暂无 Lab 数据'}</p></div>
          ) : (
            <table className="data-table">
              <thead><tr>
                <th style={{ width: '32%' }}>名称</th>
                <th style={{ width: '16%' }}>Code</th>
                <th style={{ width: '60px' }}>排序</th>
                <th style={{ width: '60px' }}>状态</th>
                <th style={{ width: '60px' }}>用例</th>
              </tr></thead>
              <tbody>
                {filteredLabs.map(lab => (
                  <tr key={lab.lab_id}
                    className={selectedLab?.lab_id === lab.lab_id ? 'selected' : ''}
                    onClick={() => openLab(lab)} style={{ cursor: 'pointer' }}>
                    <td>
                      <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{lab.name}</div>
                      {lab.description && <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>{lab.description}</div>}
                    </td>
                    <td><code style={s.codeTag}>{lab.code}</code></td>
                    <td><span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{lab.sort_order}</span></td>
                    <td><span style={{ display: 'inline-flex', padding: '2px 8px', fontSize: 11, fontWeight: 600, borderRadius: 999, background: lab.is_active ? 'var(--status-success-bg)' : 'var(--surface-tertiary)', color: lab.is_active ? 'var(--status-success)' : 'var(--text-tertiary)' }}>{lab.is_active ? '启用' : '停用'}</span></td>
                    <td><span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-primary)', fontWeight: 600 }}>{lab.case_count ?? 0}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </aside>

      <main className="split-workspace__main">
        {selectedLab ? (
          <div className="split-detail-scroll" style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '20px 24px 16px', borderBottom: '0.5px solid var(--border-subtle)' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <code style={{ fontSize: 11, fontFamily: "'JetBrains Mono', monospace", color: 'var(--accent-primary)', background: 'rgba(99,102,241,0.1)', padding: '1px 8px', borderRadius: 4 }}>{selectedLab.code}</code>
                  <span style={{ display: 'inline-flex', padding: '1px 8px', fontSize: 10, fontWeight: 600, borderRadius: 999, background: selectedLab.is_active ? 'var(--status-success-bg)' : 'var(--surface-tertiary)', color: selectedLab.is_active ? 'var(--status-success)' : 'var(--text-tertiary)' }}>{selectedLab.is_active ? '启用' : '停用'}</span>
                </div>
                <div style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)' }}>{selectedLab.name}</div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                {selectedLab.is_active && (
                  <button className="btn btn--secondary btn--sm" onClick={() => setDeactivateLab(selectedLab)} style={{ fontSize: 12, padding: '6px 14px' }}>停用</button>
                )}
                <button className="btn btn--danger btn--sm" onClick={() => setDeleteConfirm(true)} style={{ fontSize: 12, padding: '6px 14px' }}>删除</button>
              </div>
            </div>

            {error && <div className="error-banner" style={{ margin: '12px 24px 0' }}><span>⚠</span> {error}<button style={s.errorClose} onClick={() => setError(null)}>×</button></div>}
            {deleteConfirm && (
              <div style={{ margin: '12px 24px 0', padding: '12px 16px', background: 'var(--status-error-bg)', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 12, justifyContent: 'space-between' }}>
                <span style={{ fontSize: 13 }}>确认删除 Lab <strong>{selectedLab.name}</strong>？（仅当无下属用例时可删）</span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn--danger btn--sm" onClick={handleDelete} disabled={deleting} style={{ padding: '4px 12px', fontSize: 12 }}>{deleting ? '删除中...' : '确认删除'}</button>
                  <button className="btn btn--secondary btn--sm" onClick={() => setDeleteConfirm(false)} style={{ padding: '4px 12px', fontSize: 12 }}>取消</button>
                </div>
              </div>
            )}

            {/* Content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div>
                    <label style={s.label}>显示名称</label>
                    <input className="form-input" value={editName} onChange={e => setEditName(e.target.value)} placeholder="输入 Lab 名称" style={{ width: '100%', padding: '7px 10px', fontSize: 13 }} />
                  </div>
                  <div>
                    <label style={s.label}>描述</label>
                    <textarea className="form-input" value={editDesc} onChange={e => setEditDesc(e.target.value)} placeholder="输入描述（可选）" rows={2} style={{ width: '100%', padding: '7px 10px', fontSize: 13, resize: 'vertical', fontFamily: 'inherit' }} />
                  </div>
                  <div>
                    <label style={s.label}>排序权重</label>
                    <input type="number" className="form-input" value={editOrder} onChange={e => setEditOrder(Number(e.target.value))} style={{ width: 120, padding: '7px 10px', fontSize: 13 }} />
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn--primary btn--sm" onClick={handleSave} disabled={saving || !editName.trim() || !hasChanges}>
                      {saving ? '保存中...' : '保存'}
                    </button>
                    {hasChanges && (
                      <button className="btn btn--secondary btn--sm" onClick={() => { setEditName(selectedLab.name); setEditDesc(selectedLab.description || ''); setEditOrder(selectedLab.sort_order); }}>
                        重置
                      </button>
                    )}
                  </div>
                </div>

                {/* Stats */}
                <div style={{ display: 'flex', gap: 12, flexShrink: 0 }}>
                  <div style={{ background: 'var(--surface-secondary)', borderRadius: 8, padding: '12px 18px', textAlign: 'center', minWidth: 80 }}>
                    <div style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)' }}>{selectedLab.case_count ?? 0}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>用例</div>
                  </div>
                  <div style={{ background: 'var(--surface-secondary)', borderRadius: 8, padding: '12px 18px', textAlign: 'center', minWidth: 80 }}>
                    <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--accent-primary)', fontFamily: 'monospace' }}>{selectedLab.lab_id.slice(0, 8)}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>Lab ID</div>
                  </div>
                </div>
              </div>

              {/* Metadata */}
              <div>
                <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 8 }}>元数据</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div style={{ padding: '10px 14px', background: 'var(--surface-secondary)', borderRadius: 8, border: '0.5px solid var(--border-subtle)' }}>
                    <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 2 }}>创建时间</div>
                    <div style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-primary)' }}>{new Date(selectedLab.created_at).toLocaleString('zh-CN')}</div>
                  </div>
                  <div style={{ padding: '10px 14px', background: 'var(--surface-secondary)', borderRadius: 8, border: '0.5px solid var(--border-subtle)' }}>
                    <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 2 }}>更新时间</div>
                    <div style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-primary)' }}>{formatRelativeTime(selectedLab.updated_at)}（{new Date(selectedLab.updated_at).toLocaleString('zh-CN')}）</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="split-placeholder">
            <div className="split-placeholder__icon">📁</div>
            <p className="split-placeholder__text">从左侧选择一个 Lab 查看详情</p>
          </div>
        )}
      </main>

      {/* Create Modal */}
      {createOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
          onClick={() => setCreateOpen(false)}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'var(--bg-elevated)', borderRadius: 12, width: 460, maxWidth: '90vw',
            boxShadow: '0 20px 60px rgba(0,0,0,0.3)', border: '1px solid var(--border-default)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '18px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>新建 Lab</h3>
                <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-tertiary)' }}>Lab Code 创建后不可修改，将作为目录路径前缀</p>
              </div>
              <button style={{ fontSize: 20, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => setCreateOpen(false)}>×</button>
            </div>
            <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={s.label}>显示名称</label>
                <input className="form-input" placeholder="例如：DDR5 验证实验室" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                  style={{ width: '100%', padding: '7px 10px', fontSize: 13 }} autoFocus />
              </div>
              <div>
                <label style={s.label}>Code（创建后不可改）</label>
                <input className="form-input" placeholder={suggestedCode || 'LAB_CODE'} value={form.code}
                  onChange={e => { setForm({ ...form, code: e.target.value.toUpperCase() }); setCodeTouched(true); }}
                  style={{ width: '100%', padding: '7px 10px', fontSize: 13, fontFamily: 'monospace', letterSpacing: '0.5px' }} />
                {!codeTouched && suggestedCode && form.name && (
                  <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', fontSize: 12, color: '#6366f1', background: 'rgba(99,102,241,0.08)', borderRadius: 6, border: '1px dashed rgba(99,102,241,0.3)' }}>
                    <span>建议 Code：</span>
                    <button type="button" style={{ padding: '1px 8px', fontFamily: 'monospace', fontSize: 12, fontWeight: 600, color: '#6366f1', background: 'rgba(99,102,241,0.15)', border: 'none', borderRadius: 4, cursor: 'pointer' }}
                      onClick={() => setForm({ ...form, code: suggestedCode })}>{suggestedCode}</button>
                  </div>
                )}
              </div>
              <div>
                <label style={s.label}>描述（可选）</label>
                <textarea className="form-input" placeholder="简要说明该 Lab 的用途…" value={form.description || ''}
                  onChange={e => setForm({ ...form, description: e.target.value })} rows={2}
                  style={{ width: '100%', padding: '7px 10px', fontSize: 13, resize: 'vertical', fontFamily: 'inherit' }} />
              </div>
              <div>
                <label style={s.label}>排序权重（越小越靠前）</label>
                <input type="number" className="form-input" value={form.sort_order ?? 0} onChange={e => setForm({ ...form, sort_order: Number(e.target.value) })} style={{ width: 120, padding: '7px 10px', fontSize: 13 }} />
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, padding: '14px 20px', borderTop: '1px solid var(--border-subtle)' }}>
              <button className="btn btn--secondary" onClick={() => setCreateOpen(false)}>取消</button>
              <button className="btn btn--primary" onClick={handleCreate} disabled={creating || !form.name.trim()}>
                {creating ? '创建中...' : '创建 Lab'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Deactivate Modal */}
      {deactivateLab && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
          onClick={() => { setDeactivateLab(null); setTargetLabId(''); }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'var(--bg-elevated)', borderRadius: 12, width: 460, maxWidth: '90vw',
            boxShadow: '0 20px 60px rgba(0,0,0,0.3)', border: '1px solid var(--border-default)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '18px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>停用 Lab：{deactivateLab.name}</h3>
              <button style={{ fontSize: 20, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => { setDeactivateLab(null); setTargetLabId(''); }}>×</button>
            </div>
            <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ padding: '12px 16px', background: 'var(--status-warning-bg)', borderRadius: 8, color: 'var(--status-warning)', fontSize: 13 }}>
                停用前需将下属用例迁移至目标 Lab，目录路径保持不变。
                <div style={{ marginTop: 8, fontSize: 24, fontWeight: 700, fontFamily: 'monospace' }}>{deactivateLab.case_count ?? 0} <span style={{ fontSize: 13, fontWeight: 400 }}>条用例待迁移</span></div>
              </div>
              <div>
                <label style={s.label}>目标 Lab</label>
                <select className="form-input form-select" style={{ width: '100%', fontSize: 13, padding: '7px 10px' }}
                  value={targetLabId} onChange={e => setTargetLabId(e.target.value)}>
                  <option value="">选择接收用例的 Lab…</option>
                  {activeLabs.filter(l => l.lab_id !== deactivateLab.lab_id).map(l => (
                    <option key={l.lab_id} value={l.lab_id}>{l.name} ({l.code}) · {l.case_count ?? 0} 用例</option>
                  ))}
                </select>
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, padding: '14px 20px', borderTop: '1px solid var(--border-subtle)' }}>
              <button className="btn btn--secondary" onClick={() => { setDeactivateLab(null); setTargetLabId(''); }}>取消</button>
              <button className="btn btn--primary" onClick={handleDeactivate} disabled={saving || !targetLabId}
                style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)' }}>
                {saving ? '处理中...' : '确认停用并迁移'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
    </>
  );
};

const s = {
  errorClose: { background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: 'var(--text-tertiary)', padding: '0 4px', lineHeight: 1 },
  codeTag: { fontFamily: "'JetBrains Mono', monospace", fontSize: 12, padding: '2px 8px', borderRadius: 4, background: 'var(--status-info-bg)', color: 'var(--accent-primary)' } as const,
  label: { fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase' as const, letterSpacing: '0.4px', display: 'block', marginBottom: 4 },
};

export default CatalogLabsPage;
