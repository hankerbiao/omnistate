import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  ChevronRight,
  Save,
  Layout,
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
import { TestCase, TestCaseStatus, Priority, TestCaseCategory, Confidentiality, TestStep } from '../../types';
import { Layout as LayoutIcon, Settings } from 'lucide-react';

interface CaseFormProps {
  formData: TestCase;
  activeSection: string;
  isGeneratingSteps: boolean;
  onFieldChange: (path: string, value: any) => void;
  onAddStep: () => void;
  onRemoveStep: (id: string) => void;
  onUpdateStep: (id: string, field: keyof TestStep, value: string) => void;
  onAddAttachment: () => void;
  onRemoveAttachment: (id: string) => void;
  onSave: () => void;
  onCancel: () => void;
  onGenerateSteps: () => void;
  onSectionChange: (section: string) => void;
}

export const CaseForm: React.FC<CaseFormProps> = ({
  formData,
  activeSection,
  isGeneratingSteps,
  onFieldChange,
  onAddStep,
  onRemoveStep,
  onUpdateStep,
  onAddAttachment,
  onRemoveAttachment,
  onSave,
  onCancel,
  onGenerateSteps,
  onSectionChange,
}) => {
  const sections = [
    { id: 'basic', label: '基础', icon: LayoutIcon },
    { id: 'env', label: '环境', icon: Cpu },
    { id: 'steps', label: '步骤', icon: PlayCircle },
    { id: 'attachments', label: '附件', icon: Paperclip },
    { id: 'history', label: '历史', icon: History },
  ];

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
    </div>
  );
};
