import React, { useMemo, useState } from 'react';
import { api } from '../services/api';
import type { CreateTestCaseRequest, TestCaseResponse, TestCaseStep } from '../types';
import CatalogPathEditor, { type CatalogPathValue } from './catalog/CatalogPathEditor';
import { PRIORITY_COLORS, PRIORITY_LABELS } from '../constants/testCaseLabels';
import TestCaseStepEditor from './TestCaseStepEditor';
import TestCaseStepEditorV2 from './TestCaseStepEditorV2';

interface CreateTestCaseFormProps {
  onClose: () => void;
  onSuccess: () => void;
  defaultRequirementId?: string;
  lockRequirementId?: boolean;
  defaultLabId?: string;
  defaultCatalogPrefix?: string[];
  editTestCase?: TestCaseResponse;
}

interface FormSectionProps {
  title: string;
  badge?: string;
  prominent?: boolean;
  children: React.ReactNode;
}

function testCaseToFormData(testCase: TestCaseResponse): CreateTestCaseRequest {
  return {
    ref_req_id: testCase.ref_req_id || undefined,
    lab_id: testCase.lab_id,
    catalog_path: testCase.catalog_path || [],
    title: testCase.title,
    version: testCase.version,
    is_active: testCase.is_active,
    change_log: testCase.change_log,
    owner_id: testCase.owner_id,
    reviewer_id: testCase.reviewer_id,
    auto_dev_id: testCase.auto_dev_id,
    priority: testCase.priority,
    estimated_duration_sec: testCase.estimated_duration_sec,
    required_env: testCase.required_env,
    tags: testCase.tags ?? [],
    test_category: testCase.test_category,
    is_destructive: testCase.is_destructive,
    pre_condition: testCase.pre_condition,
    post_condition: testCase.post_condition,
    is_need_auto: testCase.is_need_auto,
    is_automated: testCase.is_automated,
    automation_type: testCase.automation_type,
    script_entity_id: testCase.script_entity_id,
    automation_case_ref: testCase.automation_case_ref,
    risk_level: testCase.risk_level,
    failure_analysis: testCase.failure_analysis,
    confidentiality: testCase.confidentiality,
    visibility_scope: testCase.visibility_scope,
    attachments: testCase.attachments ?? [],
    custom_fields: testCase.custom_fields ?? {},
    deprecation_reason: testCase.deprecation_reason,
    approval_history: testCase.approval_history ?? [],
    steps: testCase.steps ?? [],
    cleanup_steps: testCase.cleanup_steps ?? [],
  };
}

function validateStepList(steps: TestCaseStep[] | undefined, label: string): string | null {
  if (!steps?.length) return null;
  const seen = new Set<string>();
  for (let i = 0; i < steps.length; i++) {
    const step = steps[i];
    const name = step.name?.trim() ?? '';
    const action = step.action?.trim() ?? '';
    const expected = step.expected?.trim() ?? '';
    const stepId = step.step_id?.trim() ?? '';
    if (!stepId || !name || !action || !expected) {
      return `${label}第 ${i + 1} 步：请填写步骤标题、动作与期望`;
    }
    if (seen.has(stepId)) {
      return `${label}：步骤 ID 重复`;
    }
    seen.add(stepId);
  }
  return null;
}

function stepsChanged(a: TestCaseStep[] = [], b: TestCaseStep[] = []): boolean {
  return JSON.stringify(a) !== JSON.stringify(b);
}

const FormSection: React.FC<FormSectionProps> = ({ title, badge, prominent, children, actions }) => (
  <section
    style={{
      ...styles.section,
      ...(prominent ? styles.sectionProminent : {}),
    }}
  >
    <div style={{ ...styles.sectionHeader, justifyContent: actions ? 'space-between' : undefined }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
        <span style={styles.sectionTitle}>{title}</span>
        {badge && <span style={prominent ? styles.sectionBadgeProminent : styles.sectionBadge}>{badge}</span>}
      </div>
      {actions && <div>{actions}</div>}
    </div>
    <div style={styles.sectionContent}>{children}</div>
  </section>
);

const CreateTestCaseForm: React.FC<CreateTestCaseFormProps> = ({
  onClose,
  onSuccess,
  defaultRequirementId = '',
  lockRequirementId = false,
  defaultLabId = '',
  defaultCatalogPrefix = [],
  editTestCase,
}) => {
  const isEditMode = Boolean(editTestCase);

  const [formData, setFormData] = useState<CreateTestCaseRequest>(() => {
    if (editTestCase) {
      return testCaseToFormData(editTestCase);
    }
    return {
      ref_req_id: defaultRequirementId || undefined,
      lab_id: defaultLabId,
      catalog_path: defaultCatalogPrefix.length > 0 ? [...defaultCatalogPrefix] : [''],
      title: '',
      version: 1,
      is_active: true,
      priority: 'P1',
      tags: [],
      is_destructive: false,
      is_need_auto: false,
      is_automated: false,
      attachments: [],
      custom_fields: {},
      approval_history: [],
      steps: [],
      cleanup_steps: [],
    };
  });

  const originalSteps = editTestCase?.steps ?? [];
  const originalCleanupSteps = editTestCase?.cleanup_steps ?? [];
  const stepsDirty = isEditMode && (
    stepsChanged(formData.steps, originalSteps)
    || stepsChanged(formData.cleanup_steps, originalCleanupSteps)
  );

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'basic' | 'steps' | 'automation'>('basic');
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [cleanupExpanded, setCleanupExpanded] = useState(
    () => Boolean(editTestCase?.cleanup_steps?.length),
  );
  const [newTag, setNewTag] = useState('');
  const [catalogTouched, setCatalogTouched] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(isEditMode);
  const lockCatalogFromTree = !isEditMode && Boolean(defaultLabId) && defaultCatalogPrefix.length > 0;
  const lockLabOnly = !isEditMode && Boolean(defaultLabId) && defaultCatalogPrefix.length === 0;

  const [catalogPath, setCatalogPath] = useState<CatalogPathValue>(() => ({
    labId: editTestCase?.lab_id || defaultLabId,
    segments: editTestCase?.catalog_path?.length
      ? editTestCase.catalog_path
      : defaultCatalogPrefix.length > 0
        ? [...defaultCatalogPrefix, '']
        : [''],
  }));

  const catalogLockedPrefix = useMemo(
    () => (lockCatalogFromTree ? defaultCatalogPrefix : []),
    [lockCatalogFromTree, defaultCatalogPrefix],
  );

  const normalizePayload = (data: CreateTestCaseRequest): CreateTestCaseRequest => {
    const payload = { ...data };
    if (typeof payload.is_active === 'string') {
      payload.is_active = payload.is_active === 'true';
    }
    return payload;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setCatalogTouched(true);
    setLoading(true);
    setError(null);

    const segments = catalogPath.segments.map(s => s.trim()).filter(Boolean);
    if (!catalogPath.labId || segments.length === 0) {
      setError('请选择 Lab 并填写至少一段目录路径');
      setActiveTab('basic');
      setLoading(false);
      return;
    }

    const stepsError = validateStepList(formData.steps, '执行步骤')
      || validateStepList(formData.cleanup_steps, '清理步骤');
    if (stepsError) {
      setError(stepsError);
      setActiveTab('steps');
      setLoading(false);
      return;
    }

    try {
      const payload = normalizePayload({
        ...formData,
        lab_id: catalogPath.labId,
        catalog_path: segments,
        ref_req_id: formData.ref_req_id?.trim() || undefined,
        steps: (formData.steps ?? []).map(step => ({
          ...step,
          name: step.name.trim(),
          action: step.action.trim(),
          expected: step.expected.trim(),
        })),
        cleanup_steps: (formData.cleanup_steps ?? []).map(step => ({
          ...step,
          name: step.name.trim(),
          action: step.action.trim(),
          expected: step.expected.trim(),
        })),
      });
      if (isEditMode && editTestCase) {
        // Strip high-risk fields that must be updated via explicit commands
        const {
          owner_id: _owner,
          reviewer_id: _reviewer,
          auto_dev_id: _autoDev,
          ref_req_id: _refReq,
          ...safePayload
        } = payload;
        await api.updateTestCase(editTestCase.case_id, safePayload);
      } else {
        await api.createTestCase(payload);
      }
      onSuccess();
      onClose();
    } catch (err) {
      const fallback = isEditMode ? '更新测试用例失败' : '创建测试用例失败';
      const message = err instanceof Error && err.message ? err.message : fallback;
      setError(message);
      console.error(isEditMode ? 'Update test case error:' : 'Create test case error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }));
  };

  const handleAddTag = () => {
    if (newTag.trim()) {
      setFormData(prev => ({
        ...prev,
        tags: [...(prev.tags || []), newTag.trim()],
      }));
      setNewTag('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags?.filter(t => t !== tag) || [],
    }));
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        onClick={e => e.stopPropagation()}
        style={{ width: 720, maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}
      >
        <div className="modal__header">
          <div>
            <h3 className="modal__title">{isEditMode ? '编辑测试用例' : '创建测试用例'}</h3>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '4px 0 0' }}>
              {isEditMode
                ? `用例 ${editTestCase?.case_id} · 目录与基本信息可在此调整`
                : lockCatalogFromTree
                  ? '目录已从左侧树继承，填写名称与优先级即可快速创建'
                  : '先确定所属目录，再填写用例详情'}
            </p>
          </div>
          <button type="button" className="modal__close" onClick={onClose}>×</button>
        </div>

        {error && (
          <div style={{ ...styles.errorBanner, margin: 'var(--space-4) var(--space-6) 0' }} role="alert">
            <span style={styles.errorIcon}>!</span>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.tabs} role="tablist" aria-label="用例表单分区">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'basic'}
              aria-controls="test-case-panel-basic"
              id="test-case-tab-basic"
              style={{ ...styles.tab, ...(activeTab === 'basic' ? styles.activeTab : {}) }}
              onClick={() => setActiveTab('basic')}
            >
              基本信息
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'steps'}
              aria-controls="test-case-panel-steps"
              id="test-case-tab-steps"
              style={{ ...styles.tab, ...(activeTab === 'steps' ? styles.activeTab : {}) }}
              onClick={() => setActiveTab('steps')}
            >
              步骤
              {(formData.steps?.length ?? 0) > 0 && (
                <span style={styles.tabBadge}>{formData.steps?.length}</span>
              )}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'automation'}
              aria-controls="test-case-panel-automation"
              id="test-case-tab-automation"
              style={{ ...styles.tab, ...(activeTab === 'automation' ? styles.activeTab : {}) }}
              onClick={() => setActiveTab('automation')}
            >
              自动化
            </button>
          </div>

          <div style={styles.modalBody}>
            {activeTab === 'basic' && (
              <div
                id="test-case-panel-basic"
                role="tabpanel"
                aria-labelledby="test-case-tab-basic"
                style={styles.tabStack}
              >
                {!isEditMode ? (
                  <section style={styles.quickCreateCard}>
                    <div style={styles.quickCreateHeader}>
                      <span style={styles.quickCreateTitle}>快速创建</span>
                      <span style={styles.quickCreateBadge}>核心字段</span>
                    </div>
                    <div style={styles.quickCreateBody}>
                      <FormSection title="所属目录" badge="必填" prominent>
                        <CatalogPathEditor
                          value={catalogPath}
                          onChange={setCatalogPath}
                          titlePreview={formData.title}
                          showValidation={catalogTouched}
                          lockLab={lockCatalogFromTree || lockLabOnly}
                          lockedPrefix={catalogLockedPrefix}
                          compact
                        />
                      </FormSection>
                      <div style={styles.twoColGrid}>
                        <div style={styles.formGroup}>
                          <label style={styles.label}>
                            用例名称
                            <span style={styles.required}>*</span>
                          </label>
                          <input
                            type="text"
                            name="title"
                            className="form-input"
                            value={formData.title}
                            onChange={handleChange}
                            placeholder="输入用例名称"
                            required
                            autoFocus={lockCatalogFromTree}
                          />
                        </div>
                        <div style={styles.formGroup}>
                          <label style={styles.label}>优先级</label>
                          <div style={styles.priorityPills} role="group" aria-label="优先级">
                            {(Object.keys(PRIORITY_LABELS) as Array<keyof typeof PRIORITY_LABELS>).map(p => (
                              <button
                                key={p}
                                type="button"
                                style={{
                                  ...styles.priorityPill,
                                  ...(formData.priority === p ? styles.priorityPillActive : {}),
                                  border: `1px solid ${PRIORITY_COLORS[p]}`,
                                }}
                                onClick={() => setFormData(prev => ({ ...prev, priority: p }))}
                              >
                                <span
                                  style={{
                                    ...styles.priorityPillDot,
                                    backgroundColor: PRIORITY_COLORS[p],
                                  }}
                                />
                                {PRIORITY_LABELS[p]}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </section>
                ) : (
                  <>
                    <FormSection title="所属目录" badge="必填" prominent>
                      <CatalogPathEditor
                        value={catalogPath}
                        onChange={setCatalogPath}
                        titlePreview={formData.title}
                        showValidation={catalogTouched}
                      />
                    </FormSection>
                    <FormSection title="基本信息">
                      <div style={styles.twoColGrid}>
                        <div style={styles.formGroup}>
                          <label style={styles.label}>
                            用例名称
                            <span style={styles.required}>*</span>
                          </label>
                          <input
                            type="text"
                            name="title"
                            className="form-input"
                            value={formData.title}
                            onChange={handleChange}
                            placeholder="输入用例名称"
                            required
                          />
                        </div>
                        <div style={styles.formGroup}>
                          <label style={styles.label}>优先级</label>
                          <div style={styles.selectWrapper}>
                            <select
                              name="priority"
                              className="form-input form-select"
                              value={formData.priority}
                              onChange={handleChange}
                            >
                              {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                                <option key={value} value={value}>
                                  {label} ({value})
                                </option>
                              ))}
                            </select>
                            <span
                              style={{
                                ...styles.priorityDot,
                                backgroundColor: PRIORITY_COLORS[formData.priority as keyof typeof PRIORITY_COLORS]
                                  || PRIORITY_COLORS.P1,
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    </FormSection>
                  </>
                )}

                {!isEditMode && (
                  <button
                    type="button"
                    style={styles.advancedToggle}
                    onClick={() => setShowAdvanced(v => !v)}
                    aria-expanded={showAdvanced}
                  >
                    <span style={styles.advancedChevron} aria-hidden>
                      {showAdvanced ? '▾' : '▸'}
                    </span>
                    <span>高级选项</span>
                    <span style={styles.advancedHint}>需求关联、分类、标签、条件等</span>
                  </button>
                )}

                {(isEditMode || showAdvanced) && (
                  <>
                <FormSection title="关联需求" badge="可选">
                  <div style={styles.formGroup}>
                    <label style={styles.label}>
                      需求编号 (ref_req_id)
                      <span style={styles.optionalHint}>可选 · 与目录正交</span>
                    </label>
                    <div style={styles.inputWrapper}>
                      <input
                        type="text"
                        name="ref_req_id"
                        className="form-input"
                        value={formData.ref_req_id || ''}
                        onChange={handleChange}
                        placeholder="留空表示不绑定需求"
                        readOnly={lockRequirementId}
                        style={lockRequirementId ? styles.inputLocked : undefined}
                      />
                      {lockRequirementId && (
                        <span style={styles.lockedBadge}>已锁定</span>
                      )}
                    </div>
                    {lockRequirementId && (
                      <p style={styles.helperText}>从需求页创建/编辑时，关联需求不可修改</p>
                    )}
                  </div>
                </FormSection>

                <FormSection title="执行与分类">
                  <div style={styles.threeColGrid}>
                    <div style={styles.formGroup}>
                      <label style={styles.label}>预估时间 (秒)</label>
                      <input
                        type="number"
                        name="estimated_duration_sec"
                        className="form-input"
                        value={formData.estimated_duration_sec ?? ''}
                        onChange={handleChange}
                        placeholder="60"
                        min={0}
                      />
                    </div>

                    <div style={styles.formGroup}>
                      <label style={styles.label}>测试分类</label>
                      <input
                        type="text"
                        name="test_category"
                        className="form-input"
                        value={formData.test_category || ''}
                        onChange={handleChange}
                        placeholder="功能 / 性能等（非目录）"
                      />
                    </div>

                    <div style={styles.formGroup}>
                      <label style={styles.label}>状态</label>
                      <select
                        name="is_active"
                        className="form-input form-select"
                        value={formData.is_active ? 'true' : 'false'}
                        onChange={handleChange}
                      >
                        <option value="true">激活</option>
                        <option value="false">未激活</option>
                      </select>
                    </div>
                  </div>

                  <div style={styles.twoColGrid}>
                    <div style={styles.formGroup}>
                      <label style={styles.label}>前置条件</label>
                      <textarea
                        name="pre_condition"
                        className="form-input"
                        value={formData.pre_condition || ''}
                        onChange={handleChange}
                        placeholder="测试执行前的准备条件"
                        rows={2}
                        style={styles.textarea}
                      />
                    </div>

                    <div style={styles.formGroup}>
                      <label style={styles.label}>后置条件</label>
                      <textarea
                        name="post_condition"
                        className="form-input"
                        value={formData.post_condition || ''}
                        onChange={handleChange}
                        placeholder="测试执行后的预期状态"
                        rows={2}
                        style={styles.textarea}
                      />
                    </div>
                  </div>

                  <div style={styles.formGroup}>
                    <label style={styles.label}>标签</label>
                    <div style={styles.tagInputRow}>
                      <input
                        type="text"
                        className="form-input"
                        value={newTag}
                        onChange={e => setNewTag(e.target.value)}
                        placeholder="输入标签后回车或点击添加"
                        onKeyDown={e => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleAddTag();
                          }
                        }}
                      />
                      <button type="button" className="btn btn--secondary btn--sm" onClick={handleAddTag}>
                        添加
                      </button>
                    </div>
                    {formData.tags && formData.tags.length > 0 && (
                      <div style={styles.tagList}>
                        {formData.tags.map((tag, index) => (
                          <span key={index} style={styles.tag}>
                            {tag}
                            <button
                              type="button"
                              style={styles.tagRemove}
                              onClick={() => handleRemoveTag(tag)}
                              aria-label={`移除标签 ${tag}`}
                            >
                              ×
                            </button>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <label style={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      name="is_destructive"
                      checked={formData.is_destructive}
                      onChange={handleChange}
                    />
                    <span>破坏性测试</span>
                  </label>
                </FormSection>
                  </>
                )}

              </div>
            )}

            {activeTab === 'steps' && (
              <div
                id="test-case-panel-steps"
                role="tabpanel"
                aria-labelledby="test-case-tab-steps"
                style={styles.tabStack}
              >
                {!isEditMode && (
                  <p style={styles.stepsHint}>
                    可先创建草稿，稍后在编辑中补充步骤
                  </p>
                )}

                <FormSection title="执行步骤" badge="可选">
                  <TestCaseStepEditorV2
                    steps={formData.steps ?? []}
                    onChange={steps => setFormData(prev => ({ ...prev, steps }))}
                    testCaseTitle={formData.title}
                    category={formData.test_category}
                    preCondition={formData.pre_condition}
                    postCondition={formData.post_condition}
                  />
                </FormSection>

                <section style={styles.cleanupSection}>
                  <button
                    type="button"
                    style={styles.cleanupToggle}
                    onClick={() => setCleanupExpanded(v => !v)}
                    aria-expanded={cleanupExpanded}
                  >
                    <span style={styles.cleanupChevron} aria-hidden>
                      {cleanupExpanded ? '▾' : '▸'}
                    </span>
                    <span style={styles.cleanupTitle}>清理步骤</span>
                    <span style={styles.sectionBadge}>可选</span>
                    {(formData.cleanup_steps?.length ?? 0) > 0 && (
                      <span style={styles.cleanupCount}>{formData.cleanup_steps?.length}</span>
                    )}
                  </button>
                  {cleanupExpanded && (
                    <div style={styles.cleanupBody}>
                      <TestCaseStepEditor
                        steps={formData.cleanup_steps ?? []}
                        onChange={cleanup_steps => setFormData(prev => ({ ...prev, cleanup_steps }))}
                        emptyHint="破坏性测试建议填写清理步骤"
                      />
                    </div>
                  )}
                </section>

                {isEditMode && (
                  <FormSection title="版本说明" badge={stepsDirty ? '建议填写' : '可选'}>
                    <div style={styles.formGroup}>
                      <label style={styles.label}>
                        变更说明 (change_log)
                        {stepsDirty && <span style={styles.changeLogHint}>步骤已修改，建议填写版本说明</span>}
                      </label>
                      <textarea
                        name="change_log"
                        className="form-input"
                        value={formData.change_log || ''}
                        onChange={handleChange}
                        placeholder="描述本次步骤或内容变更"
                        rows={3}
                        style={{
                          ...styles.textarea,
                          ...(stepsDirty ? styles.changeLogHighlight : {}),
                        }}
                      />
                    </div>
                  </FormSection>
                )}
              </div>
            )}

            {activeTab === 'automation' && (
              <div
                id="test-case-panel-automation"
                role="tabpanel"
                aria-labelledby="test-case-tab-automation"
                style={styles.tabStack}
              >
                <FormSection title="自动化配置">
                  <div style={styles.checkboxRow}>
                    <label style={styles.checkboxLabel}>
                      <input
                        type="checkbox"
                        name="is_need_auto"
                        checked={formData.is_need_auto}
                        onChange={handleChange}
                      />
                      <span>需要自动化</span>
                    </label>
                    <label style={styles.checkboxLabel}>
                      <input
                        type="checkbox"
                        name="is_automated"
                        checked={formData.is_automated}
                        onChange={handleChange}
                      />
                      <span>已实现自动化</span>
                    </label>
                  </div>

                  <div style={styles.twoColGrid}>
                    <div style={styles.formGroup}>
                      <label style={styles.label}>自动化类型</label>
                      <input
                        type="text"
                        name="automation_type"
                        className="form-input"
                        value={formData.automation_type || ''}
                        onChange={handleChange}
                        placeholder="Selenium / Appium / Cypress 等"
                      />
                    </div>
                    <div style={styles.formGroup}>
                      <label style={styles.label}>脚本实体 ID</label>
                      <input
                        type="text"
                        name="script_entity_id"
                        className="form-input"
                        value={formData.script_entity_id || ''}
                        onChange={handleChange}
                        placeholder="脚本 ID"
                      />
                    </div>
                  </div>

                  <div style={styles.formGroup}>
                    <label style={styles.label}>风险等级</label>
                    <select
                      name="risk_level"
                      className="form-input form-select"
                      value={formData.risk_level || ''}
                      onChange={handleChange}
                    >
                      <option value="">选择风险等级</option>
                      <option value="LOW">低风险</option>
                      <option value="MEDIUM">中风险</option>
                      <option value="HIGH">高风险</option>
                      <option value="CRITICAL">严重风险</option>
                    </select>
                  </div>

                  <div style={styles.formGroup}>
                    <label style={styles.label}>失败分析</label>
                    <textarea
                      name="failure_analysis"
                      className="form-input"
                      value={formData.failure_analysis || ''}
                      onChange={handleChange}
                      placeholder="可能的失败原因与分析"
                      rows={5}
                      style={styles.textarea}
                    />
                  </div>
                </FormSection>
              </div>
            )}
          </div>

          <div style={styles.modalFooter}>
            <button type="button" className="btn btn--secondary btn--sm" onClick={onClose} disabled={loading}>取消</button>
            <button type="submit" className="btn btn--primary btn--sm" disabled={loading}>
              {loading ? (isEditMode ? '保存中…' : '创建中…') : (isEditMode ? '保存修改' : '创建测试用例')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  errorBanner: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 'var(--space-2)',
    margin: 'var(--space-4) var(--space-6) 0',
    padding: 'var(--space-3) var(--space-4)',
    backgroundColor: 'var(--status-error-bg)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    fontSize: 13,
    color: 'var(--text-primary)',
  },
  errorIcon: {
    flexShrink: 0,
    width: 20,
    height: 20,
    borderRadius: '50%',
    backgroundColor: 'var(--status-error)',
    color: 'white',
    fontSize: 12,
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
    minHeight: 0,
  },
  tabs: {
    display: 'flex',
    borderBottom: '1px solid var(--border-subtle)',
    padding: '0 var(--space-6)',
    gap: 'var(--space-2)',
  },
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
  },
  activeTab: {
    color: 'var(--accent-primary)',
    borderBottom: '2px solid var(--accent-primary)',
    outline: 'none',
  },
  tabBadge: {
    marginLeft: 6,
    fontSize: 11,
    fontWeight: 600,
    padding: '1px 6px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'color-mix(in srgb, var(--accent-primary) 15%, transparent)',
    color: 'var(--accent-primary)',
  },
  stepsHint: {
    margin: 0,
    fontSize: 12,
    color: 'var(--text-secondary)',
    padding: 'var(--space-2) var(--space-3)',
    backgroundColor: 'var(--surface-secondary)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-subtle)',
  },
  cleanupSection: {
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-lg)',
    overflow: 'hidden',
    backgroundColor: 'var(--surface-primary)',
  },
  cleanupToggle: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
    width: '100%',
    padding: 'var(--space-3) var(--space-4)',
    border: 'none',
    backgroundColor: 'var(--surface-secondary)',
    cursor: 'pointer',
    textAlign: 'left' as const,
  },
  cleanupChevron: {
    fontSize: 12,
    color: 'var(--text-secondary)',
  },
  cleanupTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  cleanupCount: {
    marginLeft: 'auto',
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-secondary)',
  },
  cleanupBody: {
    padding: 'var(--space-4)',
  },
  changeLogHint: {
    marginLeft: 'var(--space-2)',
    fontSize: 11,
    color: 'var(--status-warning)',
    fontWeight: 500,
  },
  changeLogHighlight: {
    border: '1px solid var(--status-warning)',
    backgroundColor: 'var(--status-warning-bg)',
  },
  quickCreateCard: {
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-lg)',
    overflow: 'hidden',
    backgroundColor: 'var(--surface-primary)',
    boxShadow: 'var(--shadow-sm)',
  },
  quickCreateHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
    padding: 'var(--space-3) var(--space-4)',
    backgroundColor: 'var(--surface-secondary)',
    borderBottom: '1px solid var(--border-subtle)',
  },
  quickCreateTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  quickCreateBadge: {
    fontSize: 10,
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'color-mix(in srgb, var(--accent-primary) 12%, transparent)',
    color: 'var(--accent-primary)',
  },
  quickCreateBody: {
    padding: 'var(--space-4)',
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-4)',
  },
  priorityPills: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 'var(--space-2)',
  },
  priorityPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '6px 12px',
    fontSize: 12,
    fontWeight: 500,
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--surface-primary)',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    transition: 'background-color var(--transition-fast), color var(--transition-fast)',
  },
  priorityPillActive: {
    backgroundColor: 'var(--surface-secondary)',
    color: 'var(--text-primary)',
    fontWeight: 600,
    boxShadow: 'var(--shadow-sm)',
  },
  priorityPillDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    flexShrink: 0,
  },
  advancedToggle: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
    width: '100%',
    padding: 'var(--space-3) var(--space-4)',
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-md)',
    backgroundColor: 'var(--surface-secondary)',
    color: 'var(--text-primary)',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    textAlign: 'left',
  },
  advancedHint: {
    marginLeft: 'auto',
    fontSize: 12,
    fontWeight: 400,
    color: 'var(--text-tertiary)',
  },
  advancedChevron: {
    fontSize: 12,
    color: 'var(--text-tertiary)',
    width: 18,
    textAlign: 'center',
  },
  modalBody: {
    flex: 1,
    overflowY: 'auto',
    padding: 'var(--space-6)',
  },
  tabStack: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-5)',
  },
  section: {
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-lg)',
    overflow: 'hidden',
    backgroundColor: 'var(--surface-primary)',
  },
  sectionProminent: {
    border: '2px solid var(--accent-primary)',
    boxShadow: 'var(--shadow-sm)',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
    padding: 'var(--space-3) var(--space-4)',
    backgroundColor: 'var(--surface-secondary)',
    borderBottom: '1px solid var(--border-subtle)',
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--text-primary)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  sectionBadge: {
    fontSize: 10,
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--surface-tertiary)',
    color: 'var(--text-tertiary)',
  },
  sectionBadgeProminent: {
    fontSize: 10,
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--accent-primary)',
    color: 'white',
  },
  sectionContent: {
    padding: 'var(--space-4)',
  },
  twoColGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
    gap: 'var(--space-4)',
  },
  threeColGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
    gap: 'var(--space-4)',
    marginBottom: 'var(--space-4)',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-2)',
  },
  label: {
    fontSize: 12,
    fontWeight: 500,
    color: 'var(--text-secondary)',
  },
  required: {
    color: 'var(--status-error)',
    marginLeft: 4,
  },
  optionalHint: {
    marginLeft: 6,
    fontWeight: 400,
    fontSize: 11,
    color: 'var(--text-tertiary)',
  },
  helperText: {
    margin: 0,
    fontSize: 12,
    color: 'var(--text-tertiary)',
  },
  selectWrapper: {
    position: 'relative',
  },
  priorityDot: {
    position: 'absolute',
    right: 12,
    top: '50%',
    transform: 'translateY(-50%)',
    width: 8,
    height: 8,
    borderRadius: '50%',
    pointerEvents: 'none',
  },
  inputWrapper: {
    position: 'relative',
  },
  inputLocked: {
    backgroundColor: 'var(--surface-secondary)',
    color: 'var(--text-secondary)',
  },
  lockedBadge: {
    position: 'absolute',
    right: 10,
    top: '50%',
    transform: 'translateY(-50%)',
    fontSize: 10,
    padding: '2px 8px',
    backgroundColor: 'var(--surface-tertiary)',
    color: 'var(--text-secondary)',
    borderRadius: 'var(--radius-full)',
    border: '1px solid var(--border-default)',
  },
  textarea: {
    resize: 'vertical',
    minHeight: 64,
  },
  tagInputRow: {
    display: 'flex',
    gap: 'var(--space-2)',
  },
  tagList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 'var(--space-2)',
    marginTop: 'var(--space-2)',
  },
  tag: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    padding: '4px 10px',
    backgroundColor: 'var(--surface-secondary)',
    borderRadius: 'var(--radius-full)',
    fontSize: 12,
  },
  tagRemove: {
    border: 'none',
    background: 'none',
    cursor: 'pointer',
    color: 'var(--text-tertiary)',
    fontSize: 14,
    lineHeight: 1,
    padding: 0,
  },
  checkboxRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 'var(--space-5)',
    marginBottom: 'var(--space-4)',
  },
  checkboxLabel: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
    fontSize: 13,
    color: 'var(--text-primary)',
    cursor: 'pointer',
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 'var(--space-3)',
    padding: 'var(--space-4) var(--space-6)',
    borderTop: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--surface-secondary)',
    borderRadius: '0 0 var(--radius-lg) var(--radius-lg)',
  },
};

export default CreateTestCaseForm;
