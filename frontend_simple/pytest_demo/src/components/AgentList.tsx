import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { ExecutionAgent } from '../types';

interface AgentListProps {
  onLogout: () => void;
}

const AgentList: React.FC<AgentListProps> = ({ onLogout }) => {
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

  const handleRefresh = () => {
    fetchAgents();
  };

  const getStatusBadgeStyle = (status: string, isOnline: boolean) => {
    if (!isOnline) {
      return {
        backgroundColor: '#dc3545',
        color: '#fff',
        padding: '4px 8px',
        borderRadius: '4px',
        fontSize: '12px',
        fontWeight: '500',
      };
    }

    switch (status) {
      case 'ONLINE':
        return {
          backgroundColor: '#28a745',
          color: '#fff',
          padding: '4px 8px',
          borderRadius: '4px',
          fontSize: '12px',
          fontWeight: '500',
        };
      case 'OFFLINE':
        return {
          backgroundColor: '#6c757d',
          color: '#fff',
          padding: '4px 8px',
          borderRadius: '4px',
          fontSize: '12px',
          fontWeight: '500',
        };
      default:
        return {
          backgroundColor: '#ffc107',
          color: '#000',
          padding: '4px 8px',
          borderRadius: '4px',
          fontSize: '12px',
          fontWeight: '500',
        };
    }
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>执行代理列表</h1>
        <div style={styles.headerButtons}>
          <button
            style={styles.refreshButton}
            onClick={handleRefresh}
            disabled={loading}
          >
            {loading ? '刷新中...' : '刷新'}
          </button>
          <button
            style={styles.logoutButton}
            onClick={onLogout}
          >
            退出登录
          </button>
        </div>
      </div>

      {error && (
        <div style={styles.errorMessage}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={styles.loading}>加载中...</div>
      ) : (
        <div style={styles.tableContainer}>
          <table style={styles.table}>
            <thead>
              <tr style={styles.tableHeader}>
                <th style={styles.tableCell}>代理ID</th>
                <th style={styles.tableCell}>主机名</th>
                <th style={styles.tableCell}>IP地址</th>
                <th style={styles.tableCell}>端口</th>
                <th style={styles.tableCell}>区域</th>
                <th style={styles.tableCell}>状态</th>
                <th style={styles.tableCell}>在线状态</th>
                <th style={styles.tableCell}>最后心跳</th>
              </tr>
            </thead>
            <tbody>
              {agents.length === 0 ? (
                <tr>
                  <td colSpan={8} style={styles.emptyCell}>
                    暂无代理
                  </td>
                </tr>
              ) : (
                agents.map((agent) => (
                  <tr key={agent.agent_id} style={styles.tableRow}>
                    <td style={styles.tableCell}>{agent.agent_id}</td>
                    <td style={styles.tableCell}>{agent.hostname}</td>
                    <td style={styles.tableCell}>{agent.ip}</td>
                    <td style={styles.tableCell}>{agent.port || '-'}</td>
                    <td style={styles.tableCell}>{agent.region}</td>
                    <td style={styles.tableCell}>
                      <span style={getStatusBadgeStyle(agent.status, agent.is_online)}>
                        {agent.status}
                      </span>
                    </td>
                    <td style={styles.tableCell}>
                      {agent.is_online ? (
                        <span style={styles.onlineBadge}>在线</span>
                      ) : (
                        <span style={styles.offlineBadge}>离线</span>
                      )}
                    </td>
                    <td style={styles.tableCell}>{formatDateTime(agent.last_heartbeat_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    padding: '20px',
    maxWidth: '1200px',
    margin: '0 auto',
  } as const,
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
  } as const,
  title: {
    fontSize: '28px',
    fontWeight: 'bold',
    color: '#333',
    margin: 0,
  } as const,
  headerButtons: {
    display: 'flex',
    gap: '10px',
  } as const,
  refreshButton: {
    padding: '10px 20px',
    backgroundColor: '#007bff',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
  } as const,
  logoutButton: {
    padding: '10px 20px',
    backgroundColor: '#dc3545',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
  } as const,
  errorMessage: {
    padding: '12px',
    backgroundColor: '#fee',
    border: '1px solid #fcc',
    borderRadius: '4px',
    color: '#c33',
    fontSize: '14px',
    marginBottom: '20px',
  } as const,
  loading: {
    textAlign: 'center' as const,
    padding: '40px',
    fontSize: '16px',
    color: '#666',
  } as const,
  tableContainer: {
    overflowX: 'auto' as const,
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  } as const,
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    backgroundColor: '#fff',
  } as const,
  tableHeader: {
    backgroundColor: '#f8f9fa',
  } as const,
  tableRow: {
    borderBottom: '1px solid #dee2e6',
  } as const,
  tableCell: {
    padding: '12px',
    textAlign: 'left' as const,
    borderBottom: '1px solid #dee2e6',
    fontSize: '14px',
  } as const,
  emptyCell: {
    textAlign: 'center' as const,
    padding: '40px',
    fontSize: '14px',
    color: '#999',
  } as const,
  onlineBadge: {
    backgroundColor: '#28a745',
    color: '#fff',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: '500',
  } as const,
  offlineBadge: {
    backgroundColor: '#dc3545',
    color: '#fff',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: '500',
  } as const,
};

export default AgentList;