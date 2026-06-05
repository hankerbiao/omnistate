import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { api } from '../services/api';
import { getCatalogLabs } from '../services/catalogLabsCache';
import type { CatalogLab, TestCaseResponse, ListTestCasesParams } from '../types';
import TestCaseDetailModal from './TestCaseDetailModal';
import CreateTestCaseForm from './CreateTestCaseForm';
import CatalogTreeSidebar from './catalog/CatalogTreeSidebar';
import { catalogStyles } from './catalog/catalogStyles';
import PageToolbar, { StatPill } from './ui/PageToolbar';
import { PRIORITY_FILTER_OPTIONS } from '../constants/testCaseLabels';
import { TEST_CASE_STATUS_FILTER_OPTIONS, getStateLabel, getWorkflowStateStyle } from '../constants/workflowLabels';

interface FilterParams {
  ref_req_id?: string;
  status?: string;
  owner_id?: string;
  reviewer_id?: string;
  priority?: string;
  is_active?: boolean;
}

const STATUS_OPTIONS = TEST_CASE_STATUS_FILTER_OPTIONS;

const PAGE_SIZE = 20;

interface ManualTestCaseListProps {
  initialStatusFilter?: string;
}

const ManualTestCaseList: React.FC<ManualTestCaseListProps> = ({ initialStatusFilter = '' }) => {
  const [testCases, setTestCases] = useState<TestCaseResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [currentOffset, setCurrentOffset] = useState(0);

  const [filters, setFilters] = useState<FilterParams>(
    initialStatusFilter ? { status: initialStatusFilter } : {},
  );
  const [showFilters, setShowFilters] = useState(Boolean(initialStatusFilter));
  const [selectedTestCase, setSelectedTestCase] = useState<TestCaseResponse | null>(null);
  const [editingTestCase, setEditingTestCase] = useState<TestCaseResponse | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [labs, setLabs] = useState<CatalogLab[]>([]);
  const [selectedLabId, setSelectedLabId] = useState('');
  const [catalogPrefix, setCatalogPrefix] = useState<string[]>([]);

  const selectedLabName = useMemo(
    () => labs.find(l => l.lab_id === selectedLabId)?.name || '',
    [labs, selectedLabId],
  );

  const fetchSeqRef = useRef(0);

  const fetchTestCases = useCallback(async (
    filterParams: FilterParams,
    offset: number,
    labId: string,
    prefix: string[],
  ) => {
    if (!labId) {
      setTestCases([]);
      setTotalCount(0);
      return;
    }

    const seq = ++fetchSeqRef.current;
    setLoading(true);
    setError(null);

    try {
      const params: ListTestCasesParams = {
        ...filterParams,
        lab_id: labId,
        catalog_prefix: prefix.length > 0 ? JSON.stringify(prefix) : undefined,
        limit: PAGE_SIZE,
        offset,
      };

      Object.keys(params).forEach(key => {
        if (params[key as keyof ListTestCasesParams] === undefined || params[key as keyof ListTestCasesParams] === '') {
          delete params[key as keyof ListTestCasesParams];
        }
      });

      const response = await api.listTestCases(params);
      if (seq !== fetchSeqRef.current) {
        return;
      }

      if (response.code === 0 || response.code === 200) {
        setTestCases(response.data || []);
        setTotalCount(response.data?.length || 0);
      } else {
        setError(response.message || '获取测试用例列表失败');
      }
    } catch (err) {
      if (seq !== fetchSeqRef.current) {
        return;
      }
      setError('获取测试用例列表失败');
      console.error('Fetch test cases error:', err);
    } finally {
      if (seq === fetchSeqRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    getCatalogLabs({ active_only: true })
      .then(items => {
        if (cancelled) return;
        setLabs(items);
        setSelectedLabId(prev => prev || items[0]?.lab_id || '');
      })
      .catch(() => {
        if (!cancelled) setLabs([]);
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    fetchTestCases(filters, currentOffset, selectedLabId, catalogPrefix);
  }, [fetchTestCases, filters, currentOffset, selectedLabId, catalogPrefix]);

  const handleApplyFilters = () => {
    setCurrentOffset(0);
  };

  const handleResetFilters = () => {
    setFilters({});
    setCurrentOffset(0);
  };

  const handleFilterChange = (key: keyof FilterParams, value: string | boolean | undefined) => {
    setFilters(prev => ({
      ...prev,
      [key]: value === '' ? undefined : value,
    }));
  };

  const handlePageChange = (newOffset: number) => {
    setCurrentOffset(newOffset);
  };

  const getStatusLabel = (status: string) => getStateLabel(status, 'TEST_CASE');

  const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1;
  const currentPage = Math.floor(currentOffset / PAGE_SIZE) + 1;

  const breadcrumbParts = useMemo(() => {
    if (!selectedLabId) return [] as string[];
    if (catalogPrefix.length === 0) return [selectedLabName || 'Lab', '全部用例'];
    return [selectedLabName || 'Lab', ...catalogPrefix];
  }, [selectedLabId, selectedLabName, catalogPrefix]);

  return (
    <div style={styles.layout}>
      <CatalogTreeSidebar
        labs={labs}
        selectedLabId={selectedLabId}
        selectedPrefix={catalogPrefix}
        onSelectLab={labId => {
          setSelectedLabId(labId);
          setCatalogPrefix([]);
          setCurrentOffset(0);
        }}
        onSelectPrefix={prefix => {
          setCatalogPrefix(prefix);
          setCurrentOffset(0);
        }}
      />
      <div style={styles.container}>
      {breadcrumbParts.length > 0 && (
        <nav style={catalogStyles.breadcrumbBar} aria-label="当前目录">
          <span style={styles.breadcrumbLabel}>当前目录</span>
          <div style={styles.breadcrumbChips}>
            {breadcrumbParts.map((part, i) => (
              <span key={`${part}-${i}`} style={styles.breadcrumbChipWrap}>
                {i > 0 && <span style={styles.breadcrumbSep}>/</span>}
                <span
                  style={{
                    ...styles.breadcrumbChip,
                    ...(i === 0 ? styles.breadcrumbChipLab : {}),
                    ...(i === breadcrumbParts.length - 1 ? styles.breadcrumbChipCurrent : {}),
                  }}
                >
                  {part}
                </span>
              </span>
            ))}
          </div>
        </nav>
      )}
      <PageToolbar
        meta={(
          <>
            <StatPill label="当前列表" value={totalCount} tone="info" />
            {selectedLabName && (
              <StatPill label="Lab" value={selectedLabName} />
            )}
            {catalogPrefix.length > 0 && (
              <StatPill label="目录" value={catalogPrefix.join(' / ')} />
            )}
          </>
        )}
        actions={(
          <>
            <button type="button" className="btn btn--primary btn--sm" onClick={() => setShowCreate(true)}>
              + 新建用例
            </button>
            <button
              type="button"
              className={`btn btn--secondary btn--sm${showFilters ? ' btn--active' : ''}`}
              onClick={() => setShowFilters(!showFilters)}
              aria-expanded={showFilters}
            >
              筛选 {showFilters ? '▴' : '▾'}
            </button>
            <button
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={() => fetchTestCases(filters, currentOffset, selectedLabId, catalogPrefix)}
              disabled={loading}
            >
              {loading ? '加载中…' : '刷新'}
            </button>
          </>
        )}
      />

      {showFilters && (
        <div className="surface-card" style={{ ...styles.filterBar, marginBottom: 20, border: undefined, boxShadow: undefined }}>
          <div style={styles.filterGrid}>
            <div style={styles.filterItem}>
              <label style={styles.filterLabel}>关联需求</label>
              <input
                type="text"
                style={styles.filterInput}
                placeholder="输入需求编号"
                value={filters.ref_req_id || ''}
                onChange={e => handleFilterChange('ref_req_id', e.target.value || undefined)}
              />
            </div>
            <div style={styles.filterItem}>
              <label style={styles.filterLabel}>状态</label>
              <select
                style={styles.filterSelect}
                value={filters.status || ''}
                onChange={e => handleFilterChange('status', e.target.value || undefined)}
              >
                {STATUS_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div style={styles.filterItem}>
              <label style={styles.filterLabel}>优先级</label>
              <select
                style={styles.filterSelect}
                value={filters.priority || ''}
                onChange={e => handleFilterChange('priority', e.target.value || undefined)}
              >
                {PRIORITY_FILTER_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div style={styles.filterItem}>
              <label style={styles.filterLabel}>负责人</label>
              <input
                type="text"
                style={styles.filterInput}
                placeholder="输入负责人ID"
                value={filters.owner_id || ''}
                onChange={e => handleFilterChange('owner_id', e.target.value || undefined)}
              />
            </div>
            <div style={styles.filterItem}>
              <label style={styles.filterLabel}>是否激活</label>
              <select
                style={styles.filterSelect}
                value={filters.is_active === undefined ? '' : String(filters.is_active)}
                onChange={e => handleFilterChange('is_active', e.target.value === '' ? undefined : e.target.value === 'true')}
              >
                <option value="">全部</option>
                <option value="true">是</option>
                <option value="false">否</option>
              </select>
            </div>
          </div>
          <div style={styles.filterActions}>
            <button type="button" className="btn btn--secondary btn--sm" onClick={handleResetFilters}>
              重置
            </button>
            <button type="button" className="btn btn--primary btn--sm" onClick={handleApplyFilters}>
              应用筛选
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="error-banner" style={{ marginBottom: 16 }}>
          <span aria-hidden>⚠</span> {error}
        </div>
      )}

      <div className="surface-card" style={styles.tableWrapper}>
        {loading ? (
          <div style={styles.loadingState}>
            <div style={styles.spinner} />
            <span>加载中...</span>
          </div>
        ) : testCases.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyIconWrap} aria-hidden>
              <span style={styles.emptyIcon}>📋</span>
            </div>
            <p style={styles.emptyTitle}>暂无测试用例</p>
            <p style={styles.emptyHint}>
              {selectedLabId
                ? catalogPrefix.length > 0
                  ? '当前目录下还没有用例，可在此路径下新建'
                  : '选择左侧子目录筛选，或新建第一条用例'
                : '请先在左侧选择 Lab'}
            </p>
            {selectedLabId && (
              <button
                type="button"
                className="btn btn--primary btn--sm"
                style={styles.emptyCta}
                onClick={() => setShowCreate(true)}
              >
                + 新建用例
              </button>
            )}
          </div>
        ) : (
          <>
            <table style={styles.table}>
              <thead>
                <tr style={styles.tableHeader}>
                  <th style={{ ...styles.th, width: '120px' }}>用例ID</th>
                  <th style={styles.th}>用例标题</th>
                  <th style={{ ...styles.th, width: '200px' }}>目录</th>
                  <th style={{ ...styles.th, width: '100px' }}>关联需求</th>
                  <th style={{ ...styles.th, width: '100px' }}>状态</th>
                  <th style={{ ...styles.th, width: '70px' }}>优先级</th>
                  <th style={{ ...styles.th, width: '100px' }}>负责人</th>
                  <th style={{ ...styles.th, width: '100px' }}>审核人</th>
                  <th style={{ ...styles.th, width: '60px' }}>版本</th>
                  <th style={{ ...styles.th, width: '140px' }}>创建时间</th>
                </tr>
              </thead>
              <tbody>
                {testCases.map((testCase, index) => {
                  const statusStyle = getWorkflowStateStyle(testCase.status);
                  return (
                    <tr
                      key={testCase.id}
                      onClick={() => setSelectedTestCase(testCase)}
                      style={{
                        ...styles.tr,
                        cursor: 'pointer',
                        animationDelay: `${index * 20}ms`,
                      }}
                    >
                      <td style={styles.td}>
                        <span style={styles.caseId}>{testCase.case_id}</span>
                      </td>
                      <td style={styles.td}>
                        <span style={styles.caseTitle}>{testCase.title}</span>
                      </td>
                      <td style={styles.td}>
                        <span style={styles.catalogText}>
                          {testCase.catalog_breadcrumb || testCase.catalog_path?.join(' / ') || '-'}
                        </span>
                      </td>
                      <td style={styles.td}>
                        <span style={styles.refReqId}>{testCase.ref_req_id || '-'}</span>
                      </td>
                      <td style={styles.td}>
                        <span
                          style={{
                            ...styles.statusBadge,
                            backgroundColor: statusStyle.bg,
                            color: statusStyle.color,
                          }}
                        >
                          {getStatusLabel(testCase.status)}
                        </span>
                      </td>
                      <td style={styles.td}>
                        <span style={styles.priorityBadge}>{testCase.priority || '-'}</span>
                      </td>
                      <td style={styles.td}>
                        <span style={styles.ownerBadge}>{testCase.owner_id || '-'}</span>
                      </td>
                      <td style={styles.td}>
                        <span style={styles.reviewerBadge}>{testCase.reviewer_id || '-'}</span>
                      </td>
                      <td style={styles.td}>
                        <span style={styles.versionBadge}>v{testCase.version}</span>
                      </td>
                      <td style={styles.td}>
                        <span style={styles.timeText}>
                          {new Date(testCase.created_at).toLocaleString('zh-CN', {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            <div style={styles.pagination}>
              <span style={styles.paginationInfo}>
                显示 {currentOffset + 1}-{Math.min(currentOffset + PAGE_SIZE, totalCount)} 条，共 {totalCount} 条
              </span>
              <div style={styles.paginationControls}>
                <button
                  style={{ ...styles.pageBtn, ...(currentPage <= 1 ? styles.pageBtnDisabled : {}) }}
                  onClick={() => handlePageChange(0)}
                  disabled={currentPage <= 1}
                >
                  首页
                </button>
                <button
                  style={{ ...styles.pageBtn, ...(currentPage <= 1 ? styles.pageBtnDisabled : {}) }}
                  onClick={() => handlePageChange(currentOffset - PAGE_SIZE)}
                  disabled={currentPage <= 1}
                >
                  上一页
                </button>
                <span style={styles.pageIndicator}>
                  第 {currentPage} / {totalPages} 页
                </span>
                <button
                  style={{ ...styles.pageBtn, ...(currentPage >= totalPages ? styles.pageBtnDisabled : {}) }}
                  onClick={() => handlePageChange(currentOffset + PAGE_SIZE)}
                  disabled={currentPage >= totalPages}
                >
                  下一页
                </button>
                <button
                  style={{ ...styles.pageBtn, ...(currentPage >= totalPages ? styles.pageBtnDisabled : {}) }}
                  onClick={() => handlePageChange((totalPages - 1) * PAGE_SIZE)}
                  disabled={currentPage >= totalPages}
                >
                  末页
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {selectedTestCase && (
        <TestCaseDetailModal
          testCase={selectedTestCase}
          onClose={() => setSelectedTestCase(null)}
          onEdit={() => {
            setEditingTestCase(selectedTestCase);
            setSelectedTestCase(null);
          }}
        />
      )}

      {editingTestCase && (
        <CreateTestCaseForm
          editTestCase={editingTestCase}
          onClose={() => setEditingTestCase(null)}
          onSuccess={() => fetchTestCases(filters, currentOffset, selectedLabId, catalogPrefix)}
        />
      )}

      {showCreate && (
        <CreateTestCaseForm
          defaultLabId={selectedLabId}
          defaultCatalogPrefix={catalogPrefix}
          onClose={() => setShowCreate(false)}
          onSuccess={() => {
            setShowCreate(false);
            fetchTestCases(filters, currentOffset, selectedLabId, catalogPrefix);
          }}
        />
      )}
      </div>
    </div>
  );
};

const styles = {
  layout: {
    display: 'flex',
    minHeight: '100%',
  } as const,
  container: {
    flex: 1,
    padding: 'var(--page-padding)',
    maxWidth: '1600px',
    margin: '0 auto',
    animation: 'fadeIn 0.4s ease',
    overflow: 'auto',
  } as const,
  breadcrumbLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase',
    letterSpacing: '0.4px',
    flexShrink: 0,
  } as const,
  breadcrumbChips: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 4,
    flex: 1,
  } as const,
  breadcrumbChipWrap: {
    display: 'inline-flex',
    alignItems: 'center',
  } as const,
  breadcrumbSep: {
    margin: '0 4px',
    color: 'var(--text-tertiary)',
    fontSize: 12,
  } as const,
  breadcrumbChip: {
    fontSize: 13,
    padding: '2px 8px',
    borderRadius: 'var(--radius-full)',
    backgroundColor: 'var(--surface-secondary)',
    color: 'var(--text-secondary)',
  } as const,
  breadcrumbChipLab: {
    color: 'var(--accent-primary)',
    fontWeight: 600,
    backgroundColor: 'var(--status-info-bg)',
  } as const,
  breadcrumbChipCurrent: {
    color: 'var(--text-primary)',
    fontWeight: 600,
  } as const,
  catalogText: {
    fontSize: 12,
    color: '#6b7280',
  } as const,
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
  } as const,
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
  } as const,
  title: {
    fontSize: '28px',
    fontWeight: 700,
    color: 'var(--text-primary)',
    letterSpacing: '-0.5px',
    margin: 0,
  } as const,
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: '28px',
    height: '28px',
    padding: '0 10px',
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: "'JetBrains Mono', monospace",
    color: 'var(--accent-purple)',
    backgroundColor: 'rgba(163, 113, 247, 0.15)',
    borderRadius: '14px',
  } as const,
  headerActions: {
    display: 'flex',
    gap: '10px',
  } as const,
  filterToggleBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  createBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 18px',
    fontSize: '13px',
    fontWeight: 600,
    color: '#fff',
    background: 'linear-gradient(135deg, #6366f1 0%, var(--accent-primary) 100%)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    boxShadow: '0 2px 8px rgba(37, 99, 235, 0.25)',
    transition: 'all var(--transition-fast)',
  } as const,
  actionBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  btnIcon: {
    fontSize: '14px',
  } as const,
  filterBar: {
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    padding: '20px',
    marginBottom: '20px',
    animation: 'slideDown 0.3s ease',
  } as const,
  filterGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: '16px',
    marginBottom: '16px',
  } as const,
  filterItem: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '6px',
  } as const,
  filterLabel: {
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  } as const,
  filterInput: {
    padding: '8px 12px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
    transition: 'border-color var(--transition-fast)',
  } as const,
  filterSelect: {
    padding: '8px 12px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
    cursor: 'pointer',
  } as const,
  filterActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
    paddingTop: '12px',
    borderTop: '1px solid var(--border-muted)',
  } as const,
  resetBtn: {
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  applyBtn: {
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: 500,
    color: '#fff',
    backgroundColor: 'var(--accent-purple)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '14px 18px',
    backgroundColor: 'var(--status-error-bg)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--accent-red)',
    fontSize: '14px',
    marginBottom: '20px',
  } as const,
  tableWrapper: {
    overflow: 'hidden',
    backgroundColor: 'transparent',
    border: 'none',
    borderRadius: 0,
  } as const,
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  } as const,
  tableHeader: {
    backgroundColor: 'var(--bg-tertiary)',
  } as const,
  th: {
    padding: '12px 16px',
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    textAlign: 'left' as const,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    borderBottom: '1px solid var(--border-default)',
  } as const,
  tr: {
    borderBottom: '1px solid var(--border-muted)',
    transition: 'background-color var(--transition-fast)',
    animation: 'slideUp 0.3s ease forwards',
    opacity: 0,
  } as const,
  td: {
    padding: '12px 16px',
    fontSize: '13px',
    color: 'var(--text-primary)',
  } as const,
  caseId: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--accent-purple)',
  } as const,
  caseTitle: {
    fontWeight: 500,
    maxWidth: '300px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  } as const,
  refReqId: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '11px',
    color: 'var(--accent-cyan)',
  } as const,
  statusBadge: {
    display: 'inline-flex',
    padding: '3px 8px',
    fontSize: '10px',
    fontWeight: 600,
    borderRadius: '10px',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.3px',
  } as const,
  priorityBadge: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '11px',
    fontWeight: 600,
    color: 'var(--accent-orange)',
  } as const,
  ownerBadge: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
  } as const,
  reviewerBadge: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
  } as const,
  versionBadge: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-tertiary)',
    padding: '2px 6px',
    borderRadius: '4px',
  } as const,
  timeText: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    fontFamily: "'JetBrains Mono', monospace",
  } as const,
  loadingState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    padding: '60px',
    color: 'var(--text-secondary)',
  } as const,
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid var(--border-default)',
    borderTopColor: 'var(--accent-purple)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  } as const,
  emptyState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 'var(--space-3)',
    padding: '72px var(--space-6)',
    color: 'var(--text-muted)',
  } as const,
  emptyIconWrap: {
    width: 64,
    height: 64,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 'var(--radius-xl)',
    backgroundColor: 'var(--surface-tertiary)',
    border: '1px solid var(--border-subtle)',
    boxShadow: 'var(--shadow-sm)',
  } as const,
  emptyIcon: {
    fontSize: '28px',
    opacity: 0.5,
  } as const,
  emptyTitle: {
    fontSize: '15px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    margin: 0,
  } as const,
  emptyHint: {
    fontSize: '13px',
    color: 'var(--text-tertiary)',
    margin: 0,
    textAlign: 'center',
    maxWidth: 320,
    lineHeight: 1.5,
  } as const,
  emptyCta: {
    marginTop: 'var(--space-2)',
  } as const,
  pagination: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderTop: '1px solid var(--border-muted)',
    backgroundColor: 'var(--bg-tertiary)',
  } as const,
  paginationInfo: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
  } as const,
  paginationControls: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  } as const,
  pageBtn: {
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  } as const,
  pageBtnDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  } as const,
  pageIndicator: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
    padding: '0 12px',
  } as const,
};

export default ManualTestCaseList;