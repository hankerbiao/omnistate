/**
 * 用例治理页面
 * 用于发现和补全不完整的测试用例（缺Lab/目录/Tag/未关联自动化用例）
 */

import React, { useState, useCallback, useMemo } from 'react';
import { api } from '../services/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  TestCaseResponse,
  AutomationTestCaseResponse,
  GovernanceStats,
  BatchUpdateCasesRequest,
  CatalogLab,
} from '../types';

// ═══════════════════════════════════════════════════════════════════════
//  类型 & 常量
// ═══════════════════════════════════════════════════════════════════════

type MissingFieldKey = 'lab_id' | 'catalog_path' | 'tags' | 'auto_link';

const MISSING_LABELS: Record<MissingFieldKey, string> = {
  lab_id: '缺 Lab',
  catalog_path: '缺目录',
  tags: '缺 Tag',
  auto_link: '未关联自动化',
};

const STAT_COLORS: Record<string, string> = {
  total_manual: '#58a6ff',
  total_auto: '#3fb950',
  missing_lab: '#f0883e',
  missing_catalog: '#d29922',
  missing_tags: '#bc8cff',
  unlinked_auto: '#f85149',
};

// ═══════════════════════════════════════════════════════════════════════
//  主组件
// ═══════════════════════════════════════════════════════════════════════

const CaseGovernancePage: React.FC = () => {
  const qc = useQueryClient();

  // ── 筛选状态 ──
  const [search, setSearch] = useState('');
  const [activeMissing, setActiveMissing] = useState<MissingFieldKey | null>(null);
  const [page, setPage] = useState(0);
  const pageSize = 50;

  // ── 批量选择 ──
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // ── 批量操作面板 ──
  const [batchLabId, setBatchLabId] = useState('');
  const [batchCatalogPath, setBatchCatalogPath] = useState('');
  const [batchTagInput, setBatchTagInput] = useState('');
  const [batchTagMode, setBatchTagMode] = useState<'add' | 'remove'>('add');

  // ── 关联弹窗 ──
  const [linkModalCase, setLinkModalCase] = useState<TestCaseResponse | null>(null);
  const [linkSearch, setLinkSearch] = useState('');

  // ═══════════════════════════════════════════════════════════════════
  //  数据查询
  // ═══════════════════════════════════════════════════════════════════

  const statsQuery = useQuery({
    queryKey: ['governance-stats'],
    queryFn: () => api.getGovernanceStats().then(r => r.data),
  });

  const listParams = useMemo(() => ({
    missing_fields: activeMissing || undefined,
    limit: pageSize,
    offset: page * pageSize,
  }), [activeMissing, page]);

  const casesQuery = useQuery({
    queryKey: ['governance-cases', listParams],
    queryFn: () => api.listTestCases(listParams).then(r => r.data),
  });

  const labsQuery = useQuery({
    queryKey: ['labs'],
    queryFn: () => api.listLabs({ active_only: true }).then(r => r.data),
  });

  // 关联弹窗：查找可关联的自动用例
  const autoCasesQuery = useQuery({
    queryKey: ['auto-cases-for-link', linkSearch],
    queryFn: () => api.listAutomationTestCases({ limit: 30 }).then(r => r.data),
    enabled: !!linkModalCase,
  });

  // ═══════════════════════════════════════════════════════════════════
  //  Mutations
  // ═══════════════════════════════════════════════════════════════════

  const batchMutation = useMutation({
    mutationFn: (req: BatchUpdateCasesRequest) => api.batchUpdateCases(req).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['governance-stats'] });
      qc.invalidateQueries({ queryKey: ['governance-cases'] });
      setSelectedIds(new Set());
      setBatchLabId('');
      setBatchCatalogPath('');
      setBatchTagInput('');
    },
  });

  const unlinkMutation = useMutation({
    mutationFn: (caseId: string) => api.unlinkAutomationCase(caseId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['governance-stats'] });
      qc.invalidateQueries({ queryKey: ['governance-cases'] });
    },
  });

  const linkMutation = useMutation({
    mutationFn: ({ caseId, autoCaseId }: { caseId: string; autoCaseId: string }) =>
      api.linkAutomationCase(caseId, { auto_case_id: autoCaseId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['governance-stats'] });
      qc.invalidateQueries({ queryKey: ['governance-cases'] });
      setLinkModalCase(null);
    },
  });

  // ═══════════════════════════════════════════════════════════════════
  //  事件处理
  // ═══════════════════════════════════════════════════════════════════

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    if (!casesQuery.data) return;
    const allIds = casesQuery.data.map(c => c.case_id);
    const allSelected = allIds.every(id => selectedIds.has(id));
    setSelectedIds(allSelected ? new Set() : new Set(allIds));
  }, [casesQuery.data, selectedIds]);

  const handleBatchApply = useCallback(() => {
    if (selectedIds.size === 0) return;
    const req: BatchUpdateCasesRequest = { case_ids: [...selectedIds] };
    if (batchLabId) req.lab_id = batchLabId;
    if (batchCatalogPath) req.catalog_path = batchCatalogPath.split('/').filter(Boolean);
    const tags = batchTagInput.split(',').map(t => t.trim()).filter(Boolean);
    if (tags.length > 0) {
      if (batchTagMode === 'add') req.tags_add = tags;
      else req.tags_remove = tags;
    }
    batchMutation.mutate(req);
  }, [selectedIds, batchLabId, batchCatalogPath, batchTagInput, batchTagMode, batchMutation]);

  // ═══════════════════════════════════════════════════════════════════
  //  渲染
  // ═══════════════════════════════════════════════════════════════════

  const stats = statsQuery.data;
  const cases = casesQuery.data ?? [];
  const labs = (labsQuery.data ?? []) as CatalogLab[];

  // 搜索过滤（客户端）
  const filteredCases = search
    ? cases.filter(c => c.title?.toLowerCase().includes(search.toLowerCase()) || c.case_id.toLowerCase().includes(search.toLowerCase()))
    : cases;

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      {/* ── 页头 ── */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-primary, #1f2937)', marginBottom: 4 }}>
          用例治理
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-secondary, #6b7280)' }}>
          发现并补全不完整的测试用例，管理手工与自动化用例关联
        </p>
      </div>

      {/* ── 统计卡片 ── */}
      <StatsBar stats={stats} isLoading={statsQuery.isLoading} activeMissing={activeMissing} onMissingClick={setActiveMissing} />

      {/* ── 筛选栏 ── */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder="搜索用例 ID / 标题..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            padding: '6px 12px', borderRadius: 6, border: '1px solid var(--border-default, #d1d5db)',
            fontSize: 13, width: 240, background: 'var(--bg-primary, #fff)',
          }}
        />
        {activeMissing && (
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 4,
            padding: '4px 10px', borderRadius: 12, fontSize: 12,
            background: STAT_COLORS[`missing_${activeMissing}`] + '20',
            color: STAT_COLORS[`missing_${activeMissing}`],
          }}>
            {MISSING_LABELS[activeMissing]}
            <button onClick={() => setActiveMissing(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: 14 }}>×</button>
          </span>
        )}
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-secondary, #6b7280)' }}>
          共 {filteredCases.length} 条
        </span>
      </div>

      {/* ── 用例表格 ── */}
      <div style={{
        border: '1px solid var(--border-default, #d1d5db)', borderRadius: 8,
        overflow: 'hidden', marginBottom: selectedIds.size > 0 ? 100 : 0,
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: 'var(--bg-secondary, #f9fafb)' }}>
              <th style={thStyle}><input type="checkbox" checked={filteredCases.length > 0 && filteredCases.every(c => selectedIds.has(c.case_id))} onChange={toggleSelectAll} /></th>
              <th style={thStyle}>ID</th>
              <th style={{ ...thStyle, textAlign: 'left' }}>标题</th>
              <th style={thStyle}>Lab</th>
              <th style={thStyle}>目录</th>
              <th style={thStyle}>Tag</th>
              <th style={thStyle}>自动关联</th>
              <th style={thStyle}>操作</th>
            </tr>
          </thead>
          <tbody>
            {casesQuery.isLoading ? (
              <tr><td colSpan={8} style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary, #6b7280)' }}>加载中...</td></tr>
            ) : filteredCases.length === 0 ? (
              <tr><td colSpan={8} style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary, #6b7280)' }}>暂无数据</td></tr>
            ) : filteredCases.map(c => (
              <CaseRow
                key={c.case_id}
                testCase={c}
                selected={selectedIds.has(c.case_id)}
                onToggle={() => toggleSelect(c.case_id)}
                onLink={() => setLinkModalCase(c)}
                onUnlink={() => unlinkMutation.mutate(c.case_id)}
                labs={labs}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* ── 分页 ── */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
        <button disabled={page === 0} onClick={() => setPage(p => p - 1)} style={pageBtnStyle}>上一页</button>
        <span style={{ fontSize: 13, lineHeight: '32px', color: 'var(--text-secondary, #6b7280)' }}>第 {page + 1} 页</span>
        <button disabled={cases.length < pageSize} onClick={() => setPage(p => p + 1)} style={pageBtnStyle}>下一页</button>
      </div>

      {/* ── 批量操作面板 ── */}
      {selectedIds.size > 0 && (
        <div style={{
          position: 'fixed', bottom: 0, left: 0, right: 0,
          background: 'var(--bg-primary, #fff)', borderTop: '1px solid var(--border-default, #d1d5db)',
          padding: '12px 24px', display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap',
          boxShadow: '0 -2px 8px rgba(0,0,0,0.08)', zIndex: 50,
        }}>
          <span style={{ fontSize: 13, fontWeight: 500 }}>已选 {selectedIds.size} 项</span>
          <select value={batchLabId} onChange={e => setBatchLabId(e.target.value)} style={inputStyle}>
            <option value="">设置 Lab...</option>
            {labs.map(l => <option key={l.lab_id} value={l.lab_id}>{l.name}</option>)}
          </select>
          <input
            type="text" placeholder="目录路径 (如: bios/boot)" value={batchCatalogPath}
            onChange={e => setBatchCatalogPath(e.target.value)} style={{ ...inputStyle, width: 160 }}
          />
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
            <select value={batchTagMode} onChange={e => setBatchTagMode(e.target.value as 'add' | 'remove')} style={{ ...inputStyle, width: 70 }}>
              <option value="add">添加</option>
              <option value="remove">移除</option>
            </select>
            <input
              type="text" placeholder="Tag (逗号分隔)" value={batchTagInput}
              onChange={e => setBatchTagInput(e.target.value)} style={{ ...inputStyle, width: 140 }}
            />
          </div>
          <button
            onClick={handleBatchApply}
            disabled={batchMutation.isPending}
            style={{
              padding: '6px 16px', borderRadius: 6, border: 'none',
              background: '#2563eb', color: '#fff', fontSize: 13, cursor: 'pointer',
              opacity: batchMutation.isPending ? 0.6 : 1,
            }}
          >
            {batchMutation.isPending ? '提交中...' : '应用'}
          </button>
          {batchMutation.data && (
            <span style={{ fontSize: 12, color: batchMutation.data.failed_count > 0 ? '#f0883e' : '#3fb950' }}>
              成功 {batchMutation.data.updated_count}{batchMutation.data.failed_count > 0 ? ` / 失败 ${batchMutation.data.failed_count}` : ''}
            </span>
          )}
        </div>
      )}

      {/* ── 关联弹窗 ── */}
      {linkModalCase && (
        <LinkModal
          testCase={linkModalCase}
          autoCases={autoCasesQuery.data ?? []}
          search={linkSearch}
          onSearchChange={setLinkSearch}
          onLink={autoCaseId => linkMutation.mutate({ caseId: linkModalCase.case_id, autoCaseId })}
          onClose={() => setLinkModalCase(null)}
          isLinking={linkMutation.isPending}
        />
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════
//  子组件
// ═══════════════════════════════════════════════════════════════════════

/** 统计卡片栏 */
const StatsBar: React.FC<{
  stats?: GovernanceStats;
  isLoading: boolean;
  activeMissing: MissingFieldKey | null;
  onMissingClick: (key: MissingFieldKey | null) => void;
}> = ({ stats, isLoading, activeMissing, onMissingClick }) => {
  const cards = stats ? [
    { key: 'total_manual' as const, label: '手工用例', value: stats.total_manual, clickable: false },
    { key: 'total_auto' as const, label: '自动用例', value: stats.total_auto, clickable: false },
    { key: 'missing_lab' as const, label: '缺 Lab', value: stats.missing_lab, clickable: true },
    { key: 'missing_catalog' as const, label: '缺目录', value: stats.missing_catalog, clickable: true },
    { key: 'missing_tags' as const, label: '缺 Tag', value: stats.missing_tags, clickable: true },
    { key: 'unlinked_auto' as const, label: '未关联自动化', value: stats.unlinked_auto, clickable: true },
  ] : [];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 20 }}>
      {isLoading ? (
        Array.from({ length: 6 }).map((_, i) => (
          <div key={i} style={{ ...statCardStyle, opacity: 0.5 }}>—</div>
        ))
      ) : cards.map(card => (
        <div
          key={card.key}
          onClick={() => card.clickable ? onMissingClick(activeMissing === card.key ? null : card.key) : undefined}
          style={{
            ...statCardStyle,
            cursor: card.clickable ? 'pointer' : 'default',
            border: activeMissing === card.key ? `2px solid ${STAT_COLORS[card.key]}` : '1px solid var(--border-default, #d1d5db)',
            borderColor: activeMissing === card.key ? STAT_COLORS[card.key] : undefined,
          }}
        >
          <div style={{ fontSize: 11, color: 'var(--text-secondary, #6b7280)', marginBottom: 4 }}>{card.label}</div>
          <div style={{ fontSize: 22, fontWeight: 600, color: STAT_COLORS[card.key] }}>{card.value}</div>
        </div>
      ))}
    </div>
  );
};

/** 用例行 */
const CaseRow: React.FC<{
  testCase: TestCaseResponse;
  selected: boolean;
  onToggle: () => void;
  onLink: () => void;
  onUnlink: () => void;
  labs: CatalogLab[];
}> = ({ testCase: c, selected, onToggle, onLink, onUnlink, labs }) => {
  const labName = labs.find(l => l.lab_id === c.lab_id)?.name || c.lab_name || '';
  const hasLab = !!c.lab_id;
  const hasCatalog = !!(c.catalog_path && c.catalog_path.length > 0);
  const hasTags = !!(c.tags && c.tags.length > 0);

  return (
    <tr style={{ borderBottom: '1px solid var(--border-default, #d1d5db)' }}>
      <td style={tdStyle}><input type="checkbox" checked={selected} onChange={onToggle} /></td>
      <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 12 }}>{c.case_id}</td>
      <td style={{ ...tdStyle, textAlign: 'left', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const }}>
        {c.title}
      </td>
      <td style={tdStyle}>
        <CompletenessDot ok={hasLab} />
        {hasLab ? <span style={{ fontSize: 12 }}>{labName}</span> : <span style={{ fontSize: 12, color: '#f0883e' }}>缺失</span>}
      </td>
      <td style={tdStyle}>
        <CompletenessDot ok={hasCatalog} />
        {hasCatalog ? <span style={{ fontSize: 12 }}>{c.catalog_path?.join(' / ')}</span> : <span style={{ fontSize: 12, color: '#d29922' }}>缺失</span>}
      </td>
      <td style={tdStyle}>
        <CompletenessDot ok={hasTags} />
        {hasTags ? (
          <span style={{ fontSize: 11 }}>
            {c.tags!.slice(0, 2).map(t => (
              <span key={t} style={{ display: 'inline-block', padding: '1px 6px', borderRadius: 8, background: '#bc8cff20', color: '#bc8cff', marginRight: 3 }}>{t}</span>
            ))}
            {c.tags!.length > 2 && <span style={{ color: 'var(--text-secondary, #6b7280)' }}>+{c.tags!.length - 2}</span>}
          </span>
        ) : <span style={{ fontSize: 12, color: '#bc8cff' }}>缺失</span>}
      </td>
      <td style={tdStyle}>
        <CompletenessDot ok={!!c.automation_case_ref} />
        <span style={{ fontSize: 12 }}>{c.automation_case_ref ? c.automation_case_ref.auto_case_id : '—'}</span>
      </td>
      <td style={tdStyle}>
        {!c.automation_case_ref ? (
          <button onClick={onLink} style={actionBtnStyle}>关联</button>
        ) : (
          <button onClick={onUnlink} style={{ ...actionBtnStyle, color: '#f85149' }}>取消关联</button>
        )}
      </td>
    </tr>
  );
};

/** 完整性指示点 */
const CompletenessDot: React.FC<{ ok: boolean }> = ({ ok }) => (
  <span style={{
    display: 'inline-block', width: 7, height: 7, borderRadius: '50%',
    background: ok ? '#3fb950' : '#f85149', marginRight: 6, verticalAlign: 'middle',
  }} />
);

/** 关联弹窗 */
const LinkModal: React.FC<{
  testCase: TestCaseResponse;
  autoCases: AutomationTestCaseResponse[];
  search: string;
  onSearchChange: (v: string) => void;
  onLink: (autoCaseId: string) => void;
  onClose: () => void;
  isLinking: boolean;
}> = ({ testCase, autoCases, search, onSearchChange, onLink, onClose, isLinking }) => {
  const filtered = search
    ? autoCases.filter(a => a.name?.toLowerCase().includes(search.toLowerCase()) || a.auto_case_id.toLowerCase().includes(search.toLowerCase()))
    : autoCases;

  // 只显示未关联或关联到当前用例的自动用例
  const linkable = filtered.filter(a => !a.dml_manual_case_id || a.dml_manual_case_id === testCase.case_id);

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
         onClick={onClose}>
      <div style={{
        background: 'var(--bg-primary, #fff)', borderRadius: 12, padding: 24, width: 520, maxHeight: '80vh', overflow: 'auto',
        boxShadow: '0 8px 30px rgba(0,0,0,0.12)',
      }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>关联自动化用例</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18 }}>×</button>
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-secondary, #6b7280)', marginBottom: 12 }}>
          为 <strong>{testCase.case_id}</strong> 选择要关联的自动化用例
        </p>
        <input
          type="text" placeholder="搜索自动用例..." value={search}
          onChange={e => onSearchChange(e.target.value)}
          style={{ ...inputStyle, width: '100%', marginBottom: 12 }}
        />
        <div style={{ maxHeight: 320, overflow: 'auto' }}>
          {linkable.length === 0 ? (
            <p style={{ textAlign: 'center', color: 'var(--text-secondary, #6b7280)', padding: 20 }}>无可关联的自动用例</p>
          ) : linkable.map(a => (
            <div key={a.auto_case_id} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '8px 12px', borderBottom: '1px solid var(--border-default, #d1d5db)',
            }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{a.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary, #6b7280)' }}>{a.auto_case_id} · {a.framework}</div>
              </div>
              <button
                onClick={() => onLink(a.auto_case_id)}
                disabled={isLinking}
                style={{ ...actionBtnStyle, opacity: isLinking ? 0.5 : 1 }}
              >
                关联
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════
//  样式常量
// ═══════════════════════════════════════════════════════════════════════

const thStyle: React.CSSProperties = {
  padding: '8px 12px', textAlign: 'center', fontSize: 12, fontWeight: 500,
  color: 'var(--text-secondary, #6b7280)', borderBottom: '1px solid var(--border-default, #d1d5db)',
};

const tdStyle: React.CSSProperties = {
  padding: '8px 12px', textAlign: 'center', fontSize: 13,
  borderBottom: '1px solid var(--border-default, #d1d5db)',
};

const statCardStyle: React.CSSProperties = {
  padding: '14px 16px', borderRadius: 8, background: 'var(--bg-primary, #fff)',
  border: '1px solid var(--border-default, #d1d5db)',
};

const inputStyle: React.CSSProperties = {
  padding: '6px 10px', borderRadius: 6, border: '1px solid var(--border-default, #d1d5db)',
  fontSize: 13, background: 'var(--bg-primary, #fff)',
};

const actionBtnStyle: React.CSSProperties = {
  padding: '3px 10px', borderRadius: 4, border: '1px solid var(--border-default, #d1d5db)',
  background: 'var(--bg-primary, #fff)', fontSize: 12, cursor: 'pointer', color: '#2563eb',
};

const pageBtnStyle: React.CSSProperties = {
  padding: '4px 12px', borderRadius: 6, border: '1px solid var(--border-default, #d1d5db)',
  background: 'var(--bg-primary, #fff)', fontSize: 13, cursor: 'pointer',
};

export default CaseGovernancePage;
