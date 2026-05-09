import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { UserResponse, CurrentUserPermissionsResponse, PermissionResponse } from '../types';

const ProfilePage: React.FC = () => {
  const [userInfo, setUserInfo] = useState<UserResponse | null>(null);
  const [permissionsInfo, setPermissionsInfo] = useState<CurrentUserPermissionsResponse | null>(null);
  const [allPermissions, setAllPermissions] = useState<PermissionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUserData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [userRes, permsRes, allPermsRes] = await Promise.all([
        api.getCurrentUser(),
        api.getCurrentUserPermissions(),
        api.listPermissions(),
      ]);

      if (userRes.code === 0 || userRes.code === 200) {
        setUserInfo(userRes.data);
      } else {
        setError(userRes.message || '获取用户信息失败');
      }

      if (permsRes.code === 0 || permsRes.code === 200) {
        setPermissionsInfo(permsRes.data);
      }

      if (allPermsRes.code === 0 || allPermsRes.code === 200) {
        setAllPermissions(allPermsRes.data || []);
      }
    } catch (err) {
      setError('获取用户信息失败');
      console.error('Fetch user data error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUserData();
  }, [fetchUserData]);

  const getPermissionName = (code: string): string => {
    const perm = allPermissions.find(p => p.code === code);
    if (perm) {
      return `${perm.name} (${code})`;
    }
    return code;
  };

  const getPermissionCategory = (code: string): string => {
    const [resource] = code.split(':');
    return resource || 'other';
  };

  const groupedPermissions = permissionsInfo?.permissions.reduce((acc, code) => {
    const category = getPermissionCategory(code);
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(code);
    return acc;
  }, {} as Record<string, string[]>) || {};

  const categoryLabels: Record<string, string> = {
    users: '用户管理',
    roles: '角色管理',
    requirements: '需求管理',
    test_cases: '测试用例',
    work_items: '工作流',
    assets: '资产管理',
    execution: '执行管理',
    automation: '自动化',
    other: '其他',
  };

  const getStatusStyle = (status: string) => {
    const styleMap: Record<string, { bg: string; color: string }> = {
      ACTIVE: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
      INACTIVE: { bg: 'var(--surface-tertiary)', color: 'var(--text-tertiary)' },
      PENDING: { bg: 'var(--status-warning-bg)', color: 'var(--status-warning)' },
    };
    return styleMap[status] || { bg: 'var(--surface-tertiary)', color: 'var(--text-secondary)' };
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingState}>
          <div style={styles.spinner} />
          <span>加载中...</span>
        </div>
      </div>
    );
  }

  if (error || !userInfo) {
    return (
      <div style={styles.container}>
        <div style={styles.errorBanner}>
          <span>⚠</span> {error || '获取用户信息失败'}
        </div>
        <button style={styles.retryBtn} onClick={fetchUserData}>
          重试
        </button>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>个人信息</h1>
      </div>

      <div style={styles.content}>
        {/* User Info Card */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h2 style={styles.cardTitle}>基本信息</h2>
          </div>
          <div style={styles.cardBody}>
            <div style={styles.avatarSection}>
              <div style={styles.avatar}>
                {(userInfo.username || userInfo.user_id || 'U').charAt(0).toUpperCase()}
              </div>
              <div style={styles.userNameSection}>
                <span style={styles.userName}>{userInfo.username || userInfo.user_id}</span>
                <span
                  className="status-badge"
                  style={getStatusStyle(userInfo.status)}
                >
                  {userInfo.status}
                </span>
              </div>
            </div>

            <div style={styles.infoGrid}>
              <div style={styles.infoItem}>
                <span style={styles.infoLabel}>用户ID</span>
                <span style={styles.infoValue} className="mono">{userInfo.user_id}</span>
              </div>
              <div style={styles.infoItem}>
                <span style={styles.infoLabel}>用户名</span>
                <span style={styles.infoValue}>{userInfo.username}</span>
              </div>
              <div style={styles.infoItem}>
                <span style={styles.infoLabel}>邮箱</span>
                <span style={styles.infoValue}>{userInfo.email || '-'}</span>
              </div>
              <div style={styles.infoItem}>
                <span style={styles.infoLabel}>状态</span>
                <span style={styles.infoValue}>
                  <span className="status-badge" style={getStatusStyle(userInfo.status)}>
                    {userInfo.status}
                  </span>
                </span>
              </div>
              <div style={styles.infoItem}>
                <span style={styles.infoLabel}>创建时间</span>
                <span style={styles.infoValue} className="mono">
                  {new Date(userInfo.created_at).toLocaleString('zh-CN')}
                </span>
              </div>
              <div style={styles.infoItem}>
                <span style={styles.infoLabel}>更新时间</span>
                <span style={styles.infoValue} className="mono">
                  {new Date(userInfo.updated_at).toLocaleString('zh-CN')}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Roles Card */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h2 style={styles.cardTitle}>角色信息</h2>
            <span style={styles.badge}>{permissionsInfo?.roles?.length || 0}</span>
          </div>
          <div style={styles.cardBody}>
            {permissionsInfo?.roles && permissionsInfo.roles.length > 0 ? (
              <div style={styles.rolesList}>
                {permissionsInfo.roles.map((role) => (
                  <div key={role.role_id} style={styles.roleItem}>
                    <span style={styles.roleIcon}>👥</span>
                    <div style={styles.roleInfo}>
                      <span style={styles.roleName}>{role.role_name}</span>
                      <span style={styles.roleId} className="mono">{role.role_id}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={styles.emptyState}>
                <span>暂无角色</span>
              </div>
            )}
          </div>
        </div>

        {/* Permissions Card */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <h2 style={styles.cardTitle}>权限列表</h2>
            <span style={styles.badge}>{permissionsInfo?.permissions?.length || 0}</span>
          </div>
          <div style={styles.cardBody}>
            {Object.keys(groupedPermissions).length > 0 ? (
              <div style={styles.permissionsGrid}>
                {Object.entries(groupedPermissions).map(([category, codes]) => (
                  <div key={category} style={styles.permissionCategory}>
                    <h3 style={styles.categoryTitle}>
                      {categoryLabels[category] || category}
                    </h3>
                    <div style={styles.permissionsList}>
                      {codes.map((code) => (
                        <span key={code} style={styles.permissionTag}>
                          {getPermissionName(code)}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={styles.emptyState}>
                <span>暂无权限</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    padding: '32px',
    maxWidth: '1000px',
    margin: '0 auto',
    animation: 'fadeIn 0.4s ease',
  } as const,
  header: {
    marginBottom: '28px',
  } as const,
  title: {
    fontSize: '28px',
    fontWeight: 700,
    color: 'var(--text-primary)',
    letterSpacing: '-0.5px',
    margin: 0,
  } as const,
  content: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '24px',
  } as const,
  card: {
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-lg)',
    overflow: 'hidden',
  } as const,
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 20px',
    borderBottom: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--surface-secondary)',
  } as const,
  cardTitle: {
    fontSize: '15px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    margin: 0,
  } as const,
  cardBody: {
    padding: '20px',
  } as const,
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: '24px',
    height: '24px',
    padding: '0 8px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--accent-primary)',
    backgroundColor: 'var(--status-info-bg)',
    borderRadius: '12px',
  } as const,
  avatarSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    marginBottom: '24px',
    paddingBottom: '24px',
    borderBottom: '1px solid var(--border-subtle)',
  } as const,
  avatar: {
    width: '64px',
    height: '64px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'var(--accent-primary)',
    borderRadius: '50%',
    fontSize: '24px',
    fontWeight: 600,
    color: 'white',
  } as const,
  userNameSection: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '6px',
  } as const,
  userName: {
    fontSize: '20px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  } as const,
  infoGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '16px',
  } as const,
  infoItem: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
  } as const,
  infoLabel: {
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  } as const,
  infoValue: {
    fontSize: '14px',
    color: 'var(--text-primary)',
  } as const,
  rolesList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '12px',
  } as const,
  roleItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 16px',
    backgroundColor: 'var(--surface-secondary)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-subtle)',
  } as const,
  roleIcon: {
    fontSize: '20px',
  } as const,
  roleInfo: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '2px',
  } as const,
  roleName: {
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--text-primary)',
  } as const,
  roleId: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
  } as const,
  permissionsGrid: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '20px',
  } as const,
  permissionCategory: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  } as const,
  categoryTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    margin: 0,
  } as const,
  permissionsList: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '8px',
  } as const,
  permissionTag: {
    display: 'inline-flex',
    padding: '4px 10px',
    fontSize: '12px',
    color: 'var(--accent-primary)',
    backgroundColor: 'var(--status-info-bg)',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid rgba(37, 99, 235, 0.2)',
  } as const,
  emptyState: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
    color: 'var(--text-tertiary)',
    fontSize: '13px',
  } as const,
  loadingState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    padding: '60px',
    color: 'var(--text-secondary)',
  } as const,
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid var(--border-default)',
    borderTopColor: 'var(--accent-primary)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  } as const,
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '14px 18px',
    backgroundColor: 'var(--status-error-bg)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--status-error)',
    fontSize: '14px',
    marginBottom: '16px',
  } as const,
  retryBtn: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 500,
    color: 'white',
    backgroundColor: 'var(--accent-primary)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  } as const,
};

export default ProfilePage;