import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { PermissionResponse } from '../types';

const getErrorMessage = (err: unknown, fallback: string) => {
  if (err instanceof Error) return `${fallback}: ${err.message}`;
  return fallback;
};

const PermissionManagement: React.FC = () => {
  const [permissions, setPermissions] = useState<PermissionResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newPermCode, setNewPermCode] = useState('');
  const [newPermName, setNewPermName] = useState('');
  const [newPermDesc, setNewPermDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
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
      setNewPermCode('');
      setNewPermName('');
      setNewPermDesc('');
    } catch (err) {
      setError(getErrorMessage(err, '创建权限失败'));
      console.error('Create permission error:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    setDeleting(true);
    setError(null);
    try {
      await api.deletePermission(deleteConfirm);
      setDeleteConfirm(null);
      await fetchPermissions();
    } catch (err) {
      setError(getErrorMessage(err, '删除权限失败'));
      console.error('Delete permission error:', err);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="workspace" style={styles.container}>
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>权限列表</h2>
          <span style={styles.subtitle}>共 {permissions.length} 个权限项</span>
        </div>
        <button className="btn btn--primary btn--sm" onClick={() => setCreateModalOpen(true)}>
          + 新建
        </button>
      </div>

      {error && (
        <div style={styles.error}>
          <span>⚠</span> {error}
          <button style={styles.errorClose} onClick={() => setError(null)}>×</button>
        </div>
      )}

      {loading ? (
        <div className="loading-overlay">
          <div className="loading-spinner" />
        </div>
      ) : permissions.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">🔑</div>
          <p className="empty-state__text">暂无权限数据</p>
        </div>
      ) : (
        <div style={styles.grid}>
          {permissions.map(perm => (
            <div key={perm.id} style={styles.card}>
              <div style={styles.cardContent}>
                <div style={styles.permName}>{perm.name}</div>
                <div style={styles.permCode}>{perm.code}</div>
                {perm.description && (
                  <div style={styles.permDesc}>{perm.description}</div>
                )}
              </div>
              <button
                style={styles.deleteBtn}
                onClick={() => setDeleteConfirm(perm.permission_id || perm.id)}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {createModalOpen && (
        <div style={styles.modalOverlay} onClick={() => setCreateModalOpen(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>新建权限</h3>
              <button style={styles.modalClose} onClick={() => setCreateModalOpen(false)}>×</button>
            </div>
            <div style={styles.modalBody}>
              <div style={styles.formGroup}>
                <label style={styles.label}>权限代码 *</label>
                <input
                  style={styles.input}
                  value={newPermCode}
                  onChange={e => setNewPermCode(e.target.value)}
                  placeholder="例如: work_items:read"
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>权限名称 *</label>
                <input
                  style={styles.input}
                  value={newPermName}
                  onChange={e => setNewPermName(e.target.value)}
                  placeholder="例如: 工作流读取"
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>描述</label>
                <textarea
                  style={styles.textarea}
                  value={newPermDesc}
                  onChange={e => setNewPermDesc(e.target.value)}
                  placeholder="可选描述"
                  rows={3}
                />
              </div>
            </div>
            <div style={styles.modalFooter}>
              <button style={styles.cancelBtn} onClick={() => setCreateModalOpen(false)}>取消</button>
              <button
                style={styles.saveBtn}
                onClick={handleCreate}
                disabled={creating || !newPermCode.trim() || !newPermName.trim()}
              >
                {creating ? '创建中...' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div style={styles.modalOverlay} onClick={() => setDeleteConfirm(null)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>确认删除</h3>
              <button style={styles.modalClose} onClick={() => setDeleteConfirm(null)}>×</button>
            </div>
            <div style={styles.modalBody}>
              <p style={{ fontSize: '14px', color: 'var(--text-primary)', margin: 0 }}>
                确定要删除权限 <strong>{deleteConfirm}</strong> 吗？
              </p>
            </div>
            <div style={styles.modalFooter}>
              <button style={styles.cancelBtn} onClick={() => setDeleteConfirm(null)}>取消</button>
              <button
                style={{
                  ...styles.dangerBtn,
                  ...(deleting ? { opacity: 0.6, cursor: 'wait' } : {}),
                }}
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? '删除中...' : '确认删除'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, any> = {
  container: {
    padding: '24px',
    height: '100%',
    overflow: 'auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 600,
  },
  subtitle: {
    fontSize: '13px',
    color: 'var(--text-tertiary)',
    marginTop: '4px',
    display: 'block',
  },
  error: {
    padding: '8px 16px',
    backgroundColor: 'var(--status-error-bg)',
    color: 'var(--status-error)',
    borderRadius: '8px',
    fontSize: '13px',
    marginBottom: '12px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  errorClose: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: '16px',
    color: 'var(--status-error)',
    padding: '0 4px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
    gap: '12px',
  },
  card: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: '16px',
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-lg)',
  },
  cardContent: {
    flex: 1,
  },
  permName: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: '4px',
  },
  permCode: {
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-primary)',
    marginBottom: '4px',
  },
  permDesc: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
  },
  deleteBtn: {
    padding: '4px 8px',
    fontSize: '12px',
    color: 'var(--status-error)',
    background: 'none',
    border: '1px solid transparent',
    borderRadius: '4px',
    cursor: 'pointer',
    opacity: 0.5,
    flexShrink: 0,
  },
  // Modal
  modalOverlay: {
    position: 'fixed' as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modal: {
    width: '480px',
    maxWidth: '90vw',
    backgroundColor: 'var(--surface-primary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    overflow: 'hidden',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '18px 24px',
    borderBottom: '1px solid var(--border-subtle)',
  },
  modalTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    margin: 0,
  },
  modalClose: {
    padding: '0 8px',
    fontSize: '20px',
    background: 'none',
    border: 'none',
    color: 'var(--text-tertiary)',
    cursor: 'pointer',
  },
  modalBody: {
    padding: '24px',
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
  input: {
    width: '100%',
    padding: '10px 14px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
    boxSizing: 'border-box' as const,
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
    resize: 'vertical' as const,
    fontFamily: 'inherit',
    boxSizing: 'border-box' as const,
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
    padding: '18px 24px',
    borderTop: '1px solid var(--border-subtle)',
  },
  saveBtn: {
    padding: '10px 18px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'white',
    backgroundColor: 'var(--accent-primary)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  cancelBtn: {
    padding: '10px 18px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'transparent',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  dangerBtn: {
    padding: '10px 18px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'white',
    backgroundColor: 'var(--status-error)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
};

export default PermissionManagement;
