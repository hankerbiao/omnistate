import React, { useState } from 'react';
import { api } from '../services/api';
import type { CreateRequirementRequest, RequirementResponse } from '../types';

/** 需求分类选项 */
const CATEGORY_OPTIONS = [
  { value: '', label: '请选择分类' },
  { value: 'FUNCTIONAL', label: '功能测试' },
  { value: 'PERFORMANCE', label: '性能测试' },
  { value: 'STABILITY', label: '稳定性测试' },
  { value: 'COMPATIBILITY', label: '兼容性测试' },
  { value: 'SECURITY', label: '安全测试' },
  { value: 'REGRESSION', label: '回归测试' },
];

/** 需求来源选项 */
const SOURCE_OPTIONS = [
  { value: '', label: '请选择来源' },
  { value: 'CUSTOMER', label: '客户需求' },
  { value: 'INTERNAL', label: '内部需求' },
  { value: 'BUG', label: '缺陷驱动' },
  { value: 'SPEC', label: '规格驱动' },
  { value: 'REGULATION', label: '合规要求' },
];

interface CreateRequirementFormProps {
  onClose: () => void;
  onSuccess: (requirement: RequirementResponse) => void;
}

const CreateRequirementForm: React.FC<CreateRequirementFormProps> = ({ onClose, onSuccess }) => {
  const [formData, setFormData] = useState<CreateRequirementRequest>({
    title: '',
    description: '',
    category: '',
    tags: [],
    source: '',
    acceptance_criteria: '',
    baseline_version: '',
    target_version: '',
    priority: 'P1',
    target_components: [],
    key_parameters: [],
    attachments: [],
    planned_start_date: '',
    planned_end_date: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tagInput, setTagInput] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // 清理空字符串字段
      const cleaned = { ...formData };
      if (!cleaned.category) delete cleaned.category;
      if (!cleaned.source) delete cleaned.source;
      if (!cleaned.acceptance_criteria) delete cleaned.acceptance_criteria;
      if (!cleaned.baseline_version) delete cleaned.baseline_version;
      if (!cleaned.target_version) delete cleaned.target_version;
      if (!cleaned.planned_start_date) delete cleaned.planned_start_date;
      if (!cleaned.planned_end_date) delete cleaned.planned_end_date;

      const response = await api.createRequirement(cleaned);
      onSuccess(response.data);
      onClose();
    } catch (err) {
      setError('创建测试需求失败');
      console.error('Create requirement error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleAddTag = () => {
    const tag = tagInput.trim();
    if (tag && !formData.tags?.includes(tag)) {
      setFormData((prev) => ({
        ...prev,
        tags: [...(prev.tags || []), tag],
      }));
    }
    setTagInput('');
  };

  const handleRemoveTag = (tag: string) => {
    setFormData((prev) => ({
      ...prev,
      tags: (prev.tags || []).filter(t => t !== tag),
    }));
  };

  const handleTagKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const applyPreset = (preset: Partial<CreateRequirementRequest>) => {
    setFormData((prev) => ({
      ...prev,
      ...preset,
    }));
  };

  const QUICK_PRESETS: { label: string; data: Partial<CreateRequirementRequest> }[] = [
    {
      label: 'DDR5 带宽',
      data: {
        title: `[测试] DDR5 内存带宽验证 ${new Date().toLocaleDateString('zh-CN')}`,
        priority: 'P1',
        category: 'PERFORMANCE',
        description: '验证 DDR5 内存读写带宽是否达到规格要求，含单通道/双通道场景。',
        acceptance_criteria: '读写带宽不低于 5600 MT/s，双通道模式下带宽翻倍。',
        baseline_version: 'v1.0',
        target_version: 'v2.1',
      },
    },
    {
      label: 'CPU 压力',
      data: {
        title: `[测试] CPU 全核压力测试 ${new Date().toLocaleDateString('zh-CN')}`,
        priority: 'P2',
        category: 'STABILITY',
        description: '长时间全核负载，观察温度与稳定性。',
        acceptance_criteria: '连续运行 72 小时无崩溃，温度不超过 95°C。',
      },
    },
    {
      label: '最小草稿',
      data: {
        title: `[测试] 工作流草稿 ${Date.now()}`,
        priority: 'P2',
        description: '',
      },
    },
  ];

  return (
    <div style={styles.modalOverlay}>
      <div style={styles.modalContent}>
        <div style={styles.modalHeader}>
          <h2 style={styles.modalTitle}>创建测试需求</h2>
          <button style={styles.closeButton} onClick={onClose}>×</button>
        </div>

        {error && <div style={styles.errorMessage}>{error}</div>}

        <div style={styles.presetBar}>
          <span style={styles.presetLabel}>快速填充：</span>
          {QUICK_PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              style={styles.presetBtn}
              onClick={() => applyPreset(preset.data)}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          {/* 基础信息行 */}
          <div style={styles.formRow}>
            <div style={{ ...styles.formGroup, flex: 2 }}>
              <label style={styles.label}>
                需求标题 <span style={styles.required}>*</span>
              </label>
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleChange}
                style={styles.input}
                placeholder="输入需求标题"
                required
              />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>优先级</label>
              <select
                name="priority"
                value={formData.priority}
                onChange={handleChange}
                style={styles.input}
              >
                <option value="P0">P0</option>
                <option value="P1">P1</option>
                <option value="P2">P2</option>
                <option value="P3">P3</option>
              </select>
            </div>
          </div>

          {/* 分类 & 来源 */}
          <div style={styles.formRow}>
            <div style={styles.formGroup}>
              <label style={styles.label}>需求分类</label>
              <select
                name="category"
                value={formData.category || ''}
                onChange={handleChange}
                style={styles.input}
              >
                {CATEGORY_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>需求来源</label>
              <select
                name="source"
                value={formData.source || ''}
                onChange={handleChange}
                style={styles.input}
              >
                {SOURCE_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* 版本信息 */}
          <div style={styles.formRow}>
            <div style={styles.formGroup}>
              <label style={styles.label}>基线版本</label>
              <input
                type="text"
                name="baseline_version"
                value={formData.baseline_version || ''}
                onChange={handleChange}
                style={styles.input}
                placeholder="对比基准版本"
              />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>目标版本</label>
              <input
                type="text"
                name="target_version"
                value={formData.target_version || ''}
                onChange={handleChange}
                style={styles.input}
                placeholder="待验证版本"
              />
            </div>
          </div>

          {/* 计划时间 */}
          <div style={styles.formRow}>
            <div style={styles.formGroup}>
              <label style={styles.label}>计划开始日期</label>
              <input
                type="date"
                name="planned_start_date"
                value={formData.planned_start_date || ''}
                onChange={handleChange}
                style={styles.input}
              />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>计划结束日期</label>
              <input
                type="date"
                name="planned_end_date"
                value={formData.planned_end_date || ''}
                onChange={handleChange}
                style={styles.input}
              />
            </div>
          </div>

          {/* 标签 */}
          <div style={styles.formGroup}>
            <label style={styles.label}>标签</label>
            <div style={styles.tagInputRow}>
              <input
                type="text"
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                onKeyDown={handleTagKeyDown}
                style={{ ...styles.input, flex: 1 }}
                placeholder="输入标签后按回车添加"
              />
              <button type="button" style={styles.addTagBtn} onClick={handleAddTag}>添加</button>
            </div>
            {formData.tags && formData.tags.length > 0 && (
              <div style={styles.tagList}>
                {formData.tags.map((tag, idx) => (
                  <span key={idx} style={styles.tagItem}>
                    {tag}
                    <button type="button" style={styles.tagRemoveBtn} onClick={() => handleRemoveTag(tag)}>×</button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* 需求描述 */}
          <div style={styles.formGroup}>
            <label style={styles.label}>需求描述</label>
            <textarea
              name="description"
              value={formData.description || ''}
              onChange={handleChange}
              style={styles.textarea}
              placeholder="描述需求的业务场景和具体要求"
              rows={4}
            />
          </div>

          {/* 验收标准 */}
          <div style={styles.formGroup}>
            <label style={styles.label}>验收标准</label>
            <textarea
              name="acceptance_criteria"
              value={formData.acceptance_criteria || ''}
              onChange={handleChange}
              style={{ ...styles.textarea, rows: 3 } as React.CSSProperties}
              placeholder="需求通过的具体条件"
            />
          </div>

          <div style={styles.modalFooter}>
            <button type="button" style={styles.cancelButton} onClick={onClose} disabled={loading}>
              取消
            </button>
            <button
              type="submit"
              style={{
                ...styles.submitButton,
                ...(loading ? styles.buttonDisabled : {}),
              }}
              disabled={loading}
            >
              {loading ? '创建中...' : '创建需求'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const styles = {
  modalOverlay: {
    position: 'fixed' as const,
    inset: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.72)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1100,
  } as const,
  modalContent: {
    width: '90%',
    maxWidth: '640px',
    maxHeight: '90vh',
    overflowY: 'auto' as const,
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    boxShadow: 'var(--shadow-lg)',
  } as const,
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px 24px',
    borderBottom: '1px solid var(--border-default)',
  } as const,
  modalTitle: {
    margin: 0,
    fontSize: '20px',
    color: 'var(--text-primary)',
  } as const,
  closeButton: {
    background: 'none',
    border: 'none',
    color: 'var(--text-muted)',
    fontSize: '28px',
    cursor: 'pointer',
    lineHeight: 1,
  } as const,
  errorMessage: {
    margin: '20px 24px 0',
    padding: '12px 14px',
    backgroundColor: 'var(--status-error-bg)',
    color: 'var(--accent-red)',
    border: '1px solid rgba(255, 107, 107, 0.3)',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
  } as const,
  presetBar: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    alignItems: 'center',
    gap: '8px',
    margin: '16px 24px 0',
    padding: '10px 12px',
    backgroundColor: 'var(--bg-primary)',
    borderRadius: 'var(--radius-md)',
    border: '1px dashed var(--border-default)',
  } as const,
  presetLabel: {
    fontSize: '12px',
    color: 'var(--text-muted)',
  } as const,
  presetBtn: {
    padding: '4px 10px',
    fontSize: '12px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-secondary)',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
  } as const,
  form: {
    padding: '24px',
  } as const,
  formRow: {
    display: 'flex',
    gap: '16px',
    marginBottom: '0',
  } as const,
  formGroup: {
    marginBottom: '18px',
    flex: 1,
  } as const,
  label: {
    display: 'block',
    marginBottom: '8px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
  } as const,
  required: {
    color: 'var(--accent-red)',
  } as const,
  input: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
    boxSizing: 'border-box' as const,
  } as const,
  textarea: {
    width: '100%',
    padding: '12px 14px',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
    resize: 'vertical' as const,
    fontFamily: 'inherit',
    boxSizing: 'border-box' as const,
  } as const,
  // ─── 标签输入 ──────────────────────────────────────────────────────────
  tagInputRow: {
    display: 'flex',
    gap: '8px',
  } as const,
  addTagBtn: {
    padding: '10px 14px',
    fontSize: '13px',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    whiteSpace: 'nowrap' as const,
  } as const,
  tagList: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '6px',
    marginTop: '8px',
  } as const,
  tagItem: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '3px 8px',
    fontSize: '12px',
    color: 'var(--accent-blue)',
    backgroundColor: 'rgba(88, 166, 255, 0.15)',
    borderRadius: '12px',
  } as const,
  tagRemoveBtn: {
    background: 'none',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    fontSize: '12px',
    padding: '0 2px',
    lineHeight: 1,
  } as const,
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
    marginTop: '24px',
  } as const,
  cancelButton: {
    padding: '10px 18px',
    backgroundColor: 'transparent',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  } as const,
  submitButton: {
    padding: '10px 18px',
    backgroundColor: 'var(--accent-cyan)',
    color: 'var(--bg-primary)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    fontWeight: 600,
  } as const,
  buttonDisabled: {
    opacity: 0.7,
    cursor: 'not-allowed',
  } as const,
};

export default CreateRequirementForm;
