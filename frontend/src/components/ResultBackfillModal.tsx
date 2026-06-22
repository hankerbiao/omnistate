import React, { useReducer, useCallback } from 'react';
import type { PlanTask, PlanTaskResult } from './myTasksTypes';
import { modalLabel } from './myTasksTypes';
import { Dialog, DialogContent } from './ui/dialog';

// ═══════════════════════════════════════════════════════════════════════
//  Reducer — 用 useReducer 替代 10 个独立 useState
// ═══════════════════════════════════════════════════════════════════════

interface ResultFormState {
  passed: boolean;
  notes: string;
  severity: string;
  actual: string;
  expected: string;
  env: string;
  testData: string;
  bugId: string;
  duration: string;
  attachments: string[];
}

type ResultFormAction =
  | { type: 'SET_PASSED'; payload: boolean }
  | { type: 'SET_NOTES'; payload: string }
  | { type: 'SET_SEVERITY'; payload: string }
  | { type: 'SET_ACTUAL'; payload: string }
  | { type: 'SET_EXPECTED'; payload: string }
  | { type: 'SET_ENV'; payload: string }
  | { type: 'SET_TEST_DATA'; payload: string }
  | { type: 'SET_BUG_ID'; payload: string }
  | { type: 'SET_DURATION'; payload: string }
  | { type: 'ADD_ATTACHMENT'; payload: string }
  | { type: 'REMOVE_ATTACHMENT'; payload: number }
  | { type: 'INIT_FROM_TASK'; payload: PlanTask }
  | { type: 'RESET' };

const initialFormState: ResultFormState = {
  passed: true,
  notes: '',
  severity: 'normal',
  actual: '',
  expected: '',
  env: '',
  testData: '',
  bugId: '',
  duration: '',
  attachments: [],
};

function resultFormReducer(state: ResultFormState, action: ResultFormAction): ResultFormState {
  switch (action.type) {
    case 'SET_PASSED':
      return { ...state, passed: action.payload };
    case 'SET_NOTES':
      return { ...state, notes: action.payload };
    case 'SET_SEVERITY':
      return { ...state, severity: action.payload };
    case 'SET_ACTUAL':
      return { ...state, actual: action.payload };
    case 'SET_EXPECTED':
      return { ...state, expected: action.payload };
    case 'SET_ENV':
      return { ...state, env: action.payload };
    case 'SET_TEST_DATA':
      return { ...state, testData: action.payload };
    case 'SET_BUG_ID':
      return { ...state, bugId: action.payload };
    case 'SET_DURATION':
      return { ...state, duration: action.payload };
    case 'ADD_ATTACHMENT':
      return { ...state, attachments: [...state.attachments, action.payload] };
    case 'REMOVE_ATTACHMENT':
      return {
        ...state,
        attachments: state.attachments.filter((_, i) => i !== action.payload),
      };
    case 'INIT_FROM_TASK':
      return {
        passed: action.payload.result?.passed ?? true,
        notes: action.payload.result?.notes ?? '',
        severity: action.payload.result?.severity ?? 'normal',
        actual: action.payload.result?.actual ?? '',
        expected: action.payload.result?.expected ?? '',
        env: action.payload.result?.env ?? '',
        testData: action.payload.result?.testData ?? '',
        bugId: action.payload.result?.bugId ?? '',
        duration: action.payload.result?.actualDuration ?? '',
        attachments: action.payload.result?.attachments ?? [],
      };
    case 'RESET':
      return initialFormState;
    default:
      return state;
  }
}

// ═══════════════════════════════════════════════════════════════════════
//  Component
// ═══════════════════════════════════════════════════════════════════════

interface ResultBackfillModalProps {
  /** 当前操作的任务，为 null 时不渲染弹窗 */
  task: PlanTask | null;
  /** 关闭弹窗 */
  onClose: () => void;
  /** 提交结果回调 */
  onSubmit: (taskId: string, result: PlanTaskResult) => void;
}

/**
 * ResultBackfillModal — 测试结果回填模态框
 * 使用 useReducer 管理 10+ 表单字段状态，替代多个独立 useState 调用。
 */
const ResultBackfillModal: React.FC<ResultBackfillModalProps> = ({ task, onClose, onSubmit }) => {
  const [form, dispatch] = useReducer(resultFormReducer, initialFormState);

  // 当 task 变化时初始化表单
  React.useEffect(() => {
    if (task) {
      dispatch({ type: 'INIT_FROM_TASK', payload: task });
    }
  }, [task]);

  const handleSubmit = useCallback(() => {
    if (!task) return;
    onSubmit(task.id, {
      passed: form.passed,
      notes: form.notes,
      severity: form.severity,
      actual: form.actual,
      expected: form.expected,
      env: form.env,
      testData: form.testData,
      bugId: form.bugId,
      actualDuration: form.duration,
      attachments: form.attachments,
      executedAt: new Date().toLocaleString('zh-CN'),
    });
    onClose();
  }, [task, form, onSubmit, onClose]);

  const handleAddAttachment = useCallback(() => {
    const name = prompt('文件名（演示）:');
    if (name) {
      dispatch({ type: 'ADD_ATTACHMENT', payload: name });
    }
  }, []);

  if (!task) return null;

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-[560px]" style={{ padding: 0, maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0,
        }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>📝 回填测试结果</h3>
            <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-tertiary)' }}>
              {task.caseId} · {task.caseTitle}
            </p>
          </div>
        </div>

        {/* Scrollable body */}
        <div style={{
          padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16,
        }}>
          {/* Plan & component info */}
          <div style={{
            display: 'flex', gap: 12, padding: '10px 14px', background: 'var(--bg-secondary)',
            borderRadius: 8, fontSize: 12, color: 'var(--text-secondary)', flexShrink: 0,
          }}>
            <span>📋 组件: {task.component}</span>
            <span>🎯 计划: {task.planTitle}</span>
          </div>

          {/* 1. Test conclusion */}
          <div>
            <label style={modalLabel}>测试结论</label>
            <div style={{ display: 'flex', gap: 8 }}>
              {[
                { key: true, label: '✅ 通过', color: '#3fb950' },
                { key: false, label: '❌ 失败', color: '#f85149' },
              ].map(opt => (
                <button
                  key={String(opt.key)}
                  onClick={() => dispatch({ type: 'SET_PASSED', payload: opt.key })}
                  style={{
                    flex: 1, padding: '10px 16px', fontSize: 13, fontWeight: 600,
                    border: form.passed === opt.key ? `2px solid ${opt.color}` : '1px solid var(--border-subtle)',
                    borderRadius: 8, cursor: 'pointer',
                    background: form.passed === opt.key ? `${opt.color}10` : 'var(--bg-primary)',
                    color: form.passed === opt.key ? opt.color : 'var(--text-secondary)',
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* 2. Severity (when failed) */}
          {!form.passed && (
            <div>
              <label style={modalLabel}>严重程度</label>
              <select
                className="form-input form-select"
                value={form.severity}
                onChange={e => dispatch({ type: 'SET_SEVERITY', payload: e.target.value })}
                style={{ width: 200, fontSize: 13 }}
              >
                <option value="blocker">Blocker — 阻塞</option>
                <option value="critical">Critical — 严重</option>
                <option value="major">Major — 主要</option>
                <option value="normal">Normal — 一般</option>
                <option value="minor">Minor — 轻微</option>
              </select>
            </div>
          )}

          {/* 3. Expected / Actual */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={modalLabel}>预期结果</label>
              <textarea
                className="form-input" rows={2} value={form.expected || ''} onChange={() => {}}
                placeholder="从用例定义中获取…"
                style={{
                  width: '100%', fontSize: 13, resize: 'vertical',
                  color: 'var(--text-tertiary)', background: 'var(--surface-secondary)',
                }}
                disabled
              />
            </div>
            <div>
              <label style={modalLabel}>实际结果 *</label>
              <textarea
                className="form-input" rows={2} value={form.actual}
                onChange={e => dispatch({ type: 'SET_ACTUAL', payload: e.target.value })}
                placeholder={form.passed ? '描述实际观察到的结果…' : '描述失败现象、实际输出…'}
                style={{ width: '100%', fontSize: 13, resize: 'vertical' }}
              />
            </div>
          </div>

          {/* 4. Notes */}
          <div>
            <label style={modalLabel}>执行备注</label>
            <textarea
              className="form-input" value={form.notes}
              onChange={e => dispatch({ type: 'SET_NOTES', payload: e.target.value })}
              placeholder={form.passed ? '记录测试环境、测试数据、观察到的异常…' : '描述失败现象、复现步骤、环境差异、是否已提缺陷…'}
              rows={3} style={{ width: '100%', fontSize: 13, resize: 'vertical' }}
            />
          </div>

          {/* 5. Environment + Test data */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={modalLabel}>环境信息</label>
              <input
                className="form-input" value={form.env}
                onChange={e => dispatch({ type: 'SET_ENV', payload: e.target.value })}
                placeholder="例如: 固件 v2.3.1 / Ubuntu 22.04"
                style={{ width: '100%', fontSize: 13 }}
              />
            </div>
            <div>
              <label style={modalLabel}>测试数据</label>
              <input
                className="form-input" value={form.testData}
                onChange={e => dispatch({ type: 'SET_TEST_DATA', payload: e.target.value })}
                placeholder="例如: 1000线程 × 4KB随机读写"
                style={{ width: '100%', fontSize: 13 }}
              />
            </div>
          </div>

          {/* 6. Bug ID + Duration */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={modalLabel}>关联缺陷</label>
              <input
                className="form-input" value={form.bugId}
                onChange={e => dispatch({ type: 'SET_BUG_ID', payload: e.target.value })}
                placeholder="BZ-XXXXX" style={{ width: '100%', fontSize: 13 }}
              />
            </div>
            <div>
              <label style={modalLabel}>实际耗时（分钟）</label>
              <input
                type="number" className="form-input" value={form.duration}
                onChange={e => dispatch({ type: 'SET_DURATION', payload: e.target.value })}
                placeholder="预估 60" style={{ width: '100%', fontSize: 13 }} min={0}
              />
            </div>
          </div>

          {/* 7. Attachments */}
          <div>
            <label style={modalLabel}>附件（日志、截图）</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {form.attachments.map((f, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px',
                  background: 'var(--bg-secondary)', borderRadius: 6, fontSize: 12,
                }}>
                  <span>📎</span>
                  <span style={{ color: 'var(--text-primary)' }}>{f}</span>
                  <button
                    onClick={() => dispatch({ type: 'REMOVE_ATTACHMENT', payload: i })}
                    style={{
                      marginLeft: 'auto', border: 'none', background: 'none',
                      cursor: 'pointer', color: 'var(--text-tertiary)', fontSize: 14,
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                onClick={handleAddAttachment}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px',
                  border: '1px dashed var(--border-default)', borderRadius: 8,
                  background: 'transparent', cursor: 'pointer', fontSize: 12, color: 'var(--text-tertiary)',
                }}
              >
                + 添加上传文件（演示）
              </button>
            </div>
          </div>

          {/* 8. Quick defect (when failed) */}
          {!form.passed && (
            <div style={{
              padding: '12px 14px', background: 'rgba(248,81,73,0.06)', borderRadius: 8,
              border: '1px solid rgba(248,81,73,0.15)', fontSize: 13, color: 'var(--text-secondary)',
              lineHeight: 1.6,
            }}>
              <div style={{ fontWeight: 600, marginBottom: 6, color: '#f85149' }}>🐛 缺陷预填模板</div>
              <div><strong>标题</strong>：【{task.caseTitle}】{form.notes.slice(0, 40)}</div>
              <div><strong>用例</strong>：{task.caseId} ｜ <strong>组件</strong>：{task.component}</div>
              <div><strong>严重程度</strong>：{form.severity} ｜ <strong>环境</strong>：{form.env || '-'}</div>
              <div><strong>实际结果</strong>：{form.actual.slice(0, 100)}{form.actual.length > 100 ? '…' : ''}</div>
              <button style={{
                marginTop: 8, padding: '4px 12px', border: '1px solid #f85149', borderRadius: 6,
                background: 'transparent', color: '#f85149', fontSize: 12, cursor: 'pointer',
              }}>
                📤 提缺陷（演示）
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          display: 'flex', justifyContent: 'flex-end', gap: 10, padding: '14px 20px',
          borderTop: '1px solid var(--border-subtle)', flexShrink: 0,
        }}>
          <button className="btn btn--secondary" onClick={onClose}>取消</button>
          <button className="btn btn--primary" onClick={handleSubmit}>✓ 提交结果</button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ResultBackfillModal;
