import React, { useEffect, useMemo, useState } from 'react';
import type { TestCaseResponse, UserResponse } from '../types';
import { WorkflowPanel, WorkflowActionToolbar, WorkflowOverflowMenu } from './workflow';
import { useWorkflow } from '../hooks/useWorkflow';
import { getStateLabel, getWorkflowStateStyle } from '../constants/workflowLabels';
import { PRIORITY_LABELS } from '../constants/testCaseLabels';
import { catalogStyles } from './catalog/catalogStyles';
import { SWITCHABLE_USERS } from '../config/users';
import { api } from '../services/api';
import TestCaseHistoryPanel from './TestCaseHistoryPanel';
import TestCaseStepList from './TestCaseStepList';

interface TestCaseDetailModalProps {
  testCase: TestCaseResponse;
  onClose: () => void;
  onEdit?: () => void;
  /** 递增时刷新变更记录（如编辑保存后） */
  changeLogRefreshSignal?: number;
}

type DetailTab = 'overview' | 'steps' | 'workflow' | 'more';

const DETAIL_TABS: { id: DetailTab; label: string; badge?: number }[] = [
  { id: 'overview', label: '概览' },
  { id: 'steps', label: '步骤' },
  { id: 'workflow', label: '工作流' },
  { id: 'more', label: '更多' },
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
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [workflowRefreshSignal, setWorkflowRefreshSignal] = useState(0);
  const [userNameMap, setUserNameMap] = useState<Map<string, string>>(() => buildUserNameMap([]));
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

  const ownerName = resolveUserName(userNameMap, testCase.owner_id);
  const reviewerName = resolveUserName(userNameMap, testCase.reviewer_id);
  const autoDevName = resolveUserName(userNameMap, testCase.auto_dev_id);
  const stateStyle = getWorkflowStateStyle(testCase.status);
  const priorityLabel = testCase.priority
    ? (PRIORITY_LABELS[testCase.priority as keyof typeof PRIORITY_LABELS] || testCase.priority)
    : null;

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

  const hasConditionContent = Boolean(
    testCase.pre_condition
    || testCase.post_condition
    || testCase.tags?.length
    || (testCase.required_env && Object.keys(testCase.required_env).length > 0),
  );

  const formatDate = (dateStr: string) => new Date(dateStr).toLocaleString('zh-CN');

  const renderEmptyState = (message: string) => (
    <p style={styles.emptyState}>{message}</p>
  );

  const renderField = (label: string, value: React.ReactNode) => {
    if (!hasDisplayValue(value)) return null;
    return (
      <div style={styles.infoRow}>
        <span style={styles.infoLabel}>{label}</span>
        <span style={styles.infoValue}>{value}</span>
      </div>
    );
  };

  const renderRequiredEnv = () => {
    if (!testCase.required_env || Object.keys(testCase.required_env).length === 0) return null;
    return (
      <div style={styles.infoRowFull}>
        <span style={styles.infoLabel}>运行环境</span>
        <div style={styles.envGrid}>
          {Object.entries(testCase.required_env).map(([key, value]) => (
            <div key={key} style={styles.envItem}>
              <span style={styles.envKey}>{key}</span>
              <span style={styles.envValue}>{String(value)}</span>
            </div>
          ))}
        </div>
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

  const overviewContent = (
    <>
      {/* Person cards */}
      {(ownerName || reviewerName || autoDevName) && (
        <div style={styles.personSummary}>
          {ownerName && (
            <div style={styles.personCard}>
              <span style={styles.personRole}>负责人</span>
              <span style={styles.personName}>{ownerName}</span>
            </div>
          )}
          {reviewerName && (
            <div style={styles.personCard}>
              <span style={styles.personRole}>审核人</span>
              <span style={styles.personName}>{reviewerName}</span>
            </div>
          )}
          {autoDevName && (
            <div style={styles.personCard}>
              <span style={styles.personRole}>自动化开发</span>
              <span style={styles.personName}>{autoDevName}</span>
            </div>
          )}
        </div>
      )}

      {/* Core fields — 3 columns for compact display */}
      <div style={styles.infoGrid3Col}>
        {renderField('关联需求', testCase.ref_req_id)}
        {renderField('测试类别', testCase.test_category)}
        {renderField('风险等级', testCase.risk_level)}
        {renderField('保密级别', testCase.confidentiality)}
        {renderField('可见范围', testCase.visibility_scope)}
        {renderField('预计时长', testCase.estimated_duration_sec ? `${testCase.estimated_duration_sec} 秒` : null)}
        {testCase.is_destructive && renderField('破坏性测试', '是')}
        {testCase.is_need_auto && renderField('需要自动化', '是')}
        {testCase.is_automated && renderField('已自动化', '是')}
        {!testCase.is_active && renderField('激活状态', '未激活')}
        {renderField('创建时间', formatDate(testCase.created_at))}
        {renderField('更新时间', formatDate(testCase.updated_at))}
      </div>

      {/* Automation sub-section — only if relevant */}
      {hasAutomationSection && (
        <div style={styles.subBlock}>
          <span style={styles.subBlockTitle}>自动化</span>
          <div style={styles.infoGrid3Col}>
            {renderField('用例 ID', testCase.automation_case_ref?.auto_case_id)}
            {renderField('版本', testCase.automation_case_ref?.version)}
            {renderField('类型', testCase.automation_type)}
            {renderField('脚本实体 ID', testCase.script_entity_id)}
          </div>
        </div>
      )}

      {/* Conditions sub-section */}
      {hasConditionContent && (
        <div style={styles.subBlock}>
          <span style={styles.subBlockTitle}>条件与环境</span>
          <div style={styles.infoGrid}>
            {renderField('前置条件', testCase.pre_condition)}
            {renderField('后置条件', testCase.post_condition)}
          </div>
          {renderRequiredEnv()}
        </div>
      )}

      {/* Tags — full width */}
      {testCase.tags?.length ? (
        <div style={{ ...styles.infoRowFull, marginTop: 16 }}>
          <span style={styles.infoLabel}>标签</span>
          <div style={styles.tagList}>
            {testCase.tags.map((tag, index) => (
              <span key={index} style={styles.tag}>{tag}</span>
            ))}
          </div>
        </div>
      ) : null}
    </>
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
    renderEmptyState('此用例未关联工作流')
  );

  return (
    <div style={styles.overlay} onClick={onClose} onKeyDown={(e) => e.key === 'Escape' && onClose()} tabIndex={0}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div style={styles.modalHeader}>
          <div style={styles.modalHeaderMain}>
            <span style={styles.caseId}>{testCase.case_id}</span>
            <h2 style={styles.modalTitle}>{testCase.title}</h2>
          </div>
          <div style={styles.headerActions}>
            {testCase.workflow_item_id && (
              <WorkflowActionToolbar
                workflowItemId={testCase.workflow_item_id}
                typeCode="TEST_CASE"
                defaultPriority={testCase.priority}
                compact
                showStateBadge
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
            <button type="button" style={styles.closeButton} onClick={onClose}>×</button>
          </div>
        </div>

        {(labLabel || catalogPathParts.length > 0) && (
          <div style={styles.catalogBanner} aria-label="Lab 与目录">
            {labLabel && (
              <div style={styles.catalogBannerRow}>
                <span style={styles.catalogBannerLabel}>所属 Lab</span>
                <span style={{ ...catalogStyles.chip, ...catalogStyles.chipLab }}>{labLabel}</span>
              </div>
            )}
            {catalogPathParts.length > 0 && (
              <div style={styles.catalogBannerRow}>
                <span style={styles.catalogBannerLabel}>分类目录</span>
                <div style={styles.catalogBannerChips}>
                  {catalogPathParts.map((part, i) => (
                    <React.Fragment key={`${part}-${i}`}>
                      {i > 0 && <span style={styles.catalogSep}>/</span>}
                      <span
                        style={{
                          ...catalogStyles.chip,
                          ...(i === catalogPathParts.length - 1 ? styles.catalogChipLeaf : {}),
                        }}
                      >
                        {part}
                      </span>
                    </React.Fragment>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div style={styles.overviewStrip}>
          <span className="status-badge" style={stateStyle}>
            {getStateLabel(testCase.status, 'TEST_CASE')}
          </span>
          <span style={styles.overviewItem}>v{testCase.version}</span>
          {priorityLabel && <span style={styles.overviewItem}>{priorityLabel}</span>}
          {ownerName && <span style={styles.overviewItem}>负责人 {ownerName}</span>}
          {testCase.ref_req_id && (
            <span style={styles.overviewItem}>需求 {testCase.ref_req_id}</span>
          )}
          <span style={styles.overviewMuted}>
            更新于 {formatDate(testCase.updated_at)}
          </span>
        </div>

        {testCase.change_log && (
          <div style={styles.versionNote}>
            <span style={styles.versionNoteLabel}>版本说明</span>
            <p style={styles.versionNoteText}>{testCase.change_log}</p>
          </div>
        )}

        <div style={styles.tabBar} role="tablist" aria-label="用例详情分区">
          {DETAIL_TABS.map((tab) => {
            const stepCount = tab.id === 'steps' ? (testCase.steps?.length ?? 0) : 0;
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls={`test-case-detail-panel-${tab.id}`}
                id={`test-case-detail-tab-${tab.id}`}
                style={{
                  ...styles.tab,
                  ...(activeTab === tab.id ? styles.activeTab : {}),
                }}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
                {stepCount > 0 && <span style={styles.tabBadge}>({stepCount})</span>}
              </button>
            );
          })}
        </div>

        <div style={styles.modalBody}>
          {activeTab === 'overview' && (
            <div
              id="test-case-detail-panel-overview"
              role="tabpanel"
              aria-labelledby="test-case-detail-tab-overview"
            >
              {overviewContent}
            </div>
          )}
          {activeTab === 'steps' && (
            <div
              id="test-case-detail-panel-steps"
              role="tabpanel"
              aria-labelledby="test-case-detail-tab-steps"
            >
              <TestCaseStepList
                steps={testCase.steps ?? []}
                cleanupSteps={testCase.cleanup_steps ?? []}
                showEditHint={showEdit}
              />
            </div>
          )}
          {activeTab === 'workflow' && (
            <div
              id="test-case-detail-panel-workflow"
              role="tabpanel"
              aria-labelledby="test-case-detail-tab-workflow"
            >
              {workflowContent}
            </div>
          )}
          {activeTab === 'more' && (
            <div
              id="test-case-detail-panel-more"
              role="tabpanel"
              aria-labelledby="test-case-detail-tab-more"
            >
              <div style={styles.infoGrid}>
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
                <p style={styles.emptyState}>
                  暂无故障分析、弃用说明、自定义字段、附件或审批记录
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const styles = {
  overlay: {
    position: 'fixed' as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    backdropFilter: 'blur(4px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2000,
    animation: 'fadeIn 0.2s ease',
  } as const,
  modal: {
    backgroundColor: 'var(--bg-elevated)',
    borderRadius: '12px',
    width: '90%',
    maxWidth: '900px',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column' as const,
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.4)',
    border: '1px solid var(--border-default)',
    animation: 'slideUp 0.3s ease',
  } as const,
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '16px',
    padding: '20px 24px',
    borderBottom: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-tertiary)',
    borderRadius: '12px 12px 0 0',
  } as const,
  modalHeaderMain: {
    minWidth: 0,
    flex: 1,
  } as const,
  caseId: {
    fontSize: '13px',
    color: 'var(--accent-cyan)',
    fontFamily: "'JetBrains Mono', monospace",
    display: 'block',
    marginBottom: '4px',
  } as const,
  modalTitle: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    wordBreak: 'break-word' as const,
  } as const,
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flexShrink: 0,
    flexWrap: 'wrap' as const,
    justifyContent: 'flex-end' as const,
  } as const,
  editButton: {
    padding: '6px 14px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'background-color var(--transition-fast), border-color var(--transition-fast)',
  } as const,
  closeButton: {
    fontSize: '28px',
    color: 'var(--text-muted)',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    padding: '0',
    lineHeight: 1,
    transition: 'color var(--transition-fast)',
  } as const,
  catalogBanner: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-2)',
    padding: 'var(--space-3) var(--space-6)',
    backgroundColor: 'var(--status-info-bg)',
    borderBottom: '1px solid var(--border-subtle)',
  } as const,
  catalogBannerRow: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 'var(--space-3)',
  } as const,
  catalogBannerLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase',
    letterSpacing: '0.45px',
    flexShrink: 0,
  } as const,
  catalogBannerChips: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 4,
    flex: 1,
  } as const,
  catalogSep: {
    color: 'var(--text-tertiary)',
    fontSize: 12,
    margin: '0 2px',
  } as const,
  catalogChipLeaf: {
    fontWeight: 600,
    borderStyle: 'dashed',
  } as const,
  overviewStrip: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    alignItems: 'center',
    gap: '10px 16px',
    padding: '12px 24px',
    borderBottom: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--bg-primary)',
  } as const,
  overviewItem: {
    fontSize: 13,
    color: 'var(--text-secondary)',
  } as const,
  overviewMuted: {
    fontSize: 12,
    color: 'var(--text-muted)',
    marginLeft: 'auto',
  } as const,
  versionNote: {
    padding: '12px 24px',
    borderBottom: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--bg-secondary)',
  } as const,
  versionNoteLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-muted)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    display: 'block',
    marginBottom: 6,
  } as const,
  versionNoteText: {
    margin: 0,
    fontSize: 13,
    color: 'var(--text-secondary)',
    whiteSpace: 'pre-wrap' as const,
    lineHeight: 1.6,
  } as const,
  tabBar: {
    display: 'flex',
    gap: 'var(--space-2)',
    padding: '0 24px',
    borderBottom: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--bg-primary)',
    overflowX: 'auto' as const,
    flexShrink: 0,
    WebkitOverflowScrolling: 'touch' as const,
  } as const,
  tab: {
    padding: 'var(--space-3) var(--space-4)',
    border: 'none',
    background: 'transparent',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 500,
    borderBottom: '2px solid transparent',
    marginBottom: -1,
    whiteSpace: 'nowrap' as const,
    flexShrink: 0,
    transition: 'color var(--transition-fast), border-color var(--transition-fast)',
  } as const,
  activeTab: {
    color: 'var(--accent-primary)',
    borderBottomColor: 'var(--accent-primary)',
    outline: 'none',
  } as const,
  tabBadge: {
    marginLeft: 4,
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-secondary)',
  } as const,
  modalBody: {
    padding: '16px 24px',
    overflowY: 'auto' as const,
    flex: 1,
    minHeight: 0,
  } as const,
  personSummary: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: 12,
    marginBottom: 16,
  } as const,
  personCard: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 4,
    padding: '10px 14px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 8,
    border: '1px solid var(--border-muted)',
    minWidth: 120,
  } as const,
  personRole: {
    fontSize: 11,
    fontWeight: 500,
    color: 'var(--text-muted)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  } as const,
  personName: {
    fontSize: 14,
    fontWeight: 500,
    color: 'var(--text-primary)',
  } as const,
  emptyState: {
    margin: 0,
    fontSize: 13,
    color: 'var(--text-muted)',
    lineHeight: 1.6,
    textAlign: 'center' as const,
    padding: '24px 16px',
  } as const,
  infoGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '12px',
  } as const,
  infoGrid3Col: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '12px',
  } as const,
  infoRow: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
  } as const,
  infoRowFull: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
    gridColumn: '1 / -1',
  } as const,
  infoLabel: {
    fontSize: '11px',
    fontWeight: 500,
    color: 'var(--text-muted)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  } as const,
  infoValue: {
    fontSize: '13px',
    color: 'var(--text-primary)',
    wordBreak: 'break-word' as const,
  } as const,
  tagList: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '6px',
  } as const,
  tag: {
    padding: '4px 10px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: '12px',
    fontSize: '12px',
    color: 'var(--text-secondary)',
  } as const,
  envGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
    gap: '8px',
    marginTop: '8px',
  } as const,
  envItem: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '2px',
    padding: '8px 12px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: '6px',
    border: '1px solid var(--border-muted)',
  } as const,
  envKey: {
    fontSize: '11px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-purple)',
    fontWeight: 500,
  } as const,
  envValue: {
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--text-primary)',
    wordBreak: 'break-all' as const,
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
  attachmentList: {
    margin: 0,
    padding: 0,
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
