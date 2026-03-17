import React, { useState } from 'react';
import { api } from '../services/api';
import type { CreateTestCaseRequest, TestCaseStep } from '../types';

interface CreateTestCaseFormProps {
  onClose: () => void;
  onSuccess: () => void;
}

const CreateTestCaseForm: React.FC<CreateTestCaseFormProps> = ({ onClose, onSuccess }) => {
  const [formData, setFormData] = useState<CreateTestCaseRequest>({
    ref_req_id: '',
    title: '',
    version: 1,
    is_active: true,
    priority: 'P1',
    target_components: [],
    tags: [],
    tooling_req: [],
    is_destructive: false,
    cleanup_steps: [],
    steps: [],
    is_need_auto: false,
    is_automated: false,
    attachments: [],
    custom_fields: {},
    approval_history: [],
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'basic' | 'steps' | 'automation'>('basic');
  const [newStep, setNewStep] = useState<TestCaseStep>({
    step_id: '',
    name: '',
    action: '',
    expected: '',
  });
  const [newComponent, setNewComponent] = useState('');
  const [newTag, setNewTag] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
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

  const handleAddStep = () => {
    if (newStep.name && newStep.action && newStep.expected) {
      const step: TestCaseStep = {
        step_id: newStep.step_id || `step_${Date.now()}`,
        name: newStep.name,
        action: newStep.action,
        expected: newStep.expected,
      };
      setFormData(prev => ({
        ...prev,
        steps: [...(prev.steps || []), step],
      }));
      setNewStep({ step_id: '', name: '', action: '', expected: '' });
    }
  };

  const handleRemoveStep = (stepId: string) => {
    setFormData(prev => ({
      ...prev,
      steps: prev.steps?.filter(s => s.step_id !== stepId) || [],
    }));
  };

  const handleAddComponent = () => {
    if (newComponent) {
      setFormData(prev => ({
        ...prev,
        target_components: [...(prev.target_components || []), newComponent],
      }));
      setNewComponent('');
    }
  };

  const handleRemoveComponent = (component: string) => {
    setFormData(prev => ({
      ...prev,
      target_components: prev.target_components?.filter(c => c !== component) || [],
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

  return (
    <div style={styles.modalOverlay}>
      <div style={styles.modalContent}>
        <div style={styles.modalHeader}>
          <h2 style={styles.modalTitle}>创建测试用例</h2>
          <button style={styles.closeButton} onClick={onClose}>×</button>
        </div>

        {error && (
          <div style={styles.errorMessage}>
            {error}
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
              基本信息
            </button>
            <button
              type="button"
              style={{
                ...styles.tab,
                ...(activeTab === 'steps' ? styles.activeTab : {}),
              }}
              onClick={() => setActiveTab('steps')}
            >
              测试步骤
            </button>
            <button
              type="button"
              style={{
                ...styles.tab,
                ...(activeTab === 'automation' ? styles.activeTab : {}),
              }}
              onClick={() => setActiveTab('automation')}
            >
              自动化
            </button>
          </div>

          <div style={styles.modalBody}>
            {activeTab === 'basic' && (
              <div style={styles.tabContent}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>
                    需求编号 <span style={styles.required}>*</span>
                  </label>
                  <input
                    type="text"
                    name="ref_req_id"
                    value={formData.ref_req_id}
                    onChange={handleChange}
                    style={styles.input}
                    placeholder="REQ-001"
                    required
                  />
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>
                    用例名称 <span style={styles.required}>*</span>
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

                <div style={styles.formRow}>
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

                  <div style={styles.formGroup}>
                    <label style={styles.label}>预估执行时间（秒）</label>
                    <input
                      type="number"
                      name="estimated_duration_sec"
                      value={formData.estimated_duration_sec || ''}
                      onChange={handleChange}
                      style={styles.input}
                      placeholder="60"
                    />
                  </div>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>前置条件</label>
                  <textarea
                    name="pre_condition"
                    value={formData.pre_condition || ''}
                    onChange={handleChange}
                    style={styles.textarea}
                    placeholder="描述测试执行前的准备条件"
                    rows={3}
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
                    rows={3}
                  />
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>目标组件</label>
                  <div style={styles.tagInputContainer}>
                    <input
                      type="text"
                      value={newComponent}
                      onChange={(e) => setNewComponent(e.target.value)}
                      style={styles.tagInput}
                      placeholder="输入组件名称"
                      onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddComponent())}
                    />
                    <button
                      type="button"
                      style={styles.addButton}
                      onClick={handleAddComponent}
                    >
                      添加
                    </button>
                  </div>
                  <div style={styles.tagList}>
                    {formData.target_components?.map((component, index) => (
                      <span key={index} style={styles.tag}>
                        {component}
                        <button
                          type="button"
                          style={styles.tagRemove}
                          onClick={() => handleRemoveComponent(component)}
                        >
                          ×
                        </button>
                      </span>
                    ))}
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
                      placeholder="输入标签"
                      onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                    />
                    <button
                      type="button"
                      style={styles.addButton}
                      onClick={handleAddTag}
                    >
                      添加
                    </button>
                  </div>
                  <div style={styles.tagList}>
                    {formData.tags?.map((tag, index) => (
                      <span key={index} style={styles.tag}>
                        {tag}
                        <button
                          type="button"
                          style={styles.tagRemove}
                          onClick={() => handleRemoveTag(tag)}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                </div>

                <div style={styles.formRow}>
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
                    <label style={styles.label}>激活状态</label>
                    <select
                      name="is_active"
                      value={formData.is_active ? 'true' : 'false'}
                      onChange={handleChange}
                      style={styles.input}
                    >
                      <option value="true">激活</option>
                      <option value="false">未激活</option>
                    </select>
                  </div>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      name="is_destructive"
                      checked={formData.is_destructive}
                      onChange={handleChange}
                      style={styles.checkbox}
                    />
                    是否为破坏性测试
                  </label>
                </div>
              </div>
            )}

            {activeTab === 'steps' && (
              <div style={styles.tabContent}>
                <div style={styles.stepForm}>
                  <h3 style={styles.sectionTitle}>添加测试步骤</h3>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>步骤名称</label>
                    <input
                      type="text"
                      value={newStep.name}
                      onChange={(e) => setNewStep({ ...newStep, name: e.target.value })}
                      style={styles.input}
                      placeholder="步骤名称"
                    />
                  </div>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>执行动作</label>
                    <textarea
                      value={newStep.action}
                      onChange={(e) => setNewStep({ ...newStep, action: e.target.value })}
                      style={styles.textarea}
                      placeholder="描述要执行的操作"
                      rows={3}
                    />
                  </div>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>预期结果</label>
                    <textarea
                      value={newStep.expected}
                      onChange={(e) => setNewStep({ ...newStep, expected: e.target.value })}
                      style={styles.textarea}
                      placeholder="描述预期的结果"
                      rows={3}
                    />
                  </div>
                  <button
                    type="button"
                    style={styles.addButton}
                    onClick={handleAddStep}
                  >
                    添加步骤
                  </button>
                </div>

                <div style={styles.stepsList}>
                  <h3 style={styles.sectionTitle}>已添加的步骤</h3>
                  {formData.steps?.length === 0 ? (
                    <p style={styles.emptyText}>暂无测试步骤</p>
                  ) : (
                    <div style={styles.stepItems}>
                      {formData.steps?.map((step, index) => (
                        <div key={step.step_id} style={styles.stepItem}>
                          <div style={styles.stepHeader}>
                            <span style={styles.stepIndex}>步骤 {index + 1}</span>
                            <button
                              type="button"
                              style={styles.removeButton}
                              onClick={() => handleRemoveStep(step.step_id)}
                            >
                              删除
                            </button>
                          </div>
                          <div style={styles.stepContent}>
                            <p><strong>名称:</strong> {step.name}</p>
                            <p><strong>动作:</strong> {step.action}</p>
                            <p><strong>预期:</strong> {step.expected}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'automation' && (
              <div style={styles.tabContent}>
                <div style={styles.formGroup}>
                  <label style={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      name="is_need_auto"
                      checked={formData.is_need_auto}
                      onChange={handleChange}
                      style={styles.checkbox}
                    />
                    是否需要自动化
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
                    是否已实现自动化
                  </label>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>自动化类型</label>
                  <input
                    type="text"
                    name="automation_type"
                    value={formData.automation_type || ''}
                    onChange={handleChange}
                    style={styles.input}
                    placeholder="Selenium/Appium等"
                  />
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
                  <select
                    name="risk_level"
                    value={formData.risk_level || ''}
                    onChange={handleChange}
                    style={styles.input}
                  >
                    <option value="">选择风险等级</option>
                    <option value="LOW">低</option>
                    <option value="MEDIUM">中</option>
                    <option value="HIGH">高</option>
                    <option value="CRITICAL">严重</option>
                  </select>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>失败分析</label>
                  <textarea
                    name="failure_analysis"
                    value={formData.failure_analysis || ''}
                    onChange={handleChange}
                    style={styles.textarea}
                    placeholder="描述可能的失败原因和分析"
                    rows={4}
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
              {loading ? '创建中...' : '创建'}
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
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    animation: 'fadeIn 0.2s ease',
  } as const,
  modalContent: {
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    width: '90%',
    maxWidth: '900px',
    maxHeight: '90vh',
    overflow: 'auto' as const,
    boxShadow: 'var(--shadow-lg)',
    animation: 'scaleIn 0.3s ease',
  } as const,
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px 24px',
    borderBottom: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-tertiary)',
  } as const,
  modalTitle: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  } as const,
  closeButton: {
    background: 'none',
    border: 'none',
    fontSize: '28px',
    cursor: 'pointer',
    color: 'var(--text-muted)',
    padding: 0,
    width: '30px',
    height: '30px',
    lineHeight: 1,
  } as const,
  errorMessage: {
    padding: '14px 18px',
    backgroundColor: 'var(--status-error-bg)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--accent-red)',
    fontSize: '14px',
    margin: '0 20px 20px',
  } as const,
  form: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: 'calc(90vh - 80px)',
  } as const,
  tabs: {
    display: 'flex',
    borderBottom: '1px solid var(--border-default)',
  } as const,
  tab: {
    flex: 1,
    padding: '15px',
    border: 'none',
    backgroundColor: 'transparent',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500,
    transition: 'all var(--transition-fast)',
  } as const,
  activeTab: {
    backgroundColor: 'var(--bg-secondary)',
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
  formRow: {
    display: 'flex',
    gap: '20px',
  } as const,
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    marginBottom: '8px',
    letterSpacing: '0.3px',
  } as const,
  required: {
    color: 'var(--accent-red)',
  } as const,
  input: {
    width: '100%',
    padding: '12px 14px',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
    transition: 'border-color var(--transition-fast)',
  } as const,
  textarea: {
    width: '100%',
    padding: '12px 14px',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    resize: 'vertical' as const,
    outline: 'none',
    fontFamily: 'inherit',
    transition: 'border-color var(--transition-fast)',
  } as const,
  tagInputContainer: {
    display: 'flex',
    gap: '10px',
    marginBottom: '10px',
  } as const,
  tagInput: {
    flex: 1,
    padding: '10px 14px',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
  } as const,
  addButton: {
    padding: '10px 18px',
    backgroundColor: 'var(--accent-green)',
    color: 'var(--bg-primary)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    fontSize: '13px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  tagList: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '8px',
  } as const,
  tag: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '6px 12px',
    backgroundColor: 'var(--bg-tertiary)',
    borderRadius: '16px',
    fontSize: '13px',
    gap: '8px',
    color: 'var(--text-primary)',
    border: '1px solid var(--border-default)',
  } as const,
  tagRemove: {
    background: 'none',
    border: 'none',
    fontSize: '18px',
    cursor: 'pointer',
    color: 'var(--text-muted)',
    padding: 0,
    lineHeight: 1,
  } as const,
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    fontSize: '14px',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
  } as const,
  checkbox: {
    width: '18px',
    height: '18px',
    cursor: 'pointer',
    accentColor: 'var(--accent-cyan)',
  } as const,
  sectionTitle: {
    fontSize: '15px',
    fontWeight: 600,
    marginBottom: '16px',
    color: 'var(--text-primary)',
  } as const,
  stepForm: {
    marginBottom: '30px',
    padding: '20px',
    backgroundColor: 'var(--bg-tertiary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-muted)',
  } as const,
  stepsList: {
    marginTop: '20px',
  } as const,
  emptyText: {
    textAlign: 'center' as const,
    color: 'var(--text-muted)',
    fontSize: '14px',
    padding: '30px',
  } as const,
  stepItems: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '12px',
  } as const,
  stepItem: {
    padding: '16px',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    backgroundColor: 'var(--bg-tertiary)',
  } as const,
  stepHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  } as const,
  stepIndex: {
    fontWeight: 600,
    color: 'var(--accent-cyan)',
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '13px',
  } as const,
  removeButton: {
    padding: '6px 14px',
    backgroundColor: 'var(--status-error-bg)',
    color: 'var(--accent-red)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    fontSize: '12px',
    fontWeight: 500,
    cursor: 'pointer',
  } as const,
  stepContent: {
    fontSize: '14px',
    lineHeight: 1.6,
    color: 'var(--text-secondary)',
  } as const,
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    padding: '20px 24px',
    borderTop: '1px solid var(--border-default)',
    backgroundColor: 'var(--bg-tertiary)',
  } as const,
  cancelButton: {
    padding: '12px 24px',
    backgroundColor: 'transparent',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  submitButton: {
    padding: '12px 28px',
    backgroundColor: 'var(--accent-cyan)',
    color: 'var(--bg-primary)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  buttonDisabled: {
    opacity: 0.6,
    cursor: 'not-allowed',
  } as const,
};

export default CreateTestCaseForm;
