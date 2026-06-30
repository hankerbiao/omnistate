/**
 * CreatePlanWizard — Multi-step plan creation wizard.
 * Redesigned: standard modal sheet pattern with fixed header/body/footer.
 */
import { Dialog, DialogClose, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Check, ChevronLeft, ChevronRight, Calendar, FileText, Info } from 'lucide-react';
import { DateRangePicker } from '../DateRangePicker';
import type { NewPlanData, CaseMapEntry, CollectionEntry } from '../types';
import { PRIORITY_COLORS } from '../types';
import type { UserResponse } from '../../../types';

interface CreatePlanWizardProps {
  wizardStep: number;
  onStepChange: (s: number) => void;
  newPlan: NewPlanData;
  onNewPlanChange: (updater: (p: NewPlanData) => NewPlanData) => void;
  caseSearch: string;
  onCaseSearchChange: (s: string) => void;
  submittingPlan: boolean;
  onCreatePlan: () => void;
  onClose: () => void;
  onToggleCase: (cid: string) => void;
  onToggleCollection: (col: { collection_id: string; name: string }) => void;
  onSetAssignment: (caseId: string, value: string) => void;
  users: UserResponse[];
  collections: CollectionEntry[];
  caseMap: Map<string, CaseMapEntry>;
  casesLoading: boolean;
  currentUserId: string;
}

const STEP_LABELS = ['基本信息', '选择用例', '分配执行人', '排期确认'];

export function CreatePlanWizard({
  wizardStep, onStepChange, newPlan, onNewPlanChange, caseSearch, onCaseSearchChange,
  submittingPlan, onCreatePlan, onClose, onToggleCase, onToggleCollection, onSetAssignment,
  users, collections, caseMap, casesLoading, currentUserId,
}: CreatePlanWizardProps) {
  const q = caseSearch.trim().toLowerCase();
  const matchedCollections = q
    ? collections.filter(col => col.name?.toLowerCase().includes(q) || (col.description || '').toLowerCase().includes(q))
    : collections;
  const allCases = Array.from(caseMap.values());
  const matchedCases = q ? allCases.filter(tc => tc.id.includes(q) || tc.title.toLowerCase().includes(q)) : allCases;

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-[880px] max-h-[90vh] p-0 gap-0 overflow-hidden grid grid-rows-[auto_minmax(0,1fr)_auto] rounded-2xl shadow-2xl">
        {/* ── Fixed header ── */}
        <div className="px-8 pt-7 pb-4 border-b border-[var(--border-subtle)] flex-shrink-0 bg-[var(--surface-primary)]">
          {/* Title row */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <DialogTitle className="text-[20px] font-bold tracking-tight text-[var(--text-primary)] leading-tight">
                新建执行计划
              </DialogTitle>
              <p className="text-xs text-[var(--text-tertiary)] mt-1">按步骤填写，完成后可随时编辑</p>
            </div>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="text-[11px] text-[var(--text-tertiary)] bg-[var(--surface-secondary)] border border-[var(--border-subtle)] px-2.5 py-1 rounded-full font-medium">
                {wizardStep} / {STEP_LABELS.length}
              </span>
              <DialogClose className="w-7 h-7 rounded-full flex items-center justify-center text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-hover)] transition-colors" aria-label="关闭">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M1 1L13 13M13 1L1 13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                </svg>
              </DialogClose>
            </div>
          </div>

          {/* Step indicators */}
          <div className="flex items-center gap-1.5">
            {STEP_LABELS.map((s, i) => {
              const step = i + 1;
              const isActive = wizardStep === step;
              const isDone = wizardStep > step;
              return (
                <div key={i} className="flex items-center gap-1.5 flex-1">
                  <div className={`flex items-center gap-2 flex-1 px-3 py-2 rounded-lg transition-all ${
                    isActive 
                      ? 'bg-[var(--status-info-bg)] border border-[var(--status-info)]' 
                      : isDone 
                        ? 'bg-[var(--status-success-bg)] border border-[var(--status-success)]'
                        : 'bg-[var(--surface-secondary)] border border-[var(--border-subtle)]'
                  }`}>
                    <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${
                      isActive 
                        ? 'bg-[var(--accent-primary)] text-white' 
                        : isDone 
                          ? 'bg-[var(--status-success)] text-white'
                          : 'bg-[var(--surface-tertiary)] text-[var(--text-tertiary)]'
                    }`}>
                      {isDone ? <Check size={10} strokeWidth={3} /> : step}
                    </span>
                    <span className={`text-[11px] font-medium whitespace-nowrap ${
                      isActive 
                        ? 'text-[var(--status-info)]' 
                        : isDone 
                          ? 'text-[var(--status-success)]'
                          : 'text-[var(--text-tertiary)]'
                    }`}>
                      {s}
                    </span>
                  </div>
                  {i < STEP_LABELS.length - 1 && (
                    <div className={`w-3 h-px flex-shrink-0 ${wizardStep > step ? 'bg-[var(--status-success)]' : 'bg-[var(--border-subtle)]'}`} />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Scrollable body ── */}
        <div className="px-8 py-5 overflow-y-auto flex-1 min-h-0 bg-[var(--surface-secondary)]">
          {wizardStep === 1 && (
            <div className="flex flex-col gap-3.5">
              {/* ── 顶部信息提示 ── */}
              <div className="flex items-start gap-2.5 p-3 rounded-lg bg-[var(--status-info-bg)] border border-[var(--status-info)]">
                <Info size={14} className="text-[var(--status-info)] mt-0.5 flex-shrink-0" />
                <p className="text-xs text-[var(--status-info)] leading-relaxed">
                  填写计划的基本信息，这些信息将帮助团队成员快速了解计划的目标和范围。
                </p>
              </div>

              {/* ── 核心信息区 ── */}
              <div className="bg-[var(--surface-primary)] rounded-xl p-5 border border-[var(--border-subtle)] space-y-4">
                {/* 计划名称 */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
                      <FileText size={14} className="text-[var(--status-info)]" />
                      计划名称 <span className="text-[var(--status-error)]">*</span>
                    </label>
                    <span className={`text-xs font-medium tabular-nums ${newPlan.title.length > 50 ? 'text-[var(--status-error)]' : 'text-[var(--text-tertiary)]'}`}>
                      {newPlan.title.length}/50
                    </span>
                  </div>
                  <Input
                    value={newPlan.title}
                    onChange={e => {
                      const val = e.target.value;
                      if (val.length <= 50) onNewPlanChange(p => ({ ...p, title: val }));
                    }}
                    placeholder="例如：Sprint 3 安全回归测试"
                    autoFocus
                    className="h-10 text-sm bg-[var(--surface-secondary)]"
                  />
                  <p className="text-xs text-[var(--text-tertiary)]">建议包含迭代版本和测试范围，便于识别</p>
                </div>

                {/* 描述 */}
                <div className="space-y-1.5">
                  <label className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
                    <FileText size={14} className="text-[var(--text-tertiary)]" />
                    描述
                  </label>
                  <Textarea
                    value={newPlan.description}
                    onChange={e => onNewPlanChange(p => ({ ...p, description: e.target.value }))}
                    placeholder="说明计划的目的、覆盖范围、验收标准等..."
                    rows={3}
                    className="min-h-[72px] text-[13px] resize-none bg-[var(--surface-secondary)]"
                  />
                </div>
              </div>

              {/* ── 计划周期 ── */}
              <div className="bg-[var(--surface-primary)] rounded-xl p-5 border border-[var(--border-subtle)] space-y-2.5">
                <label className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
                  <Calendar size={14} className="text-[var(--status-info)]" />
                  计划周期
                </label>
                <DateRangePicker
                  startDate={newPlan.startDate}
                  endDate={newPlan.endDate}
                  onChange={(start, end) => onNewPlanChange(p => ({ ...p, startDate: start, endDate: end }))}
                />
              </div>

            </div>
          )}

          {wizardStep === 2 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-[var(--text-secondary)]">已选 <strong className="text-[var(--text-primary)]">{newPlan.selectedCases.length}</strong> 个用例</span>
              </div>
              <Input value={caseSearch} onChange={e => onCaseSearchChange(e.target.value)} placeholder="搜索用例名称、ID 或预置用例集..." className="mb-3" />
              {casesLoading ? (
                <div className="py-10 text-center text-sm text-[var(--text-tertiary)]">加载用例中...</div>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {matchedCollections.map(col => (
                    <label key={col.collection_id} onClick={() => onToggleCollection(col)}
                      className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg cursor-pointer border border-[var(--border-subtle)] bg-[var(--surface-primary)] hover:bg-[var(--surface-hover)] hover:border-[var(--border-default)] transition-colors">
                      <div className="flex-1">
                        <div className="text-sm font-medium">{col.name}</div>
                        {col.description && <div className="text-[11px] text-[var(--text-tertiary)] mt-0.5">{col.description}</div>}
                      </div>
                      <Badge variant="secondary">{col.case_count} 个用例</Badge>
                    </label>
                  ))}
                  {matchedCases.map(tc => {
                    const sel = newPlan.selectedCases.includes(tc.id);
                    return (
                      <label key={tc.id} onClick={() => onToggleCase(tc.id)}
                        className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg cursor-pointer transition-colors"
                        style={{
                          border: sel ? '1.5px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                          background: sel ? 'color-mix(in srgb, var(--accent-primary) 5%, transparent)' : 'var(--surface-primary)',
                        }}>
                        <div className={`w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors ${sel ? 'bg-[var(--accent-primary)] border-[var(--accent-primary)]' : 'border-[var(--border-default)]'}`}>
                          {sel && <Check size={11} className="text-white" strokeWidth={3} />}
                        </div>
                        <span className="text-[11px] font-mono text-[var(--text-tertiary)] min-w-[50px]">{tc.id}</span>
                        <span className="flex-1 text-sm" style={{ fontWeight: sel ? 600 : 400 }}>{tc.title}</span>
                        <Badge variant={tc.type === 'auto' ? 'info' : 'secondary'}>{tc.type === 'auto' ? 'AUTO' : 'MANUAL'}</Badge>
                        {tc.priority && <span className="text-[11px] font-semibold" style={{ color: PRIORITY_COLORS[tc.priority] }}>{tc.priority}</span>}
                      </label>
                    );
                  })}
                  {matchedCollections.length === 0 && matchedCases.length === 0 && (
                    <div className="py-10 text-center text-sm text-[var(--text-tertiary)]">无匹配的用例或集合</div>
                  )}
                </div>
              )}
            </div>
          )}

          {wizardStep === 3 && (
            <div>
              <p className="text-sm text-[var(--text-secondary)] mb-3">为已选用例分配执行人</p>
              <div className="flex flex-col gap-2">
                {newPlan.selectedCases.map(cid => {
                  const tc = caseMap.get(cid);
                  if (!tc) return null;
                  return (
                    <div key={cid} className="flex items-center gap-3 px-3.5 py-2.5 bg-[var(--surface-secondary)] rounded-lg border border-[var(--border-subtle)]">
                      <span className="text-[11px] font-mono text-[var(--text-tertiary)] min-w-[50px]">{cid}</span>
                      <span className="flex-1 text-sm font-medium">{tc.title}</span>
                      <Badge variant={tc.type === 'auto' ? 'info' : 'secondary'}>{tc.type === 'auto' ? 'AUTO' : 'MANUAL'}</Badge>
                      <Select className="w-[140px] text-sm" value={newPlan.assignments[cid]?.assignee || currentUserId} onChange={e => onSetAssignment(cid, e.target.value)}>
                        {users.map(u => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
                      </Select>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {wizardStep === 4 && (
            <div className="flex flex-col gap-5">
              <div className="bg-[var(--surface-secondary)] rounded-xl p-4 border border-[var(--border-subtle)]">
                <div className="text-sm font-semibold text-[var(--text-primary)] mb-3">计划概览</div>
                <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
                  <span className="text-[var(--text-tertiary)]">名称</span>
                  <span className="font-medium text-[var(--text-primary)]">{newPlan.title || '-'}</span>
                  <span className="text-[var(--text-tertiary)]">周期</span>
                  <span className="text-[var(--text-primary)]">{newPlan.startDate || '-'} 至 {newPlan.endDate || '-'}</span>
                  <span className="text-[var(--text-tertiary)]">用例数</span>
                  <span className="font-semibold text-[var(--text-primary)]">
                    {newPlan.selectedCases.length} 个（{newPlan.selectedCases.filter(c => caseMap.get(c)?.type === 'auto').length} 自动 / {newPlan.selectedCases.filter(c => caseMap.get(c)?.type === 'manual').length} 手动）
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Fixed footer ── */}
        <div className="px-8 py-3.5 border-t border-[var(--border-subtle)] flex items-center justify-between flex-shrink-0 bg-[var(--surface-primary)]">
          <Button variant="ghost" size="sm" onClick={() => wizardStep > 1 ? onStepChange(wizardStep - 1) : onClose()} className="text-[var(--text-secondary)]">
            {wizardStep > 1 ? <><ChevronLeft size={16} /> 上一步</> : '取消'}
          </Button>
          <div className="flex items-center gap-3">
            {wizardStep < 4 && (
              <span className="text-xs text-[var(--text-tertiary)]">
                还有 {STEP_LABELS.length - wizardStep} 个步骤
              </span>
            )}
            {wizardStep < 4 ? (
              <Button size="sm" onClick={() => onStepChange(wizardStep + 1)} disabled={wizardStep === 1 && !newPlan.title.trim()} className="px-5" style={{ background: 'var(--accent-primary)', color: 'white', opacity: wizardStep === 1 && !newPlan.title.trim() ? 0.5 : 1 }}>
                下一步 <ChevronRight size={16} />
              </Button>
            ) : (
              <Button size="sm" onClick={onCreatePlan} disabled={newPlan.selectedCases.length === 0 || submittingPlan} className="px-5" style={{ background: 'var(--accent-primary)', color: 'white', opacity: submittingPlan ? 0.5 : 1 }}>
                {submittingPlan ? '创建中...' : '创建计划'}
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
