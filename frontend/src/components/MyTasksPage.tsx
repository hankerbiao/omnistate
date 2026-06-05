import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import type { WorkItem, TestCaseResponse, RequirementResponse } from '../types';
import { WorkflowPanel, WorkflowActionToolbar } from './workflow';
import {
  getStateLabel,
  getWorkflowStateStyle,
  type WorkflowTypeCode,
} from '../constants/workflowLabels';
import PageToolbar, { StatPill } from './ui/PageToolbar';

const TYPE_LABELS: Record<string, string> = {
  REQUIREMENT: '需求',
  TEST_CASE: '测试用例',
};

const TYPE_COLORS: Record<string, { bg: string; color: string }> = {
  REQUIREMENT: { bg: '#e8f5e9', color: '#2e7d32' },
  TEST_CASE: { bg: '#e3f2fd', color: '#1565c0' },
};

interface MyTasksPageProps {
  userId: string;
}

const MyTasksPage: React.FC<MyTasksPageProps> = ({ userId }) => {
  const [items, setItems] = useState<WorkItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [itemDetail, setItemDetail] = useState<RequirementResponse | TestCaseResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [workflowRefreshSignal, setWorkflowRefreshSignal] = useState(0);

  const fetchMyTasks = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.listMyWorkItems(userId);
      setItems(response.data || []);
    } catch (err) {
      setError('获取任务列表失败');
      console.error('Fetch my tasks error:', err);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    fetchMyTasks();
  }, [fetchMyTasks]);

  const loadItemDetail = async (item: WorkItem) => {
    setLoadingDetail(true);
    setItemDetail(null);
    try {
      if (item.type_code === 'REQUIREMENT' && item.req_id) {
        const res = await api.getRequirement(item.req_id);
        setItemDetail(res.data);
      } else if (item.type_code === 'TEST_CASE') {
        const caseId = (item as WorkItem & { case_id?: string }).case_id;
        if (caseId) {
          const res = await api.getTestCase(caseId);
          setItemDetail(res.data);
        }
      }
    } catch (err) {
      console.error('Fetch item detail error:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleToggleExpand = async (itemId: string) => {
    if (expandedId === itemId) {
      setExpandedId(null);
      setItemDetail(null);
      return;
    }
    setExpandedId(itemId);
    const item = items.find((i) => i.item_id === itemId);
    if (item) await loadItemDetail(item);
  };

  const handleTaskWorkflowSuccess = async () => {
    await fetchMyTasks();
    setWorkflowRefreshSignal((n) => n + 1);
  };

  const groupedItems = items.reduce<Record<string, WorkItem[]>>((acc, item) => {
    const type = item.type_code;
    if (!acc[type]) acc[type] = [];
    acc[type].push(item);
    return acc;
  }, {});

  const typeOrder = ['REQUIREMENT', 'TEST_CASE'];

  const getTypeCode = (type: string): WorkflowTypeCode =>
    type === 'TEST_CASE' ? 'TEST_CASE' : 'REQUIREMENT';

  return (
    <div className="page-content">
      <PageToolbar
        meta={(
          <>
            <StatPill label="待处理" value={items.length} />
            <StatPill label="用户" value={userId} tone="info" />
          </>
        )}
        actions={(
          <button type="button" className="btn btn--secondary btn--sm" onClick={fetchMyTasks} disabled={loading}>
            刷新
          </button>
        )}
      />

      <div className="info-banner">
        卡片<strong>右上角</strong>可直接<strong>流转状态</strong>；展开卡片可查看<strong>流转历史</strong>与详情。
        无可用操作时请 Topbar 切换对应角色用户。
      </div>

      {error && (
        <div className="error-banner" style={{ marginBottom: 16, justifyContent: 'space-between' }}>
          {error}
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => setError(null)}>×</button>
        </div>
      )}

      {loading ? (
        <div className="loading-overlay">
          <div className="loading-spinner" />
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">✅</div>
          <p className="empty-state__text">暂无待处理的任务</p>
        </div>
      ) : (
        <div style={styles.list}>
          {typeOrder.map((type) => {
            const typeItems = groupedItems[type];
            if (!typeItems?.length) return null;
            return (
              <div key={type} style={styles.group}>
                <div style={styles.groupHeader}>
                  <span
                    className="task-group__badge"
                    style={groupBadgeStyle(TYPE_COLORS[type] || { bg: '#f5f5f5', color: '#666' })}
                  >
                    {TYPE_LABELS[type] || type}
                  </span>
                  <span style={styles.groupCount}>{typeItems.length} 项</span>
                </div>
                {typeItems.map((item) => {
                  const isExpanded = expandedId === item.item_id;
                  const typeCode = getTypeCode(item.type_code);
                  return (
                    <div key={item.item_id} className={`task-card${isExpanded ? ' task-card--expanded' : ''}`}>
                      <div style={styles.cardTopRow}>
                        <div
                          style={styles.cardHeader}
                          onClick={() => { void handleToggleExpand(item.item_id); }}
                        >
                          <div style={styles.cardTitleRow}>
                            <span style={styles.cardTitle}>{item.title}</span>
                            <span style={isExpanded ? styles.arrowExpanded : styles.arrow}>▶</span>
                          </div>
                          <div style={styles.cardMeta}>
                            <span
                              className="status-badge"
                              style={getWorkflowStateStyle(item.current_state)}
                            >
                              {getStateLabel(item.current_state, typeCode)}
                            </span>
                            <span style={styles.metaTime}>
                              {new Date(item.updated_at).toLocaleString('zh-CN', {
                                month: '2-digit',
                                day: '2-digit',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                          </div>
                        </div>
                        <WorkflowActionToolbar
                          workflowItemId={item.item_id}
                          typeCode={typeCode}
                          defaultPriority={
                            itemDetail && 'priority' in itemDetail
                              ? String(itemDetail.priority || '')
                              : ''
                          }
                          onTransitionSuccess={handleTaskWorkflowSuccess}
                          compact
                        />
                      </div>

                      {isExpanded && (
                        <div style={styles.expandedContent}>
                          {loadingDetail ? (
                            <div style={styles.loadingSmall}>
                              <div className="loading-spinner" style={{ width: 20, height: 20 }} />
                            </div>
                          ) : (
                            <>
                              {item.content && (
                                <p style={styles.contentPreview}>{item.content}</p>
                              )}
                              {itemDetail && 'description' in itemDetail && itemDetail.description && (
                                <p style={styles.contentPreview}>{itemDetail.description}</p>
                              )}
                            </>
                          )}

                          <WorkflowPanel
                            workflowItemId={item.item_id}
                            entityLabel={item.title}
                            typeCode={typeCode}
                            defaultPriority={
                              itemDetail && 'priority' in itemDetail
                                ? String(itemDetail.priority || '')
                                : ''
                            }
                            onTransitionSuccess={handleTaskWorkflowSuccess}
                            compact
                            hideToolbar
                            refreshSignal={workflowRefreshSignal}
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

const groupBadgeStyle = (colors: { bg: string; color: string }): React.CSSProperties => ({
  display: 'inline-block',
  padding: '2px 10px',
  borderRadius: '4px',
  fontSize: '12px',
  fontWeight: 600,
  backgroundColor: colors.bg,
  color: colors.color,
});

const styles: Record<string, React.CSSProperties> = {
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  group: {
    display: 'flex',
    flexDirection: 'column',
  },
  groupHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '8px',
    padding: '0 4px',
  },
  groupCount: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
  },
  cardTopRow: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: '12px',
    padding: '12px 16px 12px 0',
  },
  cardHeader: {
    padding: '0 0 0 16px',
    cursor: 'pointer',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    flex: 1,
    minWidth: 0,
  },
  cardTitleRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardTitle: {
    fontSize: '14px',
    fontWeight: 500,
    flex: 1,
    lineHeight: '1.4',
  },
  arrow: {
    fontSize: '10px',
    color: 'var(--text-tertiary)',
    marginLeft: '8px',
  },
  arrowExpanded: {
    fontSize: '10px',
    color: 'var(--accent-primary)',
    marginLeft: '8px',
    transform: 'rotate(90deg)',
    display: 'inline-block',
  },
  cardMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  metaTime: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
  },
  expandedContent: {
    borderTop: '1px solid var(--border-color)',
    padding: '12px 16px',
  },
  loadingSmall: {
    display: 'flex',
    justifyContent: 'center',
    padding: '16px',
  },
  contentPreview: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
    marginBottom: '12px',
    lineHeight: 1.5,
  },
};

export default MyTasksPage;
