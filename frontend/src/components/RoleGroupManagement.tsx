/** 用户组管理 — 左侧角色列表 + 右侧成员管理与权限概览 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { api } from '../services/api';
import type { RoleResponse, UserResponse } from '../types';
import PageToolbar, { StatPill } from './ui/PageToolbar';
import {
  DetailHeader,
  DetailStatGrid,
  DetailSection,
  DetailMetaRow,
  DetailEmpty,
} from './ui/SplitDetailPanel';
import { getErrorMessage } from '../utils/errors';

interface RoleGroupManagementProps {
  onNavigate?: (page: string) => void;
}

const RoleGroupManagement: React.FC<RoleGroupManagementProps> = ({ onNavigate }) => {
  const [roles, setRoles] = useState<RoleResponse[]>([]);
  const [selectedRole, setSelectedRole] = useState<RoleResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<'all' | 'system' | 'custom'>('all');

  // Member state
  const [members, setMembers] = useState<UserResponse[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [removing, setRemoving] = useState<Set<string>>(new Set());

  // Add member state
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [availableUsers, setAvailableUsers] = useState<UserResponse[]>([]);
  const [addSearch, setAddSearch] = useState('');
  const [addingIds, setAddingIds] = useState<Set<string>>(new Set());
  const [adding, setAdding] = useState(false);

  const initialSelectedRef = useRef(false);
  const addSearchRef = useRef<HTMLInputElement>(null);

  const fetchRoles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listRoles();
      setRoles(response.data || []);
    } catch (err) {
      setError('获取角色列表失败');
      console.error('Fetch roles error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRoles();
  }, [fetchRoles]);

  // Default select first role
  useEffect(() => {
    if (!initialSelectedRef.current && roles.length > 0 && !selectedRole) {
      initialSelectedRef.current = true;
      setSelectedRole(roles[0]);
    }
  }, [roles, selectedRole]);

  const fetchMembers = useCallback(async (roleId: string) => {
    setMembersLoading(true);
    try {
      const response = await api.listUsers({ role_id: roleId, limit: 200 });
      setMembers(response.data || []);
    } catch {
      setMembers([]);
    } finally {
      setMembersLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedRole) {
      fetchMembers(selectedRole.role_id);
    } else {
      setMembers([]);
    }
  }, [selectedRole, fetchMembers]);

  const filteredRoles = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return roles.filter(role => {
      if (roleFilter === 'system' && !role.is_system) return false;
      if (roleFilter === 'custom' && role.is_system) return false;
      if (!q) return true;
      return (
        role.name.toLowerCase().includes(q) ||
        role.role_id.toLowerCase().includes(q) ||
        (role.description?.toLowerCase().includes(q) ?? false)
      );
    });
  }, [roles, searchQuery, roleFilter]);

  const handleRemoveMember = async (user: UserResponse) => {
    if (!selectedRole) return;
    const newRoleIds = (user.role_ids || []).filter(id => id !== selectedRole.role_id);
    setRemoving(prev => new Set(prev).add(user.user_id));
    try {
      await api.updateUserRoles(user.user_id, { role_ids: newRoleIds });
      setMembers(prev => prev.filter(m => m.user_id !== user.user_id));
    } catch (err) {
      setError(getErrorMessage(err, '移除成员失败'));
    } finally {
      setRemoving(prev => { const n = new Set(prev); n.delete(user.user_id); return n; });
    }
  };

  const openAddModal = async () => {
    setAddModalOpen(true);
    setAddSearch('');
    setAddingIds(new Set());
    try {
      const response = await api.listUsers({ limit: 200 });
      setAvailableUsers(response.data || []);
    } catch {
      setAvailableUsers([]);
    }
    setTimeout(() => addSearchRef.current?.focus(), 100);
  };

  const toggleAddUser = (userId: string) => {
    setAddingIds(prev => {
      const n = new Set(prev);
      if (n.has(userId)) n.delete(userId);
      else n.add(userId);
      return n;
    });
  };

  const handleAddMembers = async () => {
    if (!selectedRole || addingIds.size === 0) return;
    setAdding(true);
    setError(null);
    try {
      const memberIds = new Set(members.map(m => m.user_id));
      await Promise.all(
        Array.from(addingIds)
          .filter(uid => !memberIds.has(uid))
          .map(uid => {
            const user = availableUsers.find(u => u.user_id === uid);
            const currentIds = user?.role_ids || [];
            return api.updateUserRoles(uid, {
              role_ids: [...currentIds.filter(id => id !== selectedRole.role_id), selectedRole.role_id],
            });
          }),
      );
      setAddModalOpen(false);
      await fetchMembers(selectedRole.role_id);
    } catch (err) {
      setError(getErrorMessage(err, '添加成员失败'));
    } finally {
      setAdding(false);
    }
  };

  const filteredAvailable = useMemo(() => {
    const q = addSearch.trim().toLowerCase();
    const memberIds = new Set(members.map(m => m.user_id));
    return availableUsers
      .filter(u => !memberIds.has(u.user_id) && u.status !== 'DISABLED')
      .filter(u => {
        if (!q) return true;
        return (
          u.username?.toLowerCase().includes(q) ||
          u.user_id.toLowerCase().includes(q) ||
          u.email?.toLowerCase().includes(q)
        );
      });
  }, [availableUsers, members, addSearch]);

  const systemRoleCount = roles.filter(r => r.is_system).length;

  // ─── Render ───
  return (
    <>
    <div className={`split-workspace${selectedRole ? ' split-workspace--has-selection' : ''}`}>
      <aside className="split-workspace__list">
        <div className="split-panel-toolbar">
          <PageToolbar
            meta={
              <>
                <StatPill label="角色/组" value={roles.length} />
                <StatPill label="系统" value={systemRoleCount} tone="info" />
                <StatPill label="显示" value={filteredRoles.length} />
              </>
            }
            actions={
              onNavigate ? (
                <button type="button" className="btn btn--secondary btn--sm" onClick={() => onNavigate('roles')}>
                  经典角色管理 →
                </button>
              ) : undefined
            }
          />
        </div>

        <div className="filter-strip">
          <input
            className="form-input"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="搜索组名称、ID…"
            aria-label="搜索角色组"
          />
          <select
            className="form-input form-select"
            value={roleFilter}
            onChange={e => setRoleFilter(e.target.value as typeof roleFilter)}
            aria-label="角色类型"
          >
            <option value="all">全部</option>
            <option value="system">系统组</option>
            <option value="custom">自定义组</option>
          </select>
          <button type="button" className="btn btn--secondary btn--sm" onClick={fetchRoles} disabled={loading}>
            刷新
          </button>
        </div>

        {error && !selectedRole && (
          <div className="error-banner" style={{ margin: '0 var(--space-4) var(--space-3)' }}>
            <span>⚠</span> {error}
            <button style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, color: 'var(--text-tertiary)', marginLeft: 'auto' }} onClick={() => setError(null)}>×</button>
          </div>
        )}

        {loading && roles.length === 0 ? (
          <div className="loading-overlay"><div className="loading-spinner" /></div>
        ) : filteredRoles.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state__icon">👥</div>
            <p className="empty-state__text">
              {searchQuery || roleFilter !== 'all' ? '没有匹配的组' : '暂无角色数据'}
            </p>
          </div>
        ) : (
          <div className="split-list-scroll" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>组名称</th>
                  <th style={{ width: 60 }}>成员</th>
                  <th style={{ width: 60 }}>类型</th>
                </tr>
              </thead>
              <tbody>
                {filteredRoles.map(role => (
                  <tr
                    key={role.role_id}
                    className={selectedRole?.role_id === role.role_id ? 'selected' : ''}
                    onClick={() => setSelectedRole(role)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <span style={{ fontWeight: 500, fontSize: 13, color: 'var(--text-primary)' }}>{role.name}</span>
                      <span className="mono" style={{ display: 'block', fontSize: 11, color: 'var(--text-tertiary)' }}>{role.role_id}</span>
                    </td>
                    <td>
                      <span style={{
                        fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
                        color: role.role_id === selectedRole?.role_id
                          ? 'var(--accent-primary)' : 'var(--text-secondary)',
                        fontWeight: 600,
                      }}>
                        {role.role_id === selectedRole?.role_id ? members.length : '-'}
                      </span>
                    </td>
                    <td>
                      {role.is_system ? (
                        <span className="status-badge status-badge--info" style={{ fontSize: 10 }}>系统</span>
                      ) : (
                        <span className="status-badge status-badge--neutral" style={{ fontSize: 10 }}>自定义</span>
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
          <div className="split-detail-scroll" style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>

            <button type="button" className="split-workspace__back" onClick={() => setSelectedRole(null)}>
              ← 返回列表
            </button>

            <DetailHeader
              id={selectedRole.role_id}
              title={selectedRole.name}
              subtitle={selectedRole.description || '暂无描述'}
              badges={
                <span className={`status-badge ${selectedRole.is_system ? 'status-badge--info' : 'status-badge--neutral'}`}>
                  {selectedRole.is_system ? '系统组' : '自定义组'}
                </span>
              }
              actions={
                <button type="button" className="btn btn--secondary btn--sm" onClick={openAddModal}>
                  + 添加成员
                </button>
              }
            />

            {error && (
              <div className="error-banner" style={{ margin: '0 var(--space-5) var(--space-3)' }}>
                <span>⚠</span> {error}
                <button style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, color: 'var(--text-tertiary)', marginLeft: 'auto' }} onClick={() => setError(null)}>×</button>
              </div>
            )}

            <div className="split-detail-content">
              <DetailStatGrid stats={[
                { label: '成员', value: members.length },
                { label: '权限数', value: selectedRole.permission_ids?.length || 0 },
              ]} />

              {/* ── Members Section ── */}
              <DetailSection title={`组成员 (${members.length})`}>
                {membersLoading ? (
                  <div style={{ padding: '20px 0', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>加载中...</div>
                ) : members.length === 0 ? (
                  <div style={{ padding: '20px 0', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>
                    暂无成员。点击"添加成员"将用户加入此组。
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {members.map(user => (
                      <div key={user.user_id} style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        padding: '8px 12px', borderRadius: 8,
                        border: '1px solid var(--border-subtle)',
                        background: 'var(--bg-secondary)',
                      }}>
                        <div style={{
                          width: 28, height: 28, borderRadius: 6,
                          background: 'var(--accent-primary)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          color: '#fff', fontSize: 12, fontWeight: 600, flexShrink: 0,
                        }}>
                          {(user.username || user.user_id).charAt(0).toUpperCase()}
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                            {user.username || user.user_id}
                          </div>
                          <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                            <span className="mono">{user.user_id}</span>
                            {user.email && <span> · {user.email}</span>}
                            {user.status === 'DISABLED' && (
                              <span className="status-badge status-badge--danger" style={{ marginLeft: 6, fontSize: 10 }}>已禁用</span>
                            )}
                          </div>
                        </div>
                        {!selectedRole.is_system && (
                          <button
                            type="button"
                            title="移除此成员"
                            disabled={removing.has(user.user_id)}
                            onClick={() => handleRemoveMember(user)}
                            style={{
                              display: 'inline-flex', alignItems: 'center', gap: 4,
                              padding: '4px 10px', borderRadius: 6, border: 'none',
                              background: removing.has(user.user_id) ? '#fca5a5' : 'transparent',
                              color: removing.has(user.user_id) ? '#fff' : 'var(--text-tertiary)',
                              cursor: 'pointer', fontSize: 12, whiteSpace: 'nowrap',
                              transition: 'all 0.1s',
                            }}
                            onMouseEnter={e => { if (!removing.has(user.user_id)) { e.currentTarget.style.background = '#fee2e2'; e.currentTarget.style.color = '#ef4444'; } }}
                            onMouseLeave={e => { if (!removing.has(user.user_id)) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-tertiary)'; } }}
                          >
                            {removing.has(user.user_id) ? '移除中...' : '移除'}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </DetailSection>

              {/* ── Permissions summary ── */}
              <DetailSection title={`权限 (${selectedRole.permission_ids?.length || 0})`}>
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)', padding: '4px 0' }}>
                  <span>此组关联 {selectedRole.permission_ids?.length || 0} 个权限。 </span>
                  {onNavigate && (
                    <button
                      type="button"
                      style={{ fontSize: 12, color: 'var(--accent-primary)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline', padding: 0 }}
                      onClick={() => onNavigate('permissions')}
                    >
                      前往权限管理 →
                    </button>
                  )}
                </div>
              </DetailSection>

              {/* ── Metadata ── */}
              <DetailSection title="元数据">
                <DetailMetaRow label="创建时间" value={new Date(selectedRole.created_at).toLocaleString('zh-CN')} />
                <DetailMetaRow label="更新时间" value={new Date(selectedRole.updated_at).toLocaleString('zh-CN')} />
                <DetailMetaRow label="Role ID" value={selectedRole.role_id} />
              </DetailSection>
            </div>
          </div>
        ) : (
          <DetailEmpty icon="👈" text="从左侧选择一个组查看成员" />
        )}
      </main>
    </div>

    {/* ── Add Member Modal ── */}
    {addModalOpen && (
      <div className="modal-overlay" onClick={() => setAddModalOpen(false)}>
        <div className="modal" onClick={e => e.stopPropagation()} style={{ width: 520, maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}>
          <div className="modal__header">
            <h3 className="modal__title">添加成员 — {selectedRole?.name}</h3>
            <button className="modal__close" onClick={() => setAddModalOpen(false)}>×</button>
          </div>
          <div className="modal__body" style={{ flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <input
              ref={addSearchRef}
              className="form-input"
              value={addSearch}
              onChange={e => setAddSearch(e.target.value)}
              placeholder="搜索用户名、ID 或邮箱…"
              style={{ marginBottom: 12, width: '100%' }}
            />
            <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
              {filteredAvailable.length === 0 ? (
                <p style={{ textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12, padding: 24 }}>
                  {addSearch ? '没有匹配的用户' : '所有用户已是此组成员'}
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {filteredAvailable.map(user => {
                    const checked = addingIds.has(user.user_id);
                    return (
                      <label key={user.user_id} style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        padding: '8px 10px', borderRadius: 8, cursor: 'pointer',
                        background: checked ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)' : 'transparent',
                        border: checked ? '1px solid color-mix(in srgb, var(--accent-primary) 20%, transparent)' : '1px solid transparent',
                        transition: 'all 0.1s',
                      }}>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleAddUser(user.user_id)}
                          style={{ accentColor: 'var(--accent-primary)', width: 14, height: 14 }}
                        />
                        <div style={{
                          width: 26, height: 26, borderRadius: 6,
                          background: 'var(--accent-primary)', flexShrink: 0,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          color: '#fff', fontSize: 11, fontWeight: 600,
                        }}>
                          {(user.username || user.user_id).charAt(0).toUpperCase()}
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
                            {user.username || user.user_id}
                          </div>
                          <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                            <span className="mono">{user.user_id}</span>
                            {user.email && <span> · {user.email}</span>}
                          </div>
                        </div>
                        <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>
                          当前 {user.role_ids?.length || 0} 个组
                        </span>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
          <div className="modal__footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
              {addingIds.size > 0 ? `已选 ${addingIds.size} 人` : '选择要添加的用户'}
            </span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn--secondary" onClick={() => setAddModalOpen(false)}>取消</button>
              <button
                className="btn btn--primary"
                onClick={handleAddMembers}
                disabled={adding || addingIds.size === 0}
              >
                {adding ? '添加中...' : `添加 (${addingIds.size})`}
              </button>
            </div>
          </div>
        </div>
      </div>
    )}

    <style>{`
      .modal-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,0.4);
        z-index: 2000;
        display: flex;
        justify-content: center;
        align-items: center;
      }
      .modal {
        background: var(--bg-elevated);
        border-radius: 14px;
        border: 1px solid var(--border-default);
        box-shadow: 0 25px 60px rgba(0,0,0,0.25);
        width: 480px;
        max-width: 90vw;
      }
      .modal__header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 24px;
        border-bottom: 1px solid var(--border-subtle);
      }
      .modal__title {
        margin: 0;
        font-size: 15px;
        font-weight: 600;
        color: var(--text-primary);
      }
      .modal__close {
        background: none;
        border: none;
        font-size: 22px;
        cursor: pointer;
        color: var(--text-tertiary);
        padding: 0;
        line-height: 1;
      }
      .modal__body {
        padding: 16px 24px;
      }
      .modal__footer {
        padding: 12px 24px;
        border-top: 1px solid var(--border-subtle);
        display: flex;
        justify-content: flex-end;
        gap: 8px;
      }
    `}</style>
    </>
  );
};

export default RoleGroupManagement;
