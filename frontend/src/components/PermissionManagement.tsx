import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../services/api';
import type { PermissionResponse } from '../types';
import PageToolbar, { StatPill } from './ui/PageToolbar';

type ViewMode = 'table' | 'grouped';

const CATEGORY_LABELS: Record<string, string> = {
  users: '用户管理',
  roles: '角色管理',
  permissions: '权限管理',
  requirements: '需求管理',
  test_cases: '测试用例',
  work_items: '工作流',
  assets: '资产管理',
  execution_tasks: '执行任务',
  execution_agents: '执行 Agent',
  execution: '执行管理',
  automation: '自动化',
  catalog: '目录管理',
  duts: '被测设备',
  navigation: '导航配置',
  nav: '公共导航',
  terminal: '终端',
  other: '其他',
};

const getErrorMessage = (err: unknown, fallback: string) => {
  if (err instanceof Error) return `${fallback}: ${err.message}`;
  return fallback;
};

const getPermissionCategory = (code: string): string => {
  const [resource] = code.split(':');
  return resource || 'other';
};

const getCategoryLabel = (category: string): string =>
  CATEGORY_LABELS[category] || category;

const IconSearch = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

const IconTable = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
    <rect x="3" y="3" width="18" height="18" rx="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="3" y1="15" x2="21" y2="15" /><line x1="9" y1="3" x2="9" y2="21" />
  </svg>
);

const IconGrid = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
    <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
    <rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
  </svg>
);

const PermissionManagement: React.FC = () => {
  const [permissions, setPermissions] = useState<PermissionResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newPermCode, setNewPermCode] = useState('');
  const [newPermName, setNewPermName] = useState('');
  const [newPermDesc, setNewPermDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<PermissionResponse | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchPermissions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listPermissions();
      setPermissions(response.data || []);
    } catch (err) {
      setError(getErrorMessage(err, '获取权限列表失败'));
      console.error('Fetch permissions error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPermissions();
  }, [fetchPermissions]);

  const categories = useMemo(() => {
    const set = new Set(permissions.map(p => getPermissionCategory(p.code)));
    return Array.from(set).sort((a, b) =>
      getCategoryLabel(a).localeCompare(getCategoryLabel(b), 'zh-CN'),
    );
  }, [permissions]);

  const filteredPermissions = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return permissions
      .filter(perm => {
        if (categoryFilter && getPermissionCategory(perm.code) !== categoryFilter) {
          return false;
        }
        if (!q) return true;
        return (
          perm.code.toLowerCase().includes(q)
          || perm.name.toLowerCase().includes(q)
          || (perm.description?.toLowerCase().includes(q) ?? false)
        );
      })
      .sort((a, b) => a.code.localeCompare(b.code));
  }, [permissions, searchQuery, categoryFilter]);

  const groupedPermissions = useMemo(() => {
    return filteredPermissions.reduce<Record<string, PermissionResponse[]>>((acc, perm) => {
      const category = getPermissionCategory(perm.code);
      if (!acc[category]) acc[category] = [];
      acc[category].push(perm);
      return acc;
    }, {});
  }, [filteredPermissions]);

  const stats = useMemo(() => ({
    total: permissions.length,
    filtered: filteredPermissions.length,
    categories: categories.length,
  }), [permissions.length, filteredPermissions.length, categories.length]);

  const resetCreateForm = () => {
    setNewPermCode('');
    setNewPermName('');
    setNewPermDesc('');
  };

  const openCreateModal = () => {
    resetCreateForm();
    setCreateModalOpen(true);
  };

  const handleCreate = async () => {
    if (!newPermCode.trim() || !newPermName.trim()) {
      setError('权限代码和名称不能为空');
      return;
    }
    setCreating(true);
    setError(null);
    try {
      await api.createPermission({
        perm_id: newPermCode.trim(),
        code: newPermCode.trim(),
        name: newPermName.trim(),
        description: newPermDesc.trim() || undefined,
      });
      await fetchPermissions();
      setCreateModalOpen(false);
      resetCreateForm();
    } catch (err) {
      setError(getErrorMessage(err, '创建权限失败'));
      console.error('Create permission error:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setError(null);
    try {
      await api.deletePermission(deleteTarget.perm_id || deleteTarget.permission_id || deleteTarget.id);
      setDeleteTarget(null);
      await fetchPermissions();
    } catch (err) {
      setError(getErrorMessage(err, '删除权限失败'));
      console.error('Delete permission error:', err);
    } finally {
      setDeleting(false);
    }
  };

  const renderEmptyState = () => (
    <div className="empty-state" style={styles.emptyState}>
      <div className="empty-state__icon">{searchQuery || categoryFilter ? '🔍' : '🔑'}</div>
      <p className="empty-state__text">
        {searchQuery || categoryFilter ? '没有匹配的权限项' : '暂无权限数据'}
      </p>
      {!searchQuery && !categoryFilter && (
        <button type="button" className="btn btn--primary btn--sm" onClick={openCreateModal}>
          创建第一个权限
        </button>
      )}
    </div>
  );

  const renderTableView = () => (
    <div style={styles.tableWrap}>
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col" style={{ width: '28%' }}>权限代码</th>
            <th scope="col" style={{ width: '18%' }}>名称</th>
            <th scope="col" style={{ width: '14%' }}>分类</th>
            <th scope="col">描述</th>
            <th scope="col" style={{ width: '88px', textAlign: 'right' }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {filteredPermissions.map(perm => {
            const category = getPermissionCategory(perm.code);
            return (
              <tr key={perm.id}>
                <td>
                  <code style={styles.codeBadge}>{perm.code}</code>
                </td>
                <td style={{ fontWeight: 500 }}>{perm.name}</td>
                <td>
                  <span style={styles.categoryTag}>{getCategoryLabel(category)}</span>
                </td>
                <td style={{ color: 'var(--text-tertiary)' }}>
                  {perm.description || '—'}
                </td>
                <td style={{ textAlign: 'right' }}>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    style={styles.deleteAction}
                    onClick={() => setDeleteTarget(perm)}
                    aria-label={`删除权限 ${perm.name}`}
                  >
                    删除
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  const renderGroupedView = () => (
    <div style={styles.groupedWrap}>
      {Object.entries(groupedPermissions)
        .sort(([a], [b]) => getCategoryLabel(a).localeCompare(getCategoryLabel(b), 'zh-CN'))
        .map(([category, items]) => (
          <section key={category} style={styles.categorySection}>
            <div style={styles.categoryHeader}>
              <h3 style={styles.categoryTitle}>{getCategoryLabel(category)}</h3>
              <span style={styles.categoryCount}>{items.length} 项</span>
            </div>
            <div style={styles.cardGrid}>
              {items.map(perm => (
                <article key={perm.id} style={styles.permCard}>
                  <div style={styles.permCardBody}>
                    <div style={styles.permCardName}>{perm.name}</div>
                    <code style={styles.codeBadge}>{perm.code}</code>
                    <p style={styles.permCardDesc}>
                      {perm.description || '暂无说明，可在数据库或 init_rbac 脚本中维护。'}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    style={styles.deleteAction}
                    onClick={() => setDeleteTarget(perm)}
                    aria-label={`删除权限 ${perm.name}`}
                  >
                    删除
                  </button>
                </article>
              ))}
            </div>
          </section>
        ))}
    </div>
  );

  return (
    <div className="page-content">
      <PageToolbar
        meta={(
          <>
            <StatPill label="权限总数" value={stats.total} />
            <StatPill label="当前显示" value={stats.filtered} tone="info" />
            <StatPill label="分类" value={stats.categories} />
          </>
        )}
        actions={(
          <button type="button" className="btn btn--primary btn--sm" onClick={openCreateModal}>
            + 新建权限
          </button>
        )}
      />

      {error && (
        <div className="error-banner" style={styles.errorBanner}>
          <span>⚠ {error}</span>
          <button type="button" style={styles.errorClose} onClick={() => setError(null)} aria-label="关闭错误提示">
            ×
          </button>
        </div>
      )}

      <div className="surface-card" style={styles.mainPanel}>
        <div style={styles.toolbar}>
          <div style={styles.searchWrap}>
            <span style={styles.searchIcon} aria-hidden="true"><IconSearch /></span>
            <input
              id="perm-search"
              type="search"
              style={styles.searchInput}
              placeholder="搜索代码、名称或描述…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              aria-label="搜索权限"
            />
          </div>

          <select
            id="perm-category-filter"
            style={styles.filterSelect}
            value={categoryFilter}
            onChange={e => setCategoryFilter(e.target.value)}
            aria-label="按分类筛选"
          >
            <option value="">全部分类</option>
            {categories.map(cat => (
              <option key={cat} value={cat}>{getCategoryLabel(cat)}</option>
            ))}
          </select>

          <div style={styles.viewToggle} role="group" aria-label="视图切换">
            <button
              type="button"
              style={{ ...styles.viewBtn, ...(viewMode === 'table' ? styles.viewBtnActive : {}) }}
              onClick={() => setViewMode('table')}
              title="表格视图"
              aria-pressed={viewMode === 'table'}
            >
              <IconTable />
            </button>
            <button
              type="button"
              style={{ ...styles.viewBtn, ...(viewMode === 'grouped' ? styles.viewBtnActive : {}) }}
              onClick={() => setViewMode('grouped')}
              title="分组卡片视图"
              aria-pressed={viewMode === 'grouped'}
            >
              <IconGrid />
            </button>
          </div>

          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={fetchPermissions}
            disabled={loading}
          >
            {loading ? '刷新中…' : '刷新'}
          </button>
        </div>

        {loading && permissions.length === 0 ? (
          <div className="loading-overlay" style={styles.loadingBox}>
            <div className="loading-spinner" />
          </div>
        ) : filteredPermissions.length === 0 ? (
          renderEmptyState()
        ) : viewMode === 'table' ? (
          renderTableView()
        ) : (
          renderGroupedView()
        )}
      </div>

      {createModalOpen && (
        <div className="modal-overlay" onClick={() => setCreateModalOpen(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} role="dialog" aria-labelledby="create-perm-title">
            <div className="modal__header">
              <h2 id="create-perm-title" className="modal__title">新建权限</h2>
              <button type="button" className="modal__close" onClick={() => setCreateModalOpen(false)} aria-label="关闭">
                ×
              </button>
            </div>
            <div className="modal__body">
              <div style={styles.formGroup}>
                <label htmlFor="perm-code" style={styles.label}>权限代码 *</label>
                <input
                  id="perm-code"
                  style={styles.input}
                  value={newPermCode}
                  onChange={e => setNewPermCode(e.target.value)}
                  placeholder="例如: work_items:read"
                  autoFocus
                />
                <span style={styles.fieldHint}>建议使用 资源:操作 格式，创建后不可修改</span>
              </div>
              <div style={styles.formGroup}>
                <label htmlFor="perm-name" style={styles.label}>权限名称 *</label>
                <input
                  id="perm-name"
                  style={styles.input}
                  value={newPermName}
                  onChange={e => setNewPermName(e.target.value)}
                  placeholder="例如: 工作流读取"
                />
              </div>
              <div style={styles.formGroup}>
                <label htmlFor="perm-desc" style={styles.label}>描述</label>
                <textarea
                  id="perm-desc"
                  style={styles.textarea}
                  value={newPermDesc}
                  onChange={e => setNewPermDesc(e.target.value)}
                  placeholder="可选，说明该权限的用途"
                  rows={3}
                />
              </div>
            </div>
            <div className="modal__footer">
              <button type="button" className="btn btn--secondary" onClick={() => setCreateModalOpen(false)}>
                取消
              </button>
              <button
                type="button"
                className="btn btn--primary"
                onClick={handleCreate}
                disabled={creating || !newPermCode.trim() || !newPermName.trim()}
              >
                {creating ? '创建中…' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} role="dialog" aria-labelledby="delete-perm-title">
            <div className="modal__header">
              <h2 id="delete-perm-title" className="modal__title">确认删除</h2>
              <button type="button" className="modal__close" onClick={() => setDeleteTarget(null)} aria-label="关闭">
                ×
              </button>
            </div>
            <div className="modal__body">
              <p style={styles.deleteText}>
                确定要删除权限 <strong>{deleteTarget.name}</strong> 吗？
              </p>
              <div style={styles.deleteMeta}>
                <code style={styles.codeBadge}>{deleteTarget.code}</code>
                {deleteTarget.description && (
                  <span style={styles.deleteDesc}>{deleteTarget.description}</span>
                )}
              </div>
              <p style={styles.deleteWarning}>
                删除后，已绑定该权限的角色将失去对应授权，此操作不可撤销。
              </p>
            </div>
            <div className="modal__footer">
              <button type="button" className="btn btn--secondary" onClick={() => setDeleteTarget(null)}>
                取消
              </button>
              <button
                type="button"
                className="btn btn--danger"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? '删除中…' : '确认删除'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  page: {
    padding: 'var(--space-6)',
    maxWidth: '1200px',
    margin: '0 auto',
  },
  pageHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 'var(--space-4)',
    marginBottom: 'var(--space-6)',
    flexWrap: 'wrap',
  },
  pageTitle: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  pageDesc: {
    margin: '6px 0 0',
    fontSize: '13px',
    color: 'var(--text-tertiary)',
    lineHeight: 1.5,
    maxWidth: '560px',
  },
  inlineCode: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
    padding: '1px 6px',
    borderRadius: '4px',
    backgroundColor: 'var(--surface-secondary)',
    color: 'var(--accent-primary)',
  },
  statsGrid: {
    marginBottom: 'var(--space-5)',
  },
  errorBanner: {
    marginBottom: 'var(--space-4)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  errorClose: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: '18px',
    color: 'inherit',
    padding: '0 4px',
    lineHeight: 1,
  },
  mainPanel: {
    padding: 0,
    overflow: 'hidden',
  },
  toolbar: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: '10px',
    padding: '14px 16px',
    borderBottom: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--surface-secondary)',
  },
  searchWrap: {
    position: 'relative',
    flex: '1 1 200px',
    minWidth: '180px',
  },
  searchIcon: {
    position: 'absolute',
    left: '12px',
    top: '50%',
    transform: 'translateY(-50%)',
    color: 'var(--text-tertiary)',
    display: 'flex',
    pointerEvents: 'none',
  },
  searchInput: {
    width: '100%',
    padding: '8px 12px 8px 36px',
    fontSize: '13px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
    boxSizing: 'border-box',
  },
  filterSelect: {
    padding: '8px 32px 8px 12px',
    fontSize: '13px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
    minWidth: '140px',
  },
  viewToggle: {
    display: 'flex',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    overflow: 'hidden',
  },
  viewBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '7px 10px',
    backgroundColor: 'var(--surface-primary)',
    border: 'none',
    color: 'var(--text-tertiary)',
    cursor: 'pointer',
  },
  viewBtnActive: {
    backgroundColor: 'var(--accent-primary)',
    color: 'white',
  },
  loadingBox: {
    minHeight: '240px',
  },
  emptyState: {
    padding: '48px 24px',
  },
  tableWrap: {
    overflowX: 'auto',
  },
  codeBadge: {
    display: 'inline-block',
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
    color: 'var(--accent-primary)',
    backgroundColor: 'rgba(37, 99, 235, 0.08)',
    padding: '2px 8px',
    borderRadius: '4px',
  },
  categoryTag: {
    display: 'inline-block',
    fontSize: '12px',
    padding: '2px 8px',
    borderRadius: '999px',
    backgroundColor: 'var(--surface-secondary)',
    color: 'var(--text-secondary)',
  },
  deleteAction: {
    color: 'var(--status-error)',
  },
  groupedWrap: {
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  categorySection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  categoryHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  categoryTitle: {
    margin: 0,
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  categoryCount: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    padding: '1px 8px',
    borderRadius: '999px',
    backgroundColor: 'var(--surface-secondary)',
  },
  cardGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '10px',
  },
  permCard: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '8px',
    padding: '14px 16px',
    backgroundColor: 'var(--surface-secondary)',
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-md)',
  },
  permCardBody: {
    flex: 1,
    minWidth: 0,
  },
  permCardName: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: '6px',
  },
  permCardDesc: {
    margin: '8px 0 0',
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    lineHeight: 1.4,
  },
  formGroup: {
    marginBottom: '18px',
  },
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    marginBottom: '8px',
  },
  fieldHint: {
    display: 'block',
    marginTop: '6px',
    fontSize: '12px',
    color: 'var(--text-tertiary)',
  },
  input: {
    width: '100%',
    padding: '10px 14px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
    boxSizing: 'border-box',
  },
  textarea: {
    width: '100%',
    padding: '10px 14px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
    resize: 'vertical',
    fontFamily: 'inherit',
    boxSizing: 'border-box',
  },
  deleteText: {
    fontSize: '14px',
    color: 'var(--text-primary)',
    margin: '0 0 12px',
  },
  deleteMeta: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    padding: '12px',
    backgroundColor: 'var(--surface-secondary)',
    borderRadius: 'var(--radius-md)',
    marginBottom: '12px',
  },
  deleteDesc: {
    fontSize: '13px',
    color: 'var(--text-tertiary)',
  },
  deleteWarning: {
    fontSize: '12px',
    color: 'var(--status-error)',
    margin: 0,
    lineHeight: 1.5,
  },
};

export default PermissionManagement;
