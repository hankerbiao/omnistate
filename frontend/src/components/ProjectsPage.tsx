// ═══════════════════════════════════════════════════════════════════════
//  ProjectsPage — 项目管理页面
//   分栏布局：左侧项目列表 + 右侧项目详情（含统计面板）
//   遵循现有测试资产模块的设计风格
// ═══════════════════════════════════════════════════════════════════════

import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'
import type {
  Project,
  ProjectDetail,
} from '../types'

// ── 样式 ─────────────────────────────────────────────────────────────

const styles = {
  wrapper: {
    height: '100%',
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  },
  toolbar: {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '10px 24px', borderBottom: '1px solid var(--border-subtle)',
    background: 'var(--surface-primary)', flexShrink: 0,
  },
  workspace: {
    flex: 1, display: 'flex', overflow: 'hidden',
  },
  sidePanel: {
    width: 320, borderRight: '1px solid var(--border-subtle)',
    display: 'flex', flexDirection: 'column' as const, overflow: 'hidden',
    flexShrink: 0,
  },
  mainPanel: {
    flex: 1, display: 'flex', flexDirection: 'column' as const, overflow: 'hidden',
  },
  scroll: {
    flex: 1, overflowY: 'auto' as const, padding: '12px 0',
  },
  listItem: (isActive: boolean) => ({
    padding: '10px 16px', cursor: 'pointer', borderLeft: isActive ? '3px solid var(--accent-primary)' : '3px solid transparent',
    background: isActive ? 'var(--surface-secondary)' : 'transparent',
    transition: 'background 0.15s',
  }),
  detailScroll: {
    flex: 1, overflowY: 'auto' as const, padding: '24px',
  },
  statCard: {
    background: 'var(--surface-secondary)', borderRadius: 8, padding: '16px',
    textAlign: 'center' as const, flex: 1,
  },
  statValue: {
    fontSize: 24, fontWeight: 700, color: 'var(--accent-primary)',
  },
  statLabel: {
    fontSize: 12, color: 'var(--text-secondary)', marginTop: 4,
  },
  modalOverlay: {
    position: 'fixed' as const, inset: 0, background: 'rgba(0,0,0,0.5)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 1000,
  },
  modal: {
    background: 'var(--surface-primary)', borderRadius: 12,
    width: 500, maxWidth: '90vw', maxHeight: '80vh', overflowY: 'auto' as const,
    padding: 24, boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
  },
}

// ── 主组件 ───────────────────────────────────────────────────────────

export default function ProjectsPage() {
  // ── state ──
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string>('');
  const [projectDetail, setProjectDetail] = useState<ProjectDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // ── Modal ──
  const [showModal, setShowModal] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [formName, setFormName] = useState('');
  const [formKey, setFormKey] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  // ── 数据加载 ──
  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number | undefined> = {};
      if (statusFilter) params.status = statusFilter;
      if (searchQuery) params.name = searchQuery;
      const res = await api.listProjects(params);
      const list = res.data || { items: [], total: 0 };
      setProjects(list.items || []);
    } catch {
      setError('获取项目列表失败');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchQuery]);

  useEffect(() => { void fetchProjects(); }, [fetchProjects]);

  // ── 详情加载 ──
  useEffect(() => {
    if (!selectedId) { setProjectDetail(null); return; }
    setDetailLoading(true);
    api.getProject(selectedId)
      .then(res => setProjectDetail(res.data || null))
      .catch(() => setProjectDetail(null))
      .finally(() => setDetailLoading(false));
  }, [selectedId]);

  const selectedProject = projects.find(p => p.project_id === selectedId) || null;

  // ── 搜索/过滤 ──
  const filteredProjects = useMemo(() => {
    let list = projects;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      list = list.filter(p => p.name.toLowerCase().includes(q) || p.key.toLowerCase().includes(q));
    }
    if (statusFilter) {
      list = list.filter(p => p.status === statusFilter);
    }
    return list;
  }, [projects, searchQuery, statusFilter]);

  // ── 创建 & 编辑 ──
  const openCreateModal = () => {
    setEditMode(false);
    setFormName('');
    setFormKey('');
    setFormDesc('');
    setFormError('');
    setShowModal(true);
  };

  const openEditModal = () => {
    if (!selectedProject) return;
    setEditMode(true);
    setFormName(selectedProject.name);
    setFormKey(selectedProject.key);
    setFormDesc(selectedProject.description || '');
    setFormError('');
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!formName.trim()) { setFormError('项目名称不能为空'); return; }
    if (!editMode && !formKey.trim()) { setFormError('项目标识不能为空'); return; }
    setSaving(true);
    setFormError('');
    try {
      if (editMode && selectedId) {
        await api.updateProject(selectedId, {
          name: formName.trim(),
          key: formKey.trim() || undefined,
          description: formDesc.trim() || null,
        });
      } else {
        await api.createProject({
          name: formName.trim(),
          key: formKey.trim(),
          description: formDesc.trim() || null,
        });
      }
      setShowModal(false);
      await fetchProjects();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedId || !confirm(`确定删除项目「${selectedProject?.name}」？删除后关联数据将被清理。`)) return;
    try {
      await api.deleteProject(selectedId);
      setSelectedId('');
      await fetchProjects();
    } catch {
      setError('删除失败');
    }
  };

  // ── 归档/激活 ──
  const handleToggleStatus = async () => {
    if (!selectedId || !selectedProject) return;
    const newStatus = selectedProject.status === 'active' ? 'archived' : 'active';
    try {
      await api.updateProject(selectedId, { status: newStatus });
      await fetchProjects();
      setProjectDetail(prev => prev ? { ...prev, status: newStatus } : prev);
    } catch {
      setError('状态更新失败');
    }
  };

  // ── 渲染 ──
  const statusMeta: Record<string, { label: string; color: string }> = {
    active: { label: '活跃', color: '#3fb950' },
    archived: { label: '已归档', color: '#8b949e' },
  };

  return (
    <div style={styles.wrapper}>
      {/* ── Toolbar ── */}
      <div style={styles.toolbar}>
        <input
          className="form-input"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="搜索项目名称或标识..."
          style={{ width: 200, fontSize: 13, padding: '5px 10px' }}
        />
        <div style={{ display: 'flex', gap: 4 }}>
          {[
            { key: '', label: '全部' },
            { key: 'active', label: '活跃' },
            { key: 'archived', label: '已归档' },
          ].map(f => (
            <button key={f.key} onClick={() => setStatusFilter(f.key)}
              style={{
                padding: '3px 10px', fontSize: 12, border: 'none', borderRadius: 6, cursor: 'pointer',
                background: statusFilter === f.key ? 'var(--accent-primary)' : 'var(--surface-secondary)',
                color: statusFilter === f.key ? '#fff' : 'var(--text-secondary)',
                fontWeight: statusFilter === f.key ? 600 : 400,
              }}>
              {f.label}
            </button>
          ))}
        </div>
        <div style={{ flex: 1 }} />
        <button className="btn btn--primary btn--sm" onClick={openCreateModal}
          style={{ padding: '6px 16px', fontSize: 13 }}>
          + 新建项目
        </button>
      </div>

      {/* ── Workspace ── */}
      <div style={styles.workspace}>
        {/* 左侧列表 */}
        <aside style={styles.sidePanel}>
          <div style={styles.scroll}>
            {loading && <div style={{ padding: 16, fontSize: 13, color: 'var(--text-secondary)' }}>加载中...</div>}
            {error && <div style={{ padding: 16, fontSize: 13, color: '#f85149' }}>{error}</div>}
            {!loading && !error && filteredProjects.length === 0 && (
              <div style={{ padding: 16, fontSize: 13, color: 'var(--text-secondary)' }}>
                {searchQuery || statusFilter ? '无匹配项目' : '暂无项目，点击上方按钮创建'}
              </div>
            )}
            {filteredProjects.map(p => {
              const meta = statusMeta[p.status] || { label: p.status, color: '#8b949e' };
              const isActive = p.project_id === selectedId;
              return (
                <div key={p.project_id} onClick={() => setSelectedId(p.project_id)}
                  style={styles.listItem(isActive)}
                  onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'var(--surface-secondary)' }}
                  onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent' }}>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>{p.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', gap: 8 }}>
                    <span>{p.key}</span>
                    <span style={{ color: meta.color }}>{meta.label}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </aside>

        {/* 右侧详情 */}
        <main style={styles.mainPanel}>
          {selectedProject ? (
            <div style={styles.detailScroll}>
              {/* 头部操作 */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <button className="btn btn--ghost btn--sm" onClick={() => setSelectedId('')}
                    style={{ fontSize: 12 }}>← 返回列表</button>
                  <span style={{ fontSize: 18, fontWeight: 700 }}>{selectedProject.name}</span>
                  <span style={{
                    fontSize: 11, padding: '2px 8px', borderRadius: 10,
                    background: selectedProject.status === 'active' ? '#3fb95022' : '#8b949e22',
                    color: selectedProject.status === 'active' ? '#3fb950' : '#8b949e',
                  }}>{statusMeta[selectedProject.status]?.label || selectedProject.status}</span>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button className="btn btn--ghost btn--sm" onClick={handleToggleStatus}
                    style={{ fontSize: 12 }}>
                    {selectedProject.status === 'active' ? '归档' : '激活'}
                  </button>
                  <button className="btn btn--secondary btn--sm" onClick={openEditModal}
                    style={{ fontSize: 12 }}>编辑</button>
                  <button className="btn btn--danger btn--sm" onClick={handleDelete}
                    style={{ fontSize: 12 }}>删除</button>
                </div>
              </div>

              {/* 基本信息 */}
              <div style={{ marginBottom: 24, padding: 16, background: 'var(--surface-secondary)', borderRadius: 8 }}>
                <div style={{ fontSize: 13, marginBottom: 4 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>标识：</span>
                  <span style={{ fontWeight: 600 }}>{selectedProject.key}</span>
                </div>
                {selectedProject.description && (
                  <div style={{ fontSize: 13, marginBottom: 4 }}>
                    <span style={{ color: 'var(--text-secondary)' }}>描述：</span>
                    <span>{selectedProject.description}</span>
                  </div>
                )}
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8 }}>
                  创建者：{selectedProject.created_by || '-'} | 
                  创建时间：{selectedProject.created_at ? new Date(selectedProject.created_at).toLocaleString() : '-'}
                </div>
              </div>

              {/* 统计面板 */}
              {projectDetail?.stats ? (
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>统计概览</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                    <StatCard value={projectDetail.stats.test_case_count} label="手工用例" />
                    <StatCard value={projectDetail.stats.auto_case_count} label="自动化用例" />
                    <StatCard value={projectDetail.stats.requirement_count} label="测试需求" />
                    <StatCard value={projectDetail.stats.plan_count} label="执行计划" />
                    <StatCard value={projectDetail.stats.task_count} label="执行任务" />
                    <StatCard value={`${projectDetail.stats.task_done_count}/${projectDetail.stats.task_count}`} label="已完成/总数" />
                    <StatCard value={`${projectDetail.stats.task_progress}%`} label="任务完成率" />
                    <StatCard value={projectDetail.stats.collection_count} label="预制用例集" />
                  </div>
                </div>
              ) : detailLoading ? (
                <div style={{ padding: 16, fontSize: 13, color: 'var(--text-secondary)' }}>加载统计数据...</div>
              ) : null}
            </div>
          ) : (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontSize: 14 }}>
              选择一个项目查看详情
            </div>
          )}
        </main>
      </div>

      {/* ── Create/Edit Modal ── */}
      {showModal && (
        <div style={styles.modalOverlay} onClick={() => setShowModal(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>
              {editMode ? '编辑项目' : '新建项目'}
            </div>
            {formError && (
              <div style={{ fontSize: 12, color: '#f85149', marginBottom: 12, padding: 8, background: '#f8514911', borderRadius: 6 }}>
                {formError}
              </div>
            )}
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>名称 *</label>
              <input className="form-input" value={formName} onChange={e => setFormName(e.target.value)}
                placeholder="项目名称" style={{ width: '100%', fontSize: 13, padding: '6px 10px' }} />
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>标识 {editMode ? '' : '*'}</label>
              <input className="form-input" value={formKey} onChange={e => {
                const raw = e.target.value;
                const transformed = raw.toUpperCase().replace(/[^A-Z0-9_-]/g, '');
                setFormKey(transformed);
              }}
                placeholder="PROJ-KEY" disabled={editMode}
                style={{ width: '100%', fontSize: 13, padding: '6px 10px' }} />
              {!editMode && <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>仅支持大写字母、数字、下划线和连字符</div>}
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>描述</label>
              <textarea className="form-input" value={formDesc} onChange={e => setFormDesc(e.target.value)}
                placeholder="项目描述（可选）" rows={3}
                style={{ width: '100%', fontSize: 13, padding: '6px 10px', resize: 'vertical' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button className="btn btn--ghost btn--sm" onClick={() => setShowModal(false)}
                style={{ fontSize: 12, padding: '6px 14px' }}>取消</button>
              <button className="btn btn--primary btn--sm" onClick={handleSave} disabled={saving}
                style={{ fontSize: 12, padding: '6px 14px' }}>
                {saving ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── 统计卡片 ─────────────────────────────────────────────────────────

function StatCard({ value, label, suffix }: { value: string | number; label: string; suffix?: string }) {
  return (
    <div style={styles.statCard}>
      <div style={styles.statValue}>
        {typeof value === 'number' ? value.toLocaleString() : value}
        {suffix && <span style={{ fontSize: 14, color: 'var(--text-secondary)' }}>{suffix}</span>}
      </div>
      <div style={styles.statLabel}>{label}</div>
    </div>
  );
}
