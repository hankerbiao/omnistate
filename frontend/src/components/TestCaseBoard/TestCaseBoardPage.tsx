/** 用例看板 — 左侧多级 Lab 目录树 + 右侧卡片网格 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../../services/api';
import { getCatalogLabs } from '../../services/catalogLabsCache';
import type {
  AutomationTestCaseResponse,
  TestCaseResponse,
  CatalogLab,
} from '../../types';
import CreateAutomationTestCaseForm from '../CreateAutomationTestCaseForm';
import CreateTestCaseForm from '../CreateTestCaseForm';
import TestCaseDetailModal from '../TestCaseDetailModal';
import AutomationCaseDetailModal from '../AutomationCaseDetailModal';
import PageHero from '../ui/PageHero';
import CatalogTreeSidebar from '../catalog/CatalogTreeSidebar';
import {
  buildLabMap,
  buildUnifiedCaseList,
  getCaseStatusLabel,
  getCaseTypeLabel,
  matchesCatalogPrefix,
  collectAllTags,
  PICKER_TYPE_FILTERS,
  type UnifiedCaseItem,
  type TypeFilter,
} from './testCaseBoardTypes';
import { toggleInSet } from '../../utils/setHelpers';

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: '#22c55e', INACTIVE: '#6b7280', DRAFT: '#9ca3af',
  DEPRECATED: '#ef4444', DONE: '#22c55e',
  PENDING_REVIEW: '#f59e0b', IN_REVIEW: '#3b82f6', REJECTED: '#ef4444',
};


const IconSearch = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);
const IconPlus = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);
const IconRefresh = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" />
    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
  </svg>
);

export default function TestCaseBoardPage() {
  const [autoCases, setAutoCases] = useState<AutomationTestCaseResponse[]>([]);
  const [manualCases, setManualCases] = useState<TestCaseResponse[]>([]);
  const [labs, setLabs] = useState<CatalogLab[]>([]);
  const [loading, setLoading] = useState(true);

  const [selectedLabId, setSelectedLabId] = useState('');
  const [selectedPrefix, setSelectedPrefix] = useState<string[]>([]);
  const [showCatalog, setShowCatalog] = useState(true);

  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [tagFilter, setTagFilter] = useState<string[]>([]);

  const [selectedCase, setSelectedCase] = useState<UnifiedCaseItem | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showCreateAuto, setShowCreateAuto] = useState(false);
  const [showCreateManual, setShowCreateManual] = useState(false);
  const [editingManualCase, setEditingManualCase] = useState<TestCaseResponse | null>(null);

  // ── Delete confirmation ──
  const [deleteTarget, setDeleteTarget] = useState<UnifiedCaseItem | null>(null);
  const [deleting, setDeleting] = useState(false);

  // ── Delete all confirmation ──
  const [showDeleteAllConfirm, setShowDeleteAllConfirm] = useState(false);
  const [deletingAll, setDeletingAll] = useState(false);
  const [deleteAllProgress, setDeleteAllProgress] = useState<{ current: number; total: number } | null>(null);

  const fetchAll = useCallback(async () => {
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
      if (!selectedLabId && labItems.length > 0) setSelectedLabId(labItems[0].lab_id);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const labMap = useMemo(() => buildLabMap(labs), [labs]);

  const cards = useMemo(
    () => buildUnifiedCaseList(manualCases, autoCases, labMap),
    [manualCases, autoCases, labMap],
  );

  const filtered = useMemo(() => {
    return cards.filter(c => {
      if (typeFilter !== 'all' && c.type !== typeFilter) return false;
      if (statusFilter !== 'all' && c.status !== statusFilter) return false;
      if (!matchesCatalogPrefix(c.catalogPath, selectedPrefix)) return false;
      if (tagFilter.length > 0) {
        if (!c.tags || !tagFilter.some(t => c.tags!.includes(t))) return false;
      }
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (!c.title.toLowerCase().includes(q) && !c.caseId.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [cards, typeFilter, statusFilter, selectedPrefix, tagFilter, searchQuery]);

  const statusOptions = useMemo(() => {
    const set = new Set(cards.map(c => c.status));
    return Array.from(set).sort();
  }, [cards]);

  // ── 所有 Tag 去重排序 ──
  const allTags = useMemo(() => collectAllTags(cards), [cards]);

  const toggleTag = (tag: string) => {
    setTagFilter(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]);
  };

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => toggleInSet(prev, id));
  };

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      if (deleteTarget.type === 'manual') {
        await api.deleteTestCase(deleteTarget.id);
      } else {
        await api.deleteAutomationTestCase(deleteTarget.id);
      }
      setDeleteTarget(null);
      await fetchAll();
    } catch (err) {
      console.error('删除用例失败:', err);
      alert('删除失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
    setDeleting(false);
  }, [deleteTarget, fetchAll]);

  const handleDeleteAll = useCallback(async () => {
    setDeletingAll(true);
    setDeleteAllProgress({ current: 0, total: cards.length });
    let successCount = 0;
    let failCount = 0;
    const CONCURRENCY = 5;
    try {
      // Process in batches to avoid overwhelming the server
      for (let i = 0; i < cards.length; i += CONCURRENCY) {
        const batch = cards.slice(i, i + CONCURRENCY);
        const results = await Promise.allSettled(
          batch.map(card =>
            card.type === 'manual'
              ? api.deleteTestCase(card.id)
              : api.deleteAutomationTestCase(card.id)
          )
        );
        results.forEach(r => {
          if (r.status === 'fulfilled') successCount++;
          else failCount++;
        });
        setDeleteAllProgress({ current: Math.min(i + CONCURRENCY, cards.length), total: cards.length });
      }
      setShowDeleteAllConfirm(false);
      if (failCount > 0) {
        alert(`删除完成：成功 ${successCount} 个，失败 ${failCount} 个`);
      }
      await fetchAll();
    } catch (err) {
      console.error('批量删除失败:', err);
      alert('批量删除失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
    setDeletingAll(false);
    setDeleteAllProgress(null);
  }, [cards, fetchAll]);

  const stats = useMemo(() => ({
    total: cards.length, auto: autoCases.length, manual: manualCases.length,
  }), [cards, autoCases, manualCases]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: 'var(--space-6) var(--space-6) 0' }}>
        <PageHero
          badge="Case Center"
          description="统一浏览所有测试用例。从左侧目录树按 Lab 和分类逐级浏览，点击卡片查看详情。"
          accent="#0ea5e9"
          gradient={['#f0f9ff', '#e0f2fe', '#f0fdfa']}
        />
      </div>

      <div style={{ flex: 1, minHeight: 0, padding: 'var(--space-5) var(--space-6)', display: 'flex', gap: 16, overflow: 'hidden' }}>
        {/* 左侧：Lab 目录树 */}
        <div style={{
          width: 220, minWidth: 220, display: 'flex', flexDirection: 'column',
          border: '1px solid var(--border-default)', borderRadius: 10, background: 'var(--surface-secondary)',
          transition: 'width 0.2s, min-width 0.2s',
          ...(showCatalog ? {} : { width: 0, minWidth: 0, overflow: 'hidden', border: 'none', padding: 0 }),
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '10px 12px', borderBottom: '1px solid var(--border-default)',
          }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>📁 目录</span>
            <button
              onClick={() => setShowCatalog(false)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 11, color: 'var(--text-tertiary)', padding: 0 }}
            >✕</button>
          </div>
          <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
            {labs.length === 0 ? (
              <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>暂无 Lab</div>
            ) : (
              <CatalogTreeSidebar
                labs={labs}
                selectedLabId={selectedLabId}
                selectedPrefix={selectedPrefix}
                onSelectLab={labId => { setSelectedLabId(labId); setSelectedPrefix([]); }}
                onSelectPrefix={prefix => setSelectedPrefix(prefix)}
              />
            )}
          </div>
        </div>

        {/* 右侧：工具栏 + 卡片网格 */}
        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Toolbar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
            {!showCatalog && (
              <button onClick={() => setShowCatalog(true)} style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                width: 32, height: 32, borderRadius: 8, border: '1px solid var(--border-default)',
                background: 'var(--surface-primary)', cursor: 'pointer', fontSize: 14, color: 'var(--text-primary)',
              }} title="显示目录">▶</button>
            )}

            <div style={{ position: 'relative', flex: '0 1 240px' }}>
              <span style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-tertiary)', display: 'flex' }}>
                <IconSearch />
              </span>
              <input type="text" placeholder="搜索用例名称或 ID..." value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{ width: '100%', padding: '7px 10px 7px 30px', borderRadius: 8,
                  border: '1px solid var(--border-default)', fontSize: 13, outline: 'none', backgroundColor: 'var(--surface-primary)', color: 'var(--text-primary)', boxSizing: 'border-box' }} />
            </div>

            <div style={{ display: 'flex', background: 'var(--surface-secondary)', borderRadius: 8, padding: 2 }}>
              {PICKER_TYPE_FILTERS.map(({ key, label }) => (
                <button key={key} onClick={() => setTypeFilter(key)} style={{
                  padding: '5px 12px', borderRadius: 6, border: 'none',
                  fontSize: 12, fontWeight: 500, cursor: 'pointer',
                  background: typeFilter === key ? 'var(--surface-primary)' : 'transparent',
                  color: typeFilter === key ? 'var(--text-primary)' : 'var(--text-secondary)',
                  boxShadow: typeFilter === key ? 'var(--shadow-sm)' : 'none',
                }}>{label}</button>
              ))}
            </div>

            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
              style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid var(--border-default)',
                fontSize: 12, color: 'var(--text-primary)', background: 'var(--surface-primary)', cursor: 'pointer' }}>
              <option value="all">全部状态</option>
              {statusOptions.map(s => (
                <option key={s} value={s}>{getCaseStatusLabel(s)}</option>
              ))}
            </select>

            <div style={{ flex: 1 }} />
            <span style={{ fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>{filtered.length} / {stats.total} 条</span>
            {selectedIds.size > 0 && (
              <span style={{ fontSize: 12, color: 'var(--accent-primary)', fontWeight: 500 }}>已选 {selectedIds.size}</span>
            )}
            <button onClick={() => setShowCreateManual(true)} style={{ ...btnStyle, background: 'var(--accent-primary)', color: '#fff', border: 'none' }}>
              <IconPlus /> 手工
            </button>
            <button onClick={() => setShowCreateAuto(true)} style={{ ...btnStyle, background: 'var(--accent-secondary)', color: '#fff', border: 'none' }}>
              <IconPlus /> 自动
            </button>
            <button onClick={() => setShowDeleteAllConfirm(true)} style={{ ...btnStyle, background: 'var(--surface-primary)', color: 'var(--status-error)', border: '1px solid var(--status-error)' }}>
              🗑 删除全部
            </button>
            <button onClick={fetchAll} style={{ ...btnStyle, background: 'var(--surface-primary)', color: 'var(--text-primary)', border: '1px solid var(--border-default)' }}>
              <IconRefresh />
            </button>
          </div>

          {/* Tag chips */}
          {allTags.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap', flexShrink: 0 }}>
              {allTags.map(tag => {
                const active = tagFilter.includes(tag);
                return (
                  <button key={tag} onClick={() => toggleTag(tag)} style={{
                    display: 'inline-flex', alignItems: 'center', gap: 4,
                    padding: '3px 10px', borderRadius: 14, border: 'none',
                    fontSize: 11, fontWeight: 500, cursor: 'pointer',
                    background: active ? 'var(--status-info-bg)' : 'var(--surface-secondary)',
                    color: active ? 'var(--status-info)' : 'var(--text-secondary)',
                    transition: 'all 0.1s',
                  }}>
                    {tag}
                    {active && <span style={{ fontSize: 12, lineHeight: 1 }}>✕</span>}
                  </button>
                );
              })}
              {tagFilter.length > 0 && (
                <button onClick={() => setTagFilter([])} style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  fontSize: 11, color: 'var(--text-tertiary)', padding: '3px 6px',
                }}>清除</button>
              )}
            </div>
          )}

          {/* Card Grid */}
          <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
            {loading && filtered.length === 0 ? (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200, color: 'var(--text-tertiary)' }}>加载中...</div>
            ) : filtered.length === 0 ? (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200, color: 'var(--text-tertiary)' }}>没有匹配的用例</div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
                {filtered.map(card => {
                  const sc = STATUS_COLORS[card.status] || '#9ca3af';
                  const isSel = selectedIds.has(card.id);
                  return (
                    <div key={card.id} onClick={() => setSelectedCase(card)} style={{
                      background: 'var(--surface-primary)', borderRadius: 10, border: `1px solid ${isSel ? 'var(--accent-primary)' : 'var(--border-default)'}`,
                      padding: '12px 14px', cursor: 'pointer', position: 'relative',
                      boxShadow: 'var(--shadow-xs)',
                      transition: 'box-shadow 0.15s, border-color 0.15s', display: 'flex', flexDirection: 'column', gap: 8,
                    }}
                      onMouseEnter={e => { e.currentTarget.style.boxShadow = 'var(--shadow-md)'; e.currentTarget.style.borderColor = 'var(--accent-primary)'; }}
                      onMouseLeave={e => { e.currentTarget.style.boxShadow = 'var(--shadow-xs)'; e.currentTarget.style.borderColor = isSel ? 'var(--accent-primary)' : 'var(--border-default)'; }}
                    >
                      <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 1 }}
                        onClick={e => { e.stopPropagation(); toggleSelect(card.id); }}>
                        <input type="checkbox" checked={isSel} readOnly style={{ accentColor: 'var(--accent-primary)', cursor: 'pointer' }} />
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingRight: 24 }}>
                        <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: sc, flexShrink: 0 }} />
                        <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>{card.title}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--text-secondary)' }}>
                        <span style={{
                          fontSize: 10, fontWeight: 600, padding: '1px 8px', borderRadius: 8,
                          background: card.type === 'auto' ? 'rgba(6, 182, 212, 0.1)' : 'rgba(99, 102, 241, 0.1)',
                          color: card.type === 'auto' ? 'var(--accent-secondary)' : 'var(--accent-primary)',
                          border: `1px solid ${card.type === 'auto' ? 'rgba(6, 182, 212, 0.2)' : 'rgba(99, 102, 241, 0.2)'}`,
                        }}>{getCaseTypeLabel(card.type)}</span>
                        <span style={{ fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-tertiary)' }}>{card.caseId}</span>
                        <div style={{ flex: 1 }} />
                        <span style={{ padding: '1px 6px', borderRadius: 6, fontSize: 10, background: `${sc}15`, color: sc, fontWeight: 500 }}>
                          {getCaseStatusLabel(card.status)}
                        </span>
                        {card.framework && <span style={{ color: 'var(--text-tertiary)' }}>{card.framework}</span>}
                        {card.catalogPath && (
                          <span style={{ color: 'var(--text-tertiary)', fontSize: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 120 }}>
                            {card.catalogPath.join(' ▸ ')}
                          </span>
                        )}
                      </div>
                      {/* Tags row */}
                      {card.tags && card.tags.length > 0 && (
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {card.tags.map(t => (
                            <span key={t} style={{
                              fontSize: 9, padding: '1px 6px', borderRadius: 8,
                            background: tagFilter.includes(t) ? 'var(--status-info-bg)' : 'var(--surface-secondary)',
                            color: tagFilter.includes(t) ? 'var(--status-info)' : 'var(--text-secondary)',
                            }}>{t}</span>
                          ))}
                        </div>
                      )}
                      {/* Delete button */}
                      <div style={{ position: 'absolute', bottom: 8, right: 8, zIndex: 1 }}
                        onClick={e => { e.stopPropagation(); setDeleteTarget(card); }}>
                        <button title="删除此用例" style={{
                          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                          width: 24, height: 24, borderRadius: 6, border: 'none',
                          background: 'transparent', color: 'var(--border-subtle)', cursor: 'pointer',
                          fontSize: 14, lineHeight: 1, padding: 0,
                          transition: 'color 0.12s, background 0.12s',
                        }}
                          onMouseEnter={e => { e.currentTarget.style.background = 'var(--status-error-bg)'; e.currentTarget.style.color = 'var(--status-error)'; }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--border-subtle)'; }}
                        >🗑</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Detail modal */}
      {selectedCase && (
        selectedCase.type === 'manual' && selectedCase.manualData ? (
          <TestCaseDetailModal
            testCase={selectedCase.manualData}
            onClose={() => setSelectedCase(null)}
            onEdit={() => {
              setEditingManualCase(selectedCase.manualData!);
              setSelectedCase(null);
            }}
          />
        ) : selectedCase.type === 'auto' && selectedCase.autoData ? (
          <AutomationCaseDetailModal
            testCase={selectedCase.autoData}
            onClose={() => setSelectedCase(null)}
          />
        ) : null
      )}

      {showCreateAuto && (
        <CreateAutomationTestCaseForm onClose={() => setShowCreateAuto(false)} onSuccess={() => { setShowCreateAuto(false); fetchAll(); }} />
      )}
      {showCreateManual && (
        <CreateTestCaseForm onClose={() => setShowCreateManual(false)} onSuccess={() => { setShowCreateManual(false); fetchAll(); }} />
      )}
      {editingManualCase && (
        <CreateTestCaseForm
          editTestCase={editingManualCase}
          onClose={() => setEditingManualCase(null)}
          onSuccess={() => { setEditingManualCase(null); fetchAll(); }}
        />
      )}

      {/* ── Delete confirmation modal ── */}
      {deleteTarget && (
        <div style={{
          position: 'fixed', inset: 0, background: 'var(--overlay-bg)', zIndex: 3000,
          display: 'flex', justifyContent: 'center', alignItems: 'center',
          backdropFilter: 'blur(2px)',
        }} onClick={() => !deleting && setDeleteTarget(null)}>
          <div style={{
            background: 'var(--surface-primary)', borderRadius: 14, padding: '28px 32px',
            textAlign: 'center', maxWidth: 400, width: '90%',
            boxShadow: 'var(--shadow-lg)',
          }} onClick={e => e.stopPropagation()}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>⚠️</div>
            <h3 style={{ margin: '0 0 8px', fontSize: 17, fontWeight: 600, color: 'var(--text-primary)' }}>确认删除</h3>
            <p style={{ margin: '0 0 4px', fontSize: 14, color: 'var(--text-secondary)' }}>
              确定要删除以下测试用例吗？
            </p>
            <p style={{ margin: '0 0 16px', fontSize: 13, color: 'var(--text-primary)', fontWeight: 500 }}>
              [{deleteTarget.type === 'auto' ? '自动化' : '手工'}] {deleteTarget.title}
              <br />
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: 'var(--text-tertiary)' }}>{deleteTarget.caseId}</span>
            </p>
            <p style={{ margin: '0 0 20px', fontSize: 12, color: 'var(--status-error)', fontWeight: 500 }}>
              此操作不可撤销，关联数据将被一并删除。
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button onClick={() => setDeleteTarget(null)} disabled={deleting} style={{
                padding: '8px 24px', borderRadius: 8, border: '1px solid var(--border-default)',
                background: 'var(--surface-primary)', color: 'var(--text-primary)', cursor: 'pointer',
                fontSize: 13, fontWeight: 500, opacity: deleting ? 0.6 : 1,
              }}>取消</button>
              <button onClick={handleDelete} disabled={deleting} style={{
                padding: '8px 24px', borderRadius: 8, border: 'none',
                background: deleting ? 'var(--status-error-bg)' : 'var(--status-error)', color: '#fff',
                cursor: 'pointer', fontSize: 13, fontWeight: 600,
                display: 'flex', alignItems: 'center', gap: 6,
              }}>
                {deleting ? '删除中...' : '确认删除'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Delete all confirmation modal ── */}
      {showDeleteAllConfirm && (
        <div style={{
          position: 'fixed', inset: 0, background: 'var(--overlay-bg)', zIndex: 3000,
          display: 'flex', justifyContent: 'center', alignItems: 'center',
          backdropFilter: 'blur(2px)',
        }} onClick={() => !deletingAll && setShowDeleteAllConfirm(false)}>
          <div style={{
            background: 'var(--surface-primary)', borderRadius: 14, padding: '28px 32px',
            textAlign: 'center', maxWidth: 420, width: '90%',
            boxShadow: 'var(--shadow-lg)',
          }} onClick={e => e.stopPropagation()}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>⚠️</div>
            <h3 style={{ margin: '0 0 8px', fontSize: 17, fontWeight: 600, color: 'var(--text-primary)' }}>
              {deletingAll ? '正在删除...' : '确认删除全部用例'}
            </h3>
            {!deletingAll ? (
              <>
                <p style={{ margin: '0 0 8px', fontSize: 14, color: 'var(--text-secondary)' }}>
                  确定要删除当前加载的全部测试用例吗？
                </p>
                <p style={{ margin: '0 0 4px', fontSize: 13, color: 'var(--status-error)', fontWeight: 600 }}>
                  共 {stats.total} 个（手工 {stats.manual} 个 / 自动化 {stats.auto} 个）
                </p>
                <p style={{ margin: '0 0 20px', fontSize: 12, color: 'var(--status-error)', fontWeight: 500 }}>
                  此操作不可撤销，关联数据将被一并删除。
                </p>
                <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
                  <button onClick={() => setShowDeleteAllConfirm(false)} style={{
                    padding: '8px 24px', borderRadius: 8, border: '1px solid var(--border-default)',
                    background: 'var(--surface-primary)', color: 'var(--text-primary)', cursor: 'pointer',
                    fontSize: 13, fontWeight: 500,
                  }}>取消</button>
                  <button onClick={handleDeleteAll} style={{
                    padding: '8px 24px', borderRadius: 8, border: 'none',
                    background: 'var(--status-error)', color: '#fff',
                    cursor: 'pointer', fontSize: 13, fontWeight: 600,
                  }}>确认删除全部</button>
                </div>
              </>
            ) : (
              <div style={{ padding: '12px 0' }}>
                <div style={{
                  width: '100%', height: 6, background: 'var(--surface-secondary)',
                  borderRadius: 3, overflow: 'hidden', marginBottom: 12,
                }}>
                  <div style={{
                    height: '100%', background: 'var(--status-error)',
                    borderRadius: 3, transition: 'width 0.2s',
                    width: deleteAllProgress ? `${(deleteAllProgress.current / deleteAllProgress.total) * 100}%` : '0%',
                  }} />
                </div>
                <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)' }}>
                  {deleteAllProgress?.current ?? 0} / {deleteAllProgress?.total ?? 0}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 4,
  padding: '7px 14px', borderRadius: 8, fontSize: 12, fontWeight: 500,
  cursor: 'pointer', lineHeight: 1,
};
