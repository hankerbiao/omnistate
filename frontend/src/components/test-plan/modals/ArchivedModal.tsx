/**
 * ArchivedModal — Modal showing archived plan items.
 * Refactored to use shadcn Dialog.
 */
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { RERUNNABLE_STATUSES } from '../types';

interface ArchivedModalProps {
  open: boolean;
  loading: boolean;
  items: any[];
  onClose: () => void;
  onUnarchive: (itemId: string) => void;
  onRerunItem?: (item: any) => void;
}

export function ArchivedModal({ open, loading, items, onClose, onUnarchive, onRerunItem }: ArchivedModalProps) {
  const doneCount = items.filter((i: any) => i.status === 'done').length;
  const failCount = items.filter((i: any) => i.status === 'fail').length;

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-[620px] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>已归档条目</DialogTitle>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[var(--text-tertiary)]">{items.length} 条记录</span>
            {doneCount > 0 && <Badge variant="success">已完成 {doneCount}</Badge>}
            {failCount > 0 && <Badge variant="destructive">失败 {failCount}</Badge>}
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto flex flex-col gap-1">
          {loading ? (
            <div className="py-8 text-center text-sm text-[var(--text-tertiary)]">加载中...</div>
          ) : items.length === 0 ? (
            <div className="py-8 text-center text-[var(--text-tertiary)]">
              <div className="text-sm">暂无已归档条目</div>
              <div className="text-xs mt-1">已完成的任务会自动归档到这里</div>
            </div>
          ) : (
            items.map((item: any) => (
              <div key={item.item_id}
                className="flex items-center gap-2 px-3 py-2 rounded-md border border-[var(--border-subtle)] bg-[var(--surface-primary)] text-xs"
              >
                <div className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                  style={{ background: item.status === 'done' ? 'var(--status-success)' : item.status === 'fail' ? 'var(--status-error)' : 'var(--text-tertiary)' }}
                />
                <span className="font-mono text-[10px] text-[var(--text-tertiary)] flex-shrink-0">{item.case_id}</span>
                <span className="flex-1 truncate font-medium">{item.case_title}</span>
                <span className="text-[10px] text-[var(--text-secondary)] flex-shrink-0">{item.plan_title}</span>
                <Badge variant={item.status === 'done' ? 'success' : item.status === 'fail' ? 'destructive' : 'secondary'}>
                  {item.status === 'done' ? '已完成' : item.status === 'fail' ? '失败' : item.status}
                </Badge>
                <button onClick={() => onUnarchive(item.item_id)}
                  className="px-2.5 py-1 text-[10px] rounded border-none cursor-pointer bg-[var(--surface-secondary)] text-[var(--text-secondary)] font-medium flex-shrink-0 hover:bg-[var(--surface-hover)]"
                >
                  取回
                </button>
                {RERUNNABLE_STATUSES.includes(item.status) && onRerunItem && (
                  <button onClick={() => onRerunItem(item)}
                    className="px-2.5 py-1 text-[10px] rounded cursor-pointer font-medium flex-shrink-0"
                    style={{ border: '1px solid rgba(220,38,38,0.25)', background: 'var(--status-error-bg)', color: 'var(--status-error)' }}
                  >
                    重新执行
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
