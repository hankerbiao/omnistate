import React from 'react';
import type { RequirementResponse } from '../types';
import { WorkflowPanel, WorkflowActionToolbar } from './workflow';
import { getStateLabel, getWorkflowStateStyle } from '../constants/workflowLabels';

// ─── 附件工具函数 ────────────────────────────────────────────────────────────

/** 格式化文件大小 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** 根据 MIME 类型返回图标 emoji */
function getFileIcon(contentType: string): string {
  if (contentType.startsWith('image/')) return '🖼️';
  if (contentType === 'application/pdf') return '📄';
  if (contentType.startsWith('text/')) return '📝';
  if (contentType.includes('zip') || contentType.includes('tar') || contentType.includes('gzip')) return '🗜️';
  if (contentType.includes('spreadsheet') || contentType.includes('excel')) return '📊';
  if (contentType.includes('word') || contentType.includes('document')) return '📃';
  return '📎';
}

/** 将 storage_path 转成可下载/预览的 URL（按实际后端路径调整） */
function getAttachmentUrl(storagePath: string): string {
  return `/api/v1/attachments/download?path=${encodeURIComponent(storagePath)}`;
}

/** 需求分类标签映射 */
const CATEGORY_LABELS: Record<string, string> = {
  FUNCTIONAL: '功能测试',
  PERFORMANCE: '性能测试',
  STABILITY: '稳定性测试',
  COMPATIBILITY: '兼容性测试',
  SECURITY: '安全测试',
  REGRESSION: '回归测试',
};

/** 需求来源标签映射 */
const SOURCE_LABELS: Record<string, string> = {
  CUSTOMER: '客户需求',
  INTERNAL: '内部需求',
  BUG: '缺陷驱动',
  SPEC: '规格驱动',
  REGULATION: '合规要求',
};

/** 分类颜色映射 */
const CATEGORY_COLORS: Record<string, { bg: string; color: string }> = {
  FUNCTIONAL: { bg: 'rgba(88, 166, 255, 0.15)', color: '#58a6ff' },
  PERFORMANCE: { bg: 'rgba(255, 123, 114, 0.15)', color: '#ff7b72' },
  STABILITY: { bg: 'rgba(121, 192, 255, 0.15)', color: '#79c0ff' },
  COMPATIBILITY: { bg: 'rgba(187, 128, 9, 0.15)', color: '#bb8009' },
  SECURITY: { bg: 'rgba(219, 69, 55, 0.15)', color: '#db4537' },
  REGRESSION: { bg: 'rgba(163, 113, 247, 0.15)', color: '#a371f7' },
};

/** 复制到剪贴板 */
function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {/* 静默失败 */});
}

interface RequirementDetailModalProps {
  requirement: RequirementResponse;
  onClose: () => void;
  onUpdated?: () => void;
}

const RequirementDetailModal: React.FC<RequirementDetailModalProps> = ({ requirement, onClose, onUpdated }) => {
  const [workflowRefreshSignal, setWorkflowRefreshSignal] = React.useState(0);
  const [expandedSections, setExpandedSections] = React.useState<Set<string>>(new Set([
    'workflowActions', 'basic', 'desc', 'schedule', 'people', 'components', 'params', 'attachments', 'time',
  ]));
  const [tagsExpanded, setTagsExpanded] = React.useState(false);

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const handleWorkflowUpdated = () => {
    onUpdated?.();
    setWorkflowRefreshSignal((n) => n + 1);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  const formatDateShort = (dateStr?: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('zh-CN');
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

  /** 带复制按钮的字段 */
  const renderCopyableField = (label: string, value: string | undefined) => {
    if (!value) return renderField(label, '-');
    return (
      <div style={styles.infoRow}>
        <span style={styles.infoLabel}>{label}</span>
        <div style={styles.copyableRow}>
          <span style={styles.infoValueMono}>{value}</span>
          <button style={styles.copyBtn} onClick={() => copyToClipboard(value)} title="复制">📋</button>
        </div>
      </div>
    );
  };

  /** 人员字段：优先显示姓名，悬停显示 ID */
  const renderPersonField = (label: string, name?: string, id?: string) => {
    const displayName = name || id || '-';
    return (
      <div style={styles.infoRow}>
        <span style={styles.infoLabel}>{label}</span>
        <span style={styles.infoValue} title={id || undefined}>{displayName}</span>
      </div>
    );
  };

  // 解析分类
  const categoryLabel = requirement.category ? (CATEGORY_LABELS[requirement.category] || requirement.category) : null;
  const categoryStyle = requirement.category ? CATEGORY_COLORS[requirement.category] : null;

  // 解析来源
  const sourceLabel = requirement.source ? (SOURCE_LABELS[requirement.source] || requirement.source) : null;

  // 版本展示：优先 baseline/target，fallback 到 firmware
  const hasDualVersion = requirement.baseline_version || requirement.target_version;

  // 标签展示
  const displayTags = tagsExpanded ? requirement.tags : requirement.tags.slice(0, 6);

  return (
    <div style={styles.overlay} onClick={onClose} onKeyDown={(e) => e.key === 'Escape' && onClose()} tabIndex={0}>
      <div style={styles.modal} onClick={e => e.stopPropagation()}>
        {/* ─── Header ─── */}
        <div style={styles.modalHeader}>
          <div style={styles.modalHeaderMain}>
            <div style={styles.headerBadges}>
              <span style={styles.reqId}>{requirement.req_id}</span>
              {categoryLabel && categoryStyle && (
                <span style={{ ...styles.categoryBadge, backgroundColor: categoryStyle.bg, color: categoryStyle.color }}>
                  {categoryLabel}
                </span>
              )}
              <span className="status-badge" style={{ ...getWorkflowStateStyle(requirement.status), fontSize: '11px', padding: '2px 8px' }}>
                {getStateLabel(requirement.status, 'REQUIREMENT')}
              </span>
              <span style={styles.priorityBadge}>{requirement.priority}</span>
            </div>
            <h2 style={styles.modalTitle}>{requirement.title}</h2>
          </div>
          <div style={styles.headerActions}>
            {requirement.workflow_item_id && (
              <WorkflowActionToolbar
                workflowItemId={requirement.workflow_item_id}
                typeCode="REQUIREMENT"
                defaultPriority={requirement.priority}
                onTransitionSuccess={handleWorkflowUpdated}
                compact
                showStateBadge
              />
            )}
            <button style={styles.closeButton} onClick={onClose}>×</button>
          </div>
        </div>

        <div style={styles.modalBody}>
          {/* ─── 工作流流转 ─── */}
          {requirement.workflow_item_id && (
            <div style={styles.section}>
              <div style={styles.sectionHeader} onClick={() => toggleSection('workflowActions')}>
                <span style={styles.sectionArrow}>{expandedSections.has('workflowActions') ? '▼' : '▶'}</span>
                <span style={styles.sectionTitle}>工作流流转</span>
              </div>
              {expandedSections.has('workflowActions') && (
                <div style={styles.sectionContent}>
                  <WorkflowPanel
                    workflowItemId={requirement.workflow_item_id}
                    entityLabel={`${requirement.req_id} · ${requirement.title}`}
                    typeCode="REQUIREMENT"
                    defaultPriority={requirement.priority}
                    creatorName={requirement.creator_name || requirement.creator}
                    currentOwnerName={requirement.current_owner_name || requirement.current_owner}
                    createdAt={requirement.created_at}
                    updatedAt={requirement.updated_at}
                    compact
                    hideToolbar
                    refreshSignal={workflowRefreshSignal}
                    onTransitionSuccess={handleWorkflowUpdated}
                  />
                </div>
              )}
            </div>
          )}

          {/* ─── 基本信息 ─── */}
          <div style={styles.section}>
            <div style={styles.sectionHeader} onClick={() => toggleSection('basic')}>
              <span style={styles.sectionArrow}>{expandedSections.has('basic') ? '▼' : '▶'}</span>
              <span style={styles.sectionTitle}>基本信息</span>
            </div>
            {expandedSections.has('basic') && (
              <div style={styles.sectionContent}>
                <div style={styles.infoGrid}>
                  {renderCopyableField('需求ID', requirement.req_id)}
                  {renderField('优先级', requirement.priority)}
                  {renderField('分类', categoryLabel)}
                  {renderField('来源', sourceLabel)}
                  {renderField('版本', hasDualVersion
                    ? <span style={styles.versionRange}>
                        <span style={styles.versionLabel}>基线</span>
                        <span style={styles.versionValue}>{requirement.baseline_version || '-'}</span>
                        <span style={styles.versionArrow}>→</span>
                        <span style={styles.versionLabel}>目标</span>
                        <span style={styles.versionValue}>{requirement.target_version || '-'}</span>
                      </span>
                    : requirement.firmware_version || '-'
                  )}
                  {renderField('关联用例数', requirement.case_count > 0
                    ? <span style={styles.caseCountBadge}>{requirement.case_count} 条</span>
                    : '暂无'
                  )}
                </div>
                {/* 标签行 */}
                {requirement.tags && requirement.tags.length > 0 && (
                  <div style={styles.tagsRow}>
                    <span style={styles.infoLabel}>标签</span>
                    <div style={styles.tagList}>
                      {displayTags.map((tag, idx) => (
                        <span key={idx} style={styles.tag}>{tag}</span>
                      ))}
                      {requirement.tags.length > 6 && (
                        <span
                          style={styles.tagMore}
                          onClick={() => setTagsExpanded(!tagsExpanded)}
                          role="button"
                          tabIndex={0}
                        >
                          {tagsExpanded ? '收起' : `+${requirement.tags.length - 6}`}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ─── 描述 & 验收标准 ─── */}
          <div style={styles.section}>
            <div style={styles.sectionHeader} onClick={() => toggleSection('desc')}>
              <span style={styles.sectionArrow}>{expandedSections.has('desc') ? '▼' : '▶'}</span>
              <span style={styles.sectionTitle}>描述 & 验收标准</span>
            </div>
            {expandedSections.has('desc') && (
              <div style={styles.sectionContent}>
                <div style={styles.descSection}>
                  <div style={styles.descItem}>
                    <span style={styles.descLabel}>需求描述</span>
                    <div style={styles.descContent}>
                      {requirement.description || '无'}
                    </div>
                  </div>
                  <div style={styles.descItem}>
                    <span style={styles.descLabel}>验收标准</span>
                    <div style={{
                      ...styles.descContent,
                      ...(requirement.acceptance_criteria ? {} : styles.descContentEmpty),
                    }}>
                      {requirement.acceptance_criteria || '未设定'}
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

          {/* ─── 计划时间 ─── */}
          <div style={styles.section}>
            <div style={styles.sectionHeader} onClick={() => toggleSection('schedule')}>
              <span style={styles.sectionArrow}>{expandedSections.has('schedule') ? '▼' : '▶'}</span>
              <span style={styles.sectionTitle}>计划时间</span>
            </div>
            {expandedSections.has('schedule') && (
              <div style={styles.sectionContent}>
                <div style={styles.infoGrid}>
                  {renderField('计划开始', formatDateShort(requirement.planned_start_date))}
                  {renderField('计划结束', formatDateShort(requirement.planned_end_date))}
                  {renderField('创建时间', formatDate(requirement.created_at))}
                  {renderField('更新时间', formatDate(requirement.updated_at))}
                </div>
              </div>
            )}
          </div>

          {/* ─── 人员信息 ─── */}
          <div style={styles.section}>
            <div style={styles.sectionHeader} onClick={() => toggleSection('people')}>
              <span style={styles.sectionArrow}>{expandedSections.has('people') ? '▼' : '▶'}</span>
              <span style={styles.sectionTitle}>人员信息</span>
            </div>
            {expandedSections.has('people') && (
              <div style={styles.sectionContent}>
                <div style={styles.infoGrid}>
                  {renderPersonField('TPM负责人', requirement.tpm_owner_name, requirement.tpm_owner_id)}
                  {renderPersonField('手工开发', requirement.manual_dev_name, requirement.manual_dev_id)}
                  {renderPersonField('自动化开发', requirement.auto_dev_name, requirement.auto_dev_id)}
                  {renderPersonField('创建人', requirement.creator_name, requirement.creator)}
                  {renderPersonField('当前负责人', requirement.current_owner_name, requirement.current_owner)}
                </div>
              </div>
            )}
          </div>

          {/* ─── 目标组件 ─── */}
          {requirement.target_components && requirement.target_components.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionHeader} onClick={() => toggleSection('components')}>
                <span style={styles.sectionArrow}>{expandedSections.has('components') ? '▼' : '▶'}</span>
                <span style={styles.sectionTitle}>目标组件</span>
                <span style={styles.sectionCount}>({requirement.target_components.length})</span>
              </div>
              {expandedSections.has('components') && (
                <div style={styles.sectionContent}>
                  <div style={styles.tagList}>
                    {requirement.target_components.map((comp, idx) => (
                      <span key={idx} style={styles.componentTag}>{comp}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ─── 关键参数 ─── */}
          {requirement.key_parameters && requirement.key_parameters.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionHeader} onClick={() => toggleSection('params')}>
                <span style={styles.sectionArrow}>{expandedSections.has('params') ? '▼' : '▶'}</span>
                <span style={styles.sectionTitle}>关键参数</span>
                <span style={styles.sectionCount}>({requirement.key_parameters.length})</span>
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

          {/* ─── 附件信息 ─── */}
          {requirement.attachments && requirement.attachments.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionHeader} onClick={() => toggleSection('attachments')}>
                <span style={styles.sectionArrow}>{expandedSections.has('attachments') ? '▼' : '▶'}</span>
                <span style={styles.sectionTitle}>附件</span>
                <span style={styles.sectionCount}>({requirement.attachments.length})</span>
              </div>
              {expandedSections.has('attachments') && (
                <div style={styles.sectionContent}>
                  <div style={styles.attachmentList}>
                    {requirement.attachments.map((att) => {
                      const a = att as {
                        file_id?: string;
                        original_filename?: string;
                        storage_path?: string;
                        size?: number;
                        content_type?: string;
                        uploaded_by?: string;
                        uploaded_at?: string;
                      };
                      const name = a.original_filename ?? a.file_id ?? '未知文件';
                      const icon = getFileIcon(a.content_type ?? '');
                      const size = a.size != null ? formatFileSize(a.size) : '';
                      const url = a.storage_path ? getAttachmentUrl(a.storage_path) : undefined;
                      const isImage = a.content_type?.startsWith('image/');
                      return (
                        <div key={a.file_id ?? name} style={styles.attachmentCard}>
                          {isImage && url && (
                            <a href={url} target="_blank" rel="noopener noreferrer" style={styles.attachmentThumbLink}>
                              <img
                                src={url}
                                alt={name}
                                style={styles.attachmentThumb}
                                onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                              />
                            </a>
                          )}
                          <div style={styles.attachmentInfo}>
                            <div style={styles.attachmentName}>
                              <span style={styles.attachmentIcon}>{icon}</span>
                              {url ? (
                                <a href={url} target="_blank" rel="noopener noreferrer" style={styles.attachmentLink}>
                                  {name}
                                </a>
                              ) : (
                                <span style={styles.attachmentNameText}>{name}</span>
                              )}
                            </div>
                            <div style={styles.attachmentMeta}>
                              {size && <span style={styles.attachmentMetaItem}>{size}</span>}
                              {a.content_type && <span style={styles.attachmentMetaItem}>{a.content_type}</span>}
                              {a.uploaded_at && (
                                <span style={styles.attachmentMetaItem}>
                                  {new Date(a.uploaded_at).toLocaleString('zh-CN')}
                                </span>
                              )}
                              {a.uploaded_by && <span style={styles.attachmentMetaItem}>上传人：{a.uploaded_by}</span>}
                            </div>
                          </div>
                          {url && (
                            <a
                              href={url}
                              download={name}
                              style={styles.attachmentDownloadBtn}
                              title="下载"
                            >
                              ⬇
                            </a>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
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
    flex: 1,
    minWidth: 0,
  } as const,
  headerBadges: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '6px',
    flexWrap: 'wrap' as const,
  } as const,
  headerActions: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    flexShrink: 0,
  } as const,
  reqId: {
    fontSize: '13px',
    color: 'var(--accent-cyan)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  categoryBadge: {
    fontSize: '11px',
    padding: '2px 8px',
    borderRadius: '10px',
    fontWeight: 500,
  } as const,
  priorityBadge: {
    fontSize: '11px',
    padding: '2px 8px',
    borderRadius: '10px',
    backgroundColor: 'rgba(163, 113, 247, 0.15)',
    color: '#a371f7',
    fontWeight: 600,
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
    gap: '12px 24px',
  } as const,
  infoRow: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
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
  infoValueMono: {
    fontSize: '13px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-cyan)',
    wordBreak: 'break-all' as const,
  } as const,
  copyableRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  } as const,
  copyBtn: {
    fontSize: '12px',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    padding: '2px 4px',
    borderRadius: '3px',
    opacity: 0.6,
    transition: 'opacity 0.15s',
  } as const,
  // ─── 版本范围 ──────────────────────────────────────────────────────────
  versionRange: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '13px',
  } as const,
  versionLabel: {
    fontSize: '10px',
    color: 'var(--text-muted)',
    textTransform: 'uppercase' as const,
  } as const,
  versionValue: {
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--text-primary)',
    fontSize: '13px',
  } as const,
  versionArrow: {
    color: 'var(--text-muted)',
    fontSize: '12px',
  } as const,
  // ─── 标签 ──────────────────────────────────────────────────────────
  tagsRow: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    marginTop: '12px',
    paddingTop: '12px',
    borderTop: '1px solid var(--border-muted)',
  } as const,
  tagList: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '6px',
  } as const,
  tag: {
    fontSize: '12px',
    color: 'var(--accent-blue)',
    backgroundColor: 'rgba(88, 166, 255, 0.15)',
    padding: '3px 10px',
    borderRadius: '12px',
  } as const,
  tagMore: {
    fontSize: '12px',
    color: 'var(--accent-purple)',
    backgroundColor: 'rgba(163, 113, 247, 0.15)',
    padding: '3px 10px',
    borderRadius: '12px',
    cursor: 'pointer',
    border: 'none',
  } as const,
  componentTag: {
    fontSize: '12px',
    color: 'var(--accent-green)',
    backgroundColor: 'rgba(63, 185, 80, 0.15)',
    padding: '3px 10px',
    borderRadius: '12px',
  } as const,
  caseCountBadge: {
    fontSize: '12px',
    color: 'var(--accent-cyan)',
    backgroundColor: 'rgba(121, 192, 255, 0.15)',
    padding: '2px 8px',
    borderRadius: '10px',
    fontWeight: 500,
  } as const,
  // ─── 描述 ──────────────────────────────────────────────────────────
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
  descContentEmpty: {
    color: 'var(--text-muted)',
    fontStyle: 'italic' as const,
  } as const,
  // ─── 关键参数 ──────────────────────────────────────────────────────────
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
  // ─── 附件列表 ──────────────────────────────────────────────────────────
  attachmentList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  } as const,
  attachmentCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '10px 12px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: '8px',
    border: '1px solid var(--border-muted)',
    transition: 'background-color var(--transition-fast)',
  } as const,
  attachmentThumbLink: {
    flexShrink: 0,
  } as const,
  attachmentThumb: {
    width: '48px',
    height: '48px',
    objectFit: 'cover' as const,
    borderRadius: '4px',
    border: '1px solid var(--border-muted)',
  } as const,
  attachmentInfo: {
    flex: 1,
    minWidth: 0,
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
  } as const,
  attachmentName: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  } as const,
  attachmentIcon: {
    fontSize: '16px',
    flexShrink: 0,
  } as const,
  attachmentLink: {
    fontSize: '13px',
    color: 'var(--accent-blue)',
    textDecoration: 'none',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  } as const,
  attachmentNameText: {
    fontSize: '13px',
    color: 'var(--text-primary)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  } as const,
  attachmentMeta: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '8px',
  } as const,
  attachmentMetaItem: {
    fontSize: '11px',
    color: 'var(--text-muted)',
  } as const,
  attachmentDownloadBtn: {
    flexShrink: 0,
    fontSize: '16px',
    color: 'var(--text-muted)',
    textDecoration: 'none',
    padding: '4px 6px',
    borderRadius: '4px',
    transition: 'color var(--transition-fast)',
    cursor: 'pointer',
  } as const,
};

export default RequirementDetailModal;
