import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { ExecutionAgent } from '../types';
import { formatRelativeTime } from '../utils/date';
import PageToolbar, { StatPill } from './ui/PageToolbar';

interface AgentListProps {
  onLogout?: () => void;
}

const AgentList: React.FC<AgentListProps> = () => {
  const [agents, setAgents] = useState<ExecutionAgent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [cleaningOffline, setCleaningOffline] = useState(false);

  const handleDeleteAgent = useCallback(async (agentId: string) => {
    if (!window.confirm(`确定要删除代理 ${agentId} 吗？`)) {
      return;
    }

    setDeletingId(agentId);
    setDeleteError(null);

    try {
      await api.deleteAgent(agentId);
      setAgents(prev => prev.filter(a => a.agent_id !== agentId));
    } catch (err) {
      setDeleteError(`删除代理失败: ${agentId}`);
      console.error('Delete agent error:', err);
    } finally {
      setDeletingId(null);
    }
  }, []);

  const handleCleanupOffline = useCallback(async () => {
    const offlineAgents = agents.filter(a => !a.is_online);
    if (offlineAgents.length === 0) {
      return;
    }

    const preview = offlineAgents.slice(0, 5).map(a => a.agent_id).join('、');
    const suffix = offlineAgents.length > 5 ? ` 等 ${offlineAgents.length} 个` : '';
    if (!window.confirm(`确定清理 ${offlineAgents.length} 个离线代理吗？\n${preview}${suffix}`)) {
      return;
    }

    setCleaningOffline(true);
    setDeleteError(null);

    try {
      const response = await api.cleanupOfflineAgents();
      const deletedIds = new Set(response.data?.deleted_agent_ids || []);
      setAgents(prev => prev.filter(a => !deletedIds.has(a.agent_id)));
    } catch (err) {
      setDeleteError('清理离线代理失败');
      console.error('Cleanup offline agents error:', err);
    } finally {
      setCleaningOffline(false);
    }
  }, [agents]);

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.listAgents({});
      setAgents(response.data || []);
    } catch (err) {
      setError('获取代理列表失败');
      console.error('Fetch agents error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
    const interval = setInterval(fetchAgents, 15000); // 每 15 秒刷新
    return () => clearInterval(interval);
  }, [fetchAgents]);

  const onlineCount = agents.filter(a => a.is_online).length;
  const offlineCount = agents.length - onlineCount;

  const statusClass = (agent: ExecutionAgent) => {
    if (!agent.is_online) return 'status-badge--error';
    if (agent.status === 'ONLINE') return 'status-badge--success';
    return 'status-badge--warning';
  };

  const statusText = (agent: ExecutionAgent) => {
    if (!agent.is_online) return '离线';
    if (agent.status === 'ONLINE') return '在线';
    return agent.status;
  };

  return (
    <div className="page-content">
      <PageToolbar
        meta={(
          <>
            <StatPill label="全部" value={agents.length} />
            <StatPill label="在线" value={onlineCount} tone="success" dot pulse />
            <StatPill label="离线" value={offlineCount} tone="danger" dot />
          </>
        )}
        actions={(
          <>
            <button
              type="button"
              className="btn btn--danger-outline btn--sm"
              onClick={handleCleanupOffline}
              disabled={loading || cleaningOffline || offlineCount === 0}
              title={offlineCount === 0 ? '当前没有离线代理' : '删除所有离线代理记录'}
            >
              {cleaningOffline ? '清理中…' : `清理离线 (${offlineCount})`}
            </button>
            <button
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={fetchAgents}
              disabled={loading || cleaningOffline}
            >
              {loading ? '加载中…' : '刷新'}
            </button>
          </>
        )}
      />

      {error && (
        <div className="error-banner" style={{ marginBottom: 16 }}>
          <span aria-hidden>⚠</span> {error}
        </div>
      )}

      {deleteError && (
        <div className="error-banner" style={{ marginBottom: 16 }}>
          <span aria-hidden>⚠</span> {deleteError}
        </div>
      )}

      {loading ? (
        <div className="loading-overlay">
          <div className="loading-spinner" />
          <span>加载代理信息…</span>
        </div>
      ) : agents.length === 0 ? (
        <div className="empty-state surface-card">
          <span className="empty-state__icon" aria-hidden>◉</span>
          <p className="empty-state__text">暂无执行代理</p>
          <p style={{ fontSize: 13, color: 'var(--text-tertiary)', marginTop: 8 }}>
            启动客户端后将自动注册到此列表
          </p>
        </div>
      ) : (
        <div className="agent-grid">
          {agents.map(agent => (
            <article key={agent.agent_id} className="agent-card">
              <div className="agent-card__head">
                <span className="agent-card__id">{agent.agent_id}</span>
                <span className={`status-badge ${statusClass(agent)}`}>{statusText(agent)}</span>
              </div>

              <div className="agent-card__body">
                <div className="agent-card__row">
                  <span className="agent-card__label">主机名</span>
                  <span>{agent.hostname}</span>
                </div>
                <div className="agent-card__row">
                  <span className="agent-card__label">IP 地址</span>
                  <span className="mono">{agent.ip}</span>
                </div>
                <div className="agent-card__row">
                  <span className="agent-card__label">端口</span>
                  <span className="mono">{agent.port || '—'}</span>
                </div>
                <div className="agent-card__row">
                  <span className="agent-card__label">区域</span>
                  <span className="stat-pill stat-pill--info" style={{ padding: '2px 8px', fontSize: 11 }}>
                    {agent.region}
                  </span>
                </div>
              </div>

              <div className="agent-card__foot">
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                  心跳 ·{' '}
                  <time className="mono" style={{ color: 'var(--text-secondary)' }}>
                    {formatRelativeTime(agent.last_heartbeat_at)}
                  </time>
                </div>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  style={{ color: 'var(--status-error)' }}
                  onClick={() => handleDeleteAgent(agent.agent_id)}
                  disabled={deletingId === agent.agent_id}
                >
                  {deletingId === agent.agent_id ? '删除中…' : '删除'}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};

export default AgentList;
