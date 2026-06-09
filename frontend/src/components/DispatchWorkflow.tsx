import React, { useState, useMemo, useCallback, useEffect } from 'react';
import type { PlanTask } from './myTasksTypes';
import { STATUS_COLORS } from './myTasksTypes';
import { api } from '../services/api';
import type { CollectionListItem } from '../types';

/* ── Mock DUT machines ──────────────────────────────────────────── */

interface DutMachine {
  id: string;
  hostname: string;
  ip: string;
  region: string;
  status: 'online' | 'offline' | 'busy';
  os: string;
  cpu: string;
  memory: string;
}

const MOCK_DUT_MACHINES: DutMachine[] = [
  { id: 'dut-001', hostname: 'fw-bench-01', ip: '10.0.1.101', region: '机房A', status: 'online', os: 'Ubuntu 22.04', cpu: 'Intel Xeon 16C', memory: '64GB' },
  { id: 'dut-002', hostname: 'fw-bench-02', ip: '10.0.1.102', region: '机房A', status: 'online', os: 'Ubuntu 22.04', cpu: 'Intel Xeon 32C', memory: '128GB' },
  { id: 'dut-003', hostname: 'perf-lab-01', ip: '10.0.2.201', region: '机房B', status: 'busy', os: 'CentOS 8', cpu: 'AMD EPYC 64C', memory: '256GB' },
  { id: 'dut-004', hostname: 'perf-lab-02', ip: '10.0.2.202', region: '机房B', status: 'online', os: 'CentOS 8', cpu: 'AMD EPYC 32C', memory: '128GB' },
  { id: 'dut-005', hostname: 'stress-node-01', ip: '10.0.3.301', region: '机房C', status: 'offline', os: 'Rocky Linux 9', cpu: 'Intel Xeon 64C', memory: '512GB' },
];

/* ── Mock config fields per case ─────────────────────────────────── */

interface ConfigField {
  key: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'boolean';
  default: string | number | boolean;
}

const CASE_CONFIG_TEMPLATES: ConfigField[] = [
  { key: 'timeout_sec', label: '超时时间 (秒)', type: 'number', default: 300 },
  { key: 'retry_on_fail', label: '失败重试', type: 'boolean', default: true },
  { key: 'collect_logs', label: '收集日志', type: 'boolean', default: true },
  { key: 'env_vars', label: '环境变量', type: 'text', default: '' },
];

/* ── Component ───────────────────────────────────────────────────── */

interface DispatchWorkflowProps {
  open: boolean;
  autoTasks: PlanTask[];
  onClose: () => void;
  onFinish: (caseIds: string[]) => Promise<void> | void;
}

type WorkflowStep = 'select-cases' | 'select-dut' | 'configure' | 'confirm';

const DispatchWorkflow: React.FC<DispatchWorkflowProps> = ({ open, autoTasks, onClose, onFinish }) => {
  const [step, setStep] = useState<WorkflowStep>('select-cases');
  const [selectedCaseIds, setSelectedCaseIds] = useState<string[]>([]);
  const [selectedDut, setSelectedDut] = useState<DutMachine | null>(null);
  const [configs, setConfigs] = useState<Record<string, Record<string, string | number | boolean>>>({});
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [commonEnv, setCommonEnv] = useState('staging');
  const [commonTimeout, setCommonTimeout] = useState(30);
  const [commonRetry, setCommonRetry] = useState(0);
  const [commonNotify, setCommonNotify] = useState(true);

  // Collection search
  const [collectionQuery, setCollectionQuery] = useState('');
  const [collections, setCollections] = useState<CollectionListItem[]>([]);
  const [collectionSearching, setCollectionSearching] = useState(false);

  // Reset when opened
  React.useEffect(() => {
    if (open) {
      setStep('select-cases');
      setSelectedCaseIds(autoTasks.map(t => t.caseId));
      setSelectedDut(null);
      setConfigs({});
      setSubmitting(false);
      setSuccess(false);
      setCommonEnv('staging');
      setCommonTimeout(30);
      setCommonRetry(0);
      setCommonNotify(true);
      setCollectionQuery('');
      setCollections([]);
    }
  }, [open, autoTasks]);

  // Debounced collection search
  useEffect(() => {
    if (!collectionQuery.trim()) {
      setCollections([]);
      return;
    }
    const timer = setTimeout(async () => {
      setCollectionSearching(true);
      try {
        const res = await api.searchCollections(collectionQuery.trim(), 5);
        setCollections(res.data || []);
      } catch { setCollections([]); }
      finally { setCollectionSearching(false); }
    }, 300);
    return () => clearTimeout(timer);
  }, [collectionQuery]);

  const handleAddFromCollection = useCallback((c: CollectionListItem) => {
    // We'll just add the case_ids from the collection (matching against our autoTasks)
    // For simplicity, this adds all case_ids listed in the collection
    setSelectedCaseIds(prev => {
      const newSet = new Set(prev);
      // In a real scenario, we'd match collection case_ids against available tasks
      // For now, add all from collection that match available auto task caseIds
      const matching = autoTasks.map(t => t.caseId);
      matching.forEach(id => newSet.add(id));
      return Array.from(newSet);
    });
    setCollectionQuery('');
    setCollections([]);
  }, [autoTasks]);

  const onlineDuts = useMemo(() => MOCK_DUT_MACHINES.filter(d => d.status === 'online'), []);

  // Filtered tasks based on selected case IDs
  const selectedTasks = useMemo(
    () => autoTasks.filter(t => selectedCaseIds.includes(t.caseId)),
    [autoTasks, selectedCaseIds],
  );

  const stepLabels: Record<WorkflowStep, string> = {
    'select-cases': '选择测试用例',
    'select-dut': '选择 DUT 机器',
    'configure': '配置测试参数',
    'confirm': '确认下发',
  };

  const stepProgress: WorkflowStep[] = ['select-cases', 'select-dut', 'configure', 'confirm'];

  const getConfigForCase = (task: PlanTask) => configs[task.caseId] || {};

  const updateConfig = (caseId: string, key: string, value: string | number | boolean) => {
    setConfigs(prev => ({
      ...prev,
      [caseId]: { ...(prev[caseId] || {}), [key]: value },
    }));
  };

  const toggleCase = (caseId: string) => {
    setSelectedCaseIds(prev =>
      prev.includes(caseId) ? prev.filter(c => c !== caseId) : [...prev, caseId],
    );
  };

  const toggleAllCases = () => {
    const allIds = autoTasks.map(t => t.caseId);
    setSelectedCaseIds(prev => (prev.length === allIds.length ? [] : allIds));
  };

  const handleNextFromCases = () => {
    if (selectedCaseIds.length === 0) return;
    setStep('select-dut');
  };

  const handleNextFromDut = () => {
    if (!selectedDut) return;
    // Init default configs for selected cases
    for (const task of selectedTasks) {
      const cfg = getConfigForCase(task);
      for (const field of CASE_CONFIG_TEMPLATES) {
        if (!(field.key in cfg)) {
          updateConfig(task.caseId, field.key, field.default);
        }
      }
    }
    setStep('configure');
  };

  const handleNextFromConfig = () => setStep('confirm');

  const handleDispatch = async () => {
    setSubmitting(true);
    try {
      // 触发父组件的 API 调用
      await onFinish(selectedCaseIds);
      setSubmitting(false);
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 2000);
    } catch {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    if (submitting || success) return;
    onClose();
  };

  const handleBack = () => {
    const idx = stepProgress.indexOf(step);
    if (idx > 0) setStep(stepProgress[idx - 1]);
  };

  if (!open) return null;

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg-elevated)', borderRadius: 16, width: 720, maxWidth: '94vw',
        maxHeight: '90vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 30px 80px rgba(0,0,0,0.35)', border: '1px solid var(--border-default)',
      }}>
        {/* ── Header ── */}
        <div style={{
          padding: '18px 24px 14px', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 17, fontWeight: 600 }}>
                {success ? '✅ 下发成功' : `🚀 批量下发 · ${stepLabels[step]}`}
              </h3>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-tertiary)' }}>
                {success
                  ? `${selectedCaseIds.length} 个用例已下发到 ${selectedDut?.hostname}`
                  : `${selectedCaseIds.length}/${autoTasks.length} 个已选 · ${selectedDut ? `目标: ${selectedDut.hostname}` : '请选择 DUT 机器'}`
                }
              </p>
            </div>
            <button onClick={handleClose} style={{
              fontSize: 24, color: 'var(--text-muted)', background: 'none', border: 'none',
              cursor: 'pointer', padding: 0, lineHeight: 1,
            }}>
              ×
            </button>
          </div>
          {!success && (
            <div style={{ display: 'flex', gap: 4, marginTop: 12 }}>
              {stepProgress.map((s, idx) => (
                <React.Fragment key={s}>
                  <div style={{
                    padding: '3px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600,
                    backgroundColor: s === step ? 'var(--accent-primary)' : 'var(--surface-secondary)',
                    color: s === step ? 'white' : 'var(--text-tertiary)',
                    transition: 'all 0.15s',
                  }}>
                    {idx + 1}. {stepLabels[s]}
                  </div>
                  {idx < stepProgress.length - 1 && (
                    <div style={{ flex: 1, height: 2, alignSelf: 'center', backgroundColor: 'var(--border-subtle)', margin: '0 4px' }} />
                  )}
                </React.Fragment>
              ))}
            </div>
          )}
        </div>

        {/* ── Body ── */}
        <div style={{
          flex: 1, overflowY: 'auto', padding: '16px 24px',
          display: 'flex', flexDirection: 'column', gap: 12,
        }}>
          {success ? (
            <div style={{ padding: '24px', textAlign: 'center' }}>
              <div style={{ fontSize: 48, marginBottom: 8 }}>✅</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#3fb950' }}>下发任务已提交</div>
              <div style={{ fontSize: 13, color: 'var(--text-tertiary)', marginTop: 4 }}>
                {selectedCaseIds.length} 个用例已下发到 {selectedDut?.hostname}
              </div>
              <div style={{
                marginTop: 16, display: 'inline-flex', gap: 8, padding: '10px 16px',
                background: 'var(--surface-secondary)', borderRadius: 8, fontSize: 12,
              }}>
                <span>DUT: {selectedDut?.hostname} ({selectedDut?.ip})</span>
                <span>·</span>
                <span>用例数: {selectedCaseIds.length}</span>
              </div>
            </div>
          ) : step === 'select-cases' ? (
            <div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                选择要下发的自动化测试用例。
              </p>
              <div style={{ marginBottom: 8 }}>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 12, color: 'var(--text-secondary)' }}>
                  <input
                    type="checkbox"
                    checked={selectedCaseIds.length === autoTasks.length}
                    onChange={toggleAllCases}
                    style={{ accentColor: 'var(--accent-primary)' }}
                  />
                  全选（{autoTasks.length} 项）
                </label>
              </div>

              {/* ── Collection search ── */}
              <div style={{
                marginBottom: 10, padding: '8px 12px', borderRadius: 8,
                backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: collections.length > 0 ? 6 : 0 }}>
                  <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>📁</span>
                  <input
                    type="search"
                    value={collectionQuery}
                    onChange={e => setCollectionQuery(e.target.value)}
                    placeholder="从预置用例集批量添加…"
                    style={{
                      flex: 1, border: 'none', outline: 'none', fontSize: 12,
                      color: 'var(--text-primary)', backgroundColor: 'transparent',
                      padding: '2px 0',
                    }}
                  />
                  {collectionSearching && <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>…</span>}
                </div>
                {collections.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {collections.map(c => (
                      <button
                        key={c.collection_id}
                        type="button"
                        onClick={() => handleAddFromCollection(c)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 6, padding: '5px 8px',
                          borderRadius: 6, border: 'none', cursor: 'pointer', width: '100%',
                          textAlign: 'left', fontSize: 11, background: 'var(--surface-primary)',
                          color: 'var(--text-primary)',
                        }}
                      >
                        <span style={{ fontFamily: 'monospace', color: 'var(--accent-primary)', fontSize: 10 }}>{c.collection_id}</span>
                        <span style={{ flex: 1 }}>{c.name}</span>
                        <span style={{ color: 'var(--text-tertiary)' }}>{c.case_count + c.auto_case_count} 用例</span>
                        <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>+ 添加</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {autoTasks.map(task => {
                  const checked = selectedCaseIds.includes(task.caseId);
                  return (
                    <label
                      key={task.id}
                      onClick={() => toggleCase(task.caseId)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
                        borderRadius: 8, cursor: 'pointer',
                        border: checked ? '1.5px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                        background: checked ? 'color-mix(in srgb, var(--accent-primary) 5%, transparent)' : 'var(--bg-primary)',
                        transition: 'all 0.1s',
                      }}
                    >
                      <input type="checkbox" checked={checked} onChange={() => {}} style={{ accentColor: 'var(--accent-primary)' }} />
                      <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--accent-cyan)', minWidth: 55 }}>{task.caseId}</span>
                      <span style={{ flex: 1, fontSize: 13, fontWeight: checked ? 600 : 500 }}>{task.caseTitle}</span>
                      <span style={{ fontSize: 10, padding: '1px 8px', borderRadius: 4, background: 'rgba(57,208,214,0.12)', color: '#39d0d6', fontWeight: 600 }}>⚡ 自动化</span>
                      <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{task.component}</span>
                      <span style={{
                        fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 8,
                        color: STATUS_COLORS[task.status], background: `${STATUS_COLORS[task.status]}15`,
                      }}>
                        {task.status === 'running' ? '▶ 执行中' : '○ 待执行'}
                      </span>
                    </label>
                  );
                })}
              </div>

              {/* ── Common batch config ── */}
              <div style={{
                marginTop: 14, padding: '12px 14px', borderRadius: 10,
                background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)',
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.3px', marginBottom: 10 }}>
                  通用配置（将作为每个用例的默认值）
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-end' }}>
                  <div style={{ minWidth: 130 }}>
                    <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4 }}>环境</label>
                    <select className="form-input form-select" value={commonEnv} onChange={e => setCommonEnv(e.target.value)}
                      style={{ width: '100%', fontSize: 11, padding: '4px 8px' }}>
                      <option value="staging">Staging</option>
                      <option value="testing">Testing</option>
                      <option value="production">Production</option>
                      <option value="dev">Dev</option>
                    </select>
                  </div>
                  <div style={{ minWidth: 100 }}>
                    <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4 }}>超时时间</label>
                    <div style={{ display: 'flex', gap: 2 }}>
                      {[15, 30, 60].map(t => (
                        <button key={t} onClick={() => setCommonTimeout(t)}
                          style={{
                            padding: '3px 8px', fontSize: 10, flex: 1,
                            border: commonTimeout === t ? '1.5px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                            borderRadius: 5, cursor: 'pointer',
                            background: commonTimeout === t ? 'color-mix(in srgb, var(--accent-primary) 8%, transparent)' : 'var(--bg-primary)',
                            color: commonTimeout === t ? 'var(--accent-primary)' : 'var(--text-secondary)',
                            fontWeight: commonTimeout === t ? 600 : 400,
                          }}>
                          {t}s
                        </button>
                      ))}
                    </div>
                  </div>
                  <div style={{ minWidth: 80 }}>
                    <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4 }}>重试</label>
                    <select className="form-input form-select" value={commonRetry} onChange={e => setCommonRetry(Number(e.target.value))}
                      style={{ width: '100%', fontSize: 11, padding: '4px 8px' }}>
                      <option value={0}>不重试</option>
                      <option value={1}>重试 1 次</option>
                      <option value={2}>重试 2 次</option>
                    </select>
                  </div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 12, color: 'var(--text-secondary)' }}>
                    <input type="checkbox" checked={commonNotify} onChange={e => setCommonNotify(e.target.checked)}
                      style={{ accentColor: 'var(--accent-primary)' }} />
                    执行完成通知
                  </label>
                </div>
              </div>
            </div>
          ) : step === 'select-dut' ? (
            <div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                选择执行 {selectedCaseIds.length} 个测试用例的目标 DUT 机器。
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {onlineDuts.map(dut => (
                  <label
                    key={dut.id}
                    onClick={() => setSelectedDut(dut)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px',
                      borderRadius: 8, cursor: 'pointer',
                      border: selectedDut?.id === dut.id ? '1.5px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                      background: selectedDut?.id === dut.id ? 'color-mix(in srgb, var(--accent-primary) 5%, transparent)' : 'var(--bg-primary)',
                      transition: 'all 0.1s',
                    }}
                  >
                    <input type="radio" name="dut" checked={selectedDut?.id === dut.id} onChange={() => setSelectedDut(dut)}
                      style={{ accentColor: 'var(--accent-primary)' }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{dut.hostname}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                        {dut.ip} · {dut.region} · {dut.os} · {dut.cpu} · {dut.memory}
                      </div>
                    </div>
                    <span style={{
                      fontSize: 10, padding: '2px 8px', borderRadius: 999, fontWeight: 600,
                      backgroundColor: 'rgba(63,185,80,0.12)', color: '#3fb950',
                    }}>
                      🟢 在线
                    </span>
                  </label>
                ))}
              </div>
            </div>
          ) : step === 'configure' ? (
            <div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                为每个选中的测试用例配置执行参数。
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {selectedTasks.map(task => {
                  const taskConfig = getConfigForCase(task);
                  return (
                    <div key={task.id} style={{
                      border: '1px solid var(--border-subtle)', borderRadius: 10,
                      overflow: 'hidden',
                    }}>
                      <div style={{
                        padding: '8px 14px', fontSize: 12, fontWeight: 600,
                        backgroundColor: 'var(--surface-secondary)',
                        borderBottom: '1px solid var(--border-subtle)',
                      }}>
                        {task.caseId} · {task.caseTitle}
                        <span style={{ fontSize: 10, color: 'var(--text-tertiary)', marginLeft: 8 }}>{task.component}</span>
                      </div>
                      <div style={{ padding: '10px 14px', display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                        {CASE_CONFIG_TEMPLATES.map(field => (
                          <div key={field.key} style={{ flex: '1 1 180px', minWidth: 140 }}>
                            <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4 }}>
                              {field.label}
                            </label>
                            {field.type === 'boolean' ? (
                              <select
                                value={String(taskConfig[field.key] ?? field.default)}
                                onChange={e => updateConfig(task.caseId, field.key, e.target.value === 'true')}
                                className="form-input form-select"
                                style={{ width: '100%', fontSize: 11, padding: '4px 8px' }}
                              >
                                <option value="true">开启</option>
                                <option value="false">关闭</option>
                              </select>
                            ) : field.type === 'number' ? (
                              <input
                                type="number"
                                value={taskConfig[field.key] ?? field.default}
                                onChange={e => updateConfig(task.caseId, field.key, Number(e.target.value))}
                                className="form-input"
                                style={{ width: '100%', fontSize: 11, padding: '4px 8px' }}
                              />
                            ) : (
                              <input
                                type="text"
                                value={taskConfig[field.key] ?? field.default}
                                onChange={e => updateConfig(task.caseId, field.key, String(e.target.value))}
                                className="form-input"
                                style={{ width: '100%', fontSize: 11, padding: '4px 8px' }}
                              />
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                请确认以下下发信息。
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{
                  padding: '10px 14px', borderRadius: 8,
                  background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)',
                }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', marginBottom: 6 }}>DUT 机器</div>
                  <div style={{ fontSize: 13 }}>{selectedDut?.hostname} ({selectedDut?.ip}) · {selectedDut?.region} · {selectedDut?.os}</div>
                </div>
                <div style={{
                  padding: '10px 14px', borderRadius: 8,
                  background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)',
                }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', marginBottom: 6 }}>测试用例（{selectedCaseIds.length} 个）</div>
                  {selectedTasks.map(task => {
                    const cfg = getConfigForCase(task);
                    return (
                      <div key={task.id} style={{
                        fontSize: 12, padding: '4px 0', borderBottom: '0.5px solid var(--border-subtle)',
                        display: 'flex', gap: 8, alignItems: 'center',
                      }}>
                        <span style={{ fontFamily: 'monospace', color: 'var(--accent-cyan)', fontSize: 11, minWidth: 55 }}>{task.caseId}</span>
                        <span style={{ flex: 1 }}>{task.caseTitle}</span>
                        <span style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>超时 {cfg.timeout_sec ?? 300}s</span>
                        <span style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>重试: {cfg.retry_on_fail ? '是' : '否'}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        {!success && (
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '12px 24px', borderTop: '1px solid var(--border-subtle)',
            background: 'var(--bg-tertiary)', flexShrink: 0,
          }}>
            <button className="btn btn--ghost btn--sm" onClick={step === 'select-cases' ? handleClose : handleBack} disabled={submitting}>
              {step === 'select-cases' ? '取消' : '上一步'}
            </button>

            {step === 'select-cases' && (
              <button
                className="btn btn--primary"
                onClick={handleNextFromCases}
                disabled={selectedCaseIds.length === 0}
                style={{ padding: '8px 24px', fontSize: 13, fontWeight: 600 }}
              >
                下一步 → 选择 DUT（{selectedCaseIds.length} 个）
              </button>
            )}

            {step === 'select-dut' && (
              <button
                className="btn btn--primary"
                onClick={handleNextFromDut}
                disabled={!selectedDut}
                style={{ padding: '8px 24px', fontSize: 13, fontWeight: 600 }}
              >
                下一步 → 配置参数
              </button>
            )}

            {step === 'configure' && (
              <button
                className="btn btn--primary"
                onClick={handleNextFromConfig}
                style={{ padding: '8px 24px', fontSize: 13, fontWeight: 600 }}
              >
                下一步 → 确认下发
              </button>
            )}

            {step === 'confirm' && (
              <button
                className="btn btn--primary"
                onClick={handleDispatch}
                disabled={submitting}
                style={{ padding: '8px 24px', fontSize: 13, fontWeight: 600 }}
              >
                {submitting ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{
                      width: 12, height: 12, border: '2px solid rgba(255,255,255,0.3)',
                      borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block',
                      animation: 'spin 0.6s linear infinite',
                    }} />
                    下发中...
                  </span>
                ) : `🚀 确认下发 ${selectedCaseIds.length} 个`}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default DispatchWorkflow;
