import React, { useState, useMemo } from 'react';
import {
  Plus,
  ChevronRight,
  FileText,
  PlayCircle,
  User,
  LogIn,
  Search,
  ChevronDown,
  ChevronUp,
  Filter,
  X,
  PanelLeftClose,
  PanelLeft,
  Mail,
  Calendar,
  Shield,
} from 'lucide-react';
import { TestCase, TestCaseStatus, TestCaseCategory, Priority } from '../../types';
import { User as UserType, ROLES } from '../../constants/config';

interface CaseListProps {
  testCases: TestCase[];
  currentUser: UserType | null;
  onSelectCase: (tc: TestCase) => void;
  onCreateCase: () => void;
  onNavigateToReqList: () => void;
  onNavigateToUserMgmt: () => void;
  onLogout: () => void;
  showUserProfile: boolean;
  onToggleUserProfile: () => void;
}

interface FilterSection {
  id: string;
  label: string;
  options: { value: string; label: string; count: number }[];
}

export const CaseList: React.FC<CaseListProps> = ({
  testCases,
  currentUser,
  onSelectCase,
  onCreateCase,
  onNavigateToReqList,
  onNavigateToUserMgmt,
  onLogout,
  showUserProfile,
  onToggleUserProfile,
}) => {
  const [searchText, setSearchText] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    status: false,
    category: false,
    priority: false,
    component: false,
  });
  const [selectedFilters, setSelectedFilters] = useState<Record<string, Set<string>>>({
    status: new Set(),
    category: new Set(),
    priority: new Set(),
    component: new Set(),
  });

  const getCategoryLabel = (category: TestCaseCategory): string => {
    switch (category) {
      case TestCaseCategory.FUNCTIONAL: return '功能';
      case TestCaseCategory.STRESS: return '压力';
      case TestCaseCategory.PERFORMANCE: return '性能';
      case TestCaseCategory.COMPATIBILITY: return '兼容';
      case TestCaseCategory.STABILITY: return '稳定';
      case TestCaseCategory.SECURITY: return '安全';
      default: return '其他';
    }
  };

  const getCategoryValue = (category: TestCaseCategory): string => {
    return category;
  };

  const getStatusLabel = (status: TestCaseStatus): string => {
    switch (status) {
      case TestCaseStatus.DRAFT: return '草稿';
      case TestCaseStatus.REVIEW: return '评审中';
      case TestCaseStatus.APPROVED: return '已批准';
      case TestCaseStatus.DEPRECATED: return '已废弃';
      default: return status;
    }
  };

  const getStatusValue = (status: TestCaseStatus): string => {
    return status;
  };

  const getPriorityLabel = (priority: Priority): string => {
    switch (priority) {
      case Priority.P0: return 'P0 - 紧急';
      case Priority.P1: return 'P1 - 高';
      case Priority.P2: return 'P2 - 普通';
      default: return priority;
    }
  };

  // Build filter sections with counts
  const filterSections = useMemo((): FilterSection[] => {
    const statusOptions = Object.values(TestCaseStatus).map(status => ({
      value: getStatusValue(status),
      label: getStatusLabel(status),
      count: testCases.filter(tc => tc.status === status).length,
    }));

    const categoryOptions = Object.values(TestCaseCategory).map(category => ({
      value: getCategoryValue(category),
      label: getCategoryLabel(category),
      count: testCases.filter(tc => tc.test_category === category).length,
    }));

    const priorityOptions = Object.values(Priority).map(priority => ({
      value: priority,
      label: getPriorityLabel(priority),
      count: testCases.filter(tc => tc.priority === priority).length,
    }));

    // Get unique components
    const componentCounts = new Map<string, number>();
    testCases.forEach(tc => {
      tc.target_components.forEach(comp => {
        componentCounts.set(comp, (componentCounts.get(comp) || 0) + 1);
      });
    });
    const componentOptions = Array.from(componentCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([value, count]) => ({
        value,
        label: value,
        count,
      }));

    return [
      { id: 'status', label: '状态', options: statusOptions },
      { id: 'category', label: '测试类别', options: categoryOptions },
      { id: 'priority', label: '优先级', options: priorityOptions },
      { id: 'component', label: '目标部件', options: componentOptions },
    ];
  }, [testCases]);

  // Filter test cases based on search and selected filters
  const filteredCases = useMemo(() => {
    return testCases.filter(tc => {
      // Search filter
      if (searchText) {
        const search = searchText.toLowerCase();
        const matchesSearch =
          tc.title.toLowerCase().includes(search) ||
          tc.case_id.toLowerCase().includes(search) ||
          tc.ref_req_id.toLowerCase().includes(search) ||
          tc.owner_id.toLowerCase().includes(search) ||
          tc.tags.some(tag => tag.toLowerCase().includes(search));
        if (!matchesSearch) return false;
      }

      // Status filter
      if (selectedFilters.status.size > 0 && !selectedFilters.status.has(tc.status)) {
        return false;
      }

      // Category filter
      if (selectedFilters.category.size > 0 && !selectedFilters.category.has(tc.test_category)) {
        return false;
      }

      // Priority filter
      if (selectedFilters.priority.size > 0 && !selectedFilters.priority.has(tc.priority)) {
        return false;
      }

      // Component filter
      if (selectedFilters.component.size > 0) {
        const hasMatchingComponent = tc.target_components.some(comp => selectedFilters.component.has(comp));
        if (!hasMatchingComponent) return false;
      }

      return true;
    });
  }, [testCases, searchText, selectedFilters]);

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => ({ ...prev, [sectionId]: !prev[sectionId] }));
  };

  const toggleFilter = (sectionId: string, value: string) => {
    setSelectedFilters(prev => {
      const newSet = new Set(prev[sectionId]);
      if (newSet.has(value)) {
        newSet.delete(value);
      } else {
        newSet.add(value);
      }
      return { ...prev, [sectionId]: newSet };
    });
  };

  const clearFilters = () => {
    setSelectedFilters({
      status: new Set(),
      category: new Set(),
      priority: new Set(),
      component: new Set(),
    });
    setSearchText('');
  };

  const hasActiveFilters = searchText ||
    selectedFilters.status.size > 0 ||
    selectedFilters.category.size > 0 ||
    selectedFilters.priority.size > 0 ||
    selectedFilters.component.size > 0;

  const getCategoryClass = (category: TestCaseCategory): string => {
    switch (category) {
      case TestCaseCategory.FUNCTIONAL: return 'bg-blue-50 text-blue-600';
      case TestCaseCategory.STRESS: return 'bg-rose-50 text-rose-600';
      case TestCaseCategory.PERFORMANCE: return 'bg-purple-50 text-purple-600';
      case TestCaseCategory.COMPATIBILITY: return 'bg-amber-50 text-amber-600';
      case TestCaseCategory.STABILITY: return 'bg-emerald-50 text-emerald-600';
      case TestCaseCategory.SECURITY: return 'bg-slate-50 text-slate-600';
      default: return 'bg-slate-50 text-slate-600';
    }
  };

  const getStatusClass = (status: TestCaseStatus): string => {
    switch (status) {
      case TestCaseStatus.DRAFT: return 'bg-slate-100 text-slate-600';
      case TestCaseStatus.REVIEW: return 'bg-amber-50 text-amber-600';
      case TestCaseStatus.APPROVED: return 'bg-emerald-50 text-emerald-600';
      case TestCaseStatus.DEPRECATED: return 'bg-rose-50 text-rose-600';
      default: return 'bg-slate-100 text-slate-600';
    }
  };

  const getPriorityClass = (priority: Priority): string => {
    switch (priority) {
      case Priority.P0: return 'bg-rose-50 text-rose-600';
      case Priority.P1: return 'bg-amber-50 text-amber-600';
      default: return 'bg-emerald-50 text-emerald-600';
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA] flex">
      {/* Left Sidebar - Navigation */}
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
          <button onClick={onNavigateToReqList} className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors">
            <FileText size={18} />
            测试需求
          </button>
          <button onClick={() => {}} className="w-full flex items-center gap-3 px-4 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold shadow-lg shadow-slate-900/20">
            <PlayCircle size={18} />
            测试用例
          </button>
          <button onClick={onNavigateToUserMgmt} className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors">
            <User size={18} />
            用户管理
          </button>
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

              {/* User Profile Popup */}
              {showUserProfile && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                  <div
                    className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm"
                    onClick={onToggleUserProfile}
                  />
                  <div className="relative w-full max-w-md bg-white rounded-3xl shadow-2xl overflow-hidden">
                    {/* Header */}
                    <div className="px-6 py-5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white">
                      <div className="flex items-center justify-between">
                        <h2 className="text-lg font-bold">个人信息</h2>
                        <button
                          onClick={onToggleUserProfile}
                          className="p-1 hover:bg-white/20 rounded-lg transition-colors"
                        >
                          <X size={20} />
                        </button>
                      </div>
                    </div>

                    {/* Content */}
                    <div className="p-6 space-y-5">
                      {/* Avatar and Name */}
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

                      {/* Details */}
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

                        <div className="flex items-center gap-3 text-sm">
                          <div className="w-4 h-4 flex items-center justify-center">
                            <div className="w-2 h-2 bg-slate-400 rounded-full" />
                          </div>
                          <div>
                            <div className="text-xs text-slate-400">用户 ID</div>
                            <div className="font-mono text-xs text-slate-600">{currentUser.user_id}</div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Footer */}
                    <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex gap-3">
                      <button
                        onClick={onToggleUserProfile}
                        className="flex-1 px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-200 rounded-xl transition-all"
                      >
                        关闭
                      </button>
                      <button
                        onClick={() => {
                          onToggleUserProfile();
                          onNavigateToUserMgmt();
                        }}
                        className="flex-1 px-4 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all"
                      >
                        编辑资料
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <button onClick={onLogout} className="w-full flex items-center gap-3 px-4 py-2.5 text-slate-500 hover:bg-rose-50 hover:text-rose-600 rounded-xl text-sm font-bold transition-colors">
            <LogIn size={16} className="rotate-180" />
            退出登录
          </button>
        </div>
      </aside>

      {/* Filter Sidebar */}
      {showFilters && (
      <aside className="w-72 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-4 border-b border-slate-100">
          <div className="flex items-center gap-2 mb-4">
            <Filter size={18} className="text-slate-500" />
            <span className="font-bold text-slate-900">筛选条件</span>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="ml-auto text-xs text-indigo-600 hover:text-indigo-700 font-medium"
              >
                清除全部
              </button>
            )}
          </div>

          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="搜索用例..."
              className="w-full pl-9 pr-8 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all"
            />
            {searchText && (
              <button
                onClick={() => setSearchText('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X size={14} />
              </button>
            )}
          </div>
        </div>

        {/* Filter Tree */}
        <div className="flex-1 overflow-auto p-4 space-y-2">
          {filterSections.map(section => (
            <div key={section.id} className="border border-slate-100 rounded-xl overflow-hidden">
              <button
                onClick={() => toggleSection(section.id)}
                className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors"
              >
                <span className="text-sm font-bold text-slate-700">{section.label}</span>
                {expandedSections[section.id] ? (
                  <ChevronUp size={16} className="text-slate-400" />
                ) : (
                  <ChevronDown size={16} className="text-slate-400" />
                )}
              </button>

              {expandedSections[section.id] && (
                <div className="p-2 space-y-1">
                  {section.options.map(option => (
                    <button
                      key={option.value}
                      onClick={() => toggleFilter(section.id, option.value)}
                      className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-all ${
                        selectedFilters[section.id as keyof typeof selectedFilters].has(option.value)
                          ? 'bg-indigo-50 text-indigo-700'
                          : 'hover:bg-slate-50 text-slate-600'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <div className={`w-4 h-4 rounded border flex items-center justify-center ${
                          selectedFilters[section.id as keyof typeof selectedFilters].has(option.value)
                            ? 'bg-indigo-600 border-indigo-600'
                            : 'border-slate-300'
                        }`}>
                          {selectedFilters[section.id as keyof typeof selectedFilters].has(option.value) && (
                            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                        <span className="font-medium">{option.label}</span>
                      </div>
                      <span className={`text-xs font-bold ${
                        selectedFilters[section.id as keyof typeof selectedFilters].has(option.value)
                          ? 'text-indigo-600'
                          : 'text-slate-400'
                      }`}>
                        {option.count}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Filter Summary */}
        {hasActiveFilters && (
          <div className="p-4 border-t border-slate-100 bg-slate-50">
            <div className="text-xs text-slate-500 text-center">
              找到 <span className="font-bold text-indigo-600">{filteredCases.length}</span> 个测试用例
            </div>
          </div>
        )}
      </aside>
      )}

      {/* Main Content */}
      <main className="flex-1 p-8 space-y-8 overflow-auto">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="p-2.5 hover:bg-slate-100 rounded-xl transition-colors text-slate-500"
              title={showFilters ? '隐藏筛选面板' : '显示筛选面板'}
            >
              {showFilters ? <PanelLeftClose size={20} /> : <PanelLeft size={20} />}
            </button>
            <div>
              <h1 className="text-3xl font-bold text-slate-900 tracking-tight">测试用例管理</h1>
              <p className="text-base text-slate-500 mt-2">管理所有测试用例、查看状态和执行情况</p>
            </div>
          </div>
          <button onClick={onCreateCase} className="flex items-center gap-2 px-6 py-3 bg-slate-900 text-white rounded-2xl font-bold hover:bg-slate-800 transition-all shadow-xl hover:shadow-2xl shadow-slate-900/20 active:scale-95">
            <Plus size={20} /> 创建测试用例
          </button>
        </div>

        <div className="bg-white rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-100/50 overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="px-8 py-5 text-xs font-bold text-slate-400 uppercase tracking-wider">用例ID</th>
                <th className="px-8 py-5 text-xs font-bold text-slate-400 uppercase tracking-wider">标题</th>
                <th className="px-8 py-5 text-xs font-bold text-slate-400 uppercase tracking-wider">关联需求</th>
                <th className="px-8 py-5 text-xs font-bold text-slate-400 uppercase tracking-wider">类别</th>
                <th className="px-8 py-5 text-xs font-bold text-slate-400 uppercase tracking-wider">优先级</th>
                <th className="px-8 py-5 text-xs font-bold text-slate-400 uppercase tracking-wider">状态</th>
                <th className="px-8 py-5 text-xs font-bold text-slate-400 uppercase tracking-wider">责任人</th>
                <th className="px-8 py-5 text-xs font-bold text-slate-400 uppercase tracking-wider text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredCases.map(tc => (
                <tr key={tc.case_id} className="hover:bg-slate-50/50 transition-colors cursor-pointer" onClick={() => onSelectCase(tc)}>
                  <td className="px-8 py-5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-indigo-600 bg-indigo-50 px-2 py-1 rounded-lg border border-indigo-100">{tc.case_id}</span>
                      <span className="text-[10px] bg-slate-100 text-slate-500 px-2 py-1 rounded-lg font-bold">V{tc.version}</span>
                    </div>
                  </td>
                  <td className="px-8 py-5">
                    <div className="text-sm font-bold text-slate-900">{tc.title}</div>
                    <div className="text-xs text-slate-400 mt-1 flex gap-1">
                      {tc.tags.slice(0, 3).map(tag => (
                        <span key={tag} className="px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded">{tag}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-8 py-5">
                    <span className="text-xs font-mono text-slate-600 bg-slate-50 px-2 py-1 rounded">{tc.ref_req_id}</span>
                  </td>
                  <td className="px-8 py-5">
                    <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${getCategoryClass(tc.test_category)}`}>
                      {getCategoryLabel(tc.test_category)}
                    </span>
                  </td>
                  <td className="px-8 py-5">
                    <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${getPriorityClass(tc.priority)}`}>{tc.priority}</span>
                  </td>
                  <td className="px-8 py-5">
                    <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${getStatusClass(tc.status)}`}>
                      {getStatusLabel(tc.status)}
                    </span>
                  </td>
                  <td className="px-8 py-5 text-sm text-slate-600 font-medium">{tc.owner_id}</td>
                  <td className="px-8 py-5 text-right">
                    <button className="p-2 text-slate-300 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all">
                      <ChevronRight size={20} />
                    </button>
                  </td>
                </tr>
              ))}
              {filteredCases.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-8 py-16 text-center">
                    <div className="text-slate-400 text-sm">没有找到匹配的测试用例</div>
                    <button
                      onClick={clearFilters}
                      className="mt-2 text-indigo-600 hover:text-indigo-700 text-sm font-medium"
                    >
                      清除筛选条件
                    </button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
};