import React from 'react';
import type { RequirementResponse } from '../types';
import { WorkflowPanel, WorkflowActionToolbar } from './workflow';
import WorkflowCurrentStateBadge from './workflow/WorkflowCurrentStateBadge';
import { rdmStyles as styles } from './RequirementDetailModal.styles';
import { Dialog, DialogContent } from './ui/dialog';

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

type DetailTab = 'details' | 'components' | 'attachmentsTab' | 'workflow';

interface RequirementDetailModalProps {
  requirement: RequirementResponse;
  onClose: () => void;
  onUpdated?: () => void;
}

const RequirementDetailModal: React.FC<RequirementDetailModalProps> = ({ requirement, onClose, onUpdated }) => {
  const [activeTab, setActiveTab] = React.useState<DetailTab>('details');
  const [workflowRefreshSignal, setWorkflowRefreshSignal] = React.useState(0);

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

  // 解析分类
  const categoryLabel = requirement.category ? (CATEGORY_LABELS[requirement.category] || requirement.category) : null;
  const categoryStyle = requirement.category ? CATEGORY_COLORS[requirement.category] : null;

  // 解析来源
  const sourceLabel = requirement.source ? (SOURCE_LABELS[requirement.source] || requirement.source) : null;

  // 版本展示
  const hasDualVersion = requirement.baseline_version || requirement.target_version;

  const tags = requirement.tags ?? [];
  const hasParams = requirement.key_parameters && requirement.key_parameters.length > 0;
  const hasComponents = requirement.target_components && requirement.target_components.length > 0;
  const hasAttachments = requirement.attachments && requirement.attachments.length > 0;
  const hasWorkflow = Boolean(requirement.workflow_item_id);

  // ─── Left sidebar summary ───
  const sidebarPersonCard = (label: string, name?: string, id?: string) => {
    if (!name && !id) return null;
    const displayName = name || id || '';
    return (
      <div style={styles.sidePersonCard}>
        <span style={styles.sidePersonRole}>{label}</span>
        <span style={styles.sidePersonName} title={id || undefined}>{displayName}</span>
      </div>
    );
  };

  // ─── Right tab content ───
  const detailsContent = (
    <>
      {/* 需求描述 */}
      <div style={styles.textBlock}>
        <span style={styles.textBlockTitle}>需求描述</span>
        <div style={styles.textBlockContent}>
          {requirement.description || '无'}
        </div>
      </div>

      {/* 验收标准 */}
      <div style={styles.textBlock}>
        <span style={styles.textBlockTitle}>验收标准</span>
        <div style={{
          ...styles.textBlockContent,
          ...(requirement.acceptance_criteria ? {} : styles.textBlockEmpty),
        }}>
          {requirement.acceptance_criteria || '未设定'}
        </div>
      </div>

      {/* 风险点 */}
      {requirement.risk_points && (
        <div style={styles.textBlock}>
          <span style={styles.textBlockTitle}>风险点</span>
          <div style={styles.textBlockContent}>{requirement.risk_points}</div>
        </div>
      )}
    </>
  );

  const componentsContent = (
    <>
      {hasComponents && (
        <div style={styles.componentSection}>
          <span style={styles.subTitle}>目标组件</span>
          <div style={styles.tagList}>
            {requirement.target_components!.map((comp, idx) => (
              <span key={idx} style={styles.compTag}>{comp}</span>
            ))}
          </div>
        </div>
      )}

      {hasParams && (
        <div style={styles.componentSection}>
          <span style={styles.subTitle}>关键参数</span>
          <div style={styles.paramsGrid}>
            {requirement.key_parameters!.map((param, idx) => (
              <div key={idx} style={styles.paramCard}>
                <span style={styles.paramName}>{param.name}</span>
                <span style={styles.paramValue}>{param.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {!hasComponents && !hasParams && (
        <p style={styles.emptyHint}>暂无目标组件与关键参数</p>
      )}
    </>
  );

  const attachmentsContent = hasAttachments ? (
    <div style={styles.attachmentGrid}>
      {requirement.attachments!.map((att) => {
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
              <a href={url} target="_blank" rel="noopener noreferrer" style={styles.attachThumbLink}>
                <img
                  src={url}
                  alt={name}
                  style={styles.attachThumb}
                  onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                />
              </a>
            )}
            <div style={styles.attachInfo}>
              <div style={styles.attachName}>
                <span style={styles.attachIcon}>{icon}</span>
                {url ? (
                  <a href={url} target="_blank" rel="noopener noreferrer" style={styles.attachLink}>{name}</a>
                ) : (
                  <span style={styles.attachNameText}>{name}</span>
                )}
              </div>
              <div style={styles.attachMeta}>
                {size && <span>{size}</span>}
                {a.content_type && <span>{a.content_type}</span>}
                {a.uploaded_at && <span>{new Date(a.uploaded_at).toLocaleString('zh-CN')}</span>}
                {a.uploaded_by && <span>上传人：{a.uploaded_by}</span>}
              </div>
            </div>
            {url && (
              <a href={url} download={name} style={styles.attachDownloadBtn} title="下载">⬇</a>
            )}
          </div>
        );
      })}
    </div>
  ) : (
    <p style={styles.emptyHint}>暂无附件</p>
  );

  const workflowContent = hasWorkflow ? (
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
  ) : (
    <p style={styles.emptyHint}>此需求未关联工作流</p>
  );

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-[960px] max-h-[90vh] flex flex-col p-0 gap-0" style={{ borderRadius: 12, overflow: 'hidden' }}>
        {/* ─── Header ─── */}
        <div style={styles.modalHeader}>
          <div style={styles.modalHeaderMain}>
            <div style={styles.headerBadges}>
              <span style={styles.reqId}>{requirement.req_id}</span>
              {categoryLabel && categoryStyle && (
                <span style={{ ...styles.headerBadge, backgroundColor: categoryStyle.bg, color: categoryStyle.color }}>
                  {categoryLabel}
                </span>
              )}
              {sourceLabel && (
                <span style={{ ...styles.headerBadge, backgroundColor: 'rgba(139, 148, 158, 0.15)', color: 'var(--text-secondary)' }}>
                  {sourceLabel}
                </span>
              )}
              <WorkflowCurrentStateBadge
                state={requirement.status}
                typeCode="REQUIREMENT"
                variant="compact"
              />
              <span style={{ ...styles.headerBadge, backgroundColor: 'rgba(163, 113, 247, 0.15)', color: '#a371f7', fontWeight: 600 }}>
                {requirement.priority}
              </span>
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
                showStateBadge={false}
              />
            )}
          </div>
        </div>

        {/* ─── Split body ─── */}
        <div style={styles.splitBody}>
          {/* ── Left sidebar ── */}
          <aside style={styles.sidebar}>
            {/* 人员 */}
            <div style={styles.sidePersonGroup}>
              {sidebarPersonCard('TPM 负责人', requirement.tpm_owner_name, requirement.tpm_owner_id)}
              {sidebarPersonCard('手工开发', requirement.manual_dev_name, requirement.manual_dev_id)}
              {sidebarPersonCard('自动化开发', requirement.auto_dev_name, requirement.auto_dev_id)}
              {sidebarPersonCard('创建人', requirement.creator_name, requirement.creator)}
              {sidebarPersonCard('当前负责人', requirement.current_owner_name, requirement.current_owner)}
            </div>

            <div style={styles.sideDivider} />

            {/* 版本 */}
            <div style={styles.sideSection}>
              <span style={styles.sideSectionTitle}>版本范围</span>
              {hasDualVersion ? (
                <div style={styles.sideVersionRow}>
                  <div style={styles.sideVersionItem}>
                    <span style={styles.sideVersionLabel}>基线</span>
                    <span style={styles.sideVersionValue}>{requirement.baseline_version || '-'}</span>
                  </div>
                  <span style={styles.sideVersionArrow}>→</span>
                  <div style={styles.sideVersionItem}>
                    <span style={styles.sideVersionLabel}>目标</span>
                    <span style={styles.sideVersionValue}>{requirement.target_version || '-'}</span>
                  </div>
                </div>
              ) : (
                <span style={styles.sideFieldValue}>{requirement.firmware_version || '-'}</span>
              )}
            </div>

            <div style={styles.sideDivider} />

            {/* 计划时间 */}
            <div style={styles.sideSection}>
              <span style={styles.sideSectionTitle}>计划时间</span>
              <div style={styles.sideDateRow}>
                <span style={styles.sideDateLabel}>开始</span>
                <span style={styles.sideDateValue}>{formatDateShort(requirement.planned_start_date)}</span>
              </div>
              <div style={styles.sideDateRow}>
                <span style={styles.sideDateLabel}>结束</span>
                <span style={styles.sideDateValue}>{formatDateShort(requirement.planned_end_date)}</span>
              </div>
            </div>

            <div style={styles.sideDivider} />

            {/* 关联数据 */}
            <div style={styles.sideSection}>
              <span style={styles.sideSectionTitle}>关联数据</span>
              <div style={styles.sideMetaRow}>
                <span style={styles.sideMetaLabel}>关联用例数</span>
                <span style={styles.sideMetaValue}>
                  {requirement.case_count > 0
                    ? <span style={styles.sideCountBadge}>{requirement.case_count}</span>
                    : '-'
                  }
                </span>
              </div>
              {requirement.ref_reqs?.length ? (
                <div style={styles.sideMetaRow}>
                  <span style={styles.sideMetaLabel}>关联需求</span>
                  <span style={styles.sideMetaValue}>{requirement.ref_reqs.length}</span>
                </div>
              ) : null}
            </div>

            <div style={styles.sideDivider} />

            {/* 时间戳 */}
            <div style={styles.sideMeta}>
              <div style={styles.sideMetaRow}>
                <span style={styles.sideMetaLabel}>创建</span>
                <span style={styles.sideMetaTime}>{formatDate(requirement.created_at)}</span>
              </div>
              <div style={styles.sideMetaRow}>
                <span style={styles.sideMetaLabel}>更新</span>
                <span style={styles.sideMetaTime}>{formatDate(requirement.updated_at)}</span>
              </div>
            </div>
          </aside>

          {/* ── Right main ── */}
          <main style={styles.mainPanel}>
            {/* 标签（顶部分隔区） */}
            {tags.length > 0 && (
              <div style={styles.mainTagBar}>
                <span style={styles.sideSectionTitle}>标签</span>
                <div style={styles.tagList}>
                  {tags.map((tag, idx) => (
                    <span key={idx} style={styles.tag}>{tag}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Tab bar */}
            <div style={styles.mainTabBar}>
              <button
                type="button"
                style={{ ...styles.mainTab, ...(activeTab === 'details' ? styles.mainTabActive : {}) }}
                onClick={() => setActiveTab('details')}
              >
                描述
              </button>
              <button
                type="button"
                style={{ ...styles.mainTab, ...(activeTab === 'components' ? styles.mainTabActive : {}) }}
                onClick={() => setActiveTab('components')}
              >
                组件与参数
              </button>
              <button
                type="button"
                style={{ ...styles.mainTab, ...(activeTab === 'attachmentsTab' ? styles.mainTabActive : {}) }}
                onClick={() => setActiveTab('attachmentsTab')}
              >
                附件
                {hasAttachments && <span style={styles.mainTabBadge}>{requirement.attachments!.length}</span>}
              </button>
              <button
                type="button"
                style={{ ...styles.mainTab, ...(activeTab === 'workflow' ? styles.mainTabActive : {}) }}
                onClick={() => setActiveTab('workflow')}
              >
                工作流
              </button>
            </div>

            <div style={styles.mainContent}>
              {activeTab === 'details' && detailsContent}
              {activeTab === 'components' && componentsContent}
              {activeTab === 'attachmentsTab' && attachmentsContent}
              {activeTab === 'workflow' && workflowContent}
            </div>
          </main>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default RequirementDetailModal;
