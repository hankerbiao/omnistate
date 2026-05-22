import React from 'react';
import type { RequirementResponse } from '../types';

interface RequirementDetailModalProps {
  requirement: RequirementResponse;
  onClose: () => void;
}

const STATUS_LABELS: Record<string, string> = {
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
  ACTIVE: '激活',
  INACTIVE: '未激活',
  DEPRECATED: '已弃用',
};

const RequirementDetailModal: React.FC<RequirementDetailModalProps> = ({ requirement, onClose }) => {
  const [expandedSections, setExpandedSections] = React.useState<Set<string>>(new Set([
    'basic', 'workflow', 'components', 'params', 'meta', 'time'
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

  return (
    <div style={styles.overlay} onClick={onClose} onKeyDown={(e) => e.key === 'Escape' && onClose()} tabIndex={0}>
      <div style={styles.modal} onClick={e => e.stopPropagation()}>
        <div style={styles.modalHeader}>
          <div>
            <span style={styles.reqId}>{requirement.req_id}</span>
            <h2 style={styles.modalTitle}>{requirement.title}</h2>
          </div>
          <button style={styles.closeButton} onClick={onClose}>×</button>
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
                <div style={styles.infoGrid}>
                  {renderField('需求ID', requirement.req_id)}
                  {renderField('状态', STATUS_LABELS[requirement.status] || requirement.status)}
                  {renderField('优先级', requirement.priority)}
                  {renderField('固件版本', requirement.firmware_version || '-')}
                  {renderField('工作流ID', requirement.workflow_item_id || '-')}
                </div>
              </div>
            )}
          </div>

          {/* 工作流信息 */}
          {(requirement.creator || requirement.creator_name || requirement.current_owner || requirement.current_owner_name) && (
            <div style={styles.section}>
              <div style={styles.sectionHeader} onClick={() => toggleSection('workflow')}>
                <span style={styles.sectionArrow}>{expandedSections.has('workflow') ? '▼' : '▶'}</span>
                <span style={styles.sectionTitle}>工作流信息</span>
              </div>
              {expandedSections.has('workflow') && (
                <div style={styles.sectionContent}>
                  <div style={styles.infoGrid}>
                    {renderField('创建人ID', requirement.creator || '-')}
                    {renderField('创建人名称', requirement.creator_name || '-')}
                    {renderField('当前负责人ID', requirement.current_owner || '-')}
                    {renderField('当前负责人名称', requirement.current_owner_name || '-')}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 目标组件 */}
          {requirement.target_components && requirement.target_components.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionHeader} onClick={() => toggleSection('components')}>
                <span style={styles.sectionArrow}>{expandedSections.has('components') ? '▼' : '▶'}</span>
                <span style={styles.sectionTitle}>目标组件</span>
              </div>
              {expandedSections.has('components') && (
                <div style={styles.sectionContent}>
                  <div style={styles.tagList}>
                    {requirement.target_components.map((comp, idx) => (
                      <span key={idx} style={styles.tag}>{comp}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 详细描述 */}
          <div style={styles.section}>
            <div style={styles.sectionHeader} onClick={() => toggleSection('basic')}>
              <span style={styles.sectionArrow}>{expandedSections.has('basic') ? '▼' : '▶'}</span>
              <span style={styles.sectionTitle}>描述信息</span>
            </div>
            {expandedSections.has('basic') && (
              <div style={styles.sectionContent}>
                <div style={styles.descSection}>
                  <div style={styles.descItem}>
                    <span style={styles.descLabel}>描述</span>
                    <div style={styles.descContent}>
                      {requirement.description || '无'}
                    </div>
                  </div>
                  <div style={styles.descItem}>
                    <span style={styles.descLabel}>技术规格</span>
                    <div style={styles.descContent}>
                      {requirement.technical_spec || '无'}
                    </div>
                  </div>
                  <div style={styles.descItem}>
                    <span style={styles.descLabel}>风险点</span>
                    <div style={styles.descContent}>
                      {requirement.risk_points || '无'}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 关键参数 */}
          {requirement.key_parameters && requirement.key_parameters.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionHeader} onClick={() => toggleSection('params')}>
                <span style={styles.sectionArrow}>{expandedSections.has('params') ? '▼' : '▶'}</span>
                <span style={styles.sectionTitle}>关键参数</span>
                <span style={styles.sectionCount}>({requirement.key_parameters.length}项)</span>
              </div>
              {expandedSections.has('params') && (
                <div style={styles.sectionContent}>
                  <div style={styles.paramsList}>
                    {requirement.key_parameters.map((param, idx) => (
                      <div key={idx} style={styles.paramCard}>
                        <div style={styles.paramHeader}>
                          <span style={styles.paramName}>{param.name}</span>
                        </div>
                        <div style={styles.paramBody}>
                          <span style={styles.infoLabel}>值</span>
                          <span style={styles.paramValue}>{param.value}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 人员信息 */}
          <div style={styles.section}>
            <div style={styles.sectionHeader} onClick={() => toggleSection('meta')}>
              <span style={styles.sectionArrow}>{expandedSections.has('meta') ? '▼' : '▶'}</span>
              <span style={styles.sectionTitle}>人员信息</span>
            </div>
            {expandedSections.has('meta') && (
              <div style={styles.sectionContent}>
                <div style={styles.infoGrid}>
                  {renderField('TPM负责人', requirement.tpm_owner_id)}
                  {renderField('手工开发ID', requirement.manual_dev_id || '-')}
                  {renderField('自动化开发ID', requirement.auto_dev_id || '-')}
                </div>
              </div>
            )}
          </div>

          {/* 附件信息 */}
          {requirement.attachments && requirement.attachments.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionHeader} onClick={() => toggleSection('attachments')}>
                <span style={styles.sectionArrow}>{expandedSections.has('attachments') ? '▼' : '▶'}</span>
                <span style={styles.sectionTitle}>附件</span>
                <span style={styles.sectionCount}>({requirement.attachments.length}个)</span>
              </div>
              {expandedSections.has('attachments') && (
                <div style={styles.sectionContent}>
                  <pre style={styles.codeBlock}>{JSON.stringify(requirement.attachments, null, 2)}</pre>
                </div>
              )}
            </div>
          )}

          {/* 时间戳 */}
          <div style={styles.section}>
            <div style={styles.sectionHeader} onClick={() => toggleSection('time')}>
              <span style={styles.sectionArrow}>{expandedSections.has('time') ? '▼' : '▶'}</span>
              <span style={styles.sectionTitle}>时间戳</span>
            </div>
            {expandedSections.has('time') && (
              <div style={styles.sectionContent}>
                <div style={styles.infoGrid}>
                  {renderField('创建时间', formatDate(requirement.created_at))}
                  {renderField('更新时间', formatDate(requirement.updated_at))}
                </div>
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
  reqId: {
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
    gap: '8px',
  } as const,
  tag: {
    fontSize: '12px',
    color: 'var(--accent-blue)',
    backgroundColor: 'rgba(88, 166, 255, 0.15)',
    padding: '4px 10px',
    borderRadius: '12px',
  } as const,
  descSection: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '16px',
  } as const,
  descItem: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '6px',
  } as const,
  descLabel: {
    fontSize: '11px',
    fontWeight: 500,
    color: 'var(--text-muted)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  } as const,
  descContent: {
    fontSize: '13px',
    color: 'var(--text-primary)',
    whiteSpace: 'pre-wrap' as const,
    lineHeight: 1.6,
    padding: '12px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: '6px',
  } as const,
  paramsList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  } as const,
  paramCard: {
    padding: '12px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: '6px',
    border: '1px solid var(--border-muted)',
  } as const,
  paramHeader: {
    marginBottom: '8px',
  } as const,
  paramName: {
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-purple)',
  } as const,
  paramBody: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '2px',
  } as const,
  paramValue: {
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--text-primary)',
    wordBreak: 'break-all' as const,
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

export default RequirementDetailModal;