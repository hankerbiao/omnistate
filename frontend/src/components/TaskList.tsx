import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type {
  ExecutionTask,
  TaskStatus,
  AutomationTestCaseResponse,
  AutomationConfigField,
  DispatchCaseItem,
  ExecutionTaskCaseSummary,
  DispatchTaskResponse,
  AttachmentInfo,
} from '../types';
import PageToolbar, { StatPill } from './ui/PageToolbar';

interface TaskListProps {
  onLogout?: () => void;
}

interface DispatchModalState {
  isOpen: boolean;
  scheduleType: 'IMMEDIATE' | 'SCHEDULED';
  plannedAt: string;
  selectedCases: string[];
  category: string;
  projectTag: string;
  loading: boolean;
  submitting: boolean;
  error: string | null;
}

const getConfigFieldInputType = (fieldType?: string) => {
  const t = (fieldType || 'str').toLowerCase();
  if (t === 'int' || t === 'float' || t === 'number') return 'number';
  return 'text';
};

const normalizeConfigValue = (rawValue: unknown, field: AutomationConfigField) => {
  const t = (field.type || 'str').toLowerCase();
  if (t === 'bool' || t === 'boolean') return Boolean(rawValue);
  if (rawValue === '' || rawValue === null || rawValue === undefined) return '';
  // 如果是 file 类型或对象，保持原样
  if (t === 'file' || (typeof rawValue === 'object' && rawValue !== null)) {
    return rawValue;
  }
  if (t === 'int' || t === 'number') return Number.parseInt(String(rawValue), 10);
  if (t === 'float') return Number.parseFloat(String(rawValue));
  return String(rawValue);
};

const buildDefaultCaseConfig = (caseItem?: AutomationTestCaseResponse): Record<string, unknown> => {
  return (caseItem?.param_spec || []).reduce<Record<string, unknown>>((acc, field) => {
    acc[field.name] = field.default ?? '';
    return acc;
  }, {});
};

const buildDispatchCaseItems = (
  selectedCaseIds: string[],
  autoCases: AutomationTestCaseResponse[],
  caseConfigs: Record<string, Record<string, unknown>>,
): DispatchCaseItem[] => {
  const map = new Map(autoCases.map(c => [c.auto_case_id, c]));
  return selectedCaseIds.map(id => ({
    auto_case_id: id,
    parameters: caseConfigs[id] || buildDefaultCaseConfig(map.get(id)),
  }));
};

const formatAttachmentSize = (size: number) => {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
};

const STATUS_THEME: Record<string, { color: string; bg: string; label: string; dot?: string }> = {
  PENDING: { color: '#eab308', bg: 'rgba(234,179,8,0.1)', label: '待处理', dot: '#eab308' },
  QUEUED: { color: '#f59e0b', bg: 'rgba(245,158,11,0.1)', label: '排队中', dot: '#f59e0b' },
  READY: { color: '#60a5fa', bg: 'rgba(96,165,250,0.1)', label: '就绪', dot: '#60a5fa' },
  RUNNING: { color: '#38bdf8', bg: 'rgba(56,189,248,0.1)', label: '运行中', dot: '#38bdf8' },
  SUCCESS: { color: '#22c55e', bg: 'rgba(34,197,94,0.1)', label: '成功', dot: '#22c55e' },
  PASSED: { color: '#22c55e', bg: 'rgba(34,197,94,0.1)', label: '已通过', dot: '#22c55e' },
  FAILED: { color: '#ef4444', bg: 'rgba(239,68,68,0.1)', label: '失败', dot: '#ef4444' },
  DISPATCH_FAILED: { color: '#ef4444', bg: 'rgba(239,68,68,0.1)', label: '下发失败', dot: '#ef4444' },
  CANCELLED: { color: '#94a3b8', bg: 'rgba(148,163,184,0.1)', label: '已取消', dot: '#94a3b8' },
  SCHEDULED: { color: '#a78bfa', bg: 'rgba(167,139,250,0.1)', label: '定时', dot: '#a78bfa' },
  IMMEDIATE: { color: '#39d0d6', bg: 'rgba(57,208,214,0.1)', label: '立即', dot: '#39d0d6' },
  DISPATCHED: { color: '#39d0d6', bg: 'rgba(57,208,214,0.1)', label: '已下发', dot: '#39d0d6' },
  COMPLETED: { color: '#22c55e', bg: 'rgba(34,197,94,0.1)', label: '已完成', dot: '#22c55e' },
  CONSUMED: { color: '#34d399', bg: 'rgba(52,211,153,0.1)', label: '已消费', dot: '#34d399' },
  NOT_CONSUMED: { color: '#94a3b8', bg: 'rgba(148,163,184,0.1)', label: '未消费', dot: '#94a3b8' },
};

const getStatus = (s: string) => STATUS_THEME[s?.toUpperCase()] || { color: '#94a3b8', bg: 'rgba(148,163,184,0.1)', label: s || '-', dot: '#94a3b8' };

const FILTER_TABS = [
  { key: null, label: '全部' },
  { key: 'RUNNING', label: '运行中' },
  { key: 'PENDING', label: '待处理' },
  { key: 'COMPLETED', label: '已完成' },
  { key: 'FAILED', label: '失败' },
];

const TASK_CARD_STATUS_BORDERS: Record<string, string> = {
  RUNNING: '#38bdf8',
  PENDING: '#eab308',
  QUEUED: '#f59e0b',
  SUCCESS: '#22c55e',
  PASSED: '#22c55e',
  FAILED: '#ef4444',
  DISPATCH_FAILED: '#ef4444',
  COMPLETED: '#22c55e',
  CANCELLED: '#64748b',
};

const TaskList: React.FC<TaskListProps> = () => {
  const [tasks, setTasks] = useState<ExecutionTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<TaskStatus | null>(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [rerunningTaskId, setRerunningTaskId] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<string | null>('RUNNING');
  const [searchQuery, setSearchQuery] = useState('');

  const [dispatchModal, setDispatchModal] = useState<DispatchModalState>({
    isOpen: false,
    scheduleType: 'IMMEDIATE',
    plannedAt: '',
    selectedCases: [],
    category: 'bmc',
    projectTag: 'universal',
    loading: false,
    submitting: false,
    error: null,
  });

  const [autoCases, setAutoCases] = useState<AutomationTestCaseResponse[]>([]);
  const [caseSearchQuery, setCaseSearchQuery] = useState('');
  const [caseConfigs, setCaseConfigs] = useState<Record<string, Record<string, unknown>>>({});
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const [expandedCaseKeys, setExpandedCaseKeys] = useState<string[]>([]);
  const [caseFileUploading, setCaseFileUploading] = useState<Record<string, boolean>>({});
  const [caseFileAttachments, setCaseFileAttachments] = useState<Record<string, AttachmentInfo>>({});

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listTasks({ limit: 50 });
      setTasks(res.data || []);
    } catch {
      setError('获取任务列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  const openDispatchModal = async () => {
    setDispatchModal(prev => ({ ...prev, isOpen: true, loading: true, error: null }));
    try {
      const res = await api.listAutomationTestCases({ limit: 200 });
      setAutoCases(res.data || []);
      setCaseConfigs({});
      setCaseSearchQuery('');
    } catch {
      setDispatchModal(prev => ({ ...prev, error: '获取用例失败' }));
    } finally {
      setDispatchModal(prev => ({ ...prev, loading: false }));
    }
  };

  const closeDispatchModal = () => {
    setDispatchModal({
      isOpen: false, scheduleType: 'IMMEDIATE', plannedAt: '', selectedCases: [],
      category: 'bmc', projectTag: 'universal', loading: false, submitting: false,
      error: null,
    });
    setCaseConfigs({});
  };

  const toggleCaseSelection = (caseId: string) => {
    const selected = dispatchModal.selectedCases.includes(caseId);
    setDispatchModal(prev => ({
      ...prev,
      selectedCases: selected ? prev.selectedCases.filter(id => id !== caseId) : [...prev.selectedCases, caseId],
    }));
    if (!selected) {
      const c = autoCases.find(item => item.auto_case_id === caseId);
      setCaseConfigs(prev => ({ ...prev, [caseId]: buildDefaultCaseConfig(c) }));
    } else {
      setCaseConfigs(prev => { const n = { ...prev }; delete n[caseId]; return n; });
    }
  };

  const uploadCaseConfigFile = async (autoCaseId: string, field: AutomationConfigField, file: File) => {
    const key = `${autoCaseId}|${field.name}`;
    setCaseFileUploading(prev => ({ ...prev, [key]: true }));
    try {
      const result = await api.uploadAttachment(file);
      setCaseFileAttachments(prev => ({ ...prev, [key]: result }));
      // 存储完整的文件信息，供后端提取到 files 字段
      handleCaseConfigChange(autoCaseId, field, {
        type: "file",
        file_id: result.file_id,
        object_name: result.storage_path,
        sha256: result.sha256,
      });
    } catch {
      // upload failed silently
    } finally {
      setCaseFileUploading(prev => ({ ...prev, [key]: false }));
    }
  };

  const removeCaseConfigFile = (autoCaseId: string, field: AutomationConfigField) => {
    const key = `${autoCaseId}|${field.name}`;
    setCaseFileAttachments(prev => { const n = { ...prev }; delete n[key]; return n; });
    handleCaseConfigChange(autoCaseId, field, '');
  };

  const handleCaseConfigChange = (autoCaseId: string, field: AutomationConfigField, rawValue: unknown) => {
    setCaseConfigs(prev => ({
      ...prev,
      [autoCaseId]: { ...(prev[autoCaseId] || {}), [field.name]: normalizeConfigValue(rawValue, field) },
    }));
  };

  const handleDispatchSubmit = async () => {
    const { scheduleType, plannedAt, selectedCases, category, projectTag } = dispatchModal;
    if (selectedCases.length === 0) {
      setDispatchModal(prev => ({ ...prev, error: '请选择至少一个用例' }));
      return;
    }
    if (scheduleType === 'SCHEDULED' && !plannedAt) {
      setDispatchModal(prev => ({ ...prev, error: '请选择计划执行时间' }));
      return;
    }
    const caseMap = new Map(autoCases.map(c => [c.auto_case_id, c]));
    for (const id of selectedCases) {
      const c = caseMap.get(id);
      if (!c) { setDispatchModal(prev => ({ ...prev, error: `未找到用例：${id}` })); return; }
      const vals = caseConfigs[id] || buildDefaultCaseConfig(c);
      for (const f of c.param_spec || []) {
        const v = vals[f.name];
        if (f.required && (v === undefined || v === null || (typeof v === 'string' && v.trim() === ''))) {
          setDispatchModal(prev => ({ ...prev, error: `请填写 ${c.auto_case_id} 的配置项：${f.label || f.name}` }));
          return;
        }
      }
    }

    setDispatchModal(prev => ({ ...prev, submitting: true, error: null }));
    try {
      const cases = buildDispatchCaseItems(selectedCases, autoCases, caseConfigs);
      const first = autoCases.find(c => c.auto_case_id === selectedCases[0]);
      await api.dispatchTask({
        schedule_type: scheduleType,
        planned_at: scheduleType === 'SCHEDULED' ? plannedAt : undefined,
        category, project_tag: projectTag,
        repo_url: first?.repo_url || undefined,
        branch: first?.code_snapshot?.branch || undefined,
        pytest_options: {}, timeout: first?.report_meta?.timeout || 0,
        cases,
      });
      closeDispatchModal();
      fetchTasks();
    } catch {
      setDispatchModal(prev => ({ ...prev, error: '下发任务失败' }));
    } finally {
      setDispatchModal(prev => ({ ...prev, submitting: false }));
    }
  };

  const handleTaskClick = async (taskId: string) => {
    setModalLoading(true);
    try {
      const res = await api.getTaskStatus(taskId);
      setSelectedTask(res.data);
    } catch {
      alert('获取任务详情失败');
    } finally {
      setModalLoading(false);
    }
  };

  const handleRerunTask = async (task: Pick<ExecutionTask, 'task_id'>, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setError(null);
    setSuccessMessage(null);
    setRerunningTaskId(task.task_id);
    try {
      const res = await api.rerunTask(task.task_id, {});
      const payload = res.data as DispatchTaskResponse | undefined;
      setSuccessMessage(payload?.task_id ? `已创建重跑任务 ${payload.task_id}` : `任务已重新运行`);
      setTimeout(() => setSuccessMessage(null), 3000);
      await fetchTasks();
      if (selectedTask?.task_id === task.task_id) {
        const sr = await api.getTaskStatus(task.task_id);
        setSelectedTask(sr.data);
      }
    } catch {
      setError(`重新运行任务失败`);
    } finally {
      setRerunningTaskId(null);
    }
  };

  const toggleCaseDetails = (caseKey: string) => {
    setExpandedCaseKeys(prev => prev.includes(caseKey) ? prev.filter(k => k !== caseKey) : [...prev, caseKey]);
  };

  const handleDeleteTask = async (taskId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`确定删除任务 ${taskId}？`)) return;
    try {
      await api.deleteTask(taskId);
      fetchTasks();
    } catch {
      alert('删除任务失败');
    }
  };

  const filteredTasks = tasks.filter(task => {
    if (activeFilter === 'FAILED') return task.overall_status === 'FAILED' || task.overall_status === 'DISPATCH_FAILED';
    if (activeFilter === 'PENDING') return task.overall_status === 'PENDING' || task.overall_status === 'QUEUED';
    if (activeFilter === 'COMPLETED') return task.overall_status === 'COMPLETED' || task.overall_status === 'SUCCESS' || task.overall_status === 'PASSED';
    if (activeFilter) return task.overall_status === activeFilter;
    return true;
  }).filter(task => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return task.task_id.toLowerCase().includes(q) || task.source_task_id?.toLowerCase().includes(q);
  });

  const statusCounts = tasks.reduce((acc, t) => {
    acc[t.overall_status] = (acc[t.overall_status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const getFilterCount = (key: string | null) => {
    if (!key) return tasks.length;
    if (key === 'FAILED') return (statusCounts['FAILED'] || 0) + (statusCounts['DISPATCH_FAILED'] || 0);
    if (key === 'PENDING') return (statusCounts['PENDING'] || 0) + (statusCounts['QUEUED'] || 0);
    if (key === 'COMPLETED') return (statusCounts['COMPLETED'] || 0) + (statusCounts['SUCCESS'] || 0) + (statusCounts['PASSED'] || 0);
    return statusCounts[key] || 0;
  };

  const renderConfigField = (autoCaseId: string, caseItem: AutomationTestCaseResponse, field: AutomationConfigField) => {
    const configValues = caseConfigs[autoCaseId] || buildDefaultCaseConfig(caseItem);
    const currentValue = configValues[field.name];
    const normalizedType = (field.type || 'str').toLowerCase();

    if (field.options && field.options.length > 0) {
      return (
        <select
          style={s.fieldSelect}
          value={String(currentValue ?? '')}
          onChange={e => handleCaseConfigChange(autoCaseId, field, e.target.value)}
        >
          <option value="">请选择</option>
          {field.options.map((opt, i) => (
            <option key={i} value={String(opt.value)}>{opt.label || String(opt.value)}</option>
          ))}
        </select>
      );
    }
    if (normalizedType === 'bool' || normalizedType === 'boolean') {
      return (
        <label style={s.toggleLabel}>
          <input type="checkbox" checked={Boolean(currentValue)} onChange={e => handleCaseConfigChange(autoCaseId, field, e.target.checked)} />
          <span style={s.toggleSwitch} />
        </label>
      );
    }
    if (normalizedType === 'file') {
      const key = `${autoCaseId}|${field.name}`;
      const uploaded = caseFileAttachments[key];
      const uploading = caseFileUploading[key];
      if (uploaded) {
        return (
          <div style={s.fileChip}>
            <span>{uploaded.original_filename}</span>
            <button style={s.fileChipRemove} onClick={() => removeCaseConfigFile(autoCaseId, field)}>×</button>
          </div>
        );
      }
      return (
        <label style={s.fileBtn}>
          <input type="file" style={{ display: 'none' }} disabled={uploading}
            onChange={e => { const f = e.currentTarget.files?.[0]; if (f) uploadCaseConfigFile(autoCaseId, field, f); e.currentTarget.value = ''; }}
          />
          {uploading ? '上传中...' : '选择文件'}
        </label>
      );
    }
    return (
      <input
        type={getConfigFieldInputType(field.type)}
        style={s.fieldInput}
        value={String(currentValue ?? '')}
        onChange={e => handleCaseConfigChange(autoCaseId, field, e.target.value)}
        placeholder={field.default !== undefined ? String(field.default) : ''}
      />
    );
  };

  const renderCaseConfig = (autoCaseId: string) => {
    const caseItem = autoCases.find(c => c.auto_case_id === autoCaseId);
    if (!caseItem) return null;
    const fields = caseItem.param_spec || [];
    return (
      <div style={s.configCard}>
        <div style={s.configCardHeader}>
          <div>
            <div style={s.configCardTitle}>{caseItem.auto_case_id}</div>
            <div style={s.configCardSub}>{caseItem.script_name || caseItem.name}</div>
          </div>
          <span style={s.configCardBadge}>{fields.length} 项</span>
        </div>
        {fields.length === 0 ? (
          <div style={s.configEmpty}>无配置项</div>
        ) : (
          <div style={s.configFields}>
            {fields.map(field => (
              <div key={field.name} style={s.configField}>
                <div style={s.configFieldLabel}>
                  {field.label || field.name}
                  {field.required && <span style={{ color: '#ef4444', marginLeft: 4 }}>*</span>}
                  <span style={s.configFieldType}>{field.type || 'str'}</span>
                </div>
                {field.description && <div style={s.configFieldDesc}>{field.description}</div>}
                {renderConfigField(autoCaseId, caseItem, field)}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  const renderTaskCases = (cases: ExecutionTaskCaseSummary[] | undefined) => {
    if (!cases?.length) return <div style={s.emptySmall}>暂无用例执行信息</div>;
    return (
      <div style={s.caseGrid}>
        {cases.map(c => {
          const caseKey = `${c.task_id}-${c.case_id}`;
          const st = getStatus(c.status);
          const dispatchSt = getStatus(c.dispatch_status);
          const resultSt = getStatus(c.result_data?.status || c.status);
          const assertions = c.result_data?.assertions || [];
          const progressText = typeof c.progress_percent === 'number' ? `${Math.round(c.progress_percent)}%` : '-';
          const isExpanded = expandedCaseKeys.includes(caseKey);
          const hasDetail =
            Boolean(c.result_data?.event_type) ||
            Boolean(c.result_data?.phase) ||
            assertions.length > 0 ||
            Boolean(c.result_data?.error && Object.keys(c.result_data.error).length > 0) ||
            Boolean(c.result_data?.data && Object.keys(c.result_data.data).length > 0);
          return (
            <div key={caseKey} style={s.caseCard}>
              <div style={s.caseCardTop}>
                <div>
                  <div style={s.caseCardTitle}>{c.title || c.case_id}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
                    {c.auto_case_id || c.case_id}
                  </div>
                </div>
                <span style={{ ...s.caseBadge, background: st.bg, color: st.color }}>{st.label}</span>
              </div>
              <div style={s.caseMetrics}>
                <div style={s.caseMetric}>
                  <span style={s.caseMetricLabel}>进度</span>
                  <span style={s.caseMetricValue}>{progressText}</span>
                </div>
                <div style={s.caseMetric}>
                  <span style={s.caseMetricLabel}>下发</span>
                  <span style={s.caseMetricValue}>{c.dispatch_attempts}</span>
                </div>
                <div style={s.caseMetric}>
                  <span style={s.caseMetricLabel}>事件</span>
                  <span style={s.caseMetricValue}>{c.event_count}</span>
                </div>
                <div style={s.caseMetric}>
                  <span style={s.caseMetricLabel}>断言</span>
                  <span style={s.caseMetricValue}>{assertions.length}</span>
                </div>
              </div>
              <div style={s.caseInfoRow}>
                <span style={{ ...s.caseInfoBadge, background: dispatchSt.bg, color: dispatchSt.color }}>
                  下发 {dispatchSt.label}
                </span>
                {c.last_event_at && (
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
                    {new Date(c.last_event_at).toLocaleString('zh-CN')}
                  </span>
                )}
              </div>
              {c.failure_message && <div style={s.caseError}>{c.failure_message}</div>}
              {hasDetail && (
                <div style={s.caseDetailWrap}>
                  <button style={s.caseDetailToggle} onClick={() => toggleCaseDetails(caseKey)}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)' }}>执行细节</span>
                    <span style={{ fontSize: 12, color: 'var(--accent-cyan)', fontWeight: 600 }}>
                      {isExpanded ? '收起 ▲' : '展开 ▼'}
                    </span>
                  </button>
                  {isExpanded && (
                    <div style={{ marginTop: 12 }}>
                      <div style={s.caseDetailGrid2}>
                        <div style={s.caseDetailBlock2}>
                          <span style={s.caseDetailBlockLabel2}>开始时间</span>
                          <span style={s.caseDetailBlockVal2}>{c.started_at ? new Date(c.started_at).toLocaleString('zh-CN') : '-'}</span>
                        </div>
                        <div style={s.caseDetailBlock2}>
                          <span style={s.caseDetailBlockLabel2}>结束时间</span>
                          <span style={s.caseDetailBlockVal2}>{c.finished_at ? new Date(c.finished_at).toLocaleString('zh-CN') : '-'}</span>
                        </div>
                        <div style={s.caseDetailBlock2}>
                          <span style={s.caseDetailBlockLabel2}>最近事件</span>
                          <span style={{ ...s.caseDetailBlockVal2, fontFamily: "'JetBrains Mono', monospace" }}>{c.last_event_id || '-'}</span>
                        </div>
                        <div style={s.caseDetailBlock2}>
                          <span style={s.caseDetailBlockLabel2}>最近上报</span>
                          <span style={s.caseDetailBlockVal2}>{c.last_event_at ? new Date(c.last_event_at).toLocaleString('zh-CN') : '-'}</span>
                        </div>
                      </div>
                      <div style={s.caseMetaRow}>
                        {c.result_data?.event_type && <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>事件 {c.result_data.event_type}</span>}
                        {c.result_data?.phase && <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>阶段 {c.result_data.phase}</span>}
                        {c.result_data?.status && (
                          <span style={{ ...s.caseInfoBadge, background: resultSt.bg, color: resultSt.color }}>回报 {resultSt.label}</span>
                        )}
                      </div>
                      {assertions.length > 0 && (
                        <div style={{ marginTop: 12 }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 8 }}>断言步骤</div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {assertions.map((a, i) => {
                              const aSt = getStatus(a.status || '');
                              const msg = typeof a.error?.message === 'string' ? a.error.message : '';
                              return (
                                <div key={`${c.case_id}-assert-${i}`} style={s.assertionItem}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
                                      {a.seq ? `#${a.seq} ` : ''}{a.name || '未命名断言'}
                                    </span>
                                    <span style={{ ...s.caseInfoBadge, background: aSt.bg, color: aSt.color }}>
                                      {aSt.label}
                                    </span>
                                  </div>
                                  {a.timestamp && (
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, fontFamily: "'JetBrains Mono', monospace" }}>
                                      {new Date(a.timestamp).toLocaleString('zh-CN')}
                                    </div>
                                  )}
                                  {msg && <div style={{ ...s.caseError, marginTop: 6, fontSize: 11 }}>{msg}</div>}
                                  {a.data && Object.keys(a.data).length > 0 && (
                                    <pre style={s.codeBlock}>{JSON.stringify(a.data, null, 2)}</pre>
                                  )}
                                  {!a.data && a.error && Object.keys(a.error).length > 0 && (
                                    <pre style={s.codeBlock}>{JSON.stringify(a.error, null, 2)}</pre>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                      {c.result_data?.data && Object.keys(c.result_data.data).length > 0 && (
                        <div style={{ marginTop: 12 }}>
                          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>结果数据</div>
                          <pre style={s.codeBlock}>{JSON.stringify(c.result_data.data, null, 2)}</pre>
                        </div>
                      )}
                      {c.result_data?.error && Object.keys(c.result_data.error).length > 0 && assertions.length === 0 && (
                        <div style={{ marginTop: 12 }}>
                          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>错误数据</div>
                          <pre style={s.codeBlock}>{JSON.stringify(c.result_data.error, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="page-content" style={s.wrapper}>
      <PageToolbar
        meta={(
          <>
            <StatPill label="全部" value={tasks.length} />
            <StatPill label="当前筛选" value={filteredTasks.length} tone="info" />
          </>
        )}
        actions={(
          <>
            <div style={s.searchBox}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--text-muted)', flexShrink: 0 }}><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
              <input
                className="form-input"
                style={s.searchInput}
                type="text"
                placeholder="搜索任务 ID..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
            </div>
            <button type="button" className="btn btn--secondary btn--sm" onClick={fetchTasks} disabled={loading}>
              刷新
            </button>
            <button type="button" className="btn btn--primary btn--sm" onClick={openDispatchModal}>
              下发任务
            </button>
          </>
        )}
      />

      <div className="filter-strip" style={{ marginBottom: 16 }}>
        <div className="segmented-control" role="group" aria-label="任务状态筛选">
          {FILTER_TABS.map(tab => (
            <button
              key={tab.key || 'all'}
              type="button"
              className={`segmented-control__btn${activeFilter === tab.key ? ' segmented-control__btn--active' : ''}`}
              onClick={() => setActiveFilter(tab.key)}
            >
              {tab.label}
              <span style={{
                marginLeft: 6,
                fontSize: 11,
                opacity: activeFilter === tab.key ? 1 : 0.7,
              }}
              >
                {getFilterCount(tab.key)}
              </span>
            </button>
          ))}
        </div>
      </div>

      {error && <div className="error-banner" style={{ marginBottom: 16 }}>{error}</div>}
      {successMessage && <div style={s.successBanner}><span>✓</span> {successMessage}</div>}

      {/* ──────── TASK LIST (中间) ──────── */}
      <div style={s.list}>
        {loading ? (
          <div style={s.loadingState}>
            <div style={s.spinner} />
            <span>加载中...</span>
          </div>
        ) : filteredTasks.length === 0 ? (
          <div style={s.emptyState}>
            <div style={s.emptyIcon}>○</div>
            <p>暂无任务</p>
          </div>
        ) : (
          <div style={s.taskList}>
            {filteredTasks.map(task => {
              const borderColor = TASK_CARD_STATUS_BORDERS[task.overall_status] || 'var(--border-default)';
              const st = getStatus(task.overall_status);
              const isExpanded = expandedTaskId === task.task_id;
              return (
                <div key={task.task_id} style={{ ...s.taskCard, borderLeft: `3px solid ${borderColor}` }}>
                  <div style={s.taskCardMain}>
                    <div style={s.taskCardLeft}>
                      <div style={s.taskCardRow}>
                        <span style={s.taskId} onClick={() => handleTaskClick(task.task_id)}>{task.task_id}</span>
                        {task.source_task_id && <span style={s.sourceTag}>重跑</span>}
                        <span style={{ ...s.statusDot, background: st.dot }} />
                        <span style={{ ...s.statusLabel, color: st.color }}>{st.label}</span>
                      </div>
                      <div style={s.taskMeta}>
                        <span style={s.metaItem}>{(task.cases || []).length}/{task.case_count} 用例</span>
                        <span style={s.metaDot}>·</span>
                        <span style={s.metaItem}>{getStatus(task.schedule_type).label}</span>
                        {task.agent_id && <>
                          <span style={s.metaDot}>·</span>
                          <span style={s.metaItem}>代理 {task.agent_id}</span>
                        </>}
                      </div>
                    </div>
                    <div style={s.taskCardRight}>
                      <span style={s.taskTime}>{new Date(task.created_at).toLocaleString('zh-CN')}</span>
                      <div style={s.taskActions}>
                        <button style={s.actionBtn} onClick={e => handleRerunTask(task, e)} disabled={rerunningTaskId === task.task_id} title="重新运行">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>
                        </button>
                        <button style={s.actionDangerBtn} onClick={e => handleDeleteTask(task.task_id, e)} title="删除">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
                        </button>
                      </div>
                    </div>
                  </div>
                  <div style={s.taskCardBottom}>
                    <button style={s.expandBtn} onClick={() => setExpandedTaskId(isExpanded ? null : task.task_id)}>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ transform: isExpanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }}><polyline points="9 18 15 12 9 6" /></svg>
                      用例执行情况
                      <span style={s.expandCount}>{(task.cases || []).length}/{task.case_count}</span>
                    </button>
                    <button style={s.detailBtn} onClick={() => handleTaskClick(task.task_id)}>
                      详情
                    </button>
                  </div>
                  {isExpanded && (
                    <div style={s.expandedSection}>
                      {renderTaskCases(task.cases)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ──────── TASK DETAIL MODAL ──────── */}
      {selectedTask && (
        <div style={s.overlay} onClick={() => setSelectedTask(null)}>
          <div style={s.modal} onClick={e => e.stopPropagation()}>
            <div style={s.modalHeader}>
              <h2 style={s.modalTitle}>任务详情</h2>
              <button style={s.closeBtn} onClick={() => setSelectedTask(null)}>×</button>
            </div>
            {modalLoading ? (
              <div style={s.modalLoading}><div style={s.spinner} /></div>
            ) : (
              <div style={s.modalBody}>
                {/* Info Grid */}
                <div style={s.detailGrid}>
                  <div style={s.detailItem}>
                    <span style={s.detailLabel}>任务 ID</span>
                    <span style={s.detailValue}>{selectedTask.task_id}</span>
                  </div>
                  <div style={s.detailItem}>
                    <span style={s.detailLabel}>重跑来源</span>
                    <span style={s.detailValue}>{selectedTask.source_task_id || '-'}</span>
                  </div>
                  <div style={s.detailItem}>
                    <span style={s.detailLabel}>代理</span>
                    <span style={s.detailValue}>{selectedTask.agent_id || '-'}</span>
                  </div>
                  <div style={s.detailItem}>
                    <span style={s.detailLabel}>下发通道</span>
                    <span style={s.detailValue}>{selectedTask.dispatch_channel}</span>
                  </div>
                  <div style={s.detailItem}>
                    <span style={s.detailLabel}>用例数</span>
                    <span style={s.detailValue}>{selectedTask.case_count}</span>
                  </div>
                </div>

                {/* Status Row */}
                <div style={s.statusRow}>
                  {[
                    { label: '调度', status: selectedTask.schedule_status },
                    { label: '下发', status: selectedTask.dispatch_status },
                    { label: '消费', status: selectedTask.consume_status },
                    { label: '整体', status: selectedTask.overall_status },
                  ].map(item => {
                    const st = getStatus(item.status);
                    return (
                      <div key={item.label} style={s.statusPill}>
                        <span style={s.statusPillLabel}>{item.label}</span>
                        <span style={{ ...s.statusPillValue, background: st.bg, color: st.color }}>{st.label}</span>
                      </div>
                    );
                  })}
                </div>

                {/* Time Info */}
                <div style={s.section}>
                  <h3 style={s.sectionTitle}>时间信息</h3>
                  <div style={s.timeGrid}>
                    <div><span style={s.timeLabel}>计划执行</span><span style={s.timeValue}>{selectedTask.planned_at ? new Date(selectedTask.planned_at).toLocaleString('zh-CN') : '-'}</span></div>
                    <div><span style={s.timeLabel}>实际触发</span><span style={s.timeValue}>{selectedTask.triggered_at ? new Date(selectedTask.triggered_at).toLocaleString('zh-CN') : '-'}</span></div>
                    <div><span style={s.timeLabel}>创建时间</span><span style={s.timeValue}>{new Date(selectedTask.created_at).toLocaleString('zh-CN')}</span></div>
                    <div><span style={s.timeLabel}>更新时间</span><span style={s.timeValue}>{new Date(selectedTask.updated_at).toLocaleString('zh-CN')}</span></div>
                  </div>
                </div>

                {/* Execution Config */}
                {(selectedTask.request_payload?.execution_config) && (
                  <div style={s.section}>
                    <h3 style={s.sectionTitle}>执行配置</h3>
                    <div style={s.configDisplay}>
                      <div style={s.configRow}>
                        <span>步骤失败</span>
                        <span>{selectedTask.request_payload.execution_config.step_on_failure}</span>
                      </div>
                      <div style={s.configRow}>
                        <span>用例失败</span>
                        <span>{selectedTask.request_payload.execution_config.case_on_failure}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Attachments */}
                {selectedTask.request_payload?.attachments?.length ? (
                  <div style={s.section}>
                    <h3 style={s.sectionTitle}>附件</h3>
                    <div style={s.attachList}>
                      {selectedTask.request_payload.attachments.map(a => (
                        <div key={a.file_id} style={s.attachItem}>
                          <span>{a.original_filename}</span>
                          <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{formatAttachmentSize(a.size)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {/* Actions */}
                <div style={s.modalActions}>
                  <button style={s.ghostBtn} onClick={e => handleRerunTask(selectedTask, e)} disabled={rerunningTaskId === selectedTask.task_id}>
                    重新运行
                  </button>
                </div>

                {selectedTask.error_message && (
                  <pre style={s.errorBlock}>{selectedTask.error_message}</pre>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ──────── DISPATCH MODAL ──────── */}
      {dispatchModal.isOpen && (
        <div style={s.overlay} onClick={closeDispatchModal}>
          <div style={s.dispatchModal} onClick={e => e.stopPropagation()}>
            <div style={s.modalHeader}>
              <h2 style={s.modalTitle}>下发任务</h2>
              <button style={s.closeBtn} onClick={closeDispatchModal}>×</button>
            </div>
            {dispatchModal.loading ? (
              <div style={s.modalLoading}><div style={s.spinner} /></div>
            ) : (
              <div style={s.dispatchBody}>
                {/* Row 1: Schedule + Category + Tag */}
                <div style={s.formRow3}>
                  <div style={s.formGroup}>
                    <label style={s.formLabel}>下发方式</label>
                    <div style={s.toggleGroup}>
                      <button
                        style={{ ...s.toggleBtn, ...(dispatchModal.scheduleType === 'IMMEDIATE' ? s.toggleBtnActive : {}) }}
                        onClick={() => setDispatchModal(prev => ({ ...prev, scheduleType: 'IMMEDIATE', plannedAt: '' }))}
                      >
                        立即
                      </button>
                      <button
                        style={{ ...s.toggleBtn, ...(dispatchModal.scheduleType === 'SCHEDULED' ? s.toggleBtnActive : {}) }}
                        onClick={() => setDispatchModal(prev => ({ ...prev, scheduleType: 'SCHEDULED' }))}
                      >
                        定时
                      </button>
                    </div>
                    {dispatchModal.scheduleType === 'SCHEDULED' && (
                      <input type="datetime-local" style={s.fieldInput}
                        value={dispatchModal.plannedAt}
                        onChange={e => setDispatchModal(prev => ({ ...prev, plannedAt: e.target.value }))}
                      />
                    )}
                  </div>
                  <div style={s.formGroup}>
                    <label style={s.formLabel}>分类</label>
                    <select style={s.fieldSelect} value={dispatchModal.category}
                      onChange={e => setDispatchModal(prev => ({ ...prev, category: e.target.value }))}
                    >
                      <option value="bmc">BMC</option>
                      <option value="bios">BIOS</option>
                      <option value="os">OS</option>
                    </select>
                  </div>
                  <div style={s.formGroup}>
                    <label style={s.formLabel}>项目标签</label>
                    <select style={s.fieldSelect} value={dispatchModal.projectTag}
                      onChange={e => setDispatchModal(prev => ({ ...prev, projectTag: e.target.value }))}
                    >
                      <option value="universal">Universal</option>
                      <option value="specific">Specific</option>
                    </select>
                  </div>
                </div>

                {/* Case Selection */}
                <div style={s.formGroup}>
                  <label style={s.formLabel}>
                    选择用例
                    <span style={s.selectedCount}>{dispatchModal.selectedCases.length} 已选</span>
                  </label>
                  <div style={s.caseSearchBox}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--text-muted)', flexShrink: 0 }}><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
                    <input style={{ ...s.fieldInput, border: 'none', padding: '8px 0', background: 'transparent' }}
                      type="text" placeholder="搜索用例..."
                      value={caseSearchQuery} onChange={e => setCaseSearchQuery(e.target.value)}
                    />
                  </div>
                  <div style={s.caseListBox}>
                    {autoCases.length === 0 ? (
                      <div style={s.emptySmall}>暂无可用用例</div>
                    ) : (
                      autoCases
                        .filter(c => !caseSearchQuery || c.auto_case_id.toLowerCase().includes(caseSearchQuery.toLowerCase()) || c.script_name?.toLowerCase().includes(caseSearchQuery.toLowerCase()))
                        .map(c => {
                          const selected = dispatchModal.selectedCases.includes(c.auto_case_id);
                          return (
                            <label key={c.auto_case_id} style={{ ...s.caseItem, ...(selected ? s.caseItemSelected : {}) }}>
                              <input type="checkbox" checked={selected} onChange={() => toggleCaseSelection(c.auto_case_id)} style={{ display: 'none' }} />
                              <span style={{ ...s.checkbox, ...(selected ? s.checkboxChecked : {}) }}>
                                {selected && <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>}
                              </span>
                              <span style={s.caseItemName}>{c.auto_case_id}</span>
                              <span style={s.caseItemScript}>{c.script_name || '-'}</span>
                              <span style={s.caseItemFw}>{c.framework}</span>
                            </label>
                          );
                        })
                    )}
                  </div>
                </div>

                {/* Case Configs */}
                {dispatchModal.selectedCases.length > 0 && (
                  <div style={s.formGroup}>
                    <label style={s.formLabel}>用例配置</label>
                    <div style={s.configList}>
                      {dispatchModal.selectedCases.map(id => (
                        <div key={id}>{renderCaseConfig(id)}</div>
                      ))}
                    </div>
                  </div>
                )}

                {dispatchModal.error && <div style={s.errorBanner}>{dispatchModal.error}</div>}

                <div style={s.modalActions}>
                  <button style={s.cancelBtn} onClick={closeDispatchModal}>取消</button>
                  <button style={s.submitBtn} onClick={handleDispatchSubmit}
                    disabled={dispatchModal.submitting}
                  >
                    {dispatchModal.submitting ? '下發中...' : '确认下发'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <style>{`
        @keyframes taskSpin { to { transform: rotate(360deg); } }
        @keyframes fadeInDown {
          from { opacity: 0; transform: translateX(-50%) translateY(-20px); }
          to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default TaskList;

/* ──────────────────────────────────────────────────────────────
   STYLES
   ────────────────────────────────────────────────────────────── */
const s = {
  wrapper: {
    padding: '20px 24px 32px',
    maxWidth: '1200px',
    margin: '0 auto',
    width: '100%',
    boxSizing: 'border-box' as const,
  } as const,

  // Header
  header: {
    marginBottom: '20px',
  } as const,
  headerTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  } as const,
  filterWrapper: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '20px',
    padding: '12px 0',
  } as const,
  title: {
    fontSize: '20px',
    fontWeight: 700,
    color: 'var(--text-primary)',
    margin: 0,
    letterSpacing: '-0.3px',
  } as const,
  subtitle: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    margin: 0,
    whiteSpace: 'nowrap' as const,
  } as const,
  headerActions: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
  } as const,
  refreshBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '36px',
    height: '36px',
    fontSize: '16px',
    color: 'var(--text-secondary)',
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.15s',
  } as const,
  dispatchBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 18px',
    fontSize: '13px',
    fontWeight: 600,
    color: '#fff',
    background: 'linear-gradient(135deg, #06b6d4, #0891b2)',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.15s',
    boxShadow: '0 2px 6px rgba(6,182,212,0.25)',
  } as const,

  // Banners
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 12px',
    marginBottom: '10px',
    background: 'rgba(239,68,68,0.1)',
    border: '1px solid rgba(239,68,68,0.2)',
    borderRadius: '6px',
    color: '#f87171',
    fontSize: '12px',
  } as const,
  successBanner: {
    position: 'fixed',
    top: '20px',
    left: '50%',
    transform: 'translateX(-50%)',
    zIndex: 9999,
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 20px',
    background: '#16a34a',
    borderRadius: '8px',
    color: '#fff',
    fontSize: '14px',
    fontWeight: 500,
    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
    animation: 'fadeInDown 0.3s ease',
  } as const,

  // Filter bar
  filterBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    marginBottom: '14px',
  } as const,
  filterTabs: {
    display: 'flex',
    gap: '4px',
    background: 'var(--bg-secondary)',
    padding: '4px',
    borderRadius: '10px',
    border: '1px solid var(--border-default)',
  } as const,
  filterTab: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 14px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    background: 'transparent',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.15s',
    whiteSpace: 'nowrap' as const,
  } as const,
  filterTabActive: {
    color: 'var(--text-primary)',
    background: 'var(--bg-primary)',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    fontWeight: 600,
  } as const,
  filterCount: {
    fontSize: '11px',
    fontWeight: 600,
    padding: '2px 7px',
    borderRadius: '99px',
    color: 'var(--text-muted)',
    background: 'var(--bg-tertiary)',
  } as const,
  filterCountActive: {
    color: 'var(--accent-cyan)',
    background: 'rgba(57,208,214,0.1)',
  } as const,
  searchBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '0 12px',
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: '8px',
    minWidth: '180px',
  } as const,
  searchInput: {
    width: '100%',
    padding: '8px 0',
    fontSize: '13px',
    color: 'var(--text-primary)',
    background: 'transparent',
    border: 'none',
    outline: 'none',
  } as const,

  // Task list
  list: {
    minHeight: '200px',
  } as const,
  taskList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '10px',
  } as const,
  taskCard: {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderLeft: '4px solid var(--border-default)',
    borderRadius: '12px',
    overflow: 'hidden',
    transition: 'all 0.15s',
  } as const,
  taskCardMain: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '16px',
    padding: '14px 18px',
  } as const,
  taskCardLeft: {
    flex: 1,
    minWidth: 0,
  } as const,
  taskCardRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '6px',
  } as const,
  taskId: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '14px',
    fontWeight: 700,
    color: 'var(--accent-cyan)',
    cursor: 'pointer',
    transition: 'color 0.1s',
  } as const,
  sourceTag: {
    fontSize: '11px',
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: '99px',
    color: '#a78bfa',
    background: 'rgba(167,139,250,0.10)',
    border: '1px solid rgba(167,139,250,0.18)',
  } as const,
  statusDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    flexShrink: 0,
  } as const,
  statusLabel: {
    fontSize: '13px',
    fontWeight: 600,
  } as const,
  taskMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flexWrap: 'wrap' as const,
  } as const,
  metaItem: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  metaDot: {
    color: 'var(--border-default)',
    fontSize: '12px',
  } as const,
  taskCardRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flexShrink: 0,
  } as const,
  taskTime: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    fontFamily: "'JetBrains Mono', monospace",
    whiteSpace: 'nowrap' as const,
  } as const,
  taskActions: {
    display: 'flex',
    gap: '6px',
  } as const,
  actionBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '32px',
    height: '32px',
    color: 'var(--text-muted)',
    background: 'transparent',
    border: '1px solid var(--border-muted)',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.15s',
  } as const,
  actionDangerBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '32px',
    height: '32px',
    color: 'var(--text-muted)',
    background: 'transparent',
    border: '1px solid var(--border-muted)',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.15s',
  } as const,
  taskCardBottom: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 18px',
    borderTop: '1px solid var(--border-muted)',
  } as const,
  expandBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 10px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    background: 'transparent',
    border: '1px solid var(--border-muted)',
    borderRadius: '6px',
    cursor: 'pointer',
  } as const,
  expandCount: {
    fontSize: '12px',
    color: 'var(--accent-cyan)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  detailBtn: {
    padding: '4px 12px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--accent-cyan)',
    background: 'transparent',
    border: '1px solid rgba(57,208,214,0.2)',
    borderRadius: '6px',
    cursor: 'pointer',
  } as const,
  expandedSection: {
    padding: '16px 18px',
    borderTop: '1px solid var(--border-muted)',
    background: 'var(--bg-primary)',
  } as const,

  // Loading & Empty
  loadingState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    gap: '12px',
    padding: '60px',
    color: 'var(--text-secondary)',
  } as const,
  emptyState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    gap: '8px',
    padding: '60px',
    color: 'var(--text-muted)',
    fontSize: '14px',
  } as const,
  emptyIcon: {
    fontSize: '40px',
    opacity: 0.3,
  } as const,
  emptySmall: {
    padding: '12px',
    textAlign: 'center' as const,
    color: 'var(--text-muted)',
    fontSize: '12px',
  } as const,
  spinner: {
    width: '24px',
    height: '24px',
    border: '3px solid var(--border-default)',
    borderTopColor: 'var(--accent-cyan)',
    borderRadius: '50%',
    animation: 'taskSpin 0.8s linear infinite',
  } as const,

  // Modal common
  overlay: {
    position: 'fixed' as const,
    inset: 0,
    background: 'rgba(0,0,0,0.6)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'flex-start',
    zIndex: 1000,
    backdropFilter: 'blur(4px)',
    paddingTop: '60px',
  } as const,
  modal: {
    background: 'var(--bg-secondary)',
    borderRadius: '14px',
    border: '1px solid var(--border-default)',
    width: '100%',
    maxWidth: '800px',
    maxHeight: 'calc(100vh - 120px)',
    overflow: 'auto',
    boxShadow: '0 25px 60px rgba(0,0,0,0.3)',
    marginBottom: '60px',
  } as const,
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '14px 20px 12px',
    borderBottom: '1px solid var(--border-default)',
  } as const,
  modalTitle: {
    fontSize: '16px',
    fontWeight: 700,
    color: 'var(--text-primary)',
    margin: 0,
  } as const,
  closeBtn: {
    background: 'transparent',
    border: 'none',
    fontSize: '22px',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    lineHeight: 1,
    padding: 0,
    width: '28px',
    height: '28px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '6px',
  } as const,
  modalLoading: {
    display: 'flex',
    justifyContent: 'center',
    padding: '50px',
  } as const,
  modalBody: {
    padding: '20px',
  } as const,
  modalActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '8px',
    marginTop: '16px',
  } as const,

  // Detail modal styles
  detailGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '12px',
    marginBottom: '18px',
  } as const,
  detailItem: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '3px',
  } as const,
  detailLabel: {
    fontSize: '10px',
    color: 'var(--text-muted)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.4px',
    fontWeight: 600,
  } as const,
  detailValue: {
    fontSize: '13px',
    color: 'var(--text-primary)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  statusRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '10px',
    marginBottom: '18px',
  } as const,
  statusPill: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    gap: '4px',
    padding: '10px 8px',
    borderRadius: '10px',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-muted)',
  } as const,
  statusPillLabel: {
    fontSize: '10px',
    fontWeight: 600,
    color: 'var(--text-muted)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.4px',
  } as const,
  statusPillValue: {
    fontSize: '12px',
    fontWeight: 700,
    padding: '3px 10px',
    borderRadius: '99px',
  } as const,
  section: {
    marginBottom: '18px',
  } as const,
  sectionTitle: {
    fontSize: '11px',
    fontWeight: 700,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.4px',
    margin: '0 0 10px',
  } as const,
  timeGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '10px',
  } as const,
  timeLabel: {
    display: 'block',
    fontSize: '11px',
    color: 'var(--text-muted)',
    marginBottom: '2px',
  } as const,
  timeValue: {
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--text-secondary)',
  } as const,
  configDisplay: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '6px',
    padding: '12px',
    background: 'var(--bg-primary)',
    borderRadius: '8px',
    border: '1px solid var(--border-muted)',
  } as const,
  configRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    fontSize: '12px',
    color: 'var(--text-secondary)',
  } as const,
  attachList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '6px',
  } as const,
  attachItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '10px',
    padding: '8px 12px',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-muted)',
    borderRadius: '7px',
    fontSize: '12px',
    color: 'var(--text-primary)',
  } as const,
  ghostBtn: {
    padding: '7px 16px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--accent-cyan)',
    background: 'rgba(57,208,214,0.08)',
    border: '1px solid rgba(57,208,214,0.2)',
    borderRadius: '7px',
    cursor: 'pointer',
  } as const,
  errorBlock: {
    margin: '12px 0 0',
    padding: '12px',
    fontSize: '12px',
    fontFamily: "'JetBrains Mono', monospace",
    color: '#f87171',
    background: 'rgba(239,68,68,0.08)',
    borderRadius: '8px',
    overflow: 'auto',
    maxHeight: '150px',
    whiteSpace: 'pre-wrap' as const,
    lineHeight: 1.5,
  } as const,

  // Dispatch modal
  dispatchModal: {
    background: 'var(--bg-secondary)',
    borderRadius: '14px',
    border: '1px solid var(--border-default)',
    width: '92%',
    maxWidth: '900px',
    maxHeight: '88vh',
    overflow: 'auto',
    boxShadow: '0 25px 60px rgba(0,0,0,0.3)',
  } as const,
  dispatchBody: {
    padding: '18px',
  } as const,
  formGroup: {
    marginBottom: '16px',
  } as const,
  formLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    marginBottom: '6px',
  } as const,
  formRow3: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: '16px',
  } as const,
  toggleGroup: {
    display: 'flex',
    gap: '3px',
    padding: '3px',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: '7px',
  } as const,
  toggleBtn: {
    flex: 1,
    padding: '6px 14px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    background: 'transparent',
    border: 'none',
    borderRadius: '5px',
    cursor: 'pointer',
    transition: 'all 0.15s',
  } as const,
  toggleBtnActive: {
    color: '#fff',
    background: 'linear-gradient(135deg, #06b6d4, #0891b2)',
    boxShadow: '0 1px 3px rgba(6,182,212,0.3)',
  } as const,
  fieldInput: {
    width: '100%',
    padding: '7px 10px',
    fontSize: '12px',
    color: 'var(--text-primary)',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: '7px',
    outline: 'none',
    boxSizing: 'border-box' as const,
  } as const,
  fieldSelect: {
    width: '100%',
    padding: '7px 10px',
    fontSize: '12px',
    color: 'var(--text-primary)',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: '7px',
    outline: 'none',
    cursor: 'pointer',
    boxSizing: 'border-box' as const,
  } as const,
  retryInput: {
    width: '70px',
    padding: '6px 8px',
    fontSize: '12px',
    color: 'var(--text-primary)',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: '7px',
    outline: 'none',
    marginTop: '4px',
  } as const,

  // Execution config
  execConfigRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '14px',
    padding: '14px',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: '8px',
  } as const,
  execConfigItem: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
  } as const,
  execConfigItemLabel: {
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
  } as const,

  // Attachments
  attachArea: {
    padding: '12px',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: '8px',
  } as const,
  uploadBtn: {
    display: 'inline-flex',
    padding: '6px 14px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--accent-cyan)',
    background: 'rgba(57,208,214,0.08)',
    border: '1px dashed rgba(57,208,214,0.35)',
    borderRadius: '7px',
    cursor: 'pointer',
  } as const,
  removeBtn: {
    flexShrink: 0,
    width: '22px',
    height: '22px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '13px',
    color: 'var(--text-muted)',
    background: 'transparent',
    border: 'none',
    borderRadius: '5px',
    cursor: 'pointer',
  } as const,

  // Case selection
  selectedCount: {
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--accent-cyan)',
    background: 'rgba(57,208,214,0.1)',
    padding: '2px 8px',
    borderRadius: '99px',
  } as const,
  caseSearchBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '0 10px',
    marginBottom: '6px',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: '7px',
  } as const,
  caseListBox: {
    maxHeight: '220px',
    overflowY: 'auto',
    border: '1px solid var(--border-default)',
    borderRadius: '8px',
    background: 'var(--bg-primary)',
  } as const,
  caseItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '9px 14px',
    borderBottom: '1px solid var(--border-muted)',
    cursor: 'pointer',
    fontSize: '12px',
    color: 'var(--text-primary)',
    transition: 'background 0.1s',
  } as const,
  caseItemSelected: {
    background: 'rgba(57,208,214,0.06)',
  } as const,
  checkbox: {
    width: '16px',
    height: '16px',
    borderRadius: '4px',
    border: '2px solid var(--border-default)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    transition: 'all 0.15s',
  } as const,
  checkboxChecked: {
    background: 'linear-gradient(135deg, #06b6d4, #0891b2)',
    borderColor: '#06b6d4',
  } as const,
  caseItemName: {
    flex: 1,
    fontFamily: "'JetBrains Mono', monospace",
    fontWeight: 600,
    fontSize: '12px',
  } as const,
  caseItemScript: {
    minWidth: '100px',
    fontSize: '11px',
    color: 'var(--text-secondary)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  caseItemFw: {
    fontSize: '10px',
    fontWeight: 600,
    color: '#a78bfa',
    background: 'rgba(167,139,250,0.10)',
    padding: '2px 6px',
    borderRadius: '3px',
  } as const,

  // Case config
  configList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '10px',
  } as const,
  configCard: {
    border: '1px solid var(--border-default)',
    borderRadius: '10px',
    background: 'var(--bg-primary)',
    padding: '14px',
  } as const,
  configCardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '12px',
    paddingBottom: '10px',
    borderBottom: '1px solid var(--border-muted)',
  } as const,
  configCardTitle: {
    fontSize: '13px',
    fontWeight: 700,
    color: 'var(--text-primary)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  configCardSub: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
    marginTop: '2px',
  } as const,
  configCardBadge: {
    fontSize: '10px',
    fontWeight: 600,
    color: 'var(--accent-cyan)',
    background: 'rgba(57,208,214,0.1)',
    border: '1px solid rgba(57,208,214,0.2)',
    borderRadius: '99px',
    padding: '2px 7px',
    flexShrink: 0,
  } as const,
  configEmpty: {
    padding: '6px 0 2px',
    color: 'var(--text-muted)',
    fontSize: '12px',
  } as const,
  configFields: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
    gap: '10px',
  } as const,
  configField: {
    border: '1px solid var(--border-muted)',
    borderRadius: '8px',
    padding: '10px',
  } as const,
  configFieldLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '5px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: '3px',
  } as const,
  configFieldType: {
    fontSize: '10px',
    fontWeight: 600,
    color: '#a78bfa',
    background: 'rgba(167,139,250,0.1)',
    padding: '1px 5px',
    borderRadius: '3px',
    marginLeft: 'auto',
  } as const,
  configFieldDesc: {
    fontSize: '11px',
    color: 'var(--text-muted)',
    marginBottom: '6px',
    lineHeight: 1.4,
  } as const,
  toggleLabel: {
    display: 'inline-flex',
    alignItems: 'center',
    cursor: 'pointer',
    marginTop: '3px',
  } as const,
  toggleSwitch: {
    width: '32px',
    height: '18px',
    borderRadius: '99px',
    background: 'var(--border-default)',
    position: 'relative' as const,
    display: 'inline-block',
  } as const,
  fileBtn: {
    display: 'inline-flex',
    padding: '5px 12px',
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--accent-cyan)',
    background: 'rgba(57,208,214,0.06)',
    border: '1px dashed rgba(57,208,214,0.3)',
    borderRadius: '6px',
    cursor: 'pointer',
    marginTop: '3px',
  } as const,
  fileChip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '5px 10px',
    fontSize: '11px',
    color: 'var(--text-primary)',
    background: 'rgba(57,208,214,0.06)',
    border: '1px solid rgba(57,208,214,0.2)',
    borderRadius: '6px',
    marginTop: '3px',
  } as const,
  fileChipRemove: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '16px',
    height: '16px',
    fontSize: '11px',
    color: 'var(--text-muted)',
    background: 'transparent',
    border: 'none',
    borderRadius: '50%',
    cursor: 'pointer',
    padding: 0,
  } as const,

  // Cancel / Submit
  cancelBtn: {
    padding: '7px 18px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
    borderRadius: '7px',
    cursor: 'pointer',
  } as const,
  submitBtn: {
    padding: '7px 22px',
    fontSize: '12px',
    fontWeight: 600,
    color: '#fff',
    background: 'linear-gradient(135deg, #06b6d4, #0891b2)',
    border: 'none',
    borderRadius: '7px',
    cursor: 'pointer',
    transition: 'all 0.15s',
  } as const,

  // Case cards in expanded view
  caseGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
    gap: '12px',
  } as const,
  caseCard: {
    padding: '14px',
    borderRadius: '10px',
    border: '1px solid var(--border-muted)',
    background: 'var(--bg-secondary)',
  } as const,
  caseCardTop: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: '10px',
    marginBottom: '12px',
  } as const,
  caseCardTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    lineHeight: 1.4,
    wordBreak: 'break-word' as const,
  } as const,
  caseBadge: {
    flexShrink: 0,
    padding: '3px 8px',
    borderRadius: '99px',
    fontSize: '11px',
    fontWeight: 600,
  } as const,
  caseMetrics: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '8px',
  } as const,
  caseMetric: {
    padding: '8px 6px',
    borderRadius: '6px',
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid var(--border-muted)',
    textAlign: 'center' as const,
  } as const,
  caseMetricLabel: {
    display: 'block',
    fontSize: '11px',
    color: 'var(--text-muted)',
    marginBottom: '2px',
  } as const,
  caseMetricValue: {
    fontSize: '14px',
    fontWeight: 700,
    color: 'var(--text-primary)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  caseError: {
    marginTop: '10px',
    fontSize: '12px',
    color: '#f87171',
    lineHeight: 1.5,
  } as const,

  // Case detail expanded
  caseInfoRow: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '10px',
    marginTop: '10px',
    alignItems: 'center',
  } as const,
  caseInfoBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '2px 8px',
    borderRadius: '99px',
    fontSize: '11px',
    fontWeight: 600,
  } as const,
  caseDetailWrap: {
    marginTop: '14px',
    paddingTop: '12px',
    borderTop: '1px dashed var(--border-muted)',
  } as const,
  caseDetailToggle: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 0,
    background: 'transparent',
    border: 'none',
    cursor: 'pointer',
  } as const,
  caseDetailGrid2: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
    gap: '10px',
    marginBottom: '12px',
  } as const,
  caseDetailBlock2: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '2px',
    padding: '10px 12px',
    borderRadius: '6px',
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid var(--border-muted)',
  } as const,
  caseDetailBlockLabel2: {
    fontSize: '11px',
    color: 'var(--text-muted)',
  } as const,
  caseDetailBlockVal2: {
    fontSize: '12px',
    color: 'var(--text-primary)',
  } as const,
  caseMetaRow: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '10px',
    marginBottom: '10px',
    alignItems: 'center',
  } as const,
  assertionItem: {
    padding: '12px 14px',
    borderRadius: '8px',
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid var(--border-muted)',
  } as const,
  codeBlock: {
    margin: '10px 0 0',
    padding: '12px',
    borderRadius: '8px',
    background: 'rgba(15,23,42,0.55)',
    color: '#dbeafe',
    fontSize: '12px',
    lineHeight: 1.5,
    fontFamily: "'JetBrains Mono', monospace",
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
  } as const,
};
