import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { SearchGroup, SearchItem } from '../types';
import PageHero from './ui/PageHero';

interface SearchResultsPageProps {
  initialQuery?: string;
  onNavigate: (page: string) => void;
  onHighlight?: (type: string, id: string) => void;
}

export default function SearchResultsPage({ initialQuery = '', onNavigate, onHighlight }: SearchResultsPageProps) {
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchGroup[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [activeType, setActiveType] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const types = [
    { key: null, label: '全部' },
    { key: 'requirement', label: '需求' },
    { key: 'test_case', label: '用例' },
    { key: 'automation_case', label: '自动化用例' },
    { key: 'execution_task', label: '执行任务' },
    { key: 'comment', label: '评论' },
  ];

  const doSearch = useCallback(async (q: string, typeFilter: string | null, off: number) => {
    if (!q.trim()) return;
    setLoading(true);
    try {
      const res = await api.search(q.trim(), {
        types: typeFilter || undefined,
        limit,
        offset: off,
      });
      setResults(res.data?.results || []);
      setTotal(res.data?.total || 0);
    } catch {
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    doSearch(query, activeType, 0);
  }, [query, activeType, doSearch]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    doSearch(query, activeType, 0);
  };

  const handleSelectItem = (item: SearchItem) => {
    const params = new URLSearchParams(item.url.replace('?', ''));
    const page = params.get('page') || 'myTasks';
    onNavigate(page);
    const highlight = params.get('highlight');
    if (highlight && onHighlight) onHighlight(item.type, highlight);
  };

  return (
    <div className="page-content">
      <PageHero
        badge="global search"
        description="跨模块搜索测试需求、用例、执行任务、评论等内容。"
        accent="#6366f1"
        gradient={['#f0f0ff', '#e0e7ff', '#f0f0ff']}
      />

      <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          autoFocus
          type="search"
          value={query}
          onChange={e => { setQuery(e.target.value); setOffset(0); }}
          placeholder="输入关键词搜索..."
          style={{
            flex: 1, padding: '10px 14px', fontSize: 14, borderRadius: 8,
            border: '1px solid var(--border-default)',
            color: 'var(--text-primary)', backgroundColor: 'var(--surface-primary)',
            outline: 'none',
          }}
        />
        <button type="submit" className="btn btn--primary" disabled={loading || !query.trim()}>
          {loading ? '搜索中...' : '搜索'}
        </button>
      </form>

      {/* Type filter tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' }}>
        {types.map(t => (
          <button
            key={t.key ?? 'all'}
            type="button"
            onClick={() => { setActiveType(t.key); setOffset(0); }}
            style={{
              padding: '6px 14px', borderRadius: 999, border: 'none',
              fontSize: 12, fontWeight: 500, cursor: 'pointer',
              backgroundColor: activeType === t.key ? 'var(--accent-primary)' : 'var(--surface-secondary)',
              color: activeType === t.key ? 'white' : 'var(--text-secondary)',
            }}
          >
            {t.label}
          </button>
        ))}
        {total > 0 && <span style={{ fontSize: 12, color: 'var(--text-tertiary)', marginLeft: 8, alignSelf: 'center' }}>共 {total} 条</span>}
      </div>

      {loading && results.length === 0 ? (
        <div className="loading-overlay"><div className="loading-spinner" /></div>
      ) : results.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__icon">{query ? '🔍' : '⌨️'}</div>
          <p className="empty-state__text">
            {query ? '没有找到匹配的结果，试试其他关键词' : '输入关键词开始搜索'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {results.map(group => (
            <div key={group.type} className="surface-card" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{
                padding: '10px 16px', fontSize: 12, fontWeight: 600,
                color: 'var(--text-secondary)', backgroundColor: 'var(--surface-secondary)',
                borderBottom: '1px solid var(--border-subtle)',
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
                    padding: '12px 16px', border: 'none', background: 'transparent',
                    cursor: 'pointer', borderBottom: '0.5px solid var(--border-subtle)',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--surface-secondary)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 2 }}
                    dangerouslySetInnerHTML={{ __html: item.title }} />
                  {item.subtitle && (
                    <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 2 }}>{item.subtitle}</div>
                  )}
                  {item.highlight && (
                    <div style={{
                      fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5,
                      backgroundColor: 'var(--surface-secondary)', padding: '6px 10px',
                      borderRadius: 6, marginTop: 4,
                    }}
                      dangerouslySetInnerHTML={{ __html: item.highlight }} />
                  )}
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
