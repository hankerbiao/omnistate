import { Inbox, AlertCircle, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  title?: string
  description?: string
  icon?: React.ReactNode
  action?: React.ReactNode
  className?: string
}

export function EmptyState({
  title = '暂无数据',
  description,
  icon,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-16 px-4 text-center',
        className
      )}
    >
      <div className="mb-4 text-[var(--text-tertiary)]">
        {icon ?? <Inbox size={40} strokeWidth={1.5} />}
      </div>
      <h3 className="text-sm font-medium text-[var(--text-primary)] mb-1">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-[var(--text-tertiary)] max-w-sm">
          {description}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

interface LoadingStateProps {
  title?: string
  className?: string
  rows?: number
}

export function LoadingState({
  title = '加载中...',
  className,
  rows = 3,
}: LoadingStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-16 px-4', className)}>
      <Loader2 size={24} className="animate-spin text-[var(--accent-primary)] mb-3" />
      <p className="text-sm text-[var(--text-tertiary)]">{title}</p>
      {rows > 0 && (
        <div className="w-full max-w-md mt-6 space-y-3">
          {Array.from({ length: rows }).map((_, i) => (
            <div key={i} className="h-12 rounded-md bg-[var(--surface-tertiary)] animate-pulse" />
          ))}
        </div>
      )}
    </div>
  )
}

interface ErrorStateProps {
  title?: string
  description?: string
  onRetry?: () => void
  className?: string
}

export function ErrorState({
  title = '加载失败',
  description = '请检查网络连接后重试',
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-16 px-4 text-center',
        className
      )}
    >
      <div className="mb-4 text-[var(--status-error)]">
        <AlertCircle size={40} strokeWidth={1.5} />
      </div>
      <h3 className="text-sm font-medium text-[var(--text-primary)] mb-1">
        {title}
      </h3>
      <p className="text-sm text-[var(--text-tertiary)] max-w-sm mb-4">
        {description}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center justify-center rounded-md bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-primary-hover)] transition-colors"
        >
          重试
        </button>
      )}
    </div>
  )
}
