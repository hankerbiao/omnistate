/**
 * OverviewView — 运行总览视图
 * Shows overall execution status across all plans.
 */
import { RefreshCw, TrendingUp, CheckCircle, XCircle, Clock, Activity } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { LoadingState, EmptyState } from '@/components/ui/states';
import type { UserResponse } from '../../types';
import type { PlanItemSummary, ItemStatus } from './types';
import { STATUS_META, STATUS, PRIORITY_COLORS, RERUNNABLE_STATUSES } from './types';

interface OverviewViewProps {
  data: Record<string, any> | null;
  loading: boolean;
  onRefresh: () => void;
  onSelectPlan: (planId: string) => void;
  users: UserResponse[];
  onViewResult?: (item: PlanItemSummary) => void;
  onDeleteItem?: (planId: string, itemId: string) => void;
  onCancelExecution?: (itemId: string) => void;
}

export function OverviewView({ data, loading, onRefresh, onSelectPlan, users, onViewResult, onDeleteItem, onCancelExecution }: OverviewViewProps) {
  if (loading && !data) return <LoadingState title="加载总览数据..." className="flex-1" />;
  if (!data) return <EmptyState title="暂无总览数据" description="点击刷新按钮获取最新数据" className="flex-1" action={<Button size="sm" onClick={onRefresh}><RefreshCw size={14} /> 刷新</Button>} />;

  const stats = data.stats || {};
  const runningItems: any[] = data.running_items || [];
  const recentResults: any[] = data.recent_results || [];

  const summaryCards = [
    { label: '总计划数', value: stats.total_plans ?? 0, icon: TrendingUp, color: 'var(--accent-primary)' },
    { label: '活跃计划', value: stats.active_plans ?? 0, icon: Activity, color: 'var(--status-success)' },
    { label: '执行中', value: stats.running_items ?? 0, icon: Clock, color: 'var(--accent-primary)' },
    { label: '已完成', value: stats.done_items ?? 0, icon: CheckCircle, color: 'var(--status-success)' },
    { label: '失败', value: stats.failed_items ?? 0, icon: XCircle, color: 'var(--status-error)' },
  ];

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px' }}>
      {/* Summary cards */}
      <div className="flex gap-3 flex-wrap mb-4">
        {summaryCards.map(card => {
          const Icon = card.icon;
          return (
            <div key={card.label} className="px-4 py-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] min-w-[120px]">
              <div className="flex items-center gap-2 mb-1">
                <Icon size={14} style={{ color: card.color }} />
                <span className="text-[11px] text-[var(--text-tertiary)]">{card.label}</span>
              </div>
              <div className="text-xl font-bold" style={{ color: card.color }}>{card.value}</div>
            </div>
          );
        })}
        <Button variant="ghost" size="sm" onClick={onRefresh} className="self-center">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> 刷新
        </Button>
      </div>

      {/* Running items */}
      {runningItems.length > 0 && (
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2">正在执行 ({runningItems.length})</h3>
          <div className="flex flex-col gap-1">
            {runningItems.map((item: any) => {
              const meta = STATUS_META[item.status as ItemStatus] || STATUS_META.running;
              return (
                <div key={item.item_id} className="flex items-center gap-2 px-3 py-2 rounded-md border border-[var(--border-subtle)] bg-[var(--surface-primary)] text-xs">
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: meta.color }} />
                  <span className="font-mono text-[10px] text-[var(--text-tertiary)] flex-shrink-0">{item.case_id}</span>
                  <span className="flex-1 truncate font-medium">{item.case_title}</span>
                  {item.plan_title && <span className="text-[10px] text-[var(--text-secondary)] flex-shrink-0">{item.plan_title}</span>}
                  <Badge variant="info">{meta.label}</Badge>
                  {item.assignee_id && <span className="text-[10px] text-[var(--text-tertiary)]">{users.find(u => u.user_id === item.assignee_id)?.username || item.assignee_id}</span>}
                  {onCancelExecution && (
                    <button onClick={() => onCancelExecution(item.item_id)} className="text-[10px] px-2 py-0.5 rounded cursor-pointer" style={{ border: '1px solid rgba(220,38,38,0.25)', color: 'var(--status-error)', background: 'var(--status-error-bg)' }}>终止</button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Recent results */}
      {recentResults.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2">最近完成 ({recentResults.length})</h3>
          <div className="flex flex-col gap-1">
            {recentResults.map((item: any) => {
              const meta = STATUS_META[item.status as ItemStatus] || STATUS_META.done;
              return (
                <div key={item.item_id} className="flex items-center gap-2 px-3 py-2 rounded-md border border-[var(--border-subtle)] bg-[var(--surface-primary)] text-xs">
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: meta.color }} />
                  <span className="font-mono text-[10px] text-[var(--text-tertiary)] flex-shrink-0">{item.case_id}</span>
                  <span className="flex-1 truncate font-medium">{item.case_title}</span>
                  {item.plan_title && <span className="text-[10px] text-[var(--text-secondary)] flex-shrink-0">{item.plan_title}</span>}
                  <Badge variant={item.status === 'done' ? 'success' : 'destructive'}>{meta.label}</Badge>
                  {item.result && <Badge variant={item.result.passed ? 'success' : 'destructive'}>{item.result.passed ? '通过' : '失败'}</Badge>}
                  {(item.execution_task_id || item.result) && onViewResult && (
                    <button onClick={() => onViewResult(item as PlanItemSummary)} className="text-[10px] px-2 py-0.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] text-[var(--accent-primary)] cursor-pointer">结果</button>
                  )}
                  {RERUNNABLE_STATUSES.includes(item.status) && onDeleteItem && (
                    <button onClick={() => onDeleteItem(item.plan_id, item.item_id)} className="text-[10px] px-2 py-0.5 rounded cursor-pointer" style={{ border: '1px solid rgba(220,38,38,0.25)', color: 'var(--status-error)', background: 'var(--status-error-bg)' }}>终止</button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {runningItems.length === 0 && recentResults.length === 0 && (
        <EmptyState title="暂无执行记录" description="创建执行计划并下发任务后，这里会显示执行总览" />
      )}
    </div>
  );
}
