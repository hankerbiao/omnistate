/**
 * TimelineView — 通用垂直时间线组件
 *
 * 用于展示执行计划中的状态变更时间线、业务日志时间线等。
 * 支持按时间排序、状态着色、可展开详情。
 */

import React, { useState } from 'react';

// ═══════════════════════════════════════════════════════════════════
//  Types
// ═══════════════════════════════════════════════════════════════════

export interface TimelineItem {
  /** 时间戳（ISO 字符串） */
  time: string;
  /** 标题 */
  title: string;
  /** 描述文本 */
  description?: string;
  /** 状态（用于颜色区分） */
  status?: 'success' | 'failed' | 'running' | 'info' | 'warning';
  /** 可展开的详情内容 */
  expandable?: React.ReactNode;
  /** 自定义图标标签（如状态名缩写） */
  badge?: string;
  /** 自定义 badge 颜色 */
  badgeColor?: string;
}

interface TimelineViewProps {
  items: TimelineItem[];
  /** 标题 */
  title?: string;
  /** 是否默认折叠 */
  defaultCollapsed?: boolean;
  /** 最大显示条数，超出显示 "查看更多" */
  maxItems?: number;
}

// ═══════════════════════════════════════════════════════════════════
//  Status color map
// ═══════════════════════════════════════════════════════════════════

const STATUS_COLORS: Record<string, { dot: string; line: string; bg: string; text: string }> = {
  success: { dot: '#3fb950', line: 'rgba(63,185,80,0.3)', bg: 'rgba(63,185,80,0.06)', text: '#3fb950' },
  failed:  { dot: '#f85149', line: 'rgba(248,81,73,0.3)', bg: 'rgba(248,81,73,0.06)', text: '#f85149' },
  running: { dot: '#58a6ff', line: 'rgba(88,166,255,0.3)', bg: 'rgba(88,166,255,0.06)', text: '#58a6ff' },
  info:    { dot: '#8b949e', line: 'rgba(139,148,158,0.2)', bg: 'rgba(139,148,158,0.04)', text: '#8b949e' },
  warning: { dot: '#d29922', line: 'rgba(210,153,34,0.3)', bg: 'rgba(210,153,34,0.06)', text: '#d29922' },
};

function getStatusStyle(status?: string) {
  return STATUS_COLORS[status || 'info'] || STATUS_COLORS.info;
}

// ═══════════════════════════════════════════════════════════════════
//  Component
// ═══════════════════════════════════════════════════════════════════

export default function TimelineView({ items, title, defaultCollapsed, maxItems = 50 }: TimelineViewProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed ?? false);
  const [showAll, setShowAll] = useState(false);

  const sorted = [...items].sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());
  const displayed = showAll ? sorted : sorted.slice(0, maxItems);
  const hasMore = sorted.length > maxItems;

  return (
    <div style={{ borderRadius: 8, border: '1px solid var(--border-subtle)', overflow: 'hidden' }}>
      {/* Header */}
      {title && (
        <div
          onClick={() => setCollapsed(!collapsed)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '8px 12px', fontSize: 12, fontWeight: 600,
            color: 'var(--text-secondary)', cursor: 'pointer',
            borderBottom: collapsed ? 'none' : '1px solid var(--border-subtle)',
            background: 'var(--surface-secondary)',
            userSelect: 'none',
          }}
        >
          <span style={{ fontSize: 10, transition: 'transform 0.15s', display: 'inline-block', transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)' }}>
            ▼
          </span>
          {title}
          <span style={{ fontSize: 10, color: 'var(--text-tertiary)', marginLeft: 'auto' }}>{items.length} 条</span>
        </div>
      )}

      {!collapsed && (
        <div style={{ padding: '4px 0' }}>
          {displayed.length === 0 ? (
            <div style={{ padding: '16px 20px', fontSize: 12, color: 'var(--text-tertiary)', textAlign: 'center' }}>
              暂无记录
            </div>
          ) : (
            displayed.map((item, idx) => (
              <TimelineRow key={idx} item={item} isLast={idx === displayed.length - 1} />
            ))
          )}

          {hasMore && !showAll && (
            <div style={{ textAlign: 'center', padding: '6px 0' }}>
              <button
                onClick={() => setShowAll(true)}
                style={{
                  fontSize: 11, color: 'var(--accent-primary)', background: 'none',
                  border: 'none', cursor: 'pointer', padding: '2px 8px',
                }}
              >
                查看更多 ({sorted.length - maxItems} 条)
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  TimelineRow — 单行时间线条目
// ═══════════════════════════════════════════════════════════════════

function TimelineRow({ item, isLast }: { item: TimelineItem; isLast: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const style = getStatusStyle(item.status);
  const hasExpandable = item.expandable !== undefined;

  return (
    <div style={{ display: 'flex', padding: '0 12px' }}>
      {/* 左侧时间线 */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 20, flexShrink: 0 }}>
        <div style={{
          width: 10, height: 10, borderRadius: '50%',
          background: style.dot, marginTop: 10, flexShrink: 0,
        }} />
        {!isLast && (
          <div style={{ width: 1, flex: 1, background: style.line, minHeight: 8 }} />
        )}
      </div>

      {/* 右侧内容 */}
      <div style={{ flex: 1, padding: '6px 0 6px 8px', minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>
                {item.title}
              </span>
              {item.badge && (
                <span style={{
                  fontSize: 9, padding: '0 5px', borderRadius: 3,
                  background: item.badgeColor || 'rgba(139,148,158,0.12)',
                  color: item.badgeColor || '#8b949e', fontWeight: 600,
                }}>
                  {item.badge}
                </span>
              )}
            </div>
            {item.description && (
              <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2, lineHeight: 1.4 }}>
                {item.description}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
            <span style={{ fontSize: 10, color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}>
              {formatTime(item.time)}
            </span>
            {hasExpandable && (
              <span
                onClick={() => setExpanded(!expanded)}
                style={{
                  fontSize: 9, color: 'var(--accent-primary)', cursor: 'pointer',
                  padding: '1px 4px', borderRadius: 3,
                  background: 'rgba(88,166,255,0.08)',
                }}
              >
                {expanded ? '收起' : '详情'}
              </span>
            )}
          </div>
        </div>

        {expanded && hasExpandable && (
          <div style={{ marginTop: 6, padding: '6px 8px', borderRadius: 6, background: 'var(--surface-secondary)', fontSize: 11 }}>
            {item.expandable}
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  Helpers
// ═══════════════════════════════════════════════════════════════════

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString('zh-CN', {
      month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  } catch {
    return iso;
  }
}
