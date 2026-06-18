/**
 * CreatePlanWizard - 新建计划向导
 */
import DateRangePicker from './DateRangePicker';
import type { CreatePlanWizardProps } from './types';

const PRIORITY_COLORS: Record<string, string> = {
  P0: '#f85149', P1: '#d29922', P2: '#58a6ff', P3: '#8b949e',
};

export default function CreatePlanWizard({
  wizardStep, onStepChange, newPlan, onNewPlanChange, caseSearch, onCaseSearchChange,
  submittingPlan, onCreatePlan, onClose, onToggleCase, onToggleCollection, onSetAssignment,
  users, collections, caseMap, casesLoading, currentUserId,
}: CreatePlanWizardProps) {
  const stepLabels = ['基本信息', '选择用例', '分配执行人', '排期确认'];
  const q = caseSearch.trim().toLowerCase();
  const matchedCollections = q
    ? collections.filter((col) => col.name?.toLowerCase().includes(q) || (col.description || '').toLowerCase().includes(q))
    : collections;
  const allCases = Array.from(caseMap.values());
  const matchedCases = q ? allCases.filter((tc) => tc.id.includes(q) || tc.title.toLowerCase().includes(q)) : allCases;

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ background: 'var(--bg-elevated)', borderRadius: 12, width: 680, maxWidth: '94vw', maxHeight: '88vh', display: 'flex', flexDirection: 'column', boxShadow: '0 25px 80px rgba(0,0,0,0.35)', border: '1px solid var(--border-default)' }}>
        {/* Header */}
        <div style={{ padding: '16px 22px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>新建执行计划</div>
            <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
              {stepLabels.map((s, i) => (
                <span key={i} style={{ fontSize: 11, padding: '2px 10px', borderRadius: 8, background: wizardStep === i + 1 ? 'var(--accent-primary)' : wizardStep > i + 1 ? 'rgba(63,185,80,0.12)' : 'var(--surface-tertiary)', color: wizardStep === i + 1 ? '#fff' : wizardStep > i + 1 ? '#3fb950' : 'var(--text-tertiary)', fontWeight: wizardStep === i + 1 ? 600 : 400, display: 'flex', alignItems: 'center', gap: 4 }}>
                  {wizardStep > i + 1 ? <span style={{ fontSize: 10 }}>v</span> : <span>{i + 1}</span>}
                  <span>{s}</span>
                </span>
              ))}
            </div>
          </div>
          <button onClick={onClose} style={{ fontSize: 22, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}>x</button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '18px 22px' }}>
          {wizardStep === 1 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>计划名称 *</label>
                <input className="form-input" value={newPlan.title} onChange={(e) => onNewPlanChange({ ...newPlan, title: e.target.value })} placeholder="例如: Sprint 3 安全回归" style={{ width: '100%' }} autoFocus />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>描述</label>
                <textarea className="form-input" value={newPlan.description} onChange={(e) => onNewPlanChange({ ...newPlan, description: e.target.value })} placeholder="计划的目的、范围、备注..." rows={3} style={{ width: '100%', resize: 'vertical' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>计划周期</label>
                <DateRangePicker startDate={newPlan.startDate} endDate={newPlan.endDate} onChange={(start, end) => onNewPlanChange({ ...newPlan, startDate: start, endDate: end })} />
              </div>
            </div>
          )}

          {wizardStep === 2 && (
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                已选 <strong>{newPlan.selectedCases.length}</strong> 个用例
              </div>
              <input className="form-input" value={caseSearch} onChange={(e) => onCaseSearchChange(e.target.value)} placeholder="搜索用例名称、ID 或预置用例集..." style={{ width: '100%', fontSize: 12, padding: '6px 10px', marginBottom: 10, boxSizing: 'border-box' }} />
              {casesLoading ? (
                <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>加载用例中...</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {matchedCollections.map((col) => (
                    <label key={col.collection_id} onClick={() => onToggleCollection(col)} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', borderRadius: 6, cursor: 'pointer', border: '1px solid var(--border-subtle)', background: 'var(--bg-primary)', marginBottom: 2 }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 12, fontWeight: 500 }}>{col.name}</div>
                        {col.description && <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 1 }}>{col.description}</div>}
                      </div>
                      <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>{(col.case_count || 0)} 个用例</span>
                    </label>
                  ))}
                  {matchedCases.map((tc) => {
                    const sel = newPlan.selectedCases.includes(tc.id);
                    return (
                      <label key={tc.id} onClick={() => onToggleCase(tc.id)} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', borderRadius: 6, cursor: 'pointer', border: sel ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)', background: sel ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)' : 'var(--bg-primary)' }}>
                        <input type="checkbox" checked={sel} onChange={() => {}} style={{ accentColor: 'var(--accent-primary)' }} />
                        <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)', minWidth: 50 }}>{tc.id}</span>
                        <span style={{ flex: 1, fontSize: 12, fontWeight: sel ? 600 : 400 }}>{tc.title}</span>
                        <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: tc.type === 'auto' ? 'rgba(57,208,214,0.12)' : 'rgba(163,113,247,0.12)', color: tc.type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600 }}>{tc.type === 'auto' ? 'AUTO' : 'MANUAL'}</span>
                        {tc.priority && <span style={{ fontSize: 10, color: PRIORITY_COLORS[tc.priority] || '#8b949e', fontWeight: 600 }}>{tc.priority}</span>}
                      </label>
                    );
                  })}
                  {matchedCollections.length === 0 && matchedCases.length === 0 && (
                    <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>无匹配的用例或集合</div>
                  )}
                </div>
              )}
            </div>
          )}

          {wizardStep === 3 && (
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>为已选用例分配执行人</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {newPlan.selectedCases.map((cid) => {
                  const tc = caseMap.get(cid);
                  if (!tc) return null;
                  return (
                    <div key={cid} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', background: 'var(--bg-secondary)', borderRadius: 6, border: '1px solid var(--border-subtle)' }}>
                      <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)', minWidth: 50 }}>{cid}</span>
                      <span style={{ flex: 1, fontSize: 12, fontWeight: 500 }}>{tc.title}</span>
                      <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: tc.type === 'auto' ? 'rgba(57,208,214,0.12)' : 'rgba(163,113,247,0.12)', color: tc.type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600 }}>{tc.type === 'auto' ? 'AUTO' : 'MANUAL'}</span>
                      <select className="form-input form-select" style={{ width: 120, fontSize: 11 }} value={newPlan.assignments[cid]?.assignee || currentUserId} onChange={(e) => onSetAssignment(cid, e.target.value)}>
                        {users.map((u) => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
                      </select>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {wizardStep === 4 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>自动触发时间</label>
                <input type="datetime-local" className="form-input" value={newPlan.triggerAt} onChange={(e) => onNewPlanChange({ ...newPlan, triggerAt: e.target.value })} style={{ width: 260 }} />
                <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 4 }}>到达设定时间后自动开始执行，留空为手动触发</div>
              </div>
              <div style={{ background: 'var(--bg-secondary)', borderRadius: 8, padding: 14, border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>计划概览</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 14px', fontSize: 12 }}>
                  <span style={{ color: 'var(--text-tertiary)' }}>名称</span><span style={{ fontWeight: 500 }}>{newPlan.title || '-'}</span>
                  <span style={{ color: 'var(--text-tertiary)' }}>周期</span><span>{newPlan.startDate || '-'} 至 {newPlan.endDate || '-'}</span>
                  <span style={{ color: 'var(--text-tertiary)' }}>触发方式</span><span>{newPlan.triggerAt || '手动触发'}</span>
                  <span style={{ color: 'var(--text-tertiary)' }}>用例数</span>
                  <span style={{ fontWeight: 600 }}>
                    {newPlan.selectedCases.length} 个（{newPlan.selectedCases.filter((c) => caseMap.get(c)?.type === 'auto').length} 自动 / {newPlan.selectedCases.filter((c) => caseMap.get(c)?.type === 'manual').length} 手动）
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 22px', borderTop: '1px solid var(--border-subtle)' }}>
          <button className="btn btn--secondary btn--sm" onClick={() => wizardStep > 1 ? onStepChange(wizardStep - 1) : onClose()} style={{ fontSize: 12 }}>
            {wizardStep > 1 ? '上一步' : '取消'}
          </button>
          {wizardStep < 4 ? (
            <button className="btn btn--primary btn--sm" onClick={() => onStepChange(wizardStep + 1)} disabled={wizardStep === 1 && !newPlan.title.trim()} style={{ fontSize: 12 }}>
              下一步
            </button>
          ) : (
            <button className="btn btn--primary btn--sm" onClick={onCreatePlan} disabled={newPlan.selectedCases.length === 0 || submittingPlan} style={{ fontSize: 12 }}>
              {submittingPlan ? '创建中...' : '创建计划'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}