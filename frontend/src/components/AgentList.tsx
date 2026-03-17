import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { ExecutionAgent } from '../types';

interface AgentListProps {
  onLogout?: () => void;
}

const AgentList: React.FC<AgentListProps> = () => {
  const [agents, setAgents] = useState<ExecutionAgent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
  }, [fetchAgents]);

  const getStatusStyle = (agent: ExecutionAgent) => {
    if (!agent.is_online) {
      return {
        bg: 'var(--status-error-bg)',
        color: 'var(--accent-red)',
        text: '离线',
        pulse: false,
      };
    }
    switch (agent.status) {
      case 'ONLINE':
        return {
          bg: 'var(--status-success-bg)',
          color: 'var(--accent-green)',
          text: '在线',
          pulse: true,
        };
      default:
        return {
          bg: 'var(--status-warning-bg)',
          color: 'var(--accent-yellow)',
          text: agent.status,
          pulse: false,
        };
    }
  };

  const onlineCount = agents.filter(a => a.is_online).length;
  const offlineCount = agents.length - onlineCount;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.title}>执行代理</h1>
          <div style={styles.statsRow}>
            <span style={styles.statBadge}>
              <span style={styles.statDot} className="pulse" />
              在线 {onlineCount}
            </span>
            <span style={styles.statBadgeOffline}>
              <span style={styles.statDot} />
              离线 {offlineCount}
            </span>
          </div>
        </div>
        <div style={styles.headerActions}>
          <button style={styles.refreshBtn} onClick={fetchAgents} disabled={loading}>
            <span style={styles.btnIcon}>↻</span>
            {loading ? '加载中' : '刷新'}
          </button>
        </div>
      </div>

      {error && (
        <div style={styles.errorBanner}>
          <span>⚠</span> {error}
        </div>
      )}

      <div style={styles.grid}>
        {loading ? (
          <div style={styles.loadingState}>
            <div style={styles.spinner} />
            <span>加载代理信息...</span>
          </div>
        ) : agents.length === 0 ? (
          <div style={styles.emptyState}>
            <span style={styles.emptyIcon}>◉</span>
            <p>暂无执行代理</p>
          </div>
        ) : (
          agents.map((agent) => {
            const status = getStatusStyle(agent);
            return (
              <div
                key={agent.agent_id}
                style={styles.agentCard}
                className="agent-card"
              >
                <div style={styles.cardHeader}>
                  <div style={styles.agentIdSection}>
                    <span style={styles.agentId}>{agent.agent_id}</span>
                    <span
                      style={{
                        ...styles.statusDot,
                        backgroundColor: status.color,
                        boxShadow: status.pulse ? `0 0 8px ${status.color}` : 'none',
                      }}
                      className={status.pulse ? 'pulse' : ''}
                    />
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

                <div style={styles.cardBody}>
                  <div style={styles.infoRow}>
                    <span style={styles.infoLabel}>主机名</span>
                    <span style={styles.infoValue}>{agent.hostname}</span>
                  </div>
                  <div style={styles.infoRow}>
                    <span style={styles.infoLabel}>IP地址</span>
                    <span style={styles.infoValueMono}>{agent.ip}</span>
                  </div>
                  <div style={styles.infoRow}>
                    <span style={styles.infoLabel}>端口</span>
                    <span style={styles.infoValueMono}>{agent.port || '-'}</span>
                  </div>
                  <div style={styles.infoRow}>
                    <span style={styles.infoLabel}>区域</span>
                    <span style={styles.regionBadge}>{agent.region}</span>
                  </div>
                </div>

                <div style={styles.cardFooter}>
                  <div style={styles.timeInfo}>
                    <span style={styles.timeLabel}>最后心跳</span>
                    <span style={styles.timeValue}>
                      {new Date(agent.last_heartbeat_at).toLocaleString('zh-CN')}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .pulse {
          animation: pulse 2s ease-in-out infinite;
        }
        .agent-card:hover {
          transform: translateY(-2px);
          border-color: var(--accent-cyan);
          box-shadow: 0 8px 24px rgba(57, 208, 214, 0.15);
        }
      `}</style>
    </div>
  );
};

const styles = {
  container: {
    padding: '32px',
    maxWidth: '1400px',
    margin: '0 auto',
    animation: 'fadeIn 0.4s ease',
  } as const,
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '28px',
  } as const,
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '20px',
  } as const,
  title: {
    fontSize: '28px',
    fontWeight: 700,
    color: 'var(--text-primary)',
    letterSpacing: '-0.5px',
    margin: 0,
  } as const,
  statsRow: {
    display: 'flex',
    gap: '12px',
  } as const,
  statBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 14px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--accent-green)',
    backgroundColor: 'var(--status-success-bg)',
    borderRadius: '16px',
  } as const,
  statBadgeOffline: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 14px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--accent-red)',
    backgroundColor: 'var(--status-error-bg)',
    borderRadius: '16px',
  } as const,
  statDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: 'currentColor',
  } as const,
  headerActions: {
    display: 'flex',
    gap: '10px',
  } as const,
  refreshBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  btnIcon: {
    fontSize: '14px',
  } as const,
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
  } as const,
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
    gap: '20px',
  } as const,
  agentCard: {
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    overflow: 'hidden',
    transition: 'all var(--transition-normal)',
    animation: 'slideUp 0.4s ease forwards',
    opacity: 0,
  } as const,
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '18px 20px',
    backgroundColor: 'var(--bg-tertiary)',
    borderBottom: '1px solid var(--border-muted)',
  } as const,
  agentIdSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  } as const,
  agentId: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '15px',
    fontWeight: 600,
    color: 'var(--accent-cyan)',
  } as const,
  statusDot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
  } as const,
  statusBadge: {
    padding: '4px 12px',
    fontSize: '11px',
    fontWeight: 600,
    borderRadius: '12px',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  } as const,
  cardBody: {
    padding: '18px 20px',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '12px',
  } as const,
  infoRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  } as const,
  infoLabel: {
    fontSize: '13px',
    color: 'var(--text-muted)',
  } as const,
  infoValue: {
    fontSize: '14px',
    color: 'var(--text-primary)',
    fontWeight: 500,
  } as const,
  infoValueMono: {
    fontSize: '13px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--text-secondary)',
  } as const,
  regionBadge: {
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-purple)',
    backgroundColor: 'rgba(163, 113, 247, 0.15)',
    padding: '3px 10px',
    borderRadius: '6px',
  } as const,
  cardFooter: {
    padding: '14px 20px',
    borderTop: '1px solid var(--border-muted)',
    backgroundColor: 'var(--bg-primary)',
  } as const,
  timeInfo: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  } as const,
  timeLabel: {
    fontSize: '12px',
    color: 'var(--text-muted)',
  } as const,
  timeValue: {
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--text-secondary)',
  } as const,
  loadingState: {
    gridColumn: '1 / -1',
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    padding: '80px',
    color: 'var(--text-secondary)',
  } as const,
  spinner: {
    width: '40px',
    height: '40px',
    border: '3px solid var(--border-default)',
    borderTopColor: 'var(--accent-cyan)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  } as const,
  emptyState: {
    gridColumn: '1 / -1',
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    padding: '80px',
    color: 'var(--text-muted)',
  } as const,
  emptyIcon: {
    fontSize: '56px',
    opacity: 0.3,
  } as const,
};

export default AgentList;