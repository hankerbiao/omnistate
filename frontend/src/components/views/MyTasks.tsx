import React, { useEffect, useMemo, useState } from 'react';
import {
  Calendar,
  FileText,
  ListTodo,
  LogIn,
  Mail,
  PlayCircle,
  Search,
  Shield,
  LayoutDashboard,
  Server,
  User,
  X,
} from 'lucide-react';
import { WorkItem, WorkItemState, WorkItemType } from '../../types';
import { User as UserType, ROLES } from '../../constants/config';
import { isBackendEnabled, testDesignerApi } from '../../services/api';

interface MyTasksProps {
  currentUser: UserType | null;
  availableNavViews: string[];
  onNavigateToReqList: () => void;
  onNavigateToCaseList: () => void;
  onNavigateToTaskBoard: () => void;
  onNavigateToDutMgmt: () => void;
  onNavigateToUserMgmt: () => void;
  onNavigateToNavMgmt: () => void;
  onLogout: () => void;
  showUserProfile: boolean;
  onToggleUserProfile: () => void;
}

const asObject = (value: unknown): Record<string, unknown> =>
  value && typeof value === 'object' ? (value as Record<string, unknown>) : {};

const extractList = (input: unknown): unknown[] => {
  if (Array.isArray(input)) return input;
  const row = asObject(input);
  if (Array.isArray(row.items)) return row.items;
  if (Array.isArray(row.results)) return row.results;
  if (Array.isArray(row.data)) return row.data;
  return [];
};

const unwrapApiData = <T,>(payload: T | { data?: T } | null | undefined): T | undefined => {
  if (payload && typeof payload === 'object' && 'data' in payload) {
    return (payload as { data?: T }).data;
  }
  return payload as T | undefined;
};

const normalizeWorkItemType = (value: unknown): WorkItemType => {
  if (value === WorkItemType.REQUIREMENT) return WorkItemType.REQUIREMENT;
  if (value === WorkItemType.TEST_CASE) return WorkItemType.TEST_CASE;
  return WorkItemType.REQUIREMENT;
};

const normalizeWorkItemState = (value: unknown): WorkItemState => {
  if ((Object.values(WorkItemState) as unknown[]).includes(value)) {
    return value as WorkItemState;
  }
  return WorkItemState.DRAFT;
};

const normalizeWorkItem = (item: unknown): WorkItem => {
  const row = asObject(item);
  return {
    item_id: String(row.item_id || ''),
    type_code: normalizeWorkItemType(row.type_code),
    title: String(row.title || ''),
    content: String(row.content || ''),
    current_state: normalizeWorkItemState(row.current_state),
    current_owner_id: String(row.current_owner_id || ''),
    creator_id: String(row.creator_id || ''),
    parent_item_id: row.parent_item_id ? String(row.parent_item_id) : undefined,
    is_deleted: Boolean(row.is_deleted ?? false),
    form_data: asObject(row.form_data),
    created_at: String(row.created_at || ''),
    updated_at: String(row.updated_at || ''),
  };
};

const getStateClass = (state: string): string => {
  if (state.includes('RELEASED') || state.includes('DONE')) return 'bg-emerald-50 text-emerald-700';
  if (state.includes('REVIEW') || state.includes('UAT')) return 'bg-amber-50 text-amber-700';
  if (state.includes('DEVELOP')) return 'bg-blue-50 text-blue-700';
  if (state.includes('DRAFT')) return 'bg-slate-100 text-slate-700';
  return 'bg-indigo-50 text-indigo-700';
};

const formatDateTime = (value: string): string => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
};

export const MyTasks: React.FC<MyTasksProps> = ({
  currentUser,
  availableNavViews,
  onNavigateToReqList,
  onNavigateToCaseList,
  onNavigateToTaskBoard,
  onNavigateToDutMgmt,
  onNavigateToUserMgmt,
  onNavigateToNavMgmt,
  onLogout,
  showUserProfile,
  onToggleUserProfile,
}) => {
  const canAccessReqList = availableNavViews.includes('req_list');
  const canAccessCaseList = availableNavViews.includes('case_list');
  const canAccessTaskBoard = availableNavViews.includes('test_task_board');
  const canAccessDutMgmt = availableNavViews.includes('dut_mgmt');
  const canAccessUserMgmt = availableNavViews.includes('user_mgmt');
  const canAccessNavMgmt = availableNavViews.includes('nav_mgmt');

  const [tasks, setTasks] = useState<WorkItem[]>([]);
  const [searchText, setSearchText] = useState('');
  const [selectedState, setSelectedState] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    const ownerId = currentUser?.user_id;
    if (!ownerId) {
      setTasks([]);
      return;
    }

    if (!isBackendEnabled || !testDesignerApi) {
      setErrorMessage('后端未启用，无法加载我的任务。');
      setTasks([]);
      return;
    }

    let mounted = true;
    const loadMyTasks = async () => {
      setIsLoading(true);
      setErrorMessage('');
      try {
        const response = await testDesignerApi.listWorkItems({
          owner_id: ownerId,
          limit: 100,
          offset: 0,
        });
        const payload = unwrapApiData(response);
        const rows = extractList(payload);
        const normalized = rows.map(normalizeWorkItem).filter(item => item.item_id);
        if (mounted) {
          setTasks(normalized);
        }
      } catch (error: any) {
        if (mounted) {
          setTasks([]);
          setErrorMessage(error?.message || '加载我的任务失败');
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    void loadMyTasks();
    return () => {
      mounted = false;
    };
  }, [currentUser?.user_id, reloadTick]);

  const stateOptions = useMemo(() => {
    return Array.from(new Set(tasks.map(item => item.current_state))).filter(Boolean).sort();
  }, [tasks]);

  const filteredTasks = useMemo(() => {
    return tasks.filter(item => {
      if (selectedState && item.current_state !== selectedState) {
        return false;
      }
      if (!searchText) {
        return true;
      }
      const search = searchText.toLowerCase();
      return (
        item.item_id.toLowerCase().includes(search) ||
        item.title.toLowerCase().includes(search) ||
        item.type_code.toLowerCase().includes(search) ||
        item.current_state.toLowerCase().includes(search) ||
        item.creator_id.toLowerCase().includes(search)
      );
    });
  }, [tasks, searchText, selectedState]);

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
          <button
            onClick={() => {}}
            className="w-full flex items-center gap-3 px-4 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold shadow-lg shadow-slate-900/20"
          >
            <ListTodo size={18} />
            我的任务
          </button>
          {canAccessTaskBoard && (
            <button
              onClick={onNavigateToTaskBoard}
              className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors"
            >
              <LayoutDashboard size={18} />
              测试看板
            </button>
          )}
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
        <div className="p-8">
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 mb-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold text-slate-900">我的任务</h1>
                <p className="text-sm text-slate-500 mt-1">当前流转在你名下的工作项，共 {tasks.length} 条</p>
              </div>
              <button
                onClick={() => setReloadTick(prev => prev + 1)}
                className="px-4 py-2 text-sm font-semibold border border-slate-200 rounded-xl hover:bg-slate-50"
              >
                刷新
              </button>
            </div>

            <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="relative md:col-span-2">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  value={searchText}
                  onChange={(event) => setSearchText(event.target.value)}
                  placeholder="搜索任务ID、标题、类型、状态、创建人"
                  className="w-full pl-9 pr-3 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100"
                />
              </div>
              <select
                value={selectedState}
                onChange={(event) => setSelectedState(event.target.value)}
                className="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 bg-white"
              >
                <option value="">全部状态</option>
                {stateOptions.map(state => (
                  <option key={state} value={state}>{state}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
            {isLoading ? (
              <div className="p-10 text-center text-slate-500 text-sm">正在加载我的任务...</div>
            ) : errorMessage ? (
              <div className="p-10 text-center text-rose-600 text-sm">{errorMessage}</div>
            ) : filteredTasks.length === 0 ? (
              <div className="p-10 text-center text-slate-500 text-sm">暂无命中任务</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[960px]">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="text-left px-5 py-3 text-xs font-bold text-slate-500">任务ID</th>
                      <th className="text-left px-5 py-3 text-xs font-bold text-slate-500">标题</th>
                      <th className="text-left px-5 py-3 text-xs font-bold text-slate-500">类型</th>
                      <th className="text-left px-5 py-3 text-xs font-bold text-slate-500">当前状态</th>
                      <th className="text-left px-5 py-3 text-xs font-bold text-slate-500">创建人</th>
                      <th className="text-left px-5 py-3 text-xs font-bold text-slate-500">更新时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTasks.map(item => (
                      <tr key={item.item_id} className="border-t border-slate-100 hover:bg-slate-50/70">
                        <td className="px-5 py-4 text-sm font-mono text-slate-700">{item.item_id}</td>
                        <td className="px-5 py-4 text-sm text-slate-900 font-medium max-w-[360px]">
                          <div className="truncate">{item.title || '-'}</div>
                        </td>
                        <td className="px-5 py-4 text-sm text-slate-700">{item.type_code}</td>
                        <td className="px-5 py-4 text-sm">
                          <span className={`inline-flex px-2 py-0.5 rounded-lg text-xs font-semibold ${getStateClass(item.current_state)}`}>
                            {item.current_state}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-sm text-slate-700">{item.creator_id || '-'}</td>
                        <td className="px-5 py-4 text-sm text-slate-700">{formatDateTime(item.updated_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};
