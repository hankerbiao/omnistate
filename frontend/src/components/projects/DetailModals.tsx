// ═══════════════════════════════════════════════════════════════════════
//  projects/DetailModals.tsx — 项目详情页的下钻弹窗与统计卡片组件
// ═══════════════════════════════════════════════════════════════════════

import type { ReactNode } from 'react'
import type { MockTask, MockCase, MockPlan, MockRequirement } from './mockData'

// ── 共享样式 ─────────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  modalOverlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 } as const,
  modal: { background: 'var(--surface-primary)', borderRadius: 12, width: 680, maxWidth: '90vw', maxHeight: '85vh', overflowY: 'auto', padding: 28, boxShadow: '0 8px 32px rgba(0,0,0,0.3)' } as const,
  progressBar: { height: 6, borderRadius: 3, background: 'var(--surface-tertiary)', overflow: 'hidden', marginTop: 4 } as const,
  progressFill: (pct: number, color: string) => ({ width: `${Math.min(pct, 100)}%`, height: '100%', background: color, borderRadius: 3, transition: 'width 0.3s' }),
  pill: (bg: string, fg: string) => ({ display: 'inline-block', fontSize: 9, padding: '1px 6px', borderRadius: 7, background: bg, color: fg, fontWeight: 600 }),
  statCard: { background: 'var(--surface-secondary)', borderRadius: 6, padding: '10px 8px', textAlign: 'center', flex: 1, minWidth: 0 } as const,
  statValue: { fontSize: 18, fontWeight: 700, color: 'var(--accent-primary)', lineHeight: 1.1 } as const,
  statLabel: { fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 } as const,
}

export function pctStr(v: number): string { return `${v}%` }

const PRIORITY: Record<string, { label: string; color: string }> = {
  P0: { label: 'P0', color: '#f85149' }, P1: { label: 'P1', color: '#d29922' }, P2: { label: 'P2', color: '#8b949e' },
}

// ── 通用弹窗 ─────────────────────────────────────────────────────────

export function DetailModal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return (
    <div style={s.modalOverlay} onClick={onClose}>
      <div style={{ ...s.modal, width: 760 }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <span style={{ fontSize: 16, fontWeight: 700 }}>{title}</span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 20, color: 'var(--text-tertiary)' }}>×</button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function SectionHeader({ title, onClick }: { title: string; onClick?: () => void }) {
  return (
    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', cursor: onClick ? 'pointer' : 'default' }} onClick={onClick}>
      <span>{title}</span>
      {onClick && <span style={{ fontSize: 10, color: 'var(--text-tertiary)', marginLeft: 8, opacity: 0.6 }}>→ 查看详情</span>}
    </div>
  )
}

// ── 详情表格 ─────────────────────────────────────────────────────────

export function TaskDetailTable({ tasks }: { tasks: MockTask[] }) {
  const rowStyle = (status: string): React.CSSProperties => ({
    padding: '8px 10px', fontSize: 12, borderBottom: '1px solid var(--border-subtle)', display: 'grid', gridTemplateColumns: '80px 1fr 70px 60px 60px 80px', gap: 8, alignItems: 'center',
  })
  const statusPill = (st: string) => {
    const map: Record<string, [string, string]> = { '已完成': ['#3fb950', '#3fb95022'], '进行中': ['#d29922', '#d2992222'], '失败': ['#f85149', '#f8514922'], '待执行': ['#8b949e', '#8b949e22'] }
    const [c, b] = map[st] || ['#8b949e', '#8b949e22']; return <span style={s.pill(b, c)}>{st}</span>
  }
  return (
    <div>
      <div style={{ ...rowStyle(''), fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '2px solid var(--border-default)' }}>
        <span>编号</span><span>任务名称</span><span>负责人</span><span>进度</span><span>优先级</span><span>状态</span>
      </div>
      {tasks.map(t => (
        <div key={t.id} style={rowStyle(t.status)}>
          <span style={{ fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{t.id}</span>
          <span style={{ fontWeight: 500 }}>{t.name}</span>
          <span style={{ color: 'var(--text-secondary)' }}>{t.assignee}</span>
          <span>{pctStr(t.progress)}</span>
          <span style={s.pill(PRIORITY[t.priority]?.color + '22' || '#8b949e22', PRIORITY[t.priority]?.color || '#8b949e')}>{t.priority}</span>
          <span>{statusPill(t.status)}</span>
        </div>
      ))}
    </div>
  )
}

export function CaseDetailTable({ cases }: { cases: MockCase[]; type?: string }) {
  const rowStyle: React.CSSProperties = { padding: '8px 10px', fontSize: 12, borderBottom: '1px solid var(--border-subtle)', display: 'grid', gridTemplateColumns: '90px 1fr 70px 60px 60px', gap: 8, alignItems: 'center' }
  const stPill = (st: string) => {
    const map: Record<string, [string, string]> = { '通过': ['#3fb950', '#3fb95022'], '失败': ['#f85149', '#f8514922'], '阻塞': ['#8b949e', '#8b949e22'], '进行中': ['#d29922', '#d2992222'], '未执行': ['#8b949e', '#8b949e22'] }
    const [c, b] = map[st] || ['#8b949e', '#8b949e22']; return <span style={s.pill(b, c)}>{st}</span>
  }
  return (
    <div>
      <div style={{ ...rowStyle, fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '2px solid var(--border-default)' }}>
        <span>编号</span><span>用例名称</span><span>模块</span><span>优先级</span><span>结果</span>
      </div>
      {cases.map(c => (
        <div key={c.id} style={rowStyle}>
          <span style={{ fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{c.id}</span>
          <span style={{ fontWeight: 500 }}>{c.title}</span>
          <span style={{ color: 'var(--text-secondary)' }}>{c.module}</span>
          <span style={s.pill(PRIORITY[c.priority]?.color + '22' || '#8b949e22', PRIORITY[c.priority]?.color || '#8b949e')}>{c.priority}</span>
          <span>{stPill(c.lastResult)}</span>
        </div>
      ))}
    </div>
  )
}

export function PlanDetailTable({ plans }: { plans: MockPlan[] }) {
  const rowStyle: React.CSSProperties = { padding: '10px', fontSize: 12, borderBottom: '1px solid var(--border-subtle)', display: 'grid', gridTemplateColumns: '80px 1fr 70px 60px 60px 80px', gap: 8, alignItems: 'center' }
  const stPill = (st: string) => {
    const map: Record<string, [string, string]> = { '已完成': ['#3fb950', '#3fb95022'], '进行中': ['#d29922', '#d2992222'], '待执行': ['#8b949e', '#8b949e22'] }
    const [c, b] = map[st] || ['#8b949e', '#8b949e22']; return <span style={s.pill(b, c)}>{st}</span>
  }
  return (
    <div>
      <div style={{ ...rowStyle, fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '2px solid var(--border-default)' }}>
        <span>编号</span><span>计划名称</span><span>状态</span><span>通过率</span><span>执行人</span><span>周期</span>
      </div>
      {plans.map(p => (
        <div key={p.id} style={rowStyle}>
          <span style={{ fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{p.id}</span>
          <span style={{ fontWeight: 500 }}>{p.name}</span>
          <span>{stPill(p.status)}</span>
          <span style={{ fontWeight: 600, color: p.passed / p.total > 0.8 ? '#3fb950' : '#d29922' }}>{pctStr(Math.round(p.passed / p.total * 100))}</span>
          <span style={{ color: 'var(--text-secondary)' }}>{p.executor}</span>
          <span style={{ color: 'var(--text-secondary)' }}>{p.date}</span>
        </div>
      ))}
    </div>
  )
}

export function ReqDetailTable({ reqs }: { reqs: MockRequirement[] }) {
  const rowStyle: React.CSSProperties = { padding: '10px', fontSize: 12, borderBottom: '1px solid var(--border-subtle)', display: 'grid', gridTemplateColumns: '80px 1fr 60px 80px 60px 70px', gap: 8, alignItems: 'center' }
  const stPill = (st: string) => {
    const map: Record<string, [string, string]> = { '已覆盖': ['#3fb950', '#3fb95022'], '部分覆盖': ['#d29922', '#d2992222'], '未覆盖': ['#f85149', '#f8514922'] }
    const [c, b] = map[st] || ['#8b949e', '#8b949e22']; return <span style={s.pill(b, c)}>{st}</span>
  }
  return (
    <div>
      <div style={{ ...rowStyle, fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, borderBottom: '2px solid var(--border-default)' }}>
        <span>编号</span><span>需求名称</span><span>优先级</span><span>覆盖状态</span><span>用例数</span><span>覆盖率</span>
      </div>
      {reqs.map(r => (
        <div key={r.id} style={rowStyle}>
          <span style={{ fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{r.id}</span>
          <span style={{ fontWeight: 500 }}>{r.title}</span>
          <span style={s.pill(PRIORITY[r.priority]?.color + '22' || '#8b949e22', PRIORITY[r.priority]?.color || '#8b949e')}>{r.priority}</span>
          <span>{stPill(r.status)}</span>
          <span>{r.caseCount}</span>
          <span style={{ fontWeight: 600, color: r.coverageRate >= 80 ? '#3fb950' : r.coverageRate >= 50 ? '#d29922' : '#f85149' }}>{pctStr(r.coverageRate)}</span>
        </div>
      ))}
    </div>
  )
}

// ── 进度卡 ──────────────────────────────────────────────────────────

export function MiniProgress({ label, done, total, color = 'var(--accent-primary)' }: { label: string; done: number; total: number; color?: string }) {
  const pct = total > 0 ? Math.round(done / total * 100) : 0
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 2 }}>
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontWeight: 600, fontSize: 11 }}>{done}/{total}  {pctStr(pct)}</span>
      </div>
      <div style={s.progressBar}>
        <div style={s.progressFill(pct, color)} />
      </div>
    </div>
  )
}

// ── 通过率卡 ─────────────────────────────────────────────────────────

export function PassCard({ label, stats, color, onClick }: {
  label: string; stats: { total: number; passed: number; failed: number; pass_rate: number }; color: string; onClick?: () => void
}) {
  return (
    <div style={{ ...s.statCard, textAlign: 'left', ...(onClick ? { cursor: 'pointer' } : {}) }} onClick={onClick}>
      <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 700 }}>{pctStr(stats.pass_rate)}</div>
      <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>
        {stats.passed}/{stats.total} 通过
        {stats.failed > 0 && <span style={{ color: '#f85149' }}> | {stats.failed} 失败</span>}
      </div>
      <div style={s.progressBar}>
        <div style={s.progressFill(stats.pass_rate, color)} />
      </div>
    </div>
  )
}
