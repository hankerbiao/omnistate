import React from 'react';
import type { TestCaseStep } from '../types';
import type { StepAnalysisIssue, StepAnalysisResult } from '../types/ai';
import { api } from '../services/api';

interface TestCaseStepEditorV2Props {
  steps: TestCaseStep[];
  onChange: (steps: TestCaseStep[]) => void;
  emptyHint?: string;
  testCaseTitle?: string;
  category?: string;
  preCondition?: string;
  postCondition?: string;
}

function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

const stepActionBtnStyle: React.CSSProperties = {
  padding: '4px 10px',
  border: '1px solid var(--border-default)',
  borderRadius: 'var(--radius-sm)',
  backgroundColor: 'var(--surface-secondary)',
  color: 'var(--text-secondary)',
  cursor: 'pointer',
  fontSize: 13,
};

/** 获取步骤的严重级别（用于左侧图标） */
function getStepSeverity(issues: StepAnalysisIssue[], index: number): StepAnalysisIssue['severity'] | null {
  const stepIssues = issues.filter(i => i.stepIndex === index);
  if (stepIssues.some(i => i.severity === 'error')) return 'error';
  if (stepIssues.some(i => i.severity === 'warning')) return 'warning';
  if (stepIssues.some(i => i.severity === 'suggestion')) return 'suggestion';
  return null;
}

const TestCaseStepEditorV2: React.FC<TestCaseStepEditorV2Props> = ({
  steps,
  onChange,
  emptyHint = '从左侧添加步骤开始',
  testCaseTitle,
  category,
  preCondition,
  postCondition,
}) => {
  const [activeIndex, setActiveIndex] = React.useState(0);
  const [analysisResult, setAnalysisResult] = React.useState<StepAnalysisResult | null>(null);
  const [analyzing, setAnalyzing] = React.useState(false);
  const [analysisError, setAnalysisError] = React.useState<string | null>(null);
  const [analysisExpanded, setAnalysisExpanded] = React.useState(false);
  const [ignoredIssues, setIgnoredIssues] = React.useState<Set<string>>(new Set());

  const activeStep = steps[activeIndex] ?? null;
  const prevStep = activeIndex > 0 ? steps[activeIndex - 1] : null;

  const addStep = () => {
    const newStep: TestCaseStep = { step_id: generateUUID(), name: '', action: '', expected: '' };
    const next = [...steps, newStep];
    onChange(next);
    setActiveIndex(next.length - 1);
  };

  const removeStep = (index: number) => {
    const next = steps.filter((_, i) => i !== index);
    onChange(next);
    if (activeIndex >= index && activeIndex > 0) {
      setActiveIndex(activeIndex - 1);
    } else if (activeIndex >= next.length) {
      setActiveIndex(Math.max(0, next.length - 1));
    }
  };

  const moveStep = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= steps.length) return;
    const next = [...steps];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
    if (activeIndex === index) setActiveIndex(target);
    else if (activeIndex === target) setActiveIndex(index);
  };

  const updateStep = (index: number, patch: Partial<TestCaseStep>) => {
    onChange(steps.map((step, i) => (i === index ? { ...step, ...patch } : step)));
  };

  /** 检查当前步骤（只分析当前步骤） */
  const handleCompletenessCheck = () => {
    const issues: StepAnalysisIssue[] = [];
    const step = activeStep;
    if (!step) return;
    const i = activeIndex;
    if (!step.name.trim()) issues.push({ stepIndex: i, severity: 'error', category: 'completeness', message: '步骤标题为空', field: 'name' });
    if (!step.action.trim()) issues.push({ stepIndex: i, severity: 'error', category: 'completeness', message: '动作为空', field: 'action' });
    if (!step.expected.trim()) issues.push({ stepIndex: i, severity: 'warning', category: 'completeness', message: '期望结果为空', field: 'expected' });
    if (step.action.trim().length < 10) issues.push({ stepIndex: i, severity: 'suggestion', category: 'clarity', message: '动作描述过短，建议增加细节', field: 'action' });
    if (step.expected.trim().length < 10) issues.push({ stepIndex: i, severity: 'suggestion', category: 'clarity', message: '期望结果过短，建议增加可观测标准', field: 'expected' });
    const score = Math.max(0, 100 - issues.filter(i => i.severity === 'error').length * 20 - issues.filter(i => i.severity === 'warning').length * 10 - issues.filter(i => i.severity === 'suggestion').length * 5);
    setAnalysisResult({ score, totalSteps: 1, issues, summary: issues.length === 0 ? '当前步骤检查通过' : `当前步骤有 ${issues.length} 个问题` });
    setAnalysisExpanded(true);
  };

  const handleAnalyze = async () => {
    if (steps.length === 0) return;
    setAnalyzing(true);
    setAnalysisError(null);
    try {
      const res = await api.analyzeTestSteps({
        steps,
        title: testCaseTitle,
        category,
        pre_condition: preCondition,
        post_condition: postCondition,
      });
      setAnalysisResult(res.data);
      setAnalysisExpanded(true);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'AI 分析失败，请稍后重试';
      setAnalysisError(msg);
    } finally {
      setAnalyzing(false);
    }
  };

  /** 应用单个建议 */
  const applyIssue = (issue: StepAnalysisIssue) => {
    if (issue.stepIndex >= 0 && issue.field && issue.proposedValue !== undefined) {
      updateStep(issue.stepIndex, { [issue.field]: issue.proposedValue });
    }
  };

  /** 应用所有可修正的建议 */
  const applyAllFixable = () => {
    if (!analysisResult) return;
    const fixable = analysisResult.issues.filter(
      i => i.stepIndex >= 0 && i.field && i.proposedValue !== undefined && !ignoredIssues.has(issueKey(i))
    );
    // 按 stepIndex 分组，避免重复更新
    const patches = new Map<number, Partial<TestCaseStep>>();
    fixable.forEach(issue => {
      const existing = patches.get(issue.stepIndex) ?? {};
      patches.set(issue.stepIndex, { ...existing, [issue.field!]: issue.proposedValue });
    });
    const next = steps.map((step, i) => {
      const patch = patches.get(i);
      return patch ? { ...step, ...patch } : step;
    });
    onChange(next);
  };

  /** 忽略单条 issue */
  const ignoreIssue = (issue: StepAnalysisIssue) => {
    setIgnoredIssues(prev => new Set([...prev, issueKey(issue)]));
  };

  const issueKey = (issue: StepAnalysisIssue) => `${issue.stepIndex}-${issue.category}-${issue.message}`;

  const visibleIssues = analysisResult?.issues.filter(i => !ignoredIssues.has(issueKey(i))) ?? [];
  const hasFixable = visibleIssues.some(i => i.stepIndex >= 0 && i.field && i.proposedValue !== undefined);

  return (
    <div style={{ display: 'flex', gap: 16, minHeight: 320 }}>
      {/* 左侧步骤导航 */}
      <div style={{ width: 200, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          步骤列表
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto', maxHeight: 340 }}>
          {steps.length === 0 ? (
            <div style={{ fontSize: 12, color: 'var(--text-tertiary)', padding: '8px 0' }}>
              暂无步骤
            </div>
          ) : (
            steps.map((step, i) => {
              const severity = analysisResult ? getStepSeverity(analysisResult.issues, i) : null;
              const icon = severity === 'error' ? '✗' : severity === 'warning' ? '⚠' : severity === 'suggestion' ? '💡' : '';
              const iconColor = severity === 'error' ? 'var(--status-error)' : severity === 'warning' ? 'var(--status-warning)' : severity === 'suggestion' ? 'var(--status-info)' : 'transparent';
              return (
                <div
                  key={step.step_id}
                  onClick={() => setActiveIndex(i)}
                  style={{
                    padding: '8px 10px',
                    borderRadius: 6,
                    cursor: 'pointer',
                    border: '1px solid',
                    borderColor: i === activeIndex ? 'var(--accent-primary)' : 'var(--border-subtle)',
                    backgroundColor: i === activeIndex ? 'var(--accent-primary)' : 'var(--surface-primary)',
                    color: i === activeIndex ? 'white' : 'var(--text-primary)',
                    fontSize: 13,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    transition: 'all 0.15s ease',
                  }}
                >
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 20,
                    height: 20,
                    borderRadius: '50%',
                    backgroundColor: i === activeIndex ? 'rgba(255,255,255,0.25)' : 'var(--surface-tertiary)',
                    fontSize: 11,
                    fontWeight: 600,
                    flexShrink: 0,
                  }}>
                    {i + 1}
                  </span>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                    {step.name.trim() || '未命名步骤'}
                  </span>
                  {icon && (
                    <span style={{ fontSize: 12, color: i === activeIndex ? 'white' : iconColor, flexShrink: 0 }}>
                      {icon}
                    </span>
                  )}
                </div>
              );
            })
          )}
        </div>
        <button
          type="button"
          className="btn btn--secondary btn--sm"
          style={{ marginTop: 'auto', alignSelf: 'stretch' }}
          onClick={addStep}
        >
          + 添加步骤
        </button>
      </div>

      {/* 右侧编辑区 */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 14 }}>
        {steps.length > 0 && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <button
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={handleCompletenessCheck}
              disabled={analyzing}
              title="检查当前步骤的字段完整性"
            >
              🔍 检查当前步骤
            </button>
            <button
              type="button"
              className="btn btn--primary btn--sm"
              onClick={handleAnalyze}
              disabled={analyzing}
              title="分析全部步骤的完整性和一致性"
            >
              {analyzing ? '分析中...' : '🤖 分析全部步骤'}
            </button>
          </div>
        )}
        {steps.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, padding: '40px 0', color: 'var(--text-tertiary)' }}>
            <div style={{ fontSize: 32 }}>📝</div>
            <div style={{ fontSize: 14 }}>{emptyHint}</div>
          </div>
        ) : (
          <>
            {/* 上一步参考 */}
            {prevStep && (
              <div style={{ backgroundColor: 'var(--surface-secondary)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  上一步参考（步骤 {activeIndex}）
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-primary)', marginBottom: 4, fontWeight: 500 }}>
                  {prevStep.name}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {prevStep.action}
                </div>
              </div>
            )}

            {/* 当前步骤编辑 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, justifyContent: 'space-between' }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                编辑步骤 {activeIndex + 1}
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button
                  type="button"
                  style={{ ...stepActionBtnStyle, opacity: activeIndex === 0 ? 0.4 : 1 }}
                  onClick={() => moveStep(activeIndex, -1)}
                  disabled={activeIndex === 0}
                >
                  ↑
                </button>
                <button
                  type="button"
                  style={{ ...stepActionBtnStyle, opacity: activeIndex === steps.length - 1 ? 0.4 : 1 }}
                  onClick={() => moveStep(activeIndex, 1)}
                  disabled={activeIndex === steps.length - 1}
                >
                  ↓
                </button>
                <button
                  type="button"
                  style={{ ...stepActionBtnStyle, color: 'var(--status-error)' }}
                  onClick={() => removeStep(activeIndex)}
                >
                  删除
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={labelStyle}>步骤标题</label>
                <input
                  type="text"
                  className="form-input"
                  value={activeStep?.name || ''}
                  onChange={e => updateStep(activeIndex, { name: e.target.value })}
                  placeholder="如：安装内存、读取 SPD"
                  autoFocus
                />
              </div>
              <div>
                <label style={labelStyle}>动作</label>
                <textarea
                  className="form-input"
                  value={activeStep?.action || ''}
                  onChange={e => updateStep(activeIndex, { action: e.target.value })}
                  placeholder="描述具体操作步骤"
                  rows={3}
                  style={textareaStyle}
                />
              </div>
              <div>
                <label style={labelStyle}>期望</label>
                <textarea
                  className="form-input"
                  value={activeStep?.expected || ''}
                  onChange={e => updateStep(activeIndex, { expected: e.target.value })}
                  placeholder="描述可观测的通过标准"
                  rows={3}
                  style={{ ...textareaStyle, ...expectedTextareaStyle }}
                />
              </div>
            </div>

            {/* AI 分析面板 */}
            <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)', overflow: 'hidden', marginTop: 4 }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  backgroundColor: 'var(--surface-secondary)',
                  cursor: 'pointer',
                }}
                onClick={() => setAnalysisExpanded(v => !v)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 16 }}>🤖</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                    AI 分析
                  </span>
                  {analysisResult && (
                    <span style={{
                      fontSize: 12,
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-full)',
                      backgroundColor: analysisResult.score >= 80 ? 'var(--status-success-bg)' : analysisResult.score >= 60 ? 'var(--status-warning-bg)' : 'var(--status-error-bg)',
                      color: analysisResult.score >= 80 ? 'var(--status-success)' : analysisResult.score >= 60 ? 'var(--status-warning)' : 'var(--status-error)',
                    }}>
                      {analysisResult.score}分
                    </span>
                  )}
                  {visibleIssues.length > 0 && (
                    <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                      {visibleIssues.length} 个问题
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 12, color: 'var(--text-tertiary)', transition: 'transform 0.2s', transform: analysisExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>
                    ▾
                  </span>
                </div>
              </div>

              {analysisExpanded && (
                <div style={{ padding: 'var(--space-4)', backgroundColor: 'var(--surface-primary)', maxHeight: 280, overflowY: 'auto' }}>
                  {analyzing ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '20px 0', color: 'var(--text-secondary)', fontSize: 13 }}>
                      <div className="loading-spinner" style={{ width: 16, height: 16 }} />
                      AI 正在分析中...
                    </div>
                  ) : analysisError ? (
                    <div style={{ padding: '12px', backgroundColor: 'var(--status-error-bg)', borderRadius: 'var(--radius-md)', color: 'var(--status-error)', fontSize: 13 }}>
                      ⚠ {analysisError}
                    </div>
                  ) : !analysisResult ? (
                    <div style={{ textAlign: 'center', padding: '20px 0', color: 'var(--text-tertiary)', fontSize: 13 }}>
                      点击顶部「检查当前步骤」或「分析全部步骤」按钮开始检查
                    </div>
                  ) : visibleIssues.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '20px 0', color: 'var(--status-success)', fontSize: 13 }}>
                      ✓ 所有步骤检查通过，未发现明显问题
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {/* 一句话总结 */}
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '8px 10px', backgroundColor: 'var(--surface-secondary)', borderRadius: 'var(--radius-md)', borderLeft: '3px solid var(--accent-primary)' }}>
                        {analysisResult.summary}
                      </div>

                      {/* 一键修正 */}
                      {hasFixable && (
                        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                          <button type="button" className="btn btn--primary btn--sm" onClick={applyAllFixable}>
                            一键修正全部
                          </button>
                        </div>
                      )}

                      {/* 问题列表 */}
                      {visibleIssues.map((issue, idx) => (
                        <div key={idx} style={{
                          padding: '10px 12px',
                          borderRadius: 'var(--radius-md)',
                          border: '1px solid',
                          borderColor: issue.severity === 'error' ? 'var(--status-error)' : issue.severity === 'warning' ? 'var(--status-warning)' : 'var(--border-subtle)',
                          backgroundColor: issue.severity === 'error' ? 'var(--status-error-bg)' : issue.severity === 'warning' ? 'var(--status-warning-bg)' : 'var(--surface-secondary)',
                        }}>
                          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 6 }}>
                            <span style={{
                              fontSize: 10,
                              fontWeight: 700,
                              padding: '2px 6px',
                              borderRadius: 'var(--radius-sm)',
                              textTransform: 'uppercase',
                              backgroundColor: issue.severity === 'error' ? 'var(--status-error)' : issue.severity === 'warning' ? 'var(--status-warning)' : 'var(--status-info)',
                              color: 'white',
                              flexShrink: 0,
                            }}>
                              {issue.severity === 'error' ? '错误' : issue.severity === 'warning' ? '警告' : '建议'}
                            </span>
                            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
                              {issue.stepIndex >= 0 ? `步骤 ${issue.stepIndex + 1}` : '全局'}
                              {issue.field ? ` · ${issue.field === 'name' ? '标题' : issue.field === 'action' ? '动作' : '期望'}` : ''}
                            </span>
                          </div>
                          <div style={{ fontSize: 13, color: 'var(--text-primary)', marginBottom: 4, lineHeight: 1.5 }}>
                            {issue.message}
                          </div>
                          {issue.suggestion && (
                            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8, padding: '6px 10px', backgroundColor: 'rgba(255,255,255,0.5)', borderRadius: 'var(--radius-sm)', lineHeight: 1.5 }}>
                              💡 建议：{issue.suggestion}
                            </div>
                          )}
                          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                            {issue.proposedValue !== undefined && issue.stepIndex >= 0 && issue.field && (
                              <button
                                type="button"
                                className="btn btn--primary btn--sm"
                                style={{ padding: '4px 12px' }}
                                onClick={() => applyIssue(issue)}
                              >
                                采纳建议
                              </button>
                            )}
                            <button
                              type="button"
                              className="btn btn--ghost btn--sm"
                              style={{ padding: '4px 12px', color: 'var(--text-tertiary)' }}
                              onClick={() => ignoreIssue(issue)}
                            >
                              忽略
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: 12,
  fontWeight: 500,
  color: 'var(--text-secondary)',
  marginBottom: 6,
};

const textareaStyle: React.CSSProperties = {
  resize: 'vertical' as const,
  minHeight: 72,
  fontFamily: 'inherit',
};

const expectedTextareaStyle: React.CSSProperties = {
  backgroundColor: 'var(--status-success-bg)',
  borderLeft: '3px solid var(--status-success)',
};

export default TestCaseStepEditorV2;
