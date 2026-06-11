import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { api } from '../../services/api';
import type { SearchGroup, SearchItem } from '../../types';
import PageHero from '../../components/ui/PageHero';

interface SearchPageProps {
  onNavigate: (page: string) => void;
  onHighlight?: (type: string, id: string) => void;
}

const SEARCH_HISTORY_KEY = 'dml_search_history';

const typeOptions = [
  { key: 'requirement', label: '需求', icon: '▣', color: '#6366f1' },
  { key: 'test_case', label: '用例', icon: '⚡', color: '#2563eb' },
  { key: 'automation_case', label: '自动化用例', icon: '⟳', color: '#059669' },
  { key: 'execution_task', label: '执行任务', icon: '▶', color: '#d97706' },
  { key: 'comment', label: '评论', icon: '💬', color: '#7c3aed' },
] as const;

const sortOptions = [
  { key: 'relevance', label: '相关度优先' },
  { key: 'newest', label: '最新优先' },
] as const;

const timeOptions = [
  { key: 'all', label: '不限时间' },
  { key: 'week', label: '最近一周' },
  { key: 'month', label: '最近一月' },
] as const;

type SortKey = typeof sortOptions[number]['key'];
type TimeKey = typeof timeOptions[number]['key'];

const TIME_MS: Record<TimeKey, number> = { all: 0, week: 604_800_000, month: 2_592_000_000 };

function loadHistory(): string[] {
  try { return JSON.parse(localStorage.getItem(SEARCH_HISTORY_KEY) || '[]'); } catch { return []; }
}
function saveHistory(q: string) {
  const prev = loadHistory().filter(h => h !== q);
  prev.unshift(q);
  localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(prev.slice(0, 8)));
}

function fmtRelative(ts: string): string {
  try {
    const d = new Date(ts); const diff = Date.now() - d.getTime();
    if (diff < 60_000) return '刚刚';
    if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`;
    if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`;
    if (diff < 604_800_000) return `${Math.floor(diff / 86_400_000)} 天前`;
    return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  } catch { return ''; }
}

export default function SearchPage({ onNavigate, onHighlight }: SearchPageProps) {
  const [query, setQuery] = useState('');
  const [rawResults, setRawResults] = useState<SearchGroup[] | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [sort, setSort] = useState<SortKey>('relevance');
  const [timeFilter, setTimeFilter] = useState<TimeKey>('all');
  const [cursor, setCursor] = useState(-1);
  const debounceRef = useRef<number>(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Focus on mount & global keyboard shortcuts
  useEffect(() => {
    inputRef.current?.focus();
    const handler = (e: KeyboardEvent) => {
      if (e.key === '/' && !e.ctrlKey && !e.metaKey && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const getTypesParam = useCallback((types: Set<string>) => {
    return types.size === 0 ? undefined : Array.from(types).join(',');
  }, []);

  // Debounced live search
  const triggerSearch = useCallback((q: string, types: Set<string>) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!q.trim()) { setRawResults(null); setTotal(0); setLoading(false); return; }
    setLoading(true);
    setCursor(-1);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await api.search(q.trim(), { types: getTypesParam(types), limit: 50 });
        setRawResults(res.data?.results || []);
        setTotal(res.data?.total || 0);
      } catch { setRawResults([]); setTotal(0); }
      finally { setLoading(false); }
    }, 300);
  }, [getTypesParam]);

  const handleInput = (val: string) => {
    setQuery(val);
    triggerSearch(val, selectedTypes);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query.trim()) return;
    saveHistory(query);
    setLoading(true);
    api.search(query.trim(), { types: getTypesParam(selectedTypes), limit: 50 })
      .then(res => { setRawResults(res.data?.results || []); setTotal(res.data?.total || 0); })
      .catch(() => { setRawResults([]); setTotal(0); })
      .finally(() => setLoading(false));
  };

  const toggleType = (key: string) => {
    const next = new Set(selectedTypes);
    if (next.has(key)) next.delete(key); else next.add(key);
    setSelectedTypes(next);
    if (query.trim()) triggerSearch(query, next);
  };

  const handleSelect = (item: SearchItem) => {
    const p = new URLSearchParams(item.url.replace('?', ''));
    onNavigate(p.get('page') || 'myTasks');
    const hl = p.get('highlight');
    if (hl && onHighlight) onHighlight(item.type, hl);
  };

  // Client-side filtering & sorting
  const displayResults = useMemo(() => {
    if (!rawResults) return null;
    const cutoff = TIME_MS[timeFilter];
    return rawResults
      .map(g => {
        const items = cutoff > 0
          ? g.items.filter(i => i.updated_at && (Date.now() - new Date(i.updated_at).getTime()) <= cutoff)
          : g.items;
        const sorted = sort === 'newest'
          ? [...items].sort((a, b) => (new Date(b.updated_at || 0).getTime() - new Date(a.updated_at || 0).getTime()))
          : items;
        return { ...g, items: sorted };
      })
      .filter(g => g.items.length > 0);
  }, [rawResults, sort, timeFilter]);

  const flatResults = useMemo(() => {
    if (!displayResults) return [];
    return displayResults.flatMap(g => g.items.map(i => ({ ...i, groupType: g.type, groupLabel: g.type_label })));
  }, [displayResults]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') { setQuery(''); setRawResults(null); setCursor(-1); inputRef.current?.blur(); return; }
    if (!flatResults.length) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setCursor(c => Math.min(c + 1, flatResults.length - 1)); }
    if (e.key === 'ArrowUp') { e.preventDefault(); setCursor(c => Math.max(c - 1, -1)); }
    if (e.key === 'Enter' && cursor >= 0) { e.preventDefault(); handleSelect(flatResults[cursor]); }
  };

  // Scroll cursor into view
  useEffect(() => {
    if (cursor < 0 || !listRef.current) return;
    const el = listRef.current.children[cursor] as HTMLElement | undefined;
    el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [cursor]);

  const hasResults = rawResults !== null;
  const searchHistory = useMemo(() => loadHistory(), []);
  const allTypes = selectedTypes.size === 0;

  // ── Filter sidebar (results mode) ──
  const Sidebar = () => (
    <aside style={st.sidebar}>
      <div style={st.sidebarSection}>
        <div style={st.sidebarTitle}>搜索范围</div>
        <label style={{ ...st.checkItem, fontWeight: allTypes ? 600 : 400, color: allTypes ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
          <span style={{ ...st.checkDot, backgroundColor: allTypes ? 'var(--accent-primary)' : 'transparent', border: allTypes ? 'none' : '2px solid var(--border-default)' }}>
            {allTypes && <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>}
          </span>
          <button
            type="button"
            onClick={() => { setSelectedTypes(new Set()); if (query.trim()) triggerSearch(query, new Set()); }}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: 13, padding: 0, textAlign: 'left' }}
          >
            全部类型
          </button>
        </label>
        {typeOptions.map(t => {
          const on = selectedTypes.has(t.key);
          return (
            <label key={t.key} style={{ ...st.checkItem, fontWeight: on ? 600 : 400, color: on ? t.color : 'var(--text-secondary)' }}>
              <span style={{ ...st.checkDot, backgroundColor: on ? t.color : 'transparent', border: on ? 'none' : `2px solid ${t.color}40` }}>
                {on && <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>}
              </span>
              <button
                type="button"
                onClick={() => toggleType(t.key)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: 13, padding: 0, display: 'flex', alignItems: 'center', gap: 4 }}
              >
                <span>{t.icon}</span> {t.label}
              </button>
            </label>
          );
        })}
      </div>

      <div style={st.sidebarSection}>
        <div style={st.sidebarTitle}>排序方式</div>
        {sortOptions.map(o => (
          <label key={o.key} style={{ ...st.checkItem, fontWeight: sort === o.key ? 600 : 400, color: sort === o.key ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
            <span style={{ ...st.checkDot, backgroundColor: sort === o.key ? 'var(--text-primary)' : 'transparent', border: sort === o.key ? 'none' : '2px solid var(--border-default)', borderRadius: '50%' }} />
            <button
              type="button"
              onClick={() => setSort(o.key)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: 13, padding: 0 }}
            >
              {o.label}
            </button>
          </label>
        ))}
      </div>

      <div style={st.sidebarSection}>
        <div style={st.sidebarTitle}>时间范围</div>
        {timeOptions.map(o => (
          <label key={o.key} style={{ ...st.checkItem, fontWeight: timeFilter === o.key ? 600 : 400, color: timeFilter === o.key ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
            <span style={{ ...st.checkDot, backgroundColor: timeFilter === o.key ? 'var(--text-primary)' : 'transparent', border: timeFilter === o.key ? 'none' : '2px solid var(--border-default)', borderRadius: '50%' }} />
            <button
              type="button"
              onClick={() => setTimeFilter(o.key)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: 13, padding: 0 }}
            >
              {o.label}
            </button>
          </label>
        ))}
      </div>
    </aside>
  );

  return (
    <div style={st.page}>
      {/* ── Hero ── */}
      <PageHero
        badge="Global Search"
        description={hasResults ? `"${query}" 的搜索结果` : '跨模块搜索需求、用例、自动化用例、执行任务、评论，快速定位目标资源'}
        accent="#2563eb"
        gradient={['#eff6ff', '#eef2ff', '#f0fdfa']}
      >
        {/* Search form */}
        <div style={st.heroFormWrap}>
          <form onSubmit={handleSubmit} style={st.heroForm}>
            <div style={st.inputWrap}>
              <svg style={st.inputIcon} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                ref={inputRef}
                type="search"
                value={query}
                onChange={e => handleInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入关键词搜索...  ( / 聚焦搜索  ↓↑ 选择结果  Esc 退出)"
                style={st.input}
                aria-label="搜索"
              />
              {query && !loading && (
                <button type="button" onClick={() => { setQuery(''); setRawResults(null); setCursor(-1); inputRef.current?.focus(); }} style={st.clearBtn} aria-label="清除">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                </button>
              )}
              {loading && <span style={{ position: 'absolute', right: 12, width: 16, height: 16, border: '2px solid var(--border-default)', borderTopColor: 'var(--accent-primary)', borderRadius: '50%', animation: 'spin 0.6s linear infinite' }} />}
            </div>
            <button type="submit" className="btn btn--primary" disabled={!query.trim()} style={st.searchBtn}>
              搜索
            </button>
          </form>

          {!hasResults && (
            <>
              {/* Type pills */}
              <div style={st.pillBar}>
                <button type="button" onClick={() => { setSelectedTypes(new Set()); }} style={{ ...st.pill, backgroundColor: allTypes ? 'var(--accent-primary)' : 'rgba(255,255,255,0.7)', color: allTypes ? '#fff' : 'var(--text-secondary)', borderColor: allTypes ? 'var(--accent-primary)' : 'transparent' }}>
                  全部
                </button>
                {typeOptions.map(t => {
                  const on = selectedTypes.has(t.key);
                  return (
                    <button key={t.key} type="button" onClick={() => toggleType(t.key)} style={{ ...st.pill, backgroundColor: on ? `${t.color}18` : 'rgba(255,255,255,0.7)', color: on ? t.color : 'var(--text-secondary)', borderColor: on ? t.color : 'transparent' }}>
                      <span>{t.icon}</span> {t.label}
                    </button>
                  );
                })}
              </div>

              {/* Search history + quick tips */}
              <div style={st.auxBar}>
                {searchHistory.length > 0 && (
                  <div style={st.auxGroup}>
                    <span style={st.auxLabel}>最近搜索</span>
                    {searchHistory.slice(0, 5).map(h => (
                      <button key={h} type="button" onClick={() => { setQuery(h); saveHistory(h); triggerSearch(h, selectedTypes); }} style={st.auxBtn}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="15 18 9 12 15 6" /></svg>
                        {h}
                      </button>
                    ))}
                  </div>
                )}
                <div style={st.auxGroup}>
                  <span style={st.auxLabel}>快速入口</span>
                  {['测试用例', '自动化', '回归测试', '性能'].map(tip => (
                    <button key={tip} type="button" onClick={() => { setQuery(tip); saveHistory(tip); triggerSearch(tip, selectedTypes); }} style={st.auxBtn}>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
                      {tip}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </PageHero>

      {/* ── Results layout ── */}
      {hasResults && (
        <div style={st.resultsLayout}>
          <Sidebar />
          <div style={st.resultsMain}>
            {/* Stats cursor-info bar */}
            <div style={st.statsBar}>
              <span style={st.statsText}>
                共 <strong>{total}</strong> 条结果
                {selectedTypes.size > 0 && <span style={{ color: 'var(--text-tertiary)' }}> · {selectedTypes.size} 类</span>}
                {flatResults.length !== total && <span style={{ color: 'var(--text-tertiary)' }}> · 显示 {flatResults.length} 条</span>}
              </span>
              <span style={st.statsHint}>↓↑ 导航  /  聚焦  Esc 退出</span>
            </div>

            {/* Empty */}
            {flatResults.length === 0 && !loading && (
              <div className="empty-state" style={{ paddingTop: 40 }}>
                <div className="empty-state__icon">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" style={{ opacity: 0.35 }}>
                    <path d="M11 17a6 6 0 0 0 6-6 6 6 0 0 0-6-6 6 6 0 0 0-6 6 6 6 0 0 0 6 6z" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
                    <line x1="8" y1="11" x2="14" y2="11" />
                  </svg>
                </div>
                <p className="empty-state__text">没有找到 &ldquo;{query}&rdquo; 的相关结果</p>
                <p style={{ fontSize: 13, color: 'var(--text-tertiary)', marginTop: 4 }}>试试调整搜索范围或关键词</p>
              </div>
            )}

            {/* Result list */}
            {flatResults.length > 0 && (
              <div ref={listRef} style={st.resultList}>
                {displayResults!.map(group => {
                  const info = typeOptions.find(t => t.key === group.type);
                  return (
                    <div key={group.type} style={st.groupBlock}>
                      <div style={{ ...st.groupHeader, borderLeftColor: info?.color || 'var(--border-default)' }}>
                        <span style={{ color: info?.color, fontSize: 14 }}>{info?.icon}</span>
                        <span style={st.groupLabel}>{group.type_label}</span>
                        <span style={st.groupMeta}>{group.items.length}/{group.total}</span>
                      </div>
                      {group.items.map((item) => {
                        const flatIdx = flatResults.findIndex(f => f.id === item.id && f.type === item.type);
                        const isActive = flatIdx === cursor;
                        return (
                          <button
                            key={`${item.type}-${item.id}`}
                            type="button"
                            onClick={() => handleSelect(item)}
                            style={{
                              ...st.resultRow,
                              backgroundColor: isActive ? 'var(--surface-hover)' : 'transparent',
                              borderLeftColor: isActive ? 'var(--accent-primary)' : 'transparent',
                            }}
                            onMouseEnter={() => setCursor(flatIdx)}
                          >
                            <div style={st.resultLeft}>
                              <div style={st.resultTitle} dangerouslySetInnerHTML={{ __html: item.title }} />
                              {item.subtitle && <div style={st.resultUrl}>{item.subtitle}</div>}
                              {item.highlight && <div style={st.resultSnippet} dangerouslySetInnerHTML={{ __html: item.highlight }} />}
                            </div>
                            <div style={st.resultRight}>
                              <span style={{ ...st.resultBadge, backgroundColor: `${info?.color || '#6b7280'}12`, color: info?.color || '#6b7280' }}>
                                {item.type_label || group.type_label}
                              </span>
                              {item.updated_at && <span style={st.resultTime}>{fmtRelative(item.updated_at)}</span>}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const st: Record<string, React.CSSProperties> = {
  page: {},

  // ── Hero search area ──
  heroFormWrap: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    marginTop: 'var(--space-4)',
  },
  heroForm: {
    display: 'flex',
    gap: 10,
    width: '100%',
    maxWidth: 640,
  },
  inputWrap: {
    position: 'relative',
    flex: 1,
    display: 'flex',
    alignItems: 'center',
  },
  inputIcon: {
    position: 'absolute',
    left: 14,
    color: 'var(--text-tertiary)',
    pointerEvents: 'none',
  },
  input: {
    width: '100%',
    padding: '11px 38px 11px 42px',
    fontSize: 15,
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    backgroundColor: 'var(--surface-primary)',
    color: 'var(--text-primary)',
    outline: 'none',
    transition: 'border-color var(--transition-fast)',
  },
  clearBtn: {
    position: 'absolute',
    right: 10,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 4,
    border: 'none',
    background: 'transparent',
    color: 'var(--text-tertiary)',
    cursor: 'pointer',
    borderRadius: '50%',
  },
  searchBtn: {
    height: 42,
    padding: '0 22px',
    fontSize: 14,
    fontWeight: 600,
    flexShrink: 0,
    borderRadius: 'var(--radius-lg)',
  },

  // ── Type pills ──
  pillBar: { display: 'flex', flexWrap: 'wrap', gap: 6 },
  pill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    padding: '4px 10px',
    fontSize: 12,
    fontWeight: 500,
    borderRadius: 'var(--radius-full)',
    border: '1px solid',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
    lineHeight: 1,
  },

  // ── Aux (history + tips) ──
  auxBar: { display: 'flex', flexWrap: 'wrap', gap: 24, marginTop: 2 },
  auxGroup: { display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' as const },
  auxLabel: { fontSize: 11, color: 'var(--text-tertiary)', flexShrink: 0 },
  auxBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    padding: '3px 10px',
    fontSize: 11,
    fontWeight: 500,
    color: 'var(--accent-primary)',
    background: 'rgba(37,99,235,0.07)',
    border: 'none',
    borderRadius: 'var(--radius-full)',
    cursor: 'pointer',
  },

  // ── Results layout ──
  resultsLayout: {
    display: 'flex',
    gap: 0,
    flex: 1,
    minHeight: 0,
  },

  // ── Sidebar ──
  sidebar: {
    width: 200,
    flexShrink: 0,
    padding: 'var(--space-4) var(--space-4) var(--space-10)',
    borderRight: '1px solid var(--border-subtle)',
    backgroundColor: 'var(--surface-primary)',
    overflowY: 'auto' as const,
  },
  sidebarSection: {
    marginBottom: 'var(--space-5)',
  },
  sidebarTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
    marginBottom: 'var(--space-2)',
  },
  checkItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '4px 0',
    cursor: 'pointer',
    fontSize: 13,
    transition: 'color var(--transition-fast)',
  },
  checkDot: {
    width: 16,
    height: 16,
    borderRadius: 'var(--radius-sm)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    transition: 'all var(--transition-fast)',
  },

  // ── Results main ──
  resultsMain: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: 'var(--space-4) var(--space-6) var(--space-10)',
  },
  statsBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 0 12px',
    borderBottom: '1px solid var(--border-subtle)',
    marginBottom: 'var(--space-2)',
  },
  statsText: { fontSize: 13, color: 'var(--text-secondary)' },
  statsHint: { fontSize: 11, color: 'var(--text-tertiary)', fontFamily: "'JetBrains Mono', monospace" },

  // ── Result list ──
  resultList: { display: 'flex', flexDirection: 'column', gap: 16 },
  groupBlock: {},
  groupHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '5px 0 5px 10px',
    marginBottom: 4,
    borderLeft: '3px solid',
    borderBottom: '1px solid var(--border-subtle)',
  },
  groupLabel: { fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' },
  groupMeta: { fontSize: 11, color: 'var(--text-tertiary)', marginLeft: 2 },

  // ── Result row ──
  resultRow: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 16,
    padding: '10px 12px 10px 14px',
    marginBottom: 2,
    border: 'none',
    borderLeft: '3px solid',
    borderBottom: '0.5px solid var(--border-subtle)',
    background: 'transparent',
    textAlign: 'left',
    cursor: 'pointer',
    borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
    transition: 'background var(--transition-fast)',
    width: '100%',
  },
  resultLeft: { flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 3 },
  resultRight: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: 4,
    flexShrink: 0,
    marginTop: 1,
  },
  resultTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: 'var(--accent-primary)',
    lineHeight: 1.5,
    wordBreak: 'break-word' as const,
  },
  resultUrl: {
    fontSize: 12,
    color: 'var(--status-success)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  resultSnippet: {
    fontSize: 12,
    color: 'var(--text-secondary)',
    lineHeight: 1.6,
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  resultBadge: {
    padding: '2px 8px',
    fontSize: 11,
    fontWeight: 600,
    borderRadius: 'var(--radius-full)',
    whiteSpace: 'nowrap' as const,
  },
  resultTime: {
    fontSize: 11,
    color: 'var(--text-tertiary)',
  },
};
