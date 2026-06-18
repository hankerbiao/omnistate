/** ModernCard — 带阴影、悬停效果、可选边色装饰的卡片式列表项 */

interface ModernCardProps {
  children: React.ReactNode
  active?: boolean
  accentColor?: string
  onClick?: () => void
  style?: React.CSSProperties
  className?: string
}

export default function ModernCard({ children, active, accentColor, onClick, style, className = '' }: ModernCardProps) {
  return (
    <div
      className={className}
      onClick={onClick}
      style={{
        padding: '12px 14px',
        margin: '0 8px 6px',
        borderRadius: 10,
        cursor: onClick ? 'pointer' : 'default',
        border: active ? `1.5px solid ${accentColor || 'var(--accent-primary)'}` : '1.5px solid transparent',
        background: active ? 'color-mix(in srgb, var(--accent-primary) 6%, var(--surface-primary))' : 'var(--surface-primary)',
        boxShadow: active ? '0 1px 4px rgba(0,0,0,0.06)' : 'none',
        transition: 'all 0.15s ease',
        position: 'relative',
        ...style,
      }}
      onMouseEnter={e => {
        if (!active) {
          e.currentTarget.style.background = 'var(--surface-secondary)'
          e.currentTarget.style.borderColor = 'var(--border-subtle)'
        }
      }}
      onMouseLeave={e => {
        if (!active) {
          e.currentTarget.style.background = 'var(--surface-primary)'
          e.currentTarget.style.borderColor = 'transparent'
        }
      }}
    >
      {/* 左侧装饰条 */}
      {accentColor && (
        <div style={{
          position: 'absolute', left: 0, top: 8, bottom: 8, width: 3, borderRadius: 2,
          background: accentColor,
          opacity: active ? 1 : 0.4,
          transition: 'opacity 0.15s',
        }} />
      )}
      {children}
    </div>
  )
}

/** CardSkeleton — 卡片加载骨架屏 */
export function CardSkeleton({ count = 3 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} style={{ padding: '12px 14px', margin: '0 8px 6px', borderRadius: 10 }}>
          <div style={{ height: 14, width: '60%', background: 'var(--surface-tertiary)', borderRadius: 4, marginBottom: 8, animation: 'pulse 1.5s ease-in-out infinite' }} />
          <div style={{ height: 10, width: '40%', background: 'var(--surface-tertiary)', borderRadius: 4, animation: 'pulse 1.5s ease-in-out infinite', animationDelay: '0.1s' }} />
        </div>
      ))}
    </>
  )
}
