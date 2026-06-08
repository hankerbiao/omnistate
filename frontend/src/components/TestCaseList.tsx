import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../services/api';
import type { AutomationTestCaseResponse } from '../types';
import CreateAutomationTestCaseForm from './CreateAutomationTestCaseForm';

type DetailTab = 'code' | 'params' | 'relations' | 'meta';

interface DetailTabDef {
  id: DetailTab;
  label: string;
  condition?: boolean;
}

// 自动化用例状态映射
const AUTO_STATUS_LABELS: Record<string, string> = {
  ACTIVE: 'Active', INACTIVE: 'Inactive', DRAFT: 'Draft', DEPRECATED: 'Deprecated',
};
const STATUS_DOT: Record<string, string> = {
  ACTIVE: '#3fb950', INACTIVE: '#8b949e', DRAFT: '#58a6ff', DEPRECATED: '#f85149',
};

const FW_ICONS: Record<string, string> = {
  pytest: '🐍', Pytest: '🐍', PyTest: '🐍', unittest: '🐍',
  robotframework: '🤖', RobotFramework: '🤖', Robot: '🤖',
  playwright: '🎭', Playwright: '🎭', cypress: '🌲', Cypress: '🌲',
  selenium: '🌐', Selenium: '🌐', appium: '📱', Appium: '📱',
  requests: '📡', Requests: '📡', go: '🔵', Go: '🔵', junit: '☕', JUnit: '☕',
};

const FW_COLORS: Record<string, string> = {
  pytest: '#9cf', Playwright: '#e8e8e8', Cypress: '#69d3a8',
  Selenium: '#43b02a', Appium: '#ee6d4a', Requests: '#6cac4d',
  Go: '#00add8', RobotFramework: '#000', JUnit: '#25a162',
};

const TestCaseList: React.FC = () => {
  const [cases, setCases] = useState<AutomationTestCaseResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showDispatchModal, setShowDispatchModal] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [dispatchError, setDispatchError] = useState<string | null>(null);
  const [dispatchSuccess, setDispatchSuccess] = useState<string | null>(null);
  const [selected, setSelected] = useState<AutomationTestCaseResponse | null>(null);
  const [tab, setTab] = useState<DetailTab>('code');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  const categoryCounts = useMemo(() => {
    const map = new Map<string, number>();
    for (const c of cases) {
      const fw = c.framework || '其他';
      map.set(fw, (map.get(fw) || 0) + 1);
    }
    const sorted = Array.from(map.entries()).sort(([, a], [, b]) => b - a);
    return sorted;
  }, [cases]);

  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return cases.filter(c => {
      if (statusFilter !== 'all' && c.status !== statusFilter) return false;
      if (categoryFilter !== 'all' && (c.framework || '其他') !== categoryFilter) return false;
      if (!q) return true;
      return (
        c.name.toLowerCase().includes(q) ||
        c.auto_case_id.toLowerCase().includes(q) ||
        (c.framework || '').toLowerCase().includes(q) ||
        (c.automation_type || '').toLowerCase().includes(q)
      );
    });
  }, [cases, searchQuery, statusFilter, categoryFilter]);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listAutomationTestCases({ limit: 200 });
      setCases(res.data || []);
    } catch {
      setError('获取自动化测试用例列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleSelect = (id: string) => {
    setSelectedIds(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  };

  const fwIcon = (fw?: string) => fw ? (FW_ICONS[fw] || '⚙️') : '⚙️';
  const fwColor = (fw?: string) => fw ? (FW_COLORS[fw] || 'var(--accent-purple)') : 'var(--accent-purple)';

  const handleDispatch = async () => {
    if (selectedIds.size === 0) return;
    setDispatching(true);
    setDispatchError(null); setDispatchSuccess(null);
    try {
      const res = await api.dispatchTask({ cases: Array.from(selectedIds).map(id => ({ auto_case_id: id })) });
      if (res.code === 0 || res.code === 200) {
        setDispatchSuccess(`成功下发 ${selectedIds.size} 个，任务ID: ${res.data?.task_id}`);
        setSelectedIds(new Set());
        setTimeout(() => { setShowDispatchModal(false); setDispatchSuccess(null); }, 2000);
      } else setDispatchError(res.message || '下发任务失败');
    } catch { setDispatchError('下发任务失败'); } finally { setDispatching(false); }
  };

  const TABS: DetailTabDef[] = [
    { id: 'code', label: '代码与脚本' },
    { id: 'params', label: '参数与环境', condition: Boolean(selected && ((selected.param_spec?.length ?? 0) > 0 || (selected.runtime_env && Object.keys(selected.runtime_env).length > 0))) },
    { id: 'relations', label: '关联' },
    { id: 'meta', label: '元数据' },
  ];

  return (
    <div className="page-content" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 12, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 17, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
            ⚡ 自动化
            <span style={{ fontSize: 12, fontWeight: 500, padding: '1px 10px', borderRadius: 12, background: 'color-mix(in srgb, var(--accent-purple) 12%, transparent)', color: 'var(--accent-purple)', fontFamily: 'monospace' }}>{cases.length}</span>
          </span>
          {selectedIds.size > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 12px', background: 'color-mix(in srgb, var(--accent-blue) 8%, transparent)', borderRadius: 8, border: '1px solid color-mix(in srgb, var(--accent-blue) 18%, transparent)' }}>
              <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--accent-blue)' }}>已选 {selectedIds.size}</span>
              <button className="btn btn--primary btn--sm" onClick={() => setShowDispatchModal(true)}>下发</button>
              <button className="btn btn--ghost btn--sm" onClick={() => setSelectedIds(new Set())}>取消</button>
            </div>
          )}
          {selected && (
            <button className="btn btn--primary btn--sm" onClick={() => { setSelectedIds(new Set([selected.auto_case_id])); setShowDispatchModal(true); }}>
              ▶ 下发当前
            </button>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input className="form-input" style={{ width: 180, fontSize: 13 }} value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="搜索名称、ID、框架…" />
          <select className="form-input form-select" style={{ width: 120 }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option value="all">全部状态</option>
            <option value="ACTIVE">Active</option>
            <option value="DRAFT">Draft</option>
            <option value="INACTIVE">Inactive</option>
            <option value="DEPRECATED">Deprecated</option>
          </select>
          <button className="btn btn--ghost btn--sm" onClick={fetchAll} disabled={loading}>{loading ? '⋯' : '↻'}</button>
          <button className="btn btn--primary btn--sm" onClick={() => setShowCreateForm(true)}>+ 新建</button>
        </div>
      </div>

      {error && <div className="error-banner" style={{ marginBottom: 8, flexShrink: 0 }}>{error}</div>}

      {/* Split body */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', gap: 0, overflow: 'hidden', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-lg)', backgroundColor: 'var(--surface-primary)' }}>
        {/* ── Left list ── */}
        <div style={{ width: 300, minWidth: 300, borderRight: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-primary)' }}>
          {/* Header */}
          <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--border-subtle)', fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', display: 'flex', justifyContent: 'space-between' }}>
            <span>测试用例</span>
            <span>{filtered.length}/{cases.length}</span>
          </div>

          {/* Category pills */}
          <div style={{ padding: '6px 8px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            <button
              onClick={() => setCategoryFilter('all')}
              style={{
                fontSize: 11, padding: '3px 10px', border: 'none', borderRadius: 12, cursor: 'pointer',
                background: categoryFilter === 'all' ? 'color-mix(in srgb, var(--accent-primary) 15%, transparent)' : 'var(--surface-tertiary)',
                color: categoryFilter === 'all' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                fontWeight: categoryFilter === 'all' ? 600 : 500, transition: 'all 0.1s',
              }}
            >全部 {cases.length}</button>
            {categoryCounts.map(([fw, count]) => (
              <button
                key={fw}
                onClick={() => setCategoryFilter(fw)}
                style={{
                  fontSize: 11, padding: '3px 10px', border: 'none', borderRadius: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3,
                  background: categoryFilter === fw ? `${fwColor(fw)}20` : 'var(--surface-tertiary)',
                  color: categoryFilter === fw ? fwColor(fw) : 'var(--text-secondary)',
                  fontWeight: categoryFilter === fw ? 600 : 500, transition: 'all 0.1s',
                }}
              >{fwIcon(fw)} {fw} {count}</button>
            ))}
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {loading && cases.length === 0 ? (
              <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>加载中...</div>
            ) : filtered.length === 0 ? (
              <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>
                {searchQuery || statusFilter !== 'all' ? '无匹配' : '暂无用例'}
              </div>
            ) : filtered.map(c => {
              const isSel = selected?.auto_case_id === c.auto_case_id;
              const dot = STATUS_DOT[c.status] || '#8b949e';
              return (
                <div
                  key={c.id}
                  onClick={() => { setSelected(c); setTab('code'); }}
                  style={{
                    padding: '8px 12px', cursor: 'pointer', borderLeft: `2px solid ${isSel ? 'var(--accent-primary)' : 'transparent'}`,
                    backgroundColor: isSel ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)' : undefined,
                    borderBottom: '0.5px solid var(--border-subtle)', transition: 'background-color 0.1s',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: dot, flexShrink: 0 }} />
                    <span style={{ fontSize: 13, fontWeight: isSel ? 600 : 500, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.name}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 3 }}>
                    {c.framework && (
                      <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: `${fwColor(c.framework)}18`, color: fwColor(c.framework), fontWeight: 600, whiteSpace: 'nowrap' }}>
                        {fwIcon(c.framework)} {c.framework}
                      </span>
                    )}
                    {c.automation_type && <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>{c.automation_type}</span>}
                    <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)', marginLeft: 'auto' }}>v{c.version}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Right detail ── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-elevated)', minWidth: 0 }}>
          {!selected ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontSize: 14, gap: 8 }}>
              ← 从左侧选择一个自动化用例
            </div>
          ) : (
            <>
              {/* Detail header */}
              <div style={{ padding: '16px 24px 12px', borderBottom: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--accent-purple)', fontWeight: 500 }}>{selected.auto_case_id}</span>
                  {selected.framework && (
                    <span style={{ fontSize: 11, padding: '1px 8px', borderRadius: 6, background: `${fwColor(selected.framework)}18`, color: fwColor(selected.framework), fontWeight: 600 }}>
                      {fwIcon(selected.framework)} {selected.framework}
                    </span>
                  )}
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: STATUS_DOT[selected.status] || '#8b949e' }} />
                  <span style={{ fontSize: 12, color: STATUS_DOT[selected.status] || '#8b949e', fontWeight: 600 }}>{AUTO_STATUS_LABELS[selected.status] || selected.status}</span>
                  <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-tertiary)', padding: '1px 6px', borderRadius: 4, background: 'var(--surface-tertiary)' }}>v{selected.version}</span>
                  {selected.automation_type && <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{selected.automation_type}</span>}
                </div>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>{selected.name}</h2>
              </div>

              {/* Tabs */}
              <div style={{ display: 'flex', gap: 0, padding: '0 24px', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0 }}>
                {TABS.filter(t => t.condition !== false).map(t => (
                  <button key={t.id} type="button" style={{
                    padding: '10px 18px', border: 'none', background: 'transparent', color: tab === t.id ? 'var(--accent-primary)' : 'var(--text-tertiary)',
                    cursor: 'pointer', fontSize: 13, fontWeight: tab === t.id ? 600 : 500, borderBottom: `2px solid ${tab === t.id ? 'var(--accent-primary)' : 'transparent'}`, marginBottom: -1,
                    transition: 'color 0.15s',
                  }} onClick={() => setTab(t.id)}>{t.label}</button>
                ))}
              </div>

              {/* Tab content */}
              <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px', minHeight: 0 }}>
                {/* Code & Script */}
                {tab === 'code' && (
                  <div>
                    <Section title="仓库">
                      <div style={styles.grid2}>
                        <Field label="地址" mono>{selected.repo_url || '-'}</Field>
                        <Field label="分支" mono>{selected.repo_branch || '-'}</Field>
                        <Field label="脚本路径" mono>{selected.script_path || '-'}</Field>
                        <Field label="脚本名称">{selected.script_name || '-'}</Field>
                        <Field label="脚本实体 ID" mono>{selected.script_entity_id || '-'}</Field>
                        <Field label="执行命令" mono>{selected.entry_command || '-'}</Field>
                      </div>
                    </Section>
                    {selected.code_snapshot && <Section title="代码快照"><SnapshotBlock snapshot={selected.code_snapshot} /></Section>}
                    {selected.script_ref && (
                      <Section title="脚本引用">
                        <div style={styles.grid2}>
                          <Field label="实体 ID" mono>{selected.script_ref.entity_id || '-'}</Field>
                          <Field label="模块">{selected.script_ref.module || '-'}</Field>
                          <Field label="项目标签">{selected.script_ref.project_tag || '-'}</Field>
                          <Field label="项目范围">{selected.script_ref.project_scope || '-'}</Field>
                        </div>
                      </Section>
                    )}
                  </div>
                )}

                {/* Params & Env */}
                {tab === 'params' && (
                  <div>
                    {selected.param_spec?.length ? (
                      <Section title={`配置参数 (${selected.param_spec.length})`}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          {selected.param_spec.map((p, i) => (
                            <div key={i} style={{ padding: '10px 12px', background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-muted)' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                                <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'monospace', color: 'var(--accent-purple)' }}>{p.name}</span>
                                {p.label && <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{p.label}</span>}
                                <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--accent-cyan)', padding: '2px 6px', borderRadius: 4, background: 'rgba(57,208,214,0.15)' }}>{p.type}</span>
                                {p.required && <span style={{ fontSize: 10, color: 'var(--accent-red)', fontWeight: 600, padding: '2px 6px', borderRadius: 4, background: 'rgba(219,68,68,0.15)' }}>必填</span>}
                              </div>
                              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                <div><span style={styles.miniLabel}>默认值</span><span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-primary)' }}>{p.default !== undefined ? String(p.default) : '-'}</span></div>
                                {p.description && <div style={{ gridColumn: '1/-1' }}><span style={styles.miniLabel}>描述</span><span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{p.description}</span></div>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </Section>
                    ) : null}
                    {selected.runtime_env && Object.keys(selected.runtime_env).length > 0 && (
                      <Section title={`运行环境 (${Object.keys(selected.runtime_env).length})`}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 8 }}>
                          {Object.entries(selected.runtime_env).map(([k, v]) => (
                            <div key={k} style={{ padding: '8px 10px', background: 'var(--bg-secondary)', borderRadius: 6, border: '1px solid var(--border-muted)' }}>
                              <span style={{ display: 'block', fontSize: 11, fontFamily: 'monospace', color: 'var(--accent-purple)', fontWeight: 500, marginBottom: 2 }}>{k}</span>
                              <span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-primary)', wordBreak: 'break-all' }}>{String(v)}</span>
                            </div>
                          ))}
                        </div>
                      </Section>
                    )}
                    {(!selected.param_spec?.length && (!selected.runtime_env || Object.keys(selected.runtime_env).length === 0)) && (
                      <p style={styles.emptyHint}>暂无配置参数与运行环境</p>
                    )}
                  </div>
                )}

                {/* Relations */}
                {tab === 'relations' && (
                  <div>
                    <Section title="关联链路">
                      <div style={styles.relationChain}>
                        {/* Auto case */}
                        <div style={styles.relationNode}>
                          <span style={styles.relationIcon}>⚡</span>
                          <div>
                            <span style={styles.relationLabel}>自动化用例</span>
                            <span style={styles.relationValue}>{selected.auto_case_id}</span>
                          </div>
                        </div>

                        <span style={styles.relationArrow}>→</span>

                        {/* Manual case */}
                        <div style={{
                          ...styles.relationNode,
                          ...(selected.dml_manual_case_id ? {} : { opacity: 0.4 }),
                        }}>
                          <span style={styles.relationIcon}>📋</span>
                          <div>
                            <span style={styles.relationLabel}>手工用例</span>
                            {selected.dml_manual_case_id ? (
                              <span style={styles.relationValue}>{selected.dml_manual_case_id}</span>
                            ) : (
                              <span style={{ fontSize: 12, color: 'var(--text-tertiary)', fontStyle: 'italic' }}>未关联</span>
                            )}
                          </div>
                        </div>

                        <span style={styles.relationArrow}>→</span>

                        {/* Requirement */}
                        <div style={{
                          ...styles.relationNode,
                          opacity: selected.dml_manual_case_id ? 0.65 : 0.3,
                        }}>
                          <span style={styles.relationIcon}>📐</span>
                          <div>
                            <span style={styles.relationLabel}>关联需求</span>
                            <span style={{ fontSize: 12, color: 'var(--text-tertiary)', fontStyle: 'italic' }}>
                              {selected.dml_manual_case_id ? '通过手工用例关联' : '待关联手工用例'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </Section>

                    {selected.dml_manual_case_id && (
                      <Section title="快速操作">
                        <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0 }}>
                          手工用例 <strong style={{ fontFamily: 'monospace', color: 'var(--accent-cyan)' }}>{selected.dml_manual_case_id}</strong> 已关联到此自动化用例。
                          可前往手工用例详情页查看完整的需求关联。
                        </p>
                      </Section>
                    )}
                  </div>
                )}

                {/* Meta */}
                {tab === 'meta' && (
                  <div>
                    {selected.description && <Section title="描述"><div style={styles.descBox}>{selected.description}</div></Section>}
                    <Section title="属性">
                      <div style={styles.grid2}>
                        <Field label="维护人">{selected.maintainer_id || '-'}</Field>
                        <Field label="审核人">{selected.reviewer_id || '-'}</Field>
                        <Field label="手工用例 ID" mono>{selected.dml_manual_case_id || '-'}</Field>
                      </div>
                    </Section>
                    <Section title="时间">
                      <div style={styles.grid2}>
                        <Field label="创建时间" mono>{new Date(selected.created_at).toLocaleString('zh-CN')}</Field>
                        <Field label="更新时间" mono>{new Date(selected.updated_at).toLocaleString('zh-CN')}</Field>
                      </div>
                    </Section>
                    {selected.tags?.length ? (
                      <Section title="标签">
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {selected.tags.map((t, i) => (
                            <span key={i} style={{ fontSize: 11, padding: '3px 10px', borderRadius: 12, background: 'rgba(88,166,255,0.15)', color: '#58a6ff' }}>{t}</span>
                          ))}
                        </div>
                      </Section>
                    ) : null}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Create form modal */}
      {showCreateForm && <CreateAutomationTestCaseForm onClose={() => setShowCreateForm(false)} onSuccess={fetchAll} />}

      {/* Dispatch modal */}
      {showDispatchModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div onClick={e => e.stopPropagation()} style={{ background: 'var(--bg-elevated)', borderRadius: 12, width: 400, maxWidth: '90vw', boxShadow: '0 20px 60px rgba(0,0,0,0.4)', border: '1px solid var(--border-default)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>下发任务</h3>
              <button style={{ fontSize: 22, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => setShowDispatchModal(false)}>×</button>
            </div>
            <div style={{ padding: 20 }}>
              <p style={{ margin: '0 0 12', fontSize: 14, color: 'var(--text-secondary)' }}>将 <strong>{selectedIds.size}</strong> 个用例下发到执行队列</p>
              {dispatchError && <div style={{ padding: '10px 14px', background: 'var(--status-error-bg)', borderRadius: 6, fontSize: 13, color: 'var(--status-error)', marginBottom: 8 }}>⚠ {dispatchError}</div>}
              {dispatchSuccess && <div style={{ padding: '10px 14px', background: 'var(--status-success-bg)', borderRadius: 6, fontSize: 13, color: 'var(--status-success)' }}>✓ {dispatchSuccess}</div>}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, padding: '14px 20px', borderTop: '1px solid var(--border-subtle)' }}>
              <button className="btn btn--secondary" onClick={() => setShowDispatchModal(false)} disabled={dispatching}>取消</button>
              <button className="btn btn--primary" onClick={handleDispatch} disabled={dispatching || Boolean(dispatchSuccess)}>{dispatching ? '下发中...' : '确认下发'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ── Sub-components ──

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div style={{ marginBottom: 20 }}>
    <span style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 10 }}>{title}</span>
    {children}
  </div>
);

const Field: React.FC<{ label: string; mono?: boolean; children: React.ReactNode }> = ({ label, mono, children }) => (
  <div>
    <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', display: 'block', marginBottom: 2 }}>{label}</span>
    <span style={{ fontSize: 13, color: 'var(--text-primary)', fontFamily: mono ? 'monospace' : undefined, wordBreak: 'break-word' }}>{children}</span>
  </div>
);

const SnapshotBlock: React.FC<{ snapshot: NonNullable<AutomationTestCaseResponse['code_snapshot']> }> = ({ snapshot }) => (
  <>
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 8 }}>
      {[{ label: '分支', value: snapshot.branch }, { label: 'Commit', value: (snapshot.commit_short_id || snapshot.commit_id || '-').slice(0, 12), mono: true },
        { label: '作者', value: snapshot.author }, { label: '提交时间', value: snapshot.commit_time ? new Date(snapshot.commit_time).toLocaleString('zh-CN') : '-' },
      ].map((s, i) => (
        <div key={i} style={{ padding: '8px 12px', background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-muted)' }}>
          <span style={{ display: 'block', fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 2 }}>{s.label}</span>
          <span style={{ fontSize: 12, color: 'var(--text-primary)', fontFamily: s.mono ? 'monospace' : undefined }}>{s.value}</span>
        </div>
      ))}
    </div>
    {snapshot.message && (
      <div style={{ padding: '8px 12px', background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-muted)' }}>
        <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', display: 'block', marginBottom: 4 }}>提交信息</span>
        <pre style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', fontFamily: 'monospace', lineHeight: 1.5 }}>{snapshot.message}</pre>
      </div>
    )}
  </>
);

const styles = {
  grid2: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' } as const,
  miniLabel: { display: 'block', fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase' as const, letterSpacing: '0.4px' } as const,
  emptyHint: { fontSize: 13, color: 'var(--text-muted)', textAlign: 'center' as const, padding: '32px 16px', margin: 0 } as const,
  descBox: { fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.6, padding: 12, background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-muted)' } as const,
  // Relations
  relationChain: { display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' as const } as const,
  relationNode: { display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px', background: 'var(--bg-secondary)', borderRadius: 10, border: '1px solid var(--border-muted)', minWidth: 140 } as const,
  relationIcon: { fontSize: 20 } as const,
  relationLabel: { display: 'block', fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase' as const, letterSpacing: '0.4px' } as const,
  relationValue: { fontSize: 13, fontWeight: 500, fontFamily: 'monospace', color: 'var(--text-primary)' } as const,
  relationArrow: { fontSize: 18, color: 'var(--text-tertiary)' } as const,
};

export default TestCaseList;
