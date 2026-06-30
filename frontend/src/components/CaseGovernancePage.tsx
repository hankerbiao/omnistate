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
  CatalogLab,
} from '../types';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Badge } from './ui/badge';

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

  // ── 复选框选择 ──
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

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
    queryKey: ['auto-cases-for-link'],
    queryFn: () => api.listAutomationTestCases({ limit: 30 }).then(r => r.data),
    enabled: !!linkModalCase,
  });

  // ═══════════════════════════════════════════════════════════════════
  //  Mutations
  // ═══════════════════════════════════════════════════════════════════

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
        overflow: 'hidden', marginBottom: 0,
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
                activeMissing={activeMissing}
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
  const cards: {
    key: string;
    label: string;
    value: number;
    clickable: boolean;
    missingKey?: MissingFieldKey;
  }[] = stats ? [
    { key: 'total_manual', label: '手工用例', value: stats.total_manual, clickable: false },
    { key: 'total_auto', label: '自动用例', value: stats.total_auto, clickable: false },
    { key: 'missing_lab', label: '缺 Lab', value: stats.missing_lab, clickable: true, missingKey: 'lab_id' },
    { key: 'missing_catalog', label: '缺目录', value: stats.missing_catalog, clickable: true, missingKey: 'catalog_path' },
    { key: 'missing_tags', label: '缺 Tag', value: stats.missing_tags, clickable: true, missingKey: 'tags' },
    { key: 'unlinked_auto', label: '未关联自动化', value: stats.unlinked_auto, clickable: true, missingKey: 'auto_link' },
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
          onClick={() => card.clickable && card.missingKey ? onMissingClick(activeMissing === card.missingKey ? null : card.missingKey) : undefined}
          style={{
            ...statCardStyle,
            cursor: card.clickable ? 'pointer' : 'default',
            border: card.clickable && card.missingKey && activeMissing === card.missingKey ? `2px solid ${STAT_COLORS[card.key]}` : '1px solid var(--border-default, #d1d5db)',
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
  activeMissing: MissingFieldKey | null;
}> = ({ testCase: c, selected, onToggle, onLink, onUnlink, labs, activeMissing }) => {
  const qc = useQueryClient();
  const labName = labs.find(l => l.lab_id === c.lab_id)?.name || c.lab_name || '';
  const hasLab = !!c.lab_id;
  const hasCatalog = !!(c.catalog_path && c.catalog_path.length > 0);
  const hasTags = !!(c.tags && c.tags.length > 0);

  // 行内编辑状态
  const [editing, setEditing] = useState<'lab_id' | 'catalog_path' | 'tags' | null>(null);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);

  const startEdit = (field: 'lab_id' | 'catalog_path' | 'tags') => {
    if (field === 'lab_id') {
      setEditing('lab_id');
      setEditValue(c.lab_id || '');
    } else if (field === 'catalog_path') {
      setEditing('catalog_path');
      setEditValue((c.catalog_path || []).join('/'));
    } else {
      setEditing('tags');
      setEditValue((c.tags || []).join(', '));
    }
  };

  const cancelEdit = () => {
    setEditing(null);
    setEditValue('');
  };

  const saveEdit = async () => {
    if (!editing) return;
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {};
      if (editing === 'lab_id') {
        payload.lab_id = editValue;
      } else if (editing === 'catalog_path') {
        payload.catalog_path = editValue.split('/').filter(Boolean);
      } else if (editing === 'tags') {
        payload.tags = editValue.split(',').map(t => t.trim()).filter(Boolean);
      }
      await api.updateTestCase(c.case_id, payload as any);
      qc.invalidateQueries({ queryKey: ['governance-stats'] });
      qc.invalidateQueries({ queryKey: ['governance-cases'] });
      cancelEdit();
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  // 渲染行内编辑控件
  const renderInlineEdit = () => {
    if (!editing) return null;

    const input = editing === 'lab_id' ? (
      <select
        className="form-input form-select"
        value={editValue}
        onChange={e => setEditValue(e.target.value)}
        style={{ width: 120, fontSize: 11, padding: '2px 4px' }}
        autoFocus
      >
        <option value="">选择 Lab...</option>
        {labs.map(l => <option key={l.lab_id} value={l.lab_id}>{l.name}</option>)}
      </select>
    ) : (
      <input
        type="text"
        value={editValue}
        onChange={e => setEditValue(e.target.value)}
        placeholder={editing === 'catalog_path' ? 'bios/boot' : 'tag1, tag2'}
        style={{ width: 100, fontSize: 11, padding: '2px 4px', border: '1px solid var(--border-default, #d1d5db)', borderRadius: 4 }}
        autoFocus
      />
    );

    return (
      <span style={{ display: 'inline-flex', gap: 3, alignItems: 'center' }}>
        {input}
        <button onClick={saveEdit} disabled={saving || !editValue.trim()} style={{ ...actionBtnStyle, fontSize: 11, padding: '2px 6px' }}>
          {saving ? '...' : '确定'}
        </button>
        <button onClick={cancelEdit} style={{ ...actionBtnStyle, fontSize: 11, padding: '2px 6px', color: '#8b949e' }}>取消</button>
      </span>
    );
  };

  // 根据当前筛选的缺失类型，渲染对应的操作按钮
  const renderAction = () => {
    if (editing) return renderInlineEdit();

    if (activeMissing === 'lab_id' && !hasLab) {
      return <button onClick={() => startEdit('lab_id')} style={actionBtnStyle}>设置 Lab</button>;
    }
    if (activeMissing === 'catalog_path' && !hasCatalog) {
      return <button onClick={() => startEdit('catalog_path')} style={actionBtnStyle}>设置目录</button>;
    }
    if (activeMissing === 'tags' && !hasTags) {
      return <button onClick={() => startEdit('tags')} style={actionBtnStyle}>添加 Tag</button>;
    }
    // 默认显示自动化关联/取消关联
    if (!c.automation_case_ref) {
      return <button onClick={onLink} style={actionBtnStyle}>关联</button>;
    }
    return <button onClick={onUnlink} style={{ ...actionBtnStyle, color: '#f85149' }}>取消关联</button>;
  };

  return (
    <tr style={{ borderBottom: '1px solid var(--border-default, #d1d5db)' }}>
      <td style={tdStyle}><input type="checkbox" checked={selected} onChange={onToggle} /></td>
      <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 12 }}>{c.case_id}</td>
      <td style={{ ...tdStyle, textAlign: 'left', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const }}>
        {c.title}
      </td>
      <td style={tdStyle}>
        <CompletenessDot ok={hasLab} />
        {hasLab ? <span style={{ fontSize: 12 }}>{labName}</span> : <span style={{ fontSize: 12, color: STAT_COLORS.missing_lab }}>缺失</span>}
      </td>
      <td style={tdStyle}>
        <CompletenessDot ok={hasCatalog} />
        {hasCatalog ? <span style={{ fontSize: 12 }}>{c.catalog_path?.join(' / ')}</span> : <span style={{ fontSize: 12, color: STAT_COLORS.missing_catalog }}>缺失</span>}
      </td>
      <td style={tdStyle}>
        <CompletenessDot ok={hasTags} />
        {hasTags ? (
          <span style={{ fontSize: 11 }}>
            {c.tags!.slice(0, 2).map(t => (
              <span key={t} style={{ display: 'inline-block', padding: '1px 6px', borderRadius: 8, background: `${STAT_COLORS.missing_tags}20`, color: STAT_COLORS.missing_tags, marginRight: 3 }}>{t}</span>
            ))}
            {c.tags!.length > 2 && <span style={{ color: 'var(--text-secondary, #6b7280)' }}>+{c.tags!.length - 2}</span>}
          </span>
        ) : <span style={{ fontSize: 12, color: STAT_COLORS.missing_tags }}>缺失</span>}
      </td>
      <td style={tdStyle}>
        <CompletenessDot ok={!!c.automation_case_ref} />
        <span style={{ fontSize: 12 }}>{c.automation_case_ref ? c.automation_case_ref.auto_case_id : '—'}</span>
      </td>
      <td style={tdStyle}>{renderAction()}</td>
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
  const [frameworkFilter, setFrameworkFilter] = useState('');

  // 提取所有框架选项
  const frameworkOptions = useMemo(() => {
    const set = new Set(autoCases.map(a => a.framework).filter(Boolean));
    return Array.from(set).sort();
  }, [autoCases]);

  // 搜索 + 框架筛选
  const filtered = useMemo(() => {
    let list = autoCases;
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(a => a.name?.toLowerCase().includes(q) || a.auto_case_id.toLowerCase().includes(q));
    }
    if (frameworkFilter) {
      list = list.filter(a => a.framework === frameworkFilter);
    }
    return list;
  }, [autoCases, search, frameworkFilter]);

  // 只显示未关联或关联到当前用例的自动用例
  const linkable = filtered.filter(a => !a.linked_manual_case_id || a.linked_manual_case_id === testCase.case_id);

  const STATUS_COLORS: Record<string, string> = {
    ACTIVE: '#3fb950', INACTIVE: '#6b7280', DRAFT: '#9ca3af', DEPRECATED: '#f85149',
  };

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-[560px] max-h-[80vh] flex flex-col">
        <DialogHeader className="pb-2">
          <DialogTitle className="mb-1">关联自动化用例</DialogTitle>
          <p className="text-sm text-[var(--text-secondary)]">
            为 <strong>{testCase.case_id}</strong> 选择要关联的自动化用例
          </p>
        </DialogHeader>

        {/* 搜索 + 框架筛选行 */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <input
            className="form-input"
            type="text" placeholder="搜索自动用例名称或 ID..." value={search}
            onChange={e => onSearchChange(e.target.value)}
            style={{ flex: 1 }}
          />
          <select
            className="form-input form-select"
            value={frameworkFilter}
            onChange={e => setFrameworkFilter(e.target.value)}
            style={{ width: 130 }}
          >
            <option value="">全部框架</option>
            {frameworkOptions.map(fw => (
              <option key={fw} value={fw}>{fw}</option>
            ))}
          </select>
        </div>

        {/* 用例列表 */}
        <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
          {linkable.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary, #6b7280)', fontSize: 13 }}>
              {search || frameworkFilter ? '没有匹配的自动用例' : '暂无可关联的自动用例'}
            </div>
          ) : linkable.map(a => {
            const sc = STATUS_COLORS[a.status] || '#9ca3af';
            const isConflicted = a.linked_manual_case_id && a.linked_manual_case_id !== testCase.case_id;
            return (
              <div key={a.auto_case_id} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 12px', marginBottom: 6,
                borderRadius: 8, border: '1px solid var(--border-default, #d1d5db)',
                background: 'var(--bg-primary, #fff)',
                transition: 'border-color 0.12s, box-shadow 0.12s',
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = '#2563eb'; e.currentTarget.style.boxShadow = '0 1px 4px rgba(37,99,235,0.12)'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-default, #d1d5db)'; e.currentTarget.style.boxShadow = 'none'; }}
              >
                {/* 状态指示灯 */}
                <span style={{
                  width: 8, height: 8, borderRadius: '50%', background: sc, flexShrink: 0,
                }} />

                {/* 用例信息 */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary, #1f2937)', marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {a.name}
                    {a.automation_type && (
                      <span style={{ fontSize: 10, color: 'var(--text-tertiary, #9ca3af)', fontWeight: 400, marginLeft: 6 }}>
                        ({a.automation_type})
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 11, color: 'var(--text-secondary, #6b7280)', flexWrap: 'wrap' }}>
                    <span style={{ fontFamily: 'monospace' }}>{a.auto_case_id}</span>
                    {a.framework && <span>· {a.framework}</span>}
                    {a.maintainer_id && <span>· 维护: {a.maintainer_id}</span>}
                    <span style={{ color: sc, fontWeight: 500 }}>· {a.status}</span>
                  </div>
                  {isConflicted && (
                    <div style={{ fontSize: 11, color: '#f0883e', marginTop: 4 }}>
                      ⚠️ 已关联到其他手工用例 ({a.linked_manual_case_id})，关联将解除旧关系
                    </div>
                  )}
                </div>

                {/* 关联按钮 */}
                <button
                  onClick={() => onLink(a.auto_case_id)}
                  disabled={isLinking}
                  style={{
                    padding: '5px 14px', borderRadius: 6, border: 'none',
                    background: isLinking ? 'var(--bg-secondary, #f3f4f6)' : '#2563eb',
                    color: isLinking ? 'var(--text-secondary, #6b7280)' : '#fff',
                    fontSize: 12, fontWeight: 500, cursor: isLinking ? 'default' : 'pointer',
                    whiteSpace: 'nowrap', flexShrink: 0,
                  }}
                >
                  {isLinking ? '关联中...' : '关联'}
                </button>
              </div>
            );
          })}
        </div>

        {/* 底部提示 */}
        <div style={{ fontSize: 11, color: 'var(--text-tertiary, #9ca3af)', marginTop: 10, textAlign: 'center' }}>
          共 {linkable.length} 个可关联的自动化用例
        </div>
      </DialogContent>
    </Dialog>
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
