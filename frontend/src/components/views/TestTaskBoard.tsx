import React, { useMemo, useState } from 'react';
import {
  Calendar,
  CheckCircle2,
  Clock3,
  FileText,
  LayoutDashboard,
  ListTodo,
  LogIn,
  Mail,
  PlayCircle,
  Plus,
  Server,
  Shield,
  User,
  X,
  XCircle,
} from 'lucide-react';
import { TestCase } from '../../types';
import { User as UserType, ROLES } from '../../constants/config';

type TaskExecType = 'MANUAL' | 'AUTOMATION';
type TaskStatus = 'PLANNED' | 'RUNNING' | 'BLOCKED' | 'DONE';
type CaseResult = 'PENDING' | 'PASSED' | 'FAILED';
type StepStatus = 'PENDING' | 'PASSED' | 'FAILED';

interface TaskLog {
  id: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
  timestamp: string;
}

interface AutomationStep {
  id: string;
  title: string;
  detail: string;
  status: StepStatus;
}

interface BoardTask {
  id: string;
  title: string;
  description: string;
  assigneeId: string;
  creatorId: string;
  type: TaskExecType;
  status: TaskStatus;
  caseIds: string[];
  caseResults: Record<string, CaseResult>;
  automationSteps: AutomationStep[];
  logs: TaskLog[];
  createdAt: string;
  updatedAt: string;
}

interface NewTaskForm {
  title: string;
  description: string;
  assigneeId: string;
  type: TaskExecType;
  caseIds: string[];
  automationSteps: Array<{ id: string; title: string; detail: string }>;
}

interface TestTaskBoardProps {
  currentUser: UserType | null;
  users: UserType[];
  testCases: TestCase[];
  availableNavViews: string[];
  onNavigateToReqList: () => void;
  onNavigateToCaseList: () => void;
  onNavigateToMyTasks: () => void;
  onNavigateToDutMgmt: () => void;
  onNavigateToUserMgmt: () => void;
  onNavigateToNavMgmt: () => void;
  onLogout: () => void;
  showUserProfile: boolean;
  onToggleUserProfile: () => void;
}

const now = () => new Date().toISOString();

const generateId = (prefix: string) => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const formatDateTime = (value: string): string => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
};

const buildLog = (message: string, level: TaskLog['level'] = 'INFO'): TaskLog => ({
  id: generateId('log'),
  level,
  message,
  timestamp: now(),
});

const getStatusBadge = (status: TaskStatus): string => {
  if (status === 'DONE') return 'bg-emerald-50 text-emerald-700';
  if (status === 'BLOCKED') return 'bg-rose-50 text-rose-700';
  if (status === 'RUNNING') return 'bg-indigo-50 text-indigo-700';
  return 'bg-slate-100 text-slate-600';
};

const getCaseResultBadge = (status: CaseResult): string => {
  if (status === 'PASSED') return 'bg-emerald-50 text-emerald-700';
  if (status === 'FAILED') return 'bg-rose-50 text-rose-700';
  return 'bg-slate-100 text-slate-600';
};

const getStepBadge = (status: StepStatus): string => {
  if (status === 'PASSED') return 'bg-emerald-50 text-emerald-700';
  if (status === 'FAILED') return 'bg-rose-50 text-rose-700';
  return 'bg-slate-100 text-slate-600';
};

const getTaskProgress = (task: BoardTask): number => {
  if (task.type === 'AUTOMATION') {
    const total = task.automationSteps.length;
    if (total === 0) return 0;
    const done = task.automationSteps.filter(step => step.status !== 'PENDING').length;
    return Math.round((done / total) * 100);
  }

  const total = task.caseIds.length;
  if (total === 0) return 0;
  const done = task.caseIds.filter(caseId => task.caseResults[caseId] && task.caseResults[caseId] !== 'PENDING').length;
  return Math.round((done / total) * 100);
};

const resolveManualStatus = (task: BoardTask): TaskStatus => {
  const results = task.caseIds.map(caseId => task.caseResults[caseId] || 'PENDING');
  const hasFailed = results.includes('FAILED');
  const allFinished = results.length > 0 && results.every(result => result !== 'PENDING');

  if (hasFailed) return 'BLOCKED';
  if (allFinished) return 'DONE';
  if (results.some(result => result !== 'PENDING')) return 'RUNNING';
  return task.status === 'DONE' ? 'PLANNED' : task.status;
};

const resolveAutomationStatus = (task: BoardTask): TaskStatus => {
  const steps = task.automationSteps;
  if (steps.length === 0) return 'PLANNED';

  const hasFailed = steps.some(step => step.status === 'FAILED');
  const allFinished = steps.every(step => step.status !== 'PENDING');
  const hasStarted = steps.some(step => step.status !== 'PENDING');

  if (hasFailed) return 'BLOCKED';
  if (allFinished) return 'DONE';
  if (hasStarted) return 'RUNNING';
  return task.status === 'DONE' ? 'PLANNED' : task.status;
};

const seedAutomationSteps = () => [
  { id: generateId('step'), title: '环境准备', detail: '准备测试环境和依赖服务' },
  { id: generateId('step'), title: '执行脚本', detail: '触发自动化脚本主流程' },
  { id: generateId('step'), title: '结果归档', detail: '汇总报告并归档日志' },
];

const defaultNewTaskForm = (): NewTaskForm => ({
  title: '',
  description: '',
  assigneeId: '',
  type: 'MANUAL',
  caseIds: [],
  automationSteps: seedAutomationSteps(),
});

export const TestTaskBoard: React.FC<TestTaskBoardProps> = ({
  currentUser,
  users,
  testCases,
  availableNavViews,
  onNavigateToReqList,
  onNavigateToCaseList,
  onNavigateToMyTasks,
  onNavigateToDutMgmt,
  onNavigateToUserMgmt,
  onNavigateToNavMgmt,
  onLogout,
  showUserProfile,
  onToggleUserProfile,
}) => {
  const canAccessReqList = availableNavViews.includes('req_list');
  const canAccessCaseList = availableNavViews.includes('case_list');
  const canAccessMyTasks = availableNavViews.includes('my_tasks');
  const canAccessDutMgmt = availableNavViews.includes('dut_mgmt');
  const canAccessUserMgmt = availableNavViews.includes('user_mgmt');
  const canAccessNavMgmt = availableNavViews.includes('nav_mgmt');

  const [tasks, setTasks] = useState<BoardTask[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [showExecutionBoard, setShowExecutionBoard] = useState(false);
  const [form, setForm] = useState<NewTaskForm>(defaultNewTaskForm());

  const userMap = useMemo(() => {
    const row = new Map<string, UserType>();
    users.forEach(user => {
      row.set(user.user_id, user);
    });
    return row;
  }, [users]);

  const caseMap = useMemo(() => {
    const row = new Map<string, TestCase>();
    testCases.forEach(item => {
      row.set(item.case_id, item);
    });
    return row;
  }, [testCases]);

  const boardStats = useMemo(() => {
    const total = tasks.length;
    const running = tasks.filter(task => task.status === 'RUNNING').length;
    const blocked = tasks.filter(task => task.status === 'BLOCKED').length;
    const done = tasks.filter(task => task.status === 'DONE').length;
    return { total, running, blocked, done };
  }, [tasks]);

  const groupedTasks = useMemo(() => {
    return {
      PLANNED: tasks.filter(task => task.status === 'PLANNED'),
      RUNNING: tasks.filter(task => task.status === 'RUNNING'),
      BLOCKED: tasks.filter(task => task.status === 'BLOCKED'),
      DONE: tasks.filter(task => task.status === 'DONE'),
    };
  }, [tasks]);

  const activeTask = useMemo(
    () => (activeTaskId ? tasks.find(task => task.id === activeTaskId) || null : null),
    [activeTaskId, tasks]
  );

  const toggleCaseSelection = (caseId: string) => {
    setForm(prev => {
      const has = prev.caseIds.includes(caseId);
      return {
        ...prev,
        caseIds: has ? prev.caseIds.filter(id => id !== caseId) : [...prev.caseIds, caseId],
      };
    });
  };

  const updateStepField = (id: string, field: 'title' | 'detail', value: string) => {
    setForm(prev => ({
      ...prev,
      automationSteps: prev.automationSteps.map(step =>
        step.id === id ? { ...step, [field]: value } : step
      ),
    }));
  };

  const addStep = () => {
    setForm(prev => ({
      ...prev,
      automationSteps: [
        ...prev.automationSteps,
        { id: generateId('step'), title: `步骤 ${prev.automationSteps.length + 1}`, detail: '' },
      ],
    }));
  };

  const removeStep = (id: string) => {
    setForm(prev => ({
      ...prev,
      automationSteps: prev.automationSteps.filter(step => step.id !== id),
    }));
  };

  const resetCreateForm = () => {
    setForm(defaultNewTaskForm());
  };

  const createTask = () => {
    if (!form.title.trim()) {
      alert('请输入任务标题');
      return;
    }
    if (!form.assigneeId) {
      alert('请选择测试人');
      return;
    }
    if (form.caseIds.length === 0) {
      alert('请至少勾选一个测试用例');
      return;
    }
    if (form.type === 'AUTOMATION' && form.automationSteps.length === 0) {
      alert('自动化任务至少需要一个执行步骤');
      return;
    }

    const taskId = generateId('ttb');
    const createdAt = now();
    const caseResults = form.caseIds.reduce<Record<string, CaseResult>>((acc, caseId) => {
      acc[caseId] = 'PENDING';
      return acc;
    }, {});

    const createdTask: BoardTask = {
      id: taskId,
      title: form.title.trim(),
      description: form.description.trim(),
      assigneeId: form.assigneeId,
      creatorId: currentUser?.user_id || 'unknown',
      type: form.type,
      status: 'PLANNED',
      caseIds: form.caseIds,
      caseResults,
      automationSteps: form.type === 'AUTOMATION'
        ? form.automationSteps.map(step => ({ ...step, status: 'PENDING' as StepStatus }))
        : [],
      logs: [buildLog('任务创建成功')],
      createdAt,
      updatedAt: createdAt,
    };

    setTasks(prev => [createdTask, ...prev]);
    setActiveTaskId(taskId);
    setShowExecutionBoard(true);
    setShowCreateModal(false);
    resetCreateForm();
  };

  const updateTask = (taskId: string, updater: (task: BoardTask) => BoardTask) => {
    setTasks(prev => prev.map(task => {
      if (task.id !== taskId) return task;
      const updated = updater(task);
      return { ...updated, updatedAt: now() };
    }));
  };

  const pushTaskLog = (task: BoardTask, message: string, level: TaskLog['level'] = 'INFO'): BoardTask => ({
    ...task,
    logs: [buildLog(message, level), ...task.logs],
  });

  const startTask = (taskId: string) => {
    updateTask(taskId, task => {
      const next = pushTaskLog(task, '任务已启动');
      return { ...next, status: 'RUNNING' };
    });
  };

  const updateManualCaseResult = (taskId: string, caseId: string, result: CaseResult) => {
    updateTask(taskId, task => {
      const next: BoardTask = {
        ...task,
        caseResults: { ...task.caseResults, [caseId]: result },
      };
      const status = resolveManualStatus(next);
      const caseTitle = caseMap.get(caseId)?.title || caseId;
      const message = result === 'PENDING'
        ? `重置用例【${caseTitle}】为待执行`
        : `用例【${caseTitle}】执行结果：${result === 'PASSED' ? '通过' : '失败'}`;
      const withLog = pushTaskLog(next, message, result === 'FAILED' ? 'WARN' : 'INFO');
      return { ...withLog, status };
    });
  };

  const executeNextAutoStep = (taskId: string, isSuccess: boolean) => {
    updateTask(taskId, task => {
      const nextStep = task.automationSteps.find(step => step.status === 'PENDING');
      if (!nextStep) {
        return pushTaskLog(task, '自动化步骤已全部执行完毕');
      }

      const updatedSteps = task.automationSteps.map(step => {
        if (step.id !== nextStep.id) return step;
        return { ...step, status: isSuccess ? 'PASSED' : 'FAILED' };
      });

      const nextTask = { ...task, automationSteps: updatedSteps };
      const status = resolveAutomationStatus(nextTask);
      const withLog = pushTaskLog(
        nextTask,
        `步骤【${nextStep.title}】执行${isSuccess ? '通过' : '失败'}`,
        isSuccess ? 'INFO' : 'ERROR'
      );
      return { ...withLog, status };
    });
  };

  const retryFailedStep = (taskId: string) => {
    updateTask(taskId, task => {
      const failed = task.automationSteps.find(step => step.status === 'FAILED');
      if (!failed) {
        return pushTaskLog(task, '当前无失败步骤可重试');
      }

      const updatedSteps = task.automationSteps.map(step =>
        step.id === failed.id ? { ...step, status: 'PENDING' as StepStatus } : step
      );
      const nextTask = { ...task, automationSteps: updatedSteps, status: 'RUNNING' as TaskStatus };
      return pushTaskLog(nextTask, `步骤【${failed.title}】已重置为待执行`);
    });
  };

  const openTaskBoard = (taskId: string, startExecution: boolean = false) => {
    if (startExecution) {
      startTask(taskId);
    }
    setActiveTaskId(taskId);
    setShowExecutionBoard(true);
  };

  const closeTaskBoard = () => {
    setShowExecutionBoard(false);
    setActiveTaskId(null);
  };

  const statusColumns: Array<{ key: TaskStatus; title: string; hint: string }> = [
    { key: 'PLANNED', title: '待开始', hint: '任务已创建，等待执行' },
    { key: 'RUNNING', title: '执行中', hint: '任务正在推进' },
    { key: 'BLOCKED', title: '阻塞', hint: '存在失败项，需要处理' },
    { key: 'DONE', title: '已完成', hint: '已结束并产出结果' },
  ];

  const activeTaskProgress = activeTask ? getTaskProgress(activeTask) : 0;
  const activeTaskAssignee = activeTask ? userMap.get(activeTask.assigneeId) : null;
  const activeTaskFinishedCases = activeTask
    ? activeTask.caseIds.filter(caseId => (activeTask.caseResults[caseId] || 'PENDING') !== 'PENDING').length
    : 0;
  const activeTaskFailedSteps = activeTask
    ? activeTask.automationSteps.filter(step => step.status === 'FAILED').length
    : 0;
  const activeTaskPendingSteps = activeTask
    ? activeTask.automationSteps.filter(step => step.status === 'PENDING').length
    : 0;

  return (
    <div className="min-h-screen bg-[#F8F9FA] flex">
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-6 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-slate-900 rounded-xl flex items-center justify-center shadow-lg shadow-slate-900/20">
              <FileText size={22} className="text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900">Test Designer</h1>
              <p className="text-[10px] text-slate-400">服务器测试平台</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {canAccessReqList && (
            <button
              onClick={onNavigateToReqList}
              className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors"
            >
              <FileText size={18} />
              测试需求
            </button>
          )}
          {canAccessCaseList && (
            <button
              onClick={onNavigateToCaseList}
              className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors"
            >
              <PlayCircle size={18} />
              测试用例
            </button>
          )}
          {canAccessMyTasks && (
            <button
              onClick={onNavigateToMyTasks}
              className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors"
            >
              <ListTodo size={18} />
              我的任务
            </button>
          )}
          <button
            onClick={() => {}}
            className="w-full flex items-center gap-3 px-4 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold shadow-lg shadow-slate-900/20"
          >
            <LayoutDashboard size={18} />
            测试看板
          </button>
          {canAccessDutMgmt && (
            <button
              onClick={onNavigateToDutMgmt}
              className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors"
            >
              <Server size={18} />
              DUT 设备
            </button>
          )}
          {canAccessUserMgmt && (
            <button
              onClick={onNavigateToUserMgmt}
              className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors"
            >
              <User size={18} />
              用户管理
            </button>
          )}
          {canAccessNavMgmt && (
            <button
              onClick={onNavigateToNavMgmt}
              className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors"
            >
              <Shield size={18} />
              导航管理
            </button>
          )}
        </nav>

        <div className="p-4 border-t border-slate-100">
          {currentUser && (
            <>
              <button
                onClick={onToggleUserProfile}
                className="w-full flex items-center gap-3 p-3 bg-slate-50 rounded-xl mb-3 hover:bg-slate-100 transition-colors cursor-pointer group"
              >
                <div className="w-9 h-9 bg-indigo-100 rounded-lg flex items-center justify-center group-hover:bg-indigo-200 transition-colors">
                  <User size={16} className="text-indigo-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-slate-700 truncate">{currentUser.username}</div>
                  <div className="text-[10px] text-slate-400">{currentUser.role_ids[0] === 'ROLE_TPM' ? '测试经理' : '测试工程师'}</div>
                </div>
              </button>

              {showUserProfile && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                  <div className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm" onClick={onToggleUserProfile} />
                  <div className="relative w-full max-w-md bg-white rounded-3xl shadow-2xl overflow-hidden">
                    <div className="px-6 py-5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white">
                      <div className="flex items-center justify-between">
                        <h2 className="text-lg font-bold">个人信息</h2>
                        <button onClick={onToggleUserProfile} className="p-1 hover:bg-white/20 rounded-lg transition-colors">
                          <X size={20} />
                        </button>
                      </div>
                    </div>

                    <div className="p-6 space-y-5">
                      <div className="flex items-center gap-4">
                        <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center">
                          <User size={32} className="text-indigo-600" />
                        </div>
                        <div>
                          <div className="text-xl font-bold text-slate-900">{currentUser.username}</div>
                          <div className="text-sm text-slate-500">
                            {currentUser.role_ids[0] === 'ROLE_TPM' ? '测试经理' : '测试工程师'}
                          </div>
                          <span className={`inline-flex items-center mt-2 px-2 py-0.5 rounded-lg text-xs font-bold ${
                            currentUser.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-400'
                          }`}>
                            {currentUser.status === 'ACTIVE' ? '已启用' : '已禁用'}
                          </span>
                        </div>
                      </div>

                      <div className="space-y-3 pt-4 border-t border-slate-100">
                        <div className="flex items-center gap-3 text-sm">
                          <Mail size={16} className="text-slate-400" />
                          <div>
                            <div className="text-xs text-slate-400">邮箱地址</div>
                            <div className="font-medium text-slate-700">{currentUser.email}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 text-sm">
                          <Shield size={16} className="text-slate-400" />
                          <div>
                            <div className="text-xs text-slate-400">用户角色</div>
                            <div className="flex gap-1.5 mt-1">
                              {currentUser.role_ids.map(rid => (
                                <span key={rid} className="px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded text-xs font-bold">
                                  {ROLES.find(r => r.id === rid)?.name || rid}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 text-sm">
                          <Calendar size={16} className="text-slate-400" />
                          <div>
                            <div className="text-xs text-slate-400">创建时间</div>
                            <div className="font-medium text-slate-700">{currentUser.created_at}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          <button
            onClick={onLogout}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-slate-500 hover:bg-rose-50 hover:text-rose-600 rounded-xl text-sm font-bold transition-colors"
          >
            <LogIn size={16} className="rotate-180" />
            退出登录
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <div className="p-8 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h1 className="text-2xl font-bold text-slate-900">测试任务看板</h1>
                <p className="text-sm text-slate-500 mt-1">创建测试任务、分派执行人、追踪手动/自动化执行进度与日志</p>
              </div>
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 text-white text-sm font-bold hover:bg-slate-800 transition-colors"
              >
                <Plus size={16} /> 新建测试任务
              </button>
            </div>

            <div className="mt-5 grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="rounded-xl bg-slate-50 border border-slate-100 p-3">
                <div className="text-xs text-slate-500">任务总数</div>
                <div className="text-xl font-bold text-slate-900 mt-1">{boardStats.total}</div>
              </div>
              <div className="rounded-xl bg-indigo-50 border border-indigo-100 p-3">
                <div className="text-xs text-indigo-600">执行中</div>
                <div className="text-xl font-bold text-indigo-700 mt-1">{boardStats.running}</div>
              </div>
              <div className="rounded-xl bg-rose-50 border border-rose-100 p-3">
                <div className="text-xs text-rose-600">阻塞</div>
                <div className="text-xl font-bold text-rose-700 mt-1">{boardStats.blocked}</div>
              </div>
              <div className="rounded-xl bg-emerald-50 border border-emerald-100 p-3">
                <div className="text-xs text-emerald-600">已完成</div>
                <div className="text-xl font-bold text-emerald-700 mt-1">{boardStats.done}</div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
            {statusColumns.map(column => (
              <section key={column.key} className="bg-white rounded-2xl border border-slate-100 shadow-sm min-h-[360px]">
                <header className="px-4 py-3 border-b border-slate-100">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-bold text-slate-900">{column.title}</h2>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-lg bg-slate-100 text-slate-600">
                      {groupedTasks[column.key].length}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">{column.hint}</p>
                </header>

                <div className="p-3 space-y-3">
                  {groupedTasks[column.key].length === 0 && (
                    <div className="text-xs text-slate-400 bg-slate-50 rounded-xl px-3 py-4 text-center">暂无任务</div>
                  )}

                  {groupedTasks[column.key].map(task => {
                    const progress = getTaskProgress(task);
                    const assignee = userMap.get(task.assigneeId);
                    const totalCases = task.caseIds.length;
                    const totalLogs = task.logs.length;

                    return (
                      <article key={task.id} className="border border-slate-100 rounded-xl p-3 bg-white shadow-sm">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-sm font-bold text-slate-900 break-all">{task.title}</div>
                            <div className="mt-1 flex flex-wrap gap-1.5">
                              <span className={`text-[11px] font-bold px-2 py-0.5 rounded-lg ${getStatusBadge(task.status)}`}>
                                {task.status}
                              </span>
                              <span className="text-[11px] font-bold px-2 py-0.5 rounded-lg bg-indigo-50 text-indigo-700">
                                {task.type === 'AUTOMATION' ? '自动化' : '手动'}
                              </span>
                            </div>
                          </div>
                          <div className="text-[11px] text-slate-400">#{task.id}</div>
                        </div>

                        <div className="mt-3">
                          <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
                            <span>进度</span>
                            <span>{progress}%</span>
                          </div>
                          <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full bg-indigo-500" style={{ width: `${progress}%` }} />
                          </div>
                        </div>

                        <div className="mt-3 text-xs text-slate-500 space-y-1">
                          <div className="flex items-center gap-2">
                            <User size={14} />
                            <span>测试人：{assignee?.username || task.assigneeId}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Clock3 size={14} />
                            <span>更新时间：{formatDateTime(task.updatedAt)}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <ListTodo size={14} />
                            <span>用例：{totalCases}，日志：{totalLogs}</span>
                          </div>
                        </div>

                        <div className="mt-3 flex flex-wrap gap-2">
                          <button
                            onClick={() => openTaskBoard(task.id)}
                            className="px-2.5 py-1.5 text-xs font-bold rounded-lg bg-slate-100 text-slate-700"
                          >
                            查看测试任务
                          </button>
                          <button
                            onClick={() => openTaskBoard(task.id, task.status === 'PLANNED' || task.status === 'BLOCKED')}
                            className="px-2.5 py-1.5 text-xs font-bold rounded-lg bg-slate-900 text-white"
                          >
                            执行测试任务
                          </button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        </div>
      </main>

      {showExecutionBoard && activeTask && (
        <div className="fixed inset-0 z-[125] p-4">
          <div className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm" onClick={closeTaskBoard} />
          <div className="relative h-full w-full max-w-[1680px] mx-auto bg-white rounded-3xl border border-slate-100 shadow-2xl overflow-hidden flex flex-col">
            <header className="px-6 py-4 border-b border-slate-100 bg-slate-50">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-xl font-bold text-slate-900">{activeTask.title}</h2>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-lg ${getStatusBadge(activeTask.status)}`}>
                      {activeTask.status}
                    </span>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-lg bg-indigo-50 text-indigo-700">
                      {activeTask.type === 'AUTOMATION' ? '自动化' : '手动'}
                    </span>
                  </div>
                  <div className="text-sm text-slate-500 mt-1">
                    任务编号：<span className="font-mono">{activeTask.id}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {(activeTask.status === 'PLANNED' || activeTask.status === 'BLOCKED') && (
                    <button
                      onClick={() => startTask(activeTask.id)}
                      className="px-3 py-2 text-sm font-bold rounded-xl bg-slate-900 text-white"
                    >
                      启动任务
                    </button>
                  )}
                  <button
                    onClick={closeTaskBoard}
                    className="p-2 rounded-xl text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                    aria-label="关闭大看板"
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>

              <div className="mt-3 grid grid-cols-2 lg:grid-cols-6 gap-3">
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                  <div className="text-[11px] text-slate-400">测试人</div>
                  <div className="text-sm font-semibold text-slate-800 mt-0.5">{activeTaskAssignee?.username || activeTask.assigneeId}</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                  <div className="text-[11px] text-slate-400">进度</div>
                  <div className="text-sm font-semibold text-slate-800 mt-0.5">{activeTaskProgress}%</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                  <div className="text-[11px] text-slate-400">测试用例</div>
                  <div className="text-sm font-semibold text-slate-800 mt-0.5">{activeTask.caseIds.length}</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                  <div className="text-[11px] text-slate-400">已执行用例</div>
                  <div className="text-sm font-semibold text-slate-800 mt-0.5">{activeTaskFinishedCases}</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                  <div className="text-[11px] text-slate-400">自动化失败步骤</div>
                  <div className="text-sm font-semibold text-slate-800 mt-0.5">{activeTaskFailedSteps}</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                  <div className="text-[11px] text-slate-400">最近更新时间</div>
                  <div className="text-sm font-semibold text-slate-800 mt-0.5">{formatDateTime(activeTask.updatedAt)}</div>
                </div>
              </div>
            </header>

            <div className="flex-1 overflow-auto p-6 grid grid-cols-1 xl:grid-cols-12 gap-6">
              <section className="xl:col-span-8 space-y-4">
                <div className="bg-white border border-slate-100 rounded-2xl p-4">
                  <div className="flex items-center justify-between text-sm text-slate-500 mb-2">
                    <span>任务总体进度</span>
                    <span>{activeTaskProgress}%</span>
                  </div>
                  <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-indigo-500 transition-all" style={{ width: `${activeTaskProgress}%` }} />
                  </div>
                  {activeTask.description && (
                    <div className="mt-3 text-sm text-slate-600 whitespace-pre-wrap bg-slate-50 rounded-xl p-3">
                      {activeTask.description}
                    </div>
                  )}
                </div>

                {activeTask.type === 'AUTOMATION' ? (
                  <div className="bg-white border border-slate-100 rounded-2xl p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                      <h3 className="text-base font-bold text-slate-900">自动化执行大看板</h3>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => executeNextAutoStep(activeTask.id, true)}
                          className="px-3 py-1.5 text-xs font-bold rounded-lg bg-emerald-50 text-emerald-700"
                        >
                          下一步通过
                        </button>
                        <button
                          onClick={() => executeNextAutoStep(activeTask.id, false)}
                          className="px-3 py-1.5 text-xs font-bold rounded-lg bg-rose-50 text-rose-700"
                        >
                          下一步失败
                        </button>
                        <button
                          onClick={() => retryFailedStep(activeTask.id)}
                          className="px-3 py-1.5 text-xs font-bold rounded-lg bg-amber-50 text-amber-700"
                          disabled={activeTaskFailedSteps === 0}
                        >
                          重试失败步骤
                        </button>
                      </div>
                    </div>
                    <div className="text-xs text-slate-500 mb-3">待执行步骤：{activeTaskPendingSteps}</div>
                    <div className="space-y-2">
                      {activeTask.automationSteps.map((step, index) => (
                        <div key={step.id} className="border border-slate-100 rounded-xl p-3">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="text-sm font-semibold text-slate-800">步骤 {index + 1}：{step.title}</div>
                              {step.detail && <div className="text-xs text-slate-500 mt-1">{step.detail}</div>}
                            </div>
                            <span className={`text-[11px] font-bold px-2 py-0.5 rounded-lg ${getStepBadge(step.status)}`}>
                              {step.status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="bg-white border border-slate-100 rounded-2xl p-4">
                    <h3 className="text-base font-bold text-slate-900 mb-3">手动测试执行大看板</h3>
                    <div className="space-y-2 max-h-[52vh] overflow-auto pr-1">
                      {activeTask.caseIds.map(caseId => {
                        const caseItem = caseMap.get(caseId);
                        const result = activeTask.caseResults[caseId] || 'PENDING';
                        return (
                          <div key={caseId} className="border border-slate-100 rounded-xl p-3">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <div className="text-sm font-semibold text-slate-800">{caseItem?.title || caseId}</div>
                                <div className="text-xs text-slate-500 mt-1">
                                  用例编号：<span className="font-mono text-indigo-600">{caseId}</span>
                                </div>
                              </div>
                              <span className={`text-[11px] font-bold px-2 py-0.5 rounded-lg ${getCaseResultBadge(result)}`}>
                                {result}
                              </span>
                            </div>
                            <div className="mt-3 flex flex-wrap gap-2">
                              <button
                                onClick={() => updateManualCaseResult(activeTask.id, caseId, 'PASSED')}
                                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg bg-emerald-50 text-emerald-700 font-bold"
                              >
                                <CheckCircle2 size={12} /> 通过
                              </button>
                              <button
                                onClick={() => updateManualCaseResult(activeTask.id, caseId, 'FAILED')}
                                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg bg-rose-50 text-rose-700 font-bold"
                              >
                                <XCircle size={12} /> 失败
                              </button>
                              <button
                                onClick={() => updateManualCaseResult(activeTask.id, caseId, 'PENDING')}
                                className="px-2.5 py-1.5 text-xs rounded-lg bg-slate-100 text-slate-600 font-bold"
                              >
                                重置
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </section>

              <aside className="xl:col-span-4 space-y-4">
                <div className="bg-white border border-slate-100 rounded-2xl p-4">
                  <h3 className="text-base font-bold text-slate-900 mb-2">测试日志</h3>
                  <div className="text-xs text-slate-500 mb-3">共 {activeTask.logs.length} 条</div>
                  <div className="space-y-2 max-h-[64vh] overflow-auto pr-1">
                    {activeTask.logs.length === 0 && (
                      <div className="text-xs text-slate-400">暂无日志</div>
                    )}
                    {activeTask.logs.map(log => (
                      <div key={log.id} className="text-xs bg-slate-50 border border-slate-100 rounded-lg p-2">
                        <div className="font-mono text-[11px] text-slate-400">{formatDateTime(log.timestamp)}</div>
                        <div className={`mt-1 font-bold ${log.level === 'ERROR' ? 'text-rose-600' : log.level === 'WARN' ? 'text-amber-600' : 'text-indigo-600'}`}>
                          [{log.level}]
                        </div>
                        <div className="mt-1 text-slate-600">{log.message}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </aside>
            </div>
          </div>
        </div>
      )}

      {showCreateModal && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm" onClick={() => setShowCreateModal(false)} />
          <div className="relative w-full max-w-4xl max-h-[90vh] overflow-hidden bg-white rounded-3xl shadow-2xl border border-slate-100">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <h3 className="text-base font-bold text-slate-900">新建测试任务</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                aria-label="关闭"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-auto max-h-[calc(90vh-68px)]">
              <section className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-500 mb-1">任务标题</label>
                  <input
                    value={form.title}
                    onChange={event => setForm(prev => ({ ...prev, title: event.target.value }))}
                    placeholder="例如：3.2版本冒烟回归"
                    className="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-500 mb-1">本次测试描述</label>
                  <textarea
                    value={form.description}
                    onChange={event => setForm(prev => ({ ...prev, description: event.target.value }))}
                    rows={4}
                    placeholder="输入测试目标、范围、风险点"
                    className="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 resize-none"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-500 mb-1">指派测试人</label>
                    <select
                      value={form.assigneeId}
                      onChange={event => setForm(prev => ({ ...prev, assigneeId: event.target.value }))}
                      className="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100"
                    >
                      <option value="">请选择</option>
                      {users.filter(user => user.status === 'ACTIVE').map(user => (
                        <option key={user.user_id} value={user.user_id}>
                          {user.username} ({user.user_id})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-500 mb-1">执行方式</label>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setForm(prev => ({ ...prev, type: 'MANUAL' }))}
                        className={`flex-1 px-3 py-2.5 rounded-xl text-sm font-bold border ${
                          form.type === 'MANUAL' ? 'bg-slate-900 text-white border-slate-900' : 'bg-white text-slate-600 border-slate-200'
                        }`}
                      >
                        手动
                      </button>
                      <button
                        onClick={() => setForm(prev => ({ ...prev, type: 'AUTOMATION' }))}
                        className={`flex-1 px-3 py-2.5 rounded-xl text-sm font-bold border ${
                          form.type === 'AUTOMATION' ? 'bg-slate-900 text-white border-slate-900' : 'bg-white text-slate-600 border-slate-200'
                        }`}
                      >
                        自动化
                      </button>
                    </div>
                  </div>
                </div>

                {form.type === 'AUTOMATION' && (
                  <div className="border border-slate-100 rounded-xl p-3 bg-slate-50/60">
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-xs font-bold text-slate-600">自动化分步骤</label>
                      <button onClick={addStep} className="text-xs font-bold text-indigo-600">+ 添加步骤</button>
                    </div>
                    <div className="space-y-2 max-h-64 overflow-auto pr-1">
                      {form.automationSteps.map(step => (
                        <div key={step.id} className="rounded-lg border border-slate-200 bg-white p-2">
                          <div className="flex items-center gap-2">
                            <input
                              value={step.title}
                              onChange={event => updateStepField(step.id, 'title', event.target.value)}
                              placeholder="步骤标题"
                              className="flex-1 px-2.5 py-1.5 text-sm border border-slate-200 rounded"
                            />
                            <button
                              onClick={() => removeStep(step.id)}
                              className="text-xs text-rose-500 px-2 py-1"
                              disabled={form.automationSteps.length <= 1}
                            >
                              删除
                            </button>
                          </div>
                          <input
                            value={step.detail}
                            onChange={event => updateStepField(step.id, 'detail', event.target.value)}
                            placeholder="步骤说明"
                            className="w-full mt-2 px-2.5 py-1.5 text-sm border border-slate-200 rounded"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>

              <section>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-bold text-slate-500">勾选测试用例（{form.caseIds.length}）</label>
                  <span className="text-[11px] text-slate-400">可多选</span>
                </div>
                <div className="border border-slate-100 rounded-xl overflow-hidden bg-white">
                  <div className="max-h-[420px] overflow-auto divide-y divide-slate-100">
                    {testCases.length === 0 && (
                      <div className="p-4 text-sm text-slate-400 text-center">当前没有可选测试用例</div>
                    )}
                    {testCases.map(item => {
                      const checked = form.caseIds.includes(item.case_id);
                      return (
                        <label key={item.case_id} className="flex items-start gap-3 p-3 hover:bg-slate-50 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleCaseSelection(item.case_id)}
                            className="mt-1"
                          />
                          <div className="min-w-0">
                            <div className="text-sm font-semibold text-slate-800 truncate">{item.title || item.case_id}</div>
                            <div className="text-[11px] text-slate-500 mt-0.5 break-all">
                              <span className="font-mono text-indigo-600">{item.case_id}</span>
                              <span className="ml-2">状态：{item.status}</span>
                            </div>
                          </div>
                        </label>
                      );
                    })}
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-end gap-2">
                  <button
                    onClick={() => {
                      setShowCreateModal(false);
                      resetCreateForm();
                    }}
                    className="px-4 py-2 text-sm font-semibold border border-slate-200 rounded-xl text-slate-600 hover:bg-slate-50"
                  >
                    取消
                  </button>
                  <button
                    onClick={createTask}
                    className="px-4 py-2 text-sm font-bold rounded-xl bg-slate-900 text-white hover:bg-slate-800"
                  >
                    创建任务
                  </button>
                </div>
              </section>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
