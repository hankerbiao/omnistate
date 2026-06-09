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
import {
  getCaseDisplayTitle,
  getCaseTypeLabel,
  getCaseStatusLabel,
  PICKER_TYPE_FILTERS,
  type TypeFilter,
} from './TestCaseBoard/testCaseBoardTypes';
import {
  DetailHeader,
  DetailStatGrid,
  DetailSection,
  DetailEmpty,
  DetailMetaRow,
} from './ui/SplitDetailPanel';

interface TestCaseCollectionPageProps {
  currentUserId: string;
}

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
  mode,
  open,
  name,
  description,
  tags,
  submitting,
  onClose,
  onNameChange,
  onDescriptionChange,
  onTagsChange,
  onSubmit,
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

interface CollectionCaseRowProps {
  caseId: string;
  type: 'manual' | 'auto';
  manualMap: Map<string, TestCaseResponse>;
  autoMap: Map<string, AutomationTestCaseResponse>;
  onRemove: () => void;
}

function CollectionCaseRow({ caseId, type, manualMap, autoMap, onRemove }: CollectionCaseRowProps) {
  const title = getCaseDisplayTitle(type, caseId, manualMap, autoMap);
  const status = type === 'manual' ? manualMap.get(caseId)?.status : autoMap.get(caseId)?.status;
  return (
    <tr className="collection-case-table__row">
      <td><span className={`case-type-badge case-type-badge--${type}`}>{getCaseTypeLabel(type)}</span></td>
      <td><code className="collection-case-table__id">{caseId}</code></td>
      <td className="collection-case-table__title">{title}</td>
      <td><span className="collection-case-table__status">{status ? getCaseStatusLabel(status) : '—'}</span></td>
      <td className="collection-case-table__actions">
        <button type="button" className="btn btn--ghost btn--sm collection-case-row__remove" onClick={onRemove}>移除</button>
      </td>
    </tr>
  );
}

const TestCaseCollectionPage: React.FC<TestCaseCollectionPageProps> = ({ currentUserId }) => {
  const { items: libraryItems, manualMap, autoMap, labs, loading: libraryLoading, refresh: refreshLibrary } = useCaseLibrary();
  const [collections, setCollections] = useState<CollectionListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selected, setSelected] = useState<CollectionResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
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
  const [addOpen, setAddOpen] = useState(false);
  const addSelection = useDualCaseSelection();
  const [adding, setAdding] = useState(false);
  const [caseSearch, setCaseSearch] = useState('');
  const [caseTypeFilter, setCaseTypeFilter] = useState<TypeFilter>('all');
  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  const initialSelectedRef = useRef(false);

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

  const listStats = useMemo(() => ({
    count: collections.length,
    totalCases: collections.reduce((sum, c) => sum + c.case_count + c.auto_case_count, 0),
  }), [collections]);

  const openAddModal = () => {
    addSelection.reset();
    setAddOpen(true);
    refreshLibrary();
  };

  const excludeManualIds = useMemo(() => new Set(selected?.case_ids || []), [selected?.case_ids]);
  const excludeAutoIds = useMemo(() => new Set(selected?.auto_case_ids || []), [selected?.auto_case_ids]);

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

  const handleDelete = async () => {
    if (!selected) return;
    if (!window.confirm(`确定删除集合「${selected.name}」吗？`)) return;
    setError(null);
    try {
      await api.deleteCollection(selected.collection_id);
      setSelected(null);
      await fetchCollections();
    } catch (err) {
      setError('删除集合失败');
      console.error(err);
    }
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
      await fetchDetail(selected.collection_id);
      await fetchCollections();
    } catch (err) {
      setError('移除用例失败');
      console.error(err);
    }
  };

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
  const canDelete = selected ? currentUserId === 'admin' || currentUserId === selected.created_by : false;
  const closeDetail = () => setSelected(null);

  return (
    <>
      {error && (
        <div className="error-banner collection-page__error">
          <span>⚠ {error}</span>
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className={`collection-page split-workspace${selected ? ' split-workspace--has-selection' : ''}`}>
        <aside className="split-workspace__list">
          <div className="split-panel-toolbar">
            <PageToolbar
              meta={(
                <>
                  <StatPill label="集合数" value={listStats.count} />
                  <StatPill label="总用例数" value={listStats.totalCases} tone="info" />
                </>
              )}
              actions={(
                <button type="button" className="btn btn--primary btn--sm" onClick={() => setCreateOpen(true)}>
                  + 新建预制集合
                </button>
              )}
            />
          </div>
          <div className="filter-strip">
            <input type="search" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="搜索集合名称、描述…" className="form-input" aria-label="搜索集合" />
            <button type="button" className="btn btn--secondary btn--sm" onClick={() => fetchCollections(searchQuery || undefined)} disabled={loading}>刷新</button>
          </div>
          <div className="split-list-scroll collection-list-table-wrap">
            {loading && collections.length === 0 ? (
              <div className="loading-overlay"><div className="loading-spinner" /></div>
            ) : collections.length === 0 ? (
              <div className="empty-state"><div className="empty-state__icon">📁</div><p className="empty-state__text">{searchQuery ? '没有匹配的预制集合' : '暂无用例预制集'}</p></div>
            ) : (
              <table className="data-table collection-list-table">
                <thead>
                  <tr>
                    <th>名称</th>
                    <th className="collection-list-table__col-id">ID</th>
                    <th className="collection-list-table__col-num">手工</th>
                    <th className="collection-list-table__col-num">自动</th>
                    <th className="collection-list-table__col-time">更新</th>
                  </tr>
                </thead>
                <tbody>
                  {collections.map(c => (
                    <tr
                      key={c.collection_id}
                      className={selected?.collection_id === c.collection_id ? 'collection-list-table__row selected' : 'collection-list-table__row'}
                      onClick={() => fetchDetail(c.collection_id)}
                    >
                      <td className="collection-list-table__name">{c.name}</td>
                      <td><code className="collection-list-table__id">{c.collection_id}</code></td>
                      <td className="collection-list-table__num">{c.case_count}</td>
                      <td className="collection-list-table__num">{c.auto_case_count}</td>
                      <td className="collection-list-table__time" title={new Date(c.updated_at).toLocaleString('zh-CN')}>{formatRelativeTime(c.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </aside>

        <main className="split-workspace__main">
          {selected ? (
            <div className="split-detail-scroll">
              <button type="button" className="split-workspace__back" onClick={closeDetail}>← 返回列表</button>
              {detailLoading ? (
                <div className="loading-overlay"><div className="loading-spinner" /></div>
              ) : (
                <>
                  <DetailHeader
                    id={selected.collection_id}
                    title={selected.name}
                    subtitle={selected.description || undefined}
                    badges={(selected.tags || []).map(t => <span key={t} className="collection-tag">{t}</span>)}
                    actions={(
                      <>
                        <button type="button" className="btn btn--primary btn--sm" onClick={openAddModal}>添加用例</button>
                        <button type="button" className="btn btn--secondary btn--sm" onClick={openEdit}>编辑</button>
                        {canDelete && <button type="button" className="btn btn--danger btn--sm" onClick={handleDelete}>删除</button>}
                      </>
                    )}
                  />
                  <div className="split-detail-content">
                    <DetailStatGrid stats={[
                      { label: '手工用例', value: manualCount },
                      { label: '自动化用例', value: autoCount },
                      { label: '合计', value: totalInCollection },
                    ]} />
                    <div className="split-detail-meta-block">
                      <DetailMetaRow label="创建人" value={selected.created_by} />
                      <DetailMetaRow label="更新时间" value={`${formatRelativeTime(selected.updated_at)}（${new Date(selected.updated_at).toLocaleString('zh-CN')}）`} />
                    </div>
                    <DetailSection title="集合用例" hint={totalInCollection > 0 ? `共 ${totalInCollection} 条` : undefined}>
                      {totalInCollection > 0 && (
                        <div className="collection-case-filters">
                          <input type="search" className="form-input collection-case-filters__search" value={caseSearch} onChange={e => setCaseSearch(e.target.value)} placeholder="搜索 ID 或标题…" aria-label="搜索集合内用例" />
                          <div className="collection-case-filters__tabs" role="tablist" aria-label="用例类型">
                            {PICKER_TYPE_FILTERS.map(({ key, label }) => (
                              <button
                                key={key}
                                type="button"
                                role="tab"
                                aria-selected={caseTypeFilter === key}
                                className={caseTypeFilter === key ? 'collection-case-filters__tab collection-case-filters__tab--active' : 'collection-case-filters__tab'}
                                onClick={() => setCaseTypeFilter(key)}
                              >
                                {label}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                      {totalInCollection === 0 ? (
                        <div className="collection-case-empty">
                          <p className="collection-case-empty__text">此集合暂无用例</p>
                          <button type="button" className="btn btn--primary btn--sm" onClick={openAddModal}>+ 添加用例</button>
                        </div>
                      ) : filteredDetailCases.length === 0 ? (
                        <p className="split-detail-empty-text">没有匹配的用例</p>
                      ) : (
                        <div className="collection-case-table-wrap">
                          <table className="data-table collection-case-table">
                            <thead>
                              <tr>
                                <th style={{ width: 88 }}>类型</th>
                                <th style={{ width: 120 }}>ID</th>
                                <th>标题</th>
                                <th style={{ width: 96 }}>状态</th>
                                <th style={{ width: 72 }}>移除</th>
                              </tr>
                            </thead>
                            <tbody>
                              {filteredDetailCases.map(row => (
                                <CollectionCaseRow key={`${row.type}-${row.id}`} caseId={row.id} type={row.type} manualMap={manualMap} autoMap={autoMap} onRemove={() => handleRemoveCase(row.type, row.id)} />
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </DetailSection>
                  </div>
                </>
              )}
            </div>
          ) : (
            <DetailEmpty icon="📁" text="从左侧选择一个预制集合查看详情" />
          )}
        </main>
      </div>

      <CollectionFormModal mode="create" open={createOpen} name={newName} description={newDesc} tags={newTags} submitting={creating} onClose={() => setCreateOpen(false)} onNameChange={setNewName} onDescriptionChange={setNewDesc} onTagsChange={setNewTags} onSubmit={handleCreate} />
      <CollectionFormModal mode="edit" open={editOpen} name={editName} description={editDesc} tags={editTags} submitting={editing} onClose={() => setEditOpen(false)} onNameChange={setEditName} onDescriptionChange={setEditDesc} onTagsChange={setEditTags} onSubmit={handleEdit} />

      {addOpen && selected && (
        <div className="modal-overlay" onClick={() => setAddOpen(false)}>
          <div className="modal modal--wide collection-add-modal" onClick={e => e.stopPropagation()}>
            <div className="modal__header">
              <div>
                <h3 className="modal__title">从用例库添加用例</h3>
                <p className="collection-add-modal__subtitle">集合：{selected.name}</p>
              </div>
              <button type="button" className="modal__close" onClick={() => setAddOpen(false)}>×</button>
            </div>
            <div className="modal__body collection-add-modal__body">
              <p className="collection-add-modal__hint">从用例看板库中勾选要添加的用例。已在集合中的用例将自动排除。</p>
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
            <div className="modal__footer">
              <span className="collection-add-modal__selection">{addSelection.count > 0 ? `已选 ${addSelection.count} 个用例` : '请勾选要添加的用例'}</span>
              <button type="button" className="btn btn--secondary" onClick={() => setAddOpen(false)}>取消</button>
              <button type="button" className="btn btn--primary" onClick={handleAddCases} disabled={adding || addSelection.count === 0}>
                {adding ? '添加中…' : `添加${addSelection.count > 0 ? ` (${addSelection.count})` : ''}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default TestCaseCollectionPage;
