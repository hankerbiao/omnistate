import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Calendar,
  FileText,
  LayoutDashboard,
  ListTodo,
  LogIn,
  Mail,
  Pencil,
  PlayCircle,
  Plus,
  RefreshCcw,
  Search,
  Server,
  Shield,
  Loader2,
  Sparkles,
  Trash2,
  User,
  Wifi,
  X,
} from 'lucide-react';
import { DutAsset } from '../../types';
import { User as UserType, ROLES } from '../../constants/config';
import { isBackendEnabled, testDesignerApi } from '../../services/api';

interface DutComponentMgmtProps {
  currentUser: UserType | null;
  availableNavViews: string[];
  onNavigateToReqList: () => void;
  onNavigateToCaseList: () => void;
  onNavigateToMyTasks: () => void;
  onNavigateToTaskBoard: () => void;
  onNavigateToUserMgmt: () => void;
  onNavigateToNavMgmt: () => void;
  onLogout: () => void;
  showUserProfile: boolean;
  onToggleUserProfile: () => void;
}

interface QueryFilters {
  status: string;
  owner_team: string;
  owner: string;
  rack_location: string;
  health_status: string;
}

interface DutFormState {
  asset_id: string;
  model: string;
  status: string;
  owner_team: string;
  owner: string;
  rack_location: string;
  bmc_ip: string;
  bmc_port: string;
  os_ip: string;
  os_port: string;
  login_username: string;
  login_password: string;
  health_status: string;
  notes: string;
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

const toText = (value: unknown): string => (value === undefined || value === null ? '' : String(value));

const toNumber = (value: unknown): number | undefined => {
  if (value === undefined || value === null || value === '') return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
};

const normalizeDut = (input: unknown): DutAsset => {
  const row = asObject(input);
  return {
    id: toText(row.id) || undefined,
    asset_id: toText(row.asset_id),
    model: toText(row.model),
    status: toText(row.status) || '可用',
    owner_team: toText(row.owner_team) || undefined,
    owner: toText(row.owner) || undefined,
    rack_location: toText(row.rack_location) || undefined,
    bmc_ip: toText(row.bmc_ip ?? row.mgmt_ip) || undefined,
    bmc_port: toNumber(row.bmc_port),
    os_ip: toText(row.os_ip) || undefined,
    os_port: toNumber(row.os_port),
    login_username: toText(row.login_username) || undefined,
    login_password: toText(row.login_password) || undefined,
    health_status: toText(row.health_status) || undefined,
    notes: toText(row.notes) || undefined,
    created_at: toText(row.created_at) || undefined,
    updated_at: toText(row.updated_at) || undefined,
  };
};

const formatDateTime = (value?: string): string => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
};

const defaultForm = (): DutFormState => ({
  asset_id: '',
  model: '',
  status: '可用',
  owner_team: '',
  owner: '',
  rack_location: '',
  bmc_ip: '',
  bmc_port: '623',
  os_ip: '',
  os_port: '22',
  login_username: '',
  login_password: '',
  health_status: '正常',
  notes: '',
});

const dutToForm = (item: DutAsset): DutFormState => ({
  asset_id: item.asset_id || '',
  model: item.model || '',
  status: item.status || '可用',
  owner_team: item.owner_team || '',
  owner: item.owner || '',
  rack_location: item.rack_location || '',
  bmc_ip: item.bmc_ip || '',
  bmc_port: item.bmc_port === undefined ? '623' : String(item.bmc_port),
  os_ip: item.os_ip || '',
  os_port: item.os_port === undefined ? '22' : String(item.os_port),
  login_username: item.login_username || '',
  login_password: item.login_password || '',
  health_status: item.health_status || '正常',
  notes: item.notes || '',
});

const sampleLocalDuts = (): DutAsset[] => [
  {
    asset_id: 'SRV-BJ-001',
    model: 'Dell R760',
    status: '可用',
    owner_team: '基础设施测试组',
    owner: '张三',
    rack_location: 'BJ-DC1-A03-U21',
    bmc_ip: '10.10.1.21',
    bmc_port: 623,
    os_ip: '172.16.8.21',
    os_port: 22,
    login_username: 'root',
    login_password: '******',
    health_status: '正常',
    notes: '用于网络吞吐和稳定性回归。',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    asset_id: 'SRV-SH-014',
    model: 'Inspur NF5468M7',
    status: '占用',
    owner_team: '自动化测试平台',
    owner: '李四',
    rack_location: 'SH-LAB-B02-U08',
    bmc_ip: '10.20.6.8',
    bmc_port: 623,
    os_ip: '172.18.3.108',
    os_port: 22,
    login_username: 'admin',
    login_password: '******',
    health_status: '告警',
    notes: '风扇告警，待机房同学处理。',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const statusClassName = (status?: string): string => {
  const v = (status || '').toLowerCase();
  if (v.includes('可用') || v.includes('available')) return 'bg-emerald-50 text-emerald-700 border border-emerald-100';
  if (v.includes('占用') || v.includes('busy') || v.includes('in_use')) return 'bg-amber-50 text-amber-700 border border-amber-100';
  if (v.includes('维修') || v.includes('offline') || v.includes('下线')) return 'bg-rose-50 text-rose-700 border border-rose-100';
  return 'bg-slate-100 text-slate-700 border border-slate-200';
};

const healthClassName = (status?: string): string => {
  const v = (status || '').toLowerCase();
  if (v.includes('正常') || v.includes('healthy')) return 'bg-cyan-50 text-cyan-700 border border-cyan-100';
  if (v.includes('告警') || v.includes('warn')) return 'bg-amber-50 text-amber-700 border border-amber-100';
  if (v.includes('故障') || v.includes('error')) return 'bg-rose-50 text-rose-700 border border-rose-100';
  return 'bg-slate-100 text-slate-700 border border-slate-200';
};

const STATUS_PRESETS = ['可用', '占用', '维修中', '已下线'];
const HEALTH_PRESETS = ['正常', '告警', '故障'];

export const DutComponentMgmt: React.FC<DutComponentMgmtProps> = ({
  currentUser,
  availableNavViews,
  onNavigateToReqList,
  onNavigateToCaseList,
  onNavigateToMyTasks,
  onNavigateToTaskBoard,
  onNavigateToUserMgmt,
  onNavigateToNavMgmt,
  onLogout,
  showUserProfile,
  onToggleUserProfile,
}) => {
  const canAccessReqList = availableNavViews.includes('req_list');
  const canAccessCaseList = availableNavViews.includes('case_list');
  const canAccessMyTasks = availableNavViews.includes('my_tasks');
  const canAccessTaskBoard = availableNavViews.includes('test_task_board');
  const canAccessUserMgmt = availableNavViews.includes('user_mgmt');
  const canAccessNavMgmt = availableNavViews.includes('nav_mgmt');

  const [duts, setDuts] = useState<DutAsset[]>([]);
  const [filters, setFilters] = useState<QueryFilters>({
    status: '',
    owner_team: '',
    owner: '',
    rack_location: '',
    health_status: '',
  });
  const [searchText, setSearchText] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingAssetId, setEditingAssetId] = useState<string | null>(null);
  const [form, setForm] = useState<DutFormState>(defaultForm());
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const loadDuts = useCallback(async () => {
    if (!isBackendEnabled || !testDesignerApi) {
      setDuts(prev => (prev.length > 0 ? prev : sampleLocalDuts()));
      setErrorMessage('当前为本地演示模式（未连接后端 DUT 接口）');
      return;
    }

    setIsLoading(true);
    setErrorMessage('');
    try {
      const response = await testDesignerApi.listDuts({
        status: filters.status || undefined,
        owner_team: filters.owner_team || undefined,
        rack_location: filters.rack_location || undefined,
        health_status: filters.health_status || undefined,
        limit: 200,
        offset: 0,
      });
      const payload = unwrapApiData(response);
      const rows = extractList(payload);
      setDuts(rows.map(normalizeDut).filter(item => item.asset_id));
    } catch (error: any) {
      setErrorMessage(error?.message || '加载 DUT 列表失败');
      setDuts([]);
    } finally {
      setIsLoading(false);
    }
  }, [filters.health_status, filters.owner_team, filters.rack_location, filters.status]);

  useEffect(() => {
    void loadDuts();
  }, [loadDuts]);

  const filteredDuts = useMemo(() => {
    if (!searchText.trim()) {
      return duts;
    }
    const q = searchText.trim().toLowerCase();
    return duts.filter(item => (
      item.asset_id.toLowerCase().includes(q)
      || item.model.toLowerCase().includes(q)
      || (item.owner_team || '').toLowerCase().includes(q)
      || (item.rack_location || '').toLowerCase().includes(q)
      || (item.mgmt_ip || '').toLowerCase().includes(q)
      || (item.os_ip || '').toLowerCase().includes(q)
      || (item.status || '').toLowerCase().includes(q)
      || (item.health_status || '').toLowerCase().includes(q)
    ));
  }, [duts, searchText]);

  const stats = useMemo(() => {
    const total = duts.length;
    const available = duts.filter(item => {
      const v = (item.status || '').toLowerCase();
      return v.includes('可用') || v.includes('available');
    }).length;
    const busy = duts.filter(item => {
      const v = (item.status || '').toLowerCase();
      return v.includes('占用') || v.includes('busy') || v.includes('in_use');
    }).length;
    const healthy = duts.filter(item => {
      const v = (item.health_status || '').toLowerCase();
      return v.includes('正常') || v.includes('healthy');
    }).length;
    return { total, available, busy, healthy };
  }, [duts]);

  const handleOpenCreate = () => {
    setEditingAssetId(null);
    setForm(defaultForm());
    setShowForm(true);
  };

  const handleOpenEdit = (item: DutAsset) => {
    setEditingAssetId(item.asset_id);
    setForm(dutToForm(item));
    setShowForm(true);
  };

  const buildPayloadFromForm = (): { payload: DutAsset | null; error: string } => {
    const assetId = form.asset_id.trim();
    const model = form.model.trim();

    if (!assetId) {
      return { payload: null, error: 'asset_id 不能为空' };
    }
    if (!model) {
      return { payload: null, error: 'model 不能为空' };
    }

    const toOptional = (value: string): string | undefined => (value.trim() ? value.trim() : undefined);
    const toNumberOptional = (value: string): number | undefined => {
      const num = Number(value);
      return !isNaN(num) ? num : undefined;
    };

    const payload: DutAsset = {
      asset_id: assetId,
      model,
      status: form.status.trim() || '可用',
      owner_team: toOptional(form.owner_team),
      owner: toOptional(form.owner),
      rack_location: toOptional(form.rack_location),
      bmc_ip: toOptional(form.bmc_ip),
      bmc_port: toNumberOptional(form.bmc_port),
      os_ip: toOptional(form.os_ip),
      os_port: toNumberOptional(form.os_port),
      login_username: toOptional(form.login_username),
      login_password: toOptional(form.login_password),
      health_status: toOptional(form.health_status),
      notes: toOptional(form.notes),
    };

    return { payload, error: '' };
  };

  const handleSave = async () => {
    const { payload, error } = buildPayloadFromForm();
    if (!payload) {
      alert(error);
      return;
    }

    setIsSubmitting(true);
    try {
      if (!isBackendEnabled || !testDesignerApi) {
        if (editingAssetId) {
          setDuts(prev => prev.map(item => item.asset_id === editingAssetId
            ? { ...item, ...payload, asset_id: editingAssetId, updated_at: new Date().toISOString() }
            : item));
        } else {
          setDuts(prev => [{ ...payload, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }, ...prev]);
        }
      } else {
        if (editingAssetId) {
          const updatePayload: Partial<DutAsset> = { ...payload };
          delete updatePayload.asset_id;
          await testDesignerApi.updateDut(editingAssetId, updatePayload);
        } else {
          await testDesignerApi.createDut(payload);
        }
        await loadDuts();
      }

      setShowForm(false);
      setEditingAssetId(null);
      setForm(defaultForm());
    } catch (error: any) {
      alert(error?.message || '保存失败，请重试');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (assetId: string) => {
    const confirmed = window.confirm(`确认删除 DUT 服务器 ${assetId}？`);
    if (!confirmed) return;

    try {
      if (!isBackendEnabled || !testDesignerApi) {
        setDuts(prev => prev.filter(item => item.asset_id !== assetId));
      } else {
        await testDesignerApi.deleteDut(assetId);
        await loadDuts();
      }
    } catch (error: any) {
      alert(error?.message || '删除失败，请重试');
    }
  };

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
            <button onClick={onNavigateToReqList} className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors">
              <FileText size={18} /> 测试需求
            </button>
          )}
          {canAccessCaseList && (
            <button onClick={onNavigateToCaseList} className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors">
              <PlayCircle size={18} /> 测试用例
            </button>
          )}
          {canAccessMyTasks && (
            <button onClick={onNavigateToMyTasks} className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors">
              <ListTodo size={18} /> 我的任务
            </button>
          )}
          {canAccessTaskBoard && (
            <button onClick={onNavigateToTaskBoard} className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors">
              <LayoutDashboard size={18} /> 测试看板
            </button>
          )}
          <button onClick={() => {}} className="w-full flex items-center gap-3 px-4 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold shadow-lg shadow-slate-900/20">
            <Server size={18} /> DUT 设备
          </button>
          {canAccessUserMgmt && (
            <button onClick={onNavigateToUserMgmt} className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors">
              <User size={18} /> 用户管理
            </button>
          )}
          {canAccessNavMgmt && (
            <button onClick={onNavigateToNavMgmt} className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors">
              <Shield size={18} /> 导航管理
            </button>
          )}
        </nav>

        <div className="p-4 border-t border-slate-100">
          {currentUser && (
            <>
              <button onClick={onToggleUserProfile} className="w-full flex items-center gap-3 p-3 bg-slate-50 rounded-xl mb-3 hover:bg-slate-100 transition-colors cursor-pointer group">
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
                          <div className="text-sm text-slate-500">{currentUser.role_ids[0] === 'ROLE_TPM' ? '测试经理' : '测试工程师'}</div>
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

          <button onClick={onLogout} className="w-full flex items-center gap-3 px-4 py-2.5 text-slate-500 hover:bg-rose-50 hover:text-rose-600 rounded-xl text-sm font-bold transition-colors">
            <LogIn size={16} className="rotate-180" /> 退出登录
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <div className="p-8 space-y-6">
          <section className="relative overflow-hidden rounded-3xl border border-slate-100 bg-white shadow-sm">
            <div className="absolute -right-16 -top-16 w-56 h-56 bg-indigo-100/60 rounded-full blur-2xl" />
            <div className="absolute -left-10 -bottom-12 w-48 h-48 bg-cyan-100/50 rounded-full blur-2xl" />
            <div className="relative p-6">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h1 className="text-2xl font-bold text-slate-900">DUT 服务器录入中心</h1>
                  <p className="text-sm text-slate-500 mt-1">仅维护服务器基础信息与状态，不包含部件字典字段</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => void loadDuts()}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-slate-200 text-slate-700 text-sm font-semibold hover:bg-slate-50"
                  >
                    <RefreshCcw size={15} /> 刷新
                  </button>
                  <button
                    onClick={handleOpenCreate}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-900 text-white text-sm font-bold hover:bg-slate-800"
                  >
                    <Plus size={15} /> 新建服务器
                  </button>
                </div>
              </div>

              <div className="mt-5 grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="rounded-xl bg-slate-50 border border-slate-100 px-4 py-3">
                  <div className="text-xs text-slate-500">服务器总数</div>
                  <div className="text-xl font-bold text-slate-900 mt-1">{stats.total}</div>
                </div>
                <div className="rounded-xl bg-emerald-50 border border-emerald-100 px-4 py-3">
                  <div className="text-xs text-emerald-600">可用</div>
                  <div className="text-xl font-bold text-emerald-700 mt-1">{stats.available}</div>
                </div>
                <div className="rounded-xl bg-amber-50 border border-amber-100 px-4 py-3">
                  <div className="text-xs text-amber-600">占用中</div>
                  <div className="text-xl font-bold text-amber-700 mt-1">{stats.busy}</div>
                </div>
                <div className="rounded-xl bg-cyan-50 border border-cyan-100 px-4 py-3">
                  <div className="text-xs text-cyan-600">健康正常</div>
                  <div className="text-xl font-bold text-cyan-700 mt-1">{stats.healthy}</div>
                </div>
              </div>
            </div>
          </section>

          <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
            <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
              <input
                value={filters.status}
                onChange={e => setFilters(prev => ({ ...prev, status: e.target.value }))}
                placeholder="按设备状态过滤"
                className="px-3 py-2.5 border border-slate-200 rounded-xl text-sm"
              />
              <input
                value={filters.owner}
                onChange={e => setFilters(prev => ({ ...prev, owner: e.target.value }))}
                placeholder="按负责人过滤"
                className="px-3 py-2.5 border border-slate-200 rounded-xl text-sm"
              />
              <input
                value={filters.owner_team}
                onChange={e => setFilters(prev => ({ ...prev, owner_team: e.target.value }))}
                placeholder="按归属团队过滤"
                className="px-3 py-2.5 border border-slate-200 rounded-xl text-sm"
              />
              <input
                value={filters.rack_location}
                onChange={e => setFilters(prev => ({ ...prev, rack_location: e.target.value }))}
                placeholder="按机房机位过滤"
                className="px-3 py-2.5 border border-slate-200 rounded-xl text-sm"
              />
              <input
                value={filters.health_status}
                onChange={e => setFilters(prev => ({ ...prev, health_status: e.target.value }))}
                placeholder="按健康状态过滤"
                className="px-3 py-2.5 border border-slate-200 rounded-xl text-sm"
              />
              <button
                onClick={() => void loadDuts()}
                className="px-3 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800"
              >
                查询
              </button>
            </div>

            <div className="mt-3 relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                value={searchText}
                onChange={e => setSearchText(e.target.value)}
                placeholder="前端搜索：资产编号 / 型号 / 负责人 / 团队 / IP"
                className="w-full pl-9 pr-3 py-2.5 border border-slate-200 rounded-xl text-sm"
              />
            </div>

            {errorMessage && <div className="mt-3 text-xs text-amber-700 bg-amber-50 border border-amber-100 px-3 py-2 rounded-lg">{errorMessage}</div>}
          </section>

          <section className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
            {isLoading ? (
              <div className="p-10 text-center text-sm text-slate-500">正在加载服务器列表...</div>
            ) : filteredDuts.length === 0 ? (
              <div className="p-10 text-center text-sm text-slate-500">暂无数据</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[1300px]">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="text-left px-4 py-3 text-xs font-bold text-slate-500">资产编号</th>
                      <th className="text-left px-4 py-3 text-xs font-bold text-slate-500">服务器型号</th>
                      <th className="text-left px-4 py-3 text-xs font-bold text-slate-500">设备状态</th>
                      <th className="text-left px-4 py-3 text-xs font-bold text-slate-500">健康状态</th>
                      <th className="text-left px-4 py-3 text-xs font-bold text-slate-500">负责人 / 团队</th>
                      <th className="text-left px-4 py-3 text-xs font-bold text-slate-500">BMC / OS IP</th>
                      <th className="text-left px-4 py-3 text-xs font-bold text-slate-500">机位</th>
                      <th className="text-left px-4 py-3 text-xs font-bold text-slate-500">更新时间</th>
                      <th className="text-left px-4 py-3 text-xs font-bold text-slate-500">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDuts.map(item => (
                      <tr key={item.asset_id} className="border-t border-slate-100 hover:bg-slate-50/60">
                        <td className="px-4 py-3 text-sm font-mono text-indigo-700">{item.asset_id}</td>
                        <td className="px-4 py-3 text-sm text-slate-700">{item.model}</td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-0.5 rounded-lg text-xs font-bold ${statusClassName(item.status)}`}>{item.status || '-'}</span>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-0.5 rounded-lg text-xs font-bold ${healthClassName(item.health_status)}`}>{item.health_status || '-'}</span>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-700">{item.owner || '-'} / {item.owner_team || '-'}</td>
                        <td className="px-4 py-3 text-sm text-slate-700">{item.bmc_ip || '-'} : {item.bmc_port || '-'} / {item.os_ip || '-'}</td>
                        <td className="px-4 py-3 text-sm text-slate-700">{item.rack_location || '-'}</td>
                        <td className="px-4 py-3 text-sm text-slate-500">{formatDateTime(item.updated_at)}</td>
                        <td className="px-4 py-3 text-sm">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleOpenEdit(item)}
                              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 text-xs font-bold"
                            >
                              <Pencil size={12} /> 编辑
                            </button>
                            <button
                              onClick={() => void handleDelete(item.asset_id)}
                              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-rose-50 text-rose-700 text-xs font-bold"
                            >
                              <Trash2 size={12} /> 删除
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      </main>

      {showForm && (
        <div className="fixed inset-0 z-[120] flex items-center justify-center p-4 sm:p-6">
          <div
            className="absolute inset-0 bg-slate-900/35 backdrop-blur-md"
            style={{ animation: 'dutMaskIn 240ms ease-out' }}
            onClick={() => setShowForm(false)}
          />
          <div
            className="relative w-full max-w-5xl max-h-[92vh] overflow-hidden rounded-3xl border border-white/60 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.25)]"
            style={{ animation: 'dutDialogIn 360ms cubic-bezier(0.22, 1, 0.36, 1)' }}
          >
            <div className="relative px-6 py-5 border-b border-slate-100 bg-gradient-to-r from-sky-50 via-cyan-50 to-indigo-50">
              <div className="absolute -right-8 -top-6 w-28 h-28 rounded-full bg-cyan-200/40 blur-2xl" style={{ animation: 'dutFloat 4s ease-in-out infinite' }} />
              <div className="absolute -left-10 -bottom-10 w-24 h-24 rounded-full bg-indigo-200/35 blur-2xl" style={{ animation: 'dutFloat 5s ease-in-out infinite' }} />
              <div className="relative flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-xl font-extrabold text-slate-900 tracking-tight">
                    {editingAssetId ? `编辑服务器：${editingAssetId}` : '新建服务器录入'}
                  </h3>
                  <p className="text-sm text-slate-600 mt-1">
                    录入服务器身份、网络、系统与健康状态，帮助测试任务快速分配可用 DUT。
                  </p>
                </div>
                <button
                  onClick={() => setShowForm(false)}
                  className="p-2 rounded-xl text-slate-400 hover:bg-white/80 hover:text-slate-700 transition-colors"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="p-6 overflow-auto max-h-[calc(92vh-188px)] space-y-4 bg-slate-50/70">
              <section
                className="rounded-2xl border border-sky-100 bg-white p-4 shadow-sm"
                style={{ animation: 'dutSlideUp 300ms ease-out both', animationDelay: '60ms' }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles size={16} className="text-sky-500" />
                  <h4 className="text-sm font-bold text-slate-900">基础识别信息</h4>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  <label className="block">
                    <span className="text-xs font-semibold text-slate-500">资产编号 *</span>
                    <input
                      value={form.asset_id}
                      onChange={e => setForm(prev => ({ ...prev, asset_id: e.target.value }))}
                      disabled={Boolean(editingAssetId)}
                      placeholder="例如：SRV-BJ-001"
                      className="mt-1 w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white disabled:bg-slate-100 focus:outline-none focus:ring-4 focus:ring-sky-100 focus:border-sky-400 transition-all"
                    />
                  </label>
                  <label className="block">
                    <span className="text-xs font-semibold text-slate-500">服务器型号 *</span>
                    <input
                      value={form.model}
                      onChange={e => setForm(prev => ({ ...prev, model: e.target.value }))}
                      placeholder="例如：Dell R760 / H3C UniServer"
                      className="mt-1 w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-4 focus:ring-sky-100 focus:border-sky-400 transition-all"
                    />
                  </label>
                  <label className="block">
                    <span className="text-xs font-semibold text-slate-500">归属团队</span>
                    <input
                      value={form.owner_team}
                      onChange={e => setForm(prev => ({ ...prev, owner_team: e.target.value }))}
                      placeholder="例如：自动化测试平台组"
                      className="mt-1 w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-4 focus:ring-sky-100 focus:border-sky-400 transition-all"
                    />
                  </label>
                  <label className="block">
                    <span className="text-xs font-semibold text-slate-500">机器负责人</span>
                    <select
                      value={form.owner}
                      onChange={e => setForm(prev => ({ ...prev, owner: e.target.value }))}
                      className="mt-1 w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-4 focus:ring-sky-100 focus:border-sky-400 transition-all"
                    >
                      <option value="">请选择负责人</option>
                      <option value="张三">张三</option>
                      <option value="李四">李四</option>
                      <option value="王五">王五</option>
                      <option value="赵六">赵六</option>
                    </select>
                  </label>
                  <label className="block">
                    <span className="text-xs font-semibold text-slate-500">机房机位</span>
                    <input
                      value={form.rack_location}
                      onChange={e => setForm(prev => ({ ...prev, rack_location: e.target.value }))}
                      placeholder="例如：BJ-DC1-A03-U21"
                      className="mt-1 w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-4 focus:ring-sky-100 focus:border-sky-400 transition-all"
                    />
                  </label>
                </div>
              </section>

              <section
                className="rounded-2xl border border-indigo-100 bg-white p-4 shadow-sm"
                style={{ animation: 'dutSlideUp 320ms ease-out both', animationDelay: '110ms' }}
              >
                <h4 className="text-sm font-bold text-slate-900 mb-3">网络与系统信息</h4>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  <label className="block">
                    <span className="text-xs font-semibold text-slate-500">BMC IP</span>
                    <div className="flex gap-2">
                      <input
                        value={form.bmc_ip}
                        onChange={e => setForm(prev => ({ ...prev, bmc_ip: e.target.value }))}
                        placeholder="例如：10.10.1.21"
                        className="flex-1 mt-1 px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-4 focus:ring-indigo-100 focus:border-indigo-400 transition-all"
                      />
                      <input
                        value={form.bmc_port}
                        onChange={e => setForm(prev => ({ ...prev, bmc_port: e.target.value }))}
                        placeholder="端口"
                        className="w-24 mt-1 px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-4 focus:ring-indigo-100 focus:border-indigo-400 transition-all"
                      />
                    </div>
                  </label>
                  <label className="block">
                    <span className="text-xs font-semibold text-slate-500">OS IP</span>
                    <div className="flex gap-2">
                      <input
                        value={form.os_ip}
                        onChange={e => setForm(prev => ({ ...prev, os_ip: e.target.value }))}
                        placeholder="例如：172.16.8.21"
                        className="flex-1 mt-1 px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-4 focus:ring-indigo-100 focus:border-indigo-400 transition-all"
                      />
                      <input
                        value={form.os_port}
                        onChange={e => setForm(prev => ({ ...prev, os_port: e.target.value }))}
                        placeholder="端口"
                        className="w-24 mt-1 px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-4 focus:ring-indigo-100 focus:border-indigo-400 transition-all"
                      />
                    </div>
                  </label>
                  <label className="block">
                    <span className="text-xs font-semibold text-slate-500">登录用户名</span>
                    <input
                      value={form.login_username}
                      onChange={e => setForm(prev => ({ ...prev, login_username: e.target.value }))}
                      placeholder="例如：root 或 admin"
                      className="mt-1 w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-4 focus:ring-indigo-100 focus:border-indigo-400 transition-all"
                    />
                  </label>
                  <label className="block">
                    <span className="text-xs font-semibold text-slate-500">登录密码</span>
                    <input
                      type="password"
                      value={form.login_password}
                      onChange={e => setForm(prev => ({ ...prev, login_password: e.target.value }))}
                      placeholder="登录密码"
                      className="mt-1 w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-4 focus:ring-indigo-100 focus:border-indigo-400 transition-all"
                    />
                  </label>
                </div>
              </section>

              <section
                className="rounded-2xl border border-emerald-100 bg-white p-4 shadow-sm"
                style={{ animation: 'dutSlideUp 340ms ease-out both', animationDelay: '160ms' }}
              >
                <h4 className="text-sm font-bold text-slate-900 mb-3">状态信息</h4>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <label className="block">
                    <span className="text-xs font-semibold text-slate-500">设备状态 *</span>
                    <select
                      value={form.status}
                      onChange={e => setForm(prev => ({ ...prev, status: e.target.value }))}
                      className="mt-1 w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-4 focus:ring-emerald-100 focus:border-emerald-400 transition-all"
                    >
                      {STATUS_PRESETS.map(option => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </label>
                  <label className="block">
                    <span className="text-xs font-semibold text-slate-500">健康状态 *</span>
                    <select
                      value={form.health_status}
                      onChange={e => setForm(prev => ({ ...prev, health_status: e.target.value }))}
                      className="mt-1 w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-4 focus:ring-cyan-100 focus:border-cyan-400 transition-all"
                    >
                      {HEALTH_PRESETS.map(option => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </label>
                </div>
              </section>

              <section
                className="rounded-2xl border border-rose-100 bg-white p-4 shadow-sm"
                style={{ animation: 'dutSlideUp 340ms ease-out both', animationDelay: '180ms' }}
              >
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-bold text-slate-900">连接测试</h4>
                  <button
                    onClick={async () => {
                      // TODO: 实现连接测试功能
                      alert('连接测试功能开发中...');
                    }}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold bg-rose-600 text-white hover:bg-rose-700 transition-all"
                  >
                    <Wifi size={16} />
                    测试连接
                  </button>
                </div>
                <div className="text-xs text-slate-600 bg-rose-50 border border-rose-100 rounded-lg p-3">
                  可测试 BMC 和 OS 的连接状态，确保录入信息准确无误。
                </div>
              </section>

              <section
                className="rounded-2xl border border-amber-100 bg-white p-4 shadow-sm"
                style={{ animation: 'dutSlideUp 360ms ease-out both', animationDelay: '210ms' }}
              >
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  <div className="lg:col-span-2">
                    <h4 className="text-sm font-bold text-slate-900 mb-2">备注与测试建议</h4>
                    <textarea
                      value={form.notes}
                      onChange={e => setForm(prev => ({ ...prev, notes: e.target.value }))}
                      rows={5}
                      placeholder="可填写当前用途、风险提示、机房联系人、预约窗口等信息"
                      className="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-4 focus:ring-amber-100 focus:border-amber-400 transition-all"
                    />
                  </div>
                  <div className="rounded-xl bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-100 p-3">
                    <div className="text-xs font-bold text-amber-700 mb-2">录入建议</div>
                    <div className="text-xs text-amber-800/90 leading-5">
                      建议补充最近一次用途、值班联系人和维护窗口。遇到“告警/故障”状态时，备注中写明影响范围，便于任务排期避让。
                    </div>
                  </div>
                </div>
              </section>
            </div>

            <div className="px-6 py-4 border-t border-slate-100 bg-white flex items-center justify-end gap-3">
              <button
                onClick={() => setShowForm(false)}
                className="px-4 py-2.5 text-sm font-semibold border border-slate-200 rounded-xl text-slate-600 hover:bg-slate-50 transition-colors"
              >
                取消
              </button>
              <button
                onClick={() => void handleSave()}
                disabled={isSubmitting}
                className="px-5 py-2.5 text-sm font-bold rounded-xl bg-gradient-to-r from-slate-900 to-indigo-900 text-white hover:from-slate-800 hover:to-indigo-800 disabled:opacity-50 transition-all"
              >
                {isSubmitting ? '保存中...' : '保存服务器信息'}
              </button>
            </div>
          </div>
        </div>
      )}
      <style>{`
        @keyframes dutMaskIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes dutDialogIn {
          from { opacity: 0; transform: translateY(24px) scale(0.96); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes dutSlideUp {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes dutFloat {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-8px); }
        }
      `}</style>
    </div>
  );
};
