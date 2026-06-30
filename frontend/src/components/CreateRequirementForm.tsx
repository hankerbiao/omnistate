import React, { useState } from 'react';
import { api } from '../services/api';
import type { CreateRequirementRequest, RequirementResponse } from '../types';
import AIPolishButton from './ui/AIPolishButton';

/** 预设推荐标签 */
const RECOMMENDED_TAGS = ['功能', '性能', '稳定性', '兼容性', '安全', '回归', '自动化', '压力', '冒烟'];

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

interface CreateRequirementFormProps {
  onClose: () => void;
  onSuccess: (requirement: RequirementResponse) => void;
}

// ── 颜色常量 ──────────────────────────────────────────
const C = {
  purple: '#7c3aed',
  purpleLight: '#f5f3ff',
  blue: '#3b82f6',
  blueLight: '#eff6ff',
  green: '#16a34a',
  greenLight: '#f0fdf4',
  amber: '#d97706',
  amberLight: '#fffbeb',
  red: '#dc2626',
  redLight: '#fef2f2',
  gray: '#64748b',
  grayLight: '#f8fafc',
  border: '#e2e8f0',
  subtle: '#f1f5f9',
};

const CreateRequirementForm: React.FC<CreateRequirementFormProps> = ({ onClose, onSuccess }) => {
  const [formData, setFormData] = useState<CreateRequirementRequest>({
    title: '',
    description: '',
    category: '',
    tags: [],
    acceptance_criteria: '',
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

  // 拆解的描述区块
  const [descSections, setDescSections] = useState({
    background: '',
    functional: '',
    precondition: '',
    testFocus: '',
  });

  const PRIORITY_ITEMS = [
    { value: 'P0', label: 'P0', desc: '紧急', color: C.red, bg: C.redLight },
    { value: 'P1', label: 'P1', desc: '重要', color: C.amber, bg: C.amberLight },
    { value: 'P2', label: 'P2', desc: '一般', color: C.blue, bg: C.blueLight },
    { value: 'P3', label: 'P3', desc: '较低', color: C.gray, bg: C.grayLight },
  ];

  const handleDescChange = (field: keyof typeof descSections, value: string) => {
    setDescSections((prev) => ({ ...prev, [field]: value }));
  };

  const buildDescription = () => {
    const parts: string[] = [];
    if (descSections.background.trim()) {
      parts.push(`【业务背景】\n${descSections.background.trim()}`);
    }
    if (descSections.functional.trim()) {
      parts.push(`【功能描述】\n${descSections.functional.trim()}`);
    }
    if (descSections.precondition.trim()) {
      parts.push(`【前置条件】\n${descSections.precondition.trim()}`);
    }
    if (descSections.testFocus.trim()) {
      parts.push(`【测试要点】\n${descSections.testFocus.trim()}`);
    }
    return parts.join('\n\n');
  };

  const toggleRecommendedTag = (tag: string) => {
    setFormData((prev) => ({
      ...prev,
      tags: prev.tags?.includes(tag)
        ? prev.tags.filter(t => t !== tag)
        : [...(prev.tags || []), tag],
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const description = buildDescription();
      const cleaned = { ...formData, description };
      if (!cleaned.category) delete cleaned.category;
      if (!cleaned.acceptance_criteria) delete cleaned.acceptance_criteria;
      if (!cleaned.planned_start_date) delete cleaned.planned_start_date;
      if (!cleaned.planned_end_date) delete cleaned.planned_end_date;

      const response = await api.createRequirement(cleaned);
      onSuccess(response.data);
      onClose();
    } catch (err) {
      setError('创建测试用例编写需求失败');
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

  return (
    <div style={styles.modalOverlay} onClick={onClose}>
      <div style={styles.modalContent} onClick={e => e.stopPropagation()}>

        {/* ═══ Header ═══ */}
        <div style={styles.header}>
          <div style={styles.headerLeft}>
            <div style={styles.headerIcon}>📋</div>
            <div>
              <h2 style={styles.headerTitle}>创建测试用例编写需求</h2>
              <p style={styles.headerSub}>填写需求信息，后续将自动关联工作流与测试用例</p>
            </div>
          </div>
          <button style={styles.closeBtn} onClick={onClose}>✕</button>
        </div>
        <div style={styles.headerAccent} />

        {/* ═══ Error ═══ */}
        {error && (
          <div style={styles.errorBar}>
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* ═══ Form ═══ */}
        <form onSubmit={handleSubmit} style={styles.formBody}>

          {/* ─── 基础信息 ─── */}
          <div style={styles.section}>
            <div style={styles.sectionHeader}>
              <span style={styles.sectionIcon}>📌</span>
              <span style={styles.sectionTitle}>基础信息</span>
            </div>
            <div style={styles.sectionBody}>
              <div style={styles.twoCol}>
                <div style={styles.field}>
                  <label style={styles.fieldLabel}>
                    需求标题 <span style={{ color: C.red }}>*</span>
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
                <div style={styles.field}>
                  <label style={styles.fieldLabel}>优先级</label>
                  <div style={styles.priorityGroup}>
                    {PRIORITY_ITEMS.map(p => (
                      <button
                        key={p.value}
                        type="button"
                        onClick={() => setFormData(prev => ({ ...prev, priority: p.value }))}
                        style={{
                          ...styles.priorityPill,
                          ...(formData.priority === p.value
                            ? { borderColor: p.color, backgroundColor: p.bg, color: p.color, fontWeight: 600 }
                            : {}),
                        }}
                      >
                        <span style={{
                          ...styles.priorityDot,
                          backgroundColor: p.color,
                          ...(formData.priority === p.value ? { boxShadow: `0 0 0 2px ${p.color}40` } : {}),
                        }} />
                        <span>{p.label}</span>
                        <span style={styles.priorityDesc}>{p.desc}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div style={styles.twoCol}>
                <div style={styles.field}>
                  <label style={styles.fieldLabel}>需求分类</label>
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
                <div style={styles.field}>
                  <label style={styles.fieldLabel}>验收标准</label>
                  <textarea
                    name="acceptance_criteria"
                    value={formData.acceptance_criteria || ''}
                    onChange={handleChange}
                    style={{ ...styles.input, ...styles.textarea, minHeight: 60 }}
                    placeholder="需求通过的具体条件"
                    rows={2}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* ─── 计划时间（紧凑行） ─── */}
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
            <div style={{ flex: 1 }}>
              <label style={{ ...styles.fieldLabel, marginBottom: 6, display: 'block' }}>起始日期</label>
              <input
                type="date"
                value={formData.planned_start_date || ''}
                onChange={e => setFormData(prev => ({ ...prev, planned_start_date: e.target.value }))}
                style={styles.input}
              />
            </div>
            <span style={{ paddingBottom: 10, color: C.gray, fontSize: 13 }}>→</span>
            <div style={{ flex: 1 }}>
              <label style={{ ...styles.fieldLabel, marginBottom: 6, display: 'block' }}>结束日期</label>
              <input
                type="date"
                min={formData.planned_start_date || undefined}
                value={formData.planned_end_date || ''}
                onChange={e => setFormData(prev => ({ ...prev, planned_end_date: e.target.value }))}
                style={styles.input}
              />
            </div>
          </div>

          {/* ─── 标签 ─── */}
          <div style={styles.section}>
            <div style={styles.sectionHeader}>
              <span style={styles.sectionIcon}>🏷️</span>
              <span style={styles.sectionTitle}>标签</span>
            </div>
            <div style={styles.sectionBody}>
              <div style={styles.recommendedTags}>
                {RECOMMENDED_TAGS.map(tag => {
                  const active = formData.tags?.includes(tag);
                  return (
                    <button
                      key={tag}
                      type="button"
                      style={{
                        ...styles.tagPill,
                        ...(active ? styles.tagPillActive : {}),
                      }}
                      onClick={() => toggleRecommendedTag(tag)}
                    >
                      {active ? '✓ ' : ''}{tag}
                    </button>
                  );
                })}
              </div>
              <div style={styles.tagInputRow}>
                <input
                  type="text"
                  value={tagInput}
                  onChange={e => setTagInput(e.target.value)}
                  onKeyDown={handleTagKeyDown}
                  style={{ ...styles.input, flex: 1 }}
                  placeholder="自定义标签，回车添加"
                />
                <button type="button" style={styles.tagAddBtn} onClick={handleAddTag}>添加</button>
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
          </div>

          {/* ─── 需求描述（结构化） ─── */}
          <div style={styles.section}>
            <div style={styles.sectionHeader}>
              <span style={styles.sectionIcon}>✏️</span>
              <span style={styles.sectionTitle}>需求描述</span>
              <span style={styles.sectionHint}>逐项填写，编写人员可快速理解</span>
            </div>
            <div style={styles.sectionBody}>
              <div style={styles.descGrid}>
                {([
                  { key: 'background', label: '业务背景', placeholder: '为什么需要这个需求？业务场景是什么？', rows: 3 as const },
                  { key: 'functional', label: '功能描述', placeholder: '具体要测哪些功能？变更点是什么？', rows: 3 as const },
                  { key: 'precondition', label: '前置条件', placeholder: '环境/数据/配置有什么要求？', rows: 3 as const },
                  { key: 'testFocus', label: '测试要点', placeholder: '重点验证哪些方面？边界情况？', rows: 3 as const },
                ] as const).map(({ key, label, placeholder, rows }) => (
                  <div key={key} style={styles.descItem}>
                    <div style={styles.descLabelRow}>
                      <span style={styles.descLabel}>{label}</span>
                      <AIPolishButton
                        text={descSections[key]}
                        onPolished={(t) => handleDescChange(key, t)}
                      />
                    </div>
                    <textarea
                      value={descSections[key]}
                      onChange={e => handleDescChange(key, e.target.value)}
                      style={styles.descTextarea}
                      placeholder={placeholder}
                      rows={rows}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ═══ Footer ═══ */}
          <div style={styles.footer}>
            <button type="button" style={styles.cancelBtn} onClick={onClose} disabled={loading}>
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{
                ...styles.submitBtn,
                ...(loading ? styles.submitBtnLoading : {}),
              }}
            >
              {loading ? (
                <span style={styles.submitLoadingContent}>
                  <span style={styles.submitSpinner} />
                  创建中...
                </span>
              ) : (
                <span>创建需求</span>
              )}
            </button>
          </div>

        </form>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════
//  Styles
// ═══════════════════════════════════════════════════════════════

const FOCUS_RING = `0 0 0 3px ${C.blue}25`;

const styles: Record<string, React.CSSProperties> = {
  // ── Overlay & Modal ──
  modalOverlay: {
    position: 'fixed',
    inset: 0,
    backgroundColor: 'rgba(15, 23, 42, 0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1100,
    backdropFilter: 'blur(6px)',
  },
  modalContent: {
    width: '92%',
    maxWidth: 720,
    maxHeight: '88vh',
    overflowY: 'auto',
    backgroundColor: '#fff',
    borderRadius: 16,
    boxShadow: '0 25px 50px rgba(15, 23, 42, 0.25)',
    display: 'flex',
    flexDirection: 'column',
  },

  // ── Header ──
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: '24px 28px 16px',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 12,
  },
  headerIcon: {
    fontSize: 24,
    lineHeight: 1,
    marginTop: 2,
  },
  headerTitle: {
    margin: 0,
    fontSize: 18,
    fontWeight: 700,
    color: '#0f172a',
    letterSpacing: '-0.3px',
  },
  headerSub: {
    margin: '4px 0 0',
    fontSize: 13,
    color: C.gray,
  },
  headerAccent: {
    height: 3,
    background: 'linear-gradient(90deg, #7c3aed, #3b82f6, #06b6d4)',
    margin: '0 28px',
    borderRadius: 2,
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: C.gray,
    fontSize: 18,
    cursor: 'pointer',
    padding: '4px 8px',
    borderRadius: 6,
    lineHeight: 1,
    flexShrink: 0,
  },

  // ── Error ──
  errorBar: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    margin: '16px 28px 0',
    padding: '10px 14px',
    backgroundColor: C.redLight,
    border: `1px solid ${C.red}30`,
    borderRadius: 10,
    color: C.red,
    fontSize: 13,
  },

  // ── Form ──
  formBody: {
    padding: '20px 28px 24px',
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },

  // ── Section Card ──
  section: {
    border: `1px solid ${C.border}`,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#fff',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '12px 16px',
    backgroundColor: C.grayLight,
    borderBottom: `1px solid ${C.border}`,
  },
  sectionIcon: {
    fontSize: 14,
    lineHeight: 1,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: '#0f172a',
  },
  sectionHint: {
    marginLeft: 'auto',
    fontSize: 11,
    color: C.gray,
  },
  sectionBody: {
    padding: 16,
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },

  // ── Fields ──
  twoCol: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 12,
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  fieldLabel: {
    fontSize: 12,
    fontWeight: 600,
    color: '#475569',
    letterSpacing: '0.2px',
  },

  // ── Inputs ──
  input: {
    width: '100%',
    padding: '10px 12px',
    border: `1px solid ${C.border}`,
    borderRadius: 8,
    fontSize: 13,
    backgroundColor: '#fff',
    color: '#0f172a',
    outline: 'none',
    boxSizing: 'border-box' as const,
    transition: 'border-color 0.15s, box-shadow 0.15s',
  },
  textarea: {
    resize: 'vertical' as const,
    fontFamily: 'inherit',
    lineHeight: 1.6,
    minHeight: 72,
  },

  // ── Priority ──
  priorityGroup: {
    display: 'flex',
    gap: 6,
  },
  priorityPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    flex: 1,
    padding: '8px 8px',
    border: `1px solid ${C.border}`,
    borderRadius: 8,
    backgroundColor: '#fff',
    color: C.gray,
    fontSize: 12,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  priorityDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    flexShrink: 0,
    transition: 'box-shadow 0.15s',
  },
  priorityDesc: {
    fontSize: 10,
    color: 'inherit',
    opacity: 0.6,
    marginLeft: 'auto',
  },

  // ── Tags ──
  recommendedTags: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
  },
  tagPill: {
    padding: '5px 12px',
    fontSize: 11,
    fontWeight: 500,
    borderRadius: 999,
    border: `1px solid ${C.border}`,
    backgroundColor: '#fff',
    color: C.gray,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  tagPillActive: {
    border: `1px solid ${C.blue}`,
    backgroundColor: C.blueLight,
    color: C.blue,
    fontWeight: 600,
  },
  tagInputRow: {
    display: 'flex',
    gap: 8,
  },
  tagAddBtn: {
    padding: '10px 16px',
    fontSize: 12,
    fontWeight: 500,
    backgroundColor: C.grayLight,
    border: `1px solid ${C.border}`,
    borderRadius: 8,
    color: '#475569',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  },
  tagList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
  },
  tagItem: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    padding: '4px 10px',
    fontSize: 12,
    color: C.blue,
    backgroundColor: C.blueLight,
    borderRadius: 999,
    border: `1px solid ${C.blue}30`,
  },
  tagRemoveBtn: {
    background: 'none',
    border: 'none',
    color: 'inherit',
    cursor: 'pointer',
    fontSize: 14,
    padding: '0 2px',
    opacity: 0.6,
    lineHeight: 1,
  },

  // ── Description Sections ──
  descGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 10,
  },
  descItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    padding: '10px 12px',
    backgroundColor: C.grayLight,
    borderRadius: 10,
    border: `1px solid ${C.border}`,
    borderLeft: `3px solid ${C.purple}`,
  },
  descLabelRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  descLabel: {
    fontSize: 12,
    fontWeight: 600,
    color: '#374151',
  },
  descTextarea: {
    width: '100%',
    padding: '8px 10px',
    border: `1px solid ${C.border}`,
    borderRadius: 6,
    fontSize: 13,
    backgroundColor: '#fff',
    color: '#0f172a',
    outline: 'none',
    resize: 'vertical' as const,
    fontFamily: 'inherit',
    lineHeight: 1.6,
    boxSizing: 'border-box' as const,
    transition: 'border-color 0.15s, box-shadow 0.15s',
  },

  // ── Footer ──
  footer: {
    display: 'flex',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: 10,
    paddingTop: 4,
  },
  cancelBtn: {
    padding: '10px 20px',
    fontSize: 13,
    fontWeight: 500,
    backgroundColor: '#fff',
    color: '#475569',
    border: `1px solid ${C.border}`,
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'background 0.15s',
  },
  submitBtn: {
    padding: '10px 24px',
    fontSize: 13,
    fontWeight: 600,
    background: 'linear-gradient(135deg, #7c3aed, #6366f1)',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    boxShadow: '0 2px 8px rgba(124, 58, 237, 0.3)',
    transition: 'all 0.15s',
    minWidth: 120,
  },
  submitBtnLoading: {
    opacity: 0.7,
    cursor: 'wait',
  },
  submitLoadingContent: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
  },
  submitSpinner: {
    display: 'inline-block',
    width: 14,
    height: 14,
    border: '2px solid rgba(255,255,255,0.4)',
    borderTopColor: '#fff',
    borderRadius: '50%',
    animation: 'spin 0.6s linear infinite',
  },
};

export default CreateRequirementForm;
