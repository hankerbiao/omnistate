import { useState, useCallback } from 'react';
import type { TestCaseResponse } from '../types';
import { api } from '../services/api';
import { Dialog, DialogContent } from './ui/dialog';

interface Props {
  autoCaseId: string;
  onClose: () => void;
  onLinked: () => void;
}

export default function LinkManualCaseModal({ autoCaseId, onClose, onLinked }: Props) {
  const [manualCases, setManualCases] = useState<TestCaseResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [linking, setLinking] = useState(false);

  const handleOpen = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.listTestCases({ limit: 200 });
      setManualCases(res.data || []);
    } catch {
      setManualCases([]);
    }
    setLoading(false);
  }, []);

  // 首次渲染即加载数据
  useState(() => {
    handleOpen();
  });

  const handleLink = useCallback(async (caseId: string) => {
    setLinking(true);
    try {
      await api.linkAutomationCase(caseId, { auto_case_id: autoCaseId });
      onLinked();
    } catch (err) {
      alert('关联失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
    setLinking(false);
  }, [autoCaseId, onLinked]);

  const filtered = search
    ? manualCases.filter(c =>
        c.case_id.toLowerCase().includes(search.toLowerCase()) ||
        c.title?.toLowerCase().includes(search.toLowerCase())
      )
    : manualCases;

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-[520px]" style={{ padding: 24, maxHeight: '70vh', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>关联手工用例</h3>
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-secondary, #6b7280)', marginBottom: 12, marginTop: 0 }}>
          为 <strong>{autoCaseId}</strong> 选择要关联的手工测试用例
        </p>
        <input
          type="text" placeholder="搜索手工用例 ID 或标题..." value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            padding: '6px 12px', borderRadius: 6, border: '1px solid var(--border-default, #d1d5db)',
            fontSize: 13, marginBottom: 12, background: 'var(--bg-primary, #fff)',
          }}
        />
        <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary, #6b7280)', fontSize: 13 }}>加载中...</div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary, #6b7280)', fontSize: 13 }}>
              {search ? '没有匹配的手工用例' : '暂无可关联的手工用例'}
            </div>
          ) : (
            filtered.map(c => (
              <div key={c.case_id} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 12px', marginBottom: 6, borderRadius: 8,
                border: '1px solid var(--border-default, #d1d5db)',
                background: 'var(--bg-primary, #fff)',
                transition: 'border-color 0.12s, box-shadow 0.12s',
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = '#2563eb'; e.currentTarget.style.boxShadow = '0 1px 4px rgba(37,99,235,0.12)'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-default, #d1d5db)'; e.currentTarget.style.boxShadow = 'none'; }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary, #1f2937)', marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {c.title}
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 11, color: 'var(--text-secondary, #6b7280)', flexWrap: 'wrap' }}>
                    <span style={{ fontFamily: 'monospace' }}>{c.case_id}</span>
                    <span>· {c.status}</span>
                    {c.lab_name && <span>· {c.lab_name}</span>}
                  </div>
                </div>
                <button
                  onClick={() => handleLink(c.case_id)}
                  disabled={linking}
                  style={{
                    padding: '5px 14px', borderRadius: 6, border: 'none',
                    background: linking ? 'var(--bg-secondary, #f3f4f6)' : '#2563eb',
                    color: linking ? 'var(--text-secondary, #6b7280)' : '#fff',
                    fontSize: 12, fontWeight: 500, cursor: linking ? 'default' : 'pointer',
                    whiteSpace: 'nowrap', flexShrink: 0,
                  }}
                >
                  {linking ? '关联中...' : '关联'}
                </button>
              </div>
            ))
          )}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-tertiary, #9ca3af)', marginTop: 10, textAlign: 'center' }}>
          共 {manualCases.length} 个手工用例
        </div>
      </DialogContent>
    </Dialog>
  );
}
