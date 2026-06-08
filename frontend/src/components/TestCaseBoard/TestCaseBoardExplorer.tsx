import { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../../services/api';
import type {
  AutomationTestCaseResponse,
  TestCaseResponse,
  CatalogLab,
} from '../../types';
import CatalogTreeSidebar from '../catalog/CatalogTreeSidebar';
import TestCaseBoardDetail from './TestCaseBoardDetail';
import TestCaseBoardKanban from './TestCaseBoardKanban';
import {
  type UnifiedCaseItem,
  type TypeFilter,
  type DetailTab,
  TYPE_FILTERS,
  STATUS_FILTERS,
  getManualDot,
  getAutoDot,
  fwIcon,
  fwColor,
} from './testCaseBoardTypes';
import { boardStyles as S } from './testCaseBoardStyles';

type ViewMode = 'list' | 'kanban';

interface TestCaseBoardExplorerProps {
  autoCases: AutomationTestCaseResponse[];
  manualCases: TestCaseResponse[];
  unifiedList: UnifiedCaseItem[];
  loading: boolean;
  userNameMap: Map<string, string>;
  labs: CatalogLab[];
  selectedLabId: string;
  onRefresh: () => void;
  onCreateAuto: () => void;
  onCreateManual: () => void;
}

const TestCaseBoardExplorer: React.FC<TestCaseBoardExplorerProps> = ({
  autoCases,
  manualCases,
  unifiedList,
  loading,
  userNameMap,
  labs,
  selectedLabId: initialLabId,
  onRefresh,
  onCreateAuto,
  onCreateManual,
}) => {
  // ── Catalog states ──
  const [showCatalog, setShowCatalog] = useState(true);
  const [selectedLabId, setSelectedLabId] = useState(initialLabId);
  const [catalogPrefix, setCatalogPrefix] = useState<string[]>([]);

  // ── Filter states ──
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [frameworkFilter, setFrameworkFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // ── View ──
  const [viewMode, setViewMode] = useState<ViewMode>('list');

  // ── Selection ──
  const [selectedCase, setSelectedCase] = useState<UnifiedCaseItem | null>(null);
  const [detailTab, setDetailTab] = useState<DetailTab>('info');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // ── Dispatch modal ──
  const [showDispatchModal, setShowDispatchModal] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [dispatchError, setDispatchError] = useState<string | null>(null);
  const [dispatchSuccess, setDispatchSuccess] = useState<string | null>(null);

  // ── Sync lab selection ──
  useEffect(() => {
    if (initialLabId) setSelectedLabId(initialLabId);
  }, [initialLabId]);

  // ── Derived ──
  const catalogVisible = showCatalog && (typeFilter === 'all' || typeFilter === 'manual');
  const selectedLabName = useMemo(
    () => labs.find(l => l.lab_id === selectedLabId)?.name || '',
    [labs, selectedLabId],
  );

  // ── Framework counts for filter chips ──
  const frameworkCounts = useMemo(() => {
    const map = new Map<string, number>();
    for (const ac of autoCases) {
      const fw = ac.framework || '其他';
      map.set(fw, (map.get(fw) || 0) + 1);
    }
    return Array.from(map.entries()).sort(([, a], [, b]) => b - a);
  }, [autoCases]);

  // ── Filtered list ──
  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return unifiedList.filter(item => {
      if (typeFilter !== 'all' && item.type !== typeFilter) return false;
      if (statusFilter !== 'all' && item.status !== statusFilter) return false;
      if (frameworkFilter !== 'all' && item.type === 'auto' && (item.framework || '其他') !== frameworkFilter) return false;
      // Catalog filter
      if (item.type === 'manual' && catalogPrefix.length > 0) {
        const d = item.manualData!;
        if (d.lab_id !== selectedLabId) return false;
        if (catalogPrefix.length > 0) {
          const casePath = d.catalog_path || [];
          if (casePath.length < catalogPrefix.length) return false;
          for (let i = 0; i < catalogPrefix.length; i++) {
            if (casePath[i] !== catalogPrefix[i]) return false;
          }
        }
      }
      // Search
      if (!q) return true;
      return (
        item.title.toLowerCase().includes(q) ||
        item.caseId.toLowerCase().includes(q) ||
        (item.framework || '').toLowerCase().includes(q)
      );
    });
  }, [unifiedList, typeFilter, statusFilter, frameworkFilter, searchQuery, catalogPrefix, selectedLabId]);

  // ── Breadcrumb parts ──
  const breadcrumbParts = useMemo((): string[] => {
    if (!selectedLabId) return [];
    if (catalogPrefix.length === 0) return [selectedLabName || 'Lab', '全部用例'];
    return [selectedLabName || 'Lab', ...catalogPrefix];
  }, [selectedLabId, selectedLabName, catalogPrefix]);

  // ── Dispatch ──
  const selectedAutoId = useMemo(() => {
    if (selectedIds.size > 0) return Array.from(selectedIds);
    return selectedCase?.type === 'auto' ? [selectedCase.caseId] : [];
  }, [selectedIds, selectedCase]);

  const handleDispatch = async () => {
    if (selectedAutoId.length === 0) return;
    setDispatching(true);
    setDispatchError(null);
    setDispatchSuccess(null);
    try {
      const res = await api.dispatchTask({
        cases: selectedAutoId.map(id => ({ auto_case_id: id })),
      });
      if (res.code === 0 || res.code === 200) {
        setDispatchSuccess(`成功下发 ${selectedAutoId.length} 个，任务ID: ${res.data?.task_id}`);
        setSelectedIds(new Set());
        setTimeout(() => { setShowDispatchModal(false); setDispatchSuccess(null); }, 2000);
      } else {
        setDispatchError(res.message || '下发任务失败');
      }
    } catch {
      setDispatchError('下发任务失败');
    } finally {
      setDispatching(false);
    }
  };

  // ── Handlers ──
  const handleSelect = (caseId: string) => {
    setSelectedIds(prev => {
      const n = new Set(prev);
      n.has(caseId) ? n.delete(caseId) : n.add(caseId);
      return n;
    });
  };

  const handleCaseClick = (item: UnifiedCaseItem) => {
    setSelectedCase(item);
    setDetailTab('info');
  };

  const handleTypeFilterChange = (key: TypeFilter) => {
    setTypeFilter(key);
    setFrameworkFilter('all');
  };

  // ── Reset detail tab on selection change ──
  useEffect(() => {
    if (selectedCase) setDetailTab('info');
  }, [selectedCase?.id]);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
      {/* ── Filter Bar ── */}
      <div style={S.filterBar}>
        <div style={S.filterLeft}>
          {/* Search */}
          <input
            className="form-input"
            style={S.searchInput}
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="搜索用例名称、ID..."
          />

          {/* Type segmented control */}
          <div className="segmented-control">
            {TYPE_FILTERS.map(tf => (
              <button
                key={tf.key}
                className={`segmented-control__btn ${typeFilter === tf.key ? 'segmented-control__btn--active' : ''}`}
                onClick={() => handleTypeFilterChange(tf.key)}
              >
                {tf.icon} {tf.label}
              </button>
            ))}
          </div>

          {/* Status dropdown */}
          <select
            className="form-input form-select"
            style={{ width: 120, fontSize: 12 }}
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
          >
            <option value="all">全部状态</option>
            {STATUS_FILTERS.filter(s => s.value === 'all' || (typeFilter !== 'all' ? s.type === typeFilter : true)).map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>

          {/* Bulk actions */}
          {selectedIds.size > 0 && (
            <div style={S.bulkBar}>
              <span style={S.bulkLabel}>已选 {selectedIds.size}</span>
              <button className="btn btn--primary btn--sm" onClick={() => setShowDispatchModal(true)}>批量下发</button>
              <button className="btn btn--ghost btn--sm" onClick={() => setSelectedIds(new Set())}>取消</button>
            </div>
          )}
        </div>

        <div style={S.filterRight}>
          {/* List/Kanban toggle */}
          <div style={S.viewToggle}>
            <button
              type="button"
              style={S.viewToggleBtn(viewMode === 'list')}
              onClick={() => setViewMode('list')}
              title="列表视图"
            >
              ☰
            </button>
            <button
              type="button"
              style={S.viewToggleBtn(viewMode === 'kanban')}
              onClick={() => setViewMode('kanban')}
              title="看板视图"
            >
              ▦
            </button>
          </div>

          <button className="btn btn--ghost btn--sm" onClick={onRefresh} disabled={loading} title="刷新">
            {loading ? '\u22EF' : '\u21BB'}
          </button>

          <button className="btn btn--primary btn--sm" onClick={onCreateAuto}>+ 自动化</button>
          <button className="btn btn--secondary btn--sm" onClick={onCreateManual}>+ 手工</button>
        </div>
      </div>

      {/* ── Framework filter chips ── */}
      {!catalogVisible && (typeFilter === 'all' || typeFilter === 'auto') && frameworkCounts.length > 0 && (
        <div style={S.frameworkChips}>
          <button
            onClick={() => setFrameworkFilter('all')}
            style={{
              ...S.frameworkChip,
              background: frameworkFilter === 'all' ? 'color-mix(in srgb, var(--accent-primary) 15%, transparent)' : 'var(--surface-tertiary)',
              color: frameworkFilter === 'all' ? 'var(--accent-primary)' : 'var(--text-secondary)',
              fontWeight: frameworkFilter === 'all' ? 600 : 500,
            }}
          >全部框架</button>
          {frameworkCounts.map(([fw, count]) => (
            <button
              key={fw}
              onClick={() => setFrameworkFilter(fw)}
              style={{
                ...S.frameworkChip,
                background: frameworkFilter === fw ? `${fwColor(fw)}20` : 'var(--surface-tertiary)',
                color: frameworkFilter === fw ? fwColor(fw) : 'var(--text-secondary)',
                fontWeight: frameworkFilter === fw ? 600 : 500,
              }}
            >{fwIcon(fw)} {fw} {count}</button>
          ))}
        </div>
      )}

      {/* ── Main Split ── */}
      <div className="split-workspace">
        {/* Left Panel */}
        <div className="split-workspace__list" style={{ width: 320, minWidth: 280 }}>
          {/* Catalog Tree */}
          {catalogVisible && selectedLabId && (
            <>
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '6px 10px', borderBottom: '1px solid var(--border-subtle)',
                cursor: 'pointer', userSelect: 'none',
              }} onClick={() => setShowCatalog(!showCatalog)}>
                <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', display: 'flex', alignItems: 'center', gap: 4 }}>
                  {'\uD83D\uDCC1'} 目录 {catalogPrefix.length > 0 && `(${breadcrumbParts.join(' / ')})`}
                </span>
                <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{showCatalog ? '收起 \u25B4' : '展开 \u25BE'}</span>
              </div>
              {showCatalog && (
                <div style={{ maxHeight: 240, overflow: 'hidden', display: 'flex', flexDirection: 'column', borderBottom: '1px solid var(--border-subtle)' }}>
                  <CatalogTreeSidebar
                    labs={labs}
                    selectedLabId={selectedLabId}
                    selectedPrefix={catalogPrefix}
                    onSelectLab={labId => {
                      setSelectedLabId(labId);
                      setCatalogPrefix([]);
                    }}
                    onSelectPrefix={prefix => setCatalogPrefix(prefix)}
                  />
                </div>
              )}
            </>
          )}

          {/* Case List Header */}
          <div style={{
            padding: '6px 10px', borderBottom: '1px solid var(--border-subtle)', fontSize: 11, fontWeight: 600,
            color: 'var(--text-tertiary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span>用例列表</span>
              {catalogPrefix.length > 0 && (
                <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--accent-primary)', fontWeight: 500, background: 'color-mix(in srgb, var(--accent-primary) 10%, transparent)', padding: '1px 6px', borderRadius: 4 }}>
                  {catalogPrefix.join(' > ')}
                </span>
              )}
            </div>
            <span>{filtered.length}/{unifiedList.length}</span>
          </div>

          {/* Case content: list or kanban */}
          {viewMode === 'list' ? (
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {loading && unifiedList.length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>加载中...</div>
              ) : filtered.length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>
                  {searchQuery || typeFilter !== 'all' || statusFilter !== 'all' || catalogPrefix.length > 0 ? '无匹配的用例' : '暂无用例'}
                </div>
              ) : filtered.map(item => {
                const isSelected = selectedCase?.id === item.id;
                const isChecked = selectedIds.has(item.caseId);
                const isManual = item.type === 'manual';
                const dotColor = isManual ? getManualDot(item.status) : getAutoDot(item.status);

                return (
                  <div
                    key={`${item.type}-${item.id}`}
                    onClick={() => handleCaseClick(item)}
                    style={S.listItem(isSelected)}
                  >
                    <div style={S.listItemRow}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onClick={e => e.stopPropagation()}
                        onChange={() => handleSelect(item.caseId)}
                        style={{ accentColor: 'var(--accent-primary)', flexShrink: 0 }}
                      />
                      <span style={S.statusDot(dotColor)} />
                      <span style={{
                        fontSize: 13, fontWeight: isSelected ? 600 : 500, color: 'var(--text-primary)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
                      }}>
                        {item.title}
                      </span>
                    </div>
                    <div style={S.listItemMeta}>
                      <span style={S.typeBadge(isManual)}>
                        {isManual ? '\uD83D\uDCCB 手工' : '\u26A1 自动'}
                      </span>
                      {!isManual && item.framework && (
                        <span style={S.frameworkTag(fwColor(item.framework))}>
                          {fwIcon(item.framework)} {item.framework}
                        </span>
                      )}
                      <span style={S.idTag}>{item.caseId}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <TestCaseBoardKanban
              items={filtered}
              typeFilter={typeFilter}
              onCaseClick={handleCaseClick}
            />
          )}
        </div>

        {/* Right Panel: Detail */}
        <div className="split-workspace__main">
          <TestCaseBoardDetail
            item={selectedCase}
            activeTab={detailTab}
            onTabChange={setDetailTab}
            onOpenDispatch={() => setShowDispatchModal(true)}
            onRefresh={onRefresh}
          />
        </div>
      </div>

      {/* ── Dispatch Modal ── */}
      {showDispatchModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div onClick={e => e.stopPropagation()} style={{ background: 'var(--bg-elevated)', borderRadius: 12, width: 420, maxWidth: '90vw', boxShadow: '0 20px 60px rgba(0,0,0,0.4)', border: '1px solid var(--border-default)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>下发任务</h3>
              <button style={{ fontSize: 22, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => setShowDispatchModal(false)}>{'\u00D7'}</button>
            </div>
            <div style={{ padding: 20 }}>
              <p style={{ margin: '0 0 12', fontSize: 14, color: 'var(--text-secondary)' }}>
                将 <strong>{selectedAutoId.length}</strong> 个自动化用例下发到执行队列
              </p>
              {selectedAutoId.map(id => (
                <div key={id} style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-tertiary)', padding: '4px 0' }}>{'\u26A1'} {id}</div>
              ))}
              {dispatchError && <div style={{ padding: '10px 14px', background: 'var(--status-error-bg)', borderRadius: 6, fontSize: 13, color: 'var(--status-error)', marginTop: 12 }}>{'\u26A0'} {dispatchError}</div>}
              {dispatchSuccess && <div style={{ padding: '10px 14px', background: 'var(--status-success-bg)', borderRadius: 6, fontSize: 13, color: 'var(--status-success)', marginTop: 12 }}>{'\u2713'} {dispatchSuccess}</div>}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, padding: '14px 20px', borderTop: '1px solid var(--border-subtle)' }}>
              <button className="btn btn--secondary" onClick={() => setShowDispatchModal(false)} disabled={dispatching}>取消</button>
              <button className="btn btn--primary" onClick={handleDispatch} disabled={dispatching || Boolean(dispatchSuccess)}>
                {dispatching ? '下发中...' : '确认下发'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TestCaseBoardExplorer;
