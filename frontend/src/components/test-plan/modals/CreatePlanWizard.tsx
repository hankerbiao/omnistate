/**
 * CreatePlanWizard — Multi-step plan creation wizard.
 * Refactored to use shadcn Dialog.
 */
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Check, ChevronLeft, ChevronRight } from 'lucide-react';
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
      <DialogContent className="sm:max-w-[680px] max-h-[88vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>新建执行计划</DialogTitle>
          <div className="flex gap-1 mt-2">
            {STEP_LABELS.map((s, i) => (
              <span key={i} className={`text-[11px] px-2.5 py-0.5 rounded-full font-medium flex items-center gap-1 ${wizardStep === i + 1 ? 'bg-[var(--accent-primary)] text-white' : wizardStep > i + 1 ? 'bg-[var(--status-success-bg)] text-[var(--status-success)]' : 'bg-[var(--surface-tertiary)] text-[var(--text-tertiary)]'}`}>
                {wizardStep > i + 1 ? <Check size={10} /> : <span>{i + 1}</span>}
                <span>{s}</span>
              </span>
            ))}
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {wizardStep === 1 && (
            <div className="flex flex-col gap-3.5">
              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">计划名称 *</label>
                <Input value={newPlan.title} onChange={e => onNewPlanChange(p => ({ ...p, title: e.target.value }))} placeholder="例如: Sprint 3 安全回归" autoFocus />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">描述</label>
                <Textarea value={newPlan.description} onChange={e => onNewPlanChange(p => ({ ...p, description: e.target.value }))} placeholder="计划的目的、范围、备注..." rows={3} />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1.5">计划周期</label>
                <DateRangePicker startDate={newPlan.startDate} endDate={newPlan.endDate} onChange={(start, end) => onNewPlanChange(p => ({ ...p, startDate: start, endDate: end }))} />
              </div>
            </div>
          )}

          {wizardStep === 2 && (
            <div>
              <div className="text-xs text-[var(--text-secondary)] mb-2.5">已选 <strong>{newPlan.selectedCases.length}</strong> 个用例</div>
              <Input value={caseSearch} onChange={e => onCaseSearchChange(e.target.value)} placeholder="搜索用例名称、ID 或预置用例集..." className="mb-2.5" />
              {casesLoading ? (
                <div className="py-5 text-center text-[var(--text-tertiary)] text-sm">加载用例中...</div>
              ) : (
                <div className="flex flex-col gap-1">
                  {matchedCollections.map(col => (
                    <label key={col.collection_id} onClick={() => onToggleCollection(col)}
                      className="flex items-center gap-2.5 px-3 py-2 rounded-md cursor-pointer border border-[var(--border-subtle)] bg-[var(--surface-primary)] mb-0.5 hover:bg-[var(--surface-hover)]">
                      <div className="flex-1">
                        <div className="text-xs font-medium">{col.name}</div>
                        {col.description && <div className="text-[10px] text-[var(--text-tertiary)] mt-0.5">{col.description}</div>}
                      </div>
                      <span className="text-[10px] text-[var(--text-tertiary)]">{col.case_count} 个用例</span>
                    </label>
                  ))}
                  {matchedCases.map(tc => {
                    const sel = newPlan.selectedCases.includes(tc.id);
                    return (
                      <label key={tc.id} onClick={() => onToggleCase(tc.id)}
                        className="flex items-center gap-2.5 px-3 py-2 rounded-md cursor-pointer"
                        style={{ border: sel ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)', background: sel ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)' : 'var(--surface-primary)' }}>
                        <input type="checkbox" checked={sel} onChange={() => {}} style={{ accentColor: 'var(--accent-primary)' }} />
                        <span className="text-[10px] font-mono text-[var(--text-tertiary)] min-w-[50px]">{tc.id}</span>
                        <span className="flex-1 text-xs" style={{ fontWeight: sel ? 600 : 400 }}>{tc.title}</span>
                        <Badge variant={tc.type === 'auto' ? 'info' : 'secondary'}>{tc.type === 'auto' ? 'AUTO' : 'MANUAL'}</Badge>
                        {tc.priority && <span className="text-[10px] font-semibold" style={{ color: PRIORITY_COLORS[tc.priority] }}>{tc.priority}</span>}
                      </label>
                    );
                  })}
                  {matchedCollections.length === 0 && matchedCases.length === 0 && (
                    <div className="py-5 text-center text-[var(--text-tertiary)] text-xs">无匹配的用例或集合</div>
                  )}
                </div>
              )}
            </div>
          )}

          {wizardStep === 3 && (
            <div>
              <div className="text-xs text-[var(--text-secondary)] mb-2.5">为已选用例分配执行人</div>
              <div className="flex flex-col gap-1.5">
                {newPlan.selectedCases.map(cid => {
                  const tc = caseMap.get(cid);
                  if (!tc) return null;
                  return (
                    <div key={cid} className="flex items-center gap-2 px-3 py-2 bg-[var(--surface-secondary)] rounded-md border border-[var(--border-subtle)]">
                      <span className="text-[10px] font-mono text-[var(--text-tertiary)] min-w-[50px]">{cid}</span>
                      <span className="flex-1 text-xs font-medium">{tc.title}</span>
                      <Badge variant={tc.type === 'auto' ? 'info' : 'secondary'}>{tc.type === 'auto' ? 'AUTO' : 'MANUAL'}</Badge>
                      <Select className="w-[120px] text-[11px]" value={newPlan.assignments[cid]?.assignee || currentUserId} onChange={e => onSetAssignment(cid, e.target.value)}>
                        {users.map(u => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
                      </Select>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {wizardStep === 4 && (
            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">自动触发时间</label>
                <Input type="datetime-local" value={newPlan.triggerAt} onChange={e => onNewPlanChange(p => ({ ...p, triggerAt: e.target.value }))} className="w-[260px]" />
                <div className="text-[10px] text-[var(--text-tertiary)] mt-1">到达设定时间后自动开始执行，留空为手动触发</div>
              </div>
              <div className="bg-[var(--surface-secondary)] rounded-lg p-3.5 border border-[var(--border-subtle)]">
                <div className="text-sm font-semibold mb-2.5">计划概览</div>
                <div className="grid grid-cols-[auto_1fr] gap-x-3.5 gap-y-1 text-xs">
                  <span className="text-[var(--text-tertiary)]">名称</span><span className="font-medium">{newPlan.title || '-'}</span>
                  <span className="text-[var(--text-tertiary)]">周期</span><span>{newPlan.startDate || '-'} 至 {newPlan.endDate || '-'}</span>
                  <span className="text-[var(--text-tertiary)]">触发方式</span><span>{newPlan.triggerAt || '手动触发'}</span>
                  <span className="text-[var(--text-tertiary)]">用例数</span><span className="font-semibold">{newPlan.selectedCases.length} 个（{newPlan.selectedCases.filter(c => caseMap.get(c)?.type === 'auto').length} 自动 / {newPlan.selectedCases.filter(c => caseMap.get(c)?.type === 'manual').length} 手动）</span>
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="secondary" size="sm" onClick={() => wizardStep > 1 ? onStepChange(wizardStep - 1) : onClose()}>
            {wizardStep > 1 ? <><ChevronLeft size={14} /> 上一步</> : '取消'}
          </Button>
          {wizardStep < 4 ? (
            <Button size="sm" onClick={() => onStepChange(wizardStep + 1)} disabled={wizardStep === 1 && !newPlan.title.trim()}>
              下一步 <ChevronRight size={14} />
            </Button>
          ) : (
            <Button size="sm" onClick={onCreatePlan} disabled={newPlan.selectedCases.length === 0 || submittingPlan}>
              {submittingPlan ? '创建中...' : '创建计划'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
