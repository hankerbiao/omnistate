/**
 * AddCasesModal — Two-step modal for adding test cases to a plan.
 * Refactored to use shadcn Dialog.
 */
import { useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select } from '@/components/ui/select';
import { Check, ChevronRight, ChevronLeft } from 'lucide-react';
import type { PlanItemSummary } from '../types';
import type { UserResponse } from '../../../types';

interface AddCasesModalProps {
  editingItems: PlanItemSummary[];
  selectedAddCaseIds: string[];
  onToggle: (cid: string) => void;
  onClose: () => void;
  onConfirm: (assigneeId: string) => void;
  cases: { id: string; title: string; type: string; priority: string }[];
  users: UserResponse[];
}

export function AddCasesModal({ editingItems, selectedAddCaseIds, onToggle, onClose, onConfirm, cases, users }: AddCasesModalProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [assigneeId, setAssigneeId] = useState('');
  const editingCaseIds = useMemo(() => new Set(editingItems.map(e => e.case_id)), [editingItems]);

  const handleClose = () => {
    setStep(1);
    setAssigneeId('');
    onClose();
  };

  const handleConfirm = () => {
    if (assigneeId && selectedAddCaseIds.length > 0) {
      onConfirm(assigneeId);
      setStep(1);
      setAssigneeId('');
    }
  };

  return (
    <Dialog open onOpenChange={(o) => { if (!o) handleClose(); }}>
      <DialogContent className="sm:max-w-[520px] max-h-[70vh] flex flex-col">
        <DialogHeader className="pb-2">
          <DialogTitle className="mb-1 flex items-center gap-3">
            {step === 1 ? '添加测试用例' : '指派执行人'}
            <div className="flex items-center gap-1">
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${step === 1 ? 'bg-[var(--accent-primary)] text-white' : 'bg-[var(--status-success-bg)] text-[var(--status-success)]'}`}>1. 选用例</span>
              <ChevronRight size={12} className="text-[var(--text-tertiary)]" />
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${step === 2 ? 'bg-[var(--accent-primary)] text-white' : 'bg-[var(--surface-tertiary)] text-[var(--text-tertiary)]'}`}>2. 指派</span>
            </div>
          </DialogTitle>
        </DialogHeader>

        {step === 1 ? (
          <>
            <div className="flex-1 overflow-y-auto max-h-[400px] flex flex-col gap-1">
              {cases.length === 0 ? (
                <div className="py-8 text-center text-sm text-[var(--text-tertiary)]">暂无可选用例</div>
              ) : cases.map(c => {
                const isSelected = selectedAddCaseIds.includes(c.id);
                const isInPlan = editingCaseIds.has(c.id);
                return (
                  <div key={c.id}
                    className={`flex items-center gap-2 px-3 py-2 rounded-md border text-xs cursor-pointer transition-colors ${isSelected ? 'border-[var(--accent-primary)] bg-[var(--status-info-bg)]' : 'border-[var(--border-subtle)] hover:bg-[var(--surface-hover)]'}`}
                    onClick={() => !isInPlan && onToggle(c.id)}
                    style={{ opacity: isInPlan ? 0.5 : 1, cursor: isInPlan ? 'not-allowed' : 'pointer' }}
                  >
                    <div className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${isSelected ? 'bg-[var(--accent-primary)] border-[var(--accent-primary)]' : 'border-[var(--border-default)]'}`}>
                      {isSelected && <Check size={12} className="text-white" strokeWidth={3} />}
                    </div>
                    <span className="font-mono text-[10px] text-[var(--text-tertiary)]">{c.id}</span>
                    <span className="flex-1 truncate font-medium">{c.title}</span>
                    <Badge variant={c.type === 'auto' ? 'info' : 'secondary'}>{c.type === 'auto' ? '自动化' : '手工'}</Badge>
                    <Badge variant="outline">{c.priority}</Badge>
                    {isInPlan && <span className="text-[10px] text-[var(--text-tertiary)]">已在计划中</span>}
                  </div>
                );
              })}
            </div>
            <DialogFooter>
              <Button variant="ghost" size="sm" onClick={handleClose}>取消</Button>
              <Button size="sm" onClick={() => selectedAddCaseIds.length > 0 && setStep(2)} disabled={selectedAddCaseIds.length === 0}>
                下一步：指派执行人 <ChevronRight size={14} />
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <div className="flex-1 space-y-3">
              <div className="text-sm text-[var(--text-secondary)]">
                已选择 <strong>{selectedAddCaseIds.length}</strong> 个用例，请统一指派执行人：
              </div>
              <Select value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)}>
                <option value="">不指派</option>
                {users.map(u => (
                  <option key={u.user_id} value={u.user_id}>{u.username}</option>
                ))}
              </Select>
            </div>
            <DialogFooter>
              <Button variant="ghost" size="sm" onClick={() => setStep(1)}>
                <ChevronLeft size={14} /> 上一步
              </Button>
              <Button size="sm" onClick={handleConfirm} disabled={!assigneeId}>
                确认添加
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
