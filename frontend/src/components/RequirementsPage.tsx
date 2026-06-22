import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import { getCatalogLabs } from '../services/catalogLabsCache';
import type { RequirementResponse, TestCaseResponse } from '../types';
import CreateRequirementForm from './CreateRequirementForm';
import CreateTestCaseForm from './CreateTestCaseForm';
import TestCaseDetailModal from './TestCaseDetailModal';
import { WorkflowPanel, WorkflowActionToolbar } from './workflow';
import {
  getStateLabel,
  getWorkflowStateStyle,
  REQUIREMENT_STATUS_FILTER_OPTIONS,
} from '../constants/workflowLabels';
import PageToolbar, { StatPill } from './ui/PageToolbar';
import { AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription, AlertDialogFooter, AlertDialogAction, AlertDialogCancel } from './ui/alert-dialog';

/** 需求分类标签映射 */
const CATEGORY_LABELS: Record<string, string> = {
  FUNCTIONAL: '功能',
  PERFORMANCE: '性能',
  STABILITY: '稳定性',
  COMPATIBILITY: '兼容',
  SECURITY: '安全',
  REGRESSION: '回归',
};

/** 分类颜色 */
const CATEGORY_COLORS: Record<string, string> = {
  FUNCTIONAL: '#58a6ff',
  PERFORMANCE: '#ff7b72',
  STABILITY: '#79c0ff',
  COMPATIBILITY: '#bb8009',
  SECURITY: '#db4537',
  REGRESSION: '#a371f7',
};

const CATEGORY_FILTER_OPTIONS = [
  { value: '', label: '全部分类' },
  { value: 'FUNCTIONAL', label: '功能测试' },
  { value: 'PERFORMANCE', label: '性能测试' },
  { value: 'STABILITY', label: '稳定性测试' },
  { value: 'COMPATIBILITY', label: '兼容性测试' },
  { value: 'SECURITY', label: '安全测试' },
  { value: 'REGRESSION', label: '回归测试' },
];

type ActiveTab = 'workflow' | 'testcases';

interface RequirementsPageProps {
  initialStatusFilter?: string;
}

const RequirementsPage: React.FC<RequirementsPageProps> = ({ initialStatusFilter = '' }) => {
  const [requirements, setRequirements] = useState<RequirementResponse[]>([]);
  const [testCases, setTestCases] = useState<TestCaseResponse[]>([]);
  const [loadingRequirements, setLoadingRequirements] = useState(false);
  const [loadingTestCases, setLoadingTestCases] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedRequirementId, setSelectedRequirementId] = useState<string | null>(null);
  const [showCreateRequirement, setShowCreateRequirement] = useState(false);
  const [showCreateTestCase, setShowCreateTestCase] = useState(false);
  const [selectedTestCase, setSelectedTestCase] = useState<TestCaseResponse | null>(null);
  const [editingTestCase, setEditingTestCase] = useState<TestCaseResponse | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>('workflow');
  const [statusFilter, setStatusFilter] = useState(initialStatusFilter);
  const [categoryFilter, setCategoryFilter] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<{ open: boolean; reqId?: string; title?: string }>({ open: false });
  const [deleting, setDeleting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchDeleteConfirm, setBatchDeleteConfirm] = useState(false);
  const [deleteCaseConfirm, setDeleteCaseConfirm] = useState<{ open: boolean; caseId?: string; title?: string }>({ open: false });
  const [workflowTestCase, setWorkflowTestCase] = useState<TestCaseResponse | null>(null);
  const [defaultCatalogLabId, setDefaultCatalogLabId] = useState('');
  const [requirementWorkflowSignal, setRequirementWorkflowSignal] = useState(0);
  const [caseWorkflowSignal, setCaseWorkflowSignal] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const labs = await getCatalogLabs({ active_only: true });
        const first = labs[0]?.lab_id;
        if (!cancelled && first) {
          setDefaultCatalogLabId(first);
        }
      } catch {
        /* non-blocking */
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const selectedRequirement = useMemo(
    () => requirements.find((item) => item.req_id === selectedRequirementId) || null,
    [requirements, selectedRequirementId],
  );

  const fetchRequirements = useCallback(async (nextSelectedId?: string, status?: string) => {
    setLoadingRequirements(true);
    setError(null);

    try {
      const params: { limit: number; status?: string } = { limit: 50 };
      const effectiveStatus = status ?? statusFilter;
      if (effectiveStatus) {
        params.status = effectiveStatus;
      }
      const response = await api.listRequirements(params);
      const data = response.data || [];
      setRequirements(data);

      setSelectedRequirementId((current) => {
        const preferred = nextSelectedId || current;
        if (preferred && data.some((item) => item.req_id === preferred)) {
          return preferred;
        }
        return data[0]?.req_id || null;
      });
    } catch (err) {
      setError('获取需求列表失败');
      console.error('Fetch requirements error:', err);
    } finally {
      setLoadingRequirements(false);
    }
  }, [statusFilter]);

  const fetchTestCases = useCallback(async (requirementId: string) => {
    setLoadingTestCases(true);
    setError(null);

    try {
      const response = await api.listTestCases({ ref_req_id: requirementId, limit: 50 });
      setTestCases(response.data || []);
    } catch (err) {
      setError('获取测试用例失败');
      console.error('Fetch test cases error:', err);
    } finally {
      setLoadingTestCases(false);
    }
  }, []);

  useEffect(() => {
    fetchRequirements();
  }, [fetchRequirements]);

  useEffect(() => {
    if (!selectedRequirementId) {
      setTestCases([]);
      setWorkflowTestCase(null);
      return;
    }
    fetchTestCases(selectedRequirementId);
    setWorkflowTestCase(null);
  }, [fetchTestCases, selectedRequirementId]);

  const handleRequirementCreated = (requirement: RequirementResponse) => {
    fetchRequirements(requirement.req_id);
  };

  const handleTestCaseCreated = () => {
    if (selectedRequirementId) {
      fetchTestCases(selectedRequirementId);
    }
  };

  const selectTestCaseForWorkflow = useCallback(async (testCase: TestCaseResponse) => {
    setWorkflowTestCase(testCase);
    if (testCase.workflow_item_id) {
      return;
    }
    try {
      const response = await api.getTestCase(testCase.case_id);
      if (response.data?.workflow_item_id) {
        setWorkflowTestCase(response.data);
      }
    } catch (err) {
      console.error('Fetch test case detail for workflow error:', err);
    }
  }, []);

  const getPriorityStyle = (priority: string) => {
    const styleMap: Record<string, { bg: string; color: string }> = {
      P0: { bg: 'var(--status-error-bg)', color: 'var(--status-error)' },
      P1: { bg: 'var(--status-warning-bg)', color: 'var(--status-warning)' },
      P2: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
      P3: { bg: 'var(--surface-tertiary)', color: 'var(--text-tertiary)' },
    };
    return styleMap[priority] || { bg: 'var(--surface-tertiary)', color: 'var(--text-secondary)' };
  };

  const refreshRequirementData = async () => {
    if (!selectedRequirement?.req_id) return;
    await fetchRequirements(selectedRequirement.req_id);
  };

  const handleRequirementWorkflowSuccess = async () => {
    await refreshRequirementData();
    setRequirementWorkflowSignal((n) => n + 1);
  };

  const refreshTestCaseData = async () => {
    if (!selectedRequirementId) return;
    await fetchTestCases(selectedRequirementId);
    if (workflowTestCase?.case_id) {
      try {
        const response = await api.getTestCase(workflowTestCase.case_id);
        if (response.data) setWorkflowTestCase(response.data);
      } catch {
        // ignore
      }
    }
  };

  const handleCaseWorkflowSuccess = async () => {
    await refreshTestCaseData();
    setCaseWorkflowSignal((n) => n + 1);
  };

  const onlineCount = requirements.filter(r => r.status === 'RELEASED').length;

  const handleDeleteRequirement = async () => {
    if (!deleteConfirm.reqId || !selectedRequirement?.workflow_item_id) return;

    setDeleting(true);
    setError(null);
    try {
      await api.deleteRequirement(deleteConfirm.reqId);
      setDeleteConfirm({ open: false });
      // 重新获取列表
      await fetchRequirements();
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除需求失败');
      console.error('Delete requirement error:', err);
    } finally {
      setDeleting(false);
    }
  };

  const openDeleteConfirm = (reqId: string, title: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteConfirm({ open: true, reqId, title });
  };

  // 批量选择
  const toggleSelect = (reqId: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(reqId)) {
        next.delete(reqId);
      } else {
        next.add(reqId);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === requirements.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(requirements.map(r => r.req_id)));
    }
  };

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;

    setDeleting(true);
    setError(null);
    try {
      // 逐个删除
      const deletePromises = Array.from(selectedIds).map(id => api.deleteRequirement(id));
      await Promise.all(deletePromises);
      setBatchDeleteConfirm(false);
      setSelectedIds(new Set());
      await fetchRequirements();
    } catch (err) {
      setError(err instanceof Error ? err.message : '批量删除失败');
      console.error('Batch delete error:', err);
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteTestCase = async () => {
    if (!deleteCaseConfirm.caseId || !selectedRequirementId) return;

    setDeleting(true);
    setError(null);
    try {
      await api.deleteTestCase(deleteCaseConfirm.caseId);
      setDeleteCaseConfirm({ open: false });
      await fetchTestCases(selectedRequirementId);
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除测试用例失败');
      console.error('Delete test case error:', err);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className={`split-workspace${selectedRequirement ? ' split-workspace--has-selection' : ''}`}>
      <aside className="split-workspace__list">
        <div className="split-panel-toolbar">
          <PageToolbar
            meta={(
              <>
                <StatPill label="全部" value={requirements.length} />
                <StatPill label="已发布" value={onlineCount} tone="success" />
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
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  onClick={() => fetchRequirements()}
                  disabled={loadingRequirements}
                >
                  刷新
                </button>
                <button type="button" className="btn btn--primary btn--sm" onClick={() => setShowCreateRequirement(true)}>
                  + 新建
                </button>
              </>
            )}
          />
        </div>

        <div className="filter-strip">
          <select
            className="form-input form-select"
            value={statusFilter}
            aria-label="按状态筛选需求"
            onChange={(e) => {
              const next = e.target.value;
              setStatusFilter(next);
              fetchRequirements(undefined, next);
            }}
          >
            {REQUIREMENT_STATUS_FILTER_OPTIONS.map((opt) => (
              <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <select
            className="form-input form-select"
            value={categoryFilter}
            aria-label="按分类筛选需求"
            onChange={(e) => {
              setCategoryFilter(e.target.value);
            }}
          >
            {CATEGORY_FILTER_OPTIONS.map((opt) => (
              <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {loadingRequirements ? (
          <div className="loading-overlay">
            <div className="loading-spinner" />
          </div>
        ) : requirements.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state__icon">📋</div>
            <p className="empty-state__text">暂无需求，点击上方"新建"创建</p>
          </div>
        ) : (
          <div className="split-list-scroll">
            {/* Select All Header */}
            <div style={styles.selectAllRow}>
              <label style={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={selectedIds.size === requirements.length && requirements.length > 0}
                  onChange={toggleSelectAll}
                  style={styles.checkbox}
                />
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>全选</span>
              </label>
            </div>
            {requirements.map((requirement) => {
              const priorityStyle = getPriorityStyle(requirement.priority);
              const isSelected = selectedRequirementId === requirement.req_id;
              const isChecked = selectedIds.has(requirement.req_id);
              const categoryColor = requirement.category ? CATEGORY_COLORS[requirement.category] : undefined;
              const categoryText = requirement.category ? (CATEGORY_LABELS[requirement.category] || requirement.category) : null;
              const ownerName = requirement.tpm_owner_name || requirement.tpm_owner_id;
              return (
                <div
                  key={requirement.req_id}
                  className={`requirement-item ${isSelected ? 'requirement-item--selected' : ''} ${isChecked ? 'requirement-item--checked' : ''}`}
                  onClick={() => {
                    setSelectedRequirementId(requirement.req_id);
                  }}
                >
                  <div style={styles.itemHeader}>
                    <div style={styles.itemHeaderLeft}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleSelect(requirement.req_id)}
                        onClick={(e) => e.stopPropagation()}
                        style={styles.checkbox}
                      />
                      <span style={styles.itemId}>{requirement.req_id}</span>
                      {categoryText && categoryColor && (
                        <span style={{
                          fontSize: '10px',
                          padding: '1px 6px',
                          borderRadius: '8px',
                          color: categoryColor,
                          backgroundColor: `${categoryColor}22`,
                          fontWeight: 500,
                        }}>
                          {categoryText}
                        </span>
                      )}
                    </div>
                    <div style={styles.itemHeaderRight}>
                      <span
                        className="status-badge"
                        style={{ backgroundColor: priorityStyle.bg, color: priorityStyle.color }}
                      >
                        {requirement.priority}
                      </span>
                      <button
                        style={styles.deleteBtn}
                        onClick={(e) => openDeleteConfirm(requirement.req_id, requirement.title, e)}
                        title="删除"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                  <div style={styles.itemTitle}>{requirement.title}</div>
                  <div style={styles.itemMeta}>
                    <div style={styles.itemMetaLeft}>
                      <span
                        className="status-badge status-badge--neutral"
                        style={{ fontSize: '10px' }}
                      >
                        {getStateLabel(requirement.status, 'REQUIREMENT')}
                      </span>
                      {ownerName && (
                        <span style={styles.metaOwner}>{ownerName}</span>
                      )}
                      {requirement.case_count > 0 && (
                        <span style={styles.metaCaseCount}>{requirement.case_count} 用例</span>
                      )}
                      <span style={styles.metaTime}>
                        {new Date(requirement.created_at).toLocaleDateString('zh-CN')}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </aside>

      <main className="split-workspace__main">
        {selectedRequirement ? (
          <>
            <div style={styles.detailHeader}>
              <button
                type="button"
                className="split-workspace__back"
                onClick={() => setSelectedRequirementId(null)}
              >
                ← 返回列表
              </button>
              <div style={styles.detailHeaderRow}>
                <div style={styles.detailHeaderMain}>
                  <h2 style={styles.detailTitle}>{selectedRequirement.title}</h2>
                  <div style={styles.detailMeta}>
                    <span className="mono" style={styles.detailId}>{selectedRequirement.req_id}</span>
                    <span
                      className="status-badge"
                      style={getWorkflowStateStyle(selectedRequirement.status)}
                    >
                      {getStateLabel(selectedRequirement.status, 'REQUIREMENT')}
                    </span>
                    <span
                      className="status-badge"
                      style={getPriorityStyle(selectedRequirement.priority)}
                    >
                      {selectedRequirement.priority}
                    </span>
                  </div>
                  {selectedRequirement.description && (
                    <p style={styles.description}>{selectedRequirement.description}</p>
                  )}
                </div>
                {selectedRequirement.workflow_item_id && (
                  <WorkflowActionToolbar
                    workflowItemId={selectedRequirement.workflow_item_id}
                    typeCode="REQUIREMENT"
                    defaultPriority={selectedRequirement.priority}
                    onTransitionSuccess={handleRequirementWorkflowSuccess}
                    showStateBadge
                  />
                )}
              </div>
            </div>

            {/* Tabs */}
            <div className="tabs">
              <button
                className={`tab ${activeTab === 'workflow' ? 'tab--active' : ''}`}
                onClick={() => setActiveTab('workflow')}
              >
                工作流
              </button>
              <button
                className={`tab ${activeTab === 'testcases' ? 'tab--active' : ''}`}
                onClick={() => setActiveTab('testcases')}
              >
                测试用例 ({testCases.length})
              </button>
            </div>

            {/* Tab Content */}
            <div style={styles.tabContent}>
              {activeTab === 'workflow' ? (
                <div className="data-panel">
                  <div className="data-panel-header">
                    <h3 className="data-panel-title">需求工作流</h3>
                  </div>
                  <WorkflowPanel
                    workflowItemId={selectedRequirement.workflow_item_id}
                    entityLabel={`需求 ${selectedRequirement.req_id}`}
                    typeCode="REQUIREMENT"
                    defaultPriority={selectedRequirement.priority}
                    creatorName={selectedRequirement.creator_name || selectedRequirement.creator}
                    currentOwnerName={selectedRequirement.current_owner_name || selectedRequirement.current_owner}
                    createdAt={selectedRequirement.created_at}
                    updatedAt={selectedRequirement.updated_at}
                    onTransitionSuccess={handleRequirementWorkflowSuccess}
                    hideToolbar
                    refreshSignal={requirementWorkflowSignal}
                  />
                </div>
              ) : (
                <div className="data-panel">
                  <div className="data-panel-header">
                    <h3 className="data-panel-title">关联测试用例</h3>
                    <button
                      className="btn btn--primary btn--sm"
                      onClick={() => setShowCreateTestCase(true)}
                    >
                      + 创建用例
                    </button>
                  </div>

                  {loadingTestCases ? (
                    <div className="loading-overlay">
                      <div className="loading-spinner" />
                    </div>
                  ) : testCases.length === 0 ? (
                    <div className="empty-state">
                      <div className="empty-state__icon">🧪</div>
                      <p className="empty-state__text">暂无测试用例，点击上方按钮创建</p>
                    </div>
                  ) : (
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th style={{ width: '120px' }}>用例ID</th>
                          <th>名称</th>
                          <th>目录</th>
                          <th style={{ width: '60px' }}>优先级</th>
                          <th style={{ width: '80px' }}>状态</th>
                          <th style={{ width: '90px' }}>创建时间</th>
                          <th style={{ width: '120px' }}>操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        {testCases.map((testCase) => {
                          const isSelected = workflowTestCase?.case_id === testCase.case_id;
                          return (
                          <tr
                            key={testCase.id}
                            onClick={() => { void selectTestCaseForWorkflow(testCase); }}
                            style={{
                              cursor: 'pointer',
                              backgroundColor: isSelected ? 'var(--surface-hover)' : undefined,
                            }}
                          >
                            <td className="mono">{testCase.case_id}</td>
                            <td>{testCase.title}</td>
                            <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                              {testCase.catalog_breadcrumb || testCase.catalog_path?.join(' / ') || '-'}
                            </td>
                            <td>
                              <span
                                className="status-badge status-badge--neutral"
                                style={getPriorityStyle(testCase.priority || 'P3')}
                              >
                                {testCase.priority || '-'}
                              </span>
                            </td>
                            <td>
                              <span
                                className="status-badge status-badge--neutral"
                                style={getWorkflowStateStyle(testCase.status)}
                              >
                                {getStateLabel(testCase.status, 'TEST_CASE')}
                              </span>
                            </td>
                            <td className="mono">
                              {new Date(testCase.created_at).toLocaleDateString('zh-CN')}
                            </td>
                            <td>
                              <div style={styles.caseActionCell} onClick={(e) => e.stopPropagation()}>
                                <button
                                  type="button"
                                  style={styles.caseActionBtn}
                                  onClick={() => setSelectedTestCase(testCase)}
                                  title="详情"
                                >
                                  详情
                                </button>
                                <button
                                  type="button"
                                  style={styles.deleteBtn}
                                  onClick={() => {
                                    setDeleteCaseConfirm({ open: true, caseId: testCase.case_id, title: testCase.title });
                                  }}
                                  title="删除"
                                >
                                  ×
                                </button>
                              </div>
                            </td>
                          </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  )}

                  {workflowTestCase && (
                    <div style={styles.caseWorkflowPanel}>
                      <div style={styles.caseWorkflowHeader}>
                        <h4 style={styles.caseWorkflowTitle}>
                          用例工作流 · {workflowTestCase.case_id}
                        </h4>
                        <WorkflowActionToolbar
                          workflowItemId={workflowTestCase.workflow_item_id}
                          typeCode="TEST_CASE"
                          defaultPriority={workflowTestCase.priority}
                          onTransitionSuccess={handleCaseWorkflowSuccess}
                          compact
                          showStateBadge
                        />
                      </div>
                      <WorkflowPanel
                        key={workflowTestCase.workflow_item_id || workflowTestCase.case_id}
                        workflowItemId={workflowTestCase.workflow_item_id}
                        entityLabel={`用例 ${workflowTestCase.case_id} · ${workflowTestCase.title}`}
                        typeCode="TEST_CASE"
                        defaultPriority={workflowTestCase.priority}
                        creatorName={workflowTestCase.owner_id}
                        currentOwnerName={workflowTestCase.owner_id}
                        createdAt={workflowTestCase.created_at}
                        updatedAt={workflowTestCase.updated_at}
                        onTransitionSuccess={handleCaseWorkflowSuccess}
                        compact
                        hideToolbar
                        refreshSignal={caseWorkflowSignal}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="empty-state" style={{ height: '100%' }}>
            <div className="empty-state__icon">👈</div>
            <p className="empty-state__text">从左侧选择一条需求查看详情</p>
          </div>
        )}
      </main>

      {error && (
        <div style={styles.errorToast}>
          <span>⚠</span> {error}
          <button onClick={() => setError(null)} style={styles.errorClose}>×</button>
        </div>
      )}

      {showCreateRequirement && (
        <CreateRequirementForm
          onClose={() => setShowCreateRequirement(false)}
          onSuccess={handleRequirementCreated}
        />
      )}

      {showCreateTestCase && selectedRequirement && (
        <CreateTestCaseForm
          onClose={() => setShowCreateTestCase(false)}
          onSuccess={handleTestCaseCreated}
          defaultRequirementId={selectedRequirement.req_id}
          lockRequirementId
          defaultLabId={defaultCatalogLabId}
          defaultCatalogPrefix={[]}
        />
      )}

      {selectedTestCase && (
        <TestCaseDetailModal
          testCase={selectedTestCase}
          onClose={() => setSelectedTestCase(null)}
          onEdit={() => {
            setEditingTestCase(selectedTestCase);
            setSelectedTestCase(null);
          }}
        />
      )}

      {editingTestCase && (
        <CreateTestCaseForm
          editTestCase={editingTestCase}
          onClose={() => setEditingTestCase(null)}
          onSuccess={handleTestCaseCreated}
          lockRequirementId
        />
      )}

      {/* Delete Confirm Modal */}
      <AlertDialog open={deleteConfirm.open} onOpenChange={(o) => { if (!o) setDeleteConfirm({ open: false }); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除需求 <strong>"{deleteConfirm.title}"</strong> 吗？
              <p style={{ color: 'var(--status-error)', fontSize: '13px', marginTop: '8px' }}>
                此操作不可恢复，相关测试用例也将一并删除。
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeleteConfirm({ open: false })}>取消</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteRequirement} disabled={deleting}>
              {deleting ? '删除中...' : '删除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Batch Delete Confirm Modal */}
      <AlertDialog open={batchDeleteConfirm} onOpenChange={(o) => { if (!o) setBatchDeleteConfirm(false); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认批量删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除选中的 <strong>{selectedIds.size}</strong> 个需求吗？
              <p style={{ color: 'var(--status-error)', fontSize: '13px', marginTop: '8px' }}>
                此操作不可恢复，相关测试用例也将一并删除。
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setBatchDeleteConfirm(false)}>取消</AlertDialogCancel>
            <AlertDialogAction onClick={handleBatchDelete} disabled={deleting}>
              {deleting ? '删除中...' : `删除 ${selectedIds.size} 项`}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Test Case Confirm Modal */}
      <AlertDialog open={deleteCaseConfirm.open} onOpenChange={(o) => { if (!o) setDeleteCaseConfirm({ open: false }); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除测试用例</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除测试用例 <strong>"{deleteCaseConfirm.title}"</strong> 吗？
              <p style={{ color: 'var(--status-error)', fontSize: '13px', marginTop: '8px' }}>
                此操作不可恢复。
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeleteCaseConfirm({ open: false })}>取消</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteTestCase} disabled={deleting}>
              {deleting ? '删除中...' : '删除'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <style>{`
        .requirement-item {
          padding: 14px 16px;
          margin-bottom: 8px;
          background-color: var(--surface-primary);
          border: 1px solid var(--border-subtle);
          border-radius: var(--radius-md);
          cursor: pointer;
          transition: all var(--transition-fast);
        }
        .requirement-item:hover {
          border-color: var(--border-default);
          background-color: var(--surface-hover);
        }
        .requirement-item--selected {
          border-color: var(--accent-primary);
          background-color: rgba(37, 99, 235, 0.04);
        }
        .requirement-item--checked {
          background-color: rgba(37, 99, 235, 0.08);
        }
        .requirement-item button:hover {
          color: var(--status-error);
          background-color: var(--status-error-bg);
        }
      `}</style>
    </div>
  );
};

const styles = {
  selectAllRow: {
    display: 'flex',
    alignItems: 'center',
    padding: '8px 4px',
    marginBottom: '8px',
    borderBottom: '1px solid var(--border-subtle)',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    cursor: 'pointer',
  },
  checkbox: {
    width: '16px',
    height: '16px',
    cursor: 'pointer',
    accentColor: 'var(--accent-primary)',
  },
  itemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  itemHeaderLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  itemHeaderRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  itemId: {
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-primary)',
  },
  itemTitle: {
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--text-primary)',
    marginBottom: '8px',
    lineHeight: 1.4,
  },
  itemMeta: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '8px',
  },
  itemMetaLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    minWidth: 0,
  },
  metaTime: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
  },
  metaOwner: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
  },
  metaCaseCount: {
    fontSize: '10px',
    color: 'var(--accent-cyan)',
    backgroundColor: 'rgba(121, 192, 255, 0.12)',
    padding: '1px 6px',
    borderRadius: '8px',
  },
  detailHeader: {
    padding: '20px 24px',
    backgroundColor: 'var(--surface-primary)',
    borderBottom: '1px solid var(--border-subtle)',
  },
  detailHeaderRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '16px',
    flexWrap: 'wrap' as const,
  },
  detailHeaderMain: {
    flex: 1,
    minWidth: 0,
  },
  detailTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    margin: '0 0 12px 0',
  },
  detailMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  detailId: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
  },
  description: {
    marginTop: '12px',
    fontSize: '13px',
    color: 'var(--text-secondary)',
    lineHeight: 1.6,
    whiteSpace: 'pre-wrap' as const,
  },
  tabContent: {
    flex: 1,
    overflow: 'auto',
    padding: '24px',
  },
  workflowInfo: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '16px',
    marginBottom: '24px',
  },
  workflowInfoItem: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '6px',
  },
  workflowInfoLabel: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    fontWeight: 500,
  },
  workflowInfoValue: {
    fontSize: '13px',
    color: 'var(--text-primary)',
  },
  workflowActions: {
    paddingTop: '16px',
    borderTop: '1px solid var(--border-subtle)',
  },
  sectionTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    marginBottom: '12px',
  },
  actionGrid: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '10px',
  },
  actionName: {
    fontWeight: 600,
    color: 'var(--accent-primary)',
  },
  actionArrow: {
    fontSize: '12px',
    color: 'var(--text-tertiary)',
    marginLeft: '8px',
  },
  caseActionCell: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  caseActionBtn: {
    padding: '2px 8px',
    fontSize: '12px',
    color: 'var(--accent-primary)',
    backgroundColor: 'transparent',
    border: '1px solid var(--border-default)',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  caseWorkflowPanel: {
    marginTop: '16px',
    paddingTop: '16px',
    borderTop: '1px solid var(--border-subtle)',
  },
  caseWorkflowHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '12px',
    marginBottom: '12px',
    flexWrap: 'wrap' as const,
  },
  caseWorkflowTitle: {
    margin: 0,
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
  },
  caseWorkflowHint: {
    margin: '8px 0 0',
    fontSize: '13px',
    color: 'var(--text-tertiary)',
    lineHeight: 1.6,
  },
  caseWorkflowHintSub: {
    fontSize: '12px',
    color: 'var(--text-muted)',
  },
  formLabel: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    marginBottom: '6px',
  },
  errorToast: {
    position: 'fixed' as const,
    bottom: '24px',
    right: '24px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '12px 16px',
    backgroundColor: 'var(--status-error-bg)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--status-error)',
    fontSize: '13px',
    zIndex: 1000,
  },
  errorClose: {
    padding: '0 4px',
    fontSize: '16px',
    background: 'none',
    border: 'none',
    color: 'var(--status-error)',
    cursor: 'pointer',
  },
  ownerDropdown: {
    position: 'absolute' as const,
    top: '100%',
    left: 0,
    right: 0,
    maxHeight: '200px',
    overflowY: 'auto' as const,
    backgroundColor: 'var(--surface-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
    zIndex: 100,
    marginTop: '4px',
  },
  ownerDropdownItem: {
    padding: '10px 12px',
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: '1px solid var(--border-subtle)',
  },
  ownerId: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
    fontFamily: "'JetBrains Mono', monospace",
  },
  deleteBtn: {
    width: '20px',
    height: '20px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-tertiary)',
    background: 'transparent',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
    padding: 0,
  },
};

export default RequirementsPage;