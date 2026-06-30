import React, { useCallback, useEffect, useMemo, useState } from 'react';
import type { TestCaseResponse, UserResponse, ExecutionStatsResponse } from '../types';
import { WorkflowPanel, WorkflowActionToolbar, WorkflowOverflowMenu } from './workflow';
import { useWorkflow } from '../hooks/useWorkflow';
import WorkflowCurrentStateBadge from './workflow/WorkflowCurrentStateBadge';
import { PRIORITY_COLORS } from '../constants/testCaseLabels';
import { catalogStyles } from './catalog/catalogStyles';
import { SWITCHABLE_USERS } from '../config/users';
import { api } from '../services/api';
import TestCaseHistoryPanel from './TestCaseHistoryPanel';
import { Dialog, DialogContent } from './ui/dialog';
const CONFIDENTIALITY_LABELS: Record<string, string> = {
  PUBLIC: '公开',
  INTERNAL: '内部',
  CONFIDENTIAL: '机密',
  RESTRICTED: '受限',
};

const VISIBILITY_LABELS: Record<string, string> = {
  PUBLIC: '全网可见',
  TEAM: '团队可见',
  PRIVATE: '仅自己可见',
};

import TestCaseStepList from './TestCaseStepList';
import TestCaseCommentPanel from './TestCaseCommentPanel';

interface TestCaseDetailModalProps {
  testCase: TestCaseResponse;
  onClose: () => void;
  onEdit?: () => void;
  /** 递增时刷新变更记录（如编辑保存后） */
  changeLogRefreshSignal?: number;
}

type DetailTab = 'steps' | 'workflow' | 'more' | 'comments' | 'stats';

const DETAIL_TABS: { id: DetailTab; label: string; badge?: number }[] = [
  { id: 'steps', label: '步骤' },
  { id: 'workflow', label: '工作流' },
  { id: 'more', label: '更多' },
  { id: 'stats', label: '执行统计' },
  { id: 'comments', label: '评论' },
];

const NON_EDITABLE_STATES = new Set(['PENDING_REVIEW', 'DONE']);

function hasDisplayValue(value: unknown): boolean {
  if (value === undefined || value === null || value === '') return false;
  if (Array.isArray(value) && value.length === 0) return false;
  if (typeof value === 'object' && !Array.isArray(value) && Object.keys(value as object).length === 0) {
    return false;
  }
  return true;
}

function buildUserNameMap(users: UserResponse[]): Map<string, string> {
  const map = new Map<string, string>();
  for (const u of SWITCHABLE_USERS) {
    map.set(u.userId, u.label);
  }
  for (const u of users) {
    map.set(u.user_id, u.username);
  }
  return map;
}

function resolveUserName(map: Map<string, string>, userId?: string | null): string | null {
  if (!userId) return null;
  return map.get(userId) || userId;
}

function formatFileSize(bytes: unknown): string {
  const n = typeof bytes === 'number' ? bytes : Number(bytes);
  if (!Number.isFinite(n) || n <= 0) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

const TestCaseDetailModal: React.FC<TestCaseDetailModalProps> = ({
  testCase,
  onClose,
  onEdit,
  changeLogRefreshSignal = 0,
}) => {
  const showEdit = Boolean(onEdit) && !NON_EDITABLE_STATES.has(testCase.status);
  const labLabel = testCase.lab_name || testCase.lab_id || '';
  const catalogPathParts = testCase.catalog_path?.length ? testCase.catalog_path : [];
  const [activeTab, setActiveTab] = useState<DetailTab>('steps');
  const [workflowRefreshSignal, setWorkflowRefreshSignal] = useState(0);
  const [userNameMap, setUserNameMap] = useState<Map<string, string>>(() => buildUserNameMap([]));
  const [execStats, setExecStats] = useState<ExecutionStatsResponse | null>(null);
  const [execStatsLoading, setExecStatsLoading] = useState(false);
  const wf = useWorkflow(testCase.workflow_item_id);

  useEffect(() => {
    let cancelled = false;
    api.listUsers({ limit: 100 })
      .then((res) => {
        if (!cancelled) {
          setUserNameMap(buildUserNameMap(res.data || []));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setUserNameMap(buildUserNameMap([]));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const fetchExecStats = useCallback(async () => {
    setExecStatsLoading(true);
    try {
      const res = await api.getCaseExecutionStats(testCase.case_id);
      setExecStats(res.data);
    } catch {
      setExecStats(null);
    } finally {
      setExecStatsLoading(false);
    }
  }, [testCase.case_id]);

  const handleTabChange = useCallback((tab: DetailTab) => {
    setActiveTab(tab);
    if (tab === 'stats' && !execStats) {
      fetchExecStats();
    }
  }, [fetchExecStats, execStats]);

  const ownerName = resolveUserName(userNameMap, testCase.owner_id);
  const reviewerName = resolveUserName(userNameMap, testCase.reviewer_id);
  const autoDevName = resolveUserName(userNameMap, testCase.auto_dev_id);

  const hasAutomationSection = Boolean(
    testCase.automation_case_ref
    || testCase.is_automated
    || testCase.is_need_auto
    || testCase.automation_type
    || testCase.script_entity_id,
  );

  const hasAdvancedExtras = useMemo(() => (
    hasDisplayValue(testCase.failure_analysis)
    || hasDisplayValue(testCase.deprecation_reason)
    || (testCase.custom_fields && Object.keys(testCase.custom_fields).length > 0)
    || (testCase.attachments && testCase.attachments.length > 0)
    || (testCase.approval_history && testCase.approval_history.length > 0)
  ), [testCase]);

  const handleWorkflowSuccess = () => {
    setWorkflowRefreshSignal((n) => n + 1);
    void wf.refresh();
    void wf.refreshLogs();
  };

  const historyRefreshSignal = changeLogRefreshSignal + workflowRefreshSignal;

  const formatDate = (dateStr: string | null | undefined) => dateStr ? new Date(dateStr).toLocaleString('zh-CN') : '-';

  const renderField = (label: string, value: React.ReactNode) => {
    if (!hasDisplayValue(value)) return null;
    return (
      <div style={styles.sideField}>
        <span style={styles.sideFieldLabel}>{label}</span>
        <span style={styles.sideFieldValue}>{value}</span>
      </div>
    );
  };

  const renderAttachments = () => {
    if (!testCase.attachments?.length) return null;
    return (
      <ul style={styles.attachmentList}>
        {testCase.attachments.map((att, index) => {
          const filename = String(att.original_filename || att.file_id || `附件 ${index + 1}`);
          const size = formatFileSize(att.size);
          return (
            <li key={`${filename}-${index}`} style={styles.attachmentItem}>
              <span style={styles.attachmentName}>{filename}</span>
              {size && <span style={styles.attachmentMeta}>{size}</span>}
              {att.content_type && (
                <span style={styles.attachmentMeta}>{String(att.content_type)}</span>
              )}
            </li>
          );
        })}
      </ul>
    );
  };

  const renderApprovalHistory = () => {
    if (!testCase.approval_history?.length) return null;
    return (
      <div style={styles.approvalList}>
        {testCase.approval_history.map((entry, index) => {
          const action = entry.action ?? entry.status ?? entry.result;
          const actor = entry.operator_id ?? entry.user_id ?? entry.reviewer_id;
          const at = entry.created_at ?? entry.approved_at ?? entry.timestamp;
          const actorName = typeof actor === 'string' ? resolveUserName(userNameMap, actor) : null;
          if (action || actor || at) {
            return (
              <div key={index} style={styles.approvalItem}>
                {action && <span style={styles.approvalAction}>{String(action)}</span>}
                {actorName && <span>{actorName}</span>}
                {at && (
                  <span style={styles.approvalTime}>
                    {formatDate(String(at))}
                  </span>
                )}
              </div>
            );
          }
          return (
            <pre key={index} style={styles.codeBlockCompact}>
              {JSON.stringify(entry, null, 2)}
            </pre>
          );
        })}
      </div>
    );
  };

  // ─── Left sidebar: summary dashboard ───
  const sidebarCatalog = (labLabel || catalogPathParts.length > 0) && (
    <div style={styles.sideSection}>
      {labLabel && (
        <div style={styles.sideField}>
          <span style={styles.sideFieldLabel}>Lab</span>
          <span style={{ ...catalogStyles.chip, ...catalogStyles.chipLab }}>{labLabel}</span>
        </div>
      )}
      {catalogPathParts.length > 0 && (
        <div style={styles.sideField}>
          <span style={styles.sideFieldLabel}>目录</span>
          <div style={styles.sideEnvList}>
            {catalogPathParts.map((part, i) => (
              <React.Fragment key={`${part}-${i}`}>
                {i > 0 && <span style={styles.catalogSep}>/</span>}
                <span style={{ ...catalogStyles.chip, ...(i === catalogPathParts.length - 1 ? styles.catalogChipLeaf : {}) }}>
                  {part}
                </span>
              </React.Fragment>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const sidebarPersonCards = (ownerName || reviewerName || autoDevName) && (
    <div style={styles.sidePersonGroup}>
      {ownerName && (
        <div style={styles.sidePersonCard}>
          <span style={styles.sidePersonRole}>负责人</span>
          <span style={styles.sidePersonName}>{ownerName}</span>
        </div>
      )}
      {reviewerName && (
        <div style={styles.sidePersonCard}>
          <span style={styles.sidePersonRole}>审核人</span>
          <span style={styles.sidePersonName}>{reviewerName}</span>
        </div>
      )}
      {autoDevName && (
        <div style={styles.sidePersonCard}>
          <span style={styles.sidePersonRole}>自动化</span>
          <span style={styles.sidePersonName}>{autoDevName}</span>
        </div>
      )}
    </div>
  );

  const sidebarTags = testCase.tags?.length ? (
    <div style={styles.sideTags}>
      {testCase.tags.map((tag, index) => (
        <span key={index} style={styles.sideTag}>{tag}</span>
      ))}
    </div>
  ) : null;

  const sidebarConditions = (testCase.pre_condition || testCase.post_condition) && (
    <div style={styles.sideSection}>
      {testCase.pre_condition && (
        <div style={styles.sideField}>
          <span style={styles.sideFieldLabel}>前置条件</span>
          <span style={styles.sideFieldChip}>{testCase.pre_condition}</span>
        </div>
      )}
      {testCase.post_condition && (
        <div style={styles.sideField}>
          <span style={styles.sideFieldLabel}>后置条件</span>
          <span style={styles.sideFieldChip}>{testCase.post_condition}</span>
        </div>
      )}
    </div>
  );

  const sidebarMeta = (
    <div style={styles.sideMeta}>
      <div style={styles.sideMetaRow}>
        <span style={styles.sideMetaLabel}>创建</span>
        <span style={styles.sideMetaValue}>{formatDate(testCase.created_at)}</span>
      </div>
      <div style={styles.sideMetaRow}>
        <span style={styles.sideMetaLabel}>更新</span>
        <span style={styles.sideMetaValue}>{formatDate(testCase.updated_at)}</span>
      </div>
      <div style={styles.sideMetaRow}>
        <span style={styles.sideMetaLabel}>用例 ID</span>
        <span style={{ ...styles.sideMetaValue, fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{testCase.case_id}</span>
      </div>
    </div>
  );

  // ─── Right panel: tab content ───
  const stepsContent = (
    <TestCaseStepList
      steps={testCase.steps ?? []}
      cleanupSteps={testCase.cleanup_steps ?? []}
      showEditHint={showEdit}
    />
  );

  const workflowContent = testCase.workflow_item_id ? (
    <WorkflowPanel
      workflowItemId={testCase.workflow_item_id}
      entityLabel={`${testCase.case_id} · ${testCase.title}`}
      typeCode="TEST_CASE"
      defaultPriority={testCase.priority}
      creatorName={ownerName || testCase.owner_id}
      currentOwnerName={ownerName || testCase.owner_id}
      createdAt={testCase.created_at}
      updatedAt={testCase.updated_at}
      compact
      hideToolbar
      showMetaGrid={false}
      showPermissionHint={false}
      showLogs={false}
      defaultLogsCollapsed
      refreshSignal={workflowRefreshSignal}
      onTransitionSuccess={handleWorkflowSuccess}
    />
  ) : (
    <p style={styles.emptyState}>此用例未关联工作流</p>
  );

  const moreContent = (
    <>
      <div style={styles.moreGrid}>
        {renderField('关联需求', testCase.ref_req_id)}
        {renderField('测试类别', testCase.test_category)}
        {renderField('风险等级', testCase.risk_level)}
        {renderField('保密级别', CONFIDENTIALITY_LABELS[testCase.confidentiality ?? ''] || testCase.confidentiality)}
        {renderField('可见范围', VISIBILITY_LABELS[testCase.visibility_scope ?? ''] || testCase.visibility_scope)}
        {renderField('预计时长', testCase.estimated_duration_sec ? `${testCase.estimated_duration_sec}s` : null)}
      </div>
      <div style={styles.moreGrid}>
        {testCase.is_destructive && renderField('破坏性测试', '是')}
        {testCase.is_need_auto && renderField('需要自动化', '是')}
        {testCase.is_automated && renderField('已自动化', '是')}
        {!testCase.is_active && renderField('激活状态', '未激活')}
      </div>
      <div style={styles.moreGrid}>
        {renderField('故障分析', testCase.failure_analysis)}
        {renderField('弃用原因', testCase.deprecation_reason)}
      </div>
      {testCase.custom_fields && Object.keys(testCase.custom_fields).length > 0 && (
        <div style={styles.subBlock}>
          <span style={styles.subBlockTitle}>自定义字段</span>
          <pre style={styles.codeBlockCompact}>{JSON.stringify(testCase.custom_fields, null, 2)}</pre>
        </div>
      )}
      {testCase.attachments?.length > 0 && (
        <div style={styles.subBlock}>
          <span style={styles.subBlockTitle}>附件</span>
          {renderAttachments()}
        </div>
      )}
      {testCase.approval_history?.length > 0 && (
        <div style={styles.subBlock}>
          <span style={styles.subBlockTitle}>审批记录</span>
          {renderApprovalHistory()}
        </div>
      )}
      {!hasAdvancedExtras && (
        <p style={styles.emptyState}>暂无故障分析、弃用说明、自定义字段、附件或审批记录</p>
      )}
    </>
  );

  const stepCount = testCase.steps?.length ?? 0;
  const cleanupCount = testCase.cleanup_steps?.length ?? 0;

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-[960px] max-h-[90vh] flex flex-col p-0 gap-0" style={{ borderRadius: 12, overflow: 'hidden' }}>
        {/* ── Header ── */}
        <div style={styles.modalHeader}>
          <div style={styles.modalHeaderMain}>
            <div style={styles.headerTopRow}>
              {testCase.case_id && <span style={styles.caseId}>{testCase.case_id}</span>}
              <WorkflowCurrentStateBadge
                state={testCase.status}
                typeCode="TEST_CASE"
                variant="compact"
              />
              <span style={styles.headerVersion}>v{testCase.version}</span>
            </div>
            <h2 style={styles.modalTitle}>{testCase.title}</h2>
          </div>
          <div style={styles.headerActions}>
            {testCase.workflow_item_id && (
              <WorkflowActionToolbar
                workflowItemId={testCase.workflow_item_id}
                typeCode="TEST_CASE"
                defaultPriority={testCase.priority}
                compact
                showStateBadge={false}
                overflowMenu
                workflow={wf}
                onTransitionSuccess={handleWorkflowSuccess}
              />
            )}
            {showEdit && (
              <button type="button" style={styles.editButton} onClick={onEdit}>
                编辑
              </button>
            )}
            <TestCaseHistoryPanel
              caseId={testCase.case_id}
              workflowItemId={testCase.workflow_item_id}
              typeCode="TEST_CASE"
              refreshSignal={historyRefreshSignal}
            />
            {testCase.workflow_item_id && (
              <WorkflowOverflowMenu
                workflowItemId={testCase.workflow_item_id}
                workflow={wf}
                onTransitionSuccess={handleWorkflowSuccess}
              />
            )}
          </div>
        </div>

        {/* ── Split body: sidebar + main ── */}
        <div style={styles.splitBody}>
          {/* Left sidebar — always visible summary */}
          <aside style={styles.sidebar}>
            {/* Catalog (Lab + directory) */}
            {sidebarCatalog}
            <div style={styles.sideDivider} />

            {/* Person cards */}
            {sidebarPersonCards}

            {/* Tags */}
            {sidebarTags}

            {/* Divider */}
            <div style={styles.sideDivider} />

            {/* Conditions */}
            {sidebarConditions}

            {/* Automation summary */}
            {hasAutomationSection && (
              <>
                <div style={styles.sideDivider} />
                <div style={styles.sideSection}>
                  <span style={styles.sideSectionTitle}>自动化</span>
                  <div style={styles.sideFieldGrid}>
                    {renderField('类型', testCase.automation_type)}
                    {renderField('脚本 ID', testCase.script_entity_id)}
                    {renderField('自动化 ID', testCase.automation_case_ref?.auto_case_id)}
                  </div>
                </div>
              </>
            )}

            {/* Divider */}
            <div style={styles.sideDivider} />

            {/* Required env */}
            {testCase.required_env && Object.keys(testCase.required_env).length > 0 && (
              <div style={styles.sideSection}>
                <span style={styles.sideSectionTitle}>运行环境</span>
                <div style={styles.sideEnvList}>
                  {Object.entries(testCase.required_env).map(([key, value]) => (
                    <div key={key} style={styles.sideEnvItem}>
                      <span style={styles.sideEnvKey}>{key}</span>
                      <span style={styles.sideEnvValue}>{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Meta */}
            {sidebarMeta}
          </aside>

          {/* Right main — tabbed content */}
          <main style={styles.mainPanel}>
            <div style={styles.mainTabBar}>
              <button
                type="button"
                style={{ ...styles.mainTab, ...(activeTab === 'steps' ? styles.mainTabActive : {}) }}
                onClick={() => handleTabChange('steps')}
              >
                执行步骤
                {stepCount > 0 && <span style={styles.mainTabBadge}>{stepCount}</span>}
                {cleanupCount > 0 && <span style={{ ...styles.mainTabBadge, ...styles.mainTabBadgeCleanup }}>清理 {cleanupCount}</span>}
              </button>
              <button
                type="button"
                style={{ ...styles.mainTab, ...(activeTab === 'workflow' ? styles.mainTabActive : {}) }}
                onClick={() => handleTabChange('workflow')}
              >
                工作流
              </button>
              <button
                type="button"
                style={{ ...styles.mainTab, ...(activeTab === 'more' ? styles.mainTabActive : {}) }}
                onClick={() => handleTabChange('more')}
              >
                更多信息
              </button>
              <button
                type="button"
                style={{ ...styles.mainTab, ...(activeTab === 'stats' ? styles.mainTabActive : {}) }}
                onClick={() => handleTabChange('stats')}
              >
                执行统计
                {execStats && <span style={styles.mainTabBadge}>{execStats.total}</span>}
              </button>
              <button
                type="button"
                style={{ ...styles.mainTab, ...(activeTab === 'comments' ? styles.mainTabActive : {}) }}
                onClick={() => handleTabChange('comments')}
              >
                评论
              </button>
            </div>

            <div style={styles.mainContent}>
              {activeTab === 'steps' && stepsContent}
              {activeTab === 'workflow' && workflowContent}
              {activeTab === 'more' && moreContent}
              {activeTab === 'stats' && (
                <div style={{ padding: 'var(--space-4)' }}>
                  {execStatsLoading ? (
                    <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
                      <div className="loading-spinner" style={{ width: 24, height: 24 }} />
                    </div>
                  ) : execStats ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                      {/* 统计卡片 */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8 }}>
                        {[
                          { label: '总次数', value: execStats.total, color: 'var(--status-info)' },
                          { label: '通过', value: execStats.passed, color: 'var(--status-success)' },
                          { label: '失败', value: execStats.failed, color: 'var(--status-error)' },
                          { label: '通过率', value: `${execStats.pass_rate}%`, color: execStats.pass_rate >= 80 ? 'var(--status-success)' : 'var(--status-warning)' },
                        ].map(({ label, value, color }) => (
                          <div key={label} style={{
                            background: 'var(--surface-secondary)', borderRadius: 10, padding: '14px 16px',
                            border: '1px solid var(--border-subtle)', textAlign: 'center',
                          }}>
                            <div style={{ fontSize: 24, fontWeight: 700, color, lineHeight: 1.2 }}>{value}</div>
                            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>{label}</div>
                          </div>
                        ))}
                      </div>

                      {/* 最近执行记录 */}
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
                          最近执行记录
                        </div>
                        {execStats.recent.length > 0 ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            {execStats.recent.map((r) => (
                              <div key={r.result_id} style={{
                                display: 'flex', alignItems: 'center', gap: 10,
                                padding: '8px 12px', background: 'var(--surface-primary)',
                                borderRadius: 8, border: '1px solid var(--border-subtle)',
                                fontSize: 12, color: 'var(--text-secondary)',
                              }}>
                                <span style={{
                                  width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                                  backgroundColor: r.passed ? 'var(--status-success)' : 'var(--status-error)',
                                }} />
                                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                  {r.notes || (r.passed ? '测试通过' : '测试失败')}
                                </span>
                                <span style={{ color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}>
                                  {new Date(r.executed_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                                </span>
                                <span style={{ color: 'var(--text-tertiary)', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 11 }}>
                                  {r.executed_by}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p style={{ fontSize: 12, color: 'var(--text-tertiary)', fontStyle: 'italic' }}>暂无执行记录</p>
                        )}
                      </div>

                      {execStats.last_executed_at && (
                        <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                          最近执行：{new Date(execStats.last_executed_at).toLocaleString('zh-CN')}
                        </div>
                      )}
                    </div>
                  ) : (
                    <p style={{ textAlign: 'center', fontSize: 13, color: 'var(--text-tertiary)', padding: 40 }}>加载失败</p>
                  )}
                </div>
              )}
              {activeTab === 'comments' && (
                <TestCaseCommentPanel caseId={testCase.case_id} />
              )}
            </div>
          </main>
        </div>
      </DialogContent>
    </Dialog>
  );
};

const styles = {
  // ── Header ──
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '16px',
    padding: '18px 28px',
    borderBottom: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-tertiary)',
    borderRadius: '14px 14px 0 0',
  },
  modalHeaderMain: {
    minWidth: 0,
    flex: 1,
  },
  headerTopRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '6px',
    flexWrap: 'wrap' as const,
  },
  caseId: {
    fontSize: '12px',
    color: 'var(--accent-cyan)',
    fontFamily: "'JetBrains Mono', monospace",
    fontWeight: 500,
  },
  headerVersion: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
    fontFamily: "'JetBrains Mono', monospace",
  },
  headerPriorityDot: {
    width: 8, height: 8,
    borderRadius: '50%',
    display: 'inline-block',
  },
  headerPriority: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    fontWeight: 500,
  },
  modalTitle: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    wordBreak: 'break-word' as const,
    lineHeight: 1.4,
  },
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexShrink: 0,
    flexWrap: 'wrap' as const,
    justifyContent: 'flex-end' as const,
  },
  editButton: {
    padding: '6px 14px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: '6px',
    cursor: 'pointer',
  },

  // ── Catalog banner ──
  catalogBanner: {
    display: 'flex',
    flexDirection: 'row' as const,
    flexWrap: 'wrap' as const,
    gap: '12px 24px',
    padding: '10px 28px',
    backgroundColor: 'var(--status-info-bg)',
    borderBottom: '1px solid var(--border-subtle)',
  },
  catalogBannerRow: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    alignItems: 'center',
    gap: 'var(--space-3)',
  },
  catalogBannerLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.45px',
    flexShrink: 0,
    minWidth: 32,
  },
  catalogBannerChips: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    alignItems: 'center',
    gap: 4,
    flex: 1,
  },
  catalogSep: {
    color: 'var(--text-tertiary)',
    fontSize: 12,
    margin: '0 2px',
  },
  catalogChipLeaf: {
    fontWeight: 600,
    borderStyle: 'dashed',
  },

  // ── Version note ──
  versionNote: {
    padding: '10px 28px',
    borderBottom: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--bg-secondary)',
  },
  versionNoteLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-muted)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    display: 'block',
    marginBottom: 4,
  },
  versionNoteText: {
    margin: 0,
    fontSize: 13,
    color: 'var(--text-secondary)',
    whiteSpace: 'pre-wrap' as const,
    lineHeight: 1.6,
  },

  // ── Split body ──
  splitBody: {
    flex: 1,
    minHeight: 0,
    display: 'flex',
    overflow: 'hidden',
  } as const,

  // ── Left sidebar ──
  sidebar: {
    width: 320,
    minWidth: 320,
    overflowY: 'auto' as const,
    borderRight: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--bg-primary)',
    padding: '20px 20px 28px',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '16px',
  } as const,
  sidePersonGroup: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(90px, 1fr))',
    gap: '8px',
  } as const,
  sidePersonCard: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '4px',
    padding: '10px 8px',
    backgroundColor: 'var(--surface-secondary)',
    borderRadius: '8px',
    border: '1px solid var(--border-muted)',
  } as const,
  sidePersonRole: {
    fontSize: '10px',
    fontWeight: 500,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.4px',
  } as const,
  sidePersonName: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    textAlign: 'center' as const,
    wordBreak: 'break-word' as const,
  } as const,
  sideTags: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '6px',
  } as const,
  sideTag: {
    padding: '3px 10px',
    backgroundColor: 'var(--surface-tertiary)',
    borderRadius: '12px',
    fontSize: '11px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
  } as const,
  sideDivider: {
    height: 1,
    backgroundColor: 'var(--border-subtle)',
    margin: '2px 0',
  } as const,
  sideSection: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  } as const,
  sideSectionTitle: {
    fontSize: '10px',
    fontWeight: 600,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.6px',
  } as const,
  sideFieldGrid: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '6px',
  } as const,
  sideField: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '2px',
  } as const,
  sideFieldLabel: {
    fontSize: '10px',
    fontWeight: 600,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.4px',
  } as const,
  sideFieldValue: {
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-primary)',
    wordBreak: 'break-word' as const,
  } as const,
  sideFieldChip: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    lineHeight: 1.5,
    wordBreak: 'break-word' as const,
    backgroundColor: 'var(--surface-secondary)',
    padding: '6px 10px',
    borderRadius: '6px',
    border: '1px solid var(--border-muted)',
  } as const,
  sideEnvList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
  } as const,
  sideEnvItem: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '6px 10px',
    backgroundColor: 'var(--surface-secondary)',
    borderRadius: '6px',
    border: '1px solid var(--border-muted)',
  } as const,
  sideEnvKey: {
    fontSize: '11px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-purple)',
    fontWeight: 500,
  } as const,
  sideEnvValue: {
    fontSize: '11px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--text-primary)',
    wordBreak: 'break-all' as const,
  } as const,
  sideMeta: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '6px',
  } as const,
  sideMetaRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  } as const,
  sideMetaLabel: {
    fontSize: '10px',
    fontWeight: 600,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.4px',
  } as const,
  sideMetaValue: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
  } as const,

  // ── Right main panel ──
  mainPanel: {
    flex: 1,
    minWidth: 0,
    display: 'flex',
    flexDirection: 'column' as const,
    backgroundColor: 'var(--bg-elevated)',
  } as const,
  mainTabBar: {
    display: 'flex',
    gap: 0,
    padding: '0 24px',
    borderBottom: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--bg-elevated)',
    flexShrink: 0,
  } as const,
  mainTab: {
    padding: '12px 20px',
    border: 'none',
    background: 'transparent',
    color: 'var(--text-tertiary)',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 500,
    borderBottom: '2px solid transparent',
    marginBottom: -1,
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'color var(--transition-fast), border-color var(--transition-fast)',
  } as const,
  mainTabActive: {
    color: 'var(--accent-primary)',
    borderBottom: '2px solid var(--accent-primary)',
    fontWeight: 600,
  } as const,
  mainTabBadge: {
    fontSize: '11px',
    fontWeight: 600,
    padding: '1px 8px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--surface-tertiary)',
    color: 'var(--text-secondary)',
  } as const,
  mainTabBadgeCleanup: {
    backgroundColor: 'color-mix(in srgb, var(--status-warning) 12%, transparent)',
    color: 'var(--status-warning)',
  } as const,
  mainContent: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '20px 24px',
    minHeight: 0,
  } as const,

  // ── Shared ──
  emptyState: {
    margin: 0,
    fontSize: '13px',
    color: 'var(--text-muted)',
    textAlign: 'center' as const,
    padding: '32px 16px',
  } as const,
  subBlock: {
    marginTop: 16,
    paddingTop: 12,
    borderTop: '1px solid var(--border-muted)',
  } as const,
  subBlockTitle: {
    display: 'block',
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-muted)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    marginBottom: 8,
  } as const,
  moreGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '16px',
  } as const,

  // ── Attachments ──
  attachmentList: {
    margin: 0, padding: 0,
    listStyle: 'none',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 8,
  } as const,
  attachmentItem: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    alignItems: 'center',
    gap: '8px 12px',
    padding: '8px 12px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 6,
    border: '1px solid var(--border-muted)',
  } as const,
  attachmentName: {
    fontSize: 13,
    color: 'var(--text-primary)',
    fontWeight: 500,
  } as const,
  attachmentMeta: {
    fontSize: 11,
    color: 'var(--text-muted)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,

  // ── Approval ──
  approvalList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 8,
  } as const,
  approvalItem: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    alignItems: 'center',
    gap: '8px 12px',
    padding: '8px 12px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 6,
    fontSize: 13,
  } as const,
  approvalAction: {
    fontWeight: 600,
    color: 'var(--accent-primary)',
  } as const,
  approvalTime: {
    fontSize: 12,
    color: 'var(--text-muted)',
    marginLeft: 'auto',
  } as const,
  codeBlockCompact: {
    margin: 0,
    padding: '10px 12px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: '6px',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    overflow: 'auto' as const,
    maxHeight: '160px',
  } as const,
};

export default TestCaseDetailModal;
