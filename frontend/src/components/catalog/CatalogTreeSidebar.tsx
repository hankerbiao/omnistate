import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../../services/api';
import type { CatalogLab, CatalogTreeNode } from '../../types';
import { catalogStyles } from './catalogStyles';

interface CatalogTreeSidebarProps {
  labs?: CatalogLab[];
  selectedLabId: string;
  selectedPrefix: string[];
  onSelectLab: (labId: string) => void;
  onSelectPrefix: (prefix: string[]) => void;
}

const CatalogTreeSidebar: React.FC<CatalogTreeSidebarProps> = ({
  labs = [],
  selectedLabId,
  selectedPrefix,
  onSelectLab,
  onSelectPrefix,
}) => {
  const [tree, setTree] = useState<CatalogTreeNode | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [hoverKey, setHoverKey] = useState<string | null>(null);

  const loadTree = useCallback(async (labId: string) => {
    if (!labId) {
      setTree(null);
      return;
    }
    setLoading(true);
    try {
      const resp = await api.getCatalogTree(labId);
      setTree(resp.data?.tree || null);
    } catch (err) {
      console.error('Load catalog tree failed:', err);
      setTree(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedLabId) {
      loadTree(selectedLabId);
    }
  }, [selectedLabId, loadTree]);

  const toggleExpand = (pathKey: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(pathKey)) {
        next.delete(pathKey);
      } else {
        next.add(pathKey);
      }
      return next;
    });
  };

  const isPrefixSelected = (path: string[]) =>
    path.length === selectedPrefix.length && path.every((p, i) => p === selectedPrefix[i]);

  const selectedLabName = labs.find(l => l.lab_id === selectedLabId)?.name;

  const renderNode = (node: CatalogTreeNode, depth: number) => {
    if (!node.name && depth === 0) {
      return (node.children || []).map(child => renderNode(child, depth));
    }
    const pathKey = node.path.join('/');
    const hasChildren = (node.children || []).length > 0;
    const isExpanded = expanded.has(pathKey) || depth < 1;
    const selected = isPrefixSelected(node.path);
    const hovered = hoverKey === pathKey;

    return (
      <div key={pathKey || 'root'} style={{ marginLeft: depth * 10 }}>
        <div
          style={{
            ...catalogStyles.treeNode,
            ...(selected ? catalogStyles.treeNodeSelected : {}),
            ...(hovered && !selected ? catalogStyles.treeNodeHover : {}),
          }}
          onMouseEnter={() => setHoverKey(pathKey)}
          onMouseLeave={() => setHoverKey(null)}
        >
          {hasChildren ? (
            <button
              type="button"
              style={styles.expandBtn}
              onClick={() => toggleExpand(pathKey)}
              aria-expanded={isExpanded}
              aria-label={isExpanded ? '收起' : '展开'}
            >
              {isExpanded ? '▾' : '▸'}
            </button>
          ) : (
            <span style={styles.expandSpacer} />
          )}
          <button
            type="button"
            style={{
              ...styles.nodeBtn,
              ...(selected ? styles.nodeBtnSelected : {}),
            }}
            onClick={() => onSelectPrefix(node.path)}
          >
            <span style={styles.nodeName}>{node.name || '(根)'}</span>
            {node.case_count > 0 && (
              <span style={styles.count}>{node.case_count}</span>
            )}
          </button>
        </div>
        {hasChildren && isExpanded && (node.children || []).map(child => renderNode(child, depth + 1))}
      </div>
    );
  };

  const allSelected = selectedLabId && selectedPrefix.length === 0;

  return (
    <aside style={catalogStyles.sidebar} aria-label="测试用例目录树">
      <div style={styles.sidebarHeader}>
        <span style={catalogStyles.labelCaps}>目录</span>
      </div>
      <div style={styles.labSelect}>
        <label style={styles.labLabel} htmlFor="catalog-lab-select">Lab</label>
        <select
          id="catalog-lab-select"
          className="form-input form-select"
          style={styles.select}
          value={selectedLabId}
          onChange={e => {
            onSelectLab(e.target.value);
            onSelectPrefix([]);
          }}
        >
          <option value="">选择 Lab</option>
          {labs.map(lab => (
            <option key={lab.lab_id} value={lab.lab_id}>{lab.name}</option>
          ))}
        </select>
      </div>
      <button
        type="button"
        style={{
          ...styles.allBtn,
          ...(allSelected ? styles.allBtnSelected : {}),
        }}
        onClick={() => onSelectPrefix([])}
      >
        全部用例
        {selectedLabName && allSelected && (
          <span style={styles.allBtnMeta}>{selectedLabName}</span>
        )}
      </button>
      {loading && (
        <div style={styles.loadingRow}>
          <span style={styles.spinner} aria-hidden />
          <span style={styles.hint}>加载目录树…</span>
        </div>
      )}
      {!loading && !tree && selectedLabId && (
        <p style={styles.emptyTree}>该 Lab 下暂无目录段，创建用例后将自动生成</p>
      )}
      {!loading && tree && (
        <div style={styles.tree} role="tree">
          {renderNode(tree, 0)}
        </div>
      )}
      {!selectedLabId && (
        <p style={styles.emptyTree}>选择 Lab 以浏览目录</p>
      )}
    </aside>
  );
};

const styles: Record<string, React.CSSProperties> = {
  sidebarHeader: {
    marginBottom: 'var(--space-3)',
  },
  labSelect: {
    marginBottom: 'var(--space-3)',
  },
  labLabel: {
    ...catalogStyles.labelCaps,
    display: 'block',
    marginBottom: 'var(--space-1)',
  },
  select: {
    width: '100%',
    fontSize: 13,
  },
  allBtn: {
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: 2,
    textAlign: 'left',
    padding: 'var(--space-2) var(--space-3)',
    marginBottom: 'var(--space-3)',
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-md)',
    backgroundColor: 'var(--surface-primary)',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--text-primary)',
    transition: 'background-color var(--transition-fast), border-color var(--transition-fast)',
  },
  allBtnSelected: {
    borderColor: 'var(--accent-primary)',
    backgroundColor: 'color-mix(in srgb, var(--accent-primary) 8%, var(--surface-primary))',
  },
  allBtnMeta: {
    fontSize: 11,
    color: 'var(--text-tertiary)',
    fontWeight: 400,
  },
  tree: {
    fontSize: 13,
  },
  expandBtn: {
    border: 'none',
    background: 'none',
    cursor: 'pointer',
    padding: '4px 6px',
    color: 'var(--text-tertiary)',
    fontSize: 11,
    lineHeight: 1,
    borderRadius: 'var(--radius-sm)',
  },
  expandSpacer: {
    width: 22,
    flexShrink: 0,
  },
  nodeBtn: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 'var(--space-2)',
    textAlign: 'left',
    border: 'none',
    background: 'none',
    cursor: 'pointer',
    padding: '6px 8px',
    fontSize: 13,
    color: 'var(--text-primary)',
    borderRadius: 'var(--radius-md)',
  },
  nodeBtnSelected: {
    fontWeight: 600,
    color: 'var(--accent-primary)',
  },
  nodeName: {
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  count: {
    flexShrink: 0,
    fontSize: 10,
    fontWeight: 600,
    padding: '2px 6px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--surface-tertiary)',
    color: 'var(--text-tertiary)',
  },
  hint: {
    fontSize: 12,
    color: 'var(--text-tertiary)',
  },
  loadingRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
    padding: 'var(--space-2) 0',
  },
  spinner: {
    width: 14,
    height: 14,
    border: '2px solid var(--border-default)',
    borderTopColor: 'var(--accent-primary)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  emptyTree: {
    margin: 'var(--space-2) 0 0',
    fontSize: 12,
    lineHeight: 1.5,
    color: 'var(--text-tertiary)',
    padding: 'var(--space-3)',
    ...catalogStyles.cardInset,
    borderStyle: 'dashed',
  },
};

export default CatalogTreeSidebar;
