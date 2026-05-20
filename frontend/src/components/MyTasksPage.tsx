import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import type { WorkItem, WorkflowTransition } from '../types';

// 状态中文映射
const STATE_LABELS: Record<string, string> = {
  DRAFT: '草稿',
  PENDING_REVIEW: '待审核',
  PENDING_DEVELOP: '待开发',
  DEVELOPING: '开发中',
  PENDING_TEST: '待测试',
  PENDING_UAT: '待验收',
  PENDING_RELEASE: '待发布',
  RELEASED: '已发布',
  APPROVED: '已通过',
  REJECTED: '已驳回',
  CLOSED: '已关闭',
};

// 类型中文映射
const TYPE_LABELS: Record<string, string> = {
  REQUIREMENT: '需求',
  TEST_CASE: '测试用例',
};

// 类型颜色
const TYPE_COLORS: Record<string, { bg: string; color: string }> = {
  REQUIREMENT: { bg: '#e8f5e9', color: '#2e7d32' },
  TEST_CASE: { bg: '#e3f2fd', color: '#1565c0' },
};

const getStateStyle = (state: string) => {
  const styleMap: Record<string, { bg: string; color: string }> = {
    DRAFT: { bg: 'var(--surface-tertiary)', color: 'var(--text-tertiary)' },
    PENDING_REVIEW: { bg: 'var(--status-warning-bg)', color: 'var(--status-warning)' },
    PENDING_DEVELOP: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
    DEVELOPING: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
    PENDING_TEST: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
    PENDING_RELEASE: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
    RELEASED: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
    APPROVED: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
    REJECTED: { bg: 'var(--status-error-bg)', color: 'var(--status-error)' },
  };
  return styleMap[state] || { bg: 'var(--surface-tertiary)', color: 'var(--text-secondary)' };
};

const getActionLabel = (action: string) => {
  const labelMap: Record<string, string> = {
    SUBMIT: '提交评审',
    APPROVE: '通过',
    REJECT: '驳回',
    START: '开始开发',
    FINISH: '完成开发',
    PASS: '通过',
    PUBLISH: '发布',
    CLOSE: '关闭',
  };
  return labelMap[action] || action;
};

const getFieldLabel = (field: string) => {
  const labelMap: Record<string, string> = {
    target_owner_id: '目标处理人',
    priority: '优先级',
    comment: '备注',
  };
  return labelMap[field] || field;
};

interface MyTasksPageProps {
  userId: string;
}

const MyTasksPage: React.FC<MyTasksPageProps> = ({ userId }) => {
  const [items, setItems] = useState<WorkItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 展开的工作项 ID
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [transitions, setTransitions] = useState<WorkflowTransition[]>([]);
  const [loadingWorkflow, setLoadingWorkflow] = useState(false);

  // 流转弹窗
  const [transitionModal, setTransitionModal] = useState<{ open: boolean; transition?: WorkflowTransition }>({ open: false });
  const [transitionFormData, setTransitionFormData] = useState<Record<string, string>>({});
  const [transitioningAction, setTransitioningAction] = useState<string | null>(null);
  const [ownerSuggestions, setOwnerSuggestions] = useState<{ user_id: string; username: string }[]>([]);
  const [ownerSearchQuery, setOwnerSearchQuery] = useState('');
  const [showOwnerDropdown, setShowOwnerDropdown] = useState(false);

  const [itemDetail, setItemDetail] = useState<Record<string, any> | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // 获取我的任务
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

  // 获取流转信息
  const fetchTransitions = useCallback(async (itemId: string) => {
    setLoadingWorkflow(true);
    try {
      const response = await api.getWorkflowTransitions(itemId);
      setTransitions(response.data.available_transitions || []);
    } catch (err) {
      setTransitions([]);
      console.error('Fetch transitions error:', err);
    } finally {
      setLoadingWorkflow(false);
    }
  }, []);

  // 搜索用户
  const searchUsers = useCallback(async (query: string) => {
    try {
      const response = await api.listUsers(query.trim() ? { search: query, limit: 20 } : { limit: 50 });
      setOwnerSuggestions(response.data || []);
    } catch (err) {
      console.error('Search users error:', err);
    }
  }, []);

  useEffect(() => {
    fetchMyTasks();
  }, [fetchMyTasks]);

  // 展开/收起
  const handleToggleExpand = async (itemId: string) => {
    if (expandedId === itemId) {
      setExpandedId(null);
      setTransitions([]);
      setItemDetail(null);
    } else {
      setExpandedId(itemId);
      setItemDetail(null);
      fetchTransitions(itemId);

      // 获取详情
      const item = items.find(i => i.item_id === itemId);
      if (!item) return;
      setLoadingDetail(true);
      try {
        if (item.type_code === 'REQUIREMENT' && item.req_id) {
          const res = await api.getRequirement(item.req_id);
          setItemDetail(res.data);
        } else {
          // 非 REQUIREMENT 类型，直接用 work item 的 content
          setItemDetail({ content: item.content, type_code: item.type_code });
        }
      } catch (err) {
        console.error('Fetch item detail error:', err);
        setItemDetail({ content: item.content });
      } finally {
        setLoadingDetail(false);
      }
    }
  };

  // 打开流转弹窗
  const openTransitionModal = (transition: WorkflowTransition) => {
    const initialData: Record<string, string> = {};
    for (const field of transition.required_fields) {
      if (field === 'target_owner_id') {
        searchUsers('');
      }
    }
    setOwnerSearchQuery('');
    setTransitionFormData(initialData);
    setTransitionModal({ open: true, transition });
  };

  const handleSelectOwner = (user: { user_id: string; username: string }) => {
    setTransitionFormData(prev => ({ ...prev, target_owner_id: user.user_id }));
    setOwnerSearchQuery(user.username);
    setShowOwnerDropdown(false);
  };

  // 执行流转
  const handleTransitionSubmit = async () => {
    if (!expandedId || !transitionModal.transition) return;

    for (const field of transitionModal.transition.required_fields) {
      if (!transitionFormData[field]?.trim()) {
        setError(`${getFieldLabel(field)}不能为空`);
        return;
      }
    }

    setTransitioningAction(transitionModal.transition.action);
    setError(null);
    try {
      await api.transitionWorkflow(expandedId, {
        action: transitionModal.transition.action,
        form_data: transitionFormData,
      });
      setTransitionModal({ open: false });
      await fetchMyTasks();
      await fetchTransitions(expandedId);
    } catch (err) {
      setError('工作流流转失败');
      console.error('Transition error:', err);
    } finally {
      setTransitioningAction(null);
    }
  };

  // 按类型分组
  const groupedItems = items.reduce<Record<string, WorkItem[]>>((acc, item) => {
    const type = item.type_code;
    if (!acc[type]) acc[type] = [];
    acc[type].push(item);
    return acc;
  }, {});

  // 类型排序
  const typeOrder = ['REQUIREMENT', 'TEST_CASE'];

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>我的任务</h2>
          <span style={styles.subtitle}>共 {items.length} 项待处理</span>
        </div>
        <button
          className="btn btn--ghost btn--sm"
          onClick={fetchMyTasks}
          disabled={loading}
          style={{ fontSize: '18px', padding: '4px 12px' }}
        >
          ↻
        </button>
      </div>

      {error && (
        <div className="error-message" style={styles.error}>
          {error}
          <button style={styles.errorClose} onClick={() => setError(null)}>×</button>
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
          {typeOrder.map(type => {
            const typeItems = groupedItems[type];
            if (!typeItems?.length) return null;
            return (
              <div key={type} style={styles.group}>
                <div style={styles.groupHeader}>
                  <span style={styles.groupBadge(TYPE_COLORS[type] || { bg: '#f5f5f5', color: '#666' })}>
                    {TYPE_LABELS[type] || type}
                  </span>
                  <span style={styles.groupCount}>{typeItems.length} 项</span>
                </div>
                {typeItems.map(item => {
                  const isExpanded = expandedId === item.item_id;
                  return (
                    <div key={item.item_id} style={styles.card(isExpanded)}>
                      <div
                        style={styles.cardHeader}
                        onClick={() => handleToggleExpand(item.item_id)}
                      >
                        <div style={styles.cardTitleRow}>
                          <span style={styles.cardTitle}>{item.title}</span>
                          <span style={isExpanded ? styles.arrowExpanded : styles.arrow}>
                            ▶
                          </span>
                        </div>
                        <div style={styles.cardMeta}>
                          <span
                            className="status-badge"
                            style={getStateStyle(item.current_state)}
                          >
                            {STATE_LABELS[item.current_state] || item.current_state}
                          </span>
                          <span style={styles.metaTime}>
                            {new Date(item.created_at).toLocaleString('zh-CN', {
                              month: '2-digit',
                              day: '2-digit',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>
                      </div>

                      {isExpanded && (
                        <div style={styles.expandedContent}>
                          {/* 详情区域 */}
                          {loadingDetail ? (
                            <div style={styles.loadingSmall}>
                              <div className="loading-spinner" style={{ width: 20, height: 20 }} />
                            </div>
                          ) : itemDetail ? (
                            <div style={styles.detailSection}>
                              {item.content && (
                                <div style={styles.detailRow}>
                                  <span style={styles.detailLabel}>描述</span>
                                  <span style={styles.detailValue}>{item.content}</span>
                                </div>
                              )}
                              {itemDetail.description && (
                                <div style={styles.detailRow}>
                                  <span style={styles.detailLabel}>详细说明</span>
                                  <span style={styles.detailValue}>{itemDetail.description}</span>
                                </div>
                              )}
                              {'priority' in itemDetail && itemDetail.priority && (
                                <div style={styles.detailRow}>
                                  <span style={styles.detailLabel}>优先级</span>
                                  <span style={styles.detailValue}>{itemDetail.priority}</span>
                                </div>
                              )}
                              {'target_components' in itemDetail && itemDetail.target_components?.length > 0 && (
                                <div style={styles.detailRow}>
                                  <span style={styles.detailLabel}>目标组件</span>
                                  <span style={styles.detailValue}>{itemDetail.target_components.join(', ')}</span>
                                </div>
                              )}
                              {item.creator_id && (
                                <div style={styles.detailRow}>
                                  <span style={styles.detailLabel}>创建人</span>
                                  <span style={styles.detailValue}>{itemDetail.creator_name || item.creator_id}</span>
                                </div>
                              )}
                              {item.current_owner_id && (
                                <div style={styles.detailRow}>
                                  <span style={styles.detailLabel}>当前负责人</span>
                                  <span style={styles.detailValue}>{itemDetail.current_owner_name || item.current_owner_id}</span>
                                </div>
                              )}
                              <div style={styles.detailRow}>
                                <span style={styles.detailLabel}>创建时间</span>
                                <span style={styles.detailValue}>{new Date(item.created_at).toLocaleString('zh-CN')}</span>
                              </div>
                              <div style={styles.detailRow}>
                                <span style={styles.detailLabel}>更新时间</span>
                                <span style={styles.detailValue}>{new Date(item.updated_at).toLocaleString('zh-CN')}</span>
                              </div>
                            </div>
                          ) : null}

                          {/* 分隔线 */}
                          {itemDetail && transitions.length > 0 && <div style={styles.detailDivider} />}

                          {/* 流转按钮 */}
                          {loadingWorkflow ? (
                            <div style={styles.loadingSmall}>
                              <div className="loading-spinner" style={{ width: 20, height: 20 }} />
                            </div>
                          ) : transitions.length === 0 ? (
                            <div style={styles.noTransitions}>当前状态无可用操作</div>
                          ) : (
                            <div style={styles.transitionList}>
                              {transitions.map(t => (
                                <button
                                  key={t.action}
                                  className="btn btn--sm"
                                  style={styles.actionBtn(t.action)}
                                  onClick={() => openTransitionModal(t)}
                                >
                                  {getActionLabel(t.action)}
                                </button>
                              ))}
                            </div>
                          )}
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

      {/* 流转弹窗 */}
      {transitionModal.open && transitionModal.transition && (
        <div style={styles.modalOverlay} onClick={() => setTransitionModal({ open: false })}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3>{getActionLabel(transitionModal.transition.action)}</h3>
              <button style={styles.modalClose} onClick={() => setTransitionModal({ open: false })}>×</button>
            </div>
            <div style={styles.modalBody}>
              {transitionModal.transition.required_fields.map(field => (
                <div key={field} style={styles.formGroup}>
                  <label style={styles.formLabel}>{getFieldLabel(field)}</label>
                  {field === 'target_owner_id' ? (
                    <div style={{ position: 'relative' }}>
                      <input
                        className="input"
                        style={styles.formInput}
                        placeholder="搜索用户..."
                        value={ownerSearchQuery}
                        onChange={e => {
                          setOwnerSearchQuery(e.target.value);
                          searchUsers(e.target.value);
                          setShowOwnerDropdown(true);
                        }}
                        onFocus={() => {
                          setShowOwnerDropdown(true);
                          if (!ownerSearchQuery) searchUsers('');
                        }}
                      />
                      {showOwnerDropdown && ownerSuggestions.length > 0 && (
                        <div style={styles.dropdown}>
                          {ownerSuggestions.map(user => (
                            <div
                              key={user.user_id}
                              style={styles.dropdownItem}
                              onClick={() => handleSelectOwner(user)}
                            >
                              <span>{user.username}</span>
                              <span style={{ color: 'var(--text-tertiary)', fontSize: '11px' }}>
                                {user.user_id}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <input
                      className="input"
                      style={styles.formInput}
                      value={transitionFormData[field] || ''}
                      onChange={e => setTransitionFormData(prev => ({ ...prev, [field]: e.target.value }))}
                      placeholder={getFieldLabel(field)}
                    />
                  )}
                </div>
              ))}
            </div>
            <div style={styles.modalFooter}>
              <button className="btn btn--ghost" onClick={() => setTransitionModal({ open: false })}>
                取消
              </button>
              <button
                className="btn btn--primary"
                onClick={handleTransitionSubmit}
                disabled={!!transitioningAction}
              >
                {transitioningAction ? '处理中...' : '确认'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, any> = {
  container: {
    padding: '24px',
    height: '100%',
    overflow: 'auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 600,
  },
  subtitle: {
    fontSize: '13px',
    color: 'var(--text-tertiary)',
    marginTop: '4px',
    display: 'block',
  },
  error: {
    padding: '8px 16px',
    backgroundColor: 'var(--status-error-bg)',
    color: 'var(--status-error)',
    borderRadius: '8px',
    fontSize: '13px',
    marginBottom: '12px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  errorClose: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: '16px',
    color: 'var(--status-error)',
    padding: '0 4px',
  },
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
  groupBadge: (colors: { bg: string; color: string }) => ({
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: 600,
    backgroundColor: colors.bg,
    color: colors.color,
  }),
  groupCount: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
  },
  card: (isExpanded: boolean) => ({
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: '8px',
    marginBottom: '6px',
    overflow: 'hidden',
    transition: 'border-color 0.2s',
    ...(isExpanded ? { borderColor: 'var(--accent-color)' } : {}),
  }),
  cardHeader: {
    padding: '12px 16px',
    cursor: 'pointer',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
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
    transition: 'transform 0.2s',
  },
  arrowExpanded: {
    fontSize: '10px',
    color: 'var(--accent-color)',
    marginLeft: '8px',
    transform: 'rotate(90deg)',
    transition: 'transform 0.2s',
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
  detailSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    marginBottom: '4px',
  },
  detailRow: {
    display: 'flex',
    gap: '8px',
    fontSize: '13px',
    lineHeight: '1.5',
  },
  detailLabel: {
    color: 'var(--text-tertiary)',
    minWidth: '70px',
    flexShrink: 0,
  },
  detailValue: {
    color: 'var(--text-primary)',
    flex: 1,
    wordBreak: 'break-word',
  },
  detailDivider: {
    height: '1px',
    backgroundColor: 'var(--border-color)',
    margin: '12px 0',
  },
  noTransitions: {
    textAlign: 'center',
    padding: '16px',
    color: 'var(--text-tertiary)',
    fontSize: '13px',
  },
  transitionList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
  },
  actionBtn: (action: string) => {
    const colorMap: Record<string, { bg: string; color: string; border: string }> = {
      SUBMIT:    { bg: '#e3f2fd', color: '#1565c0', border: '#bbdefb' },
      START:     { bg: '#e3f2fd', color: '#1565c0', border: '#bbdefb' },
      APPROVE:   { bg: '#e8f5e9', color: '#2e7d32', border: '#c8e6c9' },
      PASS:      { bg: '#e8f5e9', color: '#2e7d32', border: '#c8e6c9' },
      FINISH:    { bg: '#e8f5e9', color: '#2e7d32', border: '#c8e6c9' },
      PUBLISH:   { bg: '#e0f2f1', color: '#00796b', border: '#b2dfdb' },
      REJECT:    { bg: '#ffebee', color: '#c62828', border: '#ffcdd2' },
      CLOSE:     { bg: '#f5f5f5', color: '#616161', border: '#e0e0e0' },
    };
    const colors = colorMap[action] || { bg: '#fafafa', color: '#757575', border: '#e0e0e0' };
    return {
      padding: '6px 14px',
      fontSize: '13px',
      borderRadius: '6px',
      border: `1px solid ${colors.border}`,
      cursor: 'pointer',
      backgroundColor: colors.bg,
      color: colors.color,
      fontWeight: 500,
      transition: 'all 0.15s',
    };
  },
  // Modal
  modalOverlay: {
    position: 'fixed' as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.4)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  modal: {
    backgroundColor: 'var(--surface-primary)',
    borderRadius: '12px',
    width: '420px',
    maxWidth: '90vw',
    boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: '1px solid var(--border-color)',
  },
  modalClose: {
    background: 'none',
    border: 'none',
    fontSize: '22px',
    cursor: 'pointer',
    color: 'var(--text-tertiary)',
    padding: '0 4px',
  },
  modalBody: {
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  formLabel: {
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
  },
  formInput: {
    width: '100%',
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid var(--border-color)',
    fontSize: '13px',
  },
  dropdown: {
    position: 'absolute' as const,
    top: '100%',
    left: 0,
    right: 0,
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: '6px',
    marginTop: '2px',
    maxHeight: '200px',
    overflow: 'auto',
    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
    zIndex: 10,
  },
  dropdownItem: {
    padding: '8px 12px',
    cursor: 'pointer',
    fontSize: '13px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '8px',
    padding: '16px 20px',
    borderTop: '1px solid var(--border-color)',
  },
};

export default MyTasksPage;
