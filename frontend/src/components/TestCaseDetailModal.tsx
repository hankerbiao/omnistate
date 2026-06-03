import React from 'react';
import type { TestCaseResponse } from '../types';

const CASE_STATUS_LABELS: Record<string, string> = {
  DRAFT: '草稿',
  PENDING_REVIEW: '待审核',
  APPROVED: '已通过',
  REJECTED: '已拒绝',
  ACTIVE: '激活',
  DEPRECATED: '已弃用',
};

interface TestCaseDetailModalProps {
  testCase: TestCaseResponse;
  onClose: () => void;
  onEdit?: () => void;
}

const NON_EDITABLE_STATES = new Set(['PENDING_REVIEW', 'DONE']);

const TestCaseDetailModal: React.FC<TestCaseDetailModalProps> = ({ testCase, onClose, onEdit }) => {
  const showEdit = Boolean(onEdit) && !NON_EDITABLE_STATES.has(testCase.status);
  const [expandedSections, setExpandedSections] = React.useState<Set<string>>(new Set([
    'basic', 'person', 'exec', 'condition', 'automation', 'meta', 'custom', 'approval', 'time'
  ]));

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  const renderInfoGrid = (children: React.ReactNode) => (
    <div style={styles.infoGrid}>{children}</div>
  );

  const renderField = (label: string, value: React.ReactNode) => {
    if (value === undefined || value === null || value === '' || value === '-') {
      return (
        <div style={styles.infoRow}>
          <span style={styles.infoLabel}>{label}</span>
          <span style={styles.infoValue}>-</span>
        </div>
      );
    }
    return (
      <div style={styles.infoRow}>
        <span style={styles.infoLabel}>{label}</span>
        <span style={styles.infoValue}>{value}</span>
      </div>
    );
  };

  const renderTags = () => {
    if (!testCase.tags || testCase.tags.length === 0) {
      return renderField('标签', '-');
    }
    return (
      <div style={styles.infoRowFull}>
        <span style={styles.infoLabel}>标签</span>
        <div style={styles.tagList}>
          {testCase.tags.map((tag, index) => (
            <span key={index} style={styles.tag}>{tag}</span>
          ))}
        </div>
      </div>
    );
  };

  const renderRequiredEnv = () => {
    if (!testCase.required_env || Object.keys(testCase.required_env).length === 0) {
      return renderField('运行环境', '-');
    }
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

  const renderCustomFields = () => {
    if (!testCase.custom_fields || Object.keys(testCase.custom_fields).length === 0) {
      return null;
    }
    return (
      <div style={styles.section}>
        <div style={styles.sectionHeader} onClick={() => toggleSection('custom')}>
          <span style={styles.sectionArrow}>{expandedSections.has('custom') ? '▼' : '▶'}</span>
          <span style={styles.sectionTitle}>自定义字段</span>
        </div>
        {expandedSections.has('custom') && (
          <div style={styles.sectionContent}>
            <pre style={styles.codeBlock}>{JSON.stringify(testCase.custom_fields, null, 2)}</pre>
          </div>
        )}
      </div>
    );
  };

  const renderAttachments = () => {
    if (!testCase.attachments || testCase.attachments.length === 0) {
      return null;
    }
    return (
      <div style={styles.section}>
        <div style={styles.sectionHeader} onClick={() => toggleSection('attachments')}>
          <span style={styles.sectionArrow}>{expandedSections.has('attachments') ? '▼' : '▶'}</span>
          <span style={styles.sectionTitle}>附件</span>
          <span style={styles.sectionCount}>({testCase.attachments.length}个)</span>
        </div>
        {expandedSections.has('attachments') && (
          <div style={styles.sectionContent}>
            <pre style={styles.codeBlock}>{JSON.stringify(testCase.attachments, null, 2)}</pre>
          </div>
        )}
      </div>
    );
  };

  const renderApprovalHistory = () => {
    if (!testCase.approval_history || testCase.approval_history.length === 0) {
      return null;
    }
    return (
      <div style={styles.section}>
        <div style={styles.sectionHeader} onClick={() => toggleSection('approval')}>
          <span style={styles.sectionArrow}>{expandedSections.has('approval') ? '▼' : '▶'}</span>
          <span style={styles.sectionTitle}>审批历史</span>
          <span style={styles.sectionCount}>({testCase.approval_history.length}条)</span>
        </div>
        {expandedSections.has('approval') && (
          <div style={styles.sectionContent}>
            <pre style={styles.codeBlock}>{JSON.stringify(testCase.approval_history, null, 2)}</pre>
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={styles.overlay} onClick={onClose} onKeyDown={(e) => e.key === 'Escape' && onClose()} tabIndex={0}>
      <div style={styles.modal} onClick={e => e.stopPropagation()}>
        <div style={styles.modalHeader}>
          <div>
            <span style={styles.caseId}>{testCase.case_id}</span>
            <h2 style={styles.modalTitle}>{testCase.title}</h2>
          </div>
          <div style={styles.headerActions}>
            {showEdit && (
              <button type="button" style={styles.editButton} onClick={onEdit}>
                编辑
              </button>
            )}
            <button type="button" style={styles.closeButton} onClick={onClose}>×</button>
          </div>
        </div>

        <div style={styles.modalBody}>
          {/* 基本信息 */}
          <div style={styles.section}>
            <div style={styles.sectionHeader} onClick={() => toggleSection('basic')}>
              <span style={styles.sectionArrow}>{expandedSections.has('basic') ? '▼' : '▶'}</span>
              <span style={styles.sectionTitle}>基本信息</span>
            </div>
            {expandedSections.has('basic') && (
              <div style={styles.sectionContent}>
                {renderInfoGrid(
                  <>
                    {renderField('用例ID', testCase.case_id)}
                    {renderField('关联需求ID', testCase.ref_req_id)}
                    {renderField('版本', `v${testCase.version}`)}
                    {renderField('状态', CASE_STATUS_LABELS[testCase.status] || testCase.status)}
                    {renderField('是否激活', testCase.is_active ? '是' : '否')}
                    {renderField('优先级', testCase.priority || '-')}
                    {renderField('测试类别', testCase.test_category || '-')}
                    {renderField('风险等级', testCase.risk_level || '-')}
                  </>
                )}
                {renderInfoGrid(
                  <>
                    {renderField('是否破坏性测试', testCase.is_destructive ? '是' : '否')}
                    {renderField('是否需要自动化', testCase.is_need_auto ? '是' : '否')}
                    {renderField('是否已自动化', testCase.is_automated ? '是' : '否')}
                    {renderField('保密级别', testCase.confidentiality || '-')}
                    {renderField('可见范围', testCase.visibility_scope || '-')}
                    {renderField('预计时长', testCase.estimated_duration_sec ? `${testCase.estimated_duration_sec}秒` : '-')}
                  </>
                )}
              </div>
            )}
          </div>

          {/* 人员信息 */}
          <div style={styles.section}>
            <div style={styles.sectionHeader} onClick={() => toggleSection('person')}>
              <span style={styles.sectionArrow}>{expandedSections.has('person') ? '▼' : '▶'}</span>
              <span style={styles.sectionTitle}>人员信息</span>
            </div>
            {expandedSections.has('person') && (
              <div style={styles.sectionContent}>
                {renderInfoGrid(
                  <>
                    {renderField('负责人ID', testCase.owner_id || '-')}
                    {renderField('审核人ID', testCase.reviewer_id || '-')}
                    {renderField('自动化开发ID', testCase.auto_dev_id || '-')}
                  </>
                )}
              </div>
            )}
          </div>

          {/* 执行信息 */}
          <div style={styles.section}>
            <div style={styles.sectionHeader} onClick={() => toggleSection('exec')}>
              <span style={styles.sectionArrow}>{expandedSections.has('exec') ? '▼' : '▶'}</span>
              <span style={styles.sectionTitle}>执行信息</span>
            </div>
            {expandedSections.has('exec') && (
              <div style={styles.sectionContent}>
                {renderInfoGrid(
                  <>
                    {renderField('自动化类型', testCase.automation_type || '-')}
                    {renderField('脚本实体ID', testCase.script_entity_id || '-')}
                    {renderField('故障分析', testCase.failure_analysis || '-')}
                  </>
                )}
              </div>
            )}
          </div>

          {/* 前置/后置条件 */}
          <div style={styles.section}>
            <div style={styles.sectionHeader} onClick={() => toggleSection('condition')}>
              <span style={styles.sectionArrow}>{expandedSections.has('condition') ? '▼' : '▶'}</span>
              <span style={styles.sectionTitle}>前置/后置条件</span>
            </div>
            {expandedSections.has('condition') && (
              <div style={styles.sectionContent}>
                {renderInfoGrid(
                  <>
                    {renderField('前置条件', testCase.pre_condition || '-')}
                    {renderField('后置条件', testCase.post_condition || '-')}
                  </>
                )}
              </div>
            )}
          </div>

          {/* 自动化关联 */}
          {testCase.automation_case_ref && (
            <div style={styles.section}>
              <div style={styles.sectionHeader} onClick={() => toggleSection('automation')}>
                <span style={styles.sectionArrow}>{expandedSections.has('automation') ? '▼' : '▶'}</span>
                <span style={styles.sectionTitle}>自动化关联</span>
              </div>
              {expandedSections.has('automation') && (
                <div style={styles.sectionContent}>
                  {renderInfoGrid(
                    <>
                      {renderField('自动化用例ID', testCase.automation_case_ref.auto_case_id)}
                      {renderField('版本', testCase.automation_case_ref.version || '-')}
                    </>
                  )}
                </div>
              )}
            </div>
          )}

          {/* 标签和运行环境 */}
          <div style={styles.section}>
            <div style={styles.sectionHeader} onClick={() => toggleSection('meta')}>
              <span style={styles.sectionArrow}>{expandedSections.has('meta') ? '▼' : '▶'}</span>
              <span style={styles.sectionTitle}>标签与运行环境</span>
            </div>
            {expandedSections.has('meta') && (
              <div style={styles.sectionContent}>
                {renderInfoGrid(renderTags())}
                {renderInfoGrid(renderRequiredEnv())}
              </div>
            )}
          </div>

          {/* 变更日志 */}
          {testCase.change_log && (
            <div style={styles.section}>
              <div style={styles.sectionHeader} onClick={() => toggleSection('changelog')}>
                <span style={styles.sectionArrow}>{expandedSections.has('changelog') ? '▼' : '▶'}</span>
                <span style={styles.sectionTitle}>变更日志</span>
              </div>
              {expandedSections.has('changelog') && (
                <div style={styles.sectionContent}>
                  <div style={styles.changeLog}>{testCase.change_log}</div>
                </div>
              )}
            </div>
          )}

          {/* 弃用信息 */}
          {testCase.deprecation_reason && (
            <div style={styles.section}>
              <div style={styles.sectionHeader} onClick={() => toggleSection('deprecate')}>
                <span style={styles.sectionArrow}>{expandedSections.has('deprecate') ? '▼' : '▶'}</span>
                <span style={styles.sectionTitle}>弃用信息</span>
              </div>
              {expandedSections.has('deprecate') && (
                <div style={styles.sectionContent}>
                  {renderField('弃用原因', testCase.deprecation_reason)}
                </div>
              )}
            </div>
          )}

          {/* 自定义字段 */}
          {renderCustomFields()}

          {/* 附件 */}
          {renderAttachments()}

          {/* 审批历史 */}
          {renderApprovalHistory()}

          {/* 时间戳 */}
          <div style={styles.section}>
            <div style={styles.sectionHeader} onClick={() => toggleSection('time')}>
              <span style={styles.sectionArrow}>{expandedSections.has('time') ? '▼' : '▶'}</span>
              <span style={styles.sectionTitle}>时间戳</span>
            </div>
            {expandedSections.has('time') && (
              <div style={styles.sectionContent}>
                {renderInfoGrid(
                  <>
                    {renderField('创建时间', formatDate(testCase.created_at))}
                    {renderField('更新时间', formatDate(testCase.updated_at))}
                  </>
                )}
              </div>
            )}
          </div>
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
  } as const,
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flexShrink: 0,
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
  modalBody: {
    padding: '16px 24px',
    overflowY: 'auto' as const,
    flex: 1,
  } as const,
  section: {
    marginBottom: '12px',
    border: '1px solid var(--border-muted)',
    borderRadius: '8px',
    overflow: 'hidden',
  } as const,
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 16px',
    backgroundColor: 'var(--bg-secondary)',
    cursor: 'pointer',
    transition: 'background-color var(--transition-fast)',
    userSelect: 'none' as const,
  } as const,
  sectionArrow: {
    fontSize: '10px',
    color: 'var(--text-muted)',
    width: '12px',
  } as const,
  sectionTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  } as const,
  sectionCount: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    fontWeight: 400,
  } as const,
  sectionContent: {
    padding: '16px',
    backgroundColor: 'var(--bg-primary)',
  } as const,
  infoGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '12px',
    marginBottom: '12px',
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
  changeLog: {
    padding: '12px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: '6px',
    fontSize: '13px',
    color: 'var(--text-secondary)',
    whiteSpace: 'pre-wrap' as const,
    lineHeight: 1.6,
  } as const,
  codeBlock: {
    margin: 0,
    padding: '12px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: '6px',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    overflow: 'auto' as const,
    maxHeight: '200px',
  } as const,
};

export default TestCaseDetailModal;