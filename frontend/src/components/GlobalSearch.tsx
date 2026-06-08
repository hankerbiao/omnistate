import { useState, useRef, useCallback, useEffect } from 'react';
import { api } from '../services/api';
import type { SearchGroup, SearchItem } from '../types';

interface GlobalSearchProps {
  onNavigate: (page: string) => void;
  onHighlight?: (type: string, id: string) => void;
}

export default function GlobalSearch({ onNavigate, onHighlight }: GlobalSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchGroup[]>([]);
  const [total, setTotal] = useState(0);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  // Keyboard shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node) &&
          inputRef.current && !inputRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      setTotal(0);
      return;
    }
    setLoading(true);
    try {
      const res = await api.search(q.trim(), { limit: 8 });
      setResults(res.data?.results || []);
      setTotal(res.data?.total || 0);
    } catch {
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleInputChange = (value: string) => {
    setQuery(value);
    setOpen(true);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSearch(value), 250);
  };

  const handleSelectItem = (item: SearchItem) => {
    setOpen(false);
    setQuery('');
    setResults([]);

    // Parse URL params from the item's url string
    const params = new URLSearchParams(item.url.replace('?', ''));
    const page = params.get('page') || 'myTasks';
    onNavigate(page);

    // If there's a highlight target, pass it through
    const highlight = params.get('highlight');
    if (highlight && onHighlight) {
      onHighlight(item.type, highlight);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setOpen(false);
      inputRef.current?.blur();
    }
    if (e.key === 'Enter' && query.trim()) {
      setOpen(false);
      setQuery('');
      setResults([]);
      // Navigate to a search results page (reuse same approach)
      onNavigate('search');
    }
  };

  const groupedLabel = results.length > 0 ? 'all results' : '';

  return (
    <div style={{ position: 'relative', flex: '0 1 320px', minWidth: 160 }}>
      <div style={{
        display: 'flex', alignItems: 'center',
        backgroundColor: 'var(--surface-secondary)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 8, padding: '4px 10px', gap: 6,
      }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input
          ref={inputRef}
          type="search"
          value={query}
          onChange={e => handleInputChange(e.target.value)}
          onFocus={() => query.trim() && setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="搜索需求、用例、任务... (Cmd+K)"
          aria-label="全局搜索"
          style={{
            flex: 1, border: 'none', outline: 'none', fontSize: 13,
            color: 'var(--text-primary)', backgroundColor: 'transparent',
            padding: '3px 0', width: '100%',
          }}
        />
        {loading && <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>...</span>}
      </div>

      {open && (results.length > 0 || loading) && (
        <div
          ref={panelRef}
          style={{
            position: 'absolute', top: '100%', left: 0, right: 0, marginTop: 4,
            backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-default)',
            borderRadius: 10, boxShadow: '0 8px 30px rgba(0,0,0,0.12)',
            maxHeight: 480, overflowY: 'auto', zIndex: 3000,
          }}
        >
          {results.map(group => (
            <div key={group.type}>
              <div style={{
                padding: '8px 14px 4px', fontSize: 11, fontWeight: 600,
                color: 'var(--text-tertiary)', textTransform: 'uppercase',
                letterSpacing: '0.3px',
              }}>
                {group.type_label} ({group.items.length}/{group.total})
              </div>
              {group.items.map(item => (
                <button
                  key={`${item.type}-${item.id}`}
                  type="button"
                  onClick={() => handleSelectItem(item)}
                  style={{
                    display: 'block', width: '100%', textAlign: 'left',
                    padding: '8px 14px', border: 'none', background: 'transparent',
                    cursor: 'pointer', borderBottom: '0.5px solid var(--border-subtle)',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--surface-secondary)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 2 }}
                    dangerouslySetInnerHTML={{ __html: item.title }} />
                  {item.subtitle && (
                    <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{item.subtitle}</div>
                  )}
                  {item.highlight && (
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2, lineHeight: 1.4 }}
                      dangerouslySetInnerHTML={{ __html: item.highlight }} />
                  )}
                </button>
              ))}
            </div>
          ))}
          {total > 6 && (
            <button
              type="button"
              onClick={() => { setOpen(false); onNavigate('search'); }}
              style={{
                display: 'block', width: '100%', padding: '10px 14px', textAlign: 'center',
                border: 'none', background: 'var(--surface-secondary)', cursor: 'pointer',
                fontSize: 12, color: 'var(--accent-primary)', fontWeight: 500,
                borderRadius: '0 0 10px 10px',
              }}
            >
              查看全部 {total} 条结果 →
            </button>
          )}
        </div>
      )}
    </div>
  );
}
