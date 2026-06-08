import React, { useState, useMemo } from 'react';

// ═══════════════════════════════════════════════════════════════════
//  Mock Data
// ═══════════════════════════════════════════════════════════════════

interface MockUser {
  id: string; name: string;
}
interface MockComponent {
  id: string; name: string;
}
interface MockCase {
  id: string; title: string; type: 'auto' | 'manual'; component: string; priority: string; duration: number;
}
interface MockPlanCase {
  caseId: string; status: 'pending' | 'running' | 'done' | 'fail'; assignee?: string;
}
interface MockPlan {
  id: string; title: string; description: string; startDate: string; endDate: string;
  triggerAt: string; status: 'draft' | 'active' | 'done'; progress: number;
  cases: MockPlanCase[];
}

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

const MOCK_PLANS: MockPlan[] = [
  {
    id: 'plan-1', title: 'Sprint 1 · 固件基线验证', description: '针对 v2.3 固件版本的全面验证，覆盖核心功能与稳定性',
    startDate: '2026-06-15', endDate: '2026-07-15', triggerAt: '2026-06-20 10:00',
    status: 'active', progress: 65,
    cases: [
      { caseId: 'TC-001', status: 'done', assignee: 'zhangwei' },
      { caseId: 'TC-002', status: 'pending', assignee: 'lina' },
      { caseId: 'TC-003', status: 'running', assignee: 'wanghao' },
      { caseId: 'TC-004', status: 'pending' },
      { caseId: 'TC-006', status: 'done', assignee: 'chenyu' },
      { caseId: 'TC-007', status: 'running', assignee: 'zhaomin' },
      { caseId: 'TC-010', status: 'pending', assignee: 'liuqing' },
    ],
  },
  {
    id: 'plan-2', title: 'Sprint 2 · 性能基准测试', description: '存储与内存性能基线，为下一迭代提供参考数据',
    startDate: '2026-07-01', endDate: '2026-07-31', triggerAt: '2026-07-05 09:00',
    status: 'active', progress: 30,
    cases: [
      { caseId: 'TC-005', status: 'running', assignee: 'huxin' },
      { caseId: 'TC-007', status: 'pending' },
      { caseId: 'TC-009', status: 'pending', assignee: 'sunjie' },
      { caseId: 'TC-011', status: 'done', assignee: 'zhangwei' },
      { caseId: 'TC-013', status: 'pending' },
    ],
  },
  {
    id: 'plan-3', title: 'Sprint 3 · 安全与兼容性', description: '安全审计、跨平台兼容性验证、边界条件测试',
    startDate: '2026-07-15', endDate: '2026-08-15', triggerAt: '2026-07-20 10:00',
    status: 'draft', progress: 0,
    cases: [
      { caseId: 'TC-008', status: 'pending' },
      { caseId: 'TC-012', status: 'pending' },
      { caseId: 'TC-014', status: 'pending', assignee: 'wanghao' },
      { caseId: 'TC-015', status: 'pending' },
    ],
  },
];

const PRIORITY_COLORS: Record<string, string> = { P0: '#f85149', P1: '#d29922', P2: '#58a6ff', P3: '#8b949e' };

const caseMap = new Map(MOCK_CASES.map(c => [c.id, c]));
const userMap = new Map(MOCK_USERS.map(u => [u.id, u]));
const compCases = (component: string) => MOCK_CASES.filter(c => c.component === component);

// ═══════════════════════════════════════════════════════════════════
//  Component
// ═══════════════════════════════════════════════════════════════════

type ViewMode = 'board' | 'list';

const TestExecutionPlan: React.FC = () => {
  const [plans, setPlans] = useState<MockPlan[]>(MOCK_PLANS);
  const [activePlanId, setActivePlanId] = useState<string>('plan-1');
  const [viewMode, setViewMode] = useState<ViewMode>('board');
  const [showWizard, setShowWizard] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const activePlan = plans.find(p => p.id === activePlanId);

  const refreshProgress = (planId: string) => {
    setPlans(prev => prev.map(p => {
      if (p.id !== planId) return p;
      const done = p.cases.filter(c => c.status === 'done').length;
      const progress = p.cases.length > 0 ? Math.round((done / p.cases.length) * 100) : 0;
      return { ...p, progress };
    }));
  };

  const updateCaseStatus = (planId: string, caseId: string, status: string) => {
    setPlans(prev => prev.map(p => {
      if (p.id !== planId) return p;
      return {
        ...p,
        cases: p.cases.map(c => c.caseId === caseId ? { ...c, status: status as any } : c),
      };
    }));
    refreshProgress(planId);
  };

  // ── Dispatch modal state ──
  const [dispatchModal, setDispatchModal] = useState<{
    open: boolean; caseId: string;
    strategy: 'immediate' | 'scheduled' | 'queue';
    plannedAt: string; environment: string; timeout: number; retry: number; notify: boolean;
    submitting: boolean; success: boolean; error: string | null;
  }>({
    open: false, caseId: '', strategy: 'immediate', plannedAt: '', environment: 'staging',
    timeout: 30, retry: 0, notify: true, submitting: false, success: false, error: null,
  });

  const openDispatchModal = (caseId: string) => {
    setDispatchModal({
      open: true, caseId, strategy: 'immediate', plannedAt: '',
      environment: 'staging', timeout: 30, retry: 0, notify: true,
      submitting: false, success: false, error: null,
    });
  };

  const closeDispatchModal = () => {
    setDispatchModal(prev => ({ ...prev, open: false, success: false }));
  };

  const handleDispatchSubmit = async () => {
    const dm = dispatchModal;
    if (dm.strategy === 'scheduled' && !dm.plannedAt) {
      setDispatchModal(prev => ({ ...prev, error: '请选择计划执行时间' }));
      return;
    }
    setDispatchModal(prev => ({ ...prev, submitting: true, error: null }));
    await new Promise(resolve => setTimeout(resolve, 1200));
    setDispatchModal(prev => ({ ...prev, submitting: false, success: true }));
    setTimeout(() => closeDispatchModal(), 2000);
  };

  const planCardProgress = plans.map(p => {
    const done = p.cases.filter(c => c.status === 'done').length;
    return { ...p, progress: p.cases.length > 0 ? Math.round((done / p.cases.length) * 100) : 0 };
  });

  // ── Wizard state ──
  const [wizardStep, setWizardStep] = useState(1);
  const [newPlan, setNewPlan] = useState<{
    title: string; description: string; startDate: string; endDate: string; triggerAt: string;
    selectedCases: string[]; assignments: Record<string, { component: string; assignee: string }>;
  }>({
    title: '', description: '', startDate: '', endDate: '', triggerAt: '',
    selectedCases: [], assignments: {},
  });

  const resetWizard = () => {
    setWizardStep(1);
    setNewPlan({ title: '', description: '', startDate: '', endDate: '', triggerAt: '', selectedCases: [], assignments: {} });
  };

  const handleCreatePlan = () => {
    if (!newPlan.title.trim()) return;
    const planCases = newPlan.selectedCases.map(cid => ({
      caseId: cid, status: 'pending' as const,
      assignee: newPlan.assignments[cid]?.assignee || undefined,
    }));
    const newId = `plan-${plans.length + 1}`;
    setPlans(prev => [...prev, {
      id: newId, title: newPlan.title, description: newPlan.description,
      startDate: newPlan.startDate, endDate: newPlan.endDate, triggerAt: newPlan.triggerAt,
      status: 'draft', progress: 0, cases: planCases,
    }]);
    setActivePlanId(newId);
    setShowWizard(false);
    resetWizard();
  };

  const toggleSelectCase = (cid: string) => {
    setNewPlan(prev => ({
      ...prev,
      selectedCases: prev.selectedCases.includes(cid)
        ? prev.selectedCases.filter(c => c !== cid)
        : [...prev.selectedCases, cid],
    }));
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
          <input className="form-input" style={{ width: 200, fontSize: 13 }} value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="搜索计划、用例…" />
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
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, overflowX: 'auto', flexShrink: 0, paddingBottom: 4 }}>
        {planCardProgress.map(p => {
          const isActive = p.id === activePlanId;
          return (
            <div key={p.id} onClick={() => setActivePlanId(p.id)} style={{
              minWidth: 200, cursor: 'pointer', borderRadius: 12, padding: '14px 18px',
              border: isActive ? '2px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
              background: isActive ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)' : 'var(--surface-primary)',
              transition: 'all 0.15s', flexShrink: 0,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{p.title}</span>
                <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 8,
                  background: p.status === 'active' ? 'rgba(63,185,80,0.15)' : p.status === 'draft' ? 'rgba(88,166,255,0.15)' : 'rgba(139,148,158,0.15)',
                  color: p.status === 'active' ? '#3fb950' : p.status === 'draft' ? '#58a6ff' : '#8b949e',
                  fontWeight: 600,
                }}>
                  {p.status === 'active' ? '进行中' : p.status === 'draft' ? '草稿' : '已完成'}
                </span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 8 }}>
                {p.startDate} → {p.endDate}
              </div>
              {/* Progress bar */}
              <div style={{ height: 4, background: 'var(--surface-tertiary)', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{ width: `${p.progress}%`, height: '100%', background: p.status === 'active' ? 'var(--accent-primary)' : 'var(--text-tertiary)', borderRadius: 2, transition: 'width 0.3s' }} />
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4, textAlign: 'right' }}>{p.progress}%</div>
            </div>
          );
        })}
      </div>

      {/* ── Board / List content ── */}
      {dispatchModal.open && (() => {
        const dm = dispatchModal;
        const tc = caseMap.get(dm.caseId);
        if (!tc) return null;
        return (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(6px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000 }}>
          <div onClick={e => e.stopPropagation()} style={{ background: 'var(--bg-elevated)', borderRadius: 16, width: 520, maxWidth: '94vw', boxShadow: '0 30px 80px rgba(0,0,0,0.35)', border: '1px solid var(--border-default)', overflow: 'hidden' }}>

            {/* Header with gradient-like background */}
            <div style={{ background: 'linear-gradient(135deg, rgba(57,208,214,0.08) 0%, rgba(163,113,247,0.08) 100%)', padding: '20px 24px 16px', borderBottom: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 14 }}>⚡</span>
                    <span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-tertiary)', background: 'var(--surface-tertiary)', padding: '1px 8px', borderRadius: 4 }}>{tc.id}</span>
                    <span style={{ fontSize: 11, padding: '1px 8px', borderRadius: 4, background: 'rgba(57,208,214,0.12)', color: '#39d0d6', fontWeight: 600 }}>{tc.type === 'auto' ? '自动化' : '手动'}</span>
                    <span style={{ fontSize: 11, color: '#d29922', fontWeight: 600 }}>{tc.priority}</span>
                  </div>
                  <h3 style={{ margin: 0, fontSize: 17, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.4 }}>{tc.title}</h3>
                  <div style={{ display: 'flex', gap: 16, marginTop: 6, fontSize: 12, color: 'var(--text-tertiary)' }}>
                    <span>⏱ 预估 {tc.duration} 分钟</span>
                    <span>📂 {MOCK_COMPONENTS.find(c => c.id === tc.component)?.name || tc.component}</span>
                  </div>
                </div>
                <button onClick={closeDispatchModal} style={{ fontSize: 24, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', padding: 0, lineHeight: 1 }}>×</button>
              </div>
            </div>

            {/* Scrollable body */}
            <div style={{ padding: '20px 24px', maxHeight: '50vh', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 18 }}>

              {/* Strategy selection */}
              <div>
                <span style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 8 }}>执行策略</span>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                  {[
                    { key: 'immediate', icon: '🚀', title: '立即执行', desc: '不排队，立即下发' },
                    { key: 'scheduled', icon: '⏰', title: '定时执行', desc: '指定时间自动触发' },
                    { key: 'queue', icon: '🔁', title: '队列等待', desc: '加入执行队列轮候' },
                  ].map(opt => (
                    <button key={opt.key} onClick={() => setDispatchModal(prev => ({ ...prev, strategy: opt.key as any, error: null }))} style={{
                      padding: '10px 8px', border: dm.strategy === opt.key ? '2px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                      borderRadius: 10, cursor: 'pointer', textAlign: 'left',
                      background: dm.strategy === opt.key ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)' : 'var(--bg-primary)',
                      transition: 'all 0.12s',
                    }}>
                      <div style={{ fontSize: 16, marginBottom: 2 }}>{opt.icon}</div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: dm.strategy === opt.key ? 'var(--accent-primary)' : 'var(--text-primary)' }}>{opt.title}</div>
                      <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 1 }}>{opt.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Scheduled time (expandable) */}
              {dm.strategy === 'scheduled' && (
                <div style={{ animation: 'fadeIn 0.2s ease' }}>
                  <span style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 6 }}>计划执行时间</span>
                  <input type="datetime-local" className="form-input" value={dm.plannedAt}
                    onChange={e => setDispatchModal(prev => ({ ...prev, plannedAt: e.target.value, error: null }))}
                    style={{ width: '100%', fontSize: 13 }} />
                </div>
              )}

              {/* Queue position hint */}
              {dm.strategy === 'queue' && (
                <div style={{ padding: '10px 14px', background: 'rgba(88,166,255,0.08)', borderRadius: 8, fontSize: 12, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 14 }}>🔁</span>
                  <span>当前队列中有 <strong style={{ color: '#58a6ff' }}>3</strong> 个任务待执行，预计等待 <strong style={{ color: '#58a6ff' }}>~12</strong> 分钟</span>
                </div>
              )}

              {/* Execution config */}
              <div>
                <span style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 8 }}>执行配置</span>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4 }}>目标环境</label>
                    <select className="form-input form-select" value={dm.environment}
                      onChange={e => setDispatchModal(prev => ({ ...prev, environment: e.target.value }))}
                      style={{ width: '100%', fontSize: 12 }}>
                      <option value="staging">🟡 Staging 预发布</option>
                      <option value="testing">🔵 Testing 测试环境</option>
                      <option value="production">🔴 Production 生产</option>
                      <option value="dev">🟢 Dev 开发环境</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4 }}>超时时间（分钟）</label>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {[15, 30, 60, 120].map(t => (
                        <button key={t} onClick={() => setDispatchModal(prev => ({ ...prev, timeout: t }))} style={{
                          flex: 1, padding: '5px 0', fontSize: 11, border: dm.timeout === t ? '1.5px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                          borderRadius: 6, cursor: 'pointer', background: dm.timeout === t ? 'color-mix(in srgb, var(--accent-primary) 8%, transparent)' : 'var(--bg-primary)',
                          color: dm.timeout === t ? 'var(--accent-primary)' : 'var(--text-secondary)', fontWeight: dm.timeout === t ? 600 : 400,
                        }}>{t}min</button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4 }}>失败重试</label>
                    <select className="form-input form-select" value={dm.retry}
                      onChange={e => setDispatchModal(prev => ({ ...prev, retry: Number(e.target.value) }))}
                      style={{ width: '100%', fontSize: 12 }}>
                      <option value={0}>不重试</option>
                      <option value={1}>1 次</option>
                      <option value={2}>2 次</option>
                      <option value={3}>3 次</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4 }}>通知</label>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {[
                        { key: true, label: '🔔 开启' },
                        { key: false, label: '🔕 关闭' },
                      ].map(opt => (
                        <button key={String(opt.key)} onClick={() => setDispatchModal(prev => ({ ...prev, notify: opt.key }))} style={{
                          flex: 1, padding: '5px 0', fontSize: 11, border: dm.notify === opt.key ? '1.5px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                          borderRadius: 6, cursor: 'pointer', background: dm.notify === opt.key ? 'color-mix(in srgb, var(--accent-primary) 8%, transparent)' : 'var(--bg-primary)',
                          color: dm.notify === opt.key ? 'var(--accent-primary)' : 'var(--text-secondary)', fontWeight: dm.notify === opt.key ? 600 : 400,
                        }}>{opt.label}</button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Error */}
              {dm.error && (
                <div style={{ padding: '10px 14px', background: 'rgba(248,81,73,0.08)', borderRadius: 8, fontSize: 13, color: '#f85149', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span>⚠️</span> {dm.error}
                </div>
              )}

              {/* Success */}
              {dm.success && (
                <div style={{ padding: '14px 16px', background: 'linear-gradient(135deg, rgba(63,185,80,0.1) 0%, rgba(57,208,214,0.06) 100%)', borderRadius: 10, border: '1px solid rgba(63,185,80,0.2)', textAlign: 'center' }}>
                  <div style={{ fontSize: 28, marginBottom: 6 }}>✅</div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#3fb950', marginBottom: 4 }}>下发成功</div>
                  <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                    任务已进入执行队列 · 任务ID: <span style={{ fontFamily: 'monospace', color: 'var(--accent-primary)' }}>TASK-{String(Date.now()).slice(-6)}</span>
                  </div>
                </div>
              )}

              {/* Mock history */}
              {!dm.success && (
                <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: 8, fontSize: 11, color: 'var(--text-tertiary)', lineHeight: 1.7 }}>
                  <span style={{ fontWeight: 600 }}>📋 上次下发记录</span>
                  <div style={{ marginTop: 2 }}>
                    TC-003 固件版本升级测试 → <span style={{ color: '#3fb950' }}>✅ 已通过</span> （06-04 14:30）
                  </div>
                  <div>
                    TC-005 CI/CD 管道集成测试 → <span style={{ color: '#f0883e' }}>⏳ 执行中</span> （06-05 09:15）
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 24px', borderTop: '1px solid var(--border-subtle)', background: 'var(--bg-tertiary)' }}>
              <button className="btn btn--ghost btn--sm" onClick={closeDispatchModal} disabled={dm.submitting}>
                {dm.success ? '关闭' : '取消'}
              </button>
              <button className="btn btn--primary" onClick={handleDispatchSubmit}
                disabled={dm.submitting || dm.success}
                style={{ padding: '8px 24px', fontSize: 13, fontWeight: 600 }}>
                {dm.submitting ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ width: 12, height: 12, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block', animation: 'spin 0.6s linear infinite' }} />
                    下发中...
                  </span>
                ) : dm.success ? '✓ 已完成' : '🚀 确认下发'}
              </button>
            </div>

            <style>{`@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }`}</style>
          </div>
        </div>);
      })()}
      {!activePlan ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontSize: 14 }}>
          选择一个计划或新建一个计划
        </div>
      ) : viewMode === 'board' ? (
        <BoardView plan={activePlan} caseMap={caseMap} userMap={userMap} onStatusChange={updateCaseStatus} onDispatch={openDispatchModal} />
      ) : (
        <ListView plan={activePlan} caseMap={caseMap} userMap={userMap} onStatusChange={updateCaseStatus} onDispatch={openDispatchModal} />
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
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                    <div>
                      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>开始日期</label>
                      <input type="date" className="form-input" value={newPlan.startDate} onChange={e => setNewPlan(p => ({ ...p, startDate: e.target.value }))} style={{ width: '100%' }} />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>结束日期</label>
                      <input type="date" className="form-input" value={newPlan.endDate} onChange={e => setNewPlan(p => ({ ...p, endDate: e.target.value }))} style={{ width: '100%' }} />
                    </div>
                  </div>
                </div>
              )}

              {/* Step 2: Select test cases */}
              {wizardStep === 2 && (
                <div>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '0 0 12px' }}>
                    从用例库中选择要执行的用例，已选 <strong>{newPlan.selectedCases.length}</strong> 个
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {MOCK_CASES.map(tc => {
                      const sel = newPlan.selectedCases.includes(tc.id);
                      return (
                        <label key={tc.id} onClick={() => toggleSelectCase(tc.id)} style={{
                          display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px',
                          borderRadius: 8, cursor: 'pointer', border: sel ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                          background: sel ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)' : 'var(--bg-primary)',
                          transition: 'all 0.1s',
                        }}>
                          <input type="checkbox" checked={sel} onChange={() => {}} style={{ accentColor: 'var(--accent-primary)' }} />
                          <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-tertiary)', minWidth: 60 }}>{tc.id}</span>
                          <span style={{ flex: 1, fontSize: 13, fontWeight: sel ? 600 : 400 }}>{tc.title}</span>
                          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6,
                            background: tc.type === 'auto' ? 'rgba(57,208,214,0.15)' : 'rgba(163,113,247,0.15)',
                            color: tc.type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600,
                          }}>
                            {tc.type === 'auto' ? '⚡ 自动化' : '📋 手动'}
                          </span>
                          <span style={{ fontSize: 11, color: PRIORITY_COLORS[tc.priority], fontWeight: 600 }}>{tc.priority}</span>
                          <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{tc.duration}min</span>
                          <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{MOCK_COMPONENTS.find(c => c.id === tc.component)?.name}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Step 3: Assign components & people */}
              {wizardStep === 3 && (
                <div>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '0 0 12px' }}>
                    为已选用例分配组件和执行人
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
                          <select className="form-input form-select" style={{ width: 140, fontSize: 12 }} value={newPlan.assignments[cid]?.component || tc.component}
                            onChange={e => setAssignment(cid, 'component', e.target.value)}>
                            {MOCK_COMPONENTS.map(comp => <option key={comp.id} value={comp.id}>{comp.name}</option>)}
                          </select>
                          <select className="form-input form-select" style={{ width: 100, fontSize: 12 }} value={newPlan.assignments[cid]?.assignee || ''}
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
                    <input type="datetime-local" className="form-input" value={newPlan.triggerAt} onChange={e => setNewPlan(p => ({ ...p, triggerAt: e.target.value }))} style={{ width: 280 }} />
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
                <button className="btn btn--primary" onClick={handleCreatePlan} disabled={newPlan.selectedCases.length === 0}>
                  ✓ 创建计划
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
//  Board View
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
  plan: MockPlan; caseMap: Map<string, MockCase>; userMap: Map<string, MockUser>;
  onStatusChange: (planId: string, caseId: string, status: string) => void;
  onDispatch: (caseId: string) => void;
}> = ({ plan, caseMap, userMap, onStatusChange, onDispatch }) => {
  // Group cases by component
  const componentGroups = useMemo(() => {
    const groups = new Map<string, MockPlanCase[]>();
    for (const pc of plan.cases) {
      const tc = caseMap.get(pc.caseId);
      const comp = tc?.component || 'other';
      if (!groups.has(comp)) groups.set(comp, []);
      groups.get(comp)!.push(pc);
    }
    return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [plan.cases, caseMap]);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Plan meta bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 12, flexShrink: 0, padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: 10, border: '1px solid var(--border-subtle)' }}>
        <span style={{ fontSize: 15, fontWeight: 600 }}>{plan.title}</span>
        <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{plan.startDate} → {plan.endDate}</span>
        <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>⏰ 触发: {plan.triggerAt}</span>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>进度 {plan.progress}%</span>
      </div>

      {/* Kanban board */}
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', gap: 12, minHeight: 0 }}>
        {componentGroups.map(([compId, cases]) => {
          const compName = [...MOCK_COMPONENTS, { id: 'other', name: '其他' }].find(c => c.id === compId)?.name || compId;
          return (
            <div key={compId} style={{ minWidth: 260, maxWidth: 300, display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
              {/* Component header */}
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', padding: '6px 10px', marginBottom: 6, display: 'flex', justifyContent: 'space-between' }}>
                <span>{compName}</span>
                <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{cases.length}</span>
              </div>
              {/* Column */}
              <div style={{ flex: 1, background: 'var(--bg-secondary)', borderRadius: 10, padding: 8, display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto' }}>
                {cases.map(pc => {
                  const tc = caseMap.get(pc.caseId);
                  if (!tc) return null;
                  return (
                    <div key={pc.caseId} style={{
                      background: STATUS_BG[pc.status], borderRadius: 8, padding: '10px 12px',
                      border: STATUS_BORDER[pc.status], cursor: 'pointer', transition: 'all 0.1s',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{tc.id}</span>
                        <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4,
                          background: tc.type === 'auto' ? 'rgba(57,208,214,0.15)' : 'rgba(163,113,247,0.15)',
                          color: tc.type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600,
                        }}>{tc.type === 'auto' ? '⚡' : '📋'}</span>
                      </div>
                      <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 6, lineHeight: 1.4 }}>{tc.title}</div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: 10, color: PRIORITY_COLORS[tc.priority], fontWeight: 600 }}>{tc.priority}</span>
                        {pc.assignee && <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>{userMap.get(pc.assignee)?.name || pc.assignee}</span>}
                      </div>
                      {/* Quick status buttons */}
                      <div style={{ display: 'flex', gap: 2, marginTop: 6 }}>
                        {COL_STATUS.map(s => (
                          <button key={s.key} onClick={e => { e.stopPropagation(); onStatusChange(plan.id, pc.caseId, s.key); }} style={{
                            flex: 1, padding: '3px 0', fontSize: 9, border: 'none', borderRadius: 4, cursor: 'pointer',
                            background: pc.status === s.key ? s.color : 'var(--surface-tertiary)',
                            color: pc.status === s.key ? '#fff' : 'var(--text-tertiary)',
                            fontWeight: pc.status === s.key ? 600 : 400, transition: 'all 0.1s',
                          }}>{s.label}</button>
                        ))}
                        {tc.type === 'auto' && (
                          <button onClick={e => { e.stopPropagation(); onDispatch(pc.caseId); }} style={{
                            padding: '3px 8px', fontSize: 9, border: 'none', borderRadius: 4, cursor: 'pointer',
                            background: 'rgba(57,208,214,0.15)', color: '#39d0d6', fontWeight: 600, whiteSpace: 'nowrap',
                          }}>▶ 下发</button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════
//  List View
// ═══════════════════════════════════════════════════════════════════

const ListView: React.FC<{
  plan: MockPlan; caseMap: Map<string, MockCase>; userMap: Map<string, MockUser>;
  onStatusChange: (planId: string, caseId: string, status: string) => void;
  onDispatch: (caseId: string) => void;
}> = ({ plan, caseMap, userMap, onStatusChange, onDispatch }) => {
  return (
    <div style={{ flex: 1, overflow: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: 'var(--surface-secondary)' }}>
            <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11 }}>用例</th>
            <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11 }}>类型</th>
            <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11 }}>组件</th>
            <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11 }}>优先级</th>
            <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11 }}>执行人</th>
            <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11 }}>状态</th>
            <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11 }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {plan.cases.map(pc => {
            const tc = caseMap.get(pc.caseId);
            if (!tc) return null;
            return (
              <tr key={pc.caseId} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td style={{ padding: '8px 14px' }}><span style={{ fontWeight: 500 }}>{tc.title}</span><br /><span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-tertiary)' }}>{tc.id}</span></td>
                <td style={{ padding: '8px 14px' }}>
                  <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6,
                    background: tc.type === 'auto' ? 'rgba(57,208,214,0.15)' : 'rgba(163,113,247,0.15)',
                    color: tc.type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600,
                  }}>{tc.type === 'auto' ? '⚡ 自动化' : '📋 手动'}</span>
                </td>
                <td style={{ padding: '8px 14px', color: 'var(--text-secondary)' }}>{MOCK_COMPONENTS.find(c => c.id === tc.component)?.name}</td>
                <td style={{ padding: '8px 14px', color: PRIORITY_COLORS[tc.priority], fontWeight: 600 }}>{tc.priority}</td>
                <td style={{ padding: '8px 14px', color: 'var(--text-secondary)' }}>{pc.assignee ? (userMap.get(pc.assignee)?.name || pc.assignee) : '-'}</td>
                <td style={{ padding: '8px 14px' }}>
                  <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 10,
                    background: pc.status === 'done' ? 'rgba(63,185,80,0.15)' : pc.status === 'running' ? 'rgba(88,166,255,0.15)' : pc.status === 'fail' ? 'rgba(248,81,73,0.15)' : 'rgba(139,148,158,0.1)',
                    color: pc.status === 'done' ? '#3fb950' : pc.status === 'running' ? '#58a6ff' : pc.status === 'fail' ? '#f85149' : '#8b949e',
                    fontWeight: 600,
                  }}>
                    {pc.status === 'done' ? '✓ 已完成' : pc.status === 'running' ? '▶ 执行中' : pc.status === 'fail' ? '✗ 失败' : '○ 待执行'}
                  </span>
                </td>
                <td style={{ padding: '8px 14px' }}>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <select className="form-input form-select" style={{ width: 90, fontSize: 11 }} value={pc.status} onChange={e => onStatusChange(plan.id, pc.caseId, e.target.value)}>
                      <option value="pending">待执行</option>
                      <option value="running">执行中</option>
                      <option value="done">已完成</option>
                      <option value="fail">失败</option>
                    </select>
                    {tc.type === 'auto' && (
                      <button onClick={() => onDispatch(pc.caseId)} style={{
                        padding: '4px 10px', fontSize: 10, border: 'none', borderRadius: 4, cursor: 'pointer',
                        background: 'rgba(57,208,214,0.15)', color: '#39d0d6', fontWeight: 600, whiteSpace: 'nowrap',
                      }}>▶ 下发</button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default TestExecutionPlan;
