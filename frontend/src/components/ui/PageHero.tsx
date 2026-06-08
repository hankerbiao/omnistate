/** 可复用的页面 Hero 头部组件 */
import type { ReactNode } from 'react'

interface PageHeroProps {
  /** 徽章标签文字（如 "Catalog Intelligence"） */
  badge: string
  /** 徽章图标（SVG 元素） */
  badgeIcon?: ReactNode
  /** 描述文字 */
  description: string
  /** 主题色（用于渐变和装饰元素）— 默认 indigo (#6366f1) */
  accent?: string
  /** 渐变色方案 — 3 个色值，默认靛蓝→紫→青 */
  gradient?: [string, string, string]
  /** 额外的子元素（如统计卡片），放在 hero 下方 */
  children?: ReactNode
  /** 样式扩展 */
  style?: React.CSSProperties
}

const defaultGradient: [string, string, string] = ['#eef2ff', '#f5f3ff', '#ecfeff']

function StarIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z" />
      <path d="M19 13l1 3 3 1-3 1-1 3-1-3-3-1 3-1 1-3z" />
    </svg>
  )
}

export default function PageHero({
  badge,
  badgeIcon,
  description,
  accent = '#6366f1',
  gradient = defaultGradient,
  children,
  style,
}: PageHeroProps) {
  const [c1, c2, c3] = gradient

  return (
    <div>
      <header style={{
        position: 'relative',
        borderRadius: 'var(--radius-xl)',
        padding: 'var(--space-5) var(--space-6)',
        marginBottom: children ? 'var(--space-6)' : 0,
        overflow: 'hidden',
        background: `linear-gradient(135deg, ${c1} 0%, ${c2} 45%, ${c3} 100%)`,
        border: `1px solid color-mix(in srgb, ${accent} 18%, var(--border-subtle))`,
        ...style,
      }}>
        {/* 装饰光晕 */}
        <div style={{
          position: 'absolute',
          top: -40,
          right: -20,
          width: 200,
          height: 200,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${accent}25 0%, transparent 70%)`,
          pointerEvents: 'none',
        }} />

        <div style={{ position: 'relative', zIndex: 1 }}>
          {/* 徽章 */}
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '4px 12px',
            marginBottom: 'var(--space-2)',
            fontSize: 12,
            fontWeight: 600,
            color: accent,
            backgroundColor: `${accent}1f`,
            borderRadius: 'var(--radius-full)',
            border: `1px solid ${accent}33`,
          }}>
            {badgeIcon || <StarIcon />}
            <span>{badge}</span>
          </div>

          {/* 描述 */}
          <p style={{
            margin: 0,
            fontSize: 14,
            color: 'var(--text-secondary)',
            maxWidth: 560,
            lineHeight: 1.6,
          }}>
            {description}
          </p>
        </div>
      </header>

      {children}
    </div>
  )
}
