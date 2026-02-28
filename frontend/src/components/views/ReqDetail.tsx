import React from 'react';
import {
  ChevronRight,
  Plus,
  FileText,
  ShieldAlert,
  AlertCircle,
  Layers,
  Paperclip,
} from 'lucide-react';
import { TestRequirement, TestCase, Priority } from '../../types';

interface ReqDetailProps {
  requirement: TestRequirement;
  testCases: TestCase[];
  onBack: () => void;
  onCreateCase: (refReqId: string) => void;
  onSelectCase: (tc: TestCase) => void;
}

export const ReqDetail: React.FC<ReqDetailProps> = ({
  requirement,
  testCases,
  onBack,
  onCreateCase,
  onSelectCase,
}) => {
  const relatedCases = testCases.filter(c => c.ref_req_id === requirement.req_id);
  const targetComponents = Array.isArray(requirement.target_components) ? requirement.target_components : [];
  const keyParameters = Array.isArray(requirement.key_parameters) ? requirement.key_parameters : [];
  const attachments = Array.isArray(requirement.attachments) ? requirement.attachments : [];
  const ownerId = requirement.tpm_owner_id || '未分配';

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-10">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-5">
          <button onClick={onBack} className="p-2.5 hover:bg-slate-100 rounded-2xl transition-colors text-slate-500">
            <ChevronRight size={24} className="rotate-180" />
          </button>
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-sm font-mono font-bold text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-lg border border-indigo-100">{requirement.req_id}</span>
              <span className={`text-xs font-bold px-2.5 py-1 rounded-lg border ${
                requirement.priority === Priority.P0 ? 'bg-rose-50 text-rose-600 border-rose-100' : 'bg-amber-50 text-amber-600 border-amber-100'
              }`}>{requirement.priority}</span>
              <span className="text-xs font-bold px-2.5 py-1 bg-slate-100 text-slate-600 rounded-lg border border-slate-200">{requirement.status}</span>
            </div>
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight">{requirement.title}</h1>
          </div>
        </div>
        <button
          onClick={() => onCreateCase(requirement.req_id)}
          className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-2xl font-bold hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-200 active:scale-95"
        >
          <Plus size={20} /> 创建测试用例
        </button>
      </div>

      <div className="grid grid-cols-3 gap-8">
        <div className="col-span-2 space-y-8">
          <div className="bg-white rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-100/50 p-8 space-y-8">
            <div>
              <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2 uppercase tracking-wider">
                <FileText size={18} className="text-indigo-600" /> 需求描述
              </h3>
              <p className="text-slate-600 text-base leading-relaxed whitespace-pre-wrap">{requirement.description}</p>
            </div>

            {requirement.technical_spec && (
              <div>
                <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2 uppercase tracking-wider">
                  <ShieldAlert size={18} className="text-indigo-600" /> 技术规范
                </h3>
                <div className="p-6 bg-slate-50/50 rounded-2xl border border-slate-100">
                  <p className="text-slate-600 text-sm leading-relaxed whitespace-pre-wrap font-mono">{requirement.technical_spec}</p>
                </div>
              </div>
            )}

            {requirement.risk_points && (
              <div className="p-6 bg-rose-50 border border-rose-100 rounded-2xl">
                <h3 className="text-sm font-bold text-rose-900 mb-3 flex items-center gap-2 uppercase tracking-wider">
                  <AlertCircle size={18} /> 风险提示
                </h3>
                <p className="text-rose-700 text-sm leading-relaxed whitespace-pre-wrap">{requirement.risk_points}</p>
              </div>
            )}
          </div>

          <div className="bg-white rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-100/50 overflow-hidden">
            <div className="px-8 py-6 border-b border-slate-50 flex justify-between items-center bg-slate-50/30">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 uppercase tracking-wider">
                <Layers size={18} className="text-indigo-600" /> 关联测试用例 ({relatedCases.length})
              </h3>
            </div>
            {relatedCases.length === 0 ? (
              <div className="p-12 text-center">
                <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Plus size={24} className="text-slate-300" />
                </div>
                <p className="text-slate-400 text-sm">暂无关联测试用例</p>
              </div>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50/50 border-b border-slate-100">
                    <th className="px-8 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Case ID</th>
                    <th className="px-8 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">标题</th>
                    <th className="px-8 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">优先级</th>
                    <th className="px-8 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">状态</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {relatedCases.map(c => (
                    <tr key={c.case_id} className="hover:bg-slate-50/80 transition-colors cursor-pointer" onClick={() => onSelectCase(c)}>
                      <td className="px-8 py-5 font-mono text-xs font-bold text-indigo-600">{c.case_id}</td>
                      <td className="px-8 py-5 text-sm font-medium text-slate-900">{c.title}</td>
                      <td className="px-8 py-5 text-xs font-bold text-rose-600">{c.priority}</td>
                      <td className="px-8 py-5">
                        <span className="text-xs font-bold px-2.5 py-1 bg-slate-100 text-slate-600 rounded-lg uppercase">{c.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="space-y-8">
          <div className="bg-white rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-100/50 p-8">
            <h3 className="text-sm font-bold text-slate-900 mb-6 uppercase tracking-wider">需求概览</h3>
            <div className="space-y-6">
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">目标部件</label>
                <div className="flex gap-2 flex-wrap">
                  {targetComponents.map(c => (
                    <span key={c} className="px-3 py-1.5 bg-indigo-50 text-indigo-600 rounded-xl text-xs font-bold">{c}</span>
                  ))}
                </div>
              </div>

              {requirement.firmware_version && (
                <div>
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">强依赖固件</label>
                  <p className="text-sm font-bold text-slate-900 bg-slate-50 px-3 py-2 rounded-xl border border-slate-100 inline-block">{requirement.firmware_version}</p>
                </div>
              )}

              {keyParameters.length > 0 && (
                <div>
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">关键参数</label>
                  <div className="grid grid-cols-1 gap-2">
                    {keyParameters.map((param, idx) => (
                      <div key={idx} className="flex justify-between text-sm border-b border-slate-50 pb-2">
                        <span className="text-slate-500">{param.key}</span>
                        <span className="font-bold text-slate-700 font-mono">{param.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="pt-6 border-t border-slate-100 space-y-4">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">TPM 负责人</label>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center text-[10px] font-bold text-slate-500">
                      {ownerId.charAt(0).toUpperCase()}
                    </div>
                    <p className="text-sm font-medium text-slate-900">{ownerId}</p>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">用例开发</label>
                  <p className="text-sm font-medium text-slate-900">{requirement.manual_dev_id || '-'}</p>
                </div>
              </div>

              {attachments.length > 0 && (
                <div className="pt-6 border-t border-slate-100">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-3">相关附件</label>
                  <div className="space-y-3">
                    {attachments.map(att => (
                      <div key={att.id} className="flex items-center gap-3 text-sm text-indigo-600 hover:text-indigo-700 hover:underline cursor-pointer group">
                        <div className="p-1.5 bg-indigo-50 rounded-lg group-hover:bg-indigo-100 transition-colors">
                          <Paperclip size={14} />
                        </div>
                        <span>{att.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
