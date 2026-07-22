import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Brain, AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import { queryKeys } from '../providers/queryKeys';
import { getErrorMessage } from '../utils/errors';
import type { WorkItem, TestCaseResponse, RequirementResponse, UserResponse, PendingTaskAnalysisResult } from '../types';
import { WorkflowActionToolbar } from './workflow';
import {
  getStateLabel,
  getWorkflowStateStyle,
  type WorkflowTypeCode,
} from '../constants/workflowLabels';
import PageToolbar from './ui/PageToolbar';
import PlanTaskTable from './PlanTaskTable';
import ResultBackfillModal from './ResultBackfillModal';
import SingleDispatchModal from './SingleDispatchModal';
import ReassignModal from './ReassignModal';
import ExecResultModal, { type ExecResultData } from './ExecResultModal';
import { transformApiItem, myTasksStyles, type PlanTask, type PlanTaskResult } from './myTasksTypes';
import CreateTestCaseForm from './CreateTestCaseForm';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';


interface MyTasksPageProps {
  userId: string;
}

type TaskCategory = 'review' | 'requirement' | 'testcase_dev';
type MyTasksTab = 'plan' | TaskCategory;
type RequirementScope = 'mine' | 'all';

interface TaskCategoryGroup {
  key: TaskCategory;
  label: string;
  color: string;
  items: WorkItem[];
}

const FONT_SCALE_STORAGE_KEY = 'my_tasks_font_scale';
const WORKFLOW_GROUP_PREVIEW_LIMIT = 8;
const PENDING_BOARD_TOP_LIMIT = 6;
type FontScaleKey = 'compact' | 'standard' | 'large';
const FONT_SCALE_OPTIONS: Array<{ key: FontScaleKey; label: string; value: number; title: string }> = [
  { key: 'compact', label: 'A-', value: 0.9, title: '缩小字体' },
  { key: 'standard', label: 'A', value: 1, title: '标准字体' },
  { key: 'large', label: 'A+', value: 1.14, title: '放大字体' },
];

type MyTasksPageStyle = React.CSSProperties & {
  '--my-tasks-font-scale': number;
  '--my-tasks-line-height': number;
};

type PendingPeriodKey = 'overdue' | 'today' | 'soon' | 'normal' | 'unset';
type PendingAiStatus = 'idle' | 'loading' | 'success' | 'error';

interface PendingBoardItem {
  id: string;
  kind: 'plan' | 'workflow';
  title: string;
  category: string;
  status: string;
  nextStep: string;
  period: PendingPeriodKey;
  periodLabel: string;
  periodDetail: string;
  dueTime?: number;
  updatedTime?: number;
}

function PendingAiAnalysisDialog({
  open,
  loading,
  result,
  error,
  onOpenChange,
  onRetry,
}: {
  open: boolean;
  loading: boolean;
  result: PendingTaskAnalysisResult | null;
  error: string | null;
  onOpenChange: (open: boolean) => void;
  onRetry: () => void;
}) {
  const score = result?.health_score ?? 0;
  const scoreTone = score >= 80 ? 'success' : score >= 60 ? 'warning' : 'danger';
  const status: PendingAiStatus = loading ? 'loading' : error ? 'error' : result ? 'success' : 'idle';
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="my-tasks-ai-dialog">
        <DialogHeader className="my-tasks-ai-dialog__header">
          <DialogTitle className="my-tasks-ai-dialog__title">
            <Brain size={19} aria-hidden="true" />
            待处理任务智能分析
          </DialogTitle>
          <span className={`my-tasks-ai-dialog__badge my-tasks-ai-dialog__badge--${status}`}>
            {status === 'loading' && <span className="my-tasks-ai-dialog__badge-spinner" aria-hidden="true" />}
            {status === 'success' && <CheckCircle2 size={14} aria-hidden="true" />}
            {status === 'error' && <AlertTriangle size={14} aria-hidden="true" />}
            {status === 'idle' ? '等待分析' : status === 'loading' ? '分析中' : status === 'success' ? '分析完成' : '分析失败'}
          </span>
        </DialogHeader>
        {loading ? (
          <div className="my-tasks-ai-state my-tasks-ai-state--loading" role="status" aria-live="polite">
            <div className="my-tasks-ai-loader" aria-hidden="true">
              <span className="my-tasks-ai-loader__ring" />
              <span className="my-tasks-ai-loader__ring my-tasks-ai-loader__ring--inner" />
              <Brain size={22} />
            </div>
            <div>
              <strong>正在分析待处理任务</strong>
              <span>识别任务分布、时间风险与优先处理项</span>
            </div>
            <span className="my-tasks-ai-progress" aria-hidden="true"><span /></span>
          </div>
        ) : error ? (
          <div className="my-tasks-ai-error" role="alert">
            <span className="my-tasks-ai-error__icon"><AlertTriangle size={24} aria-hidden="true" /></span>
            <div>
              <strong>分析未完成</strong>
              <p>{error}</p>
              <small>任务数据未发生变更，可以直接重新分析。</small>
            </div>
            <button type="button" className="btn btn--secondary btn--sm" onClick={onRetry}>
              <RefreshCw size={14} aria-hidden="true" />
              重新分析
            </button>
          </div>
        ) : result ? (
          <div className="my-tasks-ai-result">
            <div className="my-tasks-ai-success" role="status">
              <CheckCircle2 size={18} aria-hidden="true" />
              <div>
                <strong>分析完成</strong>
                <span>已生成健康评分、风险项和处理建议</span>
              </div>
              <button type="button" className="my-tasks-ai-success__action" onClick={onRetry}>
                <RefreshCw size={13} aria-hidden="true" />
                重新分析
              </button>
            </div>
            <div className={`my-tasks-ai-score my-tasks-ai-score--${scoreTone}`}>
              <div>
                <span>健康评分</span>
                <strong>{score}</strong>
              </div>
              <p>{result.summary}</p>
            </div>

            <div className="my-tasks-ai-grid">
              <section>
                <h4>异常与风险</h4>
                {result.anomalies.length > 0 ? result.anomalies.map((item, index) => (
                  <div key={`${item.title}-${index}`} className={`my-tasks-ai-card my-tasks-ai-card--${item.severity}`}>
                    <strong>{item.title}</strong>
                    <p>{item.detail}</p>
                    {item.related_ids.length > 0 && <small>{item.related_ids.join('、')}</small>}
                  </div>
                )) : <div className="my-tasks-ai-empty"><CheckCircle2 size={16} /> 暂无明显异常</div>}
              </section>

              <section>
                <h4>优先处理</h4>
                {result.priority_items.length > 0 ? result.priority_items.map(item => (
                  <div key={item.id} className="my-tasks-ai-card">
                    <span className="my-tasks-ai-priority">{item.priority}</span>
                    <strong>{item.title || item.id}</strong>
                    <p>{item.reason}</p>
                  </div>
                )) : <div className="my-tasks-ai-empty">暂无优先级建议</div>}
              </section>
            </div>

            {result.recommendations.length > 0 && (
              <section className="my-tasks-ai-recommendations">
                <h4>处理建议</h4>
                {result.recommendations.map((item, index) => <p key={index}>{item}</p>)}
              </section>
            )}
          </div>
        ) : (
          <div className="my-tasks-ai-state">
            <Brain size={28} />
            <span>点击分析按钮后生成当前待处理任务洞察</span>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

const getInitialFontScale = (): FontScaleKey => {
  if (typeof window === 'undefined') return 'standard';
  const saved = window.localStorage.getItem(FONT_SCALE_STORAGE_KEY);
  if (FONT_SCALE_OPTIONS.some(option => option.key === saved)) return saved as FontScaleKey;

  const parsed = Number(saved);
  if (!Number.isFinite(parsed)) return 'standard';
  if (parsed < 0.97) return 'compact';
  if (parsed > 1.07) return 'large';
  return 'standard';
};

const scaledFont = (px: number) => `calc(${px}px * var(--my-tasks-font-scale))`;
const DAY_MS = 24 * 60 * 60 * 1000;
const HOUR_MS = 60 * 60 * 1000;
const TERMINAL_WORKFLOW_STATES = new Set(['RELEASED', 'DONE', 'CLOSED', 'ARCHIVED']);
const PENDING_PERIOD_RANK: Record<PendingPeriodKey, number> = {
  overdue: 0,
  today: 1,
  soon: 2,
  unset: 3,
  normal: 4,
};
const PENDING_BOARD_BUCKETS: Array<{ key: PendingPeriodKey; label: string; tone: 'danger' | 'warning' | 'success' | 'default' }> = [
  { key: 'overdue', label: '超期/停留较久', tone: 'danger' },
  { key: 'today', label: '24小时内', tone: 'warning' },
  { key: 'soon', label: '3天内/需关注', tone: 'warning' },
  { key: 'normal', label: '计划内', tone: 'success' },
  { key: 'unset', label: '无时间', tone: 'default' },
];

const isActiveWorkflowItem = (item: WorkItem) =>
  Boolean(item.current_state) && !TERMINAL_WORKFLOW_STATES.has(item.current_state);

const isReviewWorkItem = (item: WorkItem) => item.current_state === 'PENDING_REVIEW';

const isRequirementTodo = (item: WorkItem) =>
  item.type_code === 'REQUIREMENT' && !isReviewWorkItem(item);

const isTestCaseDevTodo = (item: WorkItem) =>
  item.type_code === 'TEST_CASE' && !isReviewWorkItem(item);

const formatShortDate = (value?: string) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
};

const parsePlanBoundary = (value?: string, endOfDay = false) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  if (endOfDay && value.length <= 10) {
    date.setHours(23, 59, 59, 999);
  }
  return date;
};

const formatDistanceText = (diffMs: number) => {
  const absMs = Math.abs(diffMs);
  if (absMs < HOUR_MS) return '不足 1 小时';
  if (absMs < DAY_MS) return `${Math.ceil(absMs / HOUR_MS)} 小时`;
  return `${Math.ceil(absMs / DAY_MS)} 天`;
};

const getPlanTimeMeta = (start?: string, end?: string) => {
  const target = parsePlanBoundary(end || start, Boolean(end));
  const rangeText = start || end
    ? `${formatShortDate(start) || '?'} ~ ${formatShortDate(end) || '?'}`
    : '未设置';

  if (!target) {
    return {
      label: '未设置计划',
      detail: '建议补充计划时间',
      rangeText,
      color: 'var(--text-tertiary)',
      bg: 'var(--surface-tertiary)',
    };
  }

  const diff = target.getTime() - Date.now();
  const days = Math.ceil(Math.abs(diff) / DAY_MS);
  if (diff < 0) {
    return {
      label: '已超期',
      detail: days <= 1 ? '超期不足 1 天' : `超期 ${days} 天`,
      rangeText,
      color: 'var(--status-error)',
      bg: 'var(--status-error-bg)',
    };
  }
  if (days <= 1) {
    return {
      label: '今日到期',
      detail: '请优先处理',
      rangeText,
      color: 'var(--status-warning)',
      bg: 'var(--status-warning-bg)',
    };
  }
  if (days <= 3) {
    return {
      label: `剩余 ${days} 天`,
      detail: '即将到期',
      rangeText,
      color: 'var(--status-warning)',
      bg: 'var(--status-warning-bg)',
    };
  }
  return {
    label: `剩余 ${days} 天`,
    detail: '计划内',
    rangeText,
    color: 'var(--status-success)',
    bg: 'var(--status-success-bg)',
  };
};

const MyTasksPage: React.FC<MyTasksPageProps> = ({ userId }) => {
  const queryClient = useQueryClient();
  const [fontScale, setFontScale] = useState(getInitialFontScale);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [itemDetail, setItemDetail] = useState<RequirementResponse | TestCaseResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [mutationError, setMutationError] = useState<string | null>(null);

  // Modal state: which task is being edited for result backfill
  const [resultModalTask, setResultModalTask] = useState<PlanTask | null>(null);

  // Single dispatch modal state
  const [dispatchModal, setDispatchModal] = useState<{
    open: boolean; itemId: string; caseId: string; caseTitle: string; dispatchConfig?: PlanTask['dispatchConfig'];
  }>({ open: false, itemId: '', caseId: '', caseTitle: '' });

  // ── 改派弹窗 ──
  const [reassignTask, setReassignTask] = useState<PlanTask | null>(null);
  const [reassignUserId, setReassignUserId] = useState('');
  const [users, setUsers] = useState<Array<{ user_id: string; username: string }>>([]);
  const [usersLoading, setUsersLoading] = useState(false);

  // Edit test case modal state (for testcase_dev items in DEVELOPING state)
  const [editingTestCase, setEditingTestCase] = useState<TestCaseResponse | null>(null);

  // Requirement test cases (shown in expanded detail)
  const [reqTestCases, setReqTestCases] = useState<TestCaseResponse[]>([]);
  const [loadingReqTestCases, setLoadingReqTestCases] = useState(false);
  const [showCreateReqTestCase, setShowCreateReqTestCase] = useState(false);
  const [creatingReqTestCaseReqId, setCreatingReqTestCaseReqId] = useState<string | null>(null);
  const [expandedWorkflowGroups, setExpandedWorkflowGroups] = useState<Set<TaskCategory>>(() => new Set());
  const [pendingBoardOpen, setPendingBoardOpen] = useState(false);
  const [pendingAiOpen, setPendingAiOpen] = useState(false);
  const [pendingAiLoading, setPendingAiLoading] = useState(false);
  const [pendingAiResult, setPendingAiResult] = useState<PendingTaskAnalysisResult | null>(null);
  const [pendingAiError, setPendingAiError] = useState<string | null>(null);
  const [requirementScope, setRequirementScope] = useState<RequirementScope>('all');

  // ── React Query: Work items ──

  const {
    data: workItems = [],
    isLoading: workItemsLoading,
    error: workItemsError,
  } = useQuery({
    queryKey: queryKeys.workItems.my(userId),
    queryFn: async () => (await api.listMyWorkItems(userId)).data || [],
    enabled: !!userId,
  });

  // ── React Query: Plan items ──

  const {
    data: planTasks = [],
    isLoading: planItemsLoading,
    error: planItemsError,
  } = useQuery({
    queryKey: queryKeys.planItems.my(userId),
    queryFn: async () => (await api.listMyPlanItems(userId)).data?.map(transformApiItem) || [],
    enabled: !!userId,
  });

  // ── 按三种类型归类工作流事项 ──

  const getWorkflowSortRank = useCallback((item: WorkItem) => {
    if (item.current_state === 'PENDING_REVIEW') return 0;
    if (item.type_code === 'REQUIREMENT' && item.current_state === 'DEVELOPING') return 1;
    if (item.type_code === 'TEST_CASE' && item.current_state === 'DEVELOPING') return 2;
    if (item.type_code === 'TEST_CASE' && item.current_state === 'ASSIGNED') return 3;
    return 4;
  }, []);

  const sortWorkflowItems = useCallback((items: WorkItem[]) =>
    [...items].sort((a, b) => {
      const rankDiff = getWorkflowSortRank(a) - getWorkflowSortRank(b);
      if (rankDiff !== 0) return rankDiff;
      return new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime();
    }), [getWorkflowSortRank]);

  const getWorkflowGroupSummary = (items: WorkItem[]) => {
    const stateCounts = items.reduce<Record<string, number>>((acc, item) => {
      acc[item.current_state] = (acc[item.current_state] || 0) + 1;
      return acc;
    }, {});
    return Object.entries(stateCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3)
      .map(([state, count]) => `${getStateLabel(state, state === 'PENDING_REVIEW' ? 'REQUIREMENT' : 'TEST_CASE')} ${count}`)
      .join(' / ');
  };

  const categories = useMemo<TaskCategoryGroup[]>(() => {
    // (1) 审核相关 — 待审核状态的事项
    const reviewItems = workItems.filter(isReviewWorkItem);
    // (2) 测试需求管理 — REQUIREMENT 中非审核中的
    const allReqItems = workItems.filter(isRequirementTodo);
    const reqItems = requirementScope === 'mine'
      ? allReqItems.filter(it => it.creator_id === userId)
      : allReqItems;
    // (3) 测试用例开发 — TEST_CASE 中非审核中的
    const tcItems = workItems.filter(isTestCaseDevTodo);

    const result: TaskCategoryGroup[] = [];

    if (reviewItems.length > 0) {
      result.push({
        key: 'review', label: '审核相关', color: '#f0883e',
        items: sortWorkflowItems(reviewItems),
      });
    }
    if (reqItems.length > 0) {
      result.push({
        key: 'requirement', label: '测试用例编写需求待办', color: '#58a6ff',
        items: sortWorkflowItems(reqItems),
      });
    }
    if (tcItems.length > 0) {
      result.push({
        key: 'testcase_dev', label: '用例开发', color: '#a371f7',
        items: sortWorkflowItems(tcItems),
      });
    }
    return result;
  }, [requirementScope, sortWorkflowItems, userId, workItems]);

  const requirementScopeStats = useMemo(() => {
    const requirementItems = workItems.filter(isRequirementTodo);
    const all = requirementItems.length;
    const mine = requirementItems.filter(it => it.creator_id === userId).length;
    return { all, mine };
  }, [userId, workItems]);

  const categoryCounts = useMemo<Record<TaskCategory, number>>(() => ({
    review: workItems.filter(isReviewWorkItem).length,
    requirement: requirementScopeStats[requirementScope],
    testcase_dev: workItems.filter(isTestCaseDevTodo).length,
  }), [requirementScope, requirementScopeStats, workItems]);

  // ── Refresh all ──

  const handleRefreshAll = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: queryKeys.workItems.my(userId) });
    queryClient.invalidateQueries({ queryKey: queryKeys.planItems.my(userId) });
  }, [queryClient, userId]);

  // ── Workflow item handlers ──

  const loadItemDetail = async (item: WorkItem) => {
    setLoadingDetail(true);
    setItemDetail(null);
    setReqTestCases([]);
    try {
      if (item.type_code === 'REQUIREMENT' && item.req_id) {
        const res = await api.getRequirement(item.req_id);
        setItemDetail(res.data);
        // 同时加载该需求下的测试用例
        setLoadingReqTestCases(true);
        try {
          const tcRes = await api.listTestCases({ ref_req_id: item.req_id, limit: 50 });
          setReqTestCases(tcRes.data || []);
        } catch { /* ignore */ }
        setLoadingReqTestCases(false);
      } else if (item.type_code === 'TEST_CASE') {
        if (item.case_id) {
          const res = await api.getTestCase(item.case_id);
          setItemDetail(res.data);
        }
      }
    } catch { /* ignore */ } finally { setLoadingDetail(false); }
  };

  const handleToggleExpand = async (itemId: string) => {
    if (expandedId === itemId) { setExpandedId(null); setItemDetail(null); return; }
    setExpandedId(itemId);
    const item = workItems.find(i => i.item_id === itemId);
    if (item) await loadItemDetail(item);
  };

  const handleTaskWorkflowSuccess = async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.workItems.my(userId) });
  };

  const getTypeCode = (type: string): WorkflowTypeCode =>
    type === 'TEST_CASE' ? 'TEST_CASE' : 'REQUIREMENT';

  const getWorkflowTypeLabel = (item: WorkItem) => {
    if (item.current_state === 'PENDING_REVIEW') return '评审';
    if (item.type_code === 'TEST_CASE') return '测试用例';
    return '需求';
  };

  const getWorkflowNextStep = (item: WorkItem) => {
    if (item.current_state === 'PENDING_REVIEW') return '需要你审核';
    if (item.type_code === 'REQUIREMENT' && item.current_state === 'DEVELOPING') return '补充或创建测试用例';
    if (item.type_code === 'TEST_CASE' && item.current_state === 'ASSIGNED') return '开始编写用例';
    if (item.type_code === 'TEST_CASE' && item.current_state === 'DEVELOPING') return '继续编辑用例';
    return '查看详情与流程';
  };

  const getWorkflowPrimaryAction = (item: WorkItem) => {
    if (item.current_state === 'PENDING_REVIEW') return '进入评审';
    if (item.type_code === 'REQUIREMENT' && item.current_state === 'DEVELOPING') return '编写用例';
    if (item.type_code === 'TEST_CASE' && (item.current_state === 'ASSIGNED' || item.current_state === 'DEVELOPING')) {
      return '编辑用例';
    }
    return '查看详情';
  };

  const getPlanNextStep = (task: PlanTask) => {
    if (task.status === 'done') return '查看测试结果';
    if (task.status === 'running') return '跟进自动化执行结果';
    if (task.status === 'fail') return '确认失败原因并重试';
    return task.type === 'auto' ? '下发自动化执行' : '回填测试结果';
  };

  const getPlanStatusLabel = (task: PlanTask) => {
    if (task.status === 'done') return '已完成';
    if (task.status === 'running') return '执行中';
    if (task.status === 'fail') return '失败';
    return task.type === 'auto' ? '待下发' : '待回填';
  };

  const getPeriodMeta = (target?: Date | null, fallbackUpdatedAt?: string): Pick<PendingBoardItem, 'period' | 'periodLabel' | 'periodDetail' | 'dueTime' | 'updatedTime'> => {
    const nowMs = new Date().getTime();
    const updatedDate = fallbackUpdatedAt ? new Date(fallbackUpdatedAt) : null;
    const updatedTime = updatedDate && !Number.isNaN(updatedDate.getTime()) ? updatedDate.getTime() : undefined;

    if (target && !Number.isNaN(target.getTime())) {
      const dueTime = target.getTime();
      const diff = dueTime - nowMs;
      if (diff < 0) {
        return {
          period: 'overdue',
          periodLabel: '已超期',
          periodDetail: `超期 ${formatDistanceText(diff)}`,
          dueTime,
          updatedTime,
        };
      }
      if (diff <= DAY_MS) {
        return {
          period: 'today',
          periodLabel: '24小时内',
          periodDetail: `剩余 ${formatDistanceText(diff)}`,
          dueTime,
          updatedTime,
        };
      }
      if (diff <= 3 * DAY_MS) {
        return {
          period: 'soon',
          periodLabel: '3天内',
          periodDetail: `剩余 ${formatDistanceText(diff)}`,
          dueTime,
          updatedTime,
        };
      }
      return {
        period: 'normal',
        periodLabel: '计划内',
        periodDetail: `剩余 ${formatDistanceText(diff)}`,
        dueTime,
        updatedTime,
      };
    }

    if (updatedTime) {
      const age = nowMs - updatedTime;
      if (age >= 3 * DAY_MS) {
        return {
          period: 'overdue',
          periodLabel: '停留较久',
          periodDetail: `已停留 ${formatDistanceText(age)}`,
          updatedTime,
        };
      }
      if (age >= DAY_MS) {
        return {
          period: 'soon',
          periodLabel: '需关注',
          periodDetail: `已停留 ${formatDistanceText(age)}`,
          updatedTime,
        };
      }
      return {
        period: 'normal',
        periodLabel: '新近更新',
        periodDetail: `更新 ${formatDistanceText(age)}内`,
        updatedTime,
      };
    }

    return {
      period: 'unset',
      periodLabel: '无时间',
      periodDetail: '未设置计划时间',
      updatedTime,
    };
  };

  const handleWorkflowPrimaryAction = async (item: WorkItem) => {
    if (item.type_code === 'TEST_CASE' && (item.current_state === 'ASSIGNED' || item.current_state === 'DEVELOPING')) {
      await handleEditTestCase(item);
      return;
    }
    if (expandedId !== item.item_id) {
      await handleToggleExpand(item.item_id);
    }
  };

  const renderPlanTimeCard = (start?: string, end?: string) => {
    const planMeta = getPlanTimeMeta(start, end);
    return (
      <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
        <div style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>计划时间</div>
        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 8, fontSize: scaledFont(12) }}>
          <span style={{
            padding: '2px 8px', borderRadius: 999, color: planMeta.color, background: planMeta.bg,
            fontWeight: 700,
          }}>
            {planMeta.label}
          </span>
          <span style={{ color: '#475569' }}>{planMeta.rangeText}</span>
        </div>
        <div style={{ marginTop: 4, fontSize: scaledFont(11), color: '#94a3b8' }}>{planMeta.detail}</div>
      </div>
    );
  };

  const toggleWorkflowGroup = (key: TaskCategory) => {
    setExpandedWorkflowGroups(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const handleOpenResultModal = useCallback((task: PlanTask) => {
    setResultModalTask(task);
  }, []);

  const [execResultTaskId, setExecResultTaskId] = useState<string | null>(null);
  const [execResultData, setExecResultData] = useState<ExecResultData | null>(null);
  const [execResultLoading, setExecResultLoading] = useState(false);

  const handleOpenExecResult = useCallback(async (taskId: string) => {
    setExecResultTaskId(taskId);
    setExecResultLoading(true);
    setExecResultData(null);
    try {
      const res = await api.getTaskStatus(taskId);
      setExecResultData(res.data as ExecResultData);
    } catch {
      setExecResultData({ error: true });
    } finally {
      setExecResultLoading(false);
    }
  }, []);

  const handleCloseExecResult = useCallback(() => {
    setExecResultTaskId(null);
    setExecResultData(null);
  }, []);

  // ── 改派 ──
  const handleOpenReassign = useCallback(async (task: PlanTask) => {
    setReassignTask(task);
    setReassignUserId('');
    setUsersLoading(true);
    try {
      const res = await api.listUsers({ limit: 200 });
      setUsers((res.data || []).map((u: UserResponse) => ({ user_id: u.user_id, username: u.username })));
    } catch {
      setUsers([]);
    } finally {
      setUsersLoading(false);
    }
  }, []);

  const handleConfirmReassign = useCallback(async () => {
    if (!reassignTask || !reassignUserId) return;
    try {
      await api.reassignPlanItem(reassignTask.id, reassignUserId);
      queryClient.invalidateQueries({ queryKey: queryKeys.planItems.my(userId) });
      setReassignTask(null);
    } catch {
      // ignore
    }
  }, [reassignTask, reassignUserId, queryClient, userId]);

  const handleCloseResultModal = useCallback(() => {
    setResultModalTask(null);
  }, []);

  // ── React Query: Submit result mutation ──

  const submitResultMutation = useMutation({
    mutationFn: async ({ taskId, result }: { taskId: string; result: PlanTaskResult }) => {
      await api.submitPlanItemResult(taskId, {
        passed: result.passed ?? true,
        notes: result.notes ?? '',
        severity: result.severity ?? 'normal',
        actual: result.actual ?? '',
        expected: result.expected ?? '',
        env: result.env ?? '',
        test_data: result.testData ?? '',
        bug_id: result.bugId ?? '',
        actual_duration: result.actualDuration ?? '',
        attachments: result.attachments ?? [],
        executed_at: result.executedAt
          ? new Date(result.executedAt).toISOString()
          : new Date().toISOString(),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.planItems.my(userId) });
    },
    onError: (err) => {
      console.error('提交结果失败:', err);
      setMutationError(getErrorMessage(err, '提交结果失败'));
    },
  });

  const handleSubmitResult = useCallback((taskId: string, result: PlanTaskResult) => {
    submitResultMutation.mutate({ taskId, result });
  }, [submitResultMutation]);

  const handleOpenDispatchModal = useCallback((task: PlanTask) => {
    setDispatchModal({
      open: true,
      itemId: task.id,
      caseId: task.caseId,
      caseTitle: task.caseTitle,
      dispatchConfig: task.dispatchConfig,
    });
  }, []);

  const handleCloseDispatchModal = useCallback(() => {
    setDispatchModal({ open: false, itemId: '', caseId: '', caseTitle: '', dispatchConfig: undefined });
  }, []);

  const handleDispatchSuccess = useCallback(() => {
    const { itemId } = dispatchModal;
    // 乐观更新本地状态为 running
    queryClient.setQueryData<PlanTask[]>(queryKeys.planItems.my(userId), old =>
      old?.map(t => t.id === itemId ? { ...t, status: 'running' } : t)
    );
    // 刷新列表
    queryClient.invalidateQueries({ queryKey: queryKeys.planItems.my(userId) });
  }, [queryClient, userId, dispatchModal]);

  const handleEditTestCase = useCallback(async (item: WorkItem) => {
    if (!item.case_id) {
      setMutationError('该工作项未关联测试用例，无法编辑');
      return;
    }
    try {
      const res = await api.getTestCase(item.case_id);
      setEditingTestCase(res.data);
    } catch {
      setMutationError('获取测试用例详情失败');
    }
  }, []);

  // ── Pending count for stats ──
  const pendingCount = useMemo(() => {
    const workflowPending = workItems.filter(isActiveWorkflowItem).length;
    const planPending = planTasks.filter(t => t.status !== 'done').length;
    return workflowPending + planPending;
  }, [workItems, planTasks]);

  const pendingBoardItems = useMemo<PendingBoardItem[]>(() => {
    const planItems = planTasks
      .filter(task => task.status !== 'done')
      .map(task => ({
        id: task.id,
        kind: 'plan' as const,
        title: task.caseTitle || task.caseId,
        category: task.type === 'auto' ? '自动化用例执行' : '手工用例执行',
        status: getPlanStatusLabel(task),
        nextStep: getPlanNextStep(task),
        ...getPeriodMeta(parsePlanBoundary(task.dispatchConfig?.planned_at), task.dispatchConfig?.planned_at),
      }));

    const workflowItems = workItems
      .filter(isActiveWorkflowItem)
      .map(item => ({
        id: item.item_id,
        kind: 'workflow' as const,
        title: item.title,
        category: getWorkflowTypeLabel(item),
        status: getStateLabel(item.current_state, getTypeCode(item.type_code)),
        nextStep: getWorkflowNextStep(item),
        ...getPeriodMeta(null, item.updated_at),
      }));

    return [...planItems, ...workflowItems].sort((a, b) => {
      const rankDiff = PENDING_PERIOD_RANK[a.period] - PENDING_PERIOD_RANK[b.period];
      if (rankDiff !== 0) return rankDiff;
      const aTime = a.dueTime ?? a.updatedTime ?? 0;
      const bTime = b.dueTime ?? b.updatedTime ?? 0;
      return aTime - bTime;
    });
  }, [planTasks, workItems]);

  const pendingBoardStats = useMemo(() => {
    const initial: Record<PendingPeriodKey, number> = {
      overdue: 0,
      today: 0,
      soon: 0,
      normal: 0,
      unset: 0,
    };
    return pendingBoardItems.reduce((acc, item) => {
      acc[item.period] += 1;
      return acc;
    }, initial);
  }, [pendingBoardItems]);

  const pendingKindStats = useMemo(() => {
    const plan = pendingBoardItems.filter(item => item.kind === 'plan').length;
    const workflow = pendingBoardItems.length - plan;
    return { plan, workflow };
  }, [pendingBoardItems]);

  const pendingCategoryStats = useMemo(() => {
    const counts = pendingBoardItems.reduce<Record<string, number>>((acc, item) => {
      acc[item.category] = (acc[item.category] || 0) + 1;
      return acc;
    }, {});
    return Object.entries(counts)
      .map(([label, count]) => ({
        label,
        count,
        percent: pendingBoardItems.length > 0 ? Math.round((count / pendingBoardItems.length) * 100) : 0,
      }))
      .sort((a, b) => b.count - a.count);
  }, [pendingBoardItems]);

  const pendingRiskCount = pendingBoardStats.overdue + pendingBoardStats.today + pendingBoardStats.soon;
  const pendingRiskPercent = pendingCount > 0 ? Math.round((pendingRiskCount / pendingCount) * 100) : 0;
  const pendingAiStatus: PendingAiStatus = pendingAiLoading
    ? 'loading'
    : pendingAiError
      ? 'error'
      : pendingAiResult
        ? 'success'
        : 'idle';

  const pendingAiButtonLabel = {
    idle: '智能分析',
    loading: '分析中',
    success: '查看结果',
    error: '分析失败',
  }[pendingAiStatus];

  const pendingAiButtonAriaLabel = {
    idle: '智能分析当前待处理任务',
    loading: '正在智能分析当前待处理任务',
    success: '查看待处理任务智能分析结果',
    error: '重新分析当前待处理任务，当前分析失败',
  }[pendingAiStatus];

  const handleAnalyzePendingTasks = useCallback(async () => {
    setPendingAiOpen(true);
    setPendingAiLoading(true);
    setPendingAiError(null);
    setPendingAiResult(null);
    try {
      const res = await api.analyzePendingTasks({
        user_id: userId,
        stats: {
          total: pendingCount,
          plan_count: pendingKindStats.plan,
          workflow_count: pendingKindStats.workflow,
          risk_count: pendingRiskCount,
          risk_percent: pendingRiskPercent,
          overdue_count: pendingBoardStats.overdue,
          today_count: pendingBoardStats.today,
          soon_count: pendingBoardStats.soon,
          normal_count: pendingBoardStats.normal,
          unset_count: pendingBoardStats.unset,
        },
        category_stats: pendingCategoryStats,
        items: pendingBoardItems.slice(0, 30).map(item => ({
          id: item.id,
          kind: item.kind,
          title: item.title,
          category: item.category,
          status: item.status,
          next_step: item.nextStep,
          period: item.period,
          period_label: item.periodLabel,
          period_detail: item.periodDetail,
        })),
      });
      const result = res.data;
      const failedByPayload = result
        && (result.summary.includes('AI 分析失败')
          || result.anomalies.some(item => item.title.includes('AI 分析失败')));
      if (failedByPayload) {
        const message = result.summary || result.anomalies[0]?.detail || 'AI 分析失败';
        console.error('Pending task AI analysis failed:', result);
        setPendingAiResult(null);
        setPendingAiError(message);
        return;
      }
      setPendingAiResult(result);
    } catch (err) {
      const message = getErrorMessage(err, '智能分析失败');
      console.error('Pending task AI analysis request failed:', err);
      setPendingAiError(message);
    } finally {
      setPendingAiLoading(false);
    }
  }, [
    pendingBoardItems,
    pendingBoardStats,
    pendingCategoryStats,
    pendingCount,
    pendingKindStats,
    pendingRiskCount,
    pendingRiskPercent,
    userId,
  ]);

  // ── Error display ──
  const displayWorkItemsError = workItemsError ? '获取工作流任务列表失败' : null;
  const displayPlanItemsError = planItemsError ? '获取计划任务列表失败' : null;

  // ── Tab state ──
  const [activeTab, setActiveTab] = useState<MyTasksTab>('plan');

  const tabs = [
    { key: 'plan' as const, label: '用例执行任务', count: planTasks.length },
    { key: 'review' as const, label: '审核相关', count: categoryCounts.review },
    { key: 'requirement' as const, label: '测试用例编写需求待办', count: categoryCounts.requirement },
    { key: 'testcase_dev' as const, label: '用例开发', count: categoryCounts.testcase_dev },
  ];

  const activeWorkflowCategories = activeTab === 'plan'
    ? []
    : categories.filter(cat => cat.key === activeTab);
  const activeWorkflowTabLabel = tabs.find(tab => tab.key === activeTab)?.label ?? '工作流事项';

  useEffect(() => {
    window.localStorage.setItem(FONT_SCALE_STORAGE_KEY, fontScale);
  }, [fontScale]);

  const fontScaleValue = FONT_SCALE_OPTIONS.find(option => option.key === fontScale)?.value ?? 1;

  return (
    <div
      className="page-content my-tasks-page"
      style={{ '--my-tasks-font-scale': fontScaleValue, '--my-tasks-line-height': 1.65 } as MyTasksPageStyle}
    >
      <PageToolbar
        meta={(
          <>
            <button
              type="button"
              className={`stat-pill stat-pill--warning my-tasks-pending-trigger${pendingBoardOpen ? ' my-tasks-pending-trigger--active' : ''}`}
              onClick={() => setPendingBoardOpen(open => !open)}
              aria-expanded={pendingBoardOpen}
            >
              <span className="stat-pill__label">待处理</span>
              <span className="stat-pill__value">{pendingCount}</span>
            </button>
          </>
        )}
        actions={(
          <>
            <button type="button" className="btn btn--secondary btn--sm" onClick={handleRefreshAll} disabled={workItemsLoading || planItemsLoading}>
              刷新
            </button>
            <div className="my-tasks-font-controls" role="group" aria-label="字体大小">
              {FONT_SCALE_OPTIONS.map(option => (
                <button
                  key={option.key}
                  type="button"
                  className={`my-tasks-font-control${fontScale === option.key ? ' my-tasks-font-control--active' : ''}`}
                  title={option.title}
                  aria-pressed={fontScale === option.key}
                  onClick={() => setFontScale(option.key)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </>
        )}
      />

      {pendingBoardOpen && (
        <div
          className="my-tasks-pending-modal"
          role="presentation"
          onClick={() => setPendingBoardOpen(false)}
        >
          <section
            className={`my-tasks-pending-board my-tasks-pending-board--modal my-tasks-pending-board--ai-${pendingAiStatus}`}
            role="dialog"
            aria-modal="true"
            aria-label="待处理数据指标"
            onClick={e => e.stopPropagation()}
          >
            {pendingAiStatus !== 'idle' && (
              <div
                className={`my-tasks-pending-board__ai-status my-tasks-pending-board__ai-status--${pendingAiStatus}`}
                role={pendingAiStatus === 'error' ? 'alert' : 'status'}
                aria-live={pendingAiStatus === 'error' ? 'assertive' : 'polite'}
              >
                <span className="my-tasks-pending-board__ai-status-icon" aria-hidden="true">
                  {pendingAiStatus === 'loading' && <span className="my-tasks-pending-board__ai-orbit" />}
                  {pendingAiStatus === 'success' && <CheckCircle2 size={16} />}
                  {pendingAiStatus === 'error' && <AlertTriangle size={16} />}
                </span>
                <span className="my-tasks-pending-board__ai-status-copy">
                  <strong>{pendingAiStatus === 'loading' ? '智能分析正在运行' : pendingAiStatus === 'success' ? '智能分析已完成' : '智能分析失败'}</strong>
                  <small>
                    {pendingAiStatus === 'loading'
                      ? '正在识别任务风险与优先级，请稍候'
                      : pendingAiStatus === 'success'
                        ? '健康评分、风险项和处理建议已生成'
                        : pendingAiError}
                  </small>
                </span>
                {pendingAiStatus !== 'loading' && (
                  <button
                    type="button"
                    className="my-tasks-pending-board__ai-status-action"
                    onClick={pendingAiStatus === 'success' ? () => setPendingAiOpen(true) : handleAnalyzePendingTasks}
                  >
                    {pendingAiStatus === 'success' ? '查看结果' : '重试'}
                  </button>
                )}
              </div>
            )}
            <div className="my-tasks-pending-board__header">
              <div>
                <h2>待处理数据指标</h2>
                <span>当前任务结构与时间风险</span>
              </div>
              <button
                type="button"
                className="my-tasks-pending-board__close"
                onClick={() => setPendingBoardOpen(false)}
                aria-label="关闭待处理数据指标"
              >
                ×
              </button>
            </div>
            <div className="my-tasks-pending-board__hero">
              <div className="my-tasks-pending-board__total-card">
                <div className="my-tasks-pending-board__card-head">
                  <span>待处理总量</span>
                  <button
                    type="button"
                    className={`my-tasks-pending-board__ai-btn my-tasks-pending-board__ai-btn--${pendingAiStatus}`}
                    onClick={pendingAiStatus === 'success' ? () => setPendingAiOpen(true) : handleAnalyzePendingTasks}
                    disabled={pendingAiLoading || pendingCount === 0}
                    title={pendingAiStatus === 'success' ? '查看上次智能分析结果' : pendingAiStatus === 'error' ? '重新分析当前待处理任务' : '智能分析当前待处理任务'}
                    aria-label={pendingAiButtonAriaLabel}
                  >
                    {pendingAiStatus === 'loading' && <span className="my-tasks-pending-board__ai-btn-spinner" aria-hidden="true" />}
                    {pendingAiStatus === 'success' && <CheckCircle2 size={14} aria-hidden="true" />}
                    {pendingAiStatus === 'error' && <AlertTriangle size={14} aria-hidden="true" />}
                    {pendingAiStatus === 'idle' && <Brain size={14} aria-hidden="true" />}
                    <span className="my-tasks-pending-board__ai-btn-text">{pendingAiButtonLabel}</span>
                  </button>
                </div>
                <strong>{pendingCount}</strong>
                <small>用例执行任务 {pendingKindStats.plan} · 工作流 {pendingKindStats.workflow}</small>
              </div>
              <div>
                <span>风险待办</span>
                <strong>{pendingRiskCount}</strong>
                <small>占比 {pendingRiskPercent}% · 含超期、24小时内、3天内</small>
              </div>
              <div>
                <span>超期/停留较久</span>
                <strong>{pendingBoardStats.overdue}</strong>
                <small>{pendingBoardStats.overdue > 0 ? '建议优先关注' : '暂无明显积压'}</small>
              </div>
            </div>
            <div className="my-tasks-pending-board__summary">
              {PENDING_BOARD_BUCKETS.map(bucket => (
                <div key={bucket.key} className={`my-tasks-pending-board__bucket my-tasks-pending-board__bucket--${bucket.tone}`}>
                  <span>{bucket.label}</span>
                  <strong>{pendingBoardStats[bucket.key]}</strong>
                </div>
              ))}
            </div>
            <div className="my-tasks-pending-board__content">
              <div className="my-tasks-pending-board__groups">
                <div className="my-tasks-pending-board__section-title">分类占比</div>
                {pendingCategoryStats.map(stat => (
                  <div
                    key={stat.label}
                    className="my-tasks-pending-board__group"
                  >
                    <div className="my-tasks-pending-board__group-row">
                      <span>{stat.label}</span>
                      <strong>{stat.count}</strong>
                    </div>
                    <div className="my-tasks-pending-board__bar" aria-hidden="true">
                      <span style={{ width: `${stat.percent}%` }} />
                    </div>
                    <small>{stat.percent}%</small>
                  </div>
                ))}
                {pendingCategoryStats.length === 0 && (
                  <div className="my-tasks-pending-board__empty">暂无分类数据</div>
                )}
              </div>
              <div className="my-tasks-pending-board__queue">
                <div className="my-tasks-pending-board__section-title">重点关注</div>
                {pendingBoardItems.slice(0, PENDING_BOARD_TOP_LIMIT).map(item => (
                  <div key={`${item.kind}-${item.id}`} className="my-tasks-pending-board__item">
                    <div className="my-tasks-pending-board__item-main">
                      <div>
                        <span className={`my-tasks-pending-board__period my-tasks-pending-board__period--${item.period}`}>
                          {item.periodLabel}
                        </span>
                        <span className="my-tasks-pending-board__category">{item.category}</span>
                      </div>
                      <strong title={item.title}>{item.title}</strong>
                      <small>{item.nextStep} · {item.status} · {item.periodDetail}</small>
                    </div>
                  </div>
                ))}
                {pendingBoardItems.length === 0 && (
                  <div className="my-tasks-pending-board__empty">暂无待处理事项</div>
                )}
              </div>
            </div>
          </section>
        </div>
      )}

      <PendingAiAnalysisDialog
        open={pendingAiOpen}
        loading={pendingAiLoading}
        result={pendingAiResult}
        error={pendingAiError}
        onOpenChange={setPendingAiOpen}
        onRetry={handleAnalyzePendingTasks}
      />

      {displayWorkItemsError && (
        <div className="error-banner" style={{ marginBottom: 16, justifyContent: 'space-between' }}>
          {displayWorkItemsError}
        </div>
      )}

      {displayPlanItemsError && (
        <div className="error-banner" style={{ marginBottom: 16, justifyContent: 'space-between' }}>
          {displayPlanItemsError}
        </div>
      )}

      {mutationError && (
        <div className="error-banner" style={{ marginBottom: 16, justifyContent: 'space-between' }}>
          {mutationError} <button type="button" className="btn btn--ghost btn--sm" onClick={() => setMutationError(null)}>×</button>
        </div>
      )}

      {/* ── Tab bar ── */}
      {(!workItemsLoading || !planItemsLoading) && (
        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: 2, marginBottom: 16, borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: 0,
        }}>
          {tabs.map(tab => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                style={{
                  position: 'relative', padding: '8px 20px', fontSize: scaledFont(13), fontWeight: isActive ? 600 : 500,
                  color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                  background: 'transparent', border: 'none', cursor: 'pointer',
                  transition: 'color 0.15s',
                }}
              >
                {tab.label}
                <span style={{
                  marginLeft: 6, fontSize: scaledFont(11), fontWeight: 500,
                  color: isActive ? 'var(--accent-primary)' : 'var(--text-tertiary)',
                }}>
                  {tab.count}
                </span>
                {isActive && (
                  <div style={{
                    position: 'absolute', bottom: -1, left: 0, right: 0, height: 2,
                    background: 'var(--accent-primary)', borderRadius: '2px 2px 0 0',
                  }} />
                )}
              </button>
            );
          })}
        </div>
      )}

      {workItemsLoading && planItemsLoading ? (
        <div className="loading-overlay"><div className="loading-spinner" /></div>
      ) : workItems.length === 0 && planTasks.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">✅</div>
          <p className="empty-state__text">暂无待处理的任务</p>
        </div>
      ) : (
        <div style={myTasksStyles.list}>
          {activeTab === 'plan' && planTasks.length > 0 && (
            <PlanTaskTable
              planTasks={planTasks}
              onOpenResultModal={handleOpenResultModal}
              onOpenDispatchModal={handleOpenDispatchModal}
              onViewExecutionResult={handleOpenExecResult}
              onReassign={handleOpenReassign}
            />
          )}

          {activeTab === 'plan' && planTasks.length === 0 && (
            <div className="empty-state" style={{ padding: '40px 0' }}>
              <p className="empty-state__text">暂无用例执行任务</p>
            </div>
          )}

          {activeTab === 'requirement' && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: 12,
              padding: '10px 12px',
              border: '1px solid var(--border-subtle)',
              borderRadius: 8,
              background: 'var(--bg-primary)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                <span style={{ fontSize: scaledFont(13), fontWeight: 700, color: 'var(--text-primary)' }}>
                  测试用例编写需求
                </span>
                <span style={{ fontSize: scaledFont(11), color: 'var(--text-tertiary)' }}>
                  {requirementScope === 'mine'
                    ? `${requirementScopeStats.mine} / ${requirementScopeStats.all} 项`
                    : `${requirementScopeStats.all} 项`}
                </span>
              </div>
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: 2,
                borderRadius: 6,
                background: 'var(--surface-secondary)',
                border: '1px solid var(--border-subtle)',
              }}>
                {([
                  { key: 'mine' as const, label: '我创建的', count: requirementScopeStats.mine },
                  { key: 'all' as const, label: '所有需求', count: requirementScopeStats.all },
                ]).map(option => {
                  const selected = requirementScope === option.key;
                  return (
                    <button
                      key={option.key}
                      type="button"
                      className="btn btn--sm"
                      onClick={() => setRequirementScope(option.key)}
                      aria-pressed={selected}
                      style={{
                        border: 'none',
                        borderRadius: 4,
                        background: selected ? 'var(--bg-primary)' : 'transparent',
                        color: selected ? 'var(--accent-primary)' : 'var(--text-secondary)',
                        boxShadow: selected ? '0 1px 3px rgba(15, 23, 42, 0.12)' : 'none',
                        fontSize: scaledFont(12),
                        padding: '5px 10px',
                        fontWeight: selected ? 700 : 500,
                      }}
                    >
                      {option.label}
                      <span style={{ marginLeft: 6, color: selected ? 'var(--accent-primary)' : 'var(--text-tertiary)' }}>
                        {option.count}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab !== 'plan' && activeWorkflowCategories.length > 0 && activeWorkflowCategories.map(cat => {
            const isGroupExpanded = expandedWorkflowGroups.has(cat.key);
            const visibleItems = isGroupExpanded ? cat.items : cat.items.slice(0, WORKFLOW_GROUP_PREVIEW_LIMIT);
            const hiddenCount = cat.items.length - visibleItems.length;
            const groupSummary = getWorkflowGroupSummary(cat.items);
            return (
            <div key={cat.key} style={myTasksStyles.group}>
              <div style={{ ...myTasksStyles.groupHeader, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                {groupSummary && (
                  <span style={{ fontSize: scaledFont(11), color: 'var(--text-tertiary)' }}>{groupSummary}</span>
                )}
                <div style={{ flex: 1 }} />
                {cat.items.length > WORKFLOW_GROUP_PREVIEW_LIMIT && (
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={() => toggleWorkflowGroup(cat.key)}
                    style={{ fontSize: scaledFont(11), padding: '3px 10px' }}
                  >
                    {isGroupExpanded ? '收起' : `展开更多 (${hiddenCount})`}
                  </button>
                )}
              </div>
              {visibleItems.map(item => {
                const isExpanded = expandedId === item.item_id;
                const typeCode = getTypeCode(item.type_code);
                return (
                  <div key={item.item_id}>
                    <div onClick={() => { void handleToggleExpand(item.item_id); }}
                      style={{
                        display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 10, padding: '10px 12px',
                        borderBottom: '0.5px solid var(--border-subtle)',
                        cursor: 'pointer', fontSize: scaledFont(13), lineHeight: 'var(--my-tasks-line-height)', transition: 'background 0.1s',
                        background: isExpanded
                          ? 'color-mix(in srgb, var(--accent-primary) 4%, transparent)'
                          : undefined,
                      }}
                    >
                      <span style={{
                        fontSize: scaledFont(9), color: isExpanded ? 'var(--accent-primary)' : 'var(--text-tertiary)',
                        transition: 'transform 0.15s', transform: isExpanded ? 'rotate(90deg)' : 'none',
                        flexShrink: 0,
                      }}>▶</span>
                      <span style={{
                        padding: '2px 8px', borderRadius: 999, fontSize: scaledFont(10), fontWeight: 700,
                        background: item.type_code === 'TEST_CASE' ? 'rgba(124,58,237,0.12)' : `${cat.color}18`,
                        color: item.type_code === 'TEST_CASE' ? '#7c3aed' : cat.color,
                        flexShrink: 0,
                      }}>
                        {getWorkflowTypeLabel(item)}
                      </span>
                      <div style={{ flex: '1 1 280px', minWidth: 0 }}>
                        <div style={{
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                          fontWeight: isExpanded ? 700 : 600, color: 'var(--text-primary)',
                        }}>
                          {item.title}
                        </div>
                        <div style={{
                          display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 8,
                          marginTop: 2, fontSize: scaledFont(11), color: 'var(--text-tertiary)',
                        }}>
                          <span>{getWorkflowNextStep(item)}</span>
                          {item.content && <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 280 }}>{item.content}</span>}
                        </div>
                      </div>
                      <span className="status-badge" style={{
                        ...getWorkflowStateStyle(item.current_state),
                        fontSize: scaledFont(10), padding: '3px 9px', flexShrink: 0,
                      }}>{getStateLabel(item.current_state, typeCode)}</span>
                      <span style={{
                        fontSize: scaledFont(10), fontFamily: 'monospace', color: 'var(--text-tertiary)', flexShrink: 0,
                      }}>
                        更新 {new Date(item.updated_at).toLocaleString('zh-CN', {
                          month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
                        })}
                      </span>
                      <button
                        type="button"
                        className="btn btn--primary btn--sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          void handleWorkflowPrimaryAction(item);
                        }}
                        style={{ fontSize: scaledFont(11), padding: '5px 12px', flexShrink: 0 }}
                      >
                        {getWorkflowPrimaryAction(item)}
                      </button>
                      <WorkflowActionToolbar
                        workflowItemId={item.item_id}
                        typeCode={typeCode}
                        defaultPriority={itemDetail && 'priority' in itemDetail ? String(itemDetail.priority || '') : ''}
                        onTransitionSuccess={handleTaskWorkflowSuccess}
                        compact
                        lazy
                        hideActions={item.type_code === 'TEST_CASE' ? ['START_WRITE'] : undefined}
                      />
                    </div>
                    {isExpanded && (
                      <div style={{
                        padding: '10px 12px 12px 28px', borderBottom: '0.5px solid var(--border-subtle)',
                        background: 'var(--bg-primary)',
                      }}>
                        {loadingDetail ? (
                          <div style={myTasksStyles.loadingSmall}>
                            <div className="loading-spinner" style={{ width: 20, height: 20 }} />
                          </div>
                        ) : (
                          <>
                            {item.type_code === 'REQUIREMENT' && itemDetail && 'req_id' in itemDetail ? (
                              /* ── 需求详情 ── 两栏布局 ── */
                              <>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 12 }}>
                                  <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                    <div style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>优先级 & 状态</div>
                                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                                      <span style={{
                                        padding: '2px 8px', borderRadius: 4, fontSize: scaledFont(12), fontWeight: 600,
                                        backgroundColor: itemDetail.priority === 'P0' ? '#fef2f2' : itemDetail.priority === 'P1' ? '#fffbeb' : '#f1f5f9',
                                        color: itemDetail.priority === 'P0' ? '#dc2626' : itemDetail.priority === 'P1' ? '#d97706' : '#64748b',
                                      }}>{itemDetail.priority || 'P2'}</span>
                                      <span style={{ ...getWorkflowStateStyle(item.current_state), padding: '2px 8px', borderRadius: 4, fontSize: scaledFont(12) }}>
                                        {getStateLabel(item.current_state, 'REQUIREMENT')}
                                      </span>
                                    </div>
                                  </div>
                                  <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                    <div style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>分类 & 来源</div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                      {itemDetail.category && <span style={{ padding: '2px 8px', fontSize: scaledFont(12), borderRadius: 4, background: '#e2e8f0' }}>{itemDetail.category}</span>}
                                      {itemDetail.source && <span style={{ padding: '2px 8px', fontSize: scaledFont(12), borderRadius: 4, background: '#e2e8f0' }}>{itemDetail.source}</span>}
                                    </div>
                                  </div>
                                  {renderPlanTimeCard(itemDetail.planned_start_date, itemDetail.planned_end_date)}
                                </div>

                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginBottom: 12 }}>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                    <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                      <div style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 6 }}>人员</div>
                                      <div style={{ display: 'flex', flexDirection: 'column', gap: 3, fontSize: scaledFont(12), color: '#475569' }}>
                                        {itemDetail.tpm_owner_name && <span>👤 TPM: {itemDetail.tpm_owner_name}</span>}
                                        {itemDetail.manual_dev_name && <span>✏️ 手动: {itemDetail.manual_dev_name}</span>}
                                        {itemDetail.auto_dev_name && <span>🤖 自动: {itemDetail.auto_dev_name}</span>}
                                        {itemDetail.creator_name && <span>📋 创建: {itemDetail.creator_name}</span>}
                                      </div>
                                    </div>
                                    {itemDetail.tags && itemDetail.tags.length > 0 && (
                                      <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                        <div style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 6 }}>标签</div>
                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                          {itemDetail.tags.map((tag: string) => (
                                            <span key={tag} style={{ padding: '2px 8px', fontSize: 11, borderRadius: 999, background: '#eff6ff', color: '#3b82f6' }}>{tag}</span>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                    {itemDetail.description && (
                                      <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                        <div style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 6 }}>需求描述</div>
                                        <div style={{ whiteSpace: 'pre-wrap', fontSize: scaledFont(12), color: '#475569', lineHeight: 'var(--my-tasks-line-height)', maxHeight: 160, overflowY: 'auto' }}>{itemDetail.description}</div>
                                      </div>
                                    )}
                                    {itemDetail.acceptance_criteria && (
                                      <div style={{ background: '#f0fdf4', borderRadius: 8, padding: '10px 12px', border: '1px solid #bbf7d0' }}>
                                        <div style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#16a34a', marginBottom: 6 }}>✅ 验收标准</div>
                                        <div style={{ whiteSpace: 'pre-wrap', fontSize: scaledFont(12), color: '#15803d', lineHeight: 'var(--my-tasks-line-height)' }}>{itemDetail.acceptance_criteria}</div>
                                      </div>
                                    )}
                                  </div>
                                </div>

                                <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                                    <span style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
                                      关联测试用例 ({reqTestCases.length})
                                    </span>
                                    <button type="button" className="btn btn--primary btn--sm"
                                      onClick={(e) => { e.stopPropagation(); if (item.req_id) { setCreatingReqTestCaseReqId(item.req_id); setShowCreateReqTestCase(true); } }}
                                      style={{ fontSize: scaledFont(10), padding: '2px 8px' }}
                                    >+ 创建用例</button>
                                  </div>
                                  {loadingReqTestCases ? (
                                    <div style={myTasksStyles.loadingSmall}><div className="loading-spinner" style={{ width: 16, height: 16 }} /></div>
                                  ) : reqTestCases.length > 0 ? (
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 4 }}>
                                      {reqTestCases.map(tc => (
                                        <div key={tc.case_id} style={{ fontSize: scaledFont(12), color: '#475569', padding: '6px 10px', background: '#fff', borderRadius: 6, border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', gap: 8 }}>
                                          <span style={{ fontFamily: 'monospace', fontSize: scaledFont(11), color: '#94a3b8', whiteSpace: 'nowrap' }}>{tc.case_id}</span>
                                          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{tc.title}</span>
                                        </div>
                                      ))}
                                    </div>
                                  ) : (
                                    <p style={{ fontSize: scaledFont(12), color: '#94a3b8', fontStyle: 'italic' }}>暂无测试用例</p>
                                  )}
                                </div>
                              </>
                            ) : item.type_code === 'TEST_CASE' && itemDetail && 'case_id' in itemDetail ? (
                              <>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 12 }}>
                                  <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                    <div style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>用例标识</div>
                                    <div style={{ fontSize: scaledFont(12), color: '#475569', lineHeight: 'var(--my-tasks-line-height)' }}>
                                      <div style={{ fontFamily: 'monospace', color: 'var(--accent-primary)', fontWeight: 700 }}>{itemDetail.case_id}</div>
                                      <div>版本 v{itemDetail.version} · {itemDetail.is_active ? '启用' : '停用'}</div>
                                    </div>
                                  </div>
                                  <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                    <div style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>优先级 & 分类</div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                      {itemDetail.priority && <span style={{ padding: '2px 8px', fontSize: scaledFont(12), borderRadius: 4, background: '#e2e8f0' }}>{itemDetail.priority}</span>}
                                      {itemDetail.test_category && <span style={{ padding: '2px 8px', fontSize: scaledFont(12), borderRadius: 4, background: '#e2e8f0' }}>{itemDetail.test_category}</span>}
                                      {itemDetail.risk_level && <span style={{ padding: '2px 8px', fontSize: scaledFont(12), borderRadius: 4, background: '#fef3c7', color: '#92400e' }}>{itemDetail.risk_level}</span>}
                                    </div>
                                  </div>
                                  <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                    <div style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>自动化</div>
                                    <div style={{ fontSize: scaledFont(12), color: '#475569', lineHeight: 'var(--my-tasks-line-height)' }}>
                                      <div>{itemDetail.is_automated ? '已自动化' : itemDetail.is_need_auto ? '需要自动化' : '无需自动化'}</div>
                                      {itemDetail.automation_type && <div>{itemDetail.automation_type}</div>}
                                    </div>
                                  </div>
                                </div>

                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginBottom: 12 }}>
                                  <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                    <div style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 6 }}>归属</div>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 3, fontSize: scaledFont(12), color: '#475569' }}>
                                      <span>实验室: {itemDetail.lab_name || itemDetail.lab_id || '-'}</span>
                                      <span>目录: {itemDetail.catalog_breadcrumb || itemDetail.catalog_path?.join(' / ') || '-'}</span>
                                      <span>负责人: {itemDetail.owner_id || '-'}</span>
                                      <span>评审人: {itemDetail.reviewer_id || '-'}</span>
                                      <span>自动化负责人: {itemDetail.auto_dev_id || '-'}</span>
                                    </div>
                                  </div>
                                  <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                    <div style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 6 }}>执行信息</div>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 3, fontSize: scaledFont(12), color: '#475569' }}>
                                      <span>预计耗时: {itemDetail.estimated_duration_sec ? `${Math.round(itemDetail.estimated_duration_sec / 60)} 分钟` : '-'}</span>
                                      <span>步骤数: {itemDetail.steps?.length || 0}</span>
                                      <span>清理步骤: {itemDetail.cleanup_steps?.length || 0}</span>
                                      <span>破坏性: {itemDetail.is_destructive ? '是' : '否'}</span>
                                    </div>
                                  </div>
                                </div>

                                {(itemDetail.pre_condition || itemDetail.post_condition) && (
                                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginBottom: 12 }}>
                                    {itemDetail.pre_condition && (
                                      <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                        <div style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 6 }}>前置条件</div>
                                        <div style={{ whiteSpace: 'pre-wrap', fontSize: scaledFont(12), color: '#475569', lineHeight: 'var(--my-tasks-line-height)', maxHeight: 140, overflowY: 'auto' }}>{itemDetail.pre_condition}</div>
                                      </div>
                                    )}
                                    {itemDetail.post_condition && (
                                      <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px' }}>
                                        <div style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 6 }}>后置条件</div>
                                        <div style={{ whiteSpace: 'pre-wrap', fontSize: scaledFont(12), color: '#475569', lineHeight: 'var(--my-tasks-line-height)', maxHeight: 140, overflowY: 'auto' }}>{itemDetail.post_condition}</div>
                                      </div>
                                    )}
                                  </div>
                                )}

                                {itemDetail.required_env && Object.keys(itemDetail.required_env).length > 0 && (
                                  <div style={{ background: '#f8fafc', borderRadius: 8, padding: '10px 12px', marginBottom: 12 }}>
                                    <div style={{ fontSize: scaledFont(10), fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 6 }}>环境要求</div>
                                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: scaledFont(11), color: '#475569', lineHeight: 'var(--my-tasks-line-height)' }}>
                                      {JSON.stringify(itemDetail.required_env, null, 2)}
                                    </pre>
                                  </div>
                                )}
                              </>
                            ) : (
                              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                {item.content && <p style={myTasksStyles.contentPreview}>{item.content}</p>}
                                {itemDetail && 'description' in itemDetail && itemDetail.description && (
                                  <p style={myTasksStyles.contentPreview}>{itemDetail.description}</p>
                                )}
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            );
          })}

          {activeTab !== 'plan' && activeWorkflowCategories.length === 0 && (
            <div className="empty-state" style={{ padding: '40px 0' }}>
              <p className="empty-state__text">暂无{activeWorkflowTabLabel}</p>
            </div>
          )}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════ */}
      {/*  Result Backfill Modal                                  */}
      {/* ════════════════════════════════════════════════════════ */}
      <ResultBackfillModal
        task={resultModalTask}
        onClose={handleCloseResultModal}
        onSubmit={handleSubmitResult}
      />

      {/* ── 改派弹窗 ── */}
      {reassignTask && (
        <ReassignModal
          task={reassignTask}
          users={users}
          loading={usersLoading}
          currentUserId={userId}
          selectedUserId={reassignUserId}
          onSelectUser={setReassignUserId}
          onConfirm={handleConfirmReassign}
          onClose={() => setReassignTask(null)}
        />
      )}

      {execResultTaskId && (
        <ExecResultModal
          taskId={execResultTaskId}
          loading={execResultLoading}
          data={execResultData}
          onClose={handleCloseExecResult}
        />
      )}

      {/* ════════════════════════════════════════════════════════ */}
      {/*  Single Dispatch Modal                                 */}
      {/* ════════════════════════════════════════════════════════ */}
      <SingleDispatchModal
        open={dispatchModal.open}
        itemId={dispatchModal.itemId}
        caseId={dispatchModal.caseId}
        caseTitle={dispatchModal.caseTitle}
        dispatchConfig={dispatchModal.dispatchConfig}
        onClose={handleCloseDispatchModal}
        onSuccess={handleDispatchSuccess}
      />

      {/* ════════════════════════════════════════════════════════ */}
      {/*  Edit Test Case Modal (编写中的测试用例)               */}
      {/* ════════════════════════════════════════════════════════ */}
      {editingTestCase && (
        <CreateTestCaseForm
          editTestCase={editingTestCase}
          onClose={() => setEditingTestCase(null)}
          onSuccess={() => {
            setEditingTestCase(null);
            handleTaskWorkflowSuccess();
          }}
          lockRequirementId
        />
      )}

      {/* ════════════════════════════════════════════════════════ */}
      {/*  Create Test Case from Requirement Modal               */}
      {/* ════════════════════════════════════════════════════════ */}
      {showCreateReqTestCase && creatingReqTestCaseReqId && (
        <CreateTestCaseForm
          onClose={() => { setShowCreateReqTestCase(false); setCreatingReqTestCaseReqId(null); }}
          onSuccess={() => {
            setShowCreateReqTestCase(false);
            setCreatingReqTestCaseReqId(null);
            handleTaskWorkflowSuccess();
            // 重新加载测试用例列表
            if (creatingReqTestCaseReqId) {
              setLoadingReqTestCases(true);
              api.listTestCases({ ref_req_id: creatingReqTestCaseReqId, limit: 50 })
                .then(res => setReqTestCases(res.data || []))
                .catch(() => {})
                .finally(() => setLoadingReqTestCases(false));
            }
          }}
          defaultRequirementId={creatingReqTestCaseReqId}
          lockRequirementId
          defaultLabId=""
          defaultCatalogPrefix={[]}
        />
      )}
    </div>
  );
};

export default MyTasksPage;
