import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { api } from '../services/api';
import type { PermissionResponse } from '../types';
import PageToolbar, { StatPill } from './ui/PageToolbar';
import { getErrorMessage } from '../utils/errors';

type ViewMode = 'table' | 'grouped';

const CATEGORY_LABELS: Record<string, string> = {
  users: '用户管理', roles: '角色管理', permissions: '权限管理',
  requirements: '需求管理', test_cases: '测试用例', work_items: '工作流',
  assets: '资产管理', execution_tasks: '执行任务', execution_agents: '执行 Agent',
  execution: '执行管理', automation: '自动化', catalog: '目录管理',
  duts: '被测设备', navigation: '导航配置', nav: '公共导航',
  terminal: '终端', other: '其他',
};


const getPermissionCategory = (code: string): string => {
  const [resource] = code.split(':');
  return resource || 'other';
};

const getCategoryLabel = (category: string): string =>
  CATEGORY_LABELS[category] || category;

const CATEGORY_COLORS: Record<string, string> = {
  users: '#3b82f6', roles: '#8b5cf6', permissions: '#ec4899',
  requirements: '#f59e0b', test_cases: '#10b981', work_items: '#6366f1',
  execution: '#f97316', automation: '#14b8a6', catalog: '#06b6d4',
  navigation: '#a855f7', terminal: '#6b7280',
};

const PermissionManagement: React.FC = () => {
  const [permissions, setPermissions] = useState<PermissionResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('table');

  const [selectedPerm, setSelectedPerm] = useState<PermissionResponse | null>(null);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [saving, setSaving] = useState(false);

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newPermCode, setNewPermCode] = useState('');
  const [newPermName, setNewPermName] = useState('');
  const [newPermDesc, setNewPermDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const selectedPermRef = useRef(selectedPerm);
  selectedPermRef.current = selectedPerm;
  const initialSelectedRef = useRef(false);

  const fetchPermissions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listPermissions();
      const data = response.data || [];
      setPermissions(data);
      const current = selectedPermRef.current;
      if (current) {
        const updated = data.find(p => (p.perm_id || p.permission_id || p.id) === (current.perm_id || current.permission_id || current.id));
        if (updated) { setSelectedPerm(updated); setEditName(updated.name); setEditDesc(updated.description || ''); }
      }
    } catch (err) {
      setError(getErrorMessage(err, '获取权限列表失败'));
    } finally {
      setLoading(false);
    }
  }, []); // 故意不依赖 selectedPerm，用 ref 避免循环渲染

  useEffect(() => { fetchPermissions(); }, [fetchPermissions]);

  // 默认选中第一项
  useEffect(() => {
    if (!initialSelectedRef.current && permissions.length > 0 && !selectedPerm) {
      initialSelectedRef.current = true;
      openPerm(permissions[0]);
    }
  }, [permissions, selectedPerm]);

  const categories = useMemo(() => {
    const set = new Set(permissions.map(p => getPermissionCategory(p.code)));
    return Array.from(set).sort((a, b) => getCategoryLabel(a).localeCompare(getCategoryLabel(b), 'zh-CN'));
  }, [permissions]);

  const filteredPermissions = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return permissions
      .filter(perm => {
        if (categoryFilter && getPermissionCategory(perm.code) !== categoryFilter) return false;
        if (!q) return true;
        return perm.code.toLowerCase().includes(q) || perm.name.toLowerCase().includes(q) || (perm.description?.toLowerCase().includes(q) ?? false);
      })
      .sort((a, b) => a.code.localeCompare(b.code));
  }, [permissions, searchQuery, categoryFilter]);

  const groupedPermissions = useMemo(() => {
    return filteredPermissions.reduce<Record<string, PermissionResponse[]>>((acc, perm) => {
      const cat = getPermissionCategory(perm.code);
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(perm);
      return acc;
    }, {});
  }, [filteredPermissions]);

  const openPerm = (perm: PermissionResponse) => {
    setSelectedPerm(perm);
    setEditName(perm.name);
    setEditDesc(perm.description || '');
    setError(null);
  };

  const closePerm = () => { setSelectedPerm(null); };

  const handleSave = async () => {
    if (!selectedPerm || !editName.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const id = selectedPerm.perm_id || selectedPerm.permission_id || selectedPerm.id;
      await api.updatePermission(id, { name: editName.trim(), description: editDesc.trim() || undefined });
      await fetchPermissions();
    } catch (err) {
      setError(getErrorMessage(err, '保存失败'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedPerm) return;
    setDeleting(true);
    setError(null);
    try {
      const id = selectedPerm.perm_id || selectedPerm.permission_id || selectedPerm.id;
      await api.deletePermission(id);
      closePerm();
      await fetchPermissions();
    } catch (err) {
      setError(getErrorMessage(err, '删除失败'));
    } finally {
      setDeleting(false);
    }
  };

  const handleCreate = async () => {
    if (!newPermCode.trim() || !newPermName.trim()) { setError('权限代码和名称不能为空'); return; }
    setCreating(true);
    setError(null);
    try {
      await api.createPermission({ perm_id: newPermCode.trim(), code: newPermCode.trim(), name: newPermName.trim(), description: newPermDesc.trim() || undefined });
      await fetchPermissions();
      setCreateModalOpen(false);
      setNewPermCode(''); setNewPermName(''); setNewPermDesc('');
    } catch (err) {
      setError(getErrorMessage(err, '创建失败'));
    } finally {
      setCreating(false);
    }
  };

  const hasChanges = selectedPerm && (editName.trim() !== selectedPerm.name || editDesc.trim() !== (selectedPerm.description || ''));

  const catColor = (code: string) => CATEGORY_COLORS[getPermissionCategory(code)] || '#6b7280';

  return (
    <>
    {/* Hero */}
    <div style={{
      margin: '0 0 16px', borderRadius: 'var(--radius-xl)', padding: '16px 24px',
      background: 'linear-gradient(135deg, #eef2ff 0%, #f5f3ff 45%, #ecfdf5 100%)',
      border: '1px solid color-mix(in srgb, #10b981 18%, var(--border-subtle))',
      position: 'relative', overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute', top: -40, right: -20, width: 200, height: 200,
        borderRadius: '50%', background: 'radial-gradient(circle, rgba(16,185,129,0.25) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />
      <div style={{ position: 'relative', zIndex: 1 }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6, padding: '3px 12px', marginBottom: 8,
          fontSize: 12, fontWeight: 600, color: '#10b981',
          background: 'rgba(16,185,129,0.12)', borderRadius: 999, border: '1px solid rgba(16,185,129,0.2)',
        }}>
          <span>🔑</span>
          <span>Permission Management</span>
        </div>
        <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)', maxWidth: 560, lineHeight: 1.6 }}>
          权限是系统功能的最小访问控制单元。在此管理权限项的创建、编辑与删除，为角色配置提供基础数据。
        </p>
      </div>
    </div>
    <div className={`split-workspace${selectedPerm ? ' split-workspace--has-selection' : ''}`}>
      <aside className="split-workspace__list">
        <div className="split-panel-toolbar">
          <PageToolbar
            meta={<><StatPill label="权限" value={permissions.length} /><StatPill label="分类" value={categories.length} tone="info" /></>}
            actions={<>
              <input className="form-input" style={{ width: 200, fontSize: 13 }} value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="搜索代码、名称、描述…" />
              <select className="form-input form-select" style={{ width: 130 }} value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}>
                <option value="">全部分类</option>
                {categories.map(c => <option key={c} value={c}>{getCategoryLabel(c)}</option>)}
              </select>
              <div className="btn-group" style={{ display: 'flex', gap: 2, background: 'var(--surface-secondary)', borderRadius: 8, padding: 2 }}>
                <button className={`btn btn--sm${viewMode === 'table' ? ' btn--active' : ''}`} onClick={() => setViewMode('table')} style={{ padding: '4px 10px', fontSize: 12 }}>📋 表格</button>
                <button className={`btn btn--sm${viewMode === 'grouped' ? ' btn--active' : ''}`} onClick={() => setViewMode('grouped')} style={{ padding: '4px 10px', fontSize: 12 }}>📦 分组</button>
              </div>
              <button className="btn btn--primary btn--sm" onClick={() => setCreateModalOpen(true)}>+ 新建权限</button>
            </>}
          />
        </div>

        {error && !selectedPerm && <div className="error-banner" style={{ margin: '0 var(--space-4) var(--space-3)' }}><span>⚠</span> {error}<button style={styles.errorClose} onClick={() => setError(null)}>×</button></div>}

        <div className="split-list-scroll" style={{ padding: 0 }}>
          {loading && permissions.length === 0 ? (
            <div className="loading-overlay"><div className="loading-spinner" /></div>
          ) : filteredPermissions.length === 0 ? (
            <div className="empty-state" style={{ padding: 40 }}>
              <div className="empty-state__icon">{searchQuery || categoryFilter ? '🔍' : '🔑'}</div>
              <p className="empty-state__text">{searchQuery || categoryFilter ? '没有匹配的权限项' : '暂无权限数据'}</p>
            </div>
          ) : viewMode === 'table' ? (
            <table className="data-table">
              <thead><tr>
                <th style={{ width: '28%' }}>权限代码</th>
                <th style={{ width: '18%' }}>名称</th>
                <th style={{ width: '14%' }}>分类</th>
                <th>描述</th>
              </tr></thead>
              <tbody>
                {filteredPermissions.map(perm => (
                  <tr key={perm.id} className={selectedPerm && (selectedPerm.perm_id || selectedPerm.permission_id || selectedPerm.id) === (perm.perm_id || perm.permission_id || perm.id) ? 'selected' : ''}
                    onClick={() => openPerm(perm)} style={{ cursor: 'pointer' }}>
                    <td><code style={css.codeBadge}>{perm.code}</code></td>
                    <td style={{ fontWeight: 500 }}>{perm.name}</td>
                    <td><span style={{ ...css.catTag, borderColor: catColor(perm.code) + '40', color: catColor(perm.code) }}>{getCategoryLabel(getPermissionCategory(perm.code))}</span></td>
                    <td style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>{perm.description || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 20 }}>
              {Object.entries(groupedPermissions).sort(([a],[b]) => getCategoryLabel(a).localeCompare(getCategoryLabel(b), 'zh-CN')).map(([category, items]) => (
                <div key={category}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, paddingBottom: 6, borderBottom: `2px solid ${catColor(items[0]?.code || '')}` }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', flex: 1 }}>{getCategoryLabel(category)}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{items.length} 项</span>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {items.map(perm => (
                      <span key={perm.id} onClick={() => openPerm(perm)} style={{
                        padding: '6px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 12,
                        background: selectedPerm && (selectedPerm.perm_id || selectedPerm.permission_id || selectedPerm.id) === (perm.perm_id || perm.permission_id || perm.id) ? 'color-mix(in srgb, ' + catColor(perm.code) + ' 12%, transparent)' : 'var(--surface-secondary)',
                        border: '0.5px solid ' + catColor(perm.code) + '30',
                        color: 'var(--text-primary)',
                        transition: 'background 0.1s',
                      }}>
                        <div style={{ fontWeight: 500 }}>{perm.name}</div>
                        <div style={{ fontSize: 10, color: 'var(--text-tertiary)', fontFamily: 'monospace' }}>{perm.code}</div>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>

      <main className="split-workspace__main">
        {selectedPerm ? (
          <div className="split-detail-scroll" style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '20px 24px 16px', borderBottom: '0.5px solid var(--border-subtle)' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 11, fontFamily: 'monospace', color: catColor(selectedPerm.code) }}>
                    {selectedPerm.code}
                  </span>
                  <span style={{
                    fontSize: 10, padding: '0 8px', lineHeight: '18px', borderRadius: 999,
                    backgroundColor: catColor(selectedPerm.code) + '15',
                    color: catColor(selectedPerm.code), fontWeight: 500,
                  }}>
                    {getCategoryLabel(getPermissionCategory(selectedPerm.code))}
                  </span>
                </div>
                <div style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)' }}>
                  {selectedPerm.name}
                </div>
              </div>
              <button className="btn btn--danger btn--sm" onClick={() => setDeleteConfirm(true)}
                style={{ fontSize: 12, padding: '6px 14px' }}>删除</button>
            </div>

            {error && <div className="error-banner" style={{ margin: '12px 24px 0' }}><span>⚠</span> {error}<button style={styles.errorClose} onClick={() => setError(null)}>×</button></div>}
            {deleteConfirm && (
              <div style={{ margin: '12px 24px 0', padding: '12px 16px', background: 'var(--status-error-bg)', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 12, justifyContent: 'space-between' }}>
                <span style={{ fontSize: 13 }}>确认删除权限 <strong>{selectedPerm.name}</strong>？</span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn--danger btn--sm" onClick={handleDelete} disabled={deleting} style={{ padding: '4px 12px', fontSize: 12 }}>{deleting ? '删除中...' : '确认删除'}</button>
                  <button className="btn btn--secondary btn--sm" onClick={() => setDeleteConfirm(false)} style={{ padding: '4px 12px', fontSize: 12 }}>取消</button>
                </div>
              </div>
            )}

            {/* Content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 24 }}>
              {/* Editable fields */}
              <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div>
                    <label style={css.label}>权限名称</label>
                    <input className="form-input" value={editName} onChange={e => setEditName(e.target.value)}
                      placeholder="输入权限名称" style={{ width: '100%', padding: '7px 10px', fontSize: 13 }} />
                  </div>
                  <div>
                    <label style={css.label}>权限描述</label>
                    <textarea className="form-input" value={editDesc} onChange={e => setEditDesc(e.target.value)}
                      placeholder="输入权限描述（可选）" rows={3}
                      style={{ width: '100%', padding: '7px 10px', fontSize: 13, resize: 'vertical', fontFamily: 'inherit' }} />
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn--primary btn--sm" onClick={handleSave}
                      disabled={saving || !editName.trim() || !hasChanges}>
                      {saving ? '保存中...' : '保存'}
                    </button>
                    {hasChanges && (
                      <button className="btn btn--secondary btn--sm"
                        onClick={() => { setEditName(selectedPerm.name); setEditDesc(selectedPerm.description || ''); }}>
                        重置
                      </button>
                    )}
                  </div>
                </div>

                {/* Stats */}
                <div style={{ display: 'flex', gap: 12, flexShrink: 0 }}>
                  <div style={{ background: 'var(--surface-secondary)', borderRadius: 8, padding: '12px 18px', textAlign: 'center', minWidth: 80 }}>
                    <div style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-primary)' }}>1</div>
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>权限 ID</div>
                  </div>
                  <div style={{ background: 'var(--surface-secondary)', borderRadius: 8, padding: '12px 18px', textAlign: 'center', minWidth: 100 }}>
                    <div style={{ fontSize: 12, fontWeight: 500, color: catColor(selectedPerm.code), wordBreak: 'break-all' }}>{selectedPerm.perm_id || selectedPerm.permission_id || selectedPerm.id}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>系统标识</div>
                  </div>
                </div>
              </div>

              {/* Metadata */}
              <div>
                <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 8 }}>元数据</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div style={{ padding: '10px 14px', background: 'var(--surface-secondary)', borderRadius: 8, border: '0.5px solid var(--border-subtle)' }}>
                    <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 2 }}>创建时间</div>
                    <div style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-primary)' }}>{new Date(selectedPerm.created_at).toLocaleString('zh-CN')}</div>
                  </div>
                  <div style={{ padding: '10px 14px', background: 'var(--surface-secondary)', borderRadius: 8, border: '0.5px solid var(--border-subtle)' }}>
                    <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 2 }}>更新时间</div>
                    <div style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-primary)' }}>{new Date(selectedPerm.updated_at).toLocaleString('zh-CN')}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="split-placeholder">
            <div className="split-placeholder__icon">🔑</div>
            <p className="split-placeholder__text">从左侧选择一个权限查看详情</p>
          </div>
        )}
      </main>
    </div>

    {/* Create Modal */}
    {createModalOpen && (
      <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
        onClick={() => setCreateModalOpen(false)}>
        <div onClick={e => e.stopPropagation()} style={{
          background: 'var(--bg-elevated)', borderRadius: 12, width: 460, maxWidth: '90vw',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)', border: '1px solid var(--border-default)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '18px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>新建权限</h3>
            <button style={{ fontSize: 20, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => setCreateModalOpen(false)}>×</button>
          </div>
          <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <label style={css.label}>权限代码</label>
              <input className="form-input" value={newPermCode} onChange={e => setNewPermCode(e.target.value)} placeholder="例如: users:create" style={{ width: '100%', padding: '7px 10px', fontSize: 13 }} />
            </div>
            <div>
              <label style={css.label}>权限名称</label>
              <input className="form-input" value={newPermName} onChange={e => setNewPermName(e.target.value)} placeholder="例如: 创建用户" style={{ width: '100%', padding: '7px 10px', fontSize: 13 }} />
            </div>
            <div>
              <label style={css.label}>描述（可选）</label>
              <textarea className="form-input" value={newPermDesc} onChange={e => setNewPermDesc(e.target.value)} placeholder="权限说明" rows={2} style={{ width: '100%', padding: '7px 10px', fontSize: 13, resize: 'vertical', fontFamily: 'inherit' }} />
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, padding: '14px 20px', borderTop: '1px solid var(--border-subtle)' }}>
            <button className="btn btn--secondary" onClick={() => setCreateModalOpen(false)}>取消</button>
            <button className="btn btn--primary" onClick={handleCreate} disabled={creating || !newPermCode.trim() || !newPermName.trim()}>
              {creating ? '创建中...' : '创建'}
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  );
};

const styles = {
  errorClose: { background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: 'var(--text-tertiary)', padding: '0 4px', lineHeight: 1 },
};

const css = {
  codeBadge: { fontSize: 12, fontFamily: "'JetBrains Mono', monospace", color: 'var(--accent-purple)', background: 'rgba(163,113,247,0.1)', padding: '2px 6px', borderRadius: 4 } as const,
  catTag: { fontSize: 11, padding: '1px 8px', borderRadius: 999, fontWeight: 500, border: '0.5px solid' } as const,
  label: { fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase' as const, letterSpacing: '0.4px', display: 'block', marginBottom: 4 } as const,
};

export default PermissionManagement;
