import React, { useState } from 'react';
import { api } from '../services/api';
import type { CreateTestCaseRequest } from '../types';

interface CreateTestCaseFormProps {
  onClose: () => void;
  onSuccess: () => void;
  defaultRequirementId?: string;
  lockRequirementId?: boolean;
}

const CreateTestCaseForm: React.FC<CreateTestCaseFormProps> = ({
  onClose,
  onSuccess,
  defaultRequirementId = '',
  lockRequirementId = false,
}) => {
  const [formData, setFormData] = useState<CreateTestCaseRequest>({
    ref_req_id: defaultRequirementId,
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
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'basic' | 'automation'>('basic');
  const [newTag, setNewTag] = useState('');
  const [steps, setSteps] = useState<Array<{ id: string; content: string; expected: string }>>([]);
  const [stepCounter, setStepCounter] = useState(0);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await api.createTestCase(formData);
      onSuccess();
      onClose();
    } catch (err) {
      setError('创建测试用例失败');
      console.error('Create test case error:', err);
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
    if (newTag) {
      setFormData(prev => ({
        ...prev,
        tags: [...(prev.tags || []), newTag],
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

  const handleAddStep = () => {
    const newStepId = `STEP-${String(stepCounter + 1).padStart(3, '0')}`;
    setSteps(prev => [...prev, { id: newStepId, content: '', expected: '' }]);
    setStepCounter(prev => prev + 1);
  };

  const handleRemoveStep = (stepId: string) => {
    setSteps(prev => prev.filter(step => step.id !== stepId));
  };

  const handleStepChange = (stepId: string, field: 'content' | 'expected', value: string) => {
    setSteps(prev => prev.map(step => 
      step.id === stepId ? { ...step, [field]: value } : step
    ));
  };

  const priorityColors = {
    P0: '#d93021',
    P1: '#f66a0a',
    P2: '#e3b30e',
    P3: '#0b7ece',
  };

  const priorityLabels = {
    P0: '紧急',
    P1: '高',
    P2: '中',
    P3: '低',
  };

  return (
    <div style={styles.modalOverlay}>
      <div style={styles.modalContent}>
        <div style={styles.modalHeader}>
          <div>
            <h2 style={styles.modalTitle}>创建测试用例</h2>
            <p style={styles.modalSubtitle}>定义测试范围和执行步骤</p>
          </div>
          <button style={styles.closeButton} onClick={onClose}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        {error && (
          <div style={styles.errorMessage}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.tabs}>
            <button
              type="button"
              style={{
                ...styles.tab,
                ...(activeTab === 'basic' ? styles.activeTab : {}),
              }}
              onClick={() => setActiveTab('basic')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 8 }}>
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
              </svg>
              基本信息
            </button>
            <button
              type="button"
              style={{
                ...styles.tab,
                ...(activeTab === 'automation' ? styles.activeTab : {}),
              }}
              onClick={() => setActiveTab('automation')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 8 }}>
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
              </svg>
              自动化
            </button>
          </div>

          <div style={styles.modalBody}>
            {activeTab === 'basic' && (
              <div style={styles.tabContent}>
                <div style={styles.formGrid}>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>
                      需求编号
                      <span style={styles.required}>*</span>
                    </label>
                    <div style={styles.inputWrapper}>
                      <input
                        type="text"
                        name="ref_req_id"
                        value={formData.ref_req_id}
                        onChange={handleChange}
                        style={styles.input}
                        placeholder="REQ-001"
                        required
                        readOnly={lockRequirementId}
                      />
                      {lockRequirementId && (
                        <span style={styles.lockedBadge}>锁定</span>
                      )}
                    </div>
                  </div>

                  <div style={styles.formGroup}>
                    <label style={styles.label}>
                      用例名称
                      <span style={styles.required}>*</span>
                    </label>
                    <input
                      type="text"
                      name="title"
                      value={formData.title}
                      onChange={handleChange}
                      style={styles.input}
                      placeholder="输入用例名称"
                      required
                    />
                  </div>

                  <div style={styles.formGroup}>
                    <label style={styles.label}>优先级</label>
                    <div style={styles.selectWrapper}>
                      <select
                        name="priority"
                        value={formData.priority}
                        onChange={handleChange}
                        style={styles.select}
                      >
                        {Object.entries(priorityLabels).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label} ({value})
                          </option>
                        ))}
                      </select>
                      <span style={{ ...styles.priorityIndicator, backgroundColor: priorityColors[formData.priority as keyof typeof priorityColors] }} />
                    </div>
                  </div>

                  <div style={styles.formGroup}>
                    <label style={styles.label}>预估时间</label>
                    <input
                      type="number"
                      name="estimated_duration_sec"
                      value={formData.estimated_duration_sec || ''}
                      onChange={handleChange}
                      style={styles.input}
                      placeholder="60"
                      min="0"
                    />
                  </div>

                  <div style={styles.formGroup}>
                    <label style={styles.label}>测试分类</label>
                    <input
                      type="text"
                      name="test_category"
                      value={formData.test_category || ''}
                      onChange={handleChange}
                      style={styles.input}
                      placeholder="功能测试/性能测试等"
                    />
                  </div>

                  <div style={styles.formGroup}>
                    <label style={styles.label}>状态</label>
                    <select
                      name="is_active"
                      value={formData.is_active ? 'true' : 'false'}
                      onChange={handleChange}
                      style={styles.select}
                    >
                      <option value="true">激活</option>
                      <option value="false">未激活</option>
                    </select>
                  </div>
                </div>

                <div style={styles.formRow}>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>前置条件</label>
                    <textarea
                      name="pre_condition"
                      value={formData.pre_condition || ''}
                      onChange={handleChange}
                      style={styles.textarea}
                      placeholder="描述测试执行前的准备条件"
                      rows={2}
                    />
                  </div>

                  <div style={styles.formGroup}>
                    <label style={styles.label}>后置条件</label>
                    <textarea
                      name="post_condition"
                      value={formData.post_condition || ''}
                      onChange={handleChange}
                      style={styles.textarea}
                      placeholder="描述测试执行后的状态"
                      rows={2}
                    />
                  </div>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>标签</label>
                  <div style={styles.tagInputContainer}>
                    <input
                      type="text"
                      value={newTag}
                      onChange={(e) => setNewTag(e.target.value)}
                      style={styles.tagInput}
                      placeholder="输入标签后按回车"
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                    />
                    <button
                      type="button"
                      style={styles.addTagButton}
                      onClick={handleAddTag}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 5v14M5 12h14"></path>
                      </svg>
                      添加
                    </button>
                  </div>
                  <div style={styles.tagList}>
                    {formData.tags?.map((tag, index) => (
                      <span key={index} style={styles.tag}>
                        <span style={styles.tagText}>{tag}</span>
                        <button
                          type="button"
                          style={styles.tagRemove}
                          onClick={() => handleRemoveTag(tag)}
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                          </svg>
                        </button>
                      </span>
                    ))}
                  </div>
                </div>

                <div style={styles.checkboxSection}>
                  <label style={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      name="is_destructive"
                      checked={formData.is_destructive}
                      onChange={handleChange}
                      style={styles.checkbox}
                    />
                    <span style={styles.checkboxText}>是否为破坏性测试</span>
                  </label>
                </div>

                <div style={styles.compactStepForm}>
                  <div style={styles.stepHeader}>
                    <div style={styles.sectionTitle}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 8 }}>
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                      </svg>
                      测试步骤
                    </div>
                    <button
                      type="button"
                      style={styles.addStepButton}
                      onClick={handleAddStep}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                      </svg>
                      添加步骤
                    </button>
                  </div>
                  <div style={styles.stepsList}>
                    {steps.length === 0 ? (
                      <div style={styles.emptyState}>
                        <div style={styles.emptyIcon}>
                          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                            <line x1="16" y1="13" x2="8" y2="13"></line>
                            <line x1="16" y1="17" x2="8" y2="17"></line>
                            <polyline points="10 9 9 9 8 9"></polyline>
                          </svg>
                        </div>
                        <p style={styles.emptyText}>暂无测试步骤</p>
                        <p style={styles.emptySubtext}>点击上方按钮添加测试步骤</p>
                        <button
                          type="button"
                          style={styles.emptyActionButton}
                          onClick={handleAddStep}
                        >
                          立即添加
                        </button>
                      </div>
                    ) : (
                      <div style={styles.stepItems}>
                        {steps.map((step) => (
                          <div key={step.id} style={styles.stepItem}>
                            <div style={styles.stepHeaderRow}>
                              <div style={styles.stepBadge}>
                                <span style={styles.stepIndex}>{step.id}</span>
                              </div>
                              <button
                                type="button"
                                style={styles.removeStepButton}
                                onClick={() => handleRemoveStep(step.id)}
                              >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                  <line x1="18" y1="6" x2="6" y2="18"></line>
                                  <line x1="6" y1="6" x2="18" y2="18"></line>
                                </svg>
                              </button>
                            </div>
                            <div style={styles.stepInputs}>
                              <div style={styles.stepInputWrapper}>
                                <label style={styles.stepLabel}>步骤内容</label>
                                <textarea
                                  value={step.content}
                                  onChange={(e) => handleStepChange(step.id, 'content', e.target.value)}
                                  style={styles.textarea}
                                  placeholder="描述具体的测试操作步骤"
                                  rows={2}
                                />
                              </div>
                              <div style={styles.stepInputWrapper}>
                                <label style={styles.stepLabel}>期望结果</label>
                                <textarea
                                  value={step.expected}
                                  onChange={(e) => handleStepChange(step.id, 'expected', e.target.value)}
                                  style={styles.textarea}
                                  placeholder="描述预期的测试结果"
                                  rows={2}
                                />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'automation' && (
              <div style={styles.tabContent}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>自动化配置</label>
                  <div style={styles.formGrid}>
                    <div style={styles.formGroup}>
                      <label style={styles.checkboxLabel}>
                        <input
                          type="checkbox"
                          name="is_need_auto"
                          checked={formData.is_need_auto}
                          onChange={handleChange}
                          style={styles.checkbox}
                        />
                        <span style={styles.checkboxText}>需要自动化</span>
                      </label>
                    </div>

                    <div style={styles.formGroup}>
                      <label style={styles.checkboxLabel}>
                        <input
                          type="checkbox"
                          name="is_automated"
                          checked={formData.is_automated}
                          onChange={handleChange}
                          style={styles.checkbox}
                        />
                        <span style={styles.checkboxText}>已实现自动化</span>
                      </label>
                    </div>
                  </div>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>自动化类型</label>
                  <div style={styles.inputWrapper}>
                    <input
                      type="text"
                      name="automation_type"
                      value={formData.automation_type || ''}
                      onChange={handleChange}
                      style={styles.input}
                      placeholder="Selenium/Appium/Cypress等"
                    />
                    <span style={styles.inputIcon}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                      </svg>
                    </span>
                  </div>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>脚本实体ID</label>
                  <input
                    type="text"
                    name="script_entity_id"
                    value={formData.script_entity_id || ''}
                    onChange={handleChange}
                    style={styles.input}
                    placeholder="脚本ID"
                  />
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>风险等级</label>
                  <div style={styles.selectWrapper}>
                    <select
                      name="risk_level"
                      value={formData.risk_level || ''}
                      onChange={handleChange}
                      style={styles.select}
                    >
                      <option value="">选择风险等级</option>
                      <option value="LOW">低风险</option>
                      <option value="MEDIUM">中风险</option>
                      <option value="HIGH">高风险</option>
                      <option value="CRITICAL">严重风险</option>
                    </select>
                    <span style={styles.selectIcon}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"></path>
                      </svg>
                    </span>
                  </div>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>失败分析</label>
                  <textarea
                    name="failure_analysis"
                    value={formData.failure_analysis || ''}
                    onChange={handleChange}
                    style={styles.textarea}
                    placeholder="描述可能的失败原因和分析"
                    rows={6}
                  />
                </div>
              </div>
            )}
          </div>

          <div style={styles.modalFooter}>
            <button
              type="button"
              style={styles.cancelButton}
              onClick={onClose}
              disabled={loading}
            >
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
              {loading ? (
                <span style={styles.loadingContent}>
                  <svg className="spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" opacity="0.25"></circle>
                    <path d="M12 2a10 10 0 0 1 10 10h-2a8 8 0 0 0-8-8v2z"></path>
                  </svg>
                  创建中...
                </span>
              ) : (
                <span style={styles.submitContent}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                  创建测试用例
                </span>
              )}
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
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(15, 23, 42, 0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    animation: 'fadeIn 0.2s ease',
    backdropFilter: 'blur(4px)',
  } as const,
  modalContent: {
    backgroundColor: 'var(--bg-primary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    width: '90%',
    maxWidth: '900px',
    maxHeight: '90vh',
    overflow: 'auto' as const,
    boxShadow: 'var(--shadow-lg)',
    animation: 'scaleIn 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
  } as const,
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px 24px',
    borderBottom: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-tertiary)',
    borderRadius: 'var(--radius-lg) var(--radius-lg) 0 0',
  } as const,
  modalTitle: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    lineHeight: 1.4,
  } as const,
  modalSubtitle: {
    margin: '4px 0 0',
    fontSize: '13px',
    color: 'var(--text-secondary)',
  } as const,
  closeButton: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: 'var(--text-secondary)',
    padding: '8px',
    width: '36px',
    height: '36px',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all var(--transition-fast)',
  } as const,
  errorMessage: {
    padding: '16px 20px',
    backgroundColor: 'var(--status-error-bg)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-primary)',
    fontSize: '14px',
    margin: '0 24px 20px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  } as const,
  form: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: 'calc(90vh - 100px)',
  } as const,
  tabs: {
    display: 'flex',
    borderBottom: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-primary)',
  } as const,
  tab: {
    flex: 1,
    padding: '16px 20px',
    border: 'none',
    backgroundColor: 'transparent',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500,
    transition: 'all var(--transition-fast)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  } as const,
  activeTab: {
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--accent-cyan)',
    borderBottom: '2px solid var(--accent-cyan)',
  } as const,
  modalBody: {
    flex: 1,
    overflow: 'auto' as const,
    padding: '24px',
  } as const,
  tabContent: {
    display: 'block',
  } as const,
  formGroup: {
    marginBottom: '20px',
  } as const,
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '20px',
    marginBottom: '20px',
  } as const,
  formRow: {
    display: 'flex',
    gap: '20px',
    marginBottom: '20px',
  } as const,
  checkboxSection: {
    marginBottom: '20px',
    padding: '16px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-md)',
  } as const,
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    marginBottom: '8px',
    letterSpacing: '0.2px',
  } as const,
  helperText: {
    display: 'inline-block',
    marginTop: '8px',
    fontSize: '12px',
    color: 'var(--text-muted)',
  } as const,
  required: {
    color: 'var(--accent-red)',
    marginLeft: 4,
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
    transition: 'all var(--transition-fast)',
  } as const,
  textarea: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    resize: 'vertical' as const,
    minHeight: '60px',
    transition: 'all var(--transition-fast)',
  } as const,
  select: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  inputWrapper: {
    position: 'relative' as const,
  } as const,
  selectWrapper: {
    position: 'relative' as const,
  } as const,
  inputIcon: {
    position: 'absolute' as const,
    right: '12px',
    top: '50%',
    transform: 'translateY(-50%)',
    color: 'var(--text-muted)',
  } as const,
  selectIcon: {
    position: 'absolute' as const,
    right: '12px',
    top: '50%',
    transform: 'translateY(-50%)',
    color: 'var(--text-muted)',
  } as const,
  lockedBadge: {
    position: 'absolute' as const,
    right: '40px',
    top: '50%',
    transform: 'translateY(-50%)',
    fontSize: '10px',
    padding: '2px 8px',
    backgroundColor: 'var(--bg-tertiary)',
    color: 'var(--text-secondary)',
    borderRadius: '10px',
    border: '1px solid var(--border-default)',
  } as const,
  priorityIndicator: {
    position: 'absolute' as const,
    right: '12px',
    top: '50%',
    transform: 'translateY(-50%)',
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  } as const,
  tagInputContainer: {
    display: 'flex',
    gap: '8px',
    marginBottom: '12px',
  } as const,
  tagInput: {
    flex: 1,
    padding: '8px 12px',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    fontSize: '13px',
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
    transition: 'all var(--transition-fast)',
  } as const,
  addTagButton: {
    padding: '8px 16px',
    backgroundColor: 'var(--bg-secondary)',
    color: 'var(--text-primary)',
    fontSize: '13px',
    fontWeight: 500,
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    transition: 'all var(--transition-fast)',
  } as const,
  tagList: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '8px',
  } as const,
  tag: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 10px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: '12px',
    fontSize: '12px',
    color: 'var(--text-primary)',
  } as const,
  tagText: {
    color: 'var(--text-primary)',
  } as const,
  tagRemove: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: 'var(--text-muted)',
    padding: '2px',
    borderRadius: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all var(--transition-fast)',
  } as const,
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    cursor: 'pointer',
    fontSize: '14px',
    color: 'var(--text-primary)',
  } as const,
  checkboxText: {
    fontSize: '14px',
    color: 'var(--text-primary)',
  } as const,
  checkbox: {
    width: '18px',
    height: '18px',
    cursor: 'pointer',
    accentColor: 'var(--accent-cyan)',
  } as const,
  compactStepForm: {
    marginTop: '24px',
  } as const,
  stepHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  } as const,
  sectionTitle: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '15px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  } as const,
  addStepButton: {
    padding: '8px 16px',
    backgroundColor: 'var(--accent-cyan)',
    color: 'white',
    fontSize: '13px',
    fontWeight: 500,
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    transition: 'all var(--transition-fast)',
  } as const,
  stepsList: {
    minHeight: '200px',
  } as const,
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px 20px',
    textAlign: 'center',
  } as const,
  emptyIcon: {
    marginBottom: '16px',
    color: 'var(--border-default)',
  } as const,
  emptyText: {
    fontSize: '15px',
    fontWeight: 500,
    color: 'var(--text-primary)',
    marginBottom: '8px',
  } as const,
  emptySubtext: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
    marginBottom: '20px',
  } as const,
  emptyActionButton: {
    padding: '10px 24px',
    backgroundColor: 'var(--accent-cyan)',
    color: 'white',
    fontSize: '14px',
    fontWeight: 500,
    borderRadius: 'var(--radius-md)',
    transition: 'all var(--transition-fast)',
  } as const,
  stepItems: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '16px',
  } as const,
  stepItem: {
    padding: '16px',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    transition: 'all var(--transition-fast)',
  } as const,
  stepHeaderRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  } as const,
  stepBadge: {
    padding: '4px 10px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: '6px',
  } as const,
  stepIndex: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    fontFamily: 'JetBrains Mono, monospace',
  } as const,
  removeStepButton: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: 'var(--text-muted)',
    padding: '6px',
    borderRadius: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all var(--transition-fast)',
  } as const,
  stepInputs: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '12px',
  } as const,
  stepInputWrapper: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '6px',
  } as const,
  stepLabel: {
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    letterSpacing: '0.2px',
  } as const,
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    padding: '16px 24px',
    borderTop: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-tertiary)',
    borderRadius: '0 0 var(--radius-lg) var(--radius-lg)',
  } as const,
  cancelButton: {
    padding: '10px 20px',
    backgroundColor: 'var(--bg-secondary)',
    color: 'var(--text-primary)',
    fontSize: '14px',
    fontWeight: 500,
    borderRadius: 'var(--radius-md)',
    transition: 'all var(--transition-fast)',
  } as const,
  submitButton: {
    padding: '10px 24px',
    backgroundColor: 'var(--accent-cyan)',
    color: 'white',
    fontSize: '14px',
    fontWeight: 500,
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'all var(--transition-fast)',
  } as const,
  buttonDisabled: {
    opacity: 0.6,
    cursor: 'not-allowed',
  } as const,
  loadingContent: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  } as const,
  submitContent: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  } as const,
};

export default CreateTestCaseForm;
