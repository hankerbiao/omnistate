// ═══════════════════════════════════════════════════════════════════════
//  ProjectsPage — 项目管理页面
//   分栏布局：左侧项目列表 + 右侧项目详情（含统计面板/进度/通过率/快捷操作）
// ═══════════════════════════════════════════════════════════════════════

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigation } from '../providers/NavigationProvider'
import { api } from '../services/api'
import type {
  Project,
  ProjectDetail,
  ProjectStats,
  AssigneeDistribution,
} from '../types'

// ── 样式 ─────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  wrapper: { height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  toolbar: { display: 'flex', alignItems: 'center', gap: 10, padding: '10px 24px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--surface-primary)', flexShrink: 0 },
  workspace: { flex: 1, display: 'flex', overflow: 'hidden' },
  sidePanel: { width: 320, borderRight: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', overflow: 'hidden', flexShrink: 0 },
  mainPanel: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  scroll: { flex: 1, overflowY: 'auto', padding: '12px 0' },
  detailScroll: { flex: 1, overflowY: 'auto', padding: '24px' },
  statCard: { background: 'var(--surface-secondary)', borderRadius: 8, padding: '14px 12px', textAlign: 'center', flex: 1, minWidth: 0 },
  statValue: { fontSize: 22, fontWeight: 700, color: 'var(--accent-primary)', lineHeight: 1.2 },
  statLabel: { fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 },
  progressBar: { height: 8, borderRadius: 4, background: 'var(--surface-tertiary)', overflow: 'hidden', marginTop: 6 },
  progressFill: (pct: number, color: string) => ({ width: `${Math.min(pct, 100)}%`, height: '100%', background: color, borderRadius: 4, transition: 'width 0.3s' }),
  pill: (bg: string, fg: string) => ({ display: 'inline-block', fontSize: 10, padding: '1px 7px', borderRadius: 9, background: bg, color: fg, fontWeight: 600 }),
  modalOverlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 },
  modal: { background: 'var(--surface-primary)', borderRadius: 12, width: 540, maxWidth: '90vw', maxHeight: '85vh', overflowY: 'auto', padding: 28, boxShadow: '0 8px 32px rgba(0,0,0,0.3)' },
}

// ── helpers ───────────────────────────────────────────────────────────

function fmtDate(d: string | null | undefined): string {
  if (!d) return '-'
  try { return new Date(d).toLocaleDateString('zh-CN') } catch { return d }
}

function pctStr(v: number): string { return `${v}%` }

const PRIORITY: Record<string, { label: string; color: string }> = {
  P0: { label: 'P0', color: '#f85149' },
  P1: { label: 'P1', color: '#d29922' },
  P2: { label: 'P2', color: '#8b949e' },
}

const STATUS: Record<string, { label: string; color: string }> = {
  active: { label: '活跃', color: '#3fb950' },
  archived: { label: '已归档', color: '#8b949e' },
}

// ── 子组件：进度卡 ───────────────────────────────────────────────────

function MiniProgress({ label, done, total, color = 'var(--accent-primary)' }: { label: string; done: number; total: number; color?: string }) {
  const pct = total > 0 ? Math.round(done / total * 100) : 0
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}>
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontWeight: 600 }}>{done}/{total}  {pctStr(pct)}</span>
      </div>
      <div style={styles.progressBar}>
        <div style={styles.progressFill(pct, color)} />
      </div>
    </div>
  )
}

// ── 子组件：通过率卡 ─────────────────────────────────────────────────

function PassCard({ label, stats, color }: { label: string; stats: { total: number; passed: number; failed: number; pass_rate: number }; color: string }) {
  return (
    <div style={{ ...styles.statCard, textAlign: 'left' }}>
      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700 }}>{pctStr(stats.pass_rate)}</div>
      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>
        {stats.passed}/{stats.total} 通过
        {stats.failed > 0 && <span style={{ color: '#f85149' }}> | {stats.failed} 失败</span>}
      </div>
      <div style={styles.progressBar}>
        <div style={styles.progressFill(stats.pass_rate, color)} />
      </div>
    </div>
  )
}

// ── 主组件 ───────────────────────────────────────────────────────────

export default function ProjectsPage() {
  // state
  const { navigate } = useNavigation()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState('')
  const [projectDetail, setProjectDetail] = useState<ProjectDetail | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  // modal
  const [showModal, setShowModal] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [form, setForm] = useState({ name: '', key: '', description: '', priority: 'P2', owner_id: '', start_date: '', end_date: '', target_version: '', tags: '' })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  // data fetch
  const fetchProjects = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const params: Record<string, string> = {}
      if (statusFilter) params.status = statusFilter
      if (searchQuery) params.name = searchQuery
      const res = await api.listProjects(params)
      const list = res.data || { items: [], total: 0 }
      setProjects(list.items || [])
    } catch { setError('获取项目列表失败') } finally { setLoading(false) }
  }, [statusFilter, searchQuery])

  useEffect(() => { void fetchProjects() }, [fetchProjects])

  useEffect(() => {
    if (!selectedId) { setProjectDetail(null); return }
    api.getProject(selectedId).then(res => setProjectDetail(res.data || null)).catch(() => setProjectDetail(null))
  }, [selectedId])

  const selectedProject = projects.find(p => p.project_id === selectedId) || null

  const filtered = useMemo(() => {
    let list = projects
    if (searchQuery) { const q = searchQuery.toLowerCase(); list = list.filter(p => p.name.toLowerCase().includes(q) || p.key.toLowerCase().includes(q)) }
    if (statusFilter) list = list.filter(p => p.status === statusFilter)
    return list
  }, [projects, searchQuery, statusFilter])

  // modal open
  const openCreate = () => { setEditMode(false); setForm({ name: '', key: '', description: '', priority: 'P2', owner_id: '', start_date: '', end_date: '', target_version: '', tags: '' }); setFormError(''); setShowModal(true) }
  const openEdit = () => {
    if (!selectedProject) return
    setEditMode(true)
    setForm({
      name: selectedProject.name, key: selectedProject.key, description: selectedProject.description || '',
      priority: selectedProject.priority || 'P2', owner_id: selectedProject.owner_id || '',
      start_date: selectedProject.start_date ? selectedProject.start_date.slice(0, 10) : '',
      end_date: selectedProject.end_date ? selectedProject.end_date.slice(0, 10) : '',
      target_version: selectedProject.target_version || '',
      tags: selectedProject.tags?.join(', ') || '',
    })
    setFormError(''); setShowModal(true)
  }

  const handleSave = async () => {
    if (!form.name.trim()) { setFormError('项目名称不能为空'); return }
    if (!editMode && !form.key.trim()) { setFormError('项目标识不能为空'); return }
    setSaving(true); setFormError('')
    try {
      const payload: import('../types').CreateProjectRequest | import('../types').UpdateProjectRequest = {
        name: form.name.trim(),
        key: form.key.trim(),
        description: form.description.trim() || null,
        priority: form.priority,
        owner_id: form.owner_id || null,
        start_date: form.start_date ? new Date(form.start_date).toISOString() : null,
        end_date: form.end_date ? new Date(form.end_date).toISOString() : null,
        target_version: form.target_version || null,
        tags: form.tags ? form.tags.split(',').map(s => s.trim()).filter(Boolean) : [],
      }
      if (editMode) { await api.updateProject(selectedId, payload as import('../types').UpdateProjectRequest) }
      else { await api.createProject(payload as import('../types').CreateProjectRequest) }
      setShowModal(false); await fetchProjects()
    } catch (err: unknown) { setFormError(err instanceof Error ? err.message : '保存失败') } finally { setSaving(false) }
  }

  const handleDelete = async () => {
    if (!selectedId || !confirm(`确定删除项目「${selectedProject?.name}」？`)) return
    try { await api.deleteProject(selectedId); setSelectedId(''); await fetchProjects() } catch { setError('删除失败') }
  }

  const handleToggleStatus = async () => {
    if (!selectedId || !selectedProject) return
    const ns = selectedProject.status === 'active' ? 'archived' : 'active'
    try {
      await api.updateProject(selectedId, { status: ns })
      await fetchProjects()
      setProjectDetail(prev => prev ? { ...prev, status: ns } : prev)
    } catch { setError('状态更新失败') }
  }

  // stats helpers
  const stats = projectDetail?.stats as ProjectStats | null
  const taskBreakdown = stats?.task

  return (
    <div style={styles.wrapper}>
      {/* toolbar */}
      <div style={styles.toolbar}>
        <input className="form-input" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="搜索项目..." style={{ width: 180, fontSize: 13, padding: '5px 10px' }} />
        {[{ key: '', label: '全部' }, { key: 'active', label: '活跃' }, { key: 'archived', label: '已归档' }].map(f => (
          <button key={f.key} onClick={() => setStatusFilter(f.key)} style={{ padding: '3px 10px', fontSize: 12, border: 'none', borderRadius: 6, cursor: 'pointer', background: statusFilter === f.key ? 'var(--accent-primary)' : 'var(--surface-secondary)', color: statusFilter === f.key ? '#fff' : 'var(--text-secondary)', fontWeight: statusFilter === f.key ? 600 : 400 }}>{f.label}</button>
        ))}
        <div style={{ flex: 1 }} />
        <button className="btn btn--primary btn--sm" onClick={openCreate} style={{ padding: '6px 16px', fontSize: 13 }}>+ 新建项目</button>
      </div>

      {/* workspace */}
      <div style={styles.workspace}>
        <aside style={styles.sidePanel}>
          <div style={styles.scroll}>
            {loading && <div style={{ padding: 16, fontSize: 13, color: 'var(--text-secondary)' }}>加载中...</div>}
            {error && <div style={{ padding: 16, fontSize: 13, color: '#f85149' }}>{error}</div>}
            {!loading && !error && filtered.length === 0 && (
              <div style={{ padding: 16, fontSize: 13, color: 'var(--text-secondary)' }}>
                {searchQuery || statusFilter ? '无匹配项目' : '暂无项目，点击上方按钮创建'}
              </div>)}
            {filtered.map(p => {
              const meta = STATUS[p.status] || { label: p.status, color: '#8b949e' }
              const prio = PRIORITY[p.priority] || PRIORITY.P2
              const isActive = p.project_id === selectedId
              return (
                <div key={p.project_id} onClick={() => setSelectedId(p.project_id)}
                  style={{ padding: '10px 16px', cursor: 'pointer', borderLeft: isActive ? '3px solid var(--accent-primary)' : '3px solid transparent', background: isActive ? 'var(--surface-secondary)' : 'transparent', transition: 'background 0.15s' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                    <span style={{ fontSize: 14, fontWeight: 600, flex: 1 }}>{p.name}</span>
                    <span style={styles.pill(prio.color + '22', prio.color)}>{prio.label}</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span>{p.key}</span>
                    <span style={{ color: meta.color }}>{meta.label}</span>
                    {p.target_version && <span>v{p.target_version}</span>}
                  </div>
                  {p.start_date && p.end_date && (
                    <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>{fmtDate(p.start_date)} ~ {fmtDate(p.end_date)}</div>
                  )}
                </div>
              )
            })}
          </div>
        </aside>

        <main style={styles.mainPanel}>
          {selectedProject ? (
            <div style={styles.detailScroll}>
              {/* header */}
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                    <button className="btn btn--ghost btn--sm" onClick={() => setSelectedId('')} style={{ fontSize: 12 }}>← 返回列表</button>
                    <span style={{ fontSize: 18, fontWeight: 700 }}>{selectedProject.name}</span>
                    <span style={styles.pill(STATUS[selectedProject.status]?.color + '22', STATUS[selectedProject.status]?.color || '#8b949e')}>{STATUS[selectedProject.status]?.label}</span>
                    <span style={styles.pill(PRIORITY[selectedProject.priority]?.color + '22', PRIORITY[selectedProject.priority]?.color || '#8b949e')}>{PRIORITY[selectedProject.priority]?.label}</span>
                  </div>
                  {selectedProject.description && <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginLeft: 0 }}>{selectedProject.description}</div>}
                </div>
                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  <button className="btn btn--ghost btn--sm" onClick={handleToggleStatus} style={{ fontSize: 12 }}>{selectedProject.status === 'active' ? '归档' : '激活'}</button>
                  <button className="btn btn--secondary btn--sm" onClick={openEdit} style={{ fontSize: 12 }}>编辑</button>
                  <button className="btn btn--danger btn--sm" onClick={handleDelete} style={{ fontSize: 12 }}>删除</button>
                </div>
              </div>

              {/* meta row */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginBottom: 20, padding: 14, background: 'var(--surface-secondary)', borderRadius: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
                <span>标识：<b style={{ color: 'var(--text-primary)' }}>{selectedProject.key}</b></span>
                {selectedProject.owner && <span>负责人：<b>{selectedProject.owner.username}</b></span>}
                {selectedProject.target_version && <span>目标版本：<b>{selectedProject.target_version}</b></span>}
                {selectedProject.start_date && <span>周期：{fmtDate(selectedProject.start_date)} ~ {fmtDate(selectedProject.end_date)}</span>}
                <span>创建者：{selectedProject.created_by || '-'} | {fmtDate(selectedProject.created_at)}</span>
                {selectedProject.tags?.length > 0 && (
                  <span>标签：{selectedProject.tags.map((t, i) => <span key={i} style={styles.pill('var(--accent-primary)' + '18', 'var(--accent-primary)')}>{t}</span>)}</span>
                )}
              </div>

              {/* overall progress */}
              {stats && (
                <>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>整体进度</div>
                  <div style={{ marginBottom: 20 }}>
                    <MiniProgress label="执行任务" done={taskBreakdown?.done || 0} total={taskBreakdown?.total || 0} color="#3fb950" />
                    <MiniProgress label="手工通过率" done={stats.manual_pass.passed} total={stats.manual_pass.total} color="#58a6ff" />
                    <MiniProgress label="自动化通过率" done={stats.auto_pass.passed} total={stats.auto_pass.total} color="#d29922" />
                    <MiniProgress label="需求覆盖率" done={stats.test_case_count} total={stats.requirement_count} color="#a371f7" />
                  </div>
                </>
              )}

              {/* stat cards */}
              {stats && (
                <div style={{ marginBottom: 24 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>统计数据</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                    <div style={styles.statCard}><div style={styles.statValue}>{stats.test_case_count}</div><div style={styles.statLabel}>手工用例</div></div>
                    <div style={styles.statCard}><div style={styles.statValue}>{stats.auto_case_count}</div><div style={styles.statLabel}>自动化用例</div></div>
                    <div style={styles.statCard}><div style={styles.statValue}>{stats.requirement_count}</div><div style={styles.statLabel}>测试需求</div></div>
                    <div style={styles.statCard}><div style={styles.statValue}>{stats.plan_count}</div><div style={styles.statLabel}>执行计划</div></div>
                  </div>
                </div>
              )}

              {/* pass rates */}
              {stats && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 24 }}>
                  <PassCard label="手工通过率" stats={stats.manual_pass} color="#58a6ff" />
                  <PassCard label="自动化通过率" stats={stats.auto_pass} color="#d29922" />
                  <div style={{ ...styles.statCard, textAlign: 'left' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>需求覆盖率</div>
                    <div style={{ fontSize: 18, fontWeight: 700 }}>{pctStr(stats.coverage_rate)}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>{stats.test_case_count} 用例 / {stats.requirement_count} 需求</div>
                    <div style={styles.progressBar}><div style={styles.progressFill(stats.coverage_rate, '#a371f7')} /></div>
                  </div>
                </div>
              )}

              {/* task breakdown */}
              {taskBreakdown && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10, marginBottom: 24 }}>
                  <div style={styles.statCard}><div style={styles.statValue}>{taskBreakdown.total}</div><div style={styles.statLabel}>任务总数</div></div>
                  <div style={styles.statCard}><div style={{ ...styles.statValue, color: '#3fb950' }}>{taskBreakdown.done}</div><div style={styles.statLabel}>已完成</div></div>
                  <div style={styles.statCard}><div style={{ ...styles.statValue, color: '#d29922' }}>{taskBreakdown.running}</div><div style={styles.statLabel}>运行中</div></div>
                  <div style={styles.statCard}><div style={{ ...styles.statValue, color: '#f85149' }}>{taskBreakdown.failed}</div><div style={styles.statLabel}>失败</div></div>
                  <div style={styles.statCard}><div style={{ ...styles.statValue, color: '#8b949e' }}>{taskBreakdown.pending}</div><div style={styles.statLabel}>待执行</div></div>
                </div>
              )}

              {/* assignee distribution */}
              {stats?.assignee_distribution?.length > 0 && (
                <div style={{ marginBottom: 24 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>执行人分布</div>
                  {(stats.assignee_distribution as AssigneeDistribution[]).map((a, i) => (
                    <div key={a.assignee_id || i} style={{ marginBottom: 8 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 2 }}>
                        <span>{a.assignee_name || a.assignee_id || '未分配'}</span>
                        <span>{a.done_count}/{a.item_count}  {pctStr(a.progress)}</span>
                      </div>
                      <div style={styles.progressBar}><div style={styles.progressFill(a.progress, '#58a6ff')} /></div>
                    </div>
                  ))}
                </div>
              )}

              {/* quick actions */}
              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 20, marginBottom: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>快捷操作</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button className="btn btn--secondary btn--sm" onClick={() => navigate('testCases')} style={{ fontSize: 12 }}>+ 新建用例</button>
                  <button className="btn btn--secondary btn--sm" onClick={() => navigate('testPlanStudioDemo')} style={{ fontSize: 12 }}>+ 新建执行计划</button>
                  <button className="btn btn--secondary btn--sm" onClick={() => navigate('collections')} style={{ fontSize: 12 }}>+ 新建用例集</button>
                  <button className="btn btn--secondary btn--sm" onClick={() => navigate('requirements')} style={{ fontSize: 12 }}>+ 新建需求</button>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontSize: 14 }}>
              选择一个项目查看详情
            </div>
          )}
        </main>
      </div>

      {/* modal */}
      {showModal && (
        <div style={styles.modalOverlay} onClick={() => setShowModal(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>{editMode ? '编辑项目' : '新建项目'}</div>
            {formError && <div style={{ fontSize: 12, color: '#f85149', marginBottom: 12, padding: 8, background: '#f8514911', borderRadius: 6 }}>{formError}</div>}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label style={labelStyle}>名称 *</label>
                <input className="form-input" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>标识 {editMode ? '' : '*'}</label>
                <input className="form-input" value={form.key} onChange={e => setForm(p => ({ ...p, key: e.target.value.toUpperCase().replace(/[^A-Z0-9_-]/g, '') }))} disabled={editMode} style={inputStyle} />
              </div>
              <div style={{ gridColumn: 'span 2' }}>
                <label style={labelStyle}>描述</label>
                <textarea className="form-input" value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} rows={2} style={{ width: '100%', fontSize: 13, padding: '6px 10px', resize: 'vertical' }} />
              </div>
              <div>
                <label style={labelStyle}>优先级</label>
                <select className="form-input" value={form.priority} onChange={e => setForm(p => ({ ...p, priority: e.target.value }))} style={inputStyle}>
                  <option value="P0">P0 - 最高</option>
                  <option value="P1">P1 - 高</option>
                  <option value="P2">P2 - 普通</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>目标版本</label>
                <input className="form-input" value={form.target_version} onChange={e => setForm(p => ({ ...p, target_version: e.target.value }))} placeholder="v1.0.0" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>计划开始</label>
                <input type="date" className="form-input" value={form.start_date} onChange={e => setForm(p => ({ ...p, start_date: e.target.value }))} style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>计划结束</label>
                <input type="date" className="form-input" value={form.end_date} onChange={e => setForm(p => ({ ...p, end_date: e.target.value }))} style={inputStyle} />
              </div>
              <div style={{ gridColumn: 'span 2' }}>
                <label style={labelStyle}>标签（逗号分隔）</label>
                <input className="form-input" value={form.tags} onChange={e => setForm(p => ({ ...p, tags: e.target.value }))} placeholder="回归, 冒烟, 合入" style={inputStyle} />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 20 }}>
              <button className="btn btn--ghost btn--sm" onClick={() => setShowModal(false)} style={{ fontSize: 12, padding: '6px 14px' }}>取消</button>
              <button className="btn btn--primary btn--sm" onClick={handleSave} disabled={saving} style={{ fontSize: 12, padding: '6px 14px' }}>{saving ? '保存中...' : '保存'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const labelStyle: React.CSSProperties = { display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 3 }
const inputStyle: React.CSSProperties = { width: '100%', fontSize: 13, padding: '6px 10px' }
