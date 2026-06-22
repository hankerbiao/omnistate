import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../services/api';
import type { UserResponse, CurrentUserPermissionsResponse, PermissionResponse } from '../types';
import { Dialog, DialogContent } from './ui/dialog';

// 用户状态中文映射
const USER_STATUS_LABELS: Record<string, string> = {
  ACTIVE: '启用',
  INACTIVE: '禁用',
  PENDING: '待激活',
};

// ── 权限分类元数据 ──
interface CategoryMeta {
  icon: string;
  color: string;
  bg: string;
  label: string;
}

const CATEGORY_META: Record<string, CategoryMeta> = {
  users:        { icon: '👤', color: '#3b82f6', bg: 'rgba(59,130,246,0.08)', label: '用户管理' },
  roles:        { icon: '👥', color: '#8b5cf6', bg: 'rgba(139,92,246,0.08)', label: '角色管理' },
  permissions:  { icon: '🔐', color: '#ec4899', bg: 'rgba(236,72,153,0.08)', label: '权限管理' },
  requirements: { icon: '📐', color: '#f59e0b', bg: 'rgba(245,158,11,0.08)', label: '需求管理' },
  test_cases:   { icon: '📋', color: '#10b981', bg: 'rgba(16,185,129,0.08)', label: '测试用例' },
  work_items:   { icon: '⚙️', color: '#6366f1', bg: 'rgba(99,102,241,0.08)', label: '工作流' },
  catalog:      { icon: '📁', color: '#06b6d4', bg: 'rgba(6,182,212,0.08)', label: '目录管理' },
  execution:    { icon: '▶️', color: '#f97316', bg: 'rgba(249,115,22,0.08)', label: '执行管理' },
  automation:   { icon: '🤖', color: '#14b8a6', bg: 'rgba(20,184,166,0.08)', label: '自动化' },
  navigation:   { icon: '🧭', color: '#a855f7', bg: 'rgba(168,85,247,0.08)', label: '导航管理' },
  other:        { icon: '📦', color: '#6b7280', bg: 'rgba(107,114,128,0.08)', label: '其他' },
};

const ProfilePage: React.FC = () => {
  const [userInfo, setUserInfo] = useState<UserResponse | null>(null);
  const [permissionsInfo, setPermissionsInfo] = useState<CurrentUserPermissionsResponse | null>(null);
  const [allPermissions, setAllPermissions] = useState<PermissionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [permSearch, setPermSearch] = useState('');
  const [permModalOpen, setPermModalOpen] = useState(false);
  const [editingEmail, setEditingEmail] = useState(false);
  const [emailDraft, setEmailDraft] = useState('');
  const [savingEmail, setSavingEmail] = useState(false);
  const [emailSuccess, setEmailSuccess] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [editingItcode, setEditingItcode] = useState(false);
  const [itcodeDraft, setItcodeDraft] = useState('');
  const [savingItcode, setSavingItcode] = useState(false);
  const [itcodeSuccess, setItcodeSuccess] = useState<string | null>(null);
  const [itcodeError, setItcodeError] = useState<string | null>(null);
  const [savingSubscription, setSavingSubscription] = useState(false);

  const fetchUserData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 核心数据：个人信息 + 自己的权限 — 所有用户都能访问
      const [userRes, permsRes] = await Promise.all([
        api.getCurrentUser(),
        api.getCurrentUserPermissions(),
      ]);

      if (userRes.code === 0 || userRes.code === 200) {
        setUserInfo(userRes.data);
      } else {
        setError(userRes.message || '获取用户信息失败');
        setLoading(false);
        return;
      }
      if (permsRes.code === 0 || permsRes.code === 200) {
        setPermissionsInfo(permsRes.data);
      }

      // 扩展数据：全量权限和角色列表 — 仅管理员有权限，非管理员静默降级
      try {
        const allPermsRes = await api.listPermissions();
        if (allPermsRes.code === 0 || allPermsRes.code === 200) {
          setAllPermissions(allPermsRes.data || []);
        }
      } catch {
        // 非管理员无权限查看全量权限列表，不影响页面展示
      }
    } catch (err) {
      setError('获取用户信息失败');
      console.error('Fetch user data error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchUserData(); }, [fetchUserData]);

  // ── 权限查询表 ──
  const permMap = useMemo(() => {
    const map = new Map<string, PermissionResponse>();
    for (const p of allPermissions) map.set(p.code, p);
    return map;
  }, [allPermissions]);

  const getPermissionName = (code: string): string =>
    permMap.get(code)?.name || code;

  const getPermissionDescription = (code: string): string | undefined =>
    permMap.get(code)?.description || undefined;

  const getCategoryKey = (code: string): string => {
    const [resource] = code.split(':');
    return resource || 'other';
  };

  // ── 全量分类汇总（用于卡片预览） ──
  const allPermCategories = useMemo(() => {
    const codes = permissionsInfo?.permissions || [];
    const grouped: Record<string, string[]> = {};
    for (const code of codes) {
      const cat = getCategoryKey(code);
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(code);
    }
    return Object.entries(grouped)
      .map(([key, items]) => ({
        key,
        label: CATEGORY_META[key]?.label || key,
        icon: CATEGORY_META[key]?.icon || '📦',
        color: CATEGORY_META[key]?.color || '#6b7280',
        bg: CATEGORY_META[key]?.bg || 'rgba(107,114,128,0.08)',
        items,
      }))
      .sort((a, b) => b.items.length - a.items.length);
  }, [permissionsInfo]);

  // ── 分组 + 搜索（用于弹窗） ──
  const groupedAndFiltered = useMemo(() => {
    const codes = permissionsInfo?.permissions || [];
    const q = permSearch.trim().toLowerCase();

    const grouped: Record<string, string[]> = {};
    for (const code of codes) {
      if (q && !code.toLowerCase().includes(q) && !getPermissionName(code).toLowerCase().includes(q)) continue;
      const cat = getCategoryKey(code);
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(code);
    }

    return Object.entries(grouped)
      .map(([key, items]) => ({
        key,
        label: CATEGORY_META[key]?.label || key,
        icon: CATEGORY_META[key]?.icon || '📦',
        color: CATEGORY_META[key]?.color || '#6b7280',
        bg: CATEGORY_META[key]?.bg || 'rgba(107,114,128,0.08)',
        items: items.sort(),
      }))
      .sort((a, b) => b.items.length - a.items.length);
  }, [permissionsInfo, permSearch, permMap]);

  const getStatusStyle = (status: string) => {
    const styleMap: Record<string, { bg: string; color: string }> = {
      ACTIVE: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
      INACTIVE: { bg: 'var(--surface-tertiary)', color: 'var(--text-tertiary)' },
      PENDING: { bg: 'var(--status-warning-bg)', color: 'var(--status-warning)' },
    };
    return styleMap[status] || { bg: 'var(--surface-tertiary)', color: 'var(--text-secondary)' };
  };

  const handleStartEditEmail = () => {
    setEmailDraft(userInfo?.email || '');
    setEditingEmail(true);
    setEmailError(null);
    setEmailSuccess(null);
  };

  const handleCancelEditEmail = () => {
    setEditingEmail(false);
    setEmailDraft('');
    setEmailError(null);
  };

  const handleSaveEmail = async () => {
    if (!userInfo) return;
    const trimmed = emailDraft.trim();
    if (trimmed && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setEmailError('邮箱格式不正确');
      return;
    }
    setSavingEmail(true);
    setEmailError(null);
    setEmailSuccess(null);
    try {
      const res = await api.updateUser(userInfo.user_id, { email: trimmed || undefined });
      if (res.code === 0 || res.code === 200) {
        setUserInfo({ ...userInfo, email: res.data?.email || trimmed });
        setEditingEmail(false);
        setEmailSuccess('邮箱已更新');
        setTimeout(() => setEmailSuccess(null), 3000);
      } else {
        setEmailError(res.message || '更新邮箱失败');
      }
    } catch {
      setEmailError('更新邮箱失败，请稍后重试');
    } finally {
      setSavingEmail(false);
    }
  };

  const handleStartEditItcode = () => {
    setItcodeDraft(userInfo?.itcode || '');
    setEditingItcode(true);
    setItcodeError(null);
    setItcodeSuccess(null);
  };

  const handleCancelEditItcode = () => {
    setEditingItcode(false);
    setItcodeDraft('');
    setItcodeError(null);
  };

  const handleSaveItcode = async () => {
    if (!userInfo) return;
    const trimmed = itcodeDraft.trim();
    setSavingItcode(true);
    setItcodeError(null);
    setItcodeSuccess(null);
    try {
      const res = await api.updateUser(userInfo.user_id, { itcode: trimmed || undefined });
      if (res.code === 0 || res.code === 200) {
        setUserInfo({ ...userInfo, itcode: res.data?.itcode || trimmed });
        setEditingItcode(false);
        setItcodeSuccess('通知 itcode 已更新');
        setTimeout(() => setItcodeSuccess(null), 3000);
      } else {
        setItcodeError(res.message || '更新 itcode 失败');
      }
    } catch {
      setItcodeError('更新 itcode 失败，请稍后重试');
    } finally {
      setSavingItcode(false);
    }
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
        <button style={styles.retryBtn} onClick={fetchUserData}>重试</button>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>个人信息</h1>
      </div>

      <div style={styles.content}>
        {/* ── User Info Card ── */}
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
                <span className="status-badge" style={getStatusStyle(userInfo.status)}>
                  {USER_STATUS_LABELS[userInfo.status] || userInfo.status}
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
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {editingEmail ? (
                    <>
                      <input
                        className="form-input"
                        style={{ flex: 1, fontSize: 13, minWidth: 180 }}
                        value={emailDraft}
                        onChange={e => setEmailDraft(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') handleSaveEmail(); if (e.key === 'Escape') handleCancelEditEmail(); }}
                        placeholder="输入邮箱地址"
                        autoFocus
                        disabled={savingEmail}
                      />
                      <button
                        className="btn btn--primary btn--sm"
                        onClick={handleSaveEmail}
                        disabled={savingEmail}
                        style={{ whiteSpace: 'nowrap', fontSize: 12, padding: '5px 12px' }}
                      >
                        {savingEmail ? '保存中…' : '保存'}
                      </button>
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={handleCancelEditEmail}
                        disabled={savingEmail}
                        style={{ whiteSpace: 'nowrap', fontSize: 12, padding: '5px 12px' }}
                      >
                        取消
                      </button>
                    </>
                  ) : (
                    <>
                      <span style={styles.infoValue}>{userInfo.email || (
                        <span style={{ color: 'var(--text-tertiary)', fontStyle: 'italic' }}>未设置</span>
                      )}</span>
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={handleStartEditEmail}
                        title="编辑邮箱"
                        style={{ fontSize: 11, padding: '2px 8px', lineHeight: 1.4 }}
                      >
                        ✏️ 编辑
                      </button>
                    </>
                  )}
                </div>
                {emailError && (
                  <span style={{ fontSize: 11, color: 'var(--status-error)', marginTop: 2 }}>{emailError}</span>
                )}
                {emailSuccess && (
                  <span style={{ fontSize: 11, color: 'var(--status-success)', marginTop: 2 }}>{emailSuccess}</span>
                )}
              </div>
              <div style={styles.infoItem}>
                <span style={styles.infoLabel}>光圈通知 itcode</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {editingItcode ? (
                    <>
                      <input
                        className="form-input"
                        style={{ flex: 1, fontSize: 13, minWidth: 180 }}
                        value={itcodeDraft}
                        onChange={e => setItcodeDraft(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') handleSaveItcode(); if (e.key === 'Escape') handleCancelEditItcode(); }}
                        placeholder="输入 itcode"
                        autoFocus
                        disabled={savingItcode}
                      />
                      <button
                        className="btn btn--primary btn--sm"
                        onClick={handleSaveItcode}
                        disabled={savingItcode}
                        style={{ whiteSpace: 'nowrap', fontSize: 12, padding: '5px 12px' }}
                      >
                        {savingItcode ? '保存中…' : '保存'}
                      </button>
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={handleCancelEditItcode}
                        disabled={savingItcode}
                        style={{ whiteSpace: 'nowrap', fontSize: 12, padding: '5px 12px' }}
                      >
                        取消
                      </button>
                    </>
                  ) : (
                    <>
                      <span style={styles.infoValue}>{userInfo.itcode || (
                        <span style={{ color: 'var(--text-tertiary)', fontStyle: 'italic' }}>未设置</span>
                      )}</span>
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={handleStartEditItcode}
                        title="编辑 itcode"
                        style={{ fontSize: 11, padding: '2px 8px', lineHeight: 1.4 }}
                      >
                        ✏️ 编辑
                      </button>
                    </>
                  )}
                </div>
                {itcodeError && (
                  <span style={{ fontSize: 11, color: 'var(--status-error)', marginTop: 2 }}>{itcodeError}</span>
                )}
                {itcodeSuccess && (
                  <span style={{ fontSize: 11, color: 'var(--status-success)', marginTop: 2 }}>{itcodeSuccess}</span>
                )}
                <span style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 2 }}>
                  用于接收光圈通知，请联系管理员获取
                </span>
              </div>
              <div style={styles.infoItem}>
                <span style={styles.infoLabel}>订阅通知</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
                    onClick={async () => {
                      if (!userInfo || savingSubscription) return;
                      setSavingSubscription(true);
                      try {
                        const newVal = !userInfo.subscribe_notifications;
                        await api.updateUser(userInfo.user_id, { subscribe_notifications: newVal });
                        setUserInfo({ ...userInfo, subscribe_notifications: newVal });
                      } catch (err) {
                        console.error('订阅操作失败:', err);
                      } finally {
                        setSavingSubscription(false);
                      }
                    }}>
                    <div style={{
                      position: 'relative', width: 40, height: 22, borderRadius: 11,
                      background: userInfo.subscribe_notifications ? '#3fb950' : 'var(--border-default)',
                      transition: 'background 0.2s',
                    }}>
                      <div style={{
                        position: 'absolute', top: 2,
                        left: userInfo.subscribe_notifications ? 20 : 2,
                        width: 18, height: 18, borderRadius: '50%',
                        background: '#fff', transition: 'left 0.2s',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                      }} />
                    </div>
                    <span style={{ fontSize: 13 }}>
                      {userInfo.subscribe_notifications ? '已订阅' : '未订阅'}
                    </span>
                  </label>
                </div>
                <span style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 2 }}>
                  订阅后，任务改派/指派等操作会通过光圈通知您
                </span>
              </div>
              <div style={styles.infoItem}>
                <span style={styles.infoLabel}>状态</span>
                <span style={styles.infoValue}>
                  <span className="status-badge" style={getStatusStyle(userInfo.status)}>
                    {USER_STATUS_LABELS[userInfo.status] || userInfo.status}
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

        {/* ── Permissions Card ── */}
        <div style={styles.card}>
          <div style={{ ...styles.cardHeader, cursor: 'pointer' }} onClick={() => setPermModalOpen(true)}>
            <h2 style={styles.cardTitle}>权限列表</h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={styles.badge}>{permissionsInfo?.permissions?.length || 0}</span>
              <span style={{ fontSize: 12, color: 'var(--accent-primary)', fontWeight: 500 }}>
                查看详情 →
              </span>
            </div>
          </div>
          {/* Summary preview */}
          <div style={styles.cardBody}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
              {allPermCategories.map(cat => (
                <div key={cat.key} style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '8px 12px', borderRadius: 8, background: cat.bg,
                  border: `0.5px solid ${cat.color}20`,
                }}>
                  <span style={{ fontSize: 16 }}>{cat.icon}</span>
                  <div>
                    <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500, display: 'block' }}>{cat.label}</span>
                    <span style={{ fontSize: 13, fontWeight: 600, color: cat.color }}>{cat.items.length}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Permissions Modal ── */}
      <Dialog open={permModalOpen} onOpenChange={setPermModalOpen}>
        <DialogContent style={{ padding: 0, gap: 0, width: 720, maxWidth: '90vw', maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '18px 24px', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h3 style={{ margin: 0, fontSize: 17, fontWeight: 600, color: 'var(--text-primary)' }}>权限列表</h3>
              <span style={styles.badge}>{permissionsInfo?.permissions?.length || 0}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <input
                className="form-input"
                style={{ width: 200, fontSize: 12, padding: '5px 10px' }}
                value={permSearch}
                onChange={e => setPermSearch(e.target.value)}
                placeholder="搜索权限名称或代码…"
              />
            </div>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
            {groupedAndFiltered.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                {groupedAndFiltered.map(cat => (
                  <div key={cat.key}>
                    {/* Category header */}
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10,
                      paddingBottom: 8, borderBottom: `2px solid ${cat.color}`,
                    }}>
                      <span style={{ fontSize: 20 }}>{cat.icon}</span>
                      <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', flex: 1 }}>{cat.label}</span>
                      <span style={{
                        fontSize: 11, fontWeight: 600, padding: '2px 10px', borderRadius: 8,
                        color: cat.color, background: `color-mix(in srgb, ${cat.color} 15%, transparent)`,
                      }}>{cat.items.length} 项</span>
                    </div>

                    {/* Permission cards */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {cat.items.map(code => {
                        const name = getPermissionName(code);
                        const desc = getPermissionDescription(code);
                        return (
                          <div key={code} style={{
                            padding: '10px 14px', borderRadius: 8, background: 'var(--surface-secondary)',
                            border: `0.5px solid ${cat.color}20`,
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{name}</span>
                              <span style={{
                                fontSize: 10, color: 'var(--text-tertiary)', fontFamily: 'monospace',
                                background: 'var(--surface-tertiary)', padding: '1px 6px', borderRadius: 4,
                              }}>{code}</span>
                            </div>
                            {desc && (
                              <p style={{
                                margin: '4px 0 0', fontSize: 12, color: 'var(--text-secondary)',
                                lineHeight: 1.5,
                              }}>{desc}</p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 14 }}>
                {permSearch ? '无匹配的权限' : '暂无权限'}
              </div>
            )}
          </div>

          <div style={{
            padding: '12px 24px', borderTop: '1px solid var(--border-subtle)',
            textAlign: 'right', fontSize: 12, color: 'var(--text-tertiary)',
          }}>
            共 {permissionsInfo?.permissions?.length || 0} 项权限
          </div>
        </DialogContent>
      </Dialog>
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
  // ── New permission styles ──
  catGrid: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '16px',
  } as const,
  catCard: {
    padding: '14px 16px',
    borderRadius: 'var(--radius-md)',
    border: '0.5px solid var(--border-subtle)',
    transition: 'box-shadow 0.15s',
  } as const,
  catHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
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