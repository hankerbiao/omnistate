import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { api } from '../services/api';
import type { RoleResponse, PermissionResponse, UserResponse } from '../types';
import PageToolbar, { StatPill } from './ui/PageToolbar';
import { rlmStyles as styles } from './RoleManagement.styles';

const getErrorMessage = (err: unknown, fallback: string) => {
  if (err instanceof Error) return `${fallback}: ${err.message}`;
  return fallback;
};

const getPermissionKey = (perm: PermissionResponse) =>
  perm.perm_id || perm.permission_id || perm.id;

const groupPermissions = (perms: PermissionResponse[]) => {
  const groups = new Map<string, PermissionResponse[]>();
  for (const perm of perms) {
    const group = perm.code.includes(':') ? perm.code.split(':')[0] : '其他';
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group)!.push(perm);
  }
  return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b));
};

type RoleFilter = 'all' | 'system' | 'custom';

interface RoleManagementProps {
  onNavigate?: (page: string) => void;
}

const RoleManagement: React.FC<RoleManagementProps> = ({ onNavigate }) => {
  const [roles, setRoles] = useState<RoleResponse[]>([]);
  const [permissions, setPermissions] = useState<PermissionResponse[]>([]);
  const [selectedRole, setSelectedRole] = useState<RoleResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newRoleName, setNewRoleName] = useState('');
  const [newRoleDesc, setNewRoleDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchDeleteConfirm, setBatchDeleteConfirm] = useState(false);
  const [batchDeleting, setBatchDeleting] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all');
  const [permissionSearch, setPermissionSearch] = useState('');
  const [roleUsers, setRoleUsers] = useState<UserResponse[]>([]);
  const [roleUsersLoading, setRoleUsersLoading] = useState(false);

  const initialSelectedRef = useRef(false);

  const fetchRoles = useCallback(async (roleIdToRefresh?: string, syncDrawer = false) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listRoles();
      setRoles(response.data || []);
      const targetId = roleIdToRefresh ?? (syncDrawer ? selectedRole?.role_id : undefined);
      if (targetId) {
        const updated = response.data?.find(r => r.role_id === targetId);
        if (updated) {
          setSelectedRole(updated);
          setSelectedPermissionIds(new Set(updated.permission_ids || []));
          setEditName(updated.name);
          setEditDesc(updated.description || '');
        }
      }
    } catch (err) {
      setError('获取角色列表失败');
      console.error('Fetch roles error:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedRole?.role_id]);

  const fetchPermissions = useCallback(async () => {
    try {
      const response = await api.listPermissions();
      setPermissions(response.data || []);
    } catch (err) {
      console.error('Fetch permissions error:', err);
    }
  }, []);

  useEffect(() => {
    fetchRoles();
    fetchPermissions();
  }, [fetchRoles, fetchPermissions]);

  // 默认选中第一项
  useEffect(() => {
    if (!initialSelectedRef.current && roles.length > 0 && !selectedRole) {
      initialSelectedRef.current = true;
      openRoleDrawer(roles[0]);
    }
  }, [roles, selectedRole]);

  const fetchRoleUsers = useCallback(async (roleId: string) => {
    setRoleUsersLoading(true);
    try {
      const response = await api.listUsers({ role_id: roleId, limit: 50 });
      setRoleUsers(response.data || []);
    } catch {
      setRoleUsers([]);
    } finally {
      setRoleUsersLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedRole) {
      fetchRoleUsers(selectedRole.role_id);
    } else {
      setRoleUsers([]);
    }
  }, [selectedRole, fetchRoleUsers]);

  const filteredRoles = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return roles.filter(role => {
      if (roleFilter === 'system' && !role.is_system) return false;
      if (roleFilter === 'custom' && role.is_system) return false;
      if (!q) return true;
      return (
        role.name.toLowerCase().includes(q)
        || role.role_id.toLowerCase().includes(q)
        || (role.description?.toLowerCase().includes(q) ?? false)
      );
    });
  }, [roles, searchQuery, roleFilter]);

  const filteredPermissions = useMemo(() => {
    const q = permissionSearch.trim().toLowerCase();
    if (!q) return permissions;
    return permissions.filter(perm =>
      perm.name.toLowerCase().includes(q)
      || perm.code.toLowerCase().includes(q)
      || (perm.description?.toLowerCase().includes(q) ?? false),
    );
  }, [permissions, permissionSearch]);

  const permissionGroups = useMemo(
    () => groupPermissions(filteredPermissions),
    [filteredPermissions],
  );

  const selectableRoles = useMemo(
    () => filteredRoles.filter(r => !r.is_system),
    [filteredRoles],
  );

  const openRoleDrawer = (role: RoleResponse) => {
    setSelectedRole(role);
    setSelectedPermissionIds(new Set(role.permission_ids || []));
    setEditName(role.name);
    setEditDesc(role.description || '');
    setPermissionSearch('');
    setError(null);
  };

  const closeRoleDrawer = () => {
    setSelectedRole(null);
    setPermissionSearch('');
  };

  const handleSaveBasicInfo = async () => {
    if (!selectedRole || !editName.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateRole(selectedRole.role_id, {
        name: editName.trim(),
        description: editDesc.trim() || undefined,
      });
      await fetchRoles(selectedRole.role_id);
    } catch (err) {
      setError('保存角色信息失败');
      console.error('Update role error:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleTogglePermission = (permissionId: string) => {
    setSelectedPermissionIds(prev => {
      const next = new Set(prev);
      if (next.has(permissionId)) next.delete(permissionId);
      else next.add(permissionId);
      return next;
    });
  };

  const handleToggleGroup = (groupPerms: PermissionResponse[], selectAll: boolean) => {
    setSelectedPermissionIds(prev => {
      const next = new Set(prev);
      for (const perm of groupPerms) {
        const key = getPermissionKey(perm);
        if (selectAll) next.add(key);
        else next.delete(key);
      }
      return next;
    });
  };

  const handleSavePermissions = async () => {
    if (!selectedRole) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateRolePermissions(selectedRole.role_id, {
        permission_ids: Array.from(selectedPermissionIds),
      });
      await fetchRoles(selectedRole.role_id);
    } catch (err) {
      setError('保存角色权限失败');
      console.error('Update role permissions error:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateRole = async () => {
    if (!newRoleName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await api.createRole({
        name: newRoleName.trim(),
        description: newRoleDesc.trim() || undefined,
      });
      await fetchRoles();
      setCreateModalOpen(false);
      setNewRoleName('');
      setNewRoleDesc('');
    } catch (err) {
      setError(getErrorMessage(err, '创建角色失败'));
      console.error('Create role error:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteRole = async () => {
    if (!deleteConfirm) return;
    setDeleting(true);
    setError(null);
    try {
      await api.deleteRole(deleteConfirm);
      setDeleteConfirm(null);
      if (selectedRole?.role_id === deleteConfirm) closeRoleDrawer();
      await fetchRoles();
    } catch (err) {
      setError(getErrorMessage(err, '删除角色失败'));
      console.error('Delete role error:', err);
    } finally {
      setDeleting(false);
    }
  };

  const toggleSelect = (roleId: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(roleId)) next.delete(roleId);
      else next.add(roleId);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === selectableRoles.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(selectableRoles.map(r => r.role_id)));
    }
  };

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;
    setBatchDeleting(true);
    setError(null);
    try {
      await Promise.all(Array.from(selectedIds).map(id => api.deleteRole(id)));
      setBatchDeleteConfirm(false);
      if (selectedRole && selectedIds.has(selectedRole.role_id)) closeRoleDrawer();
      setSelectedIds(new Set());
      await fetchRoles();
    } catch (err) {
      setError(getErrorMessage(err, '批量删除失败'));
      console.error('Batch delete error:', err);
    } finally {
      setBatchDeleting(false);
    }
  };

  const deleteTargetRole = deleteConfirm
    ? roles.find(r => r.role_id === deleteConfirm)
    : null;

  const hasBasicInfoChanges = selectedRole && (
    editName.trim() !== selectedRole.name
    || editDesc.trim() !== (selectedRole.description || '')
  );

  const hasPermissionChanges = selectedRole && (() => {
    const current = new Set(selectedRole.permission_ids || []);
    if (current.size !== selectedPermissionIds.size) return true;
    for (const id of selectedPermissionIds) {
      if (!current.has(id)) return true;
    }
    return false;
  })();

  const systemRoleCount = roles.filter(r => r.is_system).length;

  return (
    <>
    {/* Hero */}
    <div style={{
      margin: '0 0 16px', borderRadius: 'var(--radius-xl)', padding: '16px 24px',
      background: 'linear-gradient(135deg, #eef2ff 0%, #f5f3ff 45%, #fce7f3 100%)',
      border: '1px solid color-mix(in srgb, #8b5cf6 18%, var(--border-subtle))',
      position: 'relative', overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute', top: -40, right: -20, width: 200, height: 200,
        borderRadius: '50%', background: 'radial-gradient(circle, rgba(139,92,246,0.25) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />
      <div style={{ position: 'relative', zIndex: 1 }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6, padding: '3px 12px', marginBottom: 8,
          fontSize: 12, fontWeight: 600, color: '#8b5cf6',
          background: 'rgba(139,92,246,0.12)', borderRadius: 999, border: '1px solid rgba(139,92,246,0.2)',
        }}>
          <span>👥</span>
          <span>Role Management</span>
        </div>
        <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)', maxWidth: 560, lineHeight: 1.6 }}>
          角色是权限的集合。在此管理角色定义、为角色分配权限，并查看各角色的关联用户。
        </p>
      </div>
    </div>
    <div className={`split-workspace${selectedRole ? ' split-workspace--has-selection' : ''}`}>
      <aside className="split-workspace__list">
        <div className="split-panel-toolbar">
          <PageToolbar
            meta={(
              <>
                <StatPill label="角色" value={roles.length} />
                <StatPill label="系统" value={systemRoleCount} tone="info" />
                <StatPill label="显示" value={filteredRoles.length} />
                {selectedIds.size > 0 && (
                  <StatPill label="已选" value={selectedIds.size} tone="warning" />
                )}
              </>
            )}
            actions={(
              <>
                <input
                  className="form-input"
                  style={{ width: 220, fontSize: 13 }}
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="搜索名称、ID、描述…"
                  aria-label="搜索角色"
                />
                <select
                  className="form-input form-select"
                  style={{ width: 130 }}
                  value={roleFilter}
                  onChange={e => setRoleFilter(e.target.value as RoleFilter)}
                  aria-label="角色类型"
                >
                  <option value="all">全部</option>
                  <option value="system">系统角色</option>
                  <option value="custom">自定义</option>
                </select>
                {selectedIds.size > 0 && (
                  <button
                    type="button"
                    className="btn btn--danger btn--sm"
                    onClick={() => setBatchDeleteConfirm(true)}
                  >
                    删除 ({selectedIds.size})
                  </button>
                )}
                <button type="button" className="btn btn--primary btn--sm" onClick={() => setCreateModalOpen(true)}>
                  + 新建角色
                </button>
              </>
            )}
          />
        </div>

        {error && !selectedRole && (
          <div className="error-banner" style={{ ...styles.errorBanner, margin: '0 var(--space-4) var(--space-3)' }}>
            <span>⚠</span> {error}
            <button style={styles.errorClose} onClick={() => setError(null)}>×</button>
          </div>
        )}

        {loading && roles.length === 0 ? (
          <div className="loading-overlay">
            <div className="loading-spinner" />
          </div>
        ) : filteredRoles.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state__icon">👥</div>
            <p className="empty-state__text">
              {searchQuery || roleFilter !== 'all' ? '没有匹配的角色' : '暂无角色数据'}
            </p>
          </div>
        ) : (
          <div className="split-list-scroll" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={styles.colCheck}>
                    <input
                      type="checkbox"
                      checked={selectableRoles.length > 0 && selectedIds.size === selectableRoles.length}
                      onChange={toggleSelectAll}
                      disabled={selectableRoles.length === 0}
                      style={styles.checkbox}
                    />
                  </th>
                  <th>角色名称</th>
                  <th style={styles.colCount}>权限数</th>
                  <th style={styles.colType}>类型</th>
                </tr>
              </thead>
              <tbody>
                {filteredRoles.map(role => (
                  <tr
                    key={role.role_id}
                    className={selectedRole?.role_id === role.role_id ? 'selected' : ''}
                    onClick={() => openRoleDrawer(role)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td onClick={e => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(role.role_id)}
                        onChange={() => !role.is_system && toggleSelect(role.role_id)}
                        disabled={role.is_system}
                        style={styles.checkbox}
                      />
                    </td>
                    <td>
                      <span style={styles.roleNameCell}>{role.name}</span>
                      <span className="mono" style={styles.roleIdCell}>{role.role_id}</span>
                    </td>
                    <td>
                      <span style={styles.permCountBadge}>
                        {role.permission_ids?.length || 0}
                      </span>
                    </td>
                    <td>
                      {role.is_system ? (
                        <span className="status-badge status-badge--info">系统</span>
                      ) : (
                        <span className="status-badge status-badge--neutral">自定义</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </aside>

      <main className="split-workspace__main">
        {selectedRole ? (
          <div className="split-detail-scroll" style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>

            {/* ── Header ── */}
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
              padding: '20px 24px 16px', borderBottom: '0.5px solid var(--border-subtle)',
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--accent-primary)' }}>
                    {selectedRole.role_id}
                  </span>
                  <span style={{
                    fontSize: 10, padding: '0 8px', lineHeight: '18px', borderRadius: 999,
                    backgroundColor: selectedRole.is_system ? 'var(--status-info-bg)' : 'var(--surface-secondary)',
                    color: selectedRole.is_system ? 'var(--status-info)' : 'var(--text-secondary)',
                    fontWeight: 500,
                  }}>
                    {selectedRole.is_system ? '系统' : '自定义'}
                  </span>
                </div>
                <div style={{ fontSize: 20, fontWeight: 500, lineHeight: 1.3, color: 'var(--text-primary)' }}>
                  {selectedRole.name}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
                  {selectedRole.description || '暂无描述'}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                {!selectedRole.is_system && (
                  <button
                    className="btn btn--danger btn--sm"
                    onClick={() => setDeleteConfirm(selectedRole.role_id)}
                    style={{ fontSize: 12, padding: '6px 14px' }}
                  >
                    删除
                  </button>
                )}
              </div>
            </div>

            {/* ── Error banner ── */}
            {error && (
              <div className="error-banner" style={{ margin: '12px 24px 0' }}>
                <span>⚠</span> {error}
                <button style={styles.errorClose} onClick={() => setError(null)}>×</button>
              </div>
            )}

            {/* ── Content ── */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 24 }}>

              {/* ── Form + Stats ── */}
              <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div>
                    <label style={{ ...styles.label, marginBottom: 4 }}>角色名称</label>
                    <input
                      className="form-input"
                      value={editName}
                      onChange={e => setEditName(e.target.value)}
                      placeholder="输入角色名称"
                      disabled={selectedRole.is_system}
                      style={{ width: '100%', padding: '7px 10px', fontSize: 13 }}
                    />
                  </div>
                  <div>
                    <label style={{ ...styles.label, marginBottom: 4 }}>角色描述</label>
                    <textarea
                      className="form-input"
                      value={editDesc}
                      onChange={e => setEditDesc(e.target.value)}
                      placeholder="输入角色描述（可选）"
                      rows={2}
                      disabled={selectedRole.is_system}
                      style={{ width: '100%', padding: '7px 10px', fontSize: 13, resize: 'vertical', fontFamily: 'inherit' }}
                    />
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {!selectedRole.is_system ? (
                      <>
                        <button
                          className="btn btn--primary btn--sm"
                          onClick={handleSaveBasicInfo}
                          disabled={saving || !editName.trim() || !hasBasicInfoChanges}
                        >
                          {saving ? '保存中...' : '保存'}
                        </button>
                        {hasBasicInfoChanges && (
                          <button
                            className="btn btn--secondary btn--sm"
                            onClick={() => { setEditName(selectedRole.name); setEditDesc(selectedRole.description || ''); }}
                          >
                            重置
                          </button>
                        )}
                      </>
                    ) : (
                      <p style={{ fontSize: 12, color: 'var(--text-tertiary)', margin: 0 }}>
                        系统角色不可修改名称与描述
                      </p>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 12, flexShrink: 0 }}>
                  <div style={{ background: 'var(--surface-secondary)', borderRadius: 'var(--radius-md)', padding: '12px 18px', textAlign: 'center', minWidth: 80 }}>
                    <div style={{ fontSize: 20, fontWeight: 500, lineHeight: 1.2, color: 'var(--text-primary)' }}>{selectedPermissionIds.size}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>权限</div>
                  </div>
                  <div style={{ background: 'var(--surface-secondary)', borderRadius: 'var(--radius-md)', padding: '12px 18px', textAlign: 'center', minWidth: 80 }}>
                    <div style={{ fontSize: 20, fontWeight: 500, lineHeight: 1.2, color: 'var(--text-primary)' }}>{roleUsers.length}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>用户</div>
                  </div>
                </div>
              </div>

              {/* ── 关联用户 ── */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>关联用户</span>
                </div>
                {roleUsers.length > 0 ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {roleUsers.slice(0, 30).map(user => (
                      <span key={user.user_id} style={{
                        fontSize: 11, padding: '3px 10px', borderRadius: 999,
                        backgroundColor: 'color-mix(in srgb, var(--accent-primary) 10%, transparent)',
                        color: 'var(--accent-primary)', fontWeight: 500,
                      }}>
                        {user.username || user.user_id}
                      </span>
                    ))}
                    {roleUsers.length > 30 && (
                      <span style={{ fontSize: 11, color: 'var(--text-tertiary)', padding: '3px 0' }}>+{roleUsers.length - 30} 人</span>
                    )}
                  </div>
                ) : (
                  <p style={{ fontSize: 12, color: 'var(--text-tertiary)', margin: 0 }}>
                    {roleUsersLoading ? '加载中...' : '暂无用户关联此角色'}
                  </p>
                )}
              </div>

              {/* ── 权限配置 ── */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>权限配置</span>
                    <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                      {selectedPermissionIds.size} / {permissions.length} 已选
                    </span>
                    {onNavigate && (
                      <button
                        type="button"
                        style={{ fontSize: 11, color: 'var(--accent-primary)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline', padding: 0 }}
                        onClick={(e) => { e.stopPropagation(); onNavigate('permissions'); }}
                      >
                        管理权限
                      </button>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input
                      className="form-input"
                      value={permissionSearch}
                      onChange={e => setPermissionSearch(e.target.value)}
                      placeholder="搜索权限..."
                      style={{ width: 180, padding: '5px 10px', fontSize: 11 }}
                    />
                    <button
                      className="btn btn--primary btn--sm"
                      onClick={handleSavePermissions}
                      disabled={saving || !hasPermissionChanges}
                      style={{ padding: '5px 14px', fontSize: 11 }}
                    >
                      {saving ? '保存中...' : '保存'}
                    </button>
                  </div>
                </div>

                {permissionGroups.length === 0 ? (
                  <p style={{ fontSize: 12, color: 'var(--text-tertiary)', textAlign: 'center', padding: 24 }}>
                    {permissionSearch ? '没有匹配的权限' : '暂无权限数据'}
                  </p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {permissionGroups.map(([groupName, groupPerms]) => {
                      const selectedInGroup = groupPerms.filter(p =>
                        selectedPermissionIds.has(getPermissionKey(p)),
                      ).length;
                      const allSelected = selectedInGroup === groupPerms.length;
                      const someSelected = selectedInGroup > 0 && !allSelected;
                      return (
                        <div key={groupName} style={{
                          display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center',
                          padding: '10px 14px', background: 'var(--surface-secondary)',
                          borderRadius: 'var(--radius-md)',
                        }}>
                          <label style={{
                            display: 'inline-flex', alignItems: 'center', gap: 4, cursor: 'pointer',
                            fontSize: 11, fontWeight: 500, color: 'var(--text-tertiary)', minWidth: 64,
                          }}>
                            <input
                              type="checkbox"
                              checked={allSelected}
                              ref={el => { if (el) el.indeterminate = someSelected; }}
                              onChange={() => handleToggleGroup(groupPerms, !allSelected)}
                              style={{ width: 12, height: 12, accentColor: 'var(--accent-primary)' }}
                            />
                            {groupName}
                          </label>
                          {groupPerms.map(perm => {
                            const permKey = getPermissionKey(perm);
                            const checked = selectedPermissionIds.has(permKey);
                            return (
                              <label key={permKey} style={{
                                display: 'inline-flex', alignItems: 'center', gap: 4,
                                fontSize: 11, padding: '2px 10px', borderRadius: 999, cursor: 'pointer',
                                border: checked ? '0.5px solid var(--accent-primary)' : '0.5px solid var(--border-subtle)',
                                backgroundColor: checked ? 'color-mix(in srgb, var(--accent-primary) 8%, transparent)' : 'transparent',
                                color: checked ? 'var(--accent-primary)' : 'var(--text-secondary)',
                                fontWeight: checked ? 500 : 400,
                                transition: 'all 0.1s',
                              }}>
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() => handleTogglePermission(permKey)}
                                  style={{ display: 'none' }}
                                />
                                {perm.name}
                              </label>
                            );
                          })}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

            </div>
          </div>
        ) : (
          <div className="empty-state" style={{ height: '100%' }}>
            <div className="empty-state__icon">👈</div>
            <p className="empty-state__text">从左侧选择角色进行配置</p>
          </div>
        )}
      </main>
    </div>

      {/* Create Role Modal */}
      {createModalOpen && (
        <div className="modal-overlay" onClick={() => setCreateModalOpen(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">新建角色</h3>
              <button className="modal__close" onClick={() => setCreateModalOpen(false)}>×</button>
            </div>
            <div className="modal__body">
              {error && (
                <div className="error-banner" style={{ marginBottom: 16 }}>
                  <span>⚠</span> {error}
                </div>
              )}
              <div style={styles.formGroup}>
                <label style={styles.label}>角色名称 *</label>
                <input
                  className="form-input"
                  value={newRoleName}
                  onChange={e => setNewRoleName(e.target.value)}
                  placeholder="输入角色名称"
                  autoFocus
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>角色描述</label>
                <textarea
                  className="form-input"
                  style={styles.textarea}
                  value={newRoleDesc}
                  onChange={e => setNewRoleDesc(e.target.value)}
                  placeholder="输入角色描述（可选）"
                  rows={3}
                />
              </div>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setCreateModalOpen(false)}>
                取消
              </button>
              <button
                className="btn btn--primary"
                onClick={handleCreateRole}
                disabled={creating || !newRoleName.trim()}
              >
                {creating ? '创建中...' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="modal-overlay" onClick={() => setDeleteConfirm(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">确认删除</h3>
              <button className="modal__close" onClick={() => setDeleteConfirm(null)}>×</button>
            </div>
            <div className="modal__body">
              <p style={styles.confirmText}>
                确定要删除角色 <strong>{deleteTargetRole?.name || deleteConfirm}</strong> 吗？此操作不可恢复。
              </p>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setDeleteConfirm(null)}>
                取消
              </button>
              <button
                className="btn btn--danger"
                onClick={handleDeleteRole}
                disabled={deleting}
              >
                {deleting ? '删除中...' : '确认删除'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Batch Delete Confirmation */}
      {batchDeleteConfirm && (
        <div className="modal-overlay" onClick={() => setBatchDeleteConfirm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <h3 className="modal__title">确认批量删除</h3>
              <button className="modal__close" onClick={() => setBatchDeleteConfirm(false)}>×</button>
            </div>
            <div className="modal__body">
              <p style={styles.confirmText}>
                确定要删除选中的 <strong>{selectedIds.size}</strong> 个角色吗？此操作不可恢复。
              </p>
            </div>
            <div className="modal__footer">
              <button className="btn btn--secondary" onClick={() => setBatchDeleteConfirm(false)}>
                取消
              </button>
              <button
                className="btn btn--danger"
                onClick={handleBatchDelete}
                disabled={batchDeleting}
              >
                {batchDeleting ? '删除中...' : `删除 ${selectedIds.size} 项`}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .perm-tile:hover:not(:has(input:disabled)) {
          background-color: var(--surface-hover);
          border-color: var(--accent-primary);
        }
      `}</style>
    </>
  );
};

export default RoleManagement;
