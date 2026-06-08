import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../services/api';
import type { UserResponse, RoleResponse, NavigationPageResponse, UserNavigationResponse } from '../types';
import PageToolbar, { StatPill } from './ui/PageToolbar';

type EditableUserField = 'username' | 'email';

const emptyNewUser = {
  user_id: '',
  username: '',
  password: '',
  email: '',
  role_ids: [] as string[],
};

interface UserManagementProps {
  onNavigate?: (page: string) => void;
}

const getErrorMessage = (err: unknown, fallback: string) => {
  if (err instanceof Error) {
    return `${fallback}: ${err.message}`;
  }
  return fallback;
};

const UserManagement: React.FC<UserManagementProps> = ({ onNavigate }) => {
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [roles, setRoles] = useState<RoleResponse[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingField, setEditingField] = useState<EditableUserField | null>(null);
  const [editValue, setEditValue] = useState('');
  const [selectedRoleIds, setSelectedRoleIds] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newUser, setNewUser] = useState(emptyNewUser);
  const [creating, setCreating] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchDeleteConfirm, setBatchDeleteConfirm] = useState(false);
  const [batchDeleting, setBatchDeleting] = useState(false);
  const [passwordModal, setPasswordModal] = useState(false);
  const [passwordValue, setPasswordValue] = useState('');
  const [resetting, setResetting] = useState(false);
  const [togglingStatus, setTogglingStatus] = useState(false);
  const [navPages, setNavPages] = useState<NavigationPageResponse[]>([]);
  const [userNav, setUserNav] = useState<UserNavigationResponse | null>(null);
  const [selectedNavViews, setSelectedNavViews] = useState<Set<string>>(new Set());
  const [navLoading, setNavLoading] = useState(false);
  const [navSaving, setNavSaving] = useState(false);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: { status?: string; search?: string; limit?: number } = { limit: 200 };
      if (filterStatus) {
        params.status = filterStatus;
      }
      if (searchQuery.trim()) {
        params.search = searchQuery.trim();
      }
      const response = await api.listUsers(params);
      const nextUsers = response.data || [];
      setUsers(nextUsers);
      setSelectedUser(current => {
        if (!current) return null;
        return nextUsers.find(user => user.user_id === current.user_id) || null;
      });
    } catch (err) {
      setError(getErrorMessage(err, '获取用户列表失败'));
      console.error('Fetch users error:', err);
    } finally {
      setLoading(false);
    }
  }, [filterStatus, searchQuery]);

  const fetchRoles = useCallback(async () => {
    try {
      const response = await api.listRoles();
      setRoles(response.data || []);
    } catch (err) {
      console.error('Fetch roles error:', err);
    }
  }, []);

  const fetchNavPages = useCallback(async () => {
    try {
      const response = await api.listNavigationPages({ include_inactive: false });
      const pages = (response.data || []).slice().sort((a, b) => a.order - b.order || a.view.localeCompare(b.view));
      setNavPages(pages);
    } catch (err) {
      console.error('Fetch navigation pages error:', err);
    }
  }, []);

  const fetchUserNavigation = useCallback(async (userId: string) => {
    setNavLoading(true);
    try {
      const response = await api.getUserNavigation(userId);
      const data = response.data;
      setUserNav(data || null);
      setSelectedNavViews(new Set(data?.allowed_nav_views || []));
    } catch (err) {
      console.error('Fetch user navigation error:', err);
      setUserNav(null);
      setSelectedNavViews(new Set());
    } finally {
      setNavLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
    fetchRoles();
    fetchNavPages();
  }, [fetchUsers, fetchRoles, fetchNavPages]);

  useEffect(() => {
    if (selectedUser) {
      fetchUserNavigation(selectedUser.user_id);
    } else {
      setUserNav(null);
      setSelectedNavViews(new Set());
    }
  }, [selectedUser?.user_id, fetchUserNavigation]);

  const handleSelectUser = (user: UserResponse) => {
    setSelectedUser(user);
    setSelectedRoleIds(new Set(user.role_ids));
    setEditingField(null);
  };

  const handleEditField = (field: EditableUserField, currentValue: string) => {
    setEditingField(field);
    setEditValue(currentValue || '');
    setError(null);
  };

  const handleSaveField = async () => {
    if (!selectedUser || !editingField) return;
    const value = editValue.trim();
    if (editingField === 'username' && !value) {
      setError('用户名不能为空');
      return;
    }

    setSaving(true);
    try {
      const data = { [editingField]: value };
      await api.updateUser(selectedUser.user_id, data);
      await fetchUsers();
      setEditingField(null);
      setEditValue('');
    } catch (err) {
      setError(getErrorMessage(err, '保存失败'));
      console.error('Update user error:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditingField(null);
    setEditValue('');
  };

  const handleToggleRole = (roleId: string) => {
    setError(null);
    setSelectedRoleIds(prev => {
      const next = new Set(prev);
      if (next.has(roleId)) {
        next.delete(roleId);
      } else {
        next.add(roleId);
      }
      return next;
    });
  };

  const handleSaveRoles = async () => {
    if (!selectedUser) return;

    setSaving(true);
    try {
      await api.updateUserRoles(selectedUser.user_id, {
        role_ids: Array.from(selectedRoleIds),
      });
      await fetchUsers();
      await fetchUserNavigation(selectedUser.user_id);
    } catch (err) {
      setError(getErrorMessage(err, '保存角色失败'));
      console.error('Update user roles error:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateUser = async () => {
    if (!newUser.user_id.trim() || !newUser.username.trim() || !newUser.password.trim()) {
      setError('请填写必填字段');
      return;
    }

    setCreating(true);
    try {
      await api.createUser({
        user_id: newUser.user_id.trim(),
        username: newUser.username.trim(),
        password: newUser.password,
        email: newUser.email.trim() || undefined,
        role_ids: newUser.role_ids,
      });
      await fetchUsers();
      setCreateModalOpen(false);
      setNewUser(emptyNewUser);
    } catch (err) {
      setError(getErrorMessage(err, '创建用户失败'));
      console.error('Create user error:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!deleteConfirm) return;
    setDeleting(true);
    setError(null);
    try {
      await api.deleteUser(deleteConfirm);
      setDeleteConfirm(null);
      if (selectedUser?.user_id === deleteConfirm) setSelectedUser(null);
      await fetchUsers();
    } catch (err) {
      setError(getErrorMessage(err, '删除用户失败'));
      console.error('Delete user error:', err);
    } finally {
      setDeleting(false);
    }
  };

  const toggleSelect = (userId: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(userId)) {
        next.delete(userId);
      } else {
        next.add(userId);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === users.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(users.map(u => u.user_id)));
    }
  };

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;
    setBatchDeleting(true);
    setError(null);
    try {
      const deletePromises = Array.from(selectedIds).map(id => api.deleteUser(id));
      await Promise.all(deletePromises);
      setBatchDeleteConfirm(false);
      setSelectedIds(new Set());
      if (selectedUser && selectedIds.has(selectedUser.user_id)) {
        setSelectedUser(null);
      }
      await fetchUsers();
    } catch (err) {
      setError(getErrorMessage(err, '批量删除失败'));
      console.error('Batch delete error:', err);
    } finally {
      setBatchDeleting(false);
    }
  };

  const handlePasswordReset = async () => {
    if (!selectedUser || !passwordValue.trim()) return;
    if (passwordValue.trim().length < 6) {
      setError('密码长度至少6位');
      return;
    }
    setResetting(true);
    setError(null);
    try {
      await api.updateUserPassword(selectedUser.user_id, { new_password: passwordValue.trim() });
      setPasswordModal(false);
      setPasswordValue('');
    } catch (err) {
      setError(getErrorMessage(err, '密码重置失败'));
      console.error('Password reset error:', err);
    } finally {
      setResetting(false);
    }
  };

  const handleToggleStatus = async () => {
    if (!selectedUser) return;
    const newStatus = selectedUser.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    setTogglingStatus(true);
    setError(null);
    try {
      await api.updateUser(selectedUser.user_id, { status: newStatus });
      await fetchUsers();
    } catch (err) {
      setError(getErrorMessage(err, '状态切换失败'));
      console.error('Toggle status error:', err);
    } finally {
      setTogglingStatus(false);
    }
  };

  const handleToggleNavView = (view: string) => {
    setError(null);
    setSelectedNavViews(prev => {
      const next = new Set(prev);
      if (next.has(view)) {
        next.delete(view);
      } else {
        next.add(view);
      }
      return next;
    });
  };

  const handleSaveNavigation = async () => {
    if (!selectedUser) return;
    if (selectedNavViews.size === 0) {
      setError('至少保留一个可访问导航');
      return;
    }

    setNavSaving(true);
    setError(null);
    try {
      const response = await api.updateUserNavigation(selectedUser.user_id, {
        allowed_nav_views: Array.from(selectedNavViews),
      });
      setUserNav(response.data || null);
      setSelectedNavViews(new Set(response.data?.allowed_nav_views || []));
    } catch (err) {
      setError(getErrorMessage(err, '保存导航权限失败'));
      console.error('Update user navigation error:', err);
    } finally {
      setNavSaving(false);
    }
  };

  const handleResetNavigationToRole = async () => {
    if (!selectedUser || !userNav) return;

    setNavSaving(true);
    setError(null);
    try {
      const response = await api.updateUserNavigation(selectedUser.user_id, {
        allowed_nav_views: [],
      });
      setUserNav(response.data || null);
      setSelectedNavViews(new Set(response.data?.allowed_nav_views || []));
    } catch (err) {
      setError(getErrorMessage(err, '恢复角色默认导航失败'));
      console.error('Reset user navigation error:', err);
    } finally {
      setNavSaving(false);
    }
  };

  const handleApplyRoleDerivedNavigation = () => {
    if (!userNav) return;
    setSelectedNavViews(new Set(userNav.role_derived_nav_views));
    setError(null);
  };

  const getStatusStyle = (status: string) => {
    if (status === 'ACTIVE') {
      return {
        bg: 'var(--status-success-bg)',
        color: 'var(--accent-green)',
        text: '启用',
      };
    }
    return {
      bg: 'var(--status-error-bg)',
      color: 'var(--accent-red)',
      text: '禁用',
    };
  };

  const getRoleName = (roleId: string) => {
    const role = roles.find(r => r.role_id === roleId);
    return role?.name || roleId;
  };

  const activeCount = users.filter(u => u.status === 'ACTIVE').length;

  const isSelectedUserAdmin = useMemo(
    () => selectedUser?.role_ids.includes('ADMIN') ?? false,
    [selectedUser?.role_ids],
  );

  const navViewsDirty = useMemo(() => {
    if (!userNav) return false;
    const current = Array.from(selectedNavViews).sort();
    const effective = [...userNav.allowed_nav_views].sort();
    return current.join(',') !== effective.join(',');
  }, [selectedNavViews, userNav]);

  const getNavPageLabel = (view: string) => {
    const page = navPages.find(item => item.view === view);
    return page?.label || view;
  };

  const getNavPagePermission = (view: string) => {
    const page = navPages.find(item => item.view === view);
    return page?.permission || '—';
  };

  return (
    <div className={`split-workspace${selectedUser ? ' split-workspace--has-selection' : ''}`}>
      <aside className="split-workspace__list">
        <div className="split-panel-toolbar">
          <PageToolbar
            meta={(
              <>
                <StatPill label="用户" value={users.length} />
                <StatPill label="启用" value={activeCount} tone="success" />
                {selectedIds.size > 0 && (
                  <StatPill label="已选" value={selectedIds.size} tone="info" />
                )}
              </>
            )}
            actions={(
              <>
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
                  + 新建
                </button>
              </>
            )}
          />
        </div>

        <div className="filter-strip">
          <input
            className="form-input"
            placeholder="搜索用户名或 ID…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            aria-label="搜索用户"
          />
          <select
            className="form-input form-select"
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            aria-label="按状态筛选"
          >
            <option value="">全部状态</option>
            <option value="ACTIVE">启用</option>
            <option value="INACTIVE">禁用</option>
          </select>
          <button type="button" className="btn btn--secondary btn--sm" onClick={fetchUsers} disabled={loading}>
            刷新
          </button>
        </div>

        {loading && users.length === 0 ? (
          <div className="loading-overlay">
            <div className="loading-spinner" />
          </div>
        ) : (
          <div className="split-list-scroll" style={styles.userList}>
            <div style={styles.selectAllRow}>
              <label style={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={selectedIds.size === users.length && users.length > 0}
                  onChange={toggleSelectAll}
                  style={styles.checkbox}
                />
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>全选</span>
              </label>
            </div>
            {users.map(user => {
              const status = getStatusStyle(user.status);
              return (
                <div
                  key={user.user_id}
                  style={{
                    ...styles.userItem,
                    ...(selectedUser?.user_id === user.user_id ? styles.userItemSelected : {}),
                  }}
                  onClick={() => handleSelectUser(user)}
                >
                  <div style={styles.itemHeader}>
                    <div style={styles.itemHeaderLeft}>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(user.user_id)}
                        onChange={() => toggleSelect(user.user_id)}
                        onClick={e => e.stopPropagation()}
                        style={styles.checkbox}
                      />
                      <span style={styles.userName}>{user.username}</span>
                    </div>
                    <span
                      style={{
                        ...styles.statusBadge,
                        backgroundColor: status.bg,
                        color: status.color,
                      }}
                    >
                      {status.text}
                    </span>
                  </div>
                  <div style={styles.userId}>{user.user_id}</div>
                  <div style={styles.userRoles}>
                    {user.role_ids.slice(0, 2).map(rid => (
                      <button
                        key={rid}
                        type="button"
                        style={{ ...styles.roleTag, cursor: onNavigate ? 'pointer' : 'default', border: 'none' }}
                        title="点击查看角色配置"
                        onClick={(e) => {
                          e.stopPropagation();
                          onNavigate?.('roles');
                        }}
                      >
                        {getRoleName(rid)}
                      </button>
                    ))}
                    {user.role_ids.length > 2 && (
                      <span style={styles.roleTagMore}>+{user.role_ids.length - 2}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </aside>

      <main className="split-workspace__main">
        {selectedUser ? (
          <div className="surface-card split-detail-scroll data-panel" style={{ margin: 'var(--space-5)', height: 'calc(100% - 40px)' }}>
            <button
              type="button"
              className="split-workspace__back"
              onClick={() => setSelectedUser(null)}
            >
              ← 返回列表
            </button>
            <div className="data-panel-header">
              <h3 className="data-panel-title">用户详情 - {selectedUser.username}</h3>
            </div>

            {error && (
              <div className="error-banner" style={{ marginBottom: '16px' }}>
                <span>⚠</span> {error}
                <button style={styles.errorClose} onClick={() => setError(null)}>×</button>
              </div>
            )}

            <div style={styles.detailSection}>
              <label style={styles.label}>用户ID</label>
              <div style={styles.readonlyField}>{selectedUser.user_id}</div>
            </div>

            <div style={styles.detailSection}>
              <label style={styles.label}>用户名</label>
              {editingField === 'username' ? (
                <div style={styles.editRow}>
                  <input
                    style={styles.input}
                    value={editValue}
                    onChange={e => setEditValue(e.target.value)}
                    autoFocus
                  />
                  <button style={styles.saveBtn} onClick={handleSaveField} disabled={saving}>
                    {saving ? '保存中...' : '保存'}
                  </button>
                  <button style={styles.cancelBtn} onClick={handleCancelEdit}>取消</button>
                </div>
              ) : (
                <div style={styles.editFieldRow}>
                  <span style={styles.fieldValue}>{selectedUser.username}</span>
                  <button style={styles.editBtn} onClick={() => handleEditField('username', selectedUser.username)}>
                    编辑
                  </button>
                </div>
              )}
            </div>

            <div style={styles.detailSection}>
              <label style={styles.label}>邮箱</label>
              {editingField === 'email' ? (
                <div style={styles.editRow}>
                  <input
                    style={styles.input}
                    value={editValue}
                    onChange={e => setEditValue(e.target.value)}
                    placeholder="请输入邮箱"
                    autoFocus
                  />
                  <button style={styles.saveBtn} onClick={handleSaveField} disabled={saving}>
                    {saving ? '保存中...' : '保存'}
                  </button>
                  <button style={styles.cancelBtn} onClick={handleCancelEdit}>取消</button>
                </div>
              ) : (
                <div style={styles.editFieldRow}>
                  <span style={styles.fieldValue}>{selectedUser.email || '未设置'}</span>
                  <button style={styles.editBtn} onClick={() => handleEditField('email', selectedUser.email || '')}>
                    编辑
                  </button>
                </div>
              )}
            </div>

            <div style={styles.detailSection}>
              <label style={styles.label}>状态</label>
              <div style={styles.statusRow}>
                {selectedUser.status === 'ACTIVE' ? (
                  <span style={{ ...styles.statusBadge, backgroundColor: 'var(--status-success-bg)', color: 'var(--accent-green)' }}>
                    启用
                  </span>
                ) : (
                  <span style={{ ...styles.statusBadge, backgroundColor: 'var(--status-error-bg)', color: 'var(--accent-red)' }}>
                    禁用
                  </span>
                )}
              </div>
            </div>

            <div style={styles.detailSection}>
              <label style={styles.label}>操作</label>
              <div style={styles.actionRow}>
                <button
                  style={{
                    ...styles.actionBtn,
                    backgroundColor: selectedUser.status === 'ACTIVE'
                      ? 'var(--status-warning-bg)' : 'var(--status-success-bg)',
                    color: selectedUser.status === 'ACTIVE'
                      ? 'var(--status-warning)' : 'var(--status-success)',
                  }}
                  onClick={handleToggleStatus}
                  disabled={togglingStatus}
                >
                  {togglingStatus ? '处理中...' : selectedUser.status === 'ACTIVE' ? '禁用' : '启用'}
                </button>
                <button
                  style={{ ...styles.actionBtn, backgroundColor: 'var(--status-info-bg)', color: 'var(--status-info)' }}
                  onClick={() => { setPasswordValue(''); setPasswordModal(true); }}
                >
                  重置密码
                </button>
                <button
                  style={{ ...styles.actionBtn, backgroundColor: 'var(--status-error-bg)', color: 'var(--status-error)' }}
                  onClick={() => setDeleteConfirm(selectedUser.user_id)}
                >
                  删除用户
                </button>
              </div>
            </div>

            <div style={styles.detailSection}>
              <label style={styles.label}>所属角色</label>
              <div style={styles.roleList}>
                {roles.map(role => (
                  <div
                    key={role.role_id}
                    style={{
                      ...styles.roleItem,
                      ...(selectedRoleIds.has(role.role_id) ? styles.roleItemSelected : {}),
                    }}
                    onClick={() => handleToggleRole(role.role_id)}
                    className="role-item"
                  >
                    <input
                      type="checkbox"
                      checked={selectedRoleIds.has(role.role_id)}
                      onClick={e => e.stopPropagation()}
                      onChange={() => handleToggleRole(role.role_id)}
                      style={styles.checkbox}
                    />
                    <span style={styles.roleName}>{role.name}</span>
                    {onNavigate && (
                      <button
                        type="button"
                        style={{ ...styles.roleNavBtn }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onNavigate('roles');
                        }}
                        title="查看角色配置"
                      >
                        ↗
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <button
                style={{
                  ...styles.saveRolesBtn,
                  ...(saving ? styles.saveRolesBtnDisabled : {}),
                }}
                onClick={handleSaveRoles}
                disabled={saving}
              >
                {saving ? '保存中...' : '保存角色'}
              </button>
            </div>

            <div style={styles.detailSection}>
              <label style={styles.label}>可访问导航</label>
              <p style={styles.navHint}>
                {isSelectedUserAdmin
                  ? '管理员角色自动拥有全部导航，无需单独配置。'
                  : userNav?.has_nav_override
                    ? '当前使用用户级自定义导航（覆盖角色默认）。修改角色后请点击「同步角色导航」或「恢复角色默认」。'
                    : '当前导航由角色权限自动推导；勾选后保存可设置用户级覆盖。'}
              </p>

              {navLoading ? (
                <div style={styles.navLoading}>加载导航权限...</div>
              ) : (
                <>
                  <div style={styles.navMetaRow}>
                    <span style={styles.navMetaBadge}>
                      生效 {userNav?.allowed_nav_views.length ?? 0} 项
                    </span>
                    <span style={styles.navMetaBadge}>
                      角色推导 {userNav?.role_derived_nav_views.length ?? 0} 项
                    </span>
                    {userNav?.has_nav_override && (
                      <span style={{ ...styles.navMetaBadge, ...styles.navMetaBadgeOverride }}>
                        已自定义
                      </span>
                    )}
                  </div>

                  <div style={styles.navList}>
                    {navPages.map(page => {
                      const roleDerived = userNav?.role_derived_nav_views.includes(page.view) ?? false;
                      const isSelected = selectedNavViews.has(page.view);
                      return (
                        <div
                          key={page.view}
                          style={{
                            ...styles.navItem,
                            ...(isSelected ? styles.navItemSelected : {}),
                            ...(isSelectedUserAdmin ? styles.navItemDisabled : {}),
                          }}
                          onClick={() => !isSelectedUserAdmin && handleToggleNavView(page.view)}
                          className="nav-item"
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            disabled={isSelectedUserAdmin}
                            onClick={e => e.stopPropagation()}
                            onChange={() => handleToggleNavView(page.view)}
                            style={styles.checkbox}
                          />
                          <div style={styles.navItemContent}>
                            <span style={styles.navItemLabel}>{page.label}</span>
                            <span style={styles.navItemMeta}>
                              {page.view}
                              {page.permission ? ` · ${page.permission}` : ''}
                              {roleDerived ? ' · 角色可访问' : ''}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {!isSelectedUserAdmin && (
                    <div style={styles.navActionRow}>
                      <button
                        type="button"
                        style={{
                          ...styles.navSecondaryBtn,
                          ...(navSaving ? styles.saveRolesBtnDisabled : {}),
                        }}
                        onClick={handleApplyRoleDerivedNavigation}
                        disabled={navSaving || !userNav}
                      >
                        同步角色导航
                      </button>
                      <button
                        type="button"
                        style={{
                          ...styles.navSecondaryBtn,
                          ...(navSaving ? styles.saveRolesBtnDisabled : {}),
                        }}
                        onClick={handleResetNavigationToRole}
                        disabled={navSaving || !userNav?.has_nav_override}
                      >
                        恢复角色默认
                      </button>
                      <button
                        type="button"
                        style={{
                          ...styles.saveRolesBtn,
                          ...((navSaving || !navViewsDirty) ? styles.saveRolesBtnDisabled : {}),
                        }}
                        onClick={handleSaveNavigation}
                        disabled={navSaving || !navViewsDirty}
                      >
                        {navSaving ? '保存中...' : '保存导航'}
                      </button>
                    </div>
                  )}

                  {selectedNavViews.size > 0 && (
                    <div style={styles.navSummary}>
                      <span style={styles.navSummaryLabel}>已选导航：</span>
                      {Array.from(selectedNavViews).map(view => (
                        <span key={view} style={styles.navSummaryTag} title={getNavPagePermission(view)}>
                          {getNavPageLabel(view)}
                        </span>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>

            <div style={styles.detailSection}>
              <label style={styles.label}>创建时间</label>
              <div style={styles.readonlyField}>
                {new Date(selectedUser.created_at).toLocaleString('zh-CN')}
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-state" style={{ height: '100%' }}>
            <div className="empty-state__icon">👤</div>
            <p className="empty-state__text">选择左侧用户查看详情</p>
          </div>
        )}
      </main>

      {/* Create User Modal */}
      {createModalOpen && (
        <div style={styles.modalOverlay} onClick={() => setCreateModalOpen(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>新建用户</h3>
              <button style={styles.modalClose} onClick={() => setCreateModalOpen(false)}>×</button>
            </div>
            <div style={styles.modalBody}>
              <div style={styles.formGroup}>
                <label style={styles.label}>用户ID *</label>
                <input
                  style={styles.input}
                  value={newUser.user_id}
                  onChange={e => setNewUser({ ...newUser, user_id: e.target.value })}
                  placeholder="登录用ID"
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>用户名 *</label>
                <input
                  style={styles.input}
                  value={newUser.username}
                  onChange={e => setNewUser({ ...newUser, username: e.target.value })}
                  placeholder="显示名称"
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>密码 *</label>
                <input
                  style={styles.input}
                  type="password"
                  value={newUser.password}
                  onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                  placeholder="至少6位"
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>邮箱</label>
                <input
                  style={styles.input}
                  type="email"
                  value={newUser.email}
                  onChange={e => setNewUser({ ...newUser, email: e.target.value })}
                  placeholder="可选"
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>初始角色</label>
                <div style={styles.modalRoleList}>
                  {roles.map(role => (
                    <div
                      key={role.role_id}
                      style={{
                        ...styles.modalRoleItem,
                        ...(newUser.role_ids.includes(role.role_id) ? styles.modalRoleItemSelected : {}),
                      }}
                      onClick={() => {
                        const ids = newUser.role_ids.includes(role.role_id)
                          ? newUser.role_ids.filter(id => id !== role.role_id)
                          : [...newUser.role_ids, role.role_id];
                        setNewUser({ ...newUser, role_ids: ids });
                      }}
                    >
                    <input
                      type="checkbox"
                      checked={newUser.role_ids.includes(role.role_id)}
                      onClick={e => e.stopPropagation()}
                      onChange={() => {
                        const ids = newUser.role_ids.includes(role.role_id)
                          ? newUser.role_ids.filter(id => id !== role.role_id)
                          : [...newUser.role_ids, role.role_id];
                        setNewUser({ ...newUser, role_ids: ids });
                      }}
                      style={styles.checkbox}
                    />
                      <span>{role.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div style={styles.modalFooter}>
              <button style={styles.cancelBtn} onClick={() => setCreateModalOpen(false)}>取消</button>
              <button
                style={styles.saveBtn}
                onClick={handleCreateUser}
                disabled={creating || !newUser.user_id.trim() || !newUser.username.trim() || !newUser.password}
              >
                {creating ? '创建中...' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div style={styles.modalOverlay} onClick={() => setDeleteConfirm(null)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>确认删除</h3>
              <button style={styles.modalClose} onClick={() => setDeleteConfirm(null)}>×</button>
            </div>
            <div style={styles.modalBody}>
              <p style={{ fontSize: '14px', color: 'var(--text-primary)', margin: 0 }}>
                确定要删除用户 <strong>{deleteConfirm}</strong> 吗？此操作不可恢复。
              </p>
            </div>
            <div style={styles.modalFooter}>
              <button style={styles.cancelBtn} onClick={() => setDeleteConfirm(null)}>取消</button>
              <button
                style={{
                  ...styles.dangerBtn,
                  ...(deleting ? { opacity: 0.6, cursor: 'wait' } : {}),
                }}
                onClick={handleDeleteUser}
                disabled={deleting}
              >
                {deleting ? '删除中...' : '确认删除'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Batch Delete Confirmation Modal */}
      {batchDeleteConfirm && (
        <div style={styles.modalOverlay} onClick={() => setBatchDeleteConfirm(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>确认批量删除</h3>
              <button style={styles.modalClose} onClick={() => setBatchDeleteConfirm(false)}>×</button>
            </div>
            <div style={styles.modalBody}>
              <p style={{ fontSize: '14px', color: 'var(--text-primary)', margin: 0 }}>
                确定要删除选中的 <strong>{selectedIds.size}</strong> 个用户吗？此操作不可恢复。
              </p>
            </div>
            <div style={styles.modalFooter}>
              <button style={styles.cancelBtn} onClick={() => setBatchDeleteConfirm(false)}>取消</button>
              <button
                style={{
                  ...styles.dangerBtn,
                  ...(batchDeleting ? { opacity: 0.6, cursor: 'wait' } : {}),
                }}
                onClick={handleBatchDelete}
                disabled={batchDeleting}
              >
                {batchDeleting ? '删除中...' : `删除 ${selectedIds.size} 项`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Password Reset Modal */}
      {passwordModal && (
        <div style={styles.modalOverlay} onClick={() => setPasswordModal(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>重置密码</h3>
              <button style={styles.modalClose} onClick={() => setPasswordModal(false)}>×</button>
            </div>
            <div style={styles.modalBody}>
              <p style={{ fontSize: '13px', color: 'var(--text-tertiary)', marginBottom: '12px' }}>
                为用户 <strong>{selectedUser?.username}</strong> 设置新密码
              </p>
              <input
                style={styles.input}
                type="password"
                value={passwordValue}
                onChange={e => setPasswordValue(e.target.value)}
                placeholder="输入新密码（至少6位）"
                autoFocus
              />
            </div>
            <div style={styles.modalFooter}>
              <button style={styles.cancelBtn} onClick={() => setPasswordModal(false)}>取消</button>
              <button
                style={{
                  ...styles.saveBtn,
                  ...(resetting ? { opacity: 0.6, cursor: 'wait' } : {}),
                }}
                onClick={handlePasswordReset}
                disabled={resetting || !passwordValue.trim()}
              >
                {resetting ? '重置中...' : '确认重置'}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .role-item:hover {
          background-color: var(--bg-tertiary);
          border-color: var(--accent-cyan);
        }
        .nav-item:hover:not([style*="opacity"]) {
          background-color: var(--bg-tertiary);
          border-color: var(--accent-cyan);
        }
      `}</style>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    height: 'calc(100vh - 64px)',
    animation: 'fadeIn 0.3s ease',
  } as const,
  leftPanel: {
    width: '380px',
    minWidth: '380px',
    backgroundColor: 'var(--bg-secondary)',
    borderRight: '1px solid var(--border-default)',
    display: 'flex',
    flexDirection: 'column' as const,
  },
  rightPanel: {
    flex: 1,
    padding: '28px 32px',
    overflowY: 'auto' as const,
  },
  panelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px 24px',
    borderBottom: '1px solid var(--border-muted)',
  },
  panelTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    margin: 0,
  },
  panelHint: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    marginTop: '2px',
    display: 'block',
  },
  createBtn: {
    padding: '8px 14px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--accent-cyan)',
    backgroundColor: 'transparent',
    border: '1px solid var(--accent-cyan)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  filterRow: {
    display: 'flex',
    gap: '10px',
    padding: '12px 16px',
    borderBottom: '1px solid var(--border-muted)',
  },
  searchInput: {
    flex: '1 1 160px',
    padding: '8px 12px',
    fontSize: '13px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
    minWidth: 0,
  },
  filterSelect: {
    flex: '0 0 auto',
    padding: '8px 12px',
    fontSize: '13px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  refreshBtn: {
    padding: '8px 14px',
    fontSize: '13px',
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  loadingState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    padding: '60px',
    color: 'var(--text-secondary)',
  },
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid var(--border-default)',
    borderTopColor: 'var(--accent-cyan)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  userList: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '12px',
  },
  selectAllRow: {
    display: 'flex',
    alignItems: 'center',
    padding: '8px 4px',
    marginBottom: '8px',
    borderBottom: '1px solid var(--border-muted)',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    cursor: 'pointer',
  },
  itemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px',
  },
  itemHeaderLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  userItem: {
    padding: '14px 16px',
    marginBottom: '8px',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  userItemSelected: {
    border: '1px solid var(--accent-cyan)',
    backgroundColor: 'var(--bg-tertiary)',
  },
  userItemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px',
  },
  userName: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  statusBadge: {
    padding: '3px 10px',
    fontSize: '11px',
    fontWeight: 600,
    borderRadius: '10px',
  },
  userId: {
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--text-muted)',
    marginBottom: '6px',
  },
  userRoles: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '4px',
  },
  roleTag: {
    fontSize: '11px',
    padding: '2px 8px',
    backgroundColor: 'var(--bg-tertiary)',
    borderRadius: '4px',
    color: 'var(--text-secondary)',
  },
  roleTagMore: {
    fontSize: '11px',
    padding: '2px 6px',
    color: 'var(--text-muted)',
  },
  detailSection: {
    marginBottom: '24px',
  },
  label: {
    display: 'block',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    marginBottom: '8px',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  readonlyField: {
    fontSize: '14px',
    color: 'var(--text-secondary)',
    fontFamily: "'JetBrains Mono', monospace",
  },
  fieldValue: {
    fontSize: '16px',
    color: 'var(--text-primary)',
    fontWeight: 500,
  },
  editFieldRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  editRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  input: {
    flex: 1,
    padding: '10px 14px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
  },
  saveBtn: {
    padding: '10px 18px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--bg-primary)',
    backgroundColor: 'var(--accent-cyan)',
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
  actionRow: {
    display: 'flex',
    gap: '10px',
    flexWrap: 'wrap' as const,
  },
  actionBtn: {
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: 500,
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  editBtn: {
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
  },
  statusRow: {
    display: 'flex',
    gap: '10px',
  },
  roleList: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '10px',
    marginBottom: '16px',
  },
  roleItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 14px',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  roleItemSelected: {
    border: '1px solid var(--accent-green)',
    backgroundColor: 'rgba(72, 199, 142, 0.08)',
  },
  roleName: {
    fontSize: '13px',
    color: 'var(--text-primary)',
  },
  roleNavBtn: {
    fontSize: '11px',
    color: 'var(--accent-primary)',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    padding: '2px 6px',
    borderRadius: '4px',
    opacity: 0.5,
    marginLeft: 'auto',
  },
  checkbox: {
    width: '16px',
    height: '16px',
    cursor: 'pointer',
    accentColor: 'var(--accent-cyan)',
  },
  saveRolesBtn: {
    padding: '10px 18px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--bg-primary)',
    backgroundColor: 'var(--accent-cyan)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  saveRolesBtnDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  navHint: {
    fontSize: '13px',
    color: 'var(--text-tertiary)',
    margin: '0 0 12px',
    lineHeight: 1.5,
  },
  navLoading: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
    padding: '12px 0',
  },
  navMetaRow: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '8px',
    marginBottom: '12px',
  },
  navMetaBadge: {
    fontSize: '11px',
    padding: '4px 10px',
    borderRadius: '999px',
    backgroundColor: 'var(--bg-tertiary)',
    color: 'var(--text-secondary)',
  },
  navMetaBadgeOverride: {
    backgroundColor: 'var(--status-info-bg)',
    color: 'var(--status-info)',
  },
  navList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
    marginBottom: '16px',
  },
  navItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    padding: '12px 14px',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  navItemSelected: {
    border: '1px solid var(--accent-green)',
    backgroundColor: 'rgba(72, 199, 142, 0.08)',
  },
  navItemDisabled: {
    opacity: 0.65,
    cursor: 'not-allowed',
  },
  navItemContent: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
    minWidth: 0,
  },
  navItemLabel: {
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--text-primary)',
  },
  navItemMeta: {
    fontSize: '11px',
    color: 'var(--text-muted)',
    fontFamily: "'JetBrains Mono', monospace",
  },
  navActionRow: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '10px',
    marginBottom: '12px',
  },
  navSecondaryBtn: {
    padding: '10px 18px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'transparent',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  },
  navSummary: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    alignItems: 'center',
    gap: '6px',
  },
  navSummaryLabel: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
  },
  navSummaryTag: {
    fontSize: '11px',
    padding: '3px 8px',
    borderRadius: '4px',
    backgroundColor: 'var(--bg-tertiary)',
    color: 'var(--text-secondary)',
  },
  emptyDetail: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: 'var(--text-muted)',
  },
  emptyIcon: {
    fontSize: '64px',
    opacity: 0.3,
    marginBottom: '16px',
  },
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '14px 18px',
    backgroundColor: 'var(--status-error-bg)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--accent-red)',
    fontSize: '14px',
    marginBottom: '20px',
  },
  errorClose: {
    marginLeft: 'auto',
    padding: '0 8px',
    fontSize: '18px',
    background: 'none',
    border: 'none',
    color: 'var(--accent-red)',
    cursor: 'pointer',
  },
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
    width: '520px',
    maxWidth: '90vw',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    overflow: 'hidden',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '18px 24px',
    borderBottom: '1px solid var(--border-muted)',
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
    color: 'var(--text-muted)',
    cursor: 'pointer',
  },
  modalBody: {
    padding: '24px',
    maxHeight: '60vh',
    overflowY: 'auto' as const,
  },
  formGroup: {
    marginBottom: '18px',
  },
  modalRoleList: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '8px',
  },
  modalRoleItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 14px',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontSize: '13px',
    color: 'var(--text-primary)',
  },
  modalRoleItemSelected: {
    border: '1px solid var(--accent-green)',
    backgroundColor: 'rgba(72, 199, 142, 0.08)',
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
    padding: '18px 24px',
    borderTop: '1px solid var(--border-muted)',
  },
};

export default UserManagement;
