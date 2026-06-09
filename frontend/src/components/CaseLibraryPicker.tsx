import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../services/api';
import { getCatalogLabs } from '../services/catalogLabsCache';
import type { AutomationTestCaseResponse, TestCaseResponse, CatalogLab } from '../types';
import CatalogTreeSidebar from './catalog/CatalogTreeSidebar';
import {
  buildLabMap,
  buildUnifiedCaseList,
  getCaseStatusLabel,
  getCaseTypeLabel,
  matchesCatalogPrefix,
  PICKER_TYPE_FILTERS,
  type TypeFilter,
  type UnifiedCaseItem,
} from './TestCaseBoard/testCaseBoardTypes';
import { toggleInSet } from '../utils/setHelpers';

export function useDualCaseSelection() {
  const [selectedManualIds, setSelectedManualIds] = useState<Set<string>>(new Set());
  const [selectedAutoIds, setSelectedAutoIds] = useState<Set<string>>(new Set());

  const toggleManual = useCallback((caseId: string) => {
    setSelectedManualIds(prev => toggleInSet(prev, caseId));
  }, []);

  const toggleAuto = useCallback((autoCaseId: string) => {
    setSelectedAutoIds(prev => toggleInSet(prev, autoCaseId));
  }, []);

  const mergeFiltered = useCallback((manualIds: string[], autoIds: string[]) => {
    setSelectedManualIds(prev => {
      const next = new Set(prev);
      manualIds.forEach(id => next.add(id));
      return next;
    });
    setSelectedAutoIds(prev => {
      const next = new Set(prev);
      autoIds.forEach(id => next.add(id));
      return next;
    });
  }, []);

  const clear = useCallback(() => {
    setSelectedManualIds(new Set());
    setSelectedAutoIds(new Set());
  }, []);

  const count = selectedManualIds.size + selectedAutoIds.size;

  return {
    selectedManualIds,
    selectedAutoIds,
    toggleManual,
    toggleAuto,
    mergeFiltered,
    clear,
    reset: clear,
    count,
  };
}

export function useCaseLibrary() {
  const [manualCases, setManualCases] = useState<TestCaseResponse[]>([]);
  const [autoCases, setAutoCases] = useState<AutomationTestCaseResponse[]>([]);
  const [labs, setLabs] = useState<CatalogLab[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [autoRes, manualRes, labItems] = await Promise.all([
        api.listAutomationTestCases({ limit: 200 }),
        api.listTestCases({ limit: 200 }),
        getCatalogLabs({ active_only: false }).catch(() => [] as CatalogLab[]),
      ]);
      setAutoCases(autoRes.data || []);
      setManualCases(manualRes.data || []);
      setLabs(labItems);
    } catch {
      /* ignore */
    }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const manualMap = useMemo(() => {
    const m = new Map<string, TestCaseResponse>();
    for (const c of manualCases) m.set(c.case_id, c);
    return m;
  }, [manualCases]);

  const autoMap = useMemo(() => {
    const m = new Map<string, AutomationTestCaseResponse>();
    for (const c of autoCases) m.set(c.auto_case_id, c);
    return m;
  }, [autoCases]);

  const labMap = useMemo(() => buildLabMap(labs), [labs]);

  const items = useMemo(
    () => buildUnifiedCaseList(manualCases, autoCases, labMap),
    [manualCases, autoCases, labMap],
  );

  return { items, manualMap, autoMap, labs, loading, refresh };
}

function isItemExcluded(
  item: UnifiedCaseItem,
  excludeManualIds?: Set<string>,
  excludeAutoIds?: Set<string>,
): boolean {
  if (item.type === 'manual' && excludeManualIds?.has(item.caseId)) return true;
  if (item.type === 'auto' && excludeAutoIds?.has(item.caseId)) return true;
  return false;
}

function isItemSelected(
  item: UnifiedCaseItem,
  selectedManualIds: Set<string>,
  selectedAutoIds: Set<string>,
): boolean {
  if (item.type === 'manual') return selectedManualIds.has(item.caseId);
  return selectedAutoIds.has(item.caseId);
}

export interface CaseLibraryPickerProps {
  items: UnifiedCaseItem[];
  labs?: CatalogLab[];
  loading?: boolean;
  selectedManualIds: Set<string>;
  selectedAutoIds: Set<string>;
  onToggleManual: (caseId: string) => void;
  onToggleAuto: (autoCaseId: string) => void;
  excludeManualIds?: Set<string>;
  excludeAutoIds?: Set<string>;
  onSelectFiltered?: (manualIds: string[], autoIds: string[]) => void;
  onClearSelection?: () => void;
  showCatalog?: boolean;
  onRefresh?: () => void;
}
const IconSearch = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

const IconRefresh = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" />
    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
  </svg>
);

export default function CaseLibraryPicker({
  items,
  labs = [],
  loading = false,
  selectedManualIds,
  selectedAutoIds,
  onToggleManual,
  onToggleAuto,
  excludeManualIds,
  excludeAutoIds,
  onSelectFiltered,
  onClearSelection,
  showCatalog: showCatalogProp = true,
  onRefresh,
}: CaseLibraryPickerProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const [showCatalog, setShowCatalog] = useState(showCatalogProp);
  const [selectedLabId, setSelectedLabId] = useState('');
  const [selectedPrefix, setSelectedPrefix] = useState<string[]>([]);

  useEffect(() => {
    if (!selectedLabId && labs.length > 0) {
      setSelectedLabId(labs[0].lab_id);
    }
  }, [labs, selectedLabId]);

  const filtered = useMemo(() => {
    return items.filter(item => {
      if (typeFilter !== 'all' && item.type !== typeFilter) return false;
      if (!matchesCatalogPrefix(item.catalogPath, selectedPrefix)) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (!item.title.toLowerCase().includes(q) && !item.caseId.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [items, typeFilter, selectedPrefix, searchQuery]);

  const selectableFiltered = useMemo(
    () => filtered.filter(item => !isItemExcluded(item, excludeManualIds, excludeAutoIds)),
    [filtered, excludeManualIds, excludeAutoIds],
  );

  const allFilteredSelected = selectableFiltered.length > 0
    && selectableFiltered.every(item => isItemSelected(item, selectedManualIds, selectedAutoIds));

  const selectedCount = selectedManualIds.size + selectedAutoIds.size;

  const handleToggleItem = (item: UnifiedCaseItem) => {
    if (isItemExcluded(item, excludeManualIds, excludeAutoIds)) return;
    if (item.type === 'manual') onToggleManual(item.caseId);
    else onToggleAuto(item.caseId);
  };

  const handleSelectAllFiltered = () => {
    if (!onSelectFiltered) return;
    const manualIds: string[] = [];
    const autoIds: string[] = [];
    for (const item of selectableFiltered) {
      if (item.type === 'manual') manualIds.push(item.caseId);
      else autoIds.push(item.caseId);
    }
    onSelectFiltered(manualIds, autoIds);
  };

  return (
    <div className="case-library-picker">
      <div className="case-library-picker__toolbar">
        {!showCatalog && showCatalogProp && labs.length > 0 && (
          <button
            type="button"
            className="case-library-picker__catalog-toggle"
            onClick={() => setShowCatalog(true)}
            title="显示目录"
          >
            ▶
          </button>
        )}

        <div className="case-library-picker__search">
          <span className="case-library-picker__search-icon"><IconSearch /></span>
          <input
            type="search"
            className="case-library-picker__search-input"
            placeholder="搜索用例名称或 ID…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            aria-label="搜索用例"
          />
        </div>

        <div className="case-library-picker__type-filter">
          {PICKER_TYPE_FILTERS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              className={'case-library-picker__type-btn' + (typeFilter === key ? ' case-library-picker__type-btn--active' : '')}
              onClick={() => setTypeFilter(key)}
            >
              {label}
            </button>
          ))}
        </div>

        <span className="case-library-picker__count">
          {filtered.length} / {items.length}
        </span>

        {selectedCount > 0 && (
          <span className="case-library-picker__selected-count">
            已选 {selectedCount}
          </span>
        )}

        {onRefresh && (
          <button type="button" className="case-library-picker__refresh-btn" onClick={onRefresh} title="刷新">
            <IconRefresh />
          </button>
        )}
      </div>

      <div className="case-library-picker__actions">
        <label className="case-library-picker__select-all">
          <input
            type="checkbox"
            checked={allFilteredSelected}
            disabled={selectableFiltered.length === 0}
            onChange={() => {
              if (allFilteredSelected) {
                onClearSelection?.();
              } else {
                handleSelectAllFiltered();
              }
            }}
          />
          <span>全选当前筛选结果 ({selectableFiltered.length})</span>
        </label>
        {selectedCount > 0 && onClearSelection && (
          <button type="button" className="case-library-picker__clear-btn" onClick={onClearSelection}>
            清除选择
          </button>
        )}
      </div>
      <div className="case-library-picker__body">
        {showCatalog && showCatalogProp && labs.length > 0 && (
          <div className="case-library-picker__sidebar">
            <div className="case-library-picker__sidebar-header">
              <span>目录</span>
              <button
                type="button"
                className="case-library-picker__sidebar-close"
                onClick={() => setShowCatalog(false)}
              >
                ×
              </button>
            </div>
            <div className="case-library-picker__sidebar-tree">
              <CatalogTreeSidebar
                labs={labs}
                selectedLabId={selectedLabId}
                selectedPrefix={selectedPrefix}
                onSelectLab={labId => { setSelectedLabId(labId); setSelectedPrefix([]); }}
                onSelectPrefix={prefix => setSelectedPrefix(prefix)}
              />
            </div>
          </div>
        )}

        <div className="case-library-picker__list-wrap">
          {loading && filtered.length === 0 ? (
            <div className="case-library-picker__empty">加载中…</div>
          ) : filtered.length === 0 ? (
            <div className="case-library-picker__empty">没有匹配的用例</div>
          ) : (
            <ul className="case-library-picker__list">
              {filtered.map(item => {
                const excluded = isItemExcluded(item, excludeManualIds, excludeAutoIds);
                const selected = isItemSelected(item, selectedManualIds, selectedAutoIds);
                return (
                  <li
                    key={item.type + '-' + item.caseId}
                    className={'case-library-picker__row' + (selected ? ' case-library-picker__row--selected' : '') + (excluded ? ' case-library-picker__row--excluded' : '')}
                  >
                    <label className="case-library-picker__row-label">
                      <input
                        type="checkbox"
                        checked={selected}
                        disabled={excluded}
                        onChange={() => handleToggleItem(item)}
                      />
                      <span className={'case-type-badge case-type-badge--' + item.type}>
                        {getCaseTypeLabel(item.type)}
                      </span>
                      <span className="case-library-picker__case-id">{item.caseId}</span>
                      <span className="case-library-picker__title">{item.title}</span>
                      <span className="case-library-picker__status">
                        {getCaseStatusLabel(item.status)}
                      </span>
                      {item.labName && (
                        <span className="case-library-picker__lab">{item.labName}</span>
                      )}
                      {excluded && (
                        <span className="case-library-picker__excluded-tag">已在集合中</span>
                      )}
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
