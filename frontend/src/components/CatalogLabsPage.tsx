import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import { getCatalogLabs, invalidateCatalogLabsCache } from '../services/catalogLabsCache';
import type { CatalogLab, CreateCatalogLabRequest } from '../types';
import { catalogStyles } from './catalog/catalogStyles';

const emptyForm: CreateCatalogLabRequest = { code: '', name: '', description: '', sort_order: 0 };

type StatusFilter = 'all' | 'active' | 'inactive';
type ViewMode = 'grid' | 'list';

function suggestCode(name: string): string {
  return name
    .trim()
    .replace(/[\s-]+/g, '_')
    .replace(/[^a-zA-Z0-9_]/g, '')
    .toUpperCase()
    .slice(0, 32);
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days < 1) return '今天';
  if (days < 7) return `${days} 天前`;
  if (days < 30) return `${Math.floor(days / 7)} 周前`;
  return new Date(iso).toLocaleDateString('zh-CN');
}

/* ── Icons (inline SVG, consistent with app) ── */

const IconSearch = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

const IconSparkles = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z" />
    <path d="M19 13l1 3 3 1-3 1-1 3-1-3-3-1 3-1 1-3z" />
  </svg>
);

const IconPlus = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

const IconRefresh = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" />
    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
  </svg>
);

const IconGrid = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
    <rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
  </svg>
);

const IconList = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" /><line x1="8" y1="18" x2="21" y2="18" />
    <line x1="3" y1="6" x2="3.01" y2="6" /><line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" />
  </svg>
);

const IconLab = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 2v7.31" /><path d="M14 2v7.31" /><path d="M8.5 2h7" />
    <path d="M14 9.3a6.5 6.5 0 1 1-4 0" /><path d="M5.52 16h12.96" />
  </svg>
);

const IconClose = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

/* ── Sub-components ── */

function StatCard({ label, value, sub, accent }: { label: string; value: string | number; sub?: string; accent: string }) {
  return (
    <div style={S.statCard}>
      <div style={{ ...S.statAccent, background: accent }} />
      <div style={S.statBody}>
        <div style={catalogStyles.labelCaps}>{label}</div>
        <div style={S.statValue}>{value}</div>
        {sub && <div style={S.statSub}>{sub}</div>}
      </div>
    </div>
  );
}

function LabCard({
  lab,
  maxCases,
  onEdit,
  onDeactivate,
  onDelete,
}: {
  lab: CatalogLab;
  maxCases: number;
  onEdit: () => void;
  onDeactivate: () => void;
  onDelete: () => void;
}) {
  const cases = lab.case_count ?? 0;
  const pct = maxCases > 0 ? Math.round((cases / maxCases) * 100) : 0;

  return (
    <article style={{ ...S.labCard, ...(lab.is_active ? {} : S.labCardInactive) }}>
      <div style={S.labCardHeader}>
        <div style={S.labIconWrap}>
          <IconLab />
        </div>
        <span style={{
          ...S.statusPill,
          ...(lab.is_active ? S.statusActive : S.statusInactive),
        }}>
          {lab.is_active ? '启用' : '停用'}
        </span>
      </div>

      <div style={S.labCode}>{lab.code}</div>
      <h3 style={S.labName}>{lab.name}</h3>
      {lab.description && <p style={S.labDesc}>{lab.description}</p>}

      <div style={S.labMetrics}>
        <div style={S.metricRow}>
          <span style={S.metricLabel}>用例数</span>
          <span style={S.metricValue}>{cases}</span>
        </div>
        <div style={S.progressTrack}>
          <div style={{ ...S.progressFill, width: `${pct}%` }} />
        </div>
        <div style={S.metricRow}>
          <span style={S.metricLabel}>排序</span>
          <span style={S.metricValueMono}>{lab.sort_order}</span>
        </div>
      </div>

      <div style={S.labFooter}>
        <span style={S.updatedAt}>更新 {formatRelativeTime(lab.updated_at)}</span>
        <div style={S.labActions}>
          <button type="button" style={S.actionBtn} onClick={onEdit}>编辑</button>
          {lab.is_active && (
            <button type="button" style={{ ...S.actionBtn, ...S.actionWarn }} onClick={onDeactivate}>停用</button>
          )}
          <button type="button" style={{ ...S.actionBtn, ...S.actionDanger }} onClick={onDelete}>删除</button>
        </div>
      </div>
    </article>
  );
}

function ModalShell({ title, subtitle, onClose, children }: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div style={S.overlay} onClick={onClose} role="presentation">
      <div style={S.modal} onClick={e => e.stopPropagation()} role="dialog" aria-modal="true">
        <div style={S.modalHeader}>
          <div>
            <h3 style={S.modalTitle}>{title}</h3>
            {subtitle && <p style={S.modalSubtitle}>{subtitle}</p>}
          </div>
          <button type="button" style={S.modalClose} onClick={onClose} aria-label="关闭">
            <IconClose />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function FieldLabel({ children, hint }: { children: React.ReactNode; hint?: string }) {
  return (
    <label style={S.fieldLabel}>
      <span>{children}</span>
      {hint && <span style={S.fieldHint}>{hint}</span>}
    </label>
  );
}

/* ── Main Page ── */

const CatalogLabsPage: React.FC = () => {
  const [labs, setLabs] = useState<CatalogLab[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [codeTouched, setCodeTouched] = useState(false);
  const [editLab, setEditLab] = useState<CatalogLab | null>(null);
  const [deactivateLab, setDeactivateLab] = useState<CatalogLab | null>(null);
  const [targetLabId, setTargetLabId] = useState('');
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');

  const fetchLabs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await getCatalogLabs();
      setLabs(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载 Lab 失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLabs();
  }, [fetchLabs]);

  const activeLabs = useMemo(() => labs.filter(l => l.is_active), [labs]);

  const filteredLabs = useMemo(() => {
    const q = search.trim().toLowerCase();
    return labs
      .filter(l => {
        if (statusFilter === 'active' && !l.is_active) return false;
        if (statusFilter === 'inactive' && l.is_active) return false;
        if (!q) return true;
        return l.code.toLowerCase().includes(q) || l.name.toLowerCase().includes(q);
      })
      .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name));
  }, [labs, search, statusFilter]);

  const stats = useMemo(() => {
    const totalCases = labs.reduce((s, l) => s + (l.case_count ?? 0), 0);
    return {
      total: labs.length,
      active: activeLabs.length,
      inactive: labs.length - activeLabs.length,
      totalCases,
    };
  }, [labs, activeLabs]);

  const maxCases = useMemo(
    () => Math.max(1, ...labs.map(l => l.case_count ?? 0)),
    [labs],
  );

  const suggestedCode = useMemo(() => suggestCode(form.name), [form.name]);

  const handleCreate = async () => {
    setSaving(true);
    try {
      await api.createCatalogLab({
        ...form,
        code: form.code || suggestedCode,
      });
      setCreateOpen(false);
      setForm(emptyForm);
      setCodeTouched(false);
      invalidateCatalogLabsCache();
      await fetchLabs();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!editLab) return;
    setSaving(true);
    try {
      await api.updateCatalogLab(editLab.lab_id, {
        name: editLab.name,
        description: editLab.description || undefined,
        sort_order: editLab.sort_order,
      });
      setEditLab(null);
      invalidateCatalogLabsCache();
      await fetchLabs();
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新失败');
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async () => {
    if (!deactivateLab || !targetLabId) return;
    setSaving(true);
    try {
      await api.deactivateCatalogLab(deactivateLab.lab_id, targetLabId);
      setDeactivateLab(null);
      setTargetLabId('');
      invalidateCatalogLabsCache();
      await fetchLabs();
    } catch (err) {
      setError(err instanceof Error ? err.message : '停用失败');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (lab: CatalogLab) => {
    if (!window.confirm(`确定删除 Lab「${lab.name}」？仅当无下属用例时可删。`)) return;
    try {
      await api.deleteCatalogLab(lab.lab_id);
      invalidateCatalogLabsCache();
      await fetchLabs();
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  };

  const openCreate = () => {
    setForm(emptyForm);
    setCodeTouched(false);
    setCreateOpen(true);
  };

  return (
    <div style={S.page}>
      {/* Hero */}
      <header style={S.hero}>
        <div style={S.heroGlow} />
        <div style={S.heroContent}>
          <div style={S.heroBadge}>
            <IconSparkles />
            <span>Catalog Intelligence</span>
          </div>
          <p style={S.heroDesc}>
            Lab 是测试用例目录的顶层命名空间。在此管理 Lab 生命周期、用例分布与目录健康度。
          </p>
        </div>
      </header>

      {/* Stats */}
      <div style={S.statsRow}>
        <StatCard label="Lab 总数" value={stats.total} accent="linear-gradient(135deg, #6366f1, #8b5cf6)" />
        <StatCard label="启用中" value={stats.active} sub={`${stats.inactive} 已停用`} accent="linear-gradient(135deg, #2563eb, #06b6d4)" />
        <StatCard label="用例总量" value={stats.totalCases} sub="跨全部 Lab" accent="linear-gradient(135deg, #10b981, #34d399)" />
      </div>

      {error && (
        <div style={S.errorBanner}>
          <span>{error}</span>
          <button type="button" style={S.errorDismiss} onClick={() => setError(null)}>×</button>
        </div>
      )}

      <section>
          {/* Toolbar */}
          <div style={S.toolbar}>
            <div style={S.searchWrap}>
              <span style={S.searchIcon}><IconSearch /></span>
              <input
                type="search"
                placeholder="搜索 Code 或名称…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={S.searchInput}
              />
            </div>

            <div style={S.filterGroup}>
              {(['all', 'active', 'inactive'] as const).map(key => (
                <button
                  key={key}
                  type="button"
                  style={{ ...S.filterBtn, ...(statusFilter === key ? S.filterBtnActive : {}) }}
                  onClick={() => setStatusFilter(key)}
                >
                  {key === 'all' ? '全部' : key === 'active' ? '启用' : '停用'}
                </button>
              ))}
            </div>

            <div style={S.toolbarRight}>
              <div style={S.viewToggle}>
                <button
                  type="button"
                  style={{ ...S.viewBtn, ...(viewMode === 'grid' ? S.viewBtnActive : {}) }}
                  onClick={() => setViewMode('grid')}
                  title="卡片视图"
                >
                  <IconGrid />
                </button>
                <button
                  type="button"
                  style={{ ...S.viewBtn, ...(viewMode === 'list' ? S.viewBtnActive : {}) }}
                  onClick={() => setViewMode('list')}
                  title="列表视图"
                >
                  <IconList />
                </button>
              </div>
              <button type="button" style={S.refreshBtn} onClick={fetchLabs} disabled={loading} title="刷新">
                <IconRefresh />
              </button>
              <button type="button" style={S.primaryBtn} onClick={openCreate}>
                <IconPlus />
                <span>新建 Lab</span>
              </button>
            </div>
          </div>

          {/* Content */}
          {loading ? (
            <div style={S.loadingBox}>
              <div style={S.spinner} />
              <span style={S.loadingText}>加载目录数据…</span>
            </div>
          ) : filteredLabs.length === 0 ? (
            <div style={S.emptyState}>
              <div style={S.emptyIcon}><IconLab /></div>
              <h3 style={S.emptyTitle}>
                {search || statusFilter !== 'all' ? '没有匹配的 Lab' : '还没有 Lab'}
              </h3>
              <p style={S.emptyDesc}>
                {search || statusFilter !== 'all'
                  ? '尝试调整搜索或筛选条件'
                  : '创建第一个 Lab，开始组织测试用例目录'}
              </p>
              {!search && statusFilter === 'all' && (
                <button type="button" style={S.primaryBtn} onClick={openCreate}>
                  <IconPlus /><span>创建 Lab</span>
                </button>
              )}
            </div>
          ) : viewMode === 'grid' ? (
            <div style={S.grid}>
              {filteredLabs.map(lab => (
                <LabCard
                  key={lab.lab_id}
                  lab={lab}
                  maxCases={maxCases}
                  onEdit={() => setEditLab({ ...lab })}
                  onDeactivate={() => setDeactivateLab(lab)}
                  onDelete={() => handleDelete(lab)}
                />
              ))}
            </div>
          ) : (
            <div style={{ ...catalogStyles.card, overflow: 'hidden' }}>
              <table style={S.table}>
                <thead>
                  <tr>
                    <th style={S.th}>Lab</th>
                    <th style={S.th}>Code</th>
                    <th style={S.th}>排序</th>
                    <th style={S.th}>状态</th>
                    <th style={S.th}>用例</th>
                    <th style={{ ...S.th, textAlign: 'right' }}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLabs.map(lab => (
                    <tr key={lab.lab_id} style={S.tr}>
                      <td style={S.td}>
                        <div style={S.listName}>{lab.name}</div>
                        {lab.description && <div style={S.listDesc}>{lab.description}</div>}
                      </td>
                      <td style={S.td}><code style={S.codeTag}>{lab.code}</code></td>
                      <td style={S.td}><span style={S.metricValueMono}>{lab.sort_order}</span></td>
                      <td style={S.td}>
                        <span style={{ ...S.statusPill, ...(lab.is_active ? S.statusActive : S.statusInactive) }}>
                          {lab.is_active ? '启用' : '停用'}
                        </span>
                      </td>
                      <td style={S.td}><span style={S.metricValueMono}>{lab.case_count ?? 0}</span></td>
                      <td style={{ ...S.td, textAlign: 'right' }}>
                        <div style={S.listActions}>
                          <button type="button" style={S.actionBtn} onClick={() => setEditLab({ ...lab })}>编辑</button>
                          {lab.is_active && (
                            <button type="button" style={{ ...S.actionBtn, ...S.actionWarn }} onClick={() => setDeactivateLab(lab)}>停用</button>
                          )}
                          <button type="button" style={{ ...S.actionBtn, ...S.actionDanger }} onClick={() => handleDelete(lab)}>删除</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

      {/* Create Modal */}
      {createOpen && (
        <ModalShell
          title="新建 Lab"
          subtitle="Lab Code 创建后不可修改，将作为目录路径前缀"
          onClose={() => setCreateOpen(false)}
        >
          <div style={S.formBody}>
            <div style={S.field}>
              <FieldLabel hint="必填">显示名称</FieldLabel>
              <input
                placeholder="例如：DDR5 验证实验室"
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                style={S.input}
                autoFocus
              />
            </div>
            <div style={S.field}>
              <FieldLabel hint="创建后不可改">Code</FieldLabel>
              <input
                placeholder={suggestedCode || 'LAB_CODE'}
                value={form.code}
                onChange={e => { setForm({ ...form, code: e.target.value.toUpperCase() }); setCodeTouched(true); }}
                style={S.inputMono}
              />
              {!codeTouched && suggestedCode && form.name && (
                <div style={S.suggestion}>
                  <IconSparkles />
                  <span>建议 Code：</span>
                  <button
                    type="button"
                    style={S.suggestionBtn}
                    onClick={() => setForm({ ...form, code: suggestedCode })}
                  >
                    {suggestedCode}
                  </button>
                </div>
              )}
            </div>
            <div style={S.field}>
              <FieldLabel hint="可选">描述</FieldLabel>
              <textarea
                placeholder="简要说明该 Lab 的用途…"
                value={form.description || ''}
                onChange={e => setForm({ ...form, description: e.target.value })}
                style={S.textarea}
                rows={2}
              />
            </div>
            <div style={S.field}>
              <FieldLabel hint="越小越靠前">排序权重</FieldLabel>
              <input
                type="number"
                value={form.sort_order ?? 0}
                onChange={e => setForm({ ...form, sort_order: Number(e.target.value) })}
                style={S.input}
              />
            </div>
          </div>
          <div style={S.modalActions}>
            <button type="button" style={S.secondaryBtn} onClick={() => setCreateOpen(false)}>取消</button>
            <button
              type="button"
              style={S.primaryBtn}
              disabled={saving || !form.name.trim()}
              onClick={handleCreate}
            >
              {saving ? '创建中…' : '创建 Lab'}
            </button>
          </div>
        </ModalShell>
      )}

      {/* Edit Modal */}
      {editLab && (
        <ModalShell title="编辑 Lab" subtitle={`Code: ${editLab.code}`} onClose={() => setEditLab(null)}>
          <div style={S.formBody}>
            <div style={S.field}>
              <FieldLabel>显示名称</FieldLabel>
              <input
                value={editLab.name}
                onChange={e => setEditLab({ ...editLab, name: e.target.value })}
                style={S.input}
              />
            </div>
            <div style={S.field}>
              <FieldLabel hint="可选">描述</FieldLabel>
              <textarea
                value={editLab.description || ''}
                onChange={e => setEditLab({ ...editLab, description: e.target.value })}
                style={S.textarea}
                rows={2}
              />
            </div>
            <div style={S.field}>
              <FieldLabel>排序权重</FieldLabel>
              <input
                type="number"
                value={editLab.sort_order}
                onChange={e => setEditLab({ ...editLab, sort_order: Number(e.target.value) })}
                style={S.input}
              />
            </div>
          </div>
          <div style={S.modalActions}>
            <button type="button" style={S.secondaryBtn} onClick={() => setEditLab(null)}>取消</button>
            <button type="button" style={S.primaryBtn} disabled={saving} onClick={handleUpdate}>
              {saving ? '保存中…' : '保存更改'}
            </button>
          </div>
        </ModalShell>
      )}

      {/* Deactivate Modal */}
      {deactivateLab && (
        <ModalShell
          title={`停用 Lab：${deactivateLab.name}`}
          subtitle="停用前需将下属用例迁移至目标 Lab，目录路径保持不变"
          onClose={() => { setDeactivateLab(null); setTargetLabId(''); }}
        >
          <div style={S.migrateNotice}>
            <span style={S.migrateCount}>{deactivateLab.case_count ?? 0}</span>
            <span>条用例待迁移</span>
          </div>
          <div style={S.field}>
            <FieldLabel>目标 Lab</FieldLabel>
            <select
              style={S.select}
              value={targetLabId}
              onChange={e => setTargetLabId(e.target.value)}
            >
              <option value="">选择接收用例的 Lab…</option>
              {activeLabs
                .filter(l => l.lab_id !== deactivateLab.lab_id)
                .map(l => (
                  <option key={l.lab_id} value={l.lab_id}>
                    {l.name} ({l.code}) · {l.case_count ?? 0} 用例
                  </option>
                ))}
            </select>
          </div>
          <div style={S.modalActions}>
            <button type="button" style={S.secondaryBtn} onClick={() => { setDeactivateLab(null); setTargetLabId(''); }}>
              取消
            </button>
            <button
              type="button"
              style={{ ...S.primaryBtn, ...S.deactivateBtn }}
              disabled={saving || !targetLabId}
              onClick={handleDeactivate}
            >
              {saving ? '处理中…' : '确认停用并迁移'}
            </button>
          </div>
        </ModalShell>
      )}
    </div>
  );
};

/* ── Styles ── */

const S: Record<string, React.CSSProperties> = {
  page: {
    padding: 'var(--space-6) var(--space-8)',
    maxWidth: 1440,
    margin: '0 auto',
    animation: 'fadeIn 0.35s ease',
  },
  hero: {
    position: 'relative',
    borderRadius: 'var(--radius-xl)',
    padding: 'var(--space-5) var(--space-6)',
    marginBottom: 'var(--space-6)',
    overflow: 'hidden',
    background: 'linear-gradient(135deg, #eef2ff 0%, #f5f3ff 45%, #ecfeff 100%)',
    border: '1px solid color-mix(in srgb, #6366f1 18%, var(--border-subtle))',
  },
  heroGlow: {
    position: 'absolute',
    top: -40,
    right: -20,
    width: 200,
    height: 200,
    borderRadius: '50%',
    background: 'radial-gradient(circle, rgba(99,102,241,0.25) 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  heroContent: { position: 'relative', zIndex: 1 },
  heroBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '4px 12px',
    marginBottom: 'var(--space-2)',
    fontSize: 12,
    fontWeight: 600,
    color: '#6366f1',
    backgroundColor: 'rgba(99,102,241,0.12)',
    borderRadius: 'var(--radius-full)',
    border: '1px solid rgba(99,102,241,0.2)',
  },
  heroDesc: {
    margin: 0,
    fontSize: 14,
    color: 'var(--text-secondary)',
    maxWidth: 560,
    lineHeight: 1.6,
  },
  statsRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 'var(--space-4)',
    marginBottom: 'var(--space-6)',
  },
  statCard: {
    ...catalogStyles.card,
    position: 'relative',
    display: 'flex',
    overflow: 'hidden',
    padding: 'var(--space-4) var(--space-5)',
  },
  statAccent: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    width: 4,
  },
  statBody: { paddingLeft: 'var(--space-2)' },
  statValue: {
    fontSize: 28,
    fontWeight: 700,
    color: 'var(--text-primary)',
    fontFamily: "'JetBrains Mono', monospace",
    letterSpacing: '-0.5px',
    lineHeight: 1.2,
    marginTop: 4,
  },
  statSub: { fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 },
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 14px',
    marginBottom: 'var(--space-4)',
    borderRadius: 'var(--radius-lg)',
    backgroundColor: 'var(--status-error-bg)',
    color: 'var(--status-error)',
    fontSize: 13,
  },
  errorDismiss: {
    border: 'none',
    background: 'none',
    cursor: 'pointer',
    fontSize: 18,
    color: 'inherit',
    lineHeight: 1,
    padding: '0 4px',
  },
  toolbar: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 'var(--space-3)',
    marginBottom: 'var(--space-5)',
  },
  searchWrap: {
    position: 'relative',
    flex: '1 1 200px',
    minWidth: 180,
  },
  searchIcon: {
    position: 'absolute',
    left: 12,
    top: '50%',
    transform: 'translateY(-50%)',
    color: 'var(--text-tertiary)',
    display: 'flex',
  },
  searchInput: {
    width: '100%',
    padding: '9px 12px 9px 36px',
    fontSize: 13,
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    backgroundColor: 'var(--surface-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
    transition: 'border-color var(--transition-fast), box-shadow var(--transition-fast)',
  },
  filterGroup: {
    display: 'flex',
    gap: 2,
    padding: 3,
    backgroundColor: 'var(--surface-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-subtle)',
  },
  filterBtn: {
    padding: '6px 14px',
    fontSize: 12,
    fontWeight: 500,
    border: 'none',
    borderRadius: 'var(--radius-md)',
    background: 'transparent',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  filterBtnActive: {
    backgroundColor: 'var(--surface-primary)',
    color: 'var(--accent-primary)',
    boxShadow: 'var(--shadow-xs)',
  },
  toolbarRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
    marginLeft: 'auto',
  },
  viewToggle: {
    display: 'flex',
    gap: 2,
    padding: 3,
    backgroundColor: 'var(--surface-secondary)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-subtle)',
  },
  viewBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 30,
    height: 28,
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    background: 'transparent',
    color: 'var(--text-tertiary)',
    cursor: 'pointer',
  },
  viewBtnActive: {
    backgroundColor: 'var(--surface-primary)',
    color: 'var(--accent-primary)',
    boxShadow: 'var(--shadow-xs)',
  },
  refreshBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 34,
    height: 34,
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    backgroundColor: 'var(--surface-primary)',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
  },
  primaryBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 16px',
    fontSize: 13,
    fontWeight: 600,
    color: '#fff',
    background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
    border: 'none',
    borderRadius: 'var(--radius-lg)',
    cursor: 'pointer',
    boxShadow: '0 2px 8px rgba(99,102,241,0.35)',
    transition: 'transform var(--transition-fast), box-shadow var(--transition-fast)',
  },
  secondaryBtn: {
    padding: '8px 16px',
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--surface-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    cursor: 'pointer',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: 'var(--space-4)',
  },
  labCard: {
    ...catalogStyles.card,
    padding: 'var(--space-5)',
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-2)',
    transition: 'transform var(--transition-fast), box-shadow var(--transition-fast)',
  },
  labCardInactive: { opacity: 0.72 },
  labCardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 'var(--space-1)',
  },
  labIconWrap: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 40,
    height: 40,
    borderRadius: 'var(--radius-lg)',
    background: 'linear-gradient(135deg, #eef2ff, #e0e7ff)',
    color: '#6366f1',
  },
  labCode: {
    fontSize: 11,
    fontWeight: 600,
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-primary)',
    letterSpacing: '0.5px',
  },
  labName: {
    margin: 0,
    fontSize: 16,
    fontWeight: 600,
    color: 'var(--text-primary)',
    lineHeight: 1.3,
  },
  labDesc: {
    margin: 0,
    fontSize: 12,
    color: 'var(--text-tertiary)',
    lineHeight: 1.5,
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  labMetrics: {
    marginTop: 'var(--space-2)',
    padding: 'var(--space-3)',
    ...catalogStyles.cardInset,
  },
  metricRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  metricLabel: { fontSize: 11, color: 'var(--text-tertiary)' },
  metricValue: { fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' },
  metricValueMono: {
    fontSize: 13,
    fontWeight: 600,
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--text-primary)',
  },
  progressTrack: {
    height: 4,
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--border-subtle)',
    marginBottom: 'var(--space-2)',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 'var(--radius-full)',
    background: 'linear-gradient(90deg, #6366f1, #06b6d4)',
    transition: 'width 0.4s ease',
  },
  labFooter: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-3)',
    marginTop: 'auto',
    paddingTop: 'var(--space-3)',
    borderTop: '1px solid var(--border-subtle)',
  },
  updatedAt: { fontSize: 11, color: 'var(--text-tertiary)' },
  labActions: { display: 'flex', gap: 6, flexWrap: 'wrap' },
  actionBtn: {
    padding: '4px 10px',
    fontSize: 12,
    fontWeight: 500,
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    backgroundColor: 'var(--surface-primary)',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
  },
  actionWarn: { color: 'var(--status-warning)', borderColor: 'color-mix(in srgb, var(--status-warning) 40%, var(--border-default))' },
  actionDanger: { color: 'var(--status-error)', borderColor: 'color-mix(in srgb, var(--status-error) 40%, var(--border-default))' },
  statusPill: {
    display: 'inline-flex',
    padding: '2px 8px',
    fontSize: 11,
    fontWeight: 600,
    borderRadius: 'var(--radius-full)',
  },
  statusActive: {
    backgroundColor: 'var(--status-success-bg)',
    color: 'var(--status-success)',
  },
  statusInactive: {
    backgroundColor: 'var(--surface-tertiary)',
    color: 'var(--text-tertiary)',
  },
  loadingBox: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 'var(--space-3)',
    padding: 'var(--space-12)',
    color: 'var(--text-tertiary)',
  },
  spinner: {
    width: 32,
    height: 32,
    border: '3px solid var(--border-subtle)',
    borderTopColor: '#6366f1',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  loadingText: { fontSize: 13 },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: 'var(--space-12) var(--space-6)',
    textAlign: 'center',
    ...catalogStyles.card,
  },
  emptyIcon: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 64,
    height: 64,
    marginBottom: 'var(--space-4)',
    borderRadius: 'var(--radius-xl)',
    background: 'linear-gradient(135deg, #eef2ff, #f5f3ff)',
    color: '#6366f1',
  },
  emptyTitle: { margin: '0 0 8px', fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' },
  emptyDesc: { margin: '0 0 20px', fontSize: 13, color: 'var(--text-tertiary)', maxWidth: 320 },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: {
    padding: '10px 16px',
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.4px',
    color: 'var(--text-tertiary)',
    textAlign: 'left',
    borderBottom: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--surface-secondary)',
  },
  tr: { transition: 'background-color var(--transition-fast)' },
  td: {
    padding: '12px 16px',
    fontSize: 13,
    borderBottom: '1px solid var(--border-subtle)',
    verticalAlign: 'middle',
  },
  listName: { fontWeight: 600, color: 'var(--text-primary)' },
  listDesc: { fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 },
  codeTag: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 12,
    padding: '2px 8px',
    borderRadius: 'var(--radius-sm)',
    backgroundColor: 'var(--status-info-bg)',
    color: 'var(--accent-primary)',
  },
  listActions: { display: 'flex', gap: 6, justifyContent: 'flex-end' },
  overlay: {
    position: 'fixed',
    inset: 0,
    backgroundColor: 'rgba(15, 23, 42, 0.45)',
    backdropFilter: 'blur(4px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: 'var(--space-4)',
    animation: 'fadeIn 0.2s ease',
  },
  modal: {
    backgroundColor: 'var(--surface-primary)',
    borderRadius: 'var(--radius-xl)',
    minWidth: 400,
    maxWidth: 480,
    width: '100%',
    boxShadow: 'var(--shadow-lg)',
    border: '1px solid var(--border-subtle)',
    animation: 'scaleIn 0.25s ease',
    overflow: 'hidden',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: 'var(--space-5) var(--space-6) var(--space-4)',
    borderBottom: '1px solid var(--border-subtle)',
    background: 'linear-gradient(180deg, #fafaff 0%, var(--surface-primary) 100%)',
  },
  modalTitle: { margin: 0, fontSize: 17, fontWeight: 700, color: 'var(--text-primary)' },
  modalSubtitle: { margin: '4px 0 0', fontSize: 12, color: 'var(--text-tertiary)' },
  modalClose: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 32,
    height: 32,
    border: 'none',
    borderRadius: 'var(--radius-md)',
    backgroundColor: 'transparent',
    color: 'var(--text-tertiary)',
    cursor: 'pointer',
  },
  formBody: {
    padding: 'var(--space-5) var(--space-6)',
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-4)',
  },
  field: { display: 'flex', flexDirection: 'column', gap: 6 },
  fieldLabel: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--text-secondary)',
  },
  fieldHint: { fontWeight: 400, color: 'var(--text-tertiary)' },
  input: {
    padding: '10px 12px',
    fontSize: 13,
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    backgroundColor: 'var(--surface-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
  },
  inputMono: {
    padding: '10px 12px',
    fontSize: 13,
    fontFamily: "'JetBrains Mono', monospace",
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    backgroundColor: 'var(--surface-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
    letterSpacing: '0.5px',
  },
  textarea: {
    padding: '10px 12px',
    fontSize: 13,
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    backgroundColor: 'var(--surface-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
    resize: 'vertical',
    fontFamily: 'inherit',
    lineHeight: 1.5,
  },
  select: {
    padding: '10px 12px',
    fontSize: 13,
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-lg)',
    backgroundColor: 'var(--surface-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
  },
  suggestion: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 10px',
    fontSize: 12,
    color: '#6366f1',
    backgroundColor: 'rgba(99,102,241,0.08)',
    borderRadius: 'var(--radius-md)',
    border: '1px dashed rgba(99,102,241,0.3)',
  },
  suggestionBtn: {
    padding: '2px 8px',
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 12,
    fontWeight: 600,
    color: '#6366f1',
    backgroundColor: 'rgba(99,102,241,0.15)',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
  },
  modalActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 'var(--space-2)',
    padding: 'var(--space-4) var(--space-6) var(--space-5)',
    borderTop: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--surface-secondary)',
  },
  migrateNotice: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 8,
    margin: 'var(--space-5) var(--space-6) 0',
    padding: 'var(--space-4)',
    borderRadius: 'var(--radius-lg)',
    backgroundColor: 'var(--status-warning-bg)',
    color: 'var(--status-warning)',
    fontSize: 13,
  },
  migrateCount: {
    fontSize: 24,
    fontWeight: 700,
    fontFamily: "'JetBrains Mono', monospace",
  },
  deactivateBtn: {
    background: 'linear-gradient(135deg, #f59e0b, #d97706)',
    boxShadow: '0 2px 8px rgba(245,158,11,0.35)',
  },
};

export default CatalogLabsPage;
