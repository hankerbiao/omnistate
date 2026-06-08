import { useMemo } from 'react';
import type { UnifiedCaseItem, TypeFilter } from './testCaseBoardTypes';
import { getManualDot, getAutoDot, getManualLabel, getAutoLabel, fwIcon, fwColor } from './testCaseBoardTypes';
import { boardStyles as S } from './testCaseBoardStyles';

interface TestCaseBoardKanbanProps {
  items: UnifiedCaseItem[];
  typeFilter: TypeFilter;
  onCaseClick: (item: UnifiedCaseItem) => void;
}

const AUTO_COLUMNS = ['ACTIVE', 'INACTIVE', 'DRAFT', 'DEPRECATED'];
const MANUAL_COLUMNS = ['DRAFT', 'PENDING_REVIEW', 'IN_REVIEW', 'REVISE', 'DONE', 'REJECTED'];

function getColumns(typeFilter: TypeFilter): string[] {
  if (typeFilter === 'auto') return AUTO_COLUMNS;
  if (typeFilter === 'manual') return MANUAL_COLUMNS;
  return [...AUTO_COLUMNS, ...MANUAL_COLUMNS];
}

function getColumnLabel(status: string): string {
  if (AUTO_COLUMNS.includes(status)) return getAutoLabel(status);
  return getManualLabel(status);
}

function getColumnDot(status: string): string {
  if (AUTO_COLUMNS.includes(status)) return getAutoDot(status);
  return getManualDot(status);
}

const TestCaseBoardKanban: React.FC<TestCaseBoardKanbanProps> = ({ items, typeFilter, onCaseClick }) => {
  const columns = useMemo(() => getColumns(typeFilter), [typeFilter]);

  const grouped = useMemo(() => {
    const map = new Map<string, UnifiedCaseItem[]>();
    for (const col of columns) map.set(col, []);
    for (const item of items) {
      const bucket = map.get(item.status);
      if (bucket) bucket.push(item);
      else {
        const existing = map.get(item.status) || [];
        existing.push(item);
        map.set(item.status, existing);
      }
    }
    return map;
  }, [items, columns]);

  return (
    <div style={S.kanbanWrap}>
      {columns.map(status => {
        const colItems = grouped.get(status) || [];
        const dotColor = getColumnDot(status);
        const label = getColumnLabel(status);

        return (
          <div key={status} style={S.kanbanColumn}>
            <div style={S.kanbanColumnHead}>
              <span style={S.kanbanColumnTitle}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: dotColor }} />
                {label}
              </span>
              <span style={S.kanbanColumnCount}>{colItems.length}</span>
            </div>
            <div style={S.kanbanBody}>
              {colItems.map(item => {
                const isManual = item.type === 'manual';
                const dotColor = isManual ? getManualDot(item.status) : getAutoDot(item.status);

                return (
                  <div
                    key={`${item.type}-${item.id}`}
                    style={S.kanbanCard}
                    onClick={() => onCaseClick(item)}
                    title={item.caseId}
                  >
                    <div style={S.kanbanCardTitle}>{item.title}</div>
                    <div style={S.kanbanCardMeta}>
                      <span style={{
                        ...S.typeBadge(isManual),
                        fontSize: 9,
                      }}>
                        {isManual ? '\uD83D\uDCCB' : '\u26A1'}
                        {isManual ? '手工' : '自动'}
                      </span>
                      {!isManual && item.framework && (
                        <span style={{ fontSize: 9, ...S.frameworkTag(fwColor(item.framework)) }}>
                          {fwIcon(item.framework)} {item.framework}
                        </span>
                      )}
                      {item.priority && (
                        <span style={{ fontSize: 9, color: 'var(--text-tertiary)', fontWeight: 600 }}>
                          {item.priority}
                        </span>
                      )}
                      <span style={{ fontSize: 9, fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-tertiary)', marginLeft: 'auto' }}>
                        {item.caseId.slice(0, 12)}
                      </span>
                    </div>
                  </div>
                );
              })}
              {colItems.length === 0 && (
                <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 11 }}>
                  暂无
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default TestCaseBoardKanban;
