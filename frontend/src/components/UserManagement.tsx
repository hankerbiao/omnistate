import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { UserResponse } from '../types';
import PageToolbar, { StatPill } from './ui/PageToolbar';
import { getErrorMessage } from '../utils/errors';
import { queryKeys } from '../providers/queryKeys';
import { CreateUserModal } from './user-management/modals/CreateUserModal';
import { PasswordResetModal } from './user-management/modals/PasswordResetModal';
import { DeleteConfirmModal } from './user-management/modals/DeleteConfirmModal';

interface UserManagementProps {
  onNavigate?: (page: string) => void;
}

const UserManagement: React.FC<UserManagementProps> = ({ onNavigate }) => {
  const queryClient = useQueryClient();
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRoleIds, setSelectedRoleIds] = useState<Set<string>>(new Set());
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [passwordModal, setPasswordModal] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);

  const usersQuery = useQuery({
    queryKey: [...queryKeys.users.all, filterStatus, searchQuery],
    queryFn: async () => {
      const params: { status?: string; search?: string; limit?: number } = { limit: 200 };
      if (filterStatus) params.status = filterStatus;
      if (searchQuery.trim()) params.search = searchQuery.trim();
      return (await api.listUsers(params)).data || [];
    },
  });

  const rolesQuery = useQuery({
    queryKey: queryKeys.roles.all,
    queryFn: async () => (await api.listRoles()).data || [],
  });

  const users = usersQuery.data ?? [];
  const roles = rolesQuery.data ?? [];
  const selectedUser = useMemo(
    () => users.find(user => user.user_id === selectedUserId) || null,
    [selectedUserId, users],
  );

  const activeCount = users.filter(user => user.status === 'ACTIVE').length;
  const displayError = usersQuery.error ? getErrorMessage(usersQuery.error, '获取用户列表失败') : mutationError;

  const invalidateUsers = () => queryClient.invalidateQueries({ queryKey: queryKeys.users.all });

  const createUserMutation = useMutation({
    mutationFn: async (data: { user_id: string; username: string; password: string; email: string; role_ids: string[] }) => {
      await api.createUser({
        user_id: data.user_id.trim(),
        username: data.username.trim(),
        password: data.password,
        email: data.email.trim() || undefined,
        role_ids: data.role_ids,
      });
    },
    onSuccess: () => {
      setCreateModalOpen(false);
      setMutationError(null);
      invalidateUsers();
    },
    onError: err => setMutationError(getErrorMessage(err, '创建用户失败')),
  });

  const updateUserMutation = useMutation({
    mutationFn: async (payload: { userId: string; data: Partial<Pick<UserResponse, 'username' | 'email' | 'status'>> }) => {
      await api.updateUser(payload.userId, payload.data);
    },
    onSuccess: () => {
      setMutationError(null);
      invalidateUsers();
    },
    onError: err => setMutationError(getErrorMessage(err, '更新用户失败')),
  });

  const updateRolesMutation = useMutation({
    mutationFn: async () => {
      if (!selectedUser) return;
      await api.updateUserRoles(selectedUser.user_id, { role_ids: Array.from(selectedRoleIds) });
    },
    onSuccess: () => {
      setMutationError(null);
      invalidateUsers();
    },
    onError: err => setMutationError(getErrorMessage(err, '保存角色失败')),
  });

  const passwordResetMutation = useMutation({
    mutationFn: async (password: string) => {
      if (!selectedUser) return;
      await api.updateUserPassword(selectedUser.user_id, { new_password: password });
    },
    onSuccess: () => {
      setPasswordModal(false);
      setMutationError(null);
    },
    onError: err => setMutationError(getErrorMessage(err, '密码重置失败')),
  });

  const deleteUserMutation = useMutation({
    mutationFn: async () => {
      if (!deleteConfirm) return;
      await api.deleteUser(deleteConfirm);
    },
    onSuccess: () => {
      if (selectedUserId === deleteConfirm) setSelectedUserId(null);
      setDeleteConfirm(null);
      setMutationError(null);
      invalidateUsers();
    },
    onError: err => setMutationError(getErrorMessage(err, '删除用户失败')),
  });

  const handleSelectUser = (user: UserResponse) => {
    setSelectedUserId(user.user_id);
    setSelectedRoleIds(new Set(user.role_ids || []));
    setMutationError(null);
  };

  const toggleRole = (roleId: string) => {
    setSelectedRoleIds(prev => {
      const next = new Set(prev);
      if (next.has(roleId)) next.delete(roleId);
      else next.add(roleId);
      return next;
    });
  };

  const getRoleName = (roleId: string) => roles.find(role => role.role_id === roleId)?.name || roleId;

  return (
    <div className={`split-workspace${selectedUser ? ' split-workspace--has-selection' : ''}`}>
      <aside className="split-workspace__list">
        <div className="split-panel-toolbar">
          <PageToolbar
            meta={(
              <>
                <StatPill label="用户" value={users.length} />
                <StatPill label="启用" value={activeCount} tone="success" />
              </>
            )}
            actions={<button type="button" className="btn btn--primary btn--sm" onClick={() => setCreateModalOpen(true)}>+ 新建</button>}
          />
        </div>

        <div className="filter-strip">
          <input
            className="form-input"
            placeholder="搜索用户名或 ID..."
            value={searchQuery}
            onChange={event => setSearchQuery(event.target.value)}
            aria-label="搜索用户"
          />
          <select className="form-input form-select" value={filterStatus} onChange={event => setFilterStatus(event.target.value)}>
            <option value="">全部状态</option>
            <option value="ACTIVE">启用</option>
            <option value="DISABLED">禁用</option>
          </select>
          <button type="button" className="btn btn--secondary btn--sm" onClick={() => usersQuery.refetch()} disabled={usersQuery.isLoading}>刷新</button>
        </div>

        {displayError && !selectedUser && <div className="error-banner" style={{ margin: '0 var(--space-4) var(--space-3)' }}>{displayError}</div>}

        <div className="split-list-scroll" style={{ padding: 0 }}>
          {usersQuery.isLoading && users.length === 0 ? (
            <div className="loading-overlay"><div className="loading-spinner" /></div>
          ) : users.length === 0 ? (
            <div className="empty-state"><p className="empty-state__text">暂无用户</p></div>
          ) : (
            <table className="data-table">
              <thead>
                <tr><th>用户</th><th style={{ width: 80 }}>状态</th></tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.user_id} className={selectedUserId === user.user_id ? 'selected' : ''} onClick={() => handleSelectUser(user)} style={{ cursor: 'pointer' }}>
                    <td>
                      <span style={{ fontWeight: 500 }}>{user.username}</span>
                      <span className="mono" style={{ display: 'block', fontSize: 11, color: 'var(--text-tertiary)' }}>{user.user_id}</span>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 6 }}>
                        {(user.role_ids || []).slice(0, 3).map(roleId => <span key={roleId} className="status-badge status-badge--neutral">{getRoleName(roleId)}</span>)}
                      </div>
                    </td>
                    <td><span className={`status-badge ${user.status === 'ACTIVE' ? 'status-badge--success' : 'status-badge--danger'}`}>{user.status === 'ACTIVE' ? '启用' : '禁用'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </aside>

      <main className="split-workspace__main">
        {selectedUser ? (
          <div className="split-detail-scroll" style={{ padding: 24 }}>
            <button type="button" className="split-workspace__back" onClick={() => setSelectedUserId(null)}>← 返回列表</button>
            <div className="data-panel-header" style={{ paddingLeft: 0 }}>
              <h3 className="data-panel-title">用户详情 - {selectedUser.username}</h3>
            </div>

            {displayError && <div className="error-banner" style={{ marginBottom: 16 }}>{displayError}</div>}

            <section className="surface-card" style={{ padding: 16, marginBottom: 16 }}>
              <div className="split-detail-form-grid__fields">
                <label className="text-sm font-medium text-[var(--text-secondary)]">用户 ID</label>
                <div className="form-input" style={{ background: 'var(--surface-secondary)' }}>{selectedUser.user_id}</div>
                <label className="text-sm font-medium text-[var(--text-secondary)]">用户名</label>
                <input
                  className="form-input"
                  defaultValue={selectedUser.username}
                  onBlur={event => {
                    const value = event.target.value.trim();
                    if (value && value !== selectedUser.username) updateUserMutation.mutate({ userId: selectedUser.user_id, data: { username: value } });
                  }}
                />
                <label className="text-sm font-medium text-[var(--text-secondary)]">邮箱</label>
                <input
                  className="form-input"
                  defaultValue={selectedUser.email || ''}
                  onBlur={event => {
                    const value = event.target.value.trim();
                    if (value !== (selectedUser.email || '')) updateUserMutation.mutate({ userId: selectedUser.user_id, data: { email: value || undefined } });
                  }}
                />
              </div>
            </section>

            <section className="surface-card" style={{ padding: 16, marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 12 }}>
                <h4 style={{ margin: 0, fontSize: 14 }}>角色</h4>
                {onNavigate && <button type="button" className="btn btn--secondary btn--sm" onClick={() => onNavigate('roles')}>角色管理</button>}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {roles.map(role => {
                  const checked = selectedRoleIds.has(role.role_id);
                  return (
                    <label key={role.role_id} className="form-input" style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', background: checked ? 'var(--status-info-bg)' : 'transparent' }}>
                      <input type="checkbox" checked={checked} onChange={() => toggleRole(role.role_id)} />
                      <span>{role.name}</span>
                      {role.is_system && <span className="status-badge status-badge--info">系统</span>}
                    </label>
                  );
                })}
              </div>
              <button type="button" className="btn btn--primary btn--sm" style={{ marginTop: 12 }} onClick={() => updateRolesMutation.mutate()} disabled={updateRolesMutation.isPending}>保存角色</button>
            </section>

            <section className="surface-card" style={{ padding: 16 }}>
              <h4 style={{ margin: '0 0 12px', fontSize: 14 }}>操作</h4>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn--secondary btn--sm" onClick={() => updateUserMutation.mutate({ userId: selectedUser.user_id, data: { status: selectedUser.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE' } })}>
                  {selectedUser.status === 'ACTIVE' ? '禁用' : '启用'}
                </button>
                <button type="button" className="btn btn--secondary btn--sm" onClick={() => setPasswordModal(true)}>重置密码</button>
                <button type="button" className="btn btn--danger btn--sm" onClick={() => setDeleteConfirm(selectedUser.user_id)}>删除用户</button>
              </div>
            </section>
          </div>
        ) : (
          <div className="empty-state" style={{ height: '100%' }}><p className="empty-state__text">选择左侧用户查看详情</p></div>
        )}
      </main>

      <CreateUserModal open={createModalOpen} onClose={() => setCreateModalOpen(false)} roles={roles} creating={createUserMutation.isPending} onCreateUser={data => createUserMutation.mutate(data)} />
      <PasswordResetModal open={passwordModal} username={selectedUser?.username || ''} onClose={() => setPasswordModal(false)} resetting={passwordResetMutation.isPending} onReset={password => passwordResetMutation.mutate(password)} error={mutationError} />
      <DeleteConfirmModal open={!!deleteConfirm} onClose={() => setDeleteConfirm(null)} onConfirm={() => deleteUserMutation.mutate()} title="确认删除" description={`确定要删除用户 ${deleteConfirm || ''} 吗？此操作会禁用该账号。`} deleting={deleteUserMutation.isPending} />
    </div>
  );
};

export default UserManagement;
