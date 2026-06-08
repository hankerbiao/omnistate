import React, { useCallback, useEffect, useMemo, useState } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { api } from '../services/api';

// ═══════════════════════════════════════════════════════════════════
//  Mock data for the wizard (case/component/user selection UI only)
//  Actual plan CRUD uses the backend API.
// ═══════════════════════════════════════════════════════════════════

interface MockUser { id: string; name: string; }
interface MockComponent { id: string; name: string; }
interface MockCase { id: string; title: string; type: 'auto' | 'manual'; component: string; priority: string; duration: number; }
interface MockCollection { id: string; name: string; description?: string; caseIds: string[]; }

const MOCK_USERS: MockUser[] = [
  { id: 'zhangwei', name: '张伟' }, { id: 'lina', name: '李娜' },
  { id: 'wanghao', name: '王浩' }, { id: 'chenyu', name: '陈雨' },
  { id: 'liuqing', name: '刘青' }, { id: 'zhaomin', name: '赵敏' },
  { id: 'sunjie', name: '孙杰' }, { id: 'huxin', name: '胡欣' },
];

const MOCK_COMPONENTS: MockComponent[] = [
  { id: 'mem', name: '内存验证组' }, { id: 'fw', name: '固件验证组' },
  { id: 'tool', name: '工具链组' }, { id: 'storage', name: '存储验证组' },
  { id: 'platform', name: '平台质量组' },
];

const MOCK_CASES: MockCase[] = [
  { id: 'TC-001', title: '内存读写压力测试', type: 'auto', component: 'mem', priority: 'P1', duration: 30 },
  { id: 'TC-002', title: '内存边界值校验', type: 'manual', component: 'mem', priority: 'P2', duration: 15 },
  { id: 'TC-003', title: '固件版本升级测试', type: 'auto', component: 'fw', priority: 'P1', duration: 45 },
  { id: 'TC-004', title: '固件异常断电恢复', type: 'manual', component: 'fw', priority: 'P0', duration: 60 },
  { id: 'TC-005', title: 'CI/CD 管道集成测试', type: 'auto', component: 'tool', priority: 'P2', duration: 20 },
  { id: 'TC-006', title: '覆盖率分析工具验证', type: 'manual', component: 'tool', priority: 'P3', duration: 25 },
  { id: 'TC-007', title: '存储读写性能基准', type: 'auto', component: 'storage', priority: 'P1', duration: 40 },
  { id: 'TC-008', title: 'RAID 重建测试', type: 'manual', component: 'storage', priority: 'P2', duration: 90 },
  { id: 'TC-009', title: '多用户并发访问测试', type: 'auto', component: 'platform', priority: 'P1', duration: 35 },
  { id: 'TC-010', title: '安全权限验证', type: 'manual', component: 'platform', priority: 'P0', duration: 20 },
  { id: 'TC-011', title: 'DDR4 兼容性测试', type: 'auto', component: 'mem', priority: 'P2', duration: 50 },
  { id: 'TC-012', title: '固件日志轮转测试', type: 'manual', component: 'fw', priority: 'P3', duration: 10 },
  { id: 'TC-013', title: '分布式节点通信测试', type: 'auto', component: 'storage', priority: 'P1', duration: 60 },
  { id: 'TC-014', title: '工具链部署验证', type: 'manual', component: 'tool', priority: 'P2', duration: 30 },
  { id: 'TC-015', title: '跨固件版本回滚测试', type: 'auto', component: 'fw', priority: 'P1', duration: 35 },
];

const MOCK_COLLECTIONS: MockCollection[] = [
  { id: 'col-1', name: 'Sprint 1 回归用例集', description: 'Sprint 1 阶段的全部回归测试用例', caseIds: ['TC-001', 'TC-003', 'TC-007', 'TC-011'] },
  { id: 'col-2', name: '核心功能冒烟测试', description: '每次提交前必跑的冒烟测试集合', caseIds: ['TC-001', 'TC-003', 'TC-009'] },
  { id: 'col-3', name: '内存子系统全量', description: '内存模块的所有测试用例', caseIds: ['TC-001', 'TC-002', 'TC-011'] },
  { id: 'col-4', name: '稳定性长稳测试集', description: '长时间稳定性测试用例', caseIds: ['TC-004', 'TC-008', 'TC-013'] },
];

const PRIORITY_COLORS: Record<string, string> = { P0: '#f85149', P1: '#d29922', P2: '#58a6ff', P3: '#8b949e' };
const caseMap = new Map(MOCK_CASES.map(c => [c.id, c]));

// ── PlanSummary — 轻量结构，匹配后端 PlanListItem ──
interface PlanSummary {
  plan_id: string;
  title: string;
  description: string;
  status: string;   // 'draft' | 'active' | 'done' | 'archived'
  start_date: string;
  end_date: string;
  trigger_at: string;
  created_by: string;
  item_count: number;
  done_count: number;
  progress_percent: number;
  created_at: string;
  updated_at: string;
}

// ── PlanItem — 计划内条目的摘要 ──
interface PlanItemSummary {
  item_id: string;
  case_id: string;
  case_title: string;
  ref_type: string;
  component: string;
  priority: string;
  assignee_id: string | null;
  status: string;
  order_no: number;
}

const STATUS_COLORS: Record<string, string> = {
  pending: '#8b949e', running: '#58a6ff', done: '#3fb950', fail: '#f85149',
};

const STATUS_LABELS: Record<string, string> = {
  pending: '待执行', running: '执行中', done: '已完成', fail: '失败',
};

// ═══════════════════════════════════════════════════════════════════
//  Component
// ═══════════════════════════════════════════════════════════════════

type ViewMode = 'board' | 'list';

const TestExecutionPlan: React.FC = () => {
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activePlanId, setActivePlanId] = useState<string>('');
  const [viewMode, setViewMode] = useState<ViewMode>('board');
  const [showWizard, setShowWizard] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // ── Plan detail (items) ──
  const [activePlanItems, setActivePlanItems] = useState<PlanItemSummary[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);

  // ── Fetch plan list ──

  const fetchPlans = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listPlans();
      setPlans(res.data || []);
    } catch {
      setError('获取计划列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void fetchPlans(); }, [fetchPlans]);

  // ── Fetch active plan detail ──

  useEffect(() => {
    if (!activePlanId) {
      setActivePlanItems([]);
      return;
    }
    setDetailLoading(true);
    api.getPlanDetail(activePlanId)
      .then(res => {
        const d = res.data as Record<string, unknown> | undefined;
        setActivePlanItems((d?.items as PlanItemSummary[]) || []);
      })
      .catch(() => setActivePlanItems([]))
      .finally(() => setDetailLoading(false));
  }, [activePlanId]);

  const activePlan = plans.find(p => p.plan_id === activePlanId);

  // ── Stats for plan cards ──

  const planCardData = useMemo(() =>
    plans.map(p => ({ ...p, progress: p.progress_percent ?? 0 })),
    [plans],
  );

  // ── Wizard state ──

  const [wizardStep, setWizardStep] = useState(1);
  const [caseSearch, setCaseSearch] = useState('');
  const [submittingPlan, setSubmittingPlan] = useState(false);

  const [newPlan, setNewPlan] = useState<{
    title: string; description: string; startDate: string; endDate: string; triggerAt: string;
    selectedCases: string[]; assignments: Record<string, { component: string; assignee: string }>;
  }>({
    title: '', description: '', startDate: '', endDate: '', triggerAt: '',
    selectedCases: [], assignments: {},
  });

  const resetWizard = () => {
    setWizardStep(1);
    setCaseSearch('');
    setSubmittingPlan(false);
    setNewPlan({ title: '', description: '', startDate: '', endDate: '', triggerAt: '', selectedCases: [], assignments: {} });
  };

  const handleCreatePlan = async () => {
    if (!newPlan.title.trim() || newPlan.selectedCases.length === 0) return;
    setSubmittingPlan(true);

    try {
      // Step 1: Create plan
      const planRes = await api.createPlan({
        title: newPlan.title,
        description: newPlan.description || undefined,
        start_date: newPlan.startDate || undefined,
        end_date: newPlan.endDate || undefined,
        trigger_at: newPlan.triggerAt || undefined,
      });
      const planId = (planRes.data as Record<string, unknown>)?.plan_id as string;

      // Step 2: Add items
      const items = newPlan.selectedCases.map(cid => {
        const tc = caseMap.get(cid);
        return {
          ref_type: tc?.type === 'auto' ? 'auto' : 'manual',
          case_id: cid,
          assignee_id: newPlan.assignments[cid]?.assignee || undefined,
          component: newPlan.assignments[cid]?.component || tc?.component || undefined,
        };
      });
      await api.addPlanItems(planId, { items });

      // Step 3: Refresh
      await fetchPlans();
      setActivePlanId(planId);
    } catch (err) {
      console.error('创建计划失败:', err);
    } finally {
      setSubmittingPlan(false);
      setShowWizard(false);
      resetWizard();
    }
  };

  // ── Case selection helpers ──

  const toggleSelectCase = (cid: string) => {
    setNewPlan(prev => ({
      ...prev,
      selectedCases: prev.selectedCases.includes(cid)
        ? prev.selectedCases.filter(c => c !== cid)
        : [...prev.selectedCases, cid],
    }));
  };

  const toggleSelectCollection = (col: MockCollection) => {
    setNewPlan(prev => {
      const allSelected = col.caseIds.every(cid => prev.selectedCases.includes(cid));
      const ids = new Set(prev.selectedCases);
      for (const cid of col.caseIds) {
        if (allSelected) ids.delete(cid);
        else ids.add(cid);
      }
      return { ...prev, selectedCases: Array.from(ids) };
    });
  };

  const setAssignment = (caseId: string, field: 'component' | 'assignee', value: string) => {
    setNewPlan(prev => ({
      ...prev,
      assignments: {
        ...prev.assignments,
        [caseId]: { ...(prev.assignments[caseId] || { component: '', assignee: '' }), [field]: value },
      },
    }));
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: 'var(--space-5) var(--space-6)' }}>
      {/* ── Top bar ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.3px' }}>🎯 测试执行计划</span>
          <input className="form-input" style={{ width: 200, fontSize: 13 }} value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="搜索计划…" />
          <div style={{ display: 'flex', gap: 2, background: 'var(--surface-secondary)', borderRadius: 8, padding: 2 }}>
            {(['board', 'list'] as ViewMode[]).map(m => (
              <button key={m} onClick={() => setViewMode(m)} style={{
                padding: '4px 12px', fontSize: 12, border: 'none', borderRadius: 6, cursor: 'pointer',
                background: viewMode === m ? 'var(--surface-primary)' : 'transparent',
                color: viewMode === m ? 'var(--text-primary)' : 'var(--text-tertiary)',
                fontWeight: viewMode === m ? 600 : 400, transition: 'all 0.1s',
              }}>{m === 'board' ? '📋 看板' : '📄 列表'}</button>
            ))}
          </div>
        </div>
        <button className="btn btn--primary" onClick={() => { resetWizard(); setShowWizard(true); }}>+ 新建计划</button>
      </div>

      {/* ── Plan cards (horizontal scroll) ── */}
      {loading ? (
        <div style={{ marginBottom: 20, fontSize: 13, color: 'var(--text-tertiary)' }}>加载计划列表...</div>
      ) : (
        <div style={{ display: 'flex', gap: 12, marginBottom: 20, overflowX: 'auto', flexShrink: 0, paddingBottom: 4 }}>
          {planCardData.length === 0 && (
            <div style={{ minWidth: 280, padding: '20px 24px', borderRadius: 12, border: '1px dashed var(--border-subtle)', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>
              暂无执行计划，点击「+ 新建计划」开始
            </div>
          )}
          {planCardData
            .filter(p => !searchQuery || p.title.includes(searchQuery))
            .map(p => {
            const isActive = p.plan_id === activePlanId;
            const statusLabel = p.status === 'active' ? '进行中' : p.status === 'draft' ? '草稿' : p.status === 'done' ? '已完成' : '已归档';
            const statusColor = p.status === 'active' ? '#3fb950' : p.status === 'draft' ? '#58a6ff' : '#8b949e';
            return (
              <div key={p.plan_id} onClick={() => setActivePlanId(p.plan_id)} style={{
                minWidth: 200, cursor: 'pointer', borderRadius: 12, padding: '14px 18px',
                border: isActive ? '2px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                background: isActive ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)' : 'var(--surface-primary)',
                transition: 'all 0.15s', flexShrink: 0,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{p.title}</span>
                  <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 8,
                    background: `${statusColor}20`, color: statusColor, fontWeight: 600,
                  }}>
                    {statusLabel}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 8 }}>
                  {p.start_date || '?'} → {p.end_date || '?'}
                </div>
                <div style={{ height: 4, background: 'var(--surface-tertiary)', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ width: `${p.progress}%`, height: '100%', background: p.status === 'active' ? 'var(--accent-primary)' : 'var(--text-tertiary)', borderRadius: 2, transition: 'width 0.3s' }} />
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4, textAlign: 'right' }}>
                  {p.done_count}/{p.item_count} · {p.progress}%
                </div>
              </div>
            );
          })}
        </div>
      )}

      {error && (
        <div style={{ padding: '8px 14px', marginBottom: 12, background: 'rgba(248,81,73,0.08)', borderRadius: 8, fontSize: 12, color: '#f85149', display: 'flex', alignItems: 'center', gap: 6 }}>
          ⚠️ {error}
          <button onClick={() => setError(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#f85149', fontSize: 14 }}>×</button>
        </div>
      )}

      {/* ── Plan detail content (read-only, progress only) ── */}
      {!activePlan ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontSize: 14 }}>
          选择一个计划或新建一个计划
        </div>
      ) : detailLoading ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontSize: 14 }}>
          加载计划详情...
        </div>
      ) : viewMode === 'board' ? (
        <BoardView
          plan={activePlan}
          items={activePlanItems}
        />
      ) : (
        <ListView
          plan={activePlan}
          items={activePlanItems}
        />
      )}

      {/* ════════════════════════════════════════════════ */}
      {/*  Create Plan Wizard Modal                      */}
      {/* ════════════════════════════════════════════════ */}
      {showWizard && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000 }}>
          <div onClick={e => e.stopPropagation()} style={{ background: 'var(--bg-elevated)', borderRadius: 16, width: 720, maxWidth: '94vw', maxHeight: '88vh', display: 'flex', flexDirection: 'column', boxShadow: '0 25px 80px rgba(0,0,0,0.35)', border: '1px solid var(--border-default)' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '18px 24px', borderBottom: '1px solid var(--border-subtle)' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 17, fontWeight: 600 }}>新建执行计划</h3>
                <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                  {['基本信息', '选择用例', '分配配置', '排期确认'].map((s, i) => (
                    <span key={i} style={{ fontSize: 11, padding: '2px 10px', borderRadius: 10,
                      background: wizardStep === i + 1 ? 'var(--accent-primary)' : wizardStep > i + 1 ? 'rgba(63,185,80,0.15)' : 'var(--surface-tertiary)',
                      color: wizardStep === i + 1 ? '#fff' : wizardStep > i + 1 ? '#3fb950' : 'var(--text-tertiary)',
                      fontWeight: wizardStep === i + 1 ? 600 : 400,
                    }}>
                      {wizardStep > i + 1 ? '✓' : `${i + 1}`} {s}
                    </span>
                  ))}
                </div>
              </div>
              <button onClick={() => setShowWizard(false)} style={{ fontSize: 24, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}>×</button>
            </div>

            {/* Body */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
              {/* Step 1: Basic info */}
              {wizardStep === 1 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>计划名称 *</label>
                    <input className="form-input" value={newPlan.title} onChange={e => setNewPlan(p => ({ ...p, title: e.target.value }))} placeholder="例如：Sprint 3 · 安全与兼容性" style={{ width: '100%' }} autoFocus />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>描述</label>
                    <textarea className="form-input" value={newPlan.description} onChange={e => setNewPlan(p => ({ ...p, description: e.target.value }))} placeholder="计划的目地、范围、备注…" rows={3} style={{ width: '100%', resize: 'vertical' }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>📅 计划周期</label>
                    <DateRangePicker
                      startDate={newPlan.startDate}
                      endDate={newPlan.endDate}
                      onChange={(start, end) => setNewPlan(p => ({ ...p, startDate: start, endDate: end }))}
                    />
                  </div>
                </div>
              )}

              {/* Step 2: Select test cases */}
              {wizardStep === 2 && (
                <div>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '0 0 12px' }}>
                    从用例库中选择要执行的用例，已选 <strong>{newPlan.selectedCases.length}</strong> 个
                  </p>
                  <div style={{ position: 'relative', marginBottom: 12 }}>
                    <input className="form-input" value={caseSearch} onChange={e => setCaseSearch(e.target.value)}
                      placeholder="搜索用例名称、ID 或用例集合…" style={{ width: '100%', fontSize: 13, padding: '7px 12px', boxSizing: 'border-box' }} />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {(() => {
                      const q = caseSearch.trim().toLowerCase();
                      const matchedCollections = q
                        ? MOCK_COLLECTIONS.filter(col =>
                            col.name.toLowerCase().includes(q) ||
                            (col.description || '').toLowerCase().includes(q) ||
                            col.caseIds.some(cid => cid.toLowerCase().includes(q)))
                        : MOCK_COLLECTIONS;
                      const matchedCases = q
                        ? MOCK_CASES.filter(tc => tc.id.toLowerCase().includes(q) || tc.title.toLowerCase().includes(q))
                        : MOCK_CASES;
                      return (
                        <>
                          {matchedCollections.length > 0 && (
                            <div style={{ marginBottom: 8 }}>
                              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', padding: '4px 2px 8px', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                                📂 用例集合 ({matchedCollections.length})
                              </div>
                              {matchedCollections.map(col => {
                                const allSelected = col.caseIds.every(cid => newPlan.selectedCases.includes(cid));
                                const someSelected = col.caseIds.some(cid => newPlan.selectedCases.includes(cid));
                                return (
                                  <label key={col.id} onClick={() => toggleSelectCollection(col)} style={{
                                    display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px',
                                    borderRadius: 8, cursor: 'pointer', marginBottom: 4,
                                    border: allSelected ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                                    background: allSelected ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)' : 'var(--bg-primary)',
                                  }}>
                                    <input type="checkbox" checked={allSelected}
                                      ref={el => { if (el) el.indeterminate = someSelected && !allSelected; }}
                                      onChange={() => {}} style={{ accentColor: 'var(--accent-primary)' }} />
                                    <span style={{ fontSize: 13 }}>📂</span>
                                    <div style={{ flex: 1 }}>
                                      <div style={{ fontSize: 13, fontWeight: allSelected ? 600 : 500 }}>{col.name}</div>
                                      {col.description && <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 1 }}>{col.description}</div>}
                                    </div>
                                    <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{col.caseIds.length} 个用例</span>
                                  </label>
                                );
                              })}
                            </div>
                          )}
                          {matchedCases.length > 0 && (
                            <div>
                              {!q && <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', padding: '4px 2px 8px', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                                🔬 用例 ({matchedCases.length})
                              </div>}
                              {matchedCases.map(tc => {
                                const sel = newPlan.selectedCases.includes(tc.id);
                                return (
                                  <label key={tc.id} onClick={() => toggleSelectCase(tc.id)} style={{
                                    display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px',
                                    borderRadius: 8, cursor: 'pointer',
                                    border: sel ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                                    background: sel ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)' : 'var(--bg-primary)',
                                    transition: 'all 0.1s', marginBottom: 4,
                                  }}>
                                    <input type="checkbox" checked={sel} onChange={() => {}} style={{ accentColor: 'var(--accent-primary)' }} />
                                    <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-tertiary)', minWidth: 60 }}>{tc.id}</span>
                                    <span style={{ flex: 1, fontSize: 13, fontWeight: sel ? 600 : 400 }}>{tc.title}</span>
                                    <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6,
                                      background: tc.type === 'auto' ? 'rgba(57,208,214,0.15)' : 'rgba(163,113,247,0.15)',
                                      color: tc.type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600,
                                    }}>{tc.type === 'auto' ? '⚡ 自动化' : '📋 手动'}</span>
                                    <span style={{ fontSize: 11, color: PRIORITY_COLORS[tc.priority], fontWeight: 600 }}>{tc.priority}</span>
                                    <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{tc.duration}min</span>
                                    <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{MOCK_COMPONENTS.find(c => c.id === tc.component)?.name}</span>
                                  </label>
                                );
                              })}
                            </div>
                          )}
                          {matchedCollections.length === 0 && matchedCases.length === 0 && (
                            <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>无匹配的用例或集合</div>
                          )}
                        </>
                      );
                    })()}
                  </div>
                </div>
              )}

              {/* Step 3: Assign components & people */}
              {wizardStep === 3 && (
                <div>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '0 0 12px' }}>
                    为已选用例分配组件和执行人（提交后将在「我的任务」中可见）
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {newPlan.selectedCases.map(cid => {
                      const tc = caseMap.get(cid);
                      if (!tc) return null;
                      return (
                        <div key={cid} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
                          <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-tertiary)', minWidth: 55 }}>{cid}</span>
                          <span style={{ flex: 1, fontSize: 13, fontWeight: 500 }}>{tc.title}</span>
                          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6,
                            background: tc.type === 'auto' ? 'rgba(57,208,214,0.15)' : 'rgba(163,113,247,0.15)',
                            color: tc.type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600,
                          }}>{tc.type === 'auto' ? '⚡' : '📋'}</span>
                          <select className="form-input form-select" style={{ width: 140, fontSize: 12 }}
                            value={newPlan.assignments[cid]?.component || tc.component}
                            onChange={e => setAssignment(cid, 'component', e.target.value)}>
                            {MOCK_COMPONENTS.map(comp => <option key={comp.id} value={comp.id}>{comp.name}</option>)}
                          </select>
                          <select className="form-input form-select" style={{ width: 100, fontSize: 12 }}
                            value={newPlan.assignments[cid]?.assignee || ''}
                            onChange={e => setAssignment(cid, 'assignee', e.target.value)}>
                            <option value="">执行人</option>
                            {MOCK_USERS.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
                          </select>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Step 4: Schedule & review */}
              {wizardStep === 4 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>⏰ 自动触发时间</label>
                    <input type="datetime-local" className="form-input" value={newPlan.triggerAt}
                      onChange={e => setNewPlan(p => ({ ...p, triggerAt: e.target.value }))} style={{ width: 280 }} />
                    <p style={{ fontSize: 11, color: 'var(--text-tertiary)', margin: '4px 0 0' }}>到达设定时间后自动开始执行所有待执行的用例</p>
                  </div>
                  <div style={{ background: 'var(--bg-secondary)', borderRadius: 10, padding: 16, border: '1px solid var(--border-subtle)' }}>
                    <h4 style={{ margin: '0 0 10px', fontSize: 13, fontWeight: 600 }}>📋 计划概览</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '6px 16px', fontSize: 13 }}>
                      <span style={{ color: 'var(--text-tertiary)' }}>名称</span><span style={{ fontWeight: 500 }}>{newPlan.title || '-'}</span>
                      <span style={{ color: 'var(--text-tertiary)' }}>周期</span><span>{newPlan.startDate || '?'} → {newPlan.endDate || '?'}</span>
                      <span style={{ color: 'var(--text-tertiary)' }}>触发</span><span>{newPlan.triggerAt || '手动触发'}</span>
                      <span style={{ color: 'var(--text-tertiary)' }}>用例数</span><span style={{ fontWeight: 600 }}>{newPlan.selectedCases.length} 个（{newPlan.selectedCases.filter(c => caseMap.get(c)?.type === 'auto').length} 自动 / {newPlan.selectedCases.filter(c => caseMap.get(c)?.type === 'manual').length} 手动）</span>
                      <span style={{ color: 'var(--text-tertiary)' }}>涉及组件</span><span>{new Set(newPlan.selectedCases.map(c => newPlan.assignments[c]?.component || caseMap.get(c)?.component || '')).size} 个</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '14px 24px', borderTop: '1px solid var(--border-subtle)' }}>
              <button className="btn btn--secondary" onClick={() => wizardStep > 1 ? setWizardStep(s => s - 1) : setShowWizard(false)}>
                {wizardStep > 1 ? '上一步' : '取消'}
              </button>
              {wizardStep < 4 ? (
                <button className="btn btn--primary" onClick={() => setWizardStep(s => s + 1)} disabled={wizardStep === 1 && !newPlan.title.trim()}>
                  下一步
                </button>
              ) : (
                <button className="btn btn--primary" onClick={handleCreatePlan}
                  disabled={newPlan.selectedCases.length === 0 || submittingPlan}>
                  {submittingPlan ? '创建中...' : '✓ 创建计划'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  Board View — 只读看板，展示进度
// ═══════════════════════════════════════════════════════════════════

const COL_STATUS = [
  { key: 'pending', label: '待执行', color: '#8b949e' },
  { key: 'running', label: '执行中', color: '#58a6ff' },
  { key: 'done', label: '已完成', color: '#3fb950' },
  { key: 'fail', label: '失败', color: '#f85149' },
];

const STATUS_BG: Record<string, string> = {
  pending: 'rgba(139,148,158,0.08)', running: 'rgba(88,166,255,0.08)',
  done: 'rgba(63,185,80,0.08)', fail: 'rgba(248,81,73,0.08)',
};
const STATUS_BORDER: Record<string, string> = {
  pending: '1px solid var(--border-muted)', running: '1px solid rgba(88,166,255,0.4)',
  done: '1px solid rgba(63,185,80,0.4)', fail: '1px solid rgba(248,81,73,0.4)',
};

const BoardView: React.FC<{
  plan: PlanSummary;
  items: PlanItemSummary[];
}> = ({ plan, items }) => {
  const componentGroups = useMemo(() => {
    const groups = new Map<string, PlanItemSummary[]>();
    for (const item of items) {
      const comp = item.component || 'other';
      if (!groups.has(comp)) groups.set(comp, []);
      groups.get(comp)!.push(item);
    }
    return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [items]);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Plan meta bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 12, flexShrink: 0, padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: 10, border: '1px solid var(--border-subtle)' }}>
        <span style={{ fontSize: 15, fontWeight: 600 }}>{plan.title}</span>
        <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{plan.start_date || '?'} → {plan.end_date || '?'}</span>
        {plan.trigger_at && <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>⏰ 触发: {plan.trigger_at}</span>}
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>进度 {plan.progress_percent ?? 0}% · {plan.done_count}/{plan.item_count}</span>
        <div style={{ width: 80, height: 4, background: 'var(--surface-tertiary)', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ width: `${plan.progress_percent ?? 0}%`, height: '100%', background: plan.status === 'active' ? 'var(--accent-primary)' : 'var(--text-tertiary)', borderRadius: 2, transition: 'width 0.3s' }} />
        </div>
      </div>

      {/* Read-only kanban board — 仅展示进度，无操作按钮 */}
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', gap: 12, minHeight: 0 }}>
        {componentGroups.length === 0 && (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>
            该计划暂无条目
          </div>
        )}
        {componentGroups.map(([compId, caseItems]) => {
          const compName = [...MOCK_COMPONENTS, { id: 'other', name: '其他' }].find(c => c.id === compId)?.name || compId;
          return (
            <div key={compId} style={{ minWidth: 260, maxWidth: 300, display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', padding: '6px 10px', marginBottom: 6, display: 'flex', justifyContent: 'space-between' }}>
                <span>{compName}</span>
                <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{caseItems.length}</span>
              </div>
              <div style={{ flex: 1, background: 'var(--bg-secondary)', borderRadius: 10, padding: 8, display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto' }}>
                {caseItems.map(item => (
                  <div key={item.item_id} style={{
                    background: STATUS_BG[item.status], borderRadius: 8, padding: '10px 12px',
                    border: STATUS_BORDER[item.status],
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{item.case_id}</span>
                      <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4,
                        background: item.ref_type === 'auto' ? 'rgba(57,208,214,0.15)' : 'rgba(163,113,247,0.15)',
                        color: item.ref_type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600,
                      }}>{item.ref_type === 'auto' ? '⚡' : '📋'}</span>
                    </div>
                    <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 6, lineHeight: 1.4 }}>{item.case_title}</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: 10, color: PRIORITY_COLORS[item.priority] || '#8b949e', fontWeight: 600 }}>{item.priority}</span>
                      <span style={{
                        fontSize: 10, fontWeight: 600, padding: '1px 6px', borderRadius: 4,
                        color: STATUS_COLORS[item.status], background: `${STATUS_COLORS[item.status]}15`,
                      }}>
                        {STATUS_LABELS[item.status] || item.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  List View — 只读列表，展示进度
// ═══════════════════════════════════════════════════════════════════

const ListView: React.FC<{
  plan: PlanSummary;
  items: PlanItemSummary[];
}> = ({ plan, items }) => {
  return (
    <div style={{ flex: 1, overflow: 'auto' }}>
      {/* Plan meta bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 12, flexShrink: 0, padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: 10, border: '1px solid var(--border-subtle)' }}>
        <span style={{ fontSize: 15, fontWeight: 600 }}>{plan.title}</span>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>进度 {plan.progress_percent ?? 0}% · {plan.done_count}/{plan.item_count}</span>
        <div style={{ width: 80, height: 4, background: 'var(--surface-tertiary)', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ width: `${plan.progress_percent ?? 0}%`, height: '100%', background: plan.status === 'active' ? 'var(--accent-primary)' : 'var(--text-tertiary)', borderRadius: 2, transition: 'width 0.3s' }} />
        </div>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: 'var(--surface-secondary)' }}>
            <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11 }}>用例</th>
            <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11 }}>类型</th>
            <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11 }}>组件</th>
            <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11 }}>优先级</th>
            <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11 }}>执行人</th>
            <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11 }}>状态</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 && (
            <tr><td colSpan={6} style={{ padding: '24px', textAlign: 'center', color: 'var(--text-tertiary)' }}>该计划暂无条目</td></tr>
          )}
          {items.map(item => (
            <tr key={item.item_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px 14px' }}>
                <span style={{ fontWeight: 500 }}>{item.case_title}</span>
                <br /><span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{item.case_id}</span>
              </td>
              <td style={{ padding: '8px 14px' }}>
                <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6,
                  background: item.ref_type === 'auto' ? 'rgba(57,208,214,0.15)' : 'rgba(163,113,247,0.15)',
                  color: item.ref_type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600,
                }}>{item.ref_type === 'auto' ? '⚡ 自动化' : '📋 手动'}</span>
              </td>
              <td style={{ padding: '8px 14px', color: 'var(--text-secondary)' }}>
                {[...MOCK_COMPONENTS, { id: 'other', name: '其他' }].find(c => c.id === item.component)?.name || item.component}
              </td>
              <td style={{ padding: '8px 14px', color: PRIORITY_COLORS[item.priority] || '#8b949e', fontWeight: 600 }}>{item.priority}</td>
              <td style={{ padding: '8px 14px', color: 'var(--text-secondary)' }}>
                {item.assignee_id ? ([...MOCK_USERS].find(u => u.id === item.assignee_id)?.name || item.assignee_id) : '-'}
              </td>
              <td style={{ padding: '8px 14px' }}>
                <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 10,
                  background: `${STATUS_COLORS[item.status] || '#8b949e'}15`,
                  color: STATUS_COLORS[item.status] || '#8b949e', fontWeight: 600,
                }}>
                  {STATUS_LABELS[item.status] || item.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  DateRangePicker
// ═══════════════════════════════════════════════════════════════════

function DateRangePicker({ startDate, endDate, onChange }: {
  startDate: string;
  endDate: string;
  onChange: (start: string, end: string) => void;
}) {
  const parseDate = (s: string) => s ? new Date(s + 'T00:00:00') : null;
  const fmtDate = (d: Date | null) => d ? d.toISOString().slice(0, 10) : '';
  const [start, setStart] = useState<Date | null>(parseDate(startDate));
  const [end, setEnd] = useState<Date | null>(parseDate(endDate));
  const handleChange = (dates: [Date | null, Date | null]) => {
    const [s, e] = dates;
    setStart(s);
    setEnd(e);
    onChange(fmtDate(s), fmtDate(e));
  };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <DatePicker selected={start} onChange={handleChange} startDate={start} endDate={end}
        selectsRange inline monthsShown={1} dateFormat="yyyy-MM-dd"
        calendarClassName="compact-datepicker"
        dayClassName={d => {
          const ds = fmtDate(d);
          if (startDate && endDate && ds >= startDate && ds <= endDate) return 'rdp-in-range';
          if (ds === startDate || ds === endDate) return 'rdp-selected';
          return '';
        }}
      />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
        <span style={{ fontWeight: 500, color: start ? 'var(--accent-primary)' : 'var(--text-tertiary)' }}>{startDate || '未选'}</span>
        <span style={{ color: 'var(--text-tertiary)' }}>→</span>
        <span style={{ fontWeight: 500, color: end ? 'var(--accent-primary)' : 'var(--text-tertiary)' }}>{endDate || '未选'}</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
          <button className="btn btn--ghost btn--sm" onClick={() => { setStart(null); setEnd(null); onChange('', ''); }}
            style={{ fontSize: 10, padding: '2px 8px', lineHeight: 1.6 }}>清除</button>
          <button className="btn btn--ghost btn--sm" onClick={() => { const t = new Date(); const t2 = new Date(t); setStart(t); setEnd(t2); onChange(fmtDate(t), fmtDate(t2)); }}
            style={{ fontSize: 10, padding: '2px 8px', lineHeight: 1.6 }}>今天</button>
          <button className="btn btn--ghost btn--sm" onClick={() => { const t = new Date(); const n = new Date(t); n.setDate(t.getDate() + 7); setStart(t); setEnd(n); onChange(fmtDate(t), fmtDate(n)); }}
            style={{ fontSize: 10, padding: '2px 8px', lineHeight: 1.6 }}>7天</button>
          <button className="btn btn--ghost btn--sm" onClick={() => { const t = new Date(); const n = new Date(t); n.setDate(t.getDate() + 30); setStart(t); setEnd(n); onChange(fmtDate(t), fmtDate(n)); }}
            style={{ fontSize: 10, padding: '2px 8px', lineHeight: 1.6 }}>30天</button>
        </div>
      </div>
    </div>
  );
}

export default TestExecutionPlan;
