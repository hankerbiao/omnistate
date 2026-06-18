/** MiniDonut — 简约 SVG 环形进度图 */
interface MiniDonutProps {
  pct: number
  size?: number
  strokeWidth?: number
  color?: string
  bgColor?: string
}
export function MiniDonut({ pct, size = 36, strokeWidth = 3.5, color = 'var(--accent-primary)', bgColor = 'var(--surface-tertiary)' }: MiniDonutProps) {
  const r = (size - strokeWidth) / 2
  const circ = 2 * Math.PI * r
  const dash = Math.min(Math.max(pct, 0), 100) / 100 * circ
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={bgColor} strokeWidth={strokeWidth} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={strokeWidth}
        strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        style={{ transition: 'stroke-dasharray 0.4s ease' }} />
    </svg>
  )
}

/** MiniSparkline — 简约微型折线图（3 个数据点趋势） */
interface MiniSparklineProps {
  values: number[]
  color?: string
  width?: number
  height?: number
}
export function MiniSparkline({ values, color = 'var(--accent-primary)', width = 48, height = 20 }: MiniSparklineProps) {
  if (values.length < 2) return null
  const max = Math.max(...values, 1)
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * width},${height - (v / max) * height}`).join(' ')
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" points={pts} />
    </svg>
  )
}

/** ModernStat — 增强型统计卡片（含可选环形图/趋势图） */
interface ModernStatProps {
  value: string | number
  label: string
  pct?: number
  trend?: number[]
  color?: string
  detail?: string
}
export function ModernStat({ value, label, pct, trend, color = 'var(--accent-primary)', detail }: ModernStatProps) {
  return (
    <div style={{
      background: 'var(--surface-secondary)', borderRadius: 10, padding: '16px 14px',
      display: 'flex', alignItems: 'center', gap: 14, border: '1px solid var(--border-subtle)',
      transition: 'box-shadow 0.15s, transform 0.15s',
    }}
      onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.06)'; e.currentTarget.style.transform = 'translateY(-1px)' }}
      onMouseLeave={e => { e.currentTarget.style.boxShadow = 'none'; e.currentTarget.style.transform = 'none' }}
    >
      {(pct !== undefined) && <MiniDonut pct={pct} color={color} />}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 20, fontWeight: 700, lineHeight: 1.3 }}>{value}</div>
        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>{label}</div>
        {detail && <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 1 }}>{detail}</div>}
      </div>
      {trend && trend.length >= 2 && (
        <div style={{ flexShrink: 0, opacity: 0.6 }}>
          <MiniSparkline values={trend} color={trend[trend.length - 1] >= trend[0] ? '#3fb950' : '#f85149'} />
        </div>
      )}
    </div>
  )
}
