/**
 * RerunConfirmModal — Confirmation dialog for re-running a plan item.
 * Refactored to use shadcn Dialog (Radix-based, a11y built-in).
 */
import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import type { PlanItemSummary } from '../types';
import type { UserResponse } from '../../../types';

interface RerunConfirmModalProps {
  item: PlanItemSummary;
  users: UserResponse[];
  onConfirm: (assigneeId: string) => void;
  onClose: () => void;
}

export function RerunConfirmModal({ item, users, onConfirm, onClose }: RerunConfirmModalProps) {
  const isAuto = item.ref_type === 'auto';
  const [selectedAssigneeId, setSelectedAssigneeId] = useState(item.assignee_id || '');

  return (
    <Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="sm:max-w-[440px]">
        <DialogHeader className="pb-2">
          <DialogTitle className="mb-1">确认重新执行</DialogTitle>
          <DialogDescription>
            确定要重新执行用例 <strong>{item.case_title}</strong> 吗？
          </DialogDescription>
        </DialogHeader>

        <div className="text-sm text-[var(--text-tertiary)] leading-relaxed py-1">
          {isAuto ? (
            <span>将重置为"待执行"状态并清除旧执行记录。请在状态变为待执行后，手动点击"执行"按钮下发。</span>
          ) : (
            <span>将重置为"待执行"状态，旧结果将被清除。您可以重新提交执行结果。</span>
          )}
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-medium text-[var(--text-secondary)]">指派给：</label>
          <Select
            value={selectedAssigneeId}
            onChange={(e) => setSelectedAssigneeId(e.target.value)}
          >
            <option value="">不指派</option>
            {users.map(u => (
              <option key={u.user_id} value={u.user_id}>
                {u.username} {u.user_id === item.assignee_id ? '(原执行人)' : ''}
              </option>
            ))}
          </Select>
        </div>

        <DialogFooter>
          <Button variant="ghost" size="sm" onClick={onClose}>取消</Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => onConfirm(selectedAssigneeId)}
          >
            确认执行
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
