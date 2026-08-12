// ═══════════════════════════════════════════════════════════════════════
//  ProjectsPage — 项目管理页面
//   分栏布局：左侧项目列表 + 右侧项目详情（统计数据来自后端 API）
// ═══════════════════════════════════════════════════════════════════════

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigation } from '../providers/NavigationProvider'
import { api } from '../services/api'
import type { Project, ProjectDetail, ProjectStats, BlockerItem, ProjectActivity, CreateProjectRequest, UpdateProjectRequest, ProjectMember, ProjectDocument, ProjectFolder, ProjectFile, ProjectDocumentPhase } from '../types'

// ── 样式 ─────────────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  wrapper: { height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  toolbar: { display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--surface-primary)', flexShrink: 0 },
  workspace: { flex: 1, display: 'flex', overflow: 'hidden' },
  sidePanel: { width: 280, borderRight: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', overflow: 'hidden', flexShrink: 0 },
  mainPanel: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  scroll: { flex: 1, overflowY: 'auto', padding: '8px 0' },
  detailScroll: { flex: 1, overflowY: 'auto', padding: '16px 20px' },
  statCard: { background: 'var(--surface-secondary)', borderRadius: 6, padding: '10px 8px', textAlign: 'center', flex: 1, minWidth: 0 },
  statValue: { fontSize: 18, fontWeight: 700, color: 'var(--accent-primary)', lineHeight: 1.1 },
  statLabel: { fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 },
  progressBar: { height: 6, borderRadius: 3, background: 'var(--surface-tertiary)', overflow: 'hidden', marginTop: 4 },
  modalOverlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 },
  modal: { background: 'var(--surface-primary)', borderRadius: 12, width: 680, maxWidth: '90vw', maxHeight: '85vh', overflowY: 'auto', padding: 28, boxShadow: '0 8px 32px rgba(0,0,0,0.3)' },
}

function progressFillStyle(pct: number, color: string): React.CSSProperties {
  return { width: `${Math.min(pct, 100)}%`, height: '100%', background: color, borderRadius: 3, transition: 'width 0.3s' }
}

function pillStyle(bg: string, fg: string): React.CSSProperties {
  return { display: 'inline-block', fontSize: 9, padding: '1px 6px', borderRadius: 7, background: bg, color: fg, fontWeight: 600 }
}

// ── helpers ───────────────────────────────────────────────────────────

function fmtDate(d: string | null | undefined): string {
  if (!d) return '-'
  try { return new Date(d).toLocaleDateString('zh-CN') } catch { return d }
}

function fmtDateTime(d: string | null | undefined): string {
  if (!d) return '-'
  try {
    const dt = new Date(d)
    const now = new Date()
    const diffMs = now.getTime() - dt.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    if (diffMin < 1) return '刚刚'
    if (diffMin < 60) return `${diffMin}分钟前`
    const diffHour = Math.floor(diffMin / 60)
    if (diffHour < 24) return `${diffHour}小时前`
    return dt.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  } catch { return d }
}

function pctStr(v: number): string { return `${v}%` }

const PRIORITY: Record<string, { label: string; color: string }> = {
  P0: { label: 'P0', color: '#f85149' }, P1: { label: 'P1', color: '#d29922' }, P2: { label: 'P2', color: '#8b949e' },
}
const STATUS: Record<string, { label: string; color: string }> = {
  active: { label: '活跃', color: '#3fb950' }, archived: { label: '已归档', color: '#8b949e' },
}

const EMPTY_FORM = { name: '', key: '', description: '', priority: 'P2', start_date: '', end_date: '', target_version: '', tags: '' }

// ── 子组件：进度卡 ───────────────────────────────────────────────────

function MiniProgress({ label, done, total, color = 'var(--accent-primary)' }: { label: string; done: number; total: number; color?: string }) {
  const pct = total > 0 ? Math.round(done / total * 100) : 0
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 2 }}>
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontWeight: 600, fontSize: 11 }}>{done}/{total}  {pctStr(pct)}</span>
      </div>
      <div style={s.progressBar}>
        <div style={progressFillStyle(pct, color)} />
      </div>
    </div>
  )
}

// ── 子组件：通过率卡 ─────────────────────────────────────────────────

function PassCard({ label, stats, color }: { label: string; stats: { total: number; passed: number; failed: number; pass_rate: number }; color: string }) {
  return (
    <div style={{ ...s.statCard, textAlign: 'left' }}>
      <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 700 }}>{pctStr(stats.pass_rate)}</div>
      <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>
        {stats.passed}/{stats.total} 通过
        {stats.failed > 0 && <span style={{ color: '#f85149' }}> | {stats.failed} 失败</span>}
      </div>
      <div style={s.progressBar}>
        <div style={progressFillStyle(stats.pass_rate, color)} />
      </div>
    </div>
  )
}

// ── 主组件 ───────────────────────────────────────────────────────────

export default function ProjectsPage() {
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
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  const [blockers, setBlockers] = useState<BlockerItem[]>([])
  const [activities, setActivities] = useState<ProjectActivity[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [workspace, setWorkspace] = useState<'overview' | 'members' | 'documents' | 'files'>('overview')
  const [members, setMembers] = useState<ProjectMember[]>([])
  const [documents, setDocuments] = useState<ProjectDocument[]>([])
  const [folders, setFolders] = useState<ProjectFolder[]>([])
  const [files, setFiles] = useState<ProjectFile[]>([])
  const [assetError, setAssetError] = useState('')
  const [assetBusy, setAssetBusy] = useState(false)

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
    if (!selectedId) {
      setProjectDetail(null)
      setBlockers([])
      setActivities([])
      return
    }

    let active = true
    setDetailLoading(true)
    Promise.allSettled([
      api.getProject(selectedId),
      api.getProjectBlockers(selectedId),
      api.getProjectActivities(selectedId, 20),
    ]).then(([detailRes, blockerRes, activityRes]) => {
      if (!active) return
      setProjectDetail(detailRes.status === 'fulfilled' ? detailRes.value.data || null : null)
      setBlockers(blockerRes.status === 'fulfilled' ? blockerRes.value.data || [] : [])
      setActivities(activityRes.status === 'fulfilled' ? activityRes.value.data || [] : [])
    }).finally(() => {
      if (active) setDetailLoading(false)
    })

    return () => { active = false }
  }, [selectedId])

  useEffect(() => {
    if (!selectedId) return
    setWorkspace('overview')
    setAssetError('')
    Promise.allSettled([
      api.listProjectMembers(selectedId),
      api.listProjectDocuments(selectedId),
      api.listProjectFolders(selectedId),
      api.listProjectFiles(selectedId),
    ]).then(([memberRes, documentRes, folderRes, fileRes]) => {
      setMembers(memberRes.status === 'fulfilled' ? memberRes.value.data || [] : [])
      setDocuments(documentRes.status === 'fulfilled' ? documentRes.value.data || [] : [])
      setFolders(folderRes.status === 'fulfilled' ? folderRes.value.data || [] : [])
      setFiles(fileRes.status === 'fulfilled' ? fileRes.value.data || [] : [])
    })
  }, [selectedId])

  const selectedProject = projectDetail || projects.find(p => p.project_id === selectedId) || null

  const filtered = useMemo(() => {
    let list = projects
    if (searchQuery) { const q = searchQuery.toLowerCase(); list = list.filter(p => p.name.toLowerCase().includes(q) || p.key.toLowerCase().includes(q)) }
    if (statusFilter) list = list.filter(p => p.status === statusFilter)
    return list
  }, [projects, searchQuery, statusFilter])

  // modal open
  const openCreate = () => { setEditMode(false); setForm(EMPTY_FORM); setFormError(''); setShowModal(true) }
  const openEdit = () => {
    if (!selectedProject) return
    setEditMode(true)
    setForm({
      name: selectedProject.name, key: selectedProject.key, description: selectedProject.description || '',
      priority: selectedProject.priority || 'P2',
      start_date: selectedProject.start_date ? selectedProject.start_date.slice(0, 10) : '',
      end_date: selectedProject.end_date ? selectedProject.end_date.slice(0, 10) : '',
      target_version: selectedProject.target_version || '',
      tags: selectedProject.tags?.join(', ') || '',
    }); setFormError(''); setShowModal(true)
  }
  const handleSave = async () => {
    if (!form.name.trim()) { setFormError('项目名称不能为空'); return }
    if (!editMode && !form.key.trim()) { setFormError('项目标识不能为空'); return }
    setSaving(true); setFormError('')
    try {
      const payload: CreateProjectRequest | UpdateProjectRequest = {
        name: form.name.trim(), key: form.key.trim(), description: form.description.trim() || null,
        priority: form.priority,
        start_date: form.start_date ? new Date(form.start_date).toISOString() : null,
        end_date: form.end_date ? new Date(form.end_date).toISOString() : null,
        target_version: form.target_version || null,
        tags: form.tags ? form.tags.split(',').map(s => s.trim()).filter(Boolean) : [],
      }
      if (editMode) { await api.updateProject(selectedId, payload) }
      else { await api.createProject(payload as CreateProjectRequest) }
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
    try { await api.updateProject(selectedId, { status: ns }); await fetchProjects() } catch { setError('状态更新失败') }
  }

  const refreshAssets = async () => {
    if (!selectedId) return
    const [memberRes, documentRes, folderRes, fileRes] = await Promise.all([
      api.listProjectMembers(selectedId), api.listProjectDocuments(selectedId),
      api.listProjectFolders(selectedId), api.listProjectFiles(selectedId),
    ])
    setMembers(memberRes.data || []); setDocuments(documentRes.data || [])
    setFolders(folderRes.data || []); setFiles(fileRes.data || [])
  }

  const handleDocumentUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !selectedId) return
    const name = window.prompt('文档名称', file.name)?.trim()
    if (!name) return
    const phase = (window.prompt('阶段：ECT / DVT / PVT', 'DVT') || 'DVT').toUpperCase() as ProjectDocumentPhase
    const reviewerText = window.prompt('审核人 user_id，多个用逗号分隔', '') || ''
    const reviewer_ids = reviewerText.split(',').map(item => item.trim()).filter(Boolean)
    setAssetBusy(true); setAssetError('')
    try { await api.createProjectDocument(selectedId, { name, phase_code: phase, reviewer_ids, file }); await refreshAssets() }
    catch (err) { setAssetError(err instanceof Error ? err.message : '文档上传失败') }
    finally { setAssetBusy(false); event.target.value = '' }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !selectedId) return
    setAssetBusy(true); setAssetError('')
    try { await api.uploadProjectFile(selectedId, file); await refreshAssets() }
    catch (err) { setAssetError(err instanceof Error ? err.message : '文件上传失败') }
    finally { setAssetBusy(false); event.target.value = '' }
  }

  const handleCreateFolder = async () => {
    if (!selectedId) return
    const name = window.prompt('文件夹名称')?.trim()
    if (!name) return
    setAssetBusy(true); setAssetError('')
    try { await api.createProjectFolder(selectedId, name); await refreshAssets() }
    catch (err) { setAssetError(err instanceof Error ? err.message : '文件夹创建失败') }
    finally { setAssetBusy(false) }
  }

  // 使用后端真实统计数据
  const stats = projectDetail?.stats as ProjectStats | null
  const taskBreakdown = stats?.task
  const assignees = stats?.assignee_distribution || []

  return (
    <div style={s.wrapper}>
      {/* toolbar */}
      <div style={s.toolbar}>
        <input className="form-input" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="搜索项目..." style={{ width: 160, fontSize: 12, padding: '4px 8px' }} />
        {[{ key: '', label: '全部' }, { key: 'active', label: '活跃' }, { key: 'archived', label: '已归档' }].map(f => (
          <button key={f.key} onClick={() => setStatusFilter(f.key)} style={{ padding: '3px 8px', fontSize: 11, border: 'none', borderRadius: 5, cursor: 'pointer', background: statusFilter === f.key ? 'var(--accent-primary)' : 'var(--surface-secondary)', color: statusFilter === f.key ? '#fff' : 'var(--text-secondary)', fontWeight: statusFilter === f.key ? 600 : 400 }}>{f.label}</button>
        ))}
        <div style={{ flex: 1 }} />
        <button className="btn btn--primary btn--sm" onClick={openCreate} style={{ padding: '5px 14px', fontSize: 12 }}>+ 新建</button>
      </div>

      {/* workspace */}
      <div style={s.workspace}>
        <aside style={s.sidePanel}>
          <div style={s.scroll}>
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
                  style={{ padding: '8px 14px', cursor: 'pointer', borderLeft: isActive ? '3px solid var(--accent-primary)' : '3px solid transparent', background: isActive ? 'var(--surface-secondary)' : 'transparent', transition: 'background 0.12s' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 1 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name}</span>
                    <span style={pillStyle(prio.color + '22', prio.color)}>{prio.label}</span>
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

        <main style={s.mainPanel}>
          {selectedProject ? (
            <div style={s.detailScroll}>
              {/* header + meta */}
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                    <button className="btn btn--ghost btn--sm" onClick={() => setSelectedId('')} style={{ fontSize: 12 }}>← 返回列表</button>
                    <span style={{ fontSize: 16, fontWeight: 700 }}>{selectedProject.name}</span>
                    <span style={pillStyle(STATUS[selectedProject.status]?.color + '22', STATUS[selectedProject.status]?.color || '#8b949e')}>{STATUS[selectedProject.status]?.label}</span>
                    <span style={pillStyle(PRIORITY[selectedProject.priority]?.color + '22', PRIORITY[selectedProject.priority]?.color || '#8b949e')}>{PRIORITY[selectedProject.priority]?.label}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-tertiary)', marginLeft: 4 }}>
                      {selectedProject.key}
                      {selectedProject.created_by && <> | 创建者：{selectedProject.created_by}</>}
                      {selectedProject.created_at && <> | {fmtDate(selectedProject.created_at)}</>}
                      {selectedProject.owner?.username && <> | 负责人：{selectedProject.owner.username}</>}
                      {selectedProject.target_version && <> | v{selectedProject.target_version}</>}
                    </span>
                  </div>
                  {selectedProject.description && <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginLeft: 0 }}>{selectedProject.description}</div>}
                </div>
                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  <button className="btn btn--ghost btn--sm" onClick={handleToggleStatus} style={{ fontSize: 12 }}>{selectedProject.status === 'active' ? '归档' : '激活'}</button>
                  <button className="btn btn--secondary btn--sm" onClick={openEdit} style={{ fontSize: 12 }}>编辑</button>
                  <button className="btn btn--danger btn--sm" onClick={handleDelete} style={{ fontSize: 12 }}>删除</button>
                </div>
              </div>

              {detailLoading && (
                <div style={{ marginBottom: 14, padding: 10, fontSize: 12, color: 'var(--text-secondary)' }}>刷新项目详情中...</div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', gap: 4, borderBottom: '1px solid var(--border-subtle)', marginBottom: 14 }}>
                {([['overview', '概览'], ['members', '成员与权限'], ['documents', '项目文档'], ['files', '项目文件']] as const).map(([key, label]) => (
                  <button key={key} onClick={() => setWorkspace(key)} style={{ border: 'none', borderBottom: workspace === key ? '2px solid var(--accent-primary)' : '2px solid transparent', background: 'transparent', color: workspace === key ? 'var(--accent-primary)' : 'var(--text-secondary)', padding: '7px 10px', fontSize: 12, cursor: 'pointer', fontWeight: workspace === key ? 700 : 400 }}>{label}</button>
                ))}
              </div>

              {assetError && <div style={{ marginBottom: 12, padding: 8, borderRadius: 6, background: '#f8514911', color: '#f85149', fontSize: 12 }}>{assetError}</div>}

              {workspace === 'members' && (
                <section style={{ marginBottom: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}><strong style={{ fontSize: 13 }}>项目成员与权限</strong><span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>权限在项目内配置</span></div>
                  <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 6, overflow: 'hidden' }}>
                    {members.map(member => <div key={member.user_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '9px 12px', borderBottom: '1px solid var(--border-subtle)', fontSize: 12 }}><span>{member.user_id}</span><span style={pillStyle('var(--surface-secondary)', 'var(--text-secondary)')}>{member.role_code}</span></div>)}
                    {members.length === 0 && <div style={{ padding: 14, color: 'var(--text-secondary)', fontSize: 12 }}>暂无项目成员</div>}
                  </div>
                </section>
              )}

              {workspace === 'documents' && (
                <section style={{ marginBottom: 14 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}><strong style={{ fontSize: 13 }}>受控项目文档</strong><label className="btn btn--primary btn--sm" style={{ fontSize: 11, cursor: assetBusy ? 'wait' : 'pointer' }}>上传文档<input type="file" hidden disabled={assetBusy} onChange={e => void handleDocumentUpload(e)} /></label></div>
                  <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 6, overflow: 'hidden' }}>
                    {documents.map(doc => <div key={doc.document_id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', borderBottom: '1px solid var(--border-subtle)', fontSize: 12 }}><span style={{ flex: 1, fontWeight: 600 }}>{doc.name}</span><span>{doc.phase_code}</span><span>v{doc.current_version}</span><span style={pillStyle(doc.status === 'APPROVED' ? '#3fb95022' : '#d2992222', doc.status === 'APPROVED' ? '#3fb950' : '#d29922')}>{doc.status}</span><button className="btn btn--ghost btn--sm" onClick={() => void api.getProjectDocumentDownload(selectedId, doc.document_id, doc.current_version).then(res => window.open(res.data?.download_url, '_blank'))}>下载</button></div>)}
                    {documents.length === 0 && <div style={{ padding: 14, color: 'var(--text-secondary)', fontSize: 12 }}>暂无项目文档</div>}
                  </div>
                </section>
              )}

              {workspace === 'files' && (
                <section style={{ marginBottom: 14 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}><strong style={{ fontSize: 13 }}>项目文件库</strong><div style={{ display: 'flex', gap: 6 }}><button className="btn btn--secondary btn--sm" onClick={() => void handleCreateFolder()} disabled={assetBusy}>新建文件夹</button><label className="btn btn--primary btn--sm" style={{ fontSize: 11, cursor: assetBusy ? 'wait' : 'pointer' }}>上传文件<input type="file" hidden disabled={assetBusy} onChange={e => void handleFileUpload(e)} /></label></div></div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>{folders.map(folder => <span key={folder.folder_id} style={{ padding: '4px 8px', border: '1px solid var(--border-subtle)', borderRadius: 4, fontSize: 11 }}>文件夹 / {folder.name}</span>)}</div>
                  <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 6, overflow: 'hidden' }}>{files.map(file => <div key={file.project_file_id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', borderBottom: '1px solid var(--border-subtle)', fontSize: 12 }}><span style={{ flex: 1 }}>{file.name}</span><button className="btn btn--ghost btn--sm" onClick={() => void api.getProjectFileDownload(selectedId, file.project_file_id).then(res => window.open(res.data?.download_url, '_blank'))}>下载</button></div>)}{files.length === 0 && <div style={{ padding: 14, color: 'var(--text-secondary)', fontSize: 12 }}>暂无项目文件</div>}</div>
                </section>
              )}

              {/* ── 项目进度 + 关联资源 ── */}
              {workspace === 'overview' && stats && (
                <div style={{ marginBottom: 14, padding: 14, background: 'var(--surface-primary)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>项目进度</div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {[
                        { label: '需求', count: stats.requirement_count, color: '#58a6ff', onClick: () => navigate('requirements') },
                        { label: '手工用例', count: stats.test_case_count, color: '#3fb950', onClick: () => navigate('testCases') },
                        { label: '自动化', count: stats.auto_case_count, color: '#d29922', onClick: () => navigate('testCases') },
                      ].map((item, i) => (
                        <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 3, padding: '2px 7px', borderRadius: 4, fontSize: 11, fontWeight: 600, cursor: 'pointer', background: `${item.color}12`, color: item.color, border: `1px solid ${item.color}25` }}
                          onClick={item.onClick}>
                          {item.label} <span style={{ fontWeight: 700, fontSize: 12 }}>{item.count}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                    <MiniProgress label="执行任务" done={taskBreakdown?.done || 0} total={taskBreakdown?.total || 0} color="#3fb950" />
                    <MiniProgress label="手工通过率" done={stats.manual_pass.passed} total={stats.manual_pass.total} color="#58a6ff" />
                    <MiniProgress label="自动化通过率" done={stats.auto_pass.passed} total={stats.auto_pass.total} color="#d29922" />
                    <MiniProgress label="需求覆盖率" done={stats.test_case_count} total={stats.requirement_count} color="#a371f7" />
                  </div>
                </div>
              )}

              {/* ── 风险/阻塞项 ── */}
              {workspace === 'overview' && blockers.length > 0 && (
                <div style={{ marginBottom: 14, padding: 10, background: 'color-mix(in srgb, var(--status-error) 6%, transparent)', borderRadius: 6, border: '1px solid color-mix(in srgb, var(--status-error) 13%, transparent)' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ color: 'var(--status-error)' }}>⚠</span>
                    <span style={{ color: 'var(--text-primary)' }}>风险/阻塞项</span>
                    <span style={{ fontSize: 10, fontWeight: 400, color: 'var(--text-tertiary)' }}>{blockers.length} 项需关注</span>
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {blockers.map(b => {
                      const statusColor = b.source === 'plan_item' && b.status === 'fail' ? 'var(--status-error)' : 'var(--status-warning)'
                      const prioLabel = b.priority ? ` (${b.priority})` : ''
                      return (
                        <span key={b.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '3px 9px', borderRadius: 5, background: 'color-mix(in srgb, var(--status-error) 6%, transparent)', border: '1px solid color-mix(in srgb, var(--status-error) 15%, transparent)', fontSize: 11 }}>
                          <span style={{ width: 6, height: 6, borderRadius: '50%', background: statusColor, flexShrink: 0 }} />
                          <span style={{ fontWeight: 500, color: 'var(--text-primary)', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{b.title || b.id}</span>
                          <span style={{ color: statusColor, fontSize: 10 }}>{b.status}{prioLabel}</span>
                        </span>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* ── 统计数据 ── */}
              {workspace === 'overview' && stats && (
                <div style={{ marginBottom: 14 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>统计数据</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                    <div style={s.statCard}>
                      <div style={s.statValue}>{stats.test_case_count}</div>
                      <div style={s.statLabel}>手工用例</div>
                    </div>
                    <div style={s.statCard}>
                      <div style={s.statValue}>{stats.auto_case_count}</div>
                      <div style={s.statLabel}>自动化用例</div>
                    </div>
                    <div style={s.statCard}>
                      <div style={s.statValue}>{stats.requirement_count}</div>
                      <div style={s.statLabel}>测试需求</div>
                    </div>
                    <div style={s.statCard}>
                      <div style={s.statValue}>{stats.plan_count}</div>
                      <div style={s.statLabel}>执行计划</div>
                    </div>
                  </div>
                </div>
              )}

              {/* ── 通过率 ── */}
              {workspace === 'overview' && stats && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 14 }}>
                  <PassCard label="手工通过率" stats={stats.manual_pass} color="#58a6ff" />
                  <PassCard label="自动化通过率" stats={stats.auto_pass} color="#d29922" />
                  <div style={{ ...s.statCard, textAlign: 'left' }}>
                    <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginBottom: 2 }}>需求覆盖率</div>
                    <div style={{ fontSize: 16, fontWeight: 700 }}>{pctStr(stats.coverage_rate)}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>{stats.test_case_count}用例/{stats.requirement_count}需求</div>
                    <div style={s.progressBar}><div style={progressFillStyle(stats.coverage_rate, '#a371f7')} /></div>
                  </div>
                </div>
              )}

              {/* ── 任务细分 ── */}
              {workspace === 'overview' && taskBreakdown && (
                <div style={{ marginBottom: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>任务细分</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, marginBottom: 14 }}>
                    <div style={s.statCard}><div style={s.statValue}>{taskBreakdown.total}</div><div style={s.statLabel}>任务总数</div></div>
                    <div style={s.statCard}><div style={{ ...s.statValue, color: '#3fb950' }}>{taskBreakdown.done}</div><div style={s.statLabel}>已完成</div></div>
                    <div style={s.statCard}><div style={{ ...s.statValue, color: '#d29922' }}>{taskBreakdown.running}</div><div style={s.statLabel}>运行中</div></div>
                    <div style={s.statCard}><div style={{ ...s.statValue, color: '#f85149' }}>{taskBreakdown.failed}</div><div style={s.statLabel}>失败</div></div>
                    <div style={s.statCard}><div style={{ ...s.statValue, color: '#8b949e' }}>{taskBreakdown.pending}</div><div style={s.statLabel}>待执行</div></div>
                  </div>
                </div>
              )}

              {/* ── 执行人分布 + 最近动态 ── */}
              {workspace === 'overview' && ((assignees && assignees.length > 0) || activities.length > 0) ? (
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 3fr', gap: 12, marginBottom: 14 }}>
                  {/* 左侧：执行人分布 */}
                  {assignees && assignees.length > 0 && (
                    <div style={{ background: 'var(--surface-primary)', borderRadius: 6, border: '1px solid var(--border-subtle)', padding: '10px 12px', overflow: 'hidden' }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>执行人分布</div>
                      <div style={{ maxHeight: 200, overflowY: 'auto', paddingRight: 4 }}>
                        {assignees.map((a, i) => (
                          <div key={a.assignee_id || i} style={{ marginBottom: 5, fontSize: 11 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                              <span style={{ fontWeight: 500, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.assignee_name || a.assignee_id || '未分配'}</span>
                              <span style={{ color: 'var(--text-tertiary)', flexShrink: 0 }}>{a.done_count}/{a.item_count}</span>
                            </div>
                            <div style={s.progressBar}><div style={progressFillStyle(a.progress, '#58a6ff')} /></div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {/* 右侧：最近动态 */}
                  {activities.length > 0 && (
                    <div style={{ background: 'var(--surface-primary)', borderRadius: 6, border: '1px solid var(--border-subtle)', padding: '10px 12px', overflow: 'hidden' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>最近动态</span>
                        <span style={{ fontSize: 10, fontWeight: 700, color: '#fff', background: 'var(--accent-primary)', padding: '1px 6px', borderRadius: 4, minWidth: 18, textAlign: 'center' }}>{activities.length}</span>
                      </div>
                      <div style={{ maxHeight: 200, overflowY: 'auto', paddingRight: 4 }}>
                        {activities.map((a, i) => (
                          <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, padding: '4px 0', borderBottom: i < activities.length - 1 ? '1px solid var(--border-subtle)' : 'none' }}>
                            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#58a6ff', flexShrink: 0 }} />
                            <span style={{ fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', fontSize: 11 }}>{a.username || a.user_id}</span>
                            <span style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap', fontSize: 11 }}>{a.action}</span>
                            <span style={{ color: 'var(--accent-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, fontWeight: 500, fontSize: 11 }}>「{a.target}」</span>
                            <span style={{ color: 'var(--text-tertiary)', fontSize: 10, flexShrink: 0, fontWeight: 500 }}>{fmtDateTime(a.time)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          ) : (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontSize: 14 }}>
              选择一个项目查看详情
            </div>
          )}
        </main>
      </div>

      {/* create/edit modal */}
      {showModal && (
        <div style={s.modalOverlay} onClick={() => setShowModal(false)}>
          <div style={{ ...s.modal, width: 540 }} onClick={e => e.stopPropagation()}>
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
              <button className="btn btn--primary btn--sm" onClick={() => void handleSave()} disabled={saving} style={{ fontSize: 12, padding: '6px 14px' }}>{saving ? '保存中...' : '保存'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const labelStyle: React.CSSProperties = { display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 3 }
const inputStyle: React.CSSProperties = { width: '100%', fontSize: 13, padding: '6px 10px' }
