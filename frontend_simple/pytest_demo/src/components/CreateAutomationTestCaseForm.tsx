import React, { useState } from 'react';
import { api } from '../services/api';
import type { CreateAutomationTestCaseRequest } from '../types';

interface CreateAutomationTestCaseFormProps {
  onClose: () => void;
  onSuccess: () => void;
}

const CreateAutomationTestCaseForm: React.FC<CreateAutomationTestCaseFormProps> = ({ onClose, onSuccess }) => {
  const [formData, setFormData] = useState<CreateAutomationTestCaseRequest>({
    name: '',
    version: '1.0.0',
    status: 'ACTIVE',
    framework: '',
    automation_type: '',
    repo_url: '',
    repo_branch: '',
    script_entity_id: '',
    entry_command: '',
    runtime_env: {},
    tags: [],
    maintainer_id: '',
    reviewer_id: '',
    description: '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'basic' | 'env' | 'advanced'>('basic');
  const [newTag, setNewTag] = useState('');
  const [newEnvKey, setNewEnvKey] = useState('');
  const [newEnvValue, setNewEnvValue] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await api.createAutomationTestCase(formData);
      onSuccess();
      onClose();
    } catch (err) {
      setError('创建自动化测试用例失败');
      console.error('Create automation test case error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
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

  const handleAddEnv = () => {
    if (newEnvKey && newEnvValue) {
      setFormData(prev => ({
        ...prev,
        runtime_env: {
          ...(prev.runtime_env || {}),
          [newEnvKey]: newEnvValue,
        },
      }));
      setNewEnvKey('');
      setNewEnvValue('');
    }
  };

  const handleRemoveEnv = (key: string) => {
    setFormData(prev => {
      const newEnv = { ...(prev.runtime_env || {}) };
      delete newEnv[key];
      return {
        ...prev,
        runtime_env: newEnv,
      };
    });
  };

  return (
    <div style={styles.modalOverlay}>
      <div style={styles.modalContent}>
        <div style={styles.modalHeader}>
          <h2 style={styles.modalTitle}>创建自动化测试用例</h2>
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
                ...(activeTab === 'env' ? styles.activeTab : {}),
              }}
              onClick={() => setActiveTab('env')}
            >
              运行环境
            </button>
            <button
              type="button"
              style={{
                ...styles.tab,
                ...(activeTab === 'advanced' ? styles.activeTab : {}),
              }}
              onClick={() => setActiveTab('advanced')}
            >
              高级设置
            </button>
          </div>

          <div style={styles.modalBody}>
            {activeTab === 'basic' && (
              <div style={styles.tabContent}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>
                    用例名称 <span style={styles.required}>*</span>
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    style={styles.input}
                    placeholder="输入自动化用例名称"
                    required
                  />
                </div>

                <div style={styles.formRow}>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>版本</label>
                    <input
                      type="text"
                      name="version"
                      value={formData.version}
                      onChange={handleChange}
                      style={styles.input}
                      placeholder="1.0.0"
                    />
                  </div>

                  <div style={styles.formGroup}>
                    <label style={styles.label}>状态</label>
                    <select
                      name="status"
                      value={formData.status}
                      onChange={handleChange}
                      style={styles.input}
                    >
                      <option value="ACTIVE">激活</option>
                      <option value="DEPRECATED">已弃用</option>
                    </select>
                  </div>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>自动化框架</label>
                  <input
                    type="text"
                    name="framework"
                    value={formData.framework || ''}
                    onChange={handleChange}
                    style={styles.input}
                    placeholder="Selenium/Appium/Pytest等"
                  />
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>自动化类型</label>
                  <input
                    type="text"
                    name="automation_type"
                    value={formData.automation_type || ''}
                    onChange={handleChange}
                    style={styles.input}
                    placeholder="UI自动化/API自动化等"
                  />
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>描述</label>
                  <textarea
                    name="description"
                    value={formData.description || ''}
                    onChange={handleChange}
                    style={styles.textarea}
                    placeholder="描述自动化用例的用途和目标"
                    rows={4}
                  />
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
              </div>
            )}

            {activeTab === 'env' && (
              <div style={styles.tabContent}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>脚本仓库地址</label>
                  <input
                    type="text"
                    name="repo_url"
                    value={formData.repo_url || ''}
                    onChange={handleChange}
                    style={styles.input}
                    placeholder="https://github.com/username/repo.git"
                  />
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>默认分支</label>
                  <input
                    type="text"
                    name="repo_branch"
                    value={formData.repo_branch || ''}
                    onChange={handleChange}
                    style={styles.input}
                    placeholder="main"
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
                  <label style={styles.label}>执行入口命令</label>
                  <input
                    type="text"
                    name="entry_command"
                    value={formData.entry_command || ''}
                    onChange={handleChange}
                    style={styles.input}
                    placeholder="pytest tests/test_example.py"
                  />
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>运行环境变量</label>
                  <div style={styles.envForm}>
                    <div style={styles.envInputRow}>
                      <input
                        type="text"
                        value={newEnvKey}
                        onChange={(e) => setNewEnvKey(e.target.value)}
                        style={styles.envInput}
                        placeholder="变量名"
                      />
                      <input
                        type="text"
                        value={newEnvValue}
                        onChange={(e) => setNewEnvValue(e.target.value)}
                        style={styles.envInput}
                        placeholder="变量值"
                      />
                      <button
                        type="button"
                        style={styles.addButton}
                        onClick={handleAddEnv}
                      >
                        添加
                      </button>
                    </div>
                    <div style={styles.envList}>
                      {Object.entries(formData.runtime_env || {}).map(([key, value]) => (
                        <div key={key} style={styles.envItem}>
                          <span style={styles.envKey}>{key}:</span>
                          <span style={styles.envValue}>{String(value)}</span>
                          <button
                            type="button"
                            style={styles.envRemove}
                            onClick={() => handleRemoveEnv(key)}
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'advanced' && (
              <div style={styles.tabContent}>
                <div style={styles.formRow}>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>维护人</label>
                    <input
                      type="text"
                      name="maintainer_id"
                      value={formData.maintainer_id || ''}
                      onChange={handleChange}
                      style={styles.input}
                      placeholder="用户ID"
                    />
                  </div>

                  <div style={styles.formGroup}>
                    <label style={styles.label}>评审人</label>
                    <input
                      type="text"
                      name="reviewer_id"
                      value={formData.reviewer_id || ''}
                      onChange={handleChange}
                      style={styles.input}
                      placeholder="用户ID"
                    />
                  </div>
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
    maxWidth: '800px',
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
    marginBottom: '20px',
  } as const,
  form: {
    display: 'flex',
    flexDirection: 'column' as const,
  } as const,
  tabs: {
    display: 'flex',
    borderBottom: '1px solid var(--border-default)',
    marginBottom: '20px',
  } as const,
  tab: {
    padding: '14px 24px',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    transition: 'all var(--transition-fast)',
  } as const,
  activeTab: {
    backgroundColor: 'var(--accent-purple)',
    color: 'var(--bg-primary)',
    borderBottom: '3px solid var(--accent-purple)',
  } as const,
  modalBody: {
    padding: '24px',
  } as const,
  tabContent: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '18px',
  } as const,
  formGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  } as const,
  formRow: {
    display: 'flex',
    gap: '20px',
  } as const,
  label: {
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    letterSpacing: '0.3px',
  } as const,
  required: {
    color: 'var(--accent-red)',
  } as const,
  input: {
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
    padding: '12px 14px',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    resize: 'vertical' as const,
    outline: 'none',
    fontFamily: 'inherit',
  } as const,
  tagInputContainer: {
    display: 'flex',
    gap: '10px',
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
  } as const,
  tagList: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '8px',
    marginTop: '10px',
  } as const,
  tag: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 12px',
    backgroundColor: 'rgba(163, 113, 247, 0.15)',
    borderRadius: '16px',
    fontSize: '13px',
    color: 'var(--accent-purple)',
    border: '1px solid rgba(163, 113, 247, 0.3)',
  } as const,
  tagRemove: {
    background: 'none',
    border: 'none',
    color: 'var(--accent-purple)',
    cursor: 'pointer',
    fontSize: '16px',
    fontWeight: 'bold',
    padding: 0,
    lineHeight: 1,
  } as const,
  envForm: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '12px',
  } as const,
  envInputRow: {
    display: 'flex',
    gap: '10px',
  } as const,
  envInput: {
    flex: 1,
    padding: '10px 14px',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
  } as const,
  envList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '10px',
    marginTop: '15px',
  } as const,
  envItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px',
    backgroundColor: 'var(--bg-tertiary)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-muted)',
  } as const,
  envKey: {
    fontWeight: 600,
    color: 'var(--accent-cyan)',
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '13px',
  } as const,
  envValue: {
    color: 'var(--text-secondary)',
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '13px',
    flex: 1,
  } as const,
  envRemove: {
    background: 'none',
    border: 'none',
    color: 'var(--accent-red)',
    cursor: 'pointer',
    fontSize: '18px',
    padding: 0,
    lineHeight: 1,
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
  } as const,
  submitButton: {
    padding: '12px 28px',
    backgroundColor: 'var(--accent-purple)',
    color: 'var(--bg-primary)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  } as const,
  buttonDisabled: {
    opacity: 0.6,
    cursor: 'not-allowed',
  } as const,
};

export default CreateAutomationTestCaseForm;
