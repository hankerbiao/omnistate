/**
 * AddCasesModal - 添加用例弹窗
 */
import { useMemo, useState } from 'react';
import type { AddCasesModalProps } from './types';

export default function AddCasesModal({ editingItems, selectedAddCaseIds, onToggle, onClose, onConfirm, cases, users }: AddCasesModalProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [assigneeId, setAssigneeId] = useState('');
  const editingCaseIds = useMemo(() => new Set(editingItems.map((e) => e.case_id)), [editingItems]);

  const goToAssignStep = () => {
    if (selectedAddCaseIds.length > 0) setStep(2);
  };

  const handleConfirm = () => {
    if (assigneeId && selectedAddCaseIds.length > 0) {
      onConfirm();
      setStep(1);
      setAssigneeId('');
    }
  };

  const handleClose = () => {
    setStep(1);
    setAssigneeId('');
    onClose();
  };

  const caseList = Object.values(cases);

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ background: 'var(--bg-elevated)', borderRadius: 12, width: 520, maxWidth: '94vw', maxHeight: '70vh', display: 'flex', flexDirection: 'column', boxShadow: '0 25px 60px rgba(0,0,0,0.3)', border: '1px solid var(--border-default)' }}>
        {/* Header */}
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 14, fontWeight: 600 }}>{step === 1 ? '添加测试用例' : '指派执行人'}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 8, background: step === 1 ? 'var(--accent-primary)' : 'rgba(63,185,80,0.12)', color: step === 1 ? '#fff' : '#3fb950', fontWeight: 600 }}>1. 选用例</span>
              <span style={{ fontSize: 10, color: 'var(--text-tertiary)' }}>→</span>
              <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 8, background: step === 2 ? 'var(--accent-primary)' : 'var(--surface-tertiary)', color: step === 2 ? '#fff' : 'var(--text-tertiary)', fontWeight: step === 2 ? 600 : 400 }}>2. 指派</span>
            </div>
          </div>
          <button onClick={handleClose} style={{ fontSize: 20, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}>x</button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '10px 18px' }}>
          {step === 1 ? (
            <>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 12 }}>
                已选择 <strong style={{ color: 'var(--accent-primary)' }}>{selectedAddCaseIds.length}</strong> 个用例
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {caseList.map((tc) => {
                  const alreadyInPlan = editingCaseIds.has(tc.case_id);
                  const selected = selectedAddCaseIds.includes(tc.case_id);
                  return (
                    <label
                      key={tc.case_id}
                      onClick={() => { if (!alreadyInPlan) onToggle(tc.case_id); }}
                      style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', borderRadius: 6, cursor: alreadyInPlan ? 'not-allowed' : 'pointer', opacity: alreadyInPlan ? 0.5 : 1, border: selected ? '1.5px solid var(--accent-primary)' : '1px solid var(--border-subtle)', background: selected ? 'color-mix(in srgb, var(--accent-primary) 5%, transparent)' : 'var(--bg-primary)' }}
                    >
                      <input type="checkbox" checked={selected || alreadyInPlan} disabled={alreadyInPlan} onChange={() => {}} style={{ accentColor: 'var(--accent-primary)' }} />
                      <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text-tertiary)', minWidth: 50 }}>{tc.case_id}</span>
                      <span style={{ flex: 1, fontSize: 12 }}>{tc.title}</span>
                      <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, background: tc.type === 'auto' ? 'rgba(57,208,214,0.12)' : 'rgba(163,113,247,0.12)', color: tc.type === 'auto' ? '#39d0d6' : '#a371f7', fontWeight: 600 }}>{tc.type === 'auto' ? 'AUTO' : 'MANUAL'}</span>
                      {alreadyInPlan && <span style={{ fontSize: 9, color: 'var(--text-tertiary)' }}>已在计划中</span>}
                    </label>
                  );
                })}
              </div>
            </>
          ) : (
            <>
              <div style={{ background: 'var(--surface-primary)', borderRadius: 8, padding: '12px 14px', marginBottom: 16, border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 6 }}>即将添加的用例</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{selectedAddCaseIds.length} 个用例</div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>请为这些用例指定执行人</div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 8 }}>
                  选择执行人 <span style={{ color: 'var(--status-error)' }}>*</span>
                </label>
                <select className="form-input form-select" value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)} style={{ width: '100%', fontSize: 13, padding: '8px 12px' }}>
                  <option value="">请选择执行人</option>
                  {users.map((u) => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
                </select>
                {!assigneeId && <div style={{ fontSize: 11, color: 'var(--status-warn)', marginTop: 6 }}>必须指定执行人才能添加用例</div>}
              </div>

              <div style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid var(--border-subtle)', borderRadius: 6 }}>
                {caseList.filter((tc) => selectedAddCaseIds.includes(tc.case_id)).map((tc) => (
                  <div key={tc.case_id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', borderBottom: '1px solid var(--border-subtle)', fontSize: 11 }}>
                    <span style={{ fontFamily: 'monospace', color: 'var(--text-tertiary)', minWidth: 50 }}>{tc.case_id}</span>
                    <span style={{ flex: 1 }}>{tc.title}</span>
                    <span style={{ fontSize: 9, padding: '1px 4px', borderRadius: 3, background: tc.type === 'auto' ? 'rgba(57,208,214,0.12)' : 'rgba(163,113,247,0.12)', color: tc.type === 'auto' ? '#39d0d6' : '#a371f7' }}>{tc.type === 'auto' ? 'AUTO' : 'MANUAL'}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: '10px 18px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end', gap: 6 }}>
          {step === 1 ? (
            <>
              <button className="btn btn--ghost btn--sm" onClick={handleClose} style={{ fontSize: 12 }}>取消</button>
              <button className="btn btn--primary btn--sm" onClick={goToAssignStep} disabled={selectedAddCaseIds.length === 0} style={{ fontSize: 12 }}>下一步：指派执行人 →</button>
            </>
          ) : (
            <>
              <button className="btn btn--ghost btn--sm" onClick={() => setStep(1)} style={{ fontSize: 12 }}>← 返回</button>
              <button className="btn btn--primary btn--sm" onClick={handleConfirm} disabled={!assigneeId} style={{ fontSize: 12 }}>确认添加 ({selectedAddCaseIds.length} 个)</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}