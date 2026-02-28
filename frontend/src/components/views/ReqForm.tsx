import React from 'react';
import { motion } from 'motion/react';
import {
  Plus,
  ChevronRight,
  Save,
  Layout,
  Cpu,
  Settings,
  Paperclip,
  FileText,
  Trash2,
  AlertCircle,
  Zap,
} from 'lucide-react';
import { TestRequirement, Priority, RequirementStatus } from '../../types';
import { COMPONENT_CATEGORIES } from '../../constants/config';

interface ReqFormProps {
  formData: TestRequirement;
  activeSection: string;
  isPolishing: { [key: string]: boolean };
  onFieldChange: (field: keyof TestRequirement, value: any) => void;
  onSave: () => void;
  onCancel: () => void;
  onAddAttachment: () => void;
  onRemoveAttachment: (id: string) => void;
  onToggleComponent: (comp: string) => void;
  onPolishText: (field: 'description' | 'technical_spec') => void;
  onSectionChange: (section: string) => void;
}

export const ReqForm: React.FC<ReqFormProps> = ({
  formData,
  activeSection,
  isPolishing,
  onFieldChange,
  onSave,
  onCancel,
  onAddAttachment,
  onRemoveAttachment,
  onToggleComponent,
  onPolishText,
  onSectionChange,
}) => {
  const reqTabs = [
    { id: 'basic', label: '基础', icon: Layout },
    { id: 'tech', label: '技术', icon: Cpu },
    { id: 'params', label: '参数', icon: Settings },
    { id: 'attach', label: '附件', icon: Paperclip },
  ];

  return (
    <div className="min-h-screen bg-[#F8F9FA] selection:bg-indigo-100 text-[#1A1A1A]">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-slate-200/60 px-8 py-4 flex items-center justify-between shadow-sm transition-all duration-200">
        <div className="flex items-center gap-5">
          <button onClick={onCancel} className="p-2.5 hover:bg-slate-100 rounded-xl transition-all text-slate-500 hover:text-slate-700 active:scale-95">
            <ChevronRight size={22} className="rotate-180" />
          </button>
          <div className="bg-slate-900 p-2.5 rounded-xl text-white shadow-lg shadow-slate-900/20">
            <Layout size={22} />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono font-bold text-indigo-600 tracking-wider uppercase bg-indigo-50 px-2 py-0.5 rounded-lg border border-indigo-100">{formData.req_id}</span>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest bg-slate-100 px-2 py-0.5 rounded-lg">DRAFT</span>
            </div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">{formData.title || '新建测试需求'}</h1>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button onClick={onCancel} className="px-5 py-2.5 text-sm font-bold text-slate-500 hover:bg-slate-100 hover:text-slate-700 rounded-xl transition-all">
            取消
          </button>
          <button onClick={onSave} className="flex items-center gap-2 px-8 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all shadow-lg hover:shadow-xl hover:shadow-slate-900/20 active:scale-95">
            <Save size={18} />
            保存需求
          </button>
        </div>
      </header>

      {/* Content Area */}
      <div className="max-w-[1600px] mx-auto px-8 py-10 grid grid-cols-12 gap-10">
        {/* Left Sidebar - Section Navigation */}
        <aside className="col-span-2 sticky top-28 h-fit space-y-6">
          <nav className="bg-white rounded-[1.5rem] border border-slate-100 shadow-xl shadow-slate-100/50 p-4 space-y-2">
            {reqTabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => {
                  onSectionChange(tab.id);
                  document.getElementById(tab.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }}
                className={`w-full flex items-center gap-4 px-5 py-4 rounded-xl text-sm font-bold transition-all group ${
                  activeSection === tab.id
                    ? 'bg-slate-900 text-white shadow-lg shadow-slate-900/20 scale-100'
                    : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900 hover:scale-[1.02]'
                }`}
              >
                <tab.icon size={18} className={`transition-colors ${activeSection === tab.id ? 'text-white' : 'text-slate-400 group-hover:text-slate-600'}`} />
                {tab.label}
              </button>
            ))}
          </nav>

          {/* Quick Stats / Info */}
          <div className="p-6 bg-white rounded-[1.5rem] border border-slate-100 shadow-xl shadow-slate-100/50 space-y-6">
            <div>
              <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">当前状态</h3>
              <div className="flex items-center gap-2">
                <div className={`w-2.5 h-2.5 rounded-full ${
                  formData.status === RequirementStatus.CLOSED ? 'bg-emerald-500' : 'bg-amber-500'
                }`} />
                <span className="text-sm font-bold text-slate-700">
                  {formData.status === RequirementStatus.PENDING ? '待指派' : formData.status === RequirementStatus.DEVELOPING ? '开发中' : formData.status === RequirementStatus.REVIEWING ? '评审中' : '已闭环'}
                </span>
              </div>
            </div>
            <div>
              <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">优先级</h3>
              <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold ${
                formData.priority === Priority.P0 ? 'bg-rose-50 text-rose-600 border border-rose-100' : 'bg-amber-50 text-amber-600 border border-amber-100'
              }`}>
                <AlertCircle size={12} />
                {formData.priority}
              </span>
            </div>
          </div>
        </aside>

        {/* Main Content - All Sections */}
        <main className="col-span-10 space-y-8 pb-32">

          {/* Section: Basic Info */}
          <section id="basic" className="bg-white rounded-[2.5rem] border border-slate-100 shadow-2xl shadow-slate-100/50 overflow-hidden">
            <div className="px-10 py-8 border-b border-slate-50 bg-slate-50/30 flex items-center gap-4">
              <div className="p-3 bg-white text-slate-900 rounded-2xl shadow-sm border border-slate-100">
                <Layout size={20} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-900">基础信息</h2>
                <p className="text-xs text-slate-400 font-medium mt-0.5">定义需求的核心属性与负责人</p>
              </div>
            </div>

            <div className="p-10 grid grid-cols-12 gap-8">
              <div className="col-span-8">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">需求标题</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => onFieldChange('title', e.target.value)}
                  className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-base font-bold placeholder:font-medium placeholder:text-slate-400"
                  placeholder="输入简明扼要的需求标题..."
                />
              </div>
              <div className="col-span-4">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">优先级</label>
                <div className="relative">
                  <select
                    value={formData.priority}
                    onChange={(e) => onFieldChange('priority', e.target.value)}
                    className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-base font-bold appearance-none cursor-pointer text-slate-700"
                  >
                    <option value={Priority.P0}>P0 - 紧急 (Urgent)</option>
                    <option value={Priority.P1}>P1 - 高 (High)</option>
                    <option value={Priority.P2}>P2 - 普通 (Normal)</option>
                  </select>
                  <ChevronRight className="absolute right-6 top-1/2 -translate-y-1/2 rotate-90 text-slate-400 pointer-events-none" size={20} />
                </div>
              </div>

              <div className="col-span-4">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">TPM 负责人</label>
                <input
                  type="text"
                  value={formData.tpm_owner_id}
                  onChange={(e) => onFieldChange('tpm_owner_id', e.target.value)}
                  className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold"
                  placeholder="例如: alice"
                />
              </div>

              <div className="col-span-12">
                <div className="flex items-center justify-between mb-3">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider">详细描述</label>
                  <button
                    onClick={() => onPolishText('description')}
                    disabled={isPolishing['description'] || !formData.description}
                    className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-95 ${
                      isPolishing['description']
                        ? 'bg-gradient-to-r from-indigo-500 to-violet-500 text-white'
                        : 'bg-gradient-to-r from-indigo-500 to-violet-500 text-white hover:shadow-lg hover:shadow-indigo-500/30'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    <motion.span
                      animate={isPolishing['description'] ? { rotate: 360 } : {}}
                      transition={isPolishing['description'] ? { duration: 1, repeat: Infinity, ease: "linear" } : {}}
                    >
                      <Zap size={14} className={isPolishing['description'] ? 'text-amber-300' : 'text-amber-300'} />
                    </motion.span>
                    {isPolishing['description'] ? 'AI 优化中...' : 'AI 智能润色'}
                  </button>
                </div>
                <textarea
                  value={formData.description}
                  onChange={(e) => onFieldChange('description', e.target.value)}
                  rows={5}
                  className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm leading-relaxed placeholder:text-slate-400 resize-none"
                  placeholder="请详细描述测试需求的背景、目标、预期结果及业务价值..."
                />
              </div>
            </div>
          </section>

          {/* Section: Tech Specs */}
          <section id="tech" className="bg-white rounded-[2.5rem] border border-slate-100 shadow-2xl shadow-slate-100/50 overflow-hidden">
            <div className="px-10 py-8 border-b border-slate-50 bg-slate-50/30 flex items-center gap-4">
              <div className="p-3 bg-white text-slate-900 rounded-2xl shadow-sm border border-slate-100">
                <Cpu size={20} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-900">技术规格</h2>
                <p className="text-xs text-slate-400 font-medium mt-0.5">硬件配置、固件版本及技术指标</p>
              </div>
            </div>

            <div className="p-10 grid grid-cols-12 gap-8">
              <div className="col-span-12">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">目标部件 (Target Components)</label>
                <div className="flex flex-wrap gap-3">
                  {COMPONENT_CATEGORIES.map(comp => (
                    <button
                      key={comp}
                      onClick={() => onToggleComponent(comp)}
                      className={`px-5 py-2.5 rounded-xl text-sm font-bold border transition-all active:scale-95 ${
                        formData.target_components.includes(comp)
                          ? 'bg-slate-900 text-white border-slate-900 shadow-lg shadow-slate-900/20'
                          : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-700'
                      }`}
                    >
                      {comp}
                    </button>
                  ))}
                </div>
              </div>

              <div className="col-span-6">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">固件版本</label>
                <input
                  type="text"
                  value={formData.firmware_version}
                  onChange={(e) => onFieldChange('firmware_version', e.target.value)}
                  className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold font-mono"
                  placeholder="例如: BIOS v2.1.0, BMC v1.5.2"
                />
              </div>
              <div className="col-span-6">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">测试覆盖范围</label>
                <div className="relative">
                  <select className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold text-slate-700 appearance-none cursor-pointer">
                    <option>单元级 (Unit Level)</option>
                    <option>系统级 (System Level)</option>
                    <option>集成级 (Integration Level)</option>
                  </select>
                  <ChevronRight className="absolute right-6 top-1/2 -translate-y-1/2 rotate-90 text-slate-400 pointer-events-none" size={16} />
                </div>
              </div>

              <div className="col-span-12">
                <div className="flex items-center justify-between mb-3">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider">技术规范 (SPEC)</label>
                  <button
                    onClick={() => onPolishText('technical_spec')}
                    disabled={isPolishing['technical_spec'] || !formData.technical_spec}
                    className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-95 ${
                      isPolishing['technical_spec']
                        ? 'bg-gradient-to-r from-indigo-500 to-violet-500 text-white'
                        : 'bg-gradient-to-r from-indigo-500 to-violet-500 text-white hover:shadow-lg hover:shadow-indigo-500/30'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    <motion.span
                      animate={isPolishing['technical_spec'] ? { rotate: 360 } : {}}
                      transition={isPolishing['technical_spec'] ? { duration: 1, repeat: Infinity, ease: "linear" } : {}}
                    >
                      <Zap size={14} className={isPolishing['technical_spec'] ? 'text-amber-300' : 'text-amber-300'} />
                    </motion.span>
                    {isPolishing['technical_spec'] ? 'AI 解析中...' : 'AI 规范解析'}
                  </button>
                </div>
                <div className="relative">
                  <textarea
                    value={formData.technical_spec}
                    onChange={(e) => onFieldChange('technical_spec', e.target.value)}
                    rows={6}
                    className="w-full px-6 py-5 rounded-2xl border border-slate-200 bg-slate-50/50 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono leading-relaxed placeholder:text-slate-400 resize-none"
                    placeholder="在此输入详细的技术指标、协议要求、接口定义..."
                  />
                  <div className="absolute bottom-4 right-4 text-[10px] font-bold text-slate-300 bg-white px-2 py-1 rounded-lg border border-slate-100">
                    Markdown Supported
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Section: Parameters & Risk */}
          <section id="params" className="bg-white rounded-[2.5rem] border border-slate-100 shadow-2xl shadow-slate-100/50 overflow-hidden">
            <div className="px-10 py-8 border-b border-slate-50 bg-slate-50/30 flex items-center gap-4">
              <div className="p-3 bg-white text-slate-900 rounded-2xl shadow-sm border border-slate-100">
                <Settings size={20} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-900">参数与风险</h2>
                <p className="text-xs text-slate-400 font-medium mt-0.5">关键测试参数配置及风险评估</p>
              </div>
            </div>

            <div className="p-10 space-y-8">
              <div className="bg-slate-50/50 rounded-3xl p-8 border border-slate-200/60">
                <div className="flex items-center justify-between mb-6">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider">关键测试参数 (Key Parameters)</label>
                  <button
                    onClick={() => {
                      const current = formData.key_parameters || [];
                      onFieldChange('key_parameters', [...current, { key: '', value: '' }]);
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 hover:border-indigo-300 hover:text-indigo-600 rounded-xl text-xs font-bold transition-all shadow-sm active:scale-95 text-slate-600"
                  >
                    <Plus size={14} />
                    添加参数
                  </button>
                </div>
                <div className="space-y-3">
                  <div className="grid grid-cols-12 gap-4 px-2 mb-2">
                    <div className="col-span-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest pl-1">Parameter Name</div>
                    <div className="col-span-7 text-[10px] font-bold text-slate-400 uppercase tracking-widest pl-1">Value / Constraint</div>
                    <div className="col-span-1"></div>
                  </div>
                  {(formData.key_parameters || []).map((param, idx) => (
                    <div key={idx} className="grid grid-cols-12 gap-4 items-center group">
                      <div className="col-span-4">
                        <input
                          type="text"
                          value={param.key}
                          onChange={(e) => {
                            const newList = [...formData.key_parameters];
                            newList[idx].key = e.target.value;
                            onFieldChange('key_parameters', newList);
                          }}
                          placeholder="参数名 (e.g. Voltage)"
                          className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold"
                        />
                      </div>
                      <div className="col-span-7">
                        <input
                          type="text"
                          value={param.value}
                          onChange={(e) => {
                            const newList = [...formData.key_parameters];
                            newList[idx].value = e.target.value;
                            onFieldChange('key_parameters', newList);
                          }}
                          placeholder="参数值 (e.g. 12V ±5%)"
                          className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-mono text-slate-600"
                        />
                      </div>
                      <div className="col-span-1 text-right">
                        <button
                          onClick={() => onFieldChange('key_parameters', formData.key_parameters.filter((_, i) => i !== idx))}
                          className="p-2.5 text-slate-300 hover:text-rose-500 hover:bg-rose-50 rounded-xl transition-all opacity-0 group-hover:opacity-100"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                  {(!formData.key_parameters || formData.key_parameters.length === 0) && (
                    <div className="text-center py-8 border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50/30">
                      <p className="text-xs font-bold text-slate-400">暂无关键参数配置</p>
                      <button
                        onClick={() => onFieldChange('key_parameters', [{ key: '', value: '' }])}
                        className="mt-2 text-xs font-bold text-indigo-600 hover:underline"
                      >
                        立即添加
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">风险提示 (Risk Assessment)</label>
                <div className="relative">
                  <div className="absolute top-4 left-4 p-2 bg-rose-100 text-rose-600 rounded-lg">
                    <AlertCircle size={16} />
                  </div>
                  <textarea
                    value={formData.risk_points}
                    onChange={(e) => onFieldChange('risk_points', e.target.value)}
                    rows={4}
                    className="w-full pl-14 pr-6 py-4 rounded-2xl border border-rose-100 bg-rose-50/30 focus:bg-white focus:ring-4 focus:ring-rose-500/10 focus:border-rose-500 outline-none transition-all text-sm text-slate-700 placeholder:text-rose-300/70"
                    placeholder="在此标记潜在的测试风险点、安全隐患或环境限制..."
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-8">
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">预计工时 (Hours)</label>
                  <input type="number" className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold" placeholder="0" />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">截止日期 (Deadline)</label>
                  <input type="date" className="w-full px-6 py-4 rounded-2xl border border-slate-200 bg-slate-50/30 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all text-sm font-bold text-slate-600" />
                </div>
              </div>
            </div>
          </section>

          {/* Section: Attachments */}
          <section id="attach" className="bg-white rounded-[2.5rem] border border-slate-100 shadow-2xl shadow-slate-100/50 overflow-hidden">
            <div className="px-10 py-8 border-b border-slate-50 bg-slate-50/30 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-white text-slate-900 rounded-2xl shadow-sm border border-slate-100">
                  <Paperclip size={20} />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-900">附件管理</h2>
                  <p className="text-xs text-slate-400 font-medium mt-0.5">支持 PDF, Excel, Word 及图片格式</p>
                </div>
              </div>
              <button onClick={onAddAttachment} className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition-all shadow-lg active:scale-95">
                <Plus size={14} />
                上传附件
              </button>
            </div>
            <div className="p-10">
              {formData.attachments.length === 0 ? (
                <div
                  onClick={onAddAttachment}
                  className="border-2 border-dashed border-slate-200 rounded-3xl p-16 text-center hover:border-indigo-400 hover:bg-indigo-50/10 transition-all cursor-pointer group"
                >
                  <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform duration-300">
                    <Paperclip className="text-slate-300 group-hover:text-indigo-500 transition-colors" size={28} />
                  </div>
                  <p className="text-base font-bold text-slate-600 group-hover:text-indigo-600 transition-colors">点击或拖拽文件到此处上传</p>
                  <p className="text-xs text-slate-400 mt-2">单文件最大支持 50MB</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {formData.attachments.map(att => (
                    <div key={att.id} className="flex items-center justify-between p-5 rounded-2xl bg-white border border-slate-100 shadow-sm hover:shadow-md hover:border-indigo-200 transition-all group">
                      <div className="flex items-center gap-4 overflow-hidden">
                        <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl shrink-0">
                          <FileText size={20} />
                        </div>
                        <div className="min-w-0">
                          <span className="text-sm font-bold text-slate-700 block truncate">{att.name}</span>
                          <span className="text-xs text-slate-400 mt-0.5 block">{att.size || '2.4 MB'} • {new Date().toLocaleDateString()}</span>
                        </div>
                      </div>
                      <button onClick={() => onRemoveAttachment(att.id)} className="p-2 text-slate-300 hover:text-rose-500 hover:bg-rose-50 rounded-xl transition-all">
                        <Trash2 size={18} />
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={onAddAttachment}
                    className="flex flex-col items-center justify-center p-5 rounded-2xl border-2 border-dashed border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/10 transition-all text-slate-400 hover:text-indigo-500"
                  >
                    <Plus size={24} className="mb-2" />
                    <span className="text-xs font-bold">继续添加</span>
                  </button>
                </div>
              )}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
};