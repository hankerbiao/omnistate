/**
 * 用例治理页面
 * 用于发现和补全不完整的测试用例（缺Lab/目录/Tag/未关联自动化用例）
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { useAuth } from '../providers/AuthProvider';
import { getErrorMessage } from '../utils/errors';
import type {
  TestCaseResponse,
  AutomationTestCaseResponse,
  GovernanceStats,
  CatalogLab,
  BatchUpdateResult,
  UpdateTestCaseRequest,
} from '../types';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';

type MissingFieldKey = 'lab_id' | 'catalog_path' | 'tags' | 'auto_link';

type BatchMode = 'lab_id' | 'catalog_path' | 'tags_add' | 'tags_remove';

interface FeedbackState {
  tone: 'success' | 'error' | 'info';
  message: string;
  detail?: string;
}

interface BatchFormState {
  mode: BatchMode;
  labId: string;
  catalogPath: string;
  tagsText: string;
}

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

const PAGE_SIZE = 50;
const GOVERNANCE_STATS_KEY = ['caseGovernance', 'stats'] as const;
const GOVERNANCE_CASES_KEY = ['caseGovernance', 'list'] as const;

const getMissingColor = (key: MissingFieldKey) =>
  key === 'auto_link' ? STAT_COLORS.unlinked_auto : STAT_COLORS[`missing_${key}`];

const splitPath = (value: string) => value.split('/').map(part => part.trim()).filter(Boolean);
const splitTags = (value: string) => value.split(',').map(tag => tag.trim()).filter(Boolean);
const getLinkedAutoCaseId = (testCase: TestCaseResponse) =>
  testCase.automation_case_ref?.auto_case_id
  || testCase.auto_case_ref?.auto_case_id
  || testCase.linked_auto_case_id
  || '';

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [delayMs, value]);
  return debounced;
}

const CaseGovernancePage: React.FC = () => {
  const qc = useQueryClient();
  const { userPermissions } = useAuth();
  const canWrite = userPermissions.includes('test_cases:write');

  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search.trim(), 300);
  const [activeMissing, setActiveMissing] = useState<MissingFieldKey | null>(null);
  const [page, setPage] = useState(0);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [linkModalCase, setLinkModalCase] = useState<TestCaseResponse | null>(null);
  const [batchForm, setBatchForm] = useState<BatchFormState>({
    mode: 'lab_id',
    labId: '',
    catalogPath: '',
    tagsText: '',
  });

  const resetListSelection = () => {
    setPage(0);
    setSelectedIds(new Set());
  };

  const statsQuery = useQuery({
    queryKey: GOVERNANCE_STATS_KEY,
    queryFn: () => api.getGovernanceStats().then(r => r.data),
  });

  const listParams = useMemo(() => ({
    q: debouncedSearch || undefined,
    missing_fields: activeMissing || undefined,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  }), [activeMissing, debouncedSearch, page]);

  const casesQuery = useQuery({
    queryKey: [...GOVERNANCE_CASES_KEY, listParams],
    queryFn: () => api.listGovernanceCases(listParams).then(r => r.data),
  });

  const labsQuery = useQuery({
    queryKey: ['labs'],
    queryFn: () => api.listLabs({ active_only: true }).then(r => r.data),
  });

  const refreshGovernance = () => {
    qc.invalidateQueries({ queryKey: GOVERNANCE_STATS_KEY });
    qc.invalidateQueries({ queryKey: GOVERNANCE_CASES_KEY });
  };

  const unlinkMutation = useMutation({
    mutationFn: (caseId: string) => api.unlinkAutomationCase(caseId),
    onSuccess: () => {
      setFeedback({ tone: 'success', message: '已取消自动化关联' });
      refreshGovernance();
    },
    onError: err => setFeedback({ tone: 'error', message: getErrorMessage(err, '取消关联失败') }),
  });

  const linkMutation = useMutation({
    mutationFn: ({ caseId, autoCaseId }: { caseId: string; autoCaseId: string }) =>
      api.linkAutomationCase(caseId, { auto_case_id: autoCaseId }),
    onSuccess: () => {
      setFeedback({ tone: 'success', message: '已关联自动化用例' });
      refreshGovernance();
      setLinkModalCase(null);
    },
    onError: err => setFeedback({ tone: 'error', message: getErrorMessage(err, '关联失败') }),
  });

  const batchMutation = useMutation({
    mutationFn: async () => {
      const caseIds = Array.from(selectedIds);
      if (batchForm.mode === 'lab_id') {
        if (!batchForm.labId) throw new Error('请选择 Lab');
        return (await api.batchUpdateCases({ case_ids: caseIds, lab_id: batchForm.labId })).data;
      }
      if (batchForm.mode === 'catalog_path') {
        const catalogPath = splitPath(batchForm.catalogPath);
        if (catalogPath.length === 0) throw new Error('请输入目录路径');
        return (await api.batchUpdateCases({ case_ids: caseIds, catalog_path: catalogPath })).data;
      }
      const tags = splitTags(batchForm.tagsText);
      if (tags.length === 0) throw new Error('请输入 Tag');
      if (batchForm.mode === 'tags_add') {
        return (await api.batchUpdateCases({ case_ids: caseIds, tags_add: tags })).data;
      }
      return (await api.batchUpdateCases({ case_ids: caseIds, tags_remove: tags })).data;
    },
    onSuccess: (result?: BatchUpdateResult) => {
      const failedCount = result?.failed_count ?? 0;
      setFeedback({
        tone: failedCount > 0 ? 'info' : 'success',
        message: `批量补全完成：成功 ${result?.updated_count ?? 0} 条，失败 ${failedCount} 条`,
        detail: result?.failures?.map(f => `${f.case_id}: ${f.reason}`).join('\n'),
      });
      setSelectedIds(new Set());
      refreshGovernance();
    },
    onError: err => setFeedback({ tone: 'error', message: getErrorMessage(err, '批量补全失败') }),
  });

  const cases = casesQuery.data?.items ?? [];
  const total = casesQuery.data?.total ?? 0;
  const labs = (labsQuery.data ?? []) as CatalogLab[];
  const selectedCount = selectedIds.size;
  const currentPageIds = cases.map(c => c.case_id);
  const allCurrentSelected = currentPageIds.length > 0 && currentPageIds.every(id => selectedIds.has(id));
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const toggleSelect = (caseId: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(caseId)) next.delete(caseId);
      else next.add(caseId);
      return next;
    });
  };

  const toggleSelectAll = () => {
    setSelectedIds(prev => {
      if (allCurrentSelected) {
        const next = new Set(prev);
        currentPageIds.forEach(id => next.delete(id));
        return next;
      }
      return new Set([...prev, ...currentPageIds]);
    });
  };

  const handleMissingClick = (key: MissingFieldKey | null) => {
    resetListSelection();
    setActiveMissing(key);
    setFeedback(null);
  };

  const handleSearchChange = (value: string) => {
    resetListSelection();
    setSearch(value);
  };

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text-primary, #1f2937)', marginBottom: 4 }}>
          用例治理
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-secondary, #6b7280)' }}>
          发现并补全不完整的测试用例，管理手工与自动化用例关联
        </p>
      </div>

      <StatsBar stats={statsQuery.data} isLoading={statsQuery.isLoading} activeMissing={activeMissing} onMissingClick={handleMissingClick} />

      {!canWrite && (
        <Feedback tone="info" message="当前账号只有查看权限，补全、关联和批量操作已禁用。" />
      )}
      {feedback && <Feedback tone={feedback.tone} message={feedback.message} detail={feedback.detail} onClose={() => setFeedback(null)} />}

      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder="搜索用例 ID / 标题..."
          value={search}
          onChange={e => handleSearchChange(e.target.value)}
          style={inputStyle}
        />
        {activeMissing && (
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 4,
            padding: '4px 10px', borderRadius: 12, fontSize: 12,
            background: `${getMissingColor(activeMissing)}20`,
            color: getMissingColor(activeMissing),
          }}>
            {MISSING_LABELS[activeMissing]}
            <button onClick={() => handleMissingClick(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: 14 }}>×</button>
          </span>
        )}
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-secondary, #6b7280)' }}>
          共 {total} 条
        </span>
      </div>

      {canWrite && selectedCount > 0 && (
        <BatchToolbar
          selectedCount={selectedCount}
          labs={labs}
          form={batchForm}
          onFormChange={setBatchForm}
          onClear={() => setSelectedIds(new Set())}
          onSubmit={() => batchMutation.mutate()}
          isSubmitting={batchMutation.isPending}
        />
      )}

      <div style={{
        border: '1px solid var(--border-default, #d1d5db)', borderRadius: 8,
        overflow: 'hidden', marginBottom: 0,
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: 'var(--bg-secondary, #f9fafb)' }}>
              <th style={thStyle}>
                {canWrite && <input type="checkbox" checked={allCurrentSelected} onChange={toggleSelectAll} />}
              </th>
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
              <tr><td colSpan={8} style={emptyCellStyle}>加载中...</td></tr>
            ) : cases.length === 0 ? (
              <tr><td colSpan={8} style={emptyCellStyle}>暂无数据</td></tr>
            ) : cases.map(c => (
              <CaseRow
                key={c.case_id}
                testCase={c}
                selected={selectedIds.has(c.case_id)}
                onToggle={() => toggleSelect(c.case_id)}
                onLink={() => setLinkModalCase(c)}
                onUnlink={() => unlinkMutation.mutate(c.case_id)}
                labs={labs}
                activeMissing={activeMissing}
                canWrite={canWrite}
                onError={message => setFeedback({ tone: 'error', message })}
                onSaved={() => {
                  setFeedback({ tone: 'success', message: '用例信息已保存' });
                  refreshGovernance();
                }}
              />
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
        <button disabled={page === 0 || casesQuery.isFetching} onClick={() => setPage(p => Math.max(0, p - 1))} style={pageBtnStyle}>上一页</button>
        <span style={{ fontSize: 13, lineHeight: '32px', color: 'var(--text-secondary, #6b7280)' }}>
          第 {page + 1} / {totalPages} 页
        </span>
        <button disabled={(page + 1) >= totalPages || casesQuery.isFetching} onClick={() => setPage(p => p + 1)} style={pageBtnStyle}>下一页</button>
      </div>

      {linkModalCase && (
        <LinkModal
          testCase={linkModalCase}
          onLink={autoCaseId => linkMutation.mutate({ caseId: linkModalCase.case_id, autoCaseId })}
          onClose={() => setLinkModalCase(null)}
          isLinking={linkMutation.isPending}
        />
      )}
    </div>
  );
};

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

const Feedback: React.FC<FeedbackState & { onClose?: () => void }> = ({ tone, message, detail, onClose }) => {
  const colors = {
    success: { color: '#15803d', bg: '#dcfce7', border: '#86efac' },
    error: { color: '#b91c1c', bg: '#fee2e2', border: '#fecaca' },
    info: { color: '#1d4ed8', bg: '#dbeafe', border: '#bfdbfe' },
  }[tone];
  return (
    <div style={{ padding: '10px 12px', borderRadius: 8, border: `1px solid ${colors.border}`, background: colors.bg, color: colors.color, fontSize: 13, marginBottom: 14 }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
        <span style={{ flex: 1 }}>{message}</span>
        {onClose && <button type="button" onClick={onClose} style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer' }}>×</button>}
      </div>
      {detail && <pre style={{ margin: '8px 0 0', whiteSpace: 'pre-wrap', fontSize: 12 }}>{detail}</pre>}
    </div>
  );
};

const BatchToolbar: React.FC<{
  selectedCount: number;
  labs: CatalogLab[];
  form: BatchFormState;
  onFormChange: (form: BatchFormState) => void;
  onClear: () => void;
  onSubmit: () => void;
  isSubmitting: boolean;
}> = ({ selectedCount, labs, form, onFormChange, onClear, onSubmit, isSubmitting }) => {
  const pathPreview = form.mode === 'catalog_path' ? splitPath(form.catalogPath).join(' / ') : '';
  const tagPreview = form.mode === 'tags_add' || form.mode === 'tags_remove' ? splitTags(form.tagsText).join(', ') : '';

  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', padding: 12, border: '1px solid #bfdbfe', background: '#eff6ff', borderRadius: 8, marginBottom: 14 }}>
      <strong style={{ fontSize: 13, color: '#1d4ed8' }}>已选择 {selectedCount} 条</strong>
      <select
        className="form-input form-select"
        value={form.mode}
        onChange={e => onFormChange({ ...form, mode: e.target.value as BatchMode })}
        style={{ width: 130, fontSize: 13 }}
      >
        <option value="lab_id">设置 Lab</option>
        <option value="catalog_path">设置目录</option>
        <option value="tags_add">追加 Tag</option>
        <option value="tags_remove">移除 Tag</option>
      </select>
      {form.mode === 'lab_id' ? (
        <select
          className="form-input form-select"
          value={form.labId}
          onChange={e => onFormChange({ ...form, labId: e.target.value })}
          style={{ width: 180, fontSize: 13 }}
        >
          <option value="">选择 Lab...</option>
          {labs.map(l => <option key={l.lab_id} value={l.lab_id}>{l.name}</option>)}
        </select>
      ) : (
        <input
          type="text"
          value={form.mode === 'catalog_path' ? form.catalogPath : form.tagsText}
          onChange={e => onFormChange(form.mode === 'catalog_path' ? { ...form, catalogPath: e.target.value } : { ...form, tagsText: e.target.value })}
          placeholder={form.mode === 'catalog_path' ? 'bios/boot' : 'tag1, tag2'}
          style={{ ...inputStyle, width: 240 }}
        />
      )}
      {(pathPreview || tagPreview) && (
        <span style={{ fontSize: 12, color: 'var(--text-secondary, #6b7280)' }}>
          预览：{pathPreview || tagPreview}
        </span>
      )}
      <button type="button" onClick={onSubmit} disabled={isSubmitting} style={{ ...actionBtnStyle, background: '#2563eb', color: '#fff', borderColor: '#2563eb' }}>
        {isSubmitting ? '处理中...' : '应用'}
      </button>
      <button type="button" onClick={onClear} style={{ ...actionBtnStyle, color: '#6b7280' }}>清空选择</button>
    </div>
  );
};

const CaseRow: React.FC<{
  testCase: TestCaseResponse;
  selected: boolean;
  onToggle: () => void;
  onLink: () => void;
  onUnlink: () => void;
  labs: CatalogLab[];
  activeMissing: MissingFieldKey | null;
  canWrite: boolean;
  onError: (message: string) => void;
  onSaved: () => void;
}> = ({ testCase: c, selected, onToggle, onLink, onUnlink, labs, activeMissing, canWrite, onError, onSaved }) => {
  const labName = labs.find(l => l.lab_id === c.lab_id)?.name || c.lab_name || '';
  const hasLab = !!c.lab_id;
  const hasCatalog = !!(c.catalog_path && c.catalog_path.length > 0);
  const hasTags = !!(c.tags && c.tags.length > 0);
  const linkedAutoCaseId = getLinkedAutoCaseId(c);

  const [editing, setEditing] = useState<'lab_id' | 'catalog_path' | 'tags' | null>(null);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);

  const startEdit = (field: 'lab_id' | 'catalog_path' | 'tags') => {
    if (!canWrite) return;
    setEditing(field);
    if (field === 'lab_id') setEditValue(c.lab_id || '');
    else if (field === 'catalog_path') setEditValue((c.catalog_path || []).join('/'));
    else setEditValue((c.tags || []).join(', '));
  };

  const cancelEdit = () => {
    setEditing(null);
    setEditValue('');
  };

  const saveEdit = async () => {
    if (!editing) return;
    setSaving(true);
    try {
      const payload: UpdateTestCaseRequest = {};
      if (editing === 'lab_id') {
        if (!editValue) throw new Error('请选择 Lab');
        payload.lab_id = editValue;
      } else if (editing === 'catalog_path') {
        const catalogPath = splitPath(editValue);
        if (catalogPath.length === 0) throw new Error('请输入目录路径');
        payload.catalog_path = catalogPath;
      } else if (editing === 'tags') {
        const tags = splitTags(editValue);
        if (tags.length === 0) throw new Error('请输入 Tag');
        payload.tags = tags;
      }
      await api.updateTestCase(c.case_id, payload);
      cancelEdit();
      onSaved();
    } catch (err) {
      onError(getErrorMessage(err, '保存失败'));
    } finally {
      setSaving(false);
    }
  };

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
      <span style={{ display: 'inline-flex', flexDirection: 'column', gap: 2 }}>
        <input
          type="text"
          value={editValue}
          onChange={e => setEditValue(e.target.value)}
          placeholder={editing === 'catalog_path' ? 'bios/boot' : 'tag1, tag2'}
          style={{ width: 120, fontSize: 11, padding: '2px 4px', border: '1px solid var(--border-default, #d1d5db)', borderRadius: 4 }}
          autoFocus
        />
        {editing === 'catalog_path' && editValue.trim() && (
          <span style={{ fontSize: 10, color: 'var(--text-secondary, #6b7280)' }}>{splitPath(editValue).join(' / ')}</span>
        )}
      </span>
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

  const renderAction = () => {
    if (!canWrite) return <span style={{ fontSize: 12, color: 'var(--text-tertiary, #9ca3af)' }}>只读</span>;
    if (editing) return renderInlineEdit();
    if (activeMissing === 'lab_id' && !hasLab) return <button onClick={() => startEdit('lab_id')} style={actionBtnStyle}>设置 Lab</button>;
    if (activeMissing === 'catalog_path' && !hasCatalog) return <button onClick={() => startEdit('catalog_path')} style={actionBtnStyle}>设置目录</button>;
    if (activeMissing === 'tags' && !hasTags) return <button onClick={() => startEdit('tags')} style={actionBtnStyle}>添加 Tag</button>;
    if (!linkedAutoCaseId) return <button onClick={onLink} style={actionBtnStyle}>关联</button>;
    return <button onClick={onUnlink} style={{ ...actionBtnStyle, color: '#f85149' }}>取消关联</button>;
  };

  return (
    <tr style={{ borderBottom: '1px solid var(--border-default, #d1d5db)' }}>
      <td style={tdStyle}>{canWrite && <input type="checkbox" checked={selected} onChange={onToggle} />}</td>
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
        <CompletenessDot ok={!!linkedAutoCaseId} />
        <span style={{ fontSize: 12 }}>{linkedAutoCaseId || '—'}</span>
      </td>
      <td style={tdStyle}>{renderAction()}</td>
    </tr>
  );
};

const CompletenessDot: React.FC<{ ok: boolean }> = ({ ok }) => (
  <span style={{
    display: 'inline-block', width: 7, height: 7, borderRadius: '50%',
    background: ok ? '#3fb950' : '#f85149', marginRight: 6, verticalAlign: 'middle',
  }} />
);

const LinkModal: React.FC<{
  testCase: TestCaseResponse;
  onLink: (autoCaseId: string) => void;
  onClose: () => void;
  isLinking: boolean;
}> = ({ testCase, onLink, onClose, isLinking }) => {
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search.trim(), 250);
  const [frameworkFilter, setFrameworkFilter] = useState('');

  const autoCasesQuery = useQuery({
    queryKey: ['caseGovernance', 'autoCases', testCase.case_id, debouncedSearch, frameworkFilter],
    queryFn: () => api.listAutomationTestCases({
      q: debouncedSearch || undefined,
      framework: frameworkFilter || undefined,
      linkable_for_case_id: testCase.case_id,
      limit: 80,
    }).then(r => r.data || []),
  });

  const autoCases = autoCasesQuery.data ?? [];
  const statusColors: Record<string, string> = {
    ACTIVE: '#3fb950', INACTIVE: '#6b7280', DRAFT: '#9ca3af', DEPRECATED: '#f85149',
  };

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-[620px] max-h-[80vh] flex flex-col">
        <DialogHeader className="pb-2">
          <DialogTitle className="mb-1">关联自动化用例</DialogTitle>
          <p className="text-sm text-[var(--text-secondary)]">
            为 <strong>{testCase.case_id}</strong> 选择要关联的自动化用例
          </p>
        </DialogHeader>

        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <input
            className="form-input"
            type="text"
            placeholder="搜索自动用例名称、ID 或脚本..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ flex: 1 }}
          />
          <input
            className="form-input"
            type="text"
            placeholder="框架"
            value={frameworkFilter}
            onChange={e => setFrameworkFilter(e.target.value)}
            style={{ width: 130 }}
          />
        </div>

        <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
          {autoCasesQuery.isLoading ? (
            <div style={modalEmptyStyle}>加载中...</div>
          ) : autoCases.length === 0 ? (
            <div style={modalEmptyStyle}>{search || frameworkFilter ? '没有匹配的自动用例' : '暂无可关联的自动用例'}</div>
          ) : autoCases.map((a: AutomationTestCaseResponse) => {
            const sc = statusColors[a.status] || '#9ca3af';
            return (
              <div key={a.auto_case_id} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 12px', marginBottom: 6,
                borderRadius: 8, border: '1px solid var(--border-default, #d1d5db)',
                background: 'var(--bg-primary, #fff)',
              }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: sc, flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary, #1f2937)', marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {a.name}
                    {a.automation_type && <span style={{ fontSize: 10, color: 'var(--text-tertiary, #9ca3af)', fontWeight: 400, marginLeft: 6 }}>({a.automation_type})</span>}
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 11, color: 'var(--text-secondary, #6b7280)', flexWrap: 'wrap' }}>
                    <span style={{ fontFamily: 'monospace' }}>{a.auto_case_id}</span>
                    {a.framework && <span>· {a.framework}</span>}
                    {a.maintainer_id && <span>· 维护: {a.maintainer_id}</span>}
                    <span style={{ color: sc, fontWeight: 500 }}>· {a.status}</span>
                  </div>
                </div>
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

        <div style={{ fontSize: 11, color: 'var(--text-tertiary, #9ca3af)', marginTop: 10, textAlign: 'center' }}>
          当前显示 {autoCases.length} 个可关联的自动化用例
        </div>
      </DialogContent>
    </Dialog>
  );
};

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
  padding: '6px 12px', borderRadius: 6, border: '1px solid var(--border-default, #d1d5db)',
  fontSize: 13, width: 240, background: 'var(--bg-primary, #fff)',
};

const actionBtnStyle: React.CSSProperties = {
  padding: '3px 10px', borderRadius: 4, border: '1px solid var(--border-default, #d1d5db)',
  background: 'var(--bg-primary, #fff)', fontSize: 12, cursor: 'pointer', color: '#2563eb',
};

const pageBtnStyle: React.CSSProperties = {
  padding: '4px 12px', borderRadius: 6, border: '1px solid var(--border-default, #d1d5db)',
  background: 'var(--bg-primary, #fff)', fontSize: 13, cursor: 'pointer',
};

const emptyCellStyle: React.CSSProperties = {
  textAlign: 'center', padding: 40, color: 'var(--text-secondary, #6b7280)',
};

const modalEmptyStyle: React.CSSProperties = {
  textAlign: 'center', padding: 40, color: 'var(--text-secondary, #6b7280)', fontSize: 13,
};

export default CaseGovernancePage;
