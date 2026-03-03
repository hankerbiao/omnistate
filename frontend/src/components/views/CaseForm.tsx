import React, { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  ChevronRight,
  Save,
  Cpu,
  PlayCircle,
  Paperclip,
  History,
  Plus,
  Trash2,
  FileText,
  Search,
  GripVertical,
  Zap,
  X,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { TestCase, TestCaseCategory, Confidentiality, TestStep, QuickCreateCasePayload } from '../../types';
import { User } from '../../constants/config';
import { Layout as LayoutIcon, Settings } from 'lucide-react';

interface CaseFormProps {
  formData: TestCase;
  activeSection: string;
  isGeneratingSteps: boolean;
  assignableUsers: User[];
  onFieldChange: (path: string, value: any) => void;
  onAddStep: () => void;
  onRemoveStep: (id: string) => void;
  onUpdateStep: (id: string, field: keyof TestStep, value: string) => void;
  onAddAttachment: () => void;
  onRemoveAttachment: (id: string) => void;
  onSave: () => void;
  onQuickCreateCase: (payload: QuickCreateCasePayload) => Promise<void>;
  onCancel: () => void;
  onGenerateSteps: () => void;
  onSectionChange: (section: string) => void;
}

export const CaseForm: React.FC<CaseFormProps> = ({
  formData,
  activeSection,
  isGeneratingSteps,
  assignableUsers,
  onFieldChange,
  onAddStep,
  onRemoveStep,
  onUpdateStep,
  onAddAttachment,
  onRemoveAttachment,
  onSave,
  onQuickCreateCase,
  onCancel,
  onGenerateSteps,
  onSectionChange,
}) => {
  const activeUsers = useMemo(
    () => assignableUsers.filter(user => user.status === 'ACTIVE'),
    [assignableUsers]
  );
  const [showQuickCreateModal, setShowQuickCreateModal] = useState(false);
  const [quickCreating, setQuickCreating] = useState(false);
  const [quickCreateError, setQuickCreateError] = useState('');
  const [quickCreateData, setQuickCreateData] = useState<QuickCreateCasePayload>({
    title: '',
    ref_req_id: '',
    owner_id: '',
    reviewer_id: '',
    is_need_auto: false,
    auto_dev_id: '',
    workflow_note: '',
    planned_due_date: '',
    automation_case_id: '',
    automation_case_version: '',
    source_case_id: '',
  });

  const supportsAutomation = formData.is_need_auto
    || formData.is_automated
    || Boolean(formData.auto_dev_id?.trim())
    || Boolean(formData.automation_type?.trim())
    || Boolean(formData.script_entity_id?.trim());

  const sections = [
    { id: 'basic', label: '基础', icon: LayoutIcon },
    { id: 'env', label: '环境', icon: Cpu },
    ...(supportsAutomation ? [{ id: 'automation', label: '自动化', icon: Settings }] : []),
    { id: 'steps', label: '步骤', icon: PlayCircle },
    { id: 'attachments', label: '附件', icon: Paperclip },
    { id: 'history', label: '历史', icon: History },
  ];

  useEffect(() => {
    if (!supportsAutomation && activeSection === 'automation') {
      onSectionChange('basic');
    }
  }, [supportsAutomation, activeSection, onSectionChange]);

  const automationChecklist = [
    { label: '自动化负责人', ready: Boolean(formData.auto_dev_id?.trim()) },
    { label: '自动化类型', ready: Boolean(formData.automation_type?.trim()) },
    { label: '脚本实体 ID', ready: Boolean(formData.script_entity_id?.trim()) },
    { label: '执行环境（OS）', ready: Boolean(formData.required_env.os?.trim()) },
    { label: '测试步骤 >= 1', ready: formData.steps.length > 0 },
  ];
  const automationReadyCount = automationChecklist.filter(item => item.ready).length;
  const automationReadyRate = Math.round((automationReadyCount / automationChecklist.length) * 100);

  const openQuickCreateModal = () => {
    const defaultOwner = formData.owner_id || activeUsers[0]?.user_id || '';
    setQuickCreateData({
      title: '',
      ref_req_id: formData.ref_req_id || '',
      owner_id: defaultOwner,
      reviewer_id: formData.reviewer_id || '',
      is_need_auto: formData.is_need_auto,
      auto_dev_id: formData.auto_dev_id || '',
      workflow_note: '',
      planned_due_date: '',
      automation_case_id: String(formData.custom_fields.automation_case_id || ''),
      automation_case_version: String(formData.custom_fields.automation_case_version || ''),
      source_case_id: formData.case_id,
    });
    setQuickCreateError('');
    setShowQuickCreateModal(true);
  };

  const updateQuickCreateField = (field: keyof QuickCreateCasePayload, value: string | boolean) => {
    setQuickCreateData(prev => ({ ...prev, [field]: value }));
  };

  const submitQuickCreate = async () => {
    if (!quickCreateData.title?.trim()) {
      setQuickCreateError('请填写用例标题');
      return;
    }
    if (!quickCreateData.ref_req_id?.trim()) {
      setQuickCreateError('请填写关联需求 ID');
      return;
    }
    if (!quickCreateData.owner_id?.trim()) {
      setQuickCreateError('请指定开发负责人');
      return;
    }
    if (quickCreateData.is_need_auto && !quickCreateData.auto_dev_id?.trim()) {
      setQuickCreateError('该用例需要自动化，请填写自动化负责人');
      return;
    }

    setQuickCreateError('');
    setQuickCreating(true);
    try {
      await onQuickCreateCase({
        ...quickCreateData,
        title: quickCreateData.title.trim(),
        ref_req_id: quickCreateData.ref_req_id.trim(),
        owner_id: quickCreateData.owner_id.trim(),
        reviewer_id: quickCreateData.reviewer_id?.trim(),
        auto_dev_id: quickCreateData.auto_dev_id?.trim(),
        workflow_note: quickCreateData.workflow_note?.trim(),
        automation_case_id: quickCreateData.automation_case_id?.trim(),
        automation_case_version: quickCreateData.automation_case_version?.trim(),
      });
      setShowQuickCreateModal(false);
    } catch (error: any) {
      setQuickCreateError(error?.message || '创建失败，请稍后重试');
    } finally {
      setQuickCreating(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA] selection:bg-indigo-100 text-[#1A1A1A]">
      {/* Top Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-slate-200/60 px-8 py-4 flex items-center justify-between shadow-sm transition-all duration-200">
        <div className="flex items-center gap-5">
          <button onClick={onCancel} className="p-2.5 hover:bg-slate-100 rounded-xl transition-all text-slate-500 hover:text-slate-700 active:scale-95">
            <ChevronRight size={22} className="rotate-180" />
          </button>
          <div className="bg-slate-900 p-2.5 rounded-xl text-white shadow-lg shadow-slate-900/20">
            <FileText size={22} />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono font-bold text-indigo-600 tracking-wider uppercase bg-indigo-50 px-2 py-0.5 rounded-lg border border-indigo-100">{formData.case_id}</span>
              <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-lg border border-slate-200 font-bold">V{formData.version}</span>
            </div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">{formData.title || '新建测试用例'}</h1>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={openQuickCreateModal}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold border border-indigo-200 text-indigo-700 bg-indigo-50 hover:bg-indigo-100 transition-all active:scale-95"
          >
            <Plus size={16} />
            创建自动化测试用例
          </button>
          <button onClick={onCancel} className="px-5 py-2.5 text-sm font-bold text-slate-500 hover:bg-slate-100 hover:text-slate-700 rounded-xl transition-all">
            取消
          </button>
          <button onClick={onSave} className="flex items-center gap-2 px-8 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all shadow-lg hover:shadow-xl hover:shadow-slate-900/20 active:scale-95">
            <Save size={18} />
            保存用例
          </button>
        </div>
      </header>

      <div className="max-w-[1600px] mx-auto px-8 py-10 grid grid-cols-12 gap-10">
        {/* Left Sidebar - Section Navigation */}
        <aside className="col-span-2 sticky top-28 h-fit space-y-6">
          <nav className="bg-white rounded-[1.5rem] border border-slate-100 shadow-xl shadow-slate-100/50 p-4 space-y-2">
            {sections.map(section => (
              <button
                key={section.id}
                onClick={() => {
                  onSectionChange(section.id);
                  document.getElementById(section.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }}
                className={`w-full flex items-center gap-4 px-5 py-4 rounded-xl text-sm font-bold transition-all group ${
                  activeSection === section.id
                    ? 'bg-slate-900 text-white shadow-lg shadow-slate-900/20 scale-100'
                    : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900 hover:scale-[1.02]'
                }`}
              >
                <section.icon size={18} className={`transition-colors ${activeSection === section.id ? 'text-white' : 'text-slate-400 group-hover:text-slate-600'}`} />
                {section.label}
              </button>
            ))}
          </nav>
        </aside>

        {/* Main Form Content */}
        <main className="col-span-10 space-y-8 pb-32">

          {/* Section: Basic Info */}
          <section id="basic" className="bg-white rounded-[2.5rem] border border-slate-100 shadow-2xl shadow-slate-100/50 overflow-hidden">
            <div className="px-10 py-8 border-b border-slate-50 bg-slate-50/30 flex items-center gap-4">
              <div className="p-3 bg-white text-slate-900 rounded-2xl shadow-sm border border-slate-100">
                <LayoutIcon size={20} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-900">基础信息</h2>
                <p className="text-xs text-slate-400 font-medium mt-0.5">定义用例的核心属性与分类</p>
              </div>
            </div>
            <div className="p-10 grid grid-cols-12 gap-8">
              <div className="col-span-8">
                <label className="flex items-center text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
                  用例标题
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => onFieldChange('title', e.target.value)}
                  placeholder="输入用例标题..."
                  className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-base font-bold placeholder:font-medium placeholder:text-slate-400"
                />
              </div>
              <div className="col-span-4">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">类别</label>
                <div className="relative">
                  <select
                    value={formData.test_category}
                    onChange={(e) => onFieldChange('test_category', e.target.value)}
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold text-slate-700 appearance-none cursor-pointer"
                  >
                    <option value={TestCaseCategory.FUNCTIONAL}>功能测试 (Functional)</option>
                    <option value={TestCaseCategory.STRESS}>压力测试 (Stress)</option>
                    <option value={TestCaseCategory.PERFORMANCE}>性能测试 (Performance)</option>
                    <option value={TestCaseCategory.COMPATIBILITY}>兼容性测试 (Compatibility)</option>
                    <option value={TestCaseCategory.STABILITY}>稳定性测试 (Stability)</option>
                    <option value={TestCaseCategory.SECURITY}>安全测试 (Security)</option>
                  </select>
                  <ChevronRight className="absolute right-6 top-1/2 -translate-y-1/2 rotate-90 text-slate-400 pointer-events-none" size={16} />
                </div>
              </div>
              <div className="col-span-4">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">需求ID</label>
                <input
                  type="text"
                  value={formData.ref_req_id}
                  onChange={(e) => onFieldChange('ref_req_id', e.target.value)}
                  className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold font-mono"
                  placeholder="TR-XXX"
                />
              </div>
              <div className="col-span-4">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">机密等级</label>
                <div className="relative">
                  <select
                    value={formData.confidentiality}
                    onChange={(e) => onFieldChange('confidentiality', e.target.value)}
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold text-slate-700 appearance-none cursor-pointer"
                  >
                    <option value={Confidentiality.PUBLIC}>公开 (Public)</option>
                    <option value={Confidentiality.INTERNAL}>内部 (Internal)</option>
                    <option value={Confidentiality.NDA}>保密 (Confidential)</option>
                  </select>
                  <ChevronRight className="absolute right-6 top-1/2 -translate-y-1/2 rotate-90 text-slate-400 pointer-events-none" size={16} />
                </div>
              </div>
              <div className="col-span-4">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">预估耗时 (分钟)</label>
                <input
                  type="number"
                  value={Math.round((formData.estimated_duration_sec || 0) / 60)}
                  onChange={(e) => onFieldChange('estimated_duration_sec', parseInt(e.target.value) * 60)}
                  className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold"
                />
              </div>
              <div className="col-span-12">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">标签 (Tags)</label>
                <div className="flex flex-wrap gap-3 p-4 rounded-2xl border border-slate-200 bg-slate-50/30 min-h-[80px] items-start">
                  {formData.tags.map(tag => (
                    <span key={tag} className="flex items-center gap-2 px-4 py-2 bg-white text-slate-700 rounded-xl border border-slate-200 text-sm font-bold shadow-sm transition-transform hover:scale-105 cursor-default">
                      {tag}
                      <button className="hover:text-rose-500 text-slate-400 transition-colors p-0.5 hover:bg-rose-50 rounded-full">
                        <X size={14} />
                      </button>
                    </span>
                  ))}
                  <button className="flex items-center gap-1.5 text-indigo-600 hover:text-indigo-700 text-sm font-bold px-4 py-2 hover:bg-indigo-50 rounded-xl border border-dashed border-indigo-200 hover:border-indigo-300 transition-all active:scale-95">
                    <Plus size={16} />
                    添加标签
                  </button>
                </div>
              </div>
              <div className="col-span-12">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">执行属性</label>
                <div className="grid grid-cols-3 gap-4">
                  <label className="group flex items-center justify-between p-4 rounded-2xl border border-slate-200 bg-slate-50/40 hover:border-indigo-300 transition-colors cursor-pointer">
                    <span className="text-sm font-bold text-slate-700">支持自动化</span>
                    <input
                      type="checkbox"
                      checked={formData.is_need_auto}
                      onChange={(e) => onFieldChange('is_need_auto', e.target.checked)}
                      className="h-4 w-4 accent-indigo-600"
                    />
                  </label>
                  <label className="group flex items-center justify-between p-4 rounded-2xl border border-slate-200 bg-slate-50/40 hover:border-indigo-300 transition-colors cursor-pointer">
                    <span className="text-sm font-bold text-slate-700">已自动化</span>
                    <input
                      type="checkbox"
                      checked={formData.is_automated}
                      onChange={(e) => onFieldChange('is_automated', e.target.checked)}
                      className="h-4 w-4 accent-indigo-600"
                    />
                  </label>
                  <label className="group flex items-center justify-between p-4 rounded-2xl border border-slate-200 bg-slate-50/40 hover:border-indigo-300 transition-colors cursor-pointer">
                    <span className="text-sm font-bold text-slate-700">破坏性测试</span>
                    <input
                      type="checkbox"
                      checked={formData.is_destructive}
                      onChange={(e) => onFieldChange('is_destructive', e.target.checked)}
                      className="h-4 w-4 accent-indigo-600"
                    />
                  </label>
                </div>
              </div>
            </div>
          </section>

          {/* Section: Hardware & Environment */}
          <section id="env" className="bg-white rounded-[2.5rem] border border-slate-100 shadow-2xl shadow-slate-100/50 overflow-hidden">
            <div className="px-10 py-8 border-b border-slate-50 bg-slate-50/30 flex items-center gap-4">
              <div className="p-3 bg-white text-slate-900 rounded-2xl shadow-sm border border-slate-100">
                <Cpu size={20} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-900">硬件与环境</h2>
                <p className="text-xs text-slate-400 font-medium mt-0.5">测试所需的软硬件环境配置</p>
              </div>
            </div>

            <div className="p-10 space-y-8">
              <div className="grid grid-cols-12 gap-8">
                <div className="col-span-6">
                  <label className="flex items-center text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
                    目标部件 (PN/类别)
                  </label>
                  <div className="relative group">
                    <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input
                      type="text"
                      value={formData.target_components.join(', ')}
                      onChange={(e) => onFieldChange('target_components', e.target.value.split(',').map(s => s.trim()))}
                      className="w-full pl-12 pr-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold"
                      placeholder="搜索或输入部件..."
                    />
                  </div>
                </div>
                <div className="col-span-6">
                  <label className="flex items-center text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
                    平台型号
                  </label>
                  <input
                    type="text"
                    value={formData.required_env.hardware}
                    onChange={(e) => onFieldChange('required_env.hardware', e.target.value)}
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold"
                    placeholder="e.g. Whitley, Eagle Stream"
                  />
                </div>
                <div className="col-span-6">
                  <label className="flex items-center text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
                    操作系统
                  </label>
                  <input
                    type="text"
                    value={formData.required_env.os}
                    onChange={(e) => onFieldChange('required_env.os', e.target.value)}
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold"
                    placeholder="e.g. Redhat 8.6, Ubuntu 22.04"
                  />
                </div>
                <div className="col-span-6">
                  <label className="flex items-center text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
                    固件版本
                  </label>
                  <input
                    type="text"
                    value={formData.required_env.firmware}
                    onChange={(e) => onFieldChange('required_env.firmware', e.target.value)}
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold"
                    placeholder="e.g. BIOS 1.0, BMC 2.50"
                  />
                </div>
                <div className="col-span-12">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">外部工具 / 仪器设备</label>
                  <input
                    type="text"
                    value={formData.tooling_req.join(', ')}
                    onChange={(e) => onFieldChange('tooling_req', e.target.value.split(',').map(s => s.trim()))}
                    placeholder="e.g. 示波器, 恒温恒湿箱, 网络分析仪..."
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-8">
                <div>
                  <label className="flex items-center text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
                    前置条件 (Pre-condition)
                  </label>
                  <textarea
                    value={formData.pre_condition}
                    onChange={(e) => onFieldChange('pre_condition', e.target.value)}
                    rows={4}
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/50 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono leading-relaxed placeholder:text-slate-400 resize-none"
                    placeholder="描述测试开始前必须满足的硬件连接、跳线设置或系统状态..."
                  />
                </div>
                <div>
                  <label className="flex items-center text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
                    后置条件 (Post-condition)
                  </label>
                  <textarea
                    value={formData.post_condition}
                    onChange={(e) => onFieldChange('post_condition', e.target.value)}
                    rows={4}
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/50 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono leading-relaxed placeholder:text-slate-400 resize-none"
                    placeholder="描述测试完成后的系统清理工作或期望的最终状态..."
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Section: Automation */}
          {supportsAutomation && (
            <section id="automation" className="bg-white rounded-[2.5rem] border border-slate-100 shadow-2xl shadow-slate-100/50 overflow-hidden">
              <div className="px-10 py-8 border-b border-slate-50 bg-slate-50/30 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-white text-slate-900 rounded-2xl shadow-sm border border-slate-100">
                    <Settings size={20} />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-slate-900">自动化信息</h2>
                    <p className="text-xs text-slate-400 font-medium mt-0.5">自动化脚本元数据、执行入口与就绪度检查</p>
                  </div>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
                  formData.is_automated
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : 'bg-amber-50 text-amber-700 border-amber-200'
                }`}>
                  {formData.is_automated ? '已自动化' : '待自动化'}
                </span>
              </div>

              <div className="p-10 grid grid-cols-12 gap-8">
                <div className="col-span-4">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">自动化负责人</label>
                  <input
                    type="text"
                    value={formData.auto_dev_id || ''}
                    onChange={(e) => onFieldChange('auto_dev_id', e.target.value)}
                    placeholder="例如: qa_auto_zhangsan"
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold"
                  />
                </div>
                <div className="col-span-4">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">自动化类型</label>
                  <div className="relative">
                    <select
                      value={formData.automation_type || ''}
                      onChange={(e) => onFieldChange('automation_type', e.target.value)}
                      className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold text-slate-700 appearance-none cursor-pointer"
                    >
                      <option value="">请选择</option>
                      <option value="api">API</option>
                      <option value="ui">UI</option>
                      <option value="hardware">Hardware</option>
                      <option value="stress">Stress</option>
                      <option value="hybrid">Hybrid</option>
                    </select>
                    <ChevronRight className="absolute right-6 top-1/2 -translate-y-1/2 rotate-90 text-slate-400 pointer-events-none" size={16} />
                  </div>
                </div>
                <div className="col-span-4">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">脚本实体 ID</label>
                  <input
                    type="text"
                    value={formData.script_entity_id || ''}
                    onChange={(e) => onFieldChange('script_entity_id', e.target.value)}
                    placeholder="例如: script_power_cycle_v3"
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono"
                  />
                </div>
                <div className="col-span-4">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">执行框架</label>
                  <input
                    type="text"
                    value={formData.custom_fields.automation_framework || ''}
                    onChange={(e) => onFieldChange('custom_fields.automation_framework', e.target.value)}
                    placeholder="例如: pytest / robot / playwright"
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold"
                  />
                </div>
                <div className="col-span-4">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">脚本仓库</label>
                  <input
                    type="text"
                    value={formData.custom_fields.automation_repo || ''}
                    onChange={(e) => onFieldChange('custom_fields.automation_repo', e.target.value)}
                    placeholder="例如: git@repo:test/automation.git"
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono"
                  />
                </div>
                <div className="col-span-4">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">默认分支</label>
                  <input
                    type="text"
                    value={formData.custom_fields.automation_branch || ''}
                    onChange={(e) => onFieldChange('custom_fields.automation_branch', e.target.value)}
                    placeholder="例如: main / release/v1.3"
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono"
                  />
                </div>
                <div className="col-span-6">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">关联自动化用例库 ID</label>
                  <input
                    type="text"
                    value={String(formData.custom_fields.automation_case_id || '')}
                    onChange={(e) => onFieldChange('custom_fields.automation_case_id', e.target.value)}
                    placeholder="例如: AUTO-CASE-10023"
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono"
                  />
                </div>
                <div className="col-span-6">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">自动化用例版本</label>
                  <input
                    type="text"
                    value={String(formData.custom_fields.automation_case_version || '')}
                    onChange={(e) => onFieldChange('custom_fields.automation_case_version', e.target.value)}
                    placeholder="例如: v1.3.2"
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono"
                  />
                </div>
                <div className="col-span-6">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">运行依赖</label>
                  <input
                    type="text"
                    value={formData.required_env.dependencies?.join(', ') || ''}
                    onChange={(e) => onFieldChange('required_env.dependencies', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                    placeholder="例如: python3.11, ipmitool, redfish-client"
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold"
                  />
                </div>
                <div className="col-span-6">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">自动化标签</label>
                  <input
                    type="text"
                    value={formData.custom_fields.automation_labels || ''}
                    onChange={(e) => onFieldChange('custom_fields.automation_labels', e.target.value)}
                    placeholder="例如: smoke, nightly, bmc"
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold"
                  />
                </div>
                <div className="col-span-12">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">执行命令 / 触发入口</label>
                  <textarea
                    value={formData.custom_fields.automation_command || ''}
                    onChange={(e) => onFieldChange('custom_fields.automation_command', e.target.value)}
                    rows={3}
                    placeholder="例如: pytest tests/power_cycle/test_smoke.py -m smoke"
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/50 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono leading-relaxed placeholder:text-slate-400 resize-none"
                  />
                </div>
              </div>

              <div className="px-10 pb-10">
                <div className="rounded-3xl border border-slate-200 bg-slate-50/50 p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-slate-800">自动化必要字段检查</h3>
                    <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
                      automationReadyRate === 100
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-amber-50 text-amber-700 border-amber-200'
                    }`}>
                      就绪度 {automationReadyRate}%
                    </span>
                  </div>
                  <div className="grid grid-cols-5 gap-3">
                    {automationChecklist.map((item) => (
                      <div
                        key={item.label}
                        className={`flex items-center gap-2 rounded-xl px-3 py-2 border text-xs font-bold ${
                          item.ready
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : 'bg-rose-50 text-rose-700 border-rose-200'
                        }`}
                      >
                        {item.ready ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                        <span>{item.label}</span>
                      </div>
                    ))}
                  </div>
                  {automationReadyRate < 100 && (
                    <p className="text-xs text-slate-500">
                      缺失字段：
                      {automationChecklist.filter(item => !item.ready).map(item => item.label).join('、')}
                    </p>
                  )}
                </div>
              </div>
            </section>
          )}

          {/* Section: Test Steps */}
          <section id="steps" className="bg-white rounded-[2.5rem] border border-slate-100 shadow-2xl shadow-slate-100/50 overflow-hidden">
            <div className="px-10 py-8 border-b border-slate-50 bg-slate-50/30 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-white text-slate-900 rounded-2xl shadow-sm border border-slate-100">
                  <PlayCircle size={20} />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-900">测试步骤</h2>
                  <p className="text-xs text-slate-400 font-medium mt-0.5">详细的操作步骤与预期结果</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={onGenerateSteps}
                  disabled={isGeneratingSteps || !formData.ref_req_id}
                  className={`relative flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition-all active:scale-95 overflow-hidden ${
                    isGeneratingSteps
                      ? 'bg-gradient-to-r from-indigo-500 to-violet-500 text-white'
                      : 'bg-gradient-to-r from-indigo-500 to-violet-500 text-white hover:shadow-lg hover:shadow-indigo-500/30'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {/* Animated background */}
                  <motion.div
                    animate={isGeneratingSteps ? { x: ['-100%', '100%'] } : {}}
                    transition={isGeneratingSteps ? { duration: 1.5, repeat: Infinity, ease: "linear" } : {}}
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
                  />
                  <span className="relative z-10 flex items-center gap-2">
                    {isGeneratingSteps ? (
                      <>
                        <motion.span
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                        >
                          <Zap size={16} />
                        </motion.span>
                        AI 生成中...
                        <motion.span
                          className="flex gap-0.5"
                          initial={false}
                          animate={{ opacity: 1 }}
                        >
                          <span className="w-1 h-1 bg-white rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="w-1 h-1 bg-white rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="w-1 h-1 bg-white rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </motion.span>
                      </>
                    ) : (
                      <>
                        <Zap size={16} className="text-amber-300" />
                        AI 智能生成
                      </>
                    )}
                  </span>
                </button>
                <button
                  onClick={onAddStep}
                  className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition-all active:scale-95 shadow-lg shadow-slate-900/20"
                >
                  <Plus size={16} /> 添加步骤
                </button>
              </div>
            </div>
            <div className="p-10">
              <div className="space-y-4">
                <AnimatePresence initial={false}>
                  {formData.steps.map((step, index) => (
                    <motion.div
                      key={step.step_id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className="group relative flex gap-6 p-6 rounded-[1.5rem] border border-slate-200 bg-white hover:border-indigo-300 hover:shadow-lg hover:shadow-indigo-100/30 transition-all"
                    >
                      <div className="flex flex-col items-center gap-3 pt-1">
                        <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center text-sm font-bold border border-slate-200 shadow-inner">
                          {index + 1}
                        </div>
                        <GripVertical className="text-slate-300 cursor-grab active:cursor-grabbing hover:text-indigo-400 transition-colors" size={20} />
                      </div>
                      <div className="flex-1 grid grid-cols-12 gap-8">
                        <div className="col-span-12">
                          <input
                            type="text"
                            value={step.name}
                            onChange={(e) => onUpdateStep(step.step_id, 'name', e.target.value)}
                            placeholder="步骤名称 (例如：上电循环)"
                            className="w-full px-0 py-2 text-lg font-bold bg-transparent border-b border-transparent focus:border-indigo-500 outline-none transition-all placeholder:text-slate-300 text-slate-900"
                          />
                        </div>
                        <div className="col-span-6">
                          <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">操作 / 命令</label>
                          <textarea
                            value={step.action}
                            onChange={(e) => onUpdateStep(step.step_id, 'action', e.target.value)}
                            rows={3}
                            className="w-full px-5 py-4 rounded-2xl border border-slate-200 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm bg-slate-50/30 focus:bg-white resize-none"
                            placeholder="详细的操作指令或步骤描述..."
                          />
                        </div>
                        <div className="col-span-6">
                          <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">预期结果</label>
                          <textarea
                            value={step.expected}
                            onChange={(e) => onUpdateStep(step.step_id, 'expected', e.target.value)}
                            rows={3}
                            className="w-full px-5 py-4 rounded-2xl border border-slate-200 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm bg-slate-50/30 focus:bg-white resize-none"
                            placeholder="期望的系统响应或输出结果..."
                          />
                        </div>
                      </div>
                      <button
                        onClick={() => onRemoveStep(step.step_id)}
                        className="absolute -right-3 -top-3 opacity-0 group-hover:opacity-100 w-10 h-10 bg-white border border-rose-200 text-rose-500 rounded-full flex items-center justify-center hover:bg-rose-50 transition-all shadow-md transform scale-75 group-hover:scale-100 duration-200"
                      >
                        <Trash2 size={16} />
                      </button>
                    </motion.div>
                  ))}
                </AnimatePresence>
                {formData.steps.length === 0 && (
                  <div className="py-16 text-center border-2 border-dashed border-slate-200 rounded-[1.5rem] bg-slate-50/30">
                    <p className="text-sm font-bold text-slate-400">暂无测试步骤</p>
                    <p className="text-xs text-slate-400 mt-2">点击上方按钮添加步骤或使用 AI 生成</p>
                  </div>
                )}
              </div>
            </div>
          </section>

          <div className="grid grid-cols-2 gap-10">
            {/* Section: Attachments */}
            <section id="attachments" className="bg-white rounded-[2.5rem] border border-slate-100 shadow-2xl shadow-slate-100/50 overflow-hidden">
              <div className="px-10 py-8 border-b border-slate-50 bg-slate-50/30 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-white text-slate-900 rounded-2xl shadow-sm border border-slate-100">
                    <Paperclip size={20} />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-slate-900">附件管理</h2>
                    <p className="text-xs text-slate-400 font-medium mt-0.5">相关文档与截图</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={onAddAttachment} className="p-2.5 hover:bg-slate-100 rounded-xl text-slate-500 transition-colors">
                    <Plus size={20} />
                  </button>
                </div>
              </div>
              <div className="p-8">
                {formData.attachments.length === 0 ? (
                  <div className="py-12 text-center border-2 border-dashed border-slate-200 rounded-[1.5rem] bg-slate-50/30">
                    <p className="text-xs font-bold text-slate-300 uppercase tracking-wider">暂无附件</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {formData.attachments.map(att => (
                      <div key={att.id} className="flex items-center gap-4 p-4 rounded-2xl bg-slate-50 border border-slate-100 group hover:border-indigo-200 transition-all">
                        <div className="p-2.5 bg-white rounded-xl border border-slate-100 text-slate-400">
                          <FileText size={18} />
                        </div>
                        <span className="text-sm font-bold text-slate-700 truncate flex-1">{att.name}</span>
                        <button onClick={() => onRemoveAttachment(att.id)} className="opacity-0 group-hover:opacity-100 text-slate-300 hover:text-rose-500 p-2 hover:bg-rose-50 rounded-xl transition-all">
                          <Trash2 size={18} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>

            {/* Section: Approval History */}
            <section id="history" className="bg-white rounded-[2.5rem] border border-slate-100 shadow-2xl shadow-slate-100/50 overflow-hidden">
              <div className="px-10 py-8 border-b border-slate-50 bg-slate-50/30 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-slate-900 text-white rounded-2xl shadow-sm border border-slate-100">
                    <History size={20} />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-slate-900">审批历史</h2>
                    <p className="text-xs text-slate-400 font-medium mt-0.5">版本变更与评审记录</p>
                  </div>
                </div>
              </div>
              <div className="p-8">
                {formData.approval_history.length === 0 ? (
                  <div className="py-12 text-center border-2 border-dashed border-slate-200 rounded-[1.5rem] bg-slate-50/30">
                    <p className="text-xs font-bold text-slate-300 uppercase tracking-wider">暂无记录</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {formData.approval_history.map((record, i) => (
                      <div key={i} className="flex gap-4 p-4 rounded-2xl bg-slate-50 border border-slate-100">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                          record.result === 'approved' ? 'bg-emerald-100 text-emerald-600' : 'bg-rose-100 text-rose-600'
                        }`}>
                          {record.result === 'approved' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-3 mb-1">
                            <span className="text-sm font-bold text-slate-900">{record.approver}</span>
                            <span className="text-[10px] text-slate-400 font-mono">{record.timestamp}</span>
                          </div>
                          <p className="text-xs text-slate-500 truncate italic">"{record.comment}"</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-between p-6 bg-white rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-100/50 mt-8">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2.5">
                <div className="relative">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-ping absolute opacity-75" />
                  <div className="w-2 h-2 rounded-full bg-emerald-400 relative" />
                </div>
                <span className="text-xs font-bold text-slate-400">自动保存已开启</span>
              </div>
              <div className="h-4 w-px bg-slate-200" />
              <span className="text-xs text-slate-400">
                最后更新 <span className="text-slate-600 font-medium ml-1">{new Date(formData.updated_at).toLocaleString()}</span>
              </span>
            </div>
            <div className="flex items-center gap-3">
              <button className="px-6 py-2.5 text-sm font-bold text-slate-600 bg-slate-50 border border-slate-200 rounded-xl hover:bg-slate-100 hover:border-slate-300 transition-all active:scale-95">
                导出 PDF
              </button>
              <button className="px-8 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all shadow-lg shadow-slate-900/20 active:scale-95">
                提交评审
              </button>
            </div>
          </div>
        </main>
      </div>

      <AnimatePresence>
        {showQuickCreateModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[80] bg-slate-900/40 backdrop-blur-sm flex items-start justify-center p-6 overflow-y-auto"
            style={{ scrollBehavior: 'smooth' }}
          >
            <motion.div
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.98 }}
              transition={{ duration: 0.2 }}
              className="w-full max-w-4xl bg-white rounded-[2rem] border border-slate-100 shadow-2xl shadow-slate-900/20 overflow-hidden my-8"
            >
              <div className="px-8 py-6 border-b border-slate-100 bg-slate-50/40 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-slate-900">创建自动化测试用例</h3>
                  <p className="text-xs text-slate-500 mt-1">填写基础信息后创建并指派开发人，进入任务流</p>
                </div>
                <button
                  onClick={() => setShowQuickCreateModal(false)}
                  className="p-2 rounded-xl text-slate-500 hover:bg-slate-100 transition-colors"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="p-8 grid grid-cols-12 gap-6">
                <div className="col-span-8">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">用例标题 *</label>
                  <input
                    type="text"
                    value={quickCreateData.title}
                    onChange={(e) => updateQuickCreateField('title', e.target.value)}
                    placeholder="例如：BMC 冷启动后传感器数据一致性校验"
                    className="w-full px-5 py-3 rounded-xl border border-slate-200 bg-slate-50/40 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-semibold"
                  />
                </div>
                <div className="col-span-4">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">关联需求 ID *</label>
                  <input
                    type="text"
                    value={quickCreateData.ref_req_id}
                    onChange={(e) => updateQuickCreateField('ref_req_id', e.target.value)}
                    placeholder="TR-2026-001"
                    className="w-full px-5 py-3 rounded-xl border border-slate-200 bg-slate-50/40 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono"
                  />
                </div>
                <div className="col-span-4">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">开发负责人 *</label>
                  {activeUsers.length > 0 ? (
                    <select
                      value={quickCreateData.owner_id || ''}
                      onChange={(e) => updateQuickCreateField('owner_id', e.target.value)}
                      className="w-full px-5 py-3 rounded-xl border border-slate-200 bg-slate-50/40 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-semibold"
                    >
                      <option value="">请选择开发负责人</option>
                      {activeUsers.map(user => (
                        <option key={user.user_id} value={user.user_id}>
                          {user.username} ({user.user_id})
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={quickCreateData.owner_id || ''}
                      onChange={(e) => updateQuickCreateField('owner_id', e.target.value)}
                      placeholder="输入用户 ID"
                      className="w-full px-5 py-3 rounded-xl border border-slate-200 bg-slate-50/40 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono"
                    />
                  )}
                </div>
                <div className="col-span-4">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">评审人</label>
                  {activeUsers.length > 0 ? (
                    <select
                      value={quickCreateData.reviewer_id || ''}
                      onChange={(e) => updateQuickCreateField('reviewer_id', e.target.value)}
                      className="w-full px-5 py-3 rounded-xl border border-slate-200 bg-slate-50/40 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-semibold"
                    >
                      <option value="">请选择评审人</option>
                      {activeUsers.map(user => (
                        <option key={user.user_id} value={user.user_id}>
                          {user.username} ({user.user_id})
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={quickCreateData.reviewer_id || ''}
                      onChange={(e) => updateQuickCreateField('reviewer_id', e.target.value)}
                      placeholder="输入用户 ID"
                      className="w-full px-5 py-3 rounded-xl border border-slate-200 bg-slate-50/40 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono"
                    />
                  )}
                </div>
                <div className="col-span-4">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">计划完成日期</label>
                  <input
                    type="date"
                    value={quickCreateData.planned_due_date || ''}
                    onChange={(e) => updateQuickCreateField('planned_due_date', e.target.value)}
                    className="w-full px-5 py-3 rounded-xl border border-slate-200 bg-slate-50/40 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-semibold"
                  />
                </div>
                <div className="col-span-12">
                  <div className="flex items-center justify-between p-4 rounded-xl border border-slate-200 bg-slate-50/40">
                    <span className="text-sm font-bold text-slate-700">该用例需要自动化开发</span>
                    <input
                      type="checkbox"
                      checked={quickCreateData.is_need_auto}
                      onChange={(e) => updateQuickCreateField('is_need_auto', e.target.checked)}
                      className="h-4 w-4 accent-indigo-600"
                    />
                  </div>
                </div>
                {quickCreateData.is_need_auto && (
                  <div className="col-span-6">
                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">自动化负责人 *</label>
                    {activeUsers.length > 0 ? (
                      <select
                        value={quickCreateData.auto_dev_id || ''}
                        onChange={(e) => updateQuickCreateField('auto_dev_id', e.target.value)}
                        className="w-full px-5 py-3 rounded-xl border border-slate-200 bg-slate-50/40 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-semibold"
                      >
                        <option value="">请选择自动化负责人</option>
                        {activeUsers.map(user => (
                          <option key={user.user_id} value={user.user_id}>
                            {user.username} ({user.user_id})
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={quickCreateData.auto_dev_id || ''}
                        onChange={(e) => updateQuickCreateField('auto_dev_id', e.target.value)}
                        placeholder="输入用户 ID"
                        className="w-full px-5 py-3 rounded-xl border border-slate-200 bg-slate-50/40 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono"
                      />
                    )}
                  </div>
                )}
                <div className="col-span-6">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">自动化用例库 ID</label>
                  <input
                    type="text"
                    value={quickCreateData.automation_case_id || ''}
                    onChange={(e) => updateQuickCreateField('automation_case_id', e.target.value)}
                    placeholder="AUTO-CASE-10023"
                    className="w-full px-5 py-3 rounded-xl border border-slate-200 bg-slate-50/40 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono"
                  />
                </div>
                <div className="col-span-6">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">自动化用例版本</label>
                  <input
                    type="text"
                    value={quickCreateData.automation_case_version || ''}
                    onChange={(e) => updateQuickCreateField('automation_case_version', e.target.value)}
                    placeholder="v1.0.0"
                    className="w-full px-5 py-3 rounded-xl border border-slate-200 bg-slate-50/40 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono"
                  />
                </div>
                <div className="col-span-12">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">任务说明</label>
                  <textarea
                    value={quickCreateData.workflow_note || ''}
                    onChange={(e) => updateQuickCreateField('workflow_note', e.target.value)}
                    rows={3}
                    placeholder="描述开发目标、关键验收点或注意事项"
                    className="w-full px-5 py-3 rounded-xl border border-slate-200 bg-slate-50/40 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm resize-none"
                  />
                </div>
              </div>

              <div className="px-8 pb-6">
                <div className="rounded-xl border border-slate-200 bg-slate-50/50 px-4 py-3 text-xs text-slate-600">
                  创建后将自动生成任务流事项并指派给负责人，开发完成后可在该详情页补充步骤、脚本与自动化字段后保存。
                </div>
              </div>

              <div className="px-8 py-5 border-t border-slate-100 flex items-center justify-between">
                {quickCreateError ? (
                  <span className="text-xs font-bold text-rose-600">{quickCreateError}</span>
                ) : (
                  <span className="text-xs text-slate-500">* 为必填字段</span>
                )}
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setShowQuickCreateModal(false)}
                    className="px-5 py-2.5 rounded-xl text-sm font-bold text-slate-600 hover:bg-slate-100 transition-colors"
                    disabled={quickCreating}
                  >
                    取消
                  </button>
                  <button
                    onClick={submitQuickCreate}
                    disabled={quickCreating}
                    className="px-6 py-2.5 rounded-xl text-sm font-bold text-white bg-slate-900 hover:bg-slate-800 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    {quickCreating ? '创建中...' : '创建并进入详情'}
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
