import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { api } from '../services/api';
import type {
  CollectionListItem,
  CollectionResponse,
  AutomationTestCaseResponse,
  TestCaseResponse,
} from '../types';
import PageToolbar, { StatPill } from './ui/PageToolbar';
import CaseLibraryPicker, { useCaseLibrary, useDualCaseSelection } from './CaseLibraryPicker';
import AIAnalysisPanel from './AIAnalysisPanel';
import {
  getCaseDisplayTitle,
  getCaseTypeLabel,
  getCaseStatusLabel,
  PICKER_TYPE_FILTERS,
  type TypeFilter,
} from './TestCaseBoard/testCaseBoardTypes';
import {
  DetailHeader,
  DetailEmpty,
} from './ui/SplitDetailPanel';

// ═══════════════════════════════════════════════════════════════════════
//  类型
// ═══════════════════════════════════════════════════════════════════════

interface TestCaseCollectionPageProps {
  currentUserId: string;
}

type SortKey = 'name' | 'count' | 'updated';

// ═══════════════════════════════════════════════════════════════════════
//  工具函数
// ═══════════════════════════════════════════════════════════════════════

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days < 1) return '今天';
  if (days < 7) return `${days} 天前`;
  if (days < 30) return `${Math.floor(days / 7)} 周前`;
  return new Date(iso).toLocaleDateString('zh-CN');
}

function parseTagsInput(raw: string): string[] | undefined {
  const tags = raw.split(/[,，]/).map(t => t.trim()).filter(Boolean);
  return tags.length > 0 ? tags : undefined;
}

// ═══════════════════════════════════════════════════════════════════════
//  集合表单弹窗
// ═══════════════════════════════════════════════════════════════════════

interface CollectionFormModalProps {
  mode: 'create' | 'edit';
  open: boolean;
  name: string;
  description: string;
  tags: string;
  submitting: boolean;
  onClose: () => void;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onTagsChange: (value: string) => void;
  onSubmit: () => void;
}

function CollectionFormModal({
  mode, open, name, description, tags, submitting,
  onClose, onNameChange, onDescriptionChange, onTagsChange, onSubmit,
}: CollectionFormModalProps) {
  if (!open) return null;
  const title = mode === 'create' ? '新建预制用例集' : '编辑预制集合';
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ width: 480 }}>
        <div className="modal__header">
          <h3 className="modal__title">{title}</h3>
          <button type="button" className="modal__close" onClick={onClose}>×</button>
        </div>
        <div className="modal__body">
          <div className="form-field">
            <label className="form-field__label">集合名称 *</label>
            <input className="form-input" value={name} onChange={e => onNameChange(e.target.value)} placeholder={mode === 'create' ? '例如: 回归基线集合' : undefined} autoFocus />
          </div>
          <div className="form-field">
            <label className="form-field__label">描述</label>
            <textarea className="form-input" value={description} onChange={e => onDescriptionChange(e.target.value)} placeholder="说明此预制集的用途" rows={3} />
          </div>
          <div className="form-field">
            <label className="form-field__label">标签（逗号分隔）</label>
            <input className="form-input" value={tags} onChange={e => onTagsChange(e.target.value)} placeholder="回归, 冒烟, P0" />
          </div>
        </div>
        <div className="modal__footer">
          <button type="button" className="btn btn--secondary" onClick={onClose}>取消</button>
          <button type="button" className="btn btn--primary" onClick={onSubmit} disabled={submitting || !name.trim()}>
            {submitting ? (mode === 'create' ? '创建中…' : '保存中…') : (mode === 'create' ? '创建' : '保存')}
          </button>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
//  主组件
// ═══════════════════════════════════════════════════════════════════════

const TestCaseCollectionPage: React.FC<TestCaseCollectionPageProps> = ({ currentUserId }) => {
  const { items: libraryItems, manualMap, autoMap, labs, loading: libraryLoading, refresh: refreshLibrary } = useCaseLibrary();

  // — 集合列表状态
  const [collections, setCollections] = useState<CollectionListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selected, setSelected] = useState<CollectionResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>('updated');
  const [selectedCollIds, setSelectedCollIds] = useState<Set<string>>(new Set());

  // — 创建 / 编辑状态
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newTags, setNewTags] = useState('');
  const [creating, setCreating] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editTags, setEditTags] = useState('');
  const [editing, setEditing] = useState(false);

  // — 添加用例（Drawer）
  const [addOpen, setAddOpen] = useState(false);
  const addSelection = useDualCaseSelection();
  const [adding, setAdding] = useState(false);

  // — 集合内用例筛选 & 批量选择
  const [caseSearch, setCaseSearch] = useState('');
  const [caseTypeFilter, setCaseTypeFilter] = useState<TypeFilter>('all');
  const [selectedCaseIds, setSelectedCaseIds] = useState<Set<string>>(new Set());

  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  const initialSelectedRef = useRef(false);

  // ═══════════════════════════════════════════════════════════════════
  //  数据获取
  // ═══════════════════════════════════════════════════════════════════

  const fetchCollections = useCallback(async (q?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listCollections(q || undefined);
      const items = res.data || [];
      setCollections(items);
      const current = selectedRef.current;
      if (current) {
        const still = items.find(c => c.collection_id === current.collection_id);
        if (!still) setSelected(null);
      }
    } catch (err) {
      setError('获取集合列表失败');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCollections(); }, [fetchCollections]);

  const fetchDetail = useCallback(async (id: string) => {
    setDetailLoading(true);
    setCaseSearch('');
    setCaseTypeFilter('all');
    setSelectedCaseIds(new Set());
    try {
      const res = await api.getCollection(id);
      setSelected(res.data);
    } catch {
      setSelected(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => fetchCollections(searchQuery || undefined), 300);
    return () => clearTimeout(timer);
  }, [searchQuery, fetchCollections]);

  useEffect(() => {
    if (!initialSelectedRef.current && collections.length > 0 && !selected) {
      initialSelectedRef.current = true;
      fetchDetail(collections[0].collection_id);
    }
  }, [collections, selected, fetchDetail]);

  // ═══════════════════════════════════════════════════════════════════
  //  排序 & 统计
  // ═══════════════════════════════════════════════════════════════════

  const sortedCollections = useMemo(() => {
    const list = [...collections];
    switch (sortKey) {
      case 'name':
        list.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case 'count':
        list.sort((a, b) => (b.case_count + b.auto_case_count) - (a.case_count + a.auto_case_count));
        break;
      case 'updated':
        list.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
        break;
    }
    return list;
  }, [collections, sortKey]);

  const listStats = useMemo(() => ({
    count: collections.length,
    totalCases: collections.reduce((sum, c) => sum + c.case_count + c.auto_case_count, 0),
  }), [collections]);

  // ═══════════════════════════════════════════════════════════════════
  //  用例抽屉
  // ═══════════════════════════════════════════════════════════════════

  const openAddModal = () => {
    addSelection.reset();
    setAddOpen(true);
    refreshLibrary();
  };

  const excludeManualIds = useMemo(() => new Set(selected?.case_ids || []), [selected?.case_ids]);
  const excludeAutoIds = useMemo(() => new Set(selected?.auto_case_ids || []), [selected?.auto_case_ids]);

  // ═══════════════════════════════════════════════════════════════════
  //  CRUD 操作
  // ═══════════════════════════════════════════════════════════════════

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await api.createCollection({
        name: newName.trim(),
        description: newDesc.trim() || undefined,
        tags: parseTagsInput(newTags),
      });
      setCreateOpen(false);
      setNewName('');
      setNewDesc('');
      setNewTags('');
      await fetchCollections();
    } catch (err) {
      setError('创建集合失败');
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  const openEdit = () => {
    if (!selected) return;
    setEditName(selected.name);
    setEditDesc(selected.description || '');
    setEditTags((selected.tags || []).join(', '));
    setEditOpen(true);
  };

  const handleEdit = async () => {
    if (!selected || !editName.trim()) return;
    setEditing(true);
    setError(null);
    try {
      await api.updateCollection(selected.collection_id, {
        name: editName.trim(),
        description: editDesc.trim() || undefined,
        tags: parseTagsInput(editTags) ?? [],
      });
      setEditOpen(false);
      await fetchCollections();
      await fetchDetail(selected.collection_id);
    } catch (err) {
      setError('更新集合失败');
      console.error(err);
    } finally {
      setEditing(false);
    }
  };

  const handleDelete = async (id?: string) => {
    const targetId = id || selected?.collection_id;
    const targetName = id ? collections.find(c => c.collection_id === id)?.name : selected?.name;
    if (!targetId || !targetName) return;
    if (!window.confirm(`确定删除集合「${targetName}」吗？`)) return;
    setError(null);
    try {
      await api.deleteCollection(targetId);
      if (selected?.collection_id === targetId) setSelected(null);
      setSelectedCollIds(prev => { const next = new Set(prev); next.delete(targetId); return next; });
      await fetchCollections();
    } catch (err) {
      setError('删除集合失败');
      console.error(err);
    }
  };

  const handleBatchDelete = async () => {
    if (selectedCollIds.size === 0) return;
    if (!window.confirm(`确定批量删除 ${selectedCollIds.size} 个预制集合吗？`)) return;
    setError(null);
    try {
      await Promise.all(Array.from(selectedCollIds).map(id => api.deleteCollection(id)));
      setSelectedCollIds(new Set());
      if (selected && selectedCollIds.has(selected.collection_id)) setSelected(null);
      await fetchCollections();
    } catch (err) {
      setError('批量删除失败');
      console.error(err);
    }
  };

  const toggleCollSelect = (id: string) => {
    setSelectedCollIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handleAddCases = async () => {
    if (!selected) return;
    if (addSelection.count === 0) return;
    setAdding(true);
    setError(null);
    try {
      await api.addCasesToCollection(selected.collection_id, {
        case_ids: Array.from(addSelection.selectedManualIds),
        auto_case_ids: Array.from(addSelection.selectedAutoIds),
      });
      setAddOpen(false);
      addSelection.clear();
      await fetchDetail(selected.collection_id);
      await fetchCollections();
    } catch (err) {
      setError('添加用例失败');
      console.error(err);
    } finally {
      setAdding(false);
    }
  };

  const handleRemoveCase = async (type: 'manual' | 'auto', id: string) => {
    if (!selected) return;
    try {
      await api.removeCasesFromCollection(
        selected.collection_id,
        type === 'manual' ? { case_ids: [id] } : { auto_case_ids: [id] },
      );
      setSelectedCaseIds(prev => { const next = new Set(prev); next.delete(`${type}-${id}`); return next; });
      await fetchDetail(selected.collection_id);
      await fetchCollections();
    } catch (err) {
      setError('移除用例失败');
      console.error(err);
    }
  };

  const handleBatchRemoveCases = async () => {
    if (!selected || selectedCaseIds.size === 0) return;
    if (!window.confirm(`确定从集合中批量移除 ${selectedCaseIds.size} 个用例吗？`)) return;
    setError(null);
    try {
      const manualIds: string[] = [];
      const autoIds: string[] = [];
      for (const key of selectedCaseIds) {
        if (key.startsWith('manual-')) manualIds.push(key.slice(7));
        else autoIds.push(key.slice(5));
      }
      await api.removeCasesFromCollection(selected.collection_id, {
        case_ids: manualIds,
        auto_case_ids: autoIds,
      });
      setSelectedCaseIds(new Set());
      await fetchDetail(selected.collection_id);
      await fetchCollections();
    } catch (err) {
      setError('批量移除失败');
      console.error(err);
    }
  };

  // ═══════════════════════════════════════════════════════════════════
  //  衍生数据
  // ═══════════════════════════════════════════════════════════════════

  const detailCaseRows = useMemo(() => {
    if (!selected) return [] as { type: 'manual' | 'auto'; id: string }[];
    const rows: { type: 'manual' | 'auto'; id: string }[] = [];
    selected.case_ids.forEach(id => rows.push({ type: 'manual', id }));
    selected.auto_case_ids.forEach(id => rows.push({ type: 'auto', id }));
    return rows;
  }, [selected]);

  const filteredDetailCases = useMemo(() => {
    const q = caseSearch.trim().toLowerCase();
    return detailCaseRows.filter(row => {
      if (caseTypeFilter === 'manual' && row.type !== 'manual') return false;
      if (caseTypeFilter === 'auto' && row.type !== 'auto') return false;
      if (!q) return true;
      const title = getCaseDisplayTitle(row.type, row.id, manualMap, autoMap).toLowerCase();
      return row.id.toLowerCase().includes(q) || title.includes(q);
    });
  }, [detailCaseRows, caseSearch, caseTypeFilter, manualMap, autoMap]);

  const manualCount = selected?.case_ids.length ?? 0;
  const autoCount = selected?.auto_case_ids.length ?? 0;
  const totalInCollection = manualCount + autoCount;

  // 计算集合内用例涉及的目录数（通过 manualMap 查 lab_name）
  const labCount = useMemo(() => {
    if (!selected) return 0;
    const labsSet = new Set<string>();
    selected.case_ids.forEach(id => {
      const c = manualMap.get(id);
      if (c?.lab_name) labsSet.add(c.lab_name);
      if (c?.lab_id) labsSet.add(c.lab_id);
    });
    selected.auto_case_ids.forEach(id => {
      const c = autoMap.get(id);
      // auto cases may not have lab info; try tags or description
      if (c?.tags) c.tags.forEach(t => {
        if (t.startsWith('lab:')) labsSet.add(t.slice(4));
      });
    });
    return labsSet.size;
  }, [selected, manualMap, autoMap]);

  const canDelete = selected ? currentUserId === 'admin' || currentUserId === selected.created_by : false;
  const closeDetail = () => setSelected(null);
  const isAllCasesSelected = filteredDetailCases.length > 0 && filteredDetailCases.every(r => selectedCaseIds.has(`${r.type}-${r.id}`));

  const toggleCaseSelect = (type: string, id: string) => {
    const key = `${type}-${id}`;
    setSelectedCaseIds(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const toggleAllCases = () => {
    if (isAllCasesSelected) {
      setSelectedCaseIds(new Set());
    } else {
      setSelectedCaseIds(new Set(filteredDetailCases.map(r => `${r.type}-${r.id}`)));
    }
  };

  // ═══════════════════════════════════════════════════════════════════
  //  Render
  // ═══════════════════════════════════════════════════════════════════

  return (
    <>
      {error && (
        <div className="error-banner collection-page__error">
          <span>⚠ {error}</span>
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className={`collection-page split-workspace${selected ? ' split-workspace--has-selection' : ''}`}>
        {/* ──────────────── 左侧：集合卡片列表 ──────────────── */}
        <aside className="split-workspace__list">
          <div className="split-panel-toolbar">
            <PageToolbar
              meta={
                <>
                  <StatPill label="集合数" value={listStats.count} />
                  <StatPill label="总用例数" value={listStats.totalCases} tone="info" />
                </>
              }
              actions={
                <button type="button" className="btn btn--primary btn--sm" onClick={() => setCreateOpen(true)}>
                  + 新建预制集合
                </button>
              }
            />
          </div>

          <div className="filter-strip">
            <input type="search" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="搜索集合名称、描述…" className="form-input" aria-label="搜索集合" />
            <button type="button" className="btn btn--secondary btn--sm" onClick={() => fetchCollections(searchQuery || undefined)} disabled={loading}>刷新</button>
          </div>

          {/* 排序栏 */}
          <div className="collection-sort-bar">
            <span className="collection-sort-bar__label">排序：</span>
            {([['name', '名称'], ['count', '用例数'], ['updated', '更新时间']] as [SortKey, string][]).map(([key, label]) => (
              <button
                key={key}
                type="button"
                className={sortKey === key ? 'collection-sort-bar__btn collection-sort-bar__btn--active' : 'collection-sort-bar__btn'}
                onClick={() => setSortKey(key)}
              >
                {label}
              </button>
            ))}
          </div>

          {/* 批量操作栏 */}
          {selectedCollIds.size > 0 && (
            <div className="collection-batch-bar">
              <span>已选 <span className="collection-batch-bar__count">{selectedCollIds.size}</span> 项</span>
              <div className="collection-batch-bar__actions">
                <button type="button" className="btn btn--danger btn--xs" onClick={handleBatchDelete}>批量删除</button>
                <button type="button" className="btn btn--ghost btn--xs" onClick={() => setSelectedCollIds(new Set())}>取消选择</button>
              </div>
            </div>
          )}

          {/* 卡片列表 */}
          <div className="split-list-scroll">
            {loading && collections.length === 0 ? (
              <div className="loading-overlay"><div className="loading-spinner" /></div>
            ) : sortedCollections.length === 0 ? (
              <div className="empty-state"><div className="empty-state__icon">📁</div><p className="empty-state__text">{searchQuery ? '没有匹配的预制集合' : '暂无用例预制集'}</p></div>
            ) : (
              <div className="collection-card-list">
                {sortedCollections.map(c => {
                  const isSelected = selected?.collection_id === c.collection_id;
                  const total = c.case_count + c.auto_case_count;
                  const manualRatio = total > 0 ? (c.case_count / total) * 100 : 0;
                  const autoRatio = total > 0 ? (c.auto_case_count / total) * 100 : 0;
                  return (
                    <div
                      key={c.collection_id}
                      className={`collection-card${isSelected ? ' collection-card--selected' : ''}`}
                      onClick={(e) => {
                        if ((e.target as HTMLElement).closest('.collection-card__check')) return;
                        fetchDetail(c.collection_id);
                      }}
                    >
                      <div className="collection-card__top">
                        <input
                          type="checkbox"
                          className="collection-card__check"
                          checked={selectedCollIds.has(c.collection_id)}
                          onChange={() => toggleCollSelect(c.collection_id)}
                          onClick={e => e.stopPropagation()}
                          title="多选"
                        />
                        <span className="collection-card__name" title={c.name}>{c.name}</span>
                        <code className="collection-card__id">{c.collection_id}</code>
                      </div>

                      {(c.tags && c.tags.length > 0) && (
                        <div className="collection-card__tags">
                          {c.tags.slice(0, 5).map(tag => (
                            <span key={tag} className="collection-card__tag">{tag}</span>
                          ))}
                          {c.tags.length > 5 && <span className="collection-card__tag">+{c.tags.length - 5}</span>}
                        </div>
                      )}

                      <div className="collection-card__stats">
                        <span className="collection-card__stat-item">
                          <span className="collection-card__stat-dot collection-card__stat-dot--manual" />
                          <span className="collection-card__stat-num">{c.case_count}</span>
                          <span>手工</span>
                        </span>
                        <span className="collection-card__stat-item">
                          <span className="collection-card__stat-dot collection-card__stat-dot--auto" />
                          <span className="collection-card__stat-num">{c.auto_case_count}</span>
                          <span>自动</span>
                        </span>
                      </div>

                      {total > 0 && (
                        <div className="collection-card__bar">
                          {c.case_count > 0 && <div className="collection-card__bar-fill--manual" style={{ width: `${manualRatio}%` }} />}
                          {c.auto_case_count > 0 && <div className="collection-card__bar-fill--auto" style={{ width: `${autoRatio}%` }} />}
                        </div>
                      )}

                      <div className="collection-card__meta">
                        <span>{c.created_by}</span>
                        <span title={new Date(c.updated_at).toLocaleString('zh-CN')}>{formatRelativeTime(c.updated_at)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </aside>

        {/* ──────────────── 右侧：详情 ──────────────── */}
        <main className="split-workspace__main">
          {selected ? (
            <div className="split-detail-scroll">
              <button type="button" className="split-workspace__back" onClick={closeDetail}>← 返回列表</button>
              {detailLoading ? (
                <div className="loading-overlay"><div className="loading-spinner" /></div>
              ) : (
                <>
                  {/* 头部 */}
                  <DetailHeader
                    id={selected.collection_id}
                    title={selected.name}
                    subtitle={selected.description || undefined}
                    badges={(selected.tags || []).map(t => <span key={t} className="collection-tag">{t}</span>)}
                    actions={
                      <>
                        <AIAnalysisPanel
                          caseIds={selected.case_ids}
                          autoCaseIds={selected.auto_case_ids}
                          collectionId={selected.collection_id}
                        />
                        <button type="button" className="btn btn--primary btn--sm" onClick={openAddModal}>添加用例</button>
                        <button type="button" className="btn btn--secondary btn--sm" onClick={openEdit}>编辑</button>
                        {canDelete && <button type="button" className="btn btn--danger btn--sm" onClick={() => handleDelete()}>删除</button>}
                      </>
                    }
                  />

                  {/* 创建人 + 更新时间 紧凑行 */}
                  <div className="split-detail-meta-block" style={{ flexDirection: 'row', gap: 24, margin: '4px 24px 0', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
                    <div className="split-detail-meta-row" style={{ flex: 1 }}>
                      <span className="split-detail-meta-row__label">创建人</span>
                      <span className="split-detail-meta-row__value">{selected.created_by}</span>
                    </div>
                    <div className="split-detail-meta-row" style={{ flex: 1 }}>
                      <span className="split-detail-meta-row__label">更新时间</span>
                      <span className="split-detail-meta-row__value">{formatRelativeTime(selected.updated_at)}</span>
                    </div>
                  </div>

                  <div className="split-detail-content">
                    {/* 四个统计小卡片 */}
                    <div className="collection-stats-grid">
                      <div className="collection-stat-card collection-stat-card--manual">
                        <span className="collection-stat-card__label">手工用例</span>
                        <span className="collection-stat-card__value">{manualCount}</span>
                      </div>
                      <div className="collection-stat-card collection-stat-card--auto">
                        <span className="collection-stat-card__label">自动化用例</span>
                        <span className="collection-stat-card__value">{autoCount}</span>
                      </div>
                      <div className="collection-stat-card collection-stat-card--total">
                        <span className="collection-stat-card__label">合计</span>
                        <span className="collection-stat-card__value">{totalInCollection}</span>
                      </div>
                      <div className="collection-stat-card collection-stat-card--labs">
                        <span className="collection-stat-card__label">涉及目录</span>
                        <span className="collection-stat-card__value">{labCount}</span>
                      </div>
                    </div>

                    {/* 用例列表 */}
                    <div className="split-detail-section">
                      <div className="split-detail-section__header">
                        <h4 className="split-detail-section__title">集合用例</h4>
                        {totalInCollection > 0 && <span className="split-detail-section__hint">&nbsp;共 {totalInCollection} 条</span>}
                      </div>

                      {totalInCollection > 0 && (
                        <div className="case-table-toolbar" style={{ marginTop: 8 }}>
                          <input type="search" className="form-input case-table-toolbar__search" value={caseSearch} onChange={e => setCaseSearch(e.target.value)} placeholder="搜索 ID 或标题…" aria-label="搜索集合内用例" />
                          <div className="case-table-toolbar__tabs" role="tablist" aria-label="用例类型">
                            {PICKER_TYPE_FILTERS.map(({ key, label }) => (
                              <button
                                key={key}
                                type="button"
                                role="tab"
                                aria-selected={caseTypeFilter === key}
                                className={caseTypeFilter === key ? 'case-table-toolbar__tab case-table-toolbar__tab--active' : 'case-table-toolbar__tab'}
                                onClick={() => { setCaseTypeFilter(key); setSelectedCaseIds(new Set()); }}
                              >
                                {label}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* 用例批量操作栏 */}
                      {selectedCaseIds.size > 0 && (
                        <div className="case-batch-bar">
                          <span>已选 <span className="case-batch-bar__count">{selectedCaseIds.size}</span> 个用例</span>
                          <div className="case-batch-bar__actions">
                            <button type="button" className="btn btn--danger btn--xs" onClick={handleBatchRemoveCases}>批量移除</button>
                            <button type="button" className="btn btn--ghost btn--xs" onClick={() => setSelectedCaseIds(new Set())}>取消选择</button>
                          </div>
                        </div>
                      )}

                      {totalInCollection === 0 ? (
                        <div className="collection-case-empty" style={{ marginTop: 12 }}>
                          <p className="collection-case-empty__text">此集合暂无用例</p>
                          <button type="button" className="btn btn--primary btn--sm" onClick={openAddModal}>+ 添加用例</button>
                        </div>
                      ) : filteredDetailCases.length === 0 ? (
                        <p className="split-detail-empty-text" style={{ marginTop: 12 }}>没有匹配的用例</p>
                      ) : (
                        <div className="case-table-wrap" style={{ marginTop: 8 }}>
                          <table className="case-table">
                            <thead>
                              <tr>
                                <th className="case-table__cb">
                                  <input
                                    type="checkbox"
                                    checked={isAllCasesSelected}
                                    onChange={toggleAllCases}
                                    style={{ accentColor: 'var(--accent-primary)' }}
                                  />
                                </th>
                                <th className="case-table__type">类型</th>
                                <th className="case-table__id">ID</th>
                                <th className="case-table__title">标题</th>
                                <th className="case-table__lab">所属目录</th>
                                <th className="case-table__status">状态</th>
                                <th className="case-table__actions">操作</th>
                              </tr>
                            </thead>
                            <tbody>
                              {filteredDetailCases.map(row => {
                                const title = getCaseDisplayTitle(row.type, row.id, manualMap, autoMap);
                                const status = row.type === 'manual' ? manualMap.get(row.id)?.status : autoMap.get(row.id)?.status;
                                const labName = row.type === 'manual' ? manualMap.get(row.id)?.lab_name || manualMap.get(row.id)?.lab_id || '—' : '—';
                                const key = `${row.type}-${row.id}`;
                                return (
                                  <tr
                                    key={key}
                                    className={selectedCaseIds.has(key) ? 'case-table__row case-table__row--selected' : 'case-table__row'}
                                  >
                                    <td className="case-table__cb">
                                      <input
                                        type="checkbox"
                                        checked={selectedCaseIds.has(key)}
                                        onChange={() => toggleCaseSelect(row.type, row.id)}
                                        style={{ accentColor: 'var(--accent-primary)' }}
                                      />
                                    </td>
                                    <td><span className={`case-type-badge case-type-badge--${row.type}`}>{getCaseTypeLabel(row.type)}</span></td>
                                    <td><code className="case-table__id">{row.id}</code></td>
                                    <td className="case-table__title" title={title}>{title}</td>
                                    <td className="case-table__lab">{labName}</td>
                                    <td className="case-table__status">{status ? getCaseStatusLabel(status) : '—'}</td>
                                    <td className="case-table__actions">
                                      <button type="button" className="btn btn--ghost btn--xs" style={{ color: 'var(--status-error)', fontSize: 11 }} onClick={() => handleRemoveCase(row.type, row.id)}>移除</button>
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          ) : (
            <DetailEmpty icon="📁" text="从左侧选择一个预制集合查看详情" />
          )}
        </main>
      </div>

      {/* ── 创建 / 编辑弹窗 ── */}
      <CollectionFormModal mode="create" open={createOpen} name={newName} description={newDesc} tags={newTags} submitting={creating} onClose={() => setCreateOpen(false)} onNameChange={setNewName} onDescriptionChange={setNewDesc} onTagsChange={setNewTags} onSubmit={handleCreate} />
      <CollectionFormModal mode="edit" open={editOpen} name={editName} description={editDesc} tags={editTags} submitting={editing} onClose={() => setEditOpen(false)} onNameChange={setEditName} onDescriptionChange={setEditDesc} onTagsChange={setEditTags} onSubmit={handleEdit} />

      {/* ── 添加用例：右侧抽屉 ── */}
      {addOpen && selected && (
        <>
          <div className="drawer-overlay" onClick={() => setAddOpen(false)} />
          <div className="drawer drawer--right">
            <div className="drawer__header">
              <div>
                <h3 className="drawer__title">从用例库添加用例</h3>
                <p className="drawer__subtitle">集合：{selected.name}</p>
              </div>
              <button type="button" className="drawer__close" onClick={() => setAddOpen(false)}>×</button>
            </div>
            <div className="drawer__body">
              <p className="drawer__hint">从用例看板库中勾选要添加的用例。已在集合中的用例将自动排除。</p>
              <CaseLibraryPicker
                items={libraryItems}
                labs={labs}
                loading={libraryLoading}
                selectedManualIds={addSelection.selectedManualIds}
                selectedAutoIds={addSelection.selectedAutoIds}
                onToggleManual={addSelection.toggleManual}
                onToggleAuto={addSelection.toggleAuto}
                excludeManualIds={excludeManualIds}
                excludeAutoIds={excludeAutoIds}
                onSelectFiltered={addSelection.mergeFiltered}
                onClearSelection={addSelection.clear}
                onRefresh={refreshLibrary}
              />
            </div>
            <div className="drawer__footer">
              <span className="collection-add-modal__selection">
                {addSelection.count > 0 ? `已选 ${addSelection.count} 个用例` : '请勾选要添加的用例'}
              </span>
              <button type="button" className="btn btn--secondary" onClick={() => setAddOpen(false)}>取消</button>
              <button type="button" className="btn btn--primary" onClick={handleAddCases} disabled={adding || addSelection.count === 0}>
                {adding ? '添加中…' : `添加${addSelection.count > 0 ? ` (${addSelection.count})` : ''}`}
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
};

export default TestCaseCollectionPage;
