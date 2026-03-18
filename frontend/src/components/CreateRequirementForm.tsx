import React, { useState } from 'react';
import { api } from '../services/api';
import type { CreateRequirementRequest, RequirementResponse } from '../types';

interface CreateRequirementFormProps {
  onClose: () => void;
  onSuccess: (requirement: RequirementResponse) => void;
}

const CreateRequirementForm: React.FC<CreateRequirementFormProps> = ({ onClose, onSuccess }) => {
  const [formData, setFormData] = useState<CreateRequirementRequest>({
    title: '',
    description: '',
    priority: 'P1',
    target_components: [],
    key_parameters: [],
    attachments: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await api.createRequirement(formData);
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

  return (
    <div style={styles.modalOverlay}>
      <div style={styles.modalContent}>
        <div style={styles.modalHeader}>
          <h2 style={styles.modalTitle}>创建测试需求</h2>
          <button style={styles.closeButton} onClick={onClose}>×</button>
        </div>

        {error && <div style={styles.errorMessage}>{error}</div>}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.formGroup}>
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

          <div style={styles.formGroup}>
            <label style={styles.label}>需求描述</label>
            <textarea
              name="description"
              value={formData.description || ''}
              onChange={handleChange}
              style={styles.textarea}
              placeholder="可选，用于补充测试背景"
              rows={5}
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
    maxWidth: '560px',
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
  form: {
    padding: '24px',
  } as const,
  formGroup: {
    marginBottom: '18px',
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
    padding: '12px 14px',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    fontSize: '14px',
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
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
