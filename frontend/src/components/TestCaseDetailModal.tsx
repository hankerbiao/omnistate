import type { TestCaseResponse } from '../types';

interface TestCaseDetailModalProps {
  testCase: TestCaseResponse;
  onClose: () => void;
}

const TestCaseDetailModal: React.FC<TestCaseDetailModalProps> = ({ testCase, onClose }) => {
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  const renderField = (label: string, value: React.ReactNode) => {
    if (value === undefined || value === null || value === '' || (Array.isArray(value) && value.length === 0) || (typeof value === 'object' && Object.keys(value).length === 0)) {
      return null;
    }
    return (
      <div style={styles.field}>
        <span style={styles.fieldLabel}>{label}</span>
        <span style={styles.fieldValue}>{value}</span>
      </div>
    );
  };

  const renderArrayField = (label: string, value: unknown[]) => {
    if (!value || value.length === 0) return null;
    return (
      <div style={styles.field}>
        <span style={styles.fieldLabel}>{label}</span>
        <div style={styles.tagContainer}>
          {value.map((item, index) => (
            <span key={index} style={styles.tag}>{String(item)}</span>
          ))}
        </div>
      </div>
    );
  };

  const renderObjectField = (label: string, value: Record<string, unknown>) => {
    if (!value || Object.keys(value).length === 0) return null;
    return (
      <div style={styles.field}>
        <span style={styles.fieldLabel}>{label}</span>
        <pre style={styles.codeBlock}>{JSON.stringify(value, null, 2)}</pre>
      </div>
    );
  };

  const renderAutomationRef = () => {
    if (!testCase.automation_case_ref) return null;
    const ref = testCase.automation_case_ref;
    return (
      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>自动化关联</h3>
        {renderField('自动化用例ID', ref.auto_case_id)}
        {renderField('版本', ref.version)}
      </div>
    );
  };

  const renderApprovalHistory = () => {
    if (!testCase.approval_history || testCase.approval_history.length === 0) return null;
    return (
      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>审批历史</h3>
        <pre style={styles.codeBlock}>{JSON.stringify(testCase.approval_history, null, 2)}</pre>
      </div>
    );
  };

  return (
    <div style={styles.overlay} onClick={handleOverlayClick}>
      <div style={styles.modal}>
        <div style={styles.modalHeader}>
          <div>
            <span style={styles.caseId}>{testCase.case_id}</span>
            <h2 style={styles.modalTitle}>{testCase.title}</h2>
          </div>
          <button style={styles.closeButton} onClick={onClose}>
            ×
          </button>
        </div>

        <div style={styles.modalBody}>
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>基本信息</h3>
            {renderField('用例ID', testCase.case_id)}
            {renderField('关联需求ID', testCase.ref_req_id)}
            {renderField('版本', `v${testCase.version}`)}
            {renderField('状态', testCase.status)}
            {renderField('是否激活', testCase.is_active ? '是' : '否')}
            {renderField('优先级', testCase.priority || '-')}
            {renderField('测试类别', testCase.test_category || '-')}
            {renderField('是否破坏性测试', testCase.is_destructive ? '是' : '否')}
            {renderField('是否需要自动化', testCase.is_need_auto ? '是' : '否')}
            {renderField('是否已自动化', testCase.is_automated ? '是' : '否')}
          </div>

          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>人员信息</h3>
            {renderField('负责人ID', testCase.owner_id || '-')}
            {renderField('审核人ID', testCase.reviewer_id || '-')}
            {renderField('自动化开发ID', testCase.auto_dev_id || '-')}
          </div>

          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>执行信息</h3>
            {renderField('自动化类型', testCase.automation_type || '-')}
            {renderField('脚本实体ID', testCase.script_entity_id || '-')}
            {renderField('风险等级', testCase.risk_level || '-')}
            {renderField('故障分析', testCase.failure_analysis || '-')}
            {renderField('保密级别', testCase.confidentiality || '-')}
            {renderField('可见范围', testCase.visibility_scope || '-')}
            {renderField('预计时长(秒)', testCase.estimated_duration_sec ? `${testCase.estimated_duration_sec}秒` : '-')}
          </div>

          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>前置/后置条件</h3>
            {renderField('前置条件', testCase.pre_condition || '-')}
            {renderField('后置条件', testCase.post_condition || '-')}
          </div>

          {renderArrayField('标签', testCase.tags)}
          {renderAutomationRef()}

          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>变更日志</h3>
            <div style={styles.changeLog}>
              {testCase.change_log || '无'}
            </div>
          </div>

          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>弃用信息</h3>
            {renderField('弃用原因', testCase.deprecation_reason || '-')}
          </div>

          {renderObjectField('运行环境', testCase.required_env)}
          {renderObjectField('自定义字段', testCase.custom_fields)}
          {renderApprovalHistory()}

          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>附件</h3>
            {testCase.attachments && testCase.attachments.length > 0 ? (
              <pre style={styles.codeBlock}>{JSON.stringify(testCase.attachments, null, 2)}</pre>
            ) : (
              <span style={styles.noData}>无附件</span>
            )}
          </div>

          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>时间信息</h3>
            {renderField('创建时间', formatDate(testCase.created_at))}
            {renderField('更新时间', formatDate(testCase.updated_at))}
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
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '20px',
  },
  modal: {
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    width: '100%',
    maxWidth: '800px',
    maxHeight: '90vh',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column' as const,
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '16px',
    padding: '24px',
    borderBottom: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-tertiary)',
  },
  caseId: {
    fontSize: '13px',
    color: 'var(--accent-cyan)',
    fontFamily: 'monospace',
    display: 'block',
    marginBottom: '4px',
  },
  modalTitle: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 700,
    color: 'var(--text-primary)',
  },
  closeButton: {
    fontSize: '28px',
    color: 'var(--text-muted)',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    padding: '0',
    lineHeight: 1,
    transition: 'color var(--transition-fast)',
  },
  modalBody: {
    padding: '24px',
    overflowY: 'auto' as const,
    flex: 1,
  },
  section: {
    marginBottom: '24px',
  },
  sectionTitle: {
    margin: '0 0 12px',
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  field: {
    display: 'grid',
    gridTemplateColumns: '140px 1fr',
    gap: '12px',
    padding: '8px 0',
    borderBottom: '1px solid rgba(255,255,255,0.04)',
  },
  fieldLabel: {
    fontSize: '13px',
    color: 'var(--text-muted)',
  },
  fieldValue: {
    fontSize: '14px',
    color: 'var(--text-primary)',
    wordBreak: 'break-word' as const,
  },
  tagContainer: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '6px',
  },
  tag: {
    padding: '4px 10px',
    backgroundColor: 'var(--bg-tertiary)',
    borderRadius: '999px',
    fontSize: '12px',
    color: 'var(--text-secondary)',
  },
  codeBlock: {
    margin: 0,
    padding: '12px',
    backgroundColor: 'var(--bg-primary)',
    borderRadius: 'var(--radius-md)',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    overflow: 'auto' as const,
    maxHeight: '200px',
  },
  changeLog: {
    padding: '12px',
    backgroundColor: 'var(--bg-primary)',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
    color: 'var(--text-secondary)',
    whiteSpace: 'pre-wrap' as const,
  },
  noData: {
    fontSize: '13px',
    color: 'var(--text-muted)',
    fontStyle: 'italic' as const,
  },
};

export default TestCaseDetailModal;