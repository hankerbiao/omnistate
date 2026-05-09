import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { DutResponse, DutDetailResponse, CreateDutRequest, UpdateDutRequest, ListDutsParams, ExternalMachineItem, ImportExternalMachinesResponse } from '../types';

const STATUS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'AVAILABLE', label: '可用' },
  { value: 'IN_USE', label: '使用中' },
  { value: 'MAINTENANCE', label: '维护中' },
  { value: 'RETIRED', label: '已退役' },
];

const OS_TYPE_OPTIONS = [
  { value: 'Linux', label: 'Linux' },
  { value: 'Windows', label: 'Windows' },
  { value: 'Other', label: '其他' },
];

const DutManagement: React.FC = () => {
  const [duts, setDuts] = useState<DutResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [regions, setRegions] = useState<string[]>([]);

  const [filters, setFilters] = useState<ListDutsParams>({});
  const [showFilters, setShowFilters] = useState(false);

  const [selectedDut, setSelectedDut] = useState<DutDetailResponse | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingDut, setEditingDut] = useState<DutResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // External system integration state
  const [showExternalModal, setShowExternalModal] = useState(false);
  const [externalMachines, setExternalMachines] = useState<ExternalMachineItem[]>([]);
  const [externalLoading, setExternalLoading] = useState(false);
  const [externalRegions, setExternalRegions] = useState<string[]>([]);
  const [selectedMachines, setSelectedMachines] = useState<Set<string>>(new Set());
  const [externalFilters, setExternalFilters] = useState({ region: '', status: '', search: '' });
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportExternalMachinesResponse | null>(null);

  const fetchDuts = useCallback(async (params: ListDutsParams = {}) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listDuts({ limit: 100, ...params });
      if (response.code === 0 || response.code === 200) {
        setDuts(response.data || []);
      } else {
        setError(response.message || '获取 DUT 列表失败');
      }
    } catch (err) {
      setError('获取 DUT 列表失败');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRegions = useCallback(async () => {
    try {
      const response = await api.listDutRegions();
      if (response.data) {
        setRegions(response.data);
      }
    } catch (err) {
      console.error('Failed to fetch regions:', err);
    }
  }, []);

  const fetchExternalMachines = useCallback(async () => {
    setExternalLoading(true);
    try {
      const response = await api.getExternalMachines(externalFilters);
      if (response.data) {
        setExternalMachines(response.data.items || []);
        setExternalRegions(response.data.regions || []);
      }
    } catch (err) {
      console.error('Failed to fetch external machines:', err);
    } finally {
      setExternalLoading(false);
    }
  }, [externalFilters]);

  const handleOpenExternalModal = () => {
    setShowExternalModal(true);
    setSelectedMachines(new Set());
    setImportResult(null);
    fetchExternalMachines();
  };

  const handleToggleMachine = (externalId: string) => {
    const newSelected = new Set(selectedMachines);
    if (newSelected.has(externalId)) {
      newSelected.delete(externalId);
    } else {
      newSelected.add(externalId);
    }
    setSelectedMachines(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedMachines.size === externalMachines.length) {
      setSelectedMachines(new Set());
    } else {
      setSelectedMachines(new Set(externalMachines.map(m => m.external_id)));
    }
  };

  const handleImport = async () => {
    if (selectedMachines.size === 0) {
      alert('请选择要导入的机器');
      return;
    }

    const selectedItems = externalMachines.filter(m => selectedMachines.has(m.external_id));
    const importData = selectedItems.map(m => ({
      external_id: m.external_id,
      name: m.name,
      bmc_ip: m.bmc_ip,
      bmc_password: 'admin', // Default password
      os_ip: m.os_ip,
      os_password: 'root', // Default password
      region: m.region,
      os_type: m.os_type,
      tags: m.tags,
      metadata: {
        owner: m.owner,
        model: m.model,
        cpu: m.cpu,
        memory: m.memory,
        storage: m.storage,
      },
    }));

    setImporting(true);
    try {
      const response = await api.importExternalMachines(importData);
      if (response.data) {
        setImportResult(response.data);
        if (response.data.success) {
          fetchDuts(filters);
          fetchRegions();
        }
      }
    } catch (err) {
      console.error('Failed to import machines:', err);
      alert('导入失败');
    } finally {
      setImporting(false);
    }
  };

  useEffect(() => {
    fetchDuts(filters);
    fetchRegions();
  }, []);

  const handleViewDetail = async (dut: DutResponse) => {
    try {
      const response = await api.getDut(dut.dut_id);
      if (response.data) {
        setSelectedDut(response.data);
        setShowDetailModal(true);
      }
    } catch (err) {
      setError('获取 DUT 详情失败');
      console.error(err);
    }
  };

  const handleDelete = async (dut: DutResponse) => {
    if (!confirm(`确定删除 DUT "${dut.name}" 吗？`)) return;

    try {
      await api.deleteDut(dut.dut_id);
      fetchDuts(filters);
    } catch (err) {
      setError('删除 DUT 失败');
      console.error(err);
    }
  };

  const handleCreate = async (data: CreateDutRequest) => {
    setSubmitting(true);
    try {
      await api.createDut(data);
      setShowCreateModal(false);
      fetchDuts(filters);
      fetchRegions();
    } catch (err) {
      setError('创建 DUT 失败');
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdate = async (data: UpdateDutRequest) => {
    if (!editingDut) return;
    setSubmitting(true);
    try {
      await api.updateDut(editingDut.dut_id, data);
      setEditingDut(null);
      fetchDuts(filters);
    } catch (err) {
      setError('更新 DUT 失败');
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusStyle = (status: string) => {
    const styleMap: Record<string, { bg: string; color: string }> = {
      AVAILABLE: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
      IN_USE: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
      MAINTENANCE: { bg: 'var(--status-warning-bg)', color: 'var(--status-warning)' },
      RETIRED: { bg: 'var(--surface-tertiary)', color: 'var(--text-tertiary)' },
    };
    return styleMap[status] || { bg: 'var(--surface-tertiary)', color: 'var(--text-secondary)' };
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.title}>DUT 管理</h1>
          <span style={styles.badge}>{duts.length}</span>
        </div>
        <div style={styles.headerActions}>
          <button style={styles.filterToggleBtn} onClick={() => setShowFilters(!showFilters)}>
            <span>⚙</span> 筛选 {showFilters ? '▲' : '▼'}
          </button>
          <button style={styles.actionBtn} onClick={() => fetchDuts(filters)} disabled={loading}>
            <span>↻</span> {loading ? '加载中' : '刷新'}
          </button>
          <button style={styles.actionBtn} onClick={handleOpenExternalModal}>
            <span>📥</span> 导入外部系统
          </button>
          <button style={styles.createBtn} onClick={() => setShowCreateModal(true)}>
            <span>+</span> 新建 DUT
          </button>
        </div>
      </div>

      {showFilters && (
        <div style={styles.filterBar}>
          <div style={styles.filterGrid}>
            <div style={styles.filterItem}>
              <label style={styles.filterLabel}>状态</label>
              <select
                style={styles.filterSelect}
                value={filters.status || ''}
                onChange={e => setFilters({ ...filters, status: e.target.value || undefined })}
              >
                {STATUS_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div style={styles.filterItem}>
              <label style={styles.filterLabel}>区域</label>
              <select
                style={styles.filterSelect}
                value={filters.region || ''}
                onChange={e => setFilters({ ...filters, region: e.target.value || undefined })}
              >
                <option value="">全部</option>
                {regions.map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
            <div style={styles.filterItem}>
              <label style={styles.filterLabel}>搜索</label>
              <input
                type="text"
                style={styles.filterInput}
                placeholder="名称/IP"
                value={filters.search || ''}
                onChange={e => setFilters({ ...filters, search: e.target.value || undefined })}
              />
            </div>
          </div>
          <div style={styles.filterActions}>
            <button style={styles.resetBtn} onClick={() => { setFilters({}); fetchDuts({}); }}>
              重置
            </button>
            <button style={styles.applyBtn} onClick={() => fetchDuts(filters)}>
              应用
            </button>
          </div>
        </div>
      )}

      {error && (
        <div style={styles.errorBanner}>
          <span>⚠</span> {error}
          <button onClick={() => setError(null)} style={styles.errorClose}>×</button>
        </div>
      )}

      <div style={styles.tableWrapper}>
        {loading ? (
          <div style={styles.loadingState}>
            <div style={styles.spinner} />
            <span>加载中...</span>
          </div>
        ) : duts.length === 0 ? (
          <div style={styles.emptyState}>
            <span style={styles.emptyIcon}>🖥</span>
            <p>暂无 DUT 设备</p>
          </div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr style={styles.tableHeader}>
                <th style={styles.th}>DUT ID</th>
                <th style={styles.th}>名称</th>
                <th style={styles.th}>BMC IP</th>
                <th style={styles.th}>OS IP</th>
                <th style={styles.th}>区域</th>
                <th style={styles.th}>OS 类型</th>
                <th style={styles.th}>状态</th>
                <th style={styles.th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {duts.map((dut) => {
                const statusStyle = getStatusStyle(dut.status);
                return (
                  <tr key={dut.id} style={styles.tr}>
                    <td style={styles.td}>
                      <span style={styles.dutId}>{dut.dut_id}</span>
                    </td>
                    <td style={styles.td}>{dut.name}</td>
                    <td style={styles.td}>
                      <span style={styles.ip}>{dut.bmc_ip}</span>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.ip}>{dut.os_ip}</span>
                    </td>
                    <td style={styles.td}>{dut.region}</td>
                    <td style={styles.td}>{dut.os_type}</td>
                    <td style={styles.td}>
                      <span style={{ ...styles.statusBadge, backgroundColor: statusStyle.bg, color: statusStyle.color }}>
                        {dut.status}
                      </span>
                    </td>
                    <td style={styles.td}>
                      <div style={styles.actionBtns}>
                        <button style={styles.viewBtn} onClick={() => handleViewDetail(dut)}>
                          查看
                        </button>
                        <button style={styles.editBtn} onClick={() => setEditingDut(dut)}>
                          编辑
                        </button>
                        <button style={styles.deleteBtn} onClick={() => handleDelete(dut)}>
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Detail Modal */}
      {showDetailModal && selectedDut && (
        <div style={styles.modalOverlay} onClick={() => setShowDetailModal(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h2 style={styles.modalTitle}>{selectedDut.name}</h2>
              <button style={styles.modalClose} onClick={() => setShowDetailModal(false)}>×</button>
            </div>
            <div style={styles.modalBody}>
              <div style={styles.detailGrid}>
                <div style={styles.detailSection}>
                  <h3 style={styles.detailSectionTitle}>基本信息</h3>
                  <div style={styles.detailRow}>
                    <span style={styles.detailLabel}>DUT ID</span>
                    <span style={styles.detailValue}>{selectedDut.dut_id}</span>
                  </div>
                  <div style={styles.detailRow}>
                    <span style={styles.detailLabel}>状态</span>
                    <span style={styles.detailValue}>
                      <span style={{ ...styles.statusBadge, ...getStatusStyle(selectedDut.status) }}>
                        {selectedDut.status}
                      </span>
                    </span>
                  </div>
                  <div style={styles.detailRow}>
                    <span style={styles.detailLabel}>区域</span>
                    <span style={styles.detailValue}>{selectedDut.region}</span>
                  </div>
                </div>
                <div style={styles.detailSection}>
                  <h3 style={styles.detailSectionTitle}>BMC 信息</h3>
                  <div style={styles.detailRow}>
                    <span style={styles.detailLabel}>BMC IP</span>
                    <span style={styles.detailValue}>{selectedDut.bmc_ip}</span>
                  </div>
                  <div style={styles.detailRow}>
                    <span style={styles.detailLabel}>用户名</span>
                    <span style={styles.detailValue}>{selectedDut.bmc_username}</span>
                  </div>
                  <div style={styles.detailRow}>
                    <span style={styles.detailLabel}>密码</span>
                    <span style={styles.detailValue}>{selectedDut.bmc_password}</span>
                  </div>
                </div>
                <div style={styles.detailSection}>
                  <h3 style={styles.detailSectionTitle}>OS 信息</h3>
                  <div style={styles.detailRow}>
                    <span style={styles.detailLabel}>OS IP</span>
                    <span style={styles.detailValue}>{selectedDut.os_ip}</span>
                  </div>
                  <div style={styles.detailRow}>
                    <span style={styles.detailLabel}>用户名</span>
                    <span style={styles.detailValue}>{selectedDut.os_username}</span>
                  </div>
                  <div style={styles.detailRow}>
                    <span style={styles.detailLabel}>密码</span>
                    <span style={styles.detailValue}>{selectedDut.os_password}</span>
                  </div>
                  <div style={styles.detailRow}>
                    <span style={styles.detailLabel}>OS 类型</span>
                    <span style={styles.detailValue}>{selectedDut.os_type}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create/Edit Modal */}
      {(showCreateModal || editingDut) && (
        <DutFormModal
          dut={editingDut}
          onClose={() => { setShowCreateModal(false); setEditingDut(null); }}
          onSubmit={editingDut ? handleUpdate : handleCreate}
          submitting={submitting}
        />
      )}

      {/* External System Import Modal */}
      {showExternalModal && (
        <ExternalImportModal
          machines={externalMachines}
          regions={externalRegions}
          filters={externalFilters}
          loading={externalLoading}
          selectedMachines={selectedMachines}
          importResult={importResult}
          importing={importing}
          onClose={() => { setShowExternalModal(false); setImportResult(null); }}
          onFiltersChange={setExternalFilters}
          onRefresh={fetchExternalMachines}
          onToggle={handleToggleMachine}
          onSelectAll={handleSelectAll}
          onImport={handleImport}
        />
      )}
    </div>
  );
};

// Form Modal Component
interface DutFormModalProps {
  dut?: DutResponse | null;
  onClose: () => void;
  onSubmit: (data: CreateDutRequest | UpdateDutRequest) => void;
  submitting: boolean;
}

const DutFormModal: React.FC<DutFormModalProps> = ({ dut, onClose, onSubmit, submitting }) => {
  const [formData, setFormData] = useState({
    name: dut?.name || '',
    bmc_ip: dut?.bmc_ip || '',
    bmc_username: dut?.bmc_username || 'admin',
    bmc_password: dut?.bmc_password || '',
    os_ip: dut?.os_ip || '',
    os_username: dut?.os_username || 'root',
    os_password: dut?.os_password || '',
    os_type: dut?.os_type || 'Linux',
    region: dut?.region || 'default',
    status: dut?.status || 'AVAILABLE',
    description: dut?.description || '',
  });

  const handleSubmit = () => {
    if (!formData.name || !formData.bmc_ip || !formData.bmc_password || !formData.os_ip || !formData.os_password) {
      alert('请填写必填字段');
      return;
    }
    onSubmit(formData);
  };

  const inputStyle = { ...styles.formInput, width: '100%', padding: '10px', fontSize: '14px' };
  const labelStyle = { display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px', color: 'var(--text-secondary)' };

  return (
    <div style={styles.modalOverlay} onClick={onClose}>
      <div style={styles.modal} onClick={e => e.stopPropagation()}>
        <div style={styles.modalHeader}>
          <h2 style={styles.modalTitle}>{dut ? '编辑 DUT' : '新建 DUT'}</h2>
          <button style={styles.modalClose} onClick={onClose}>×</button>
        </div>
        <div style={styles.modalBody}>
          <div style={styles.formGrid}>
            <div style={styles.formGroup}>
              <label style={labelStyle}>名称 *</label>
              <input style={inputStyle} value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} placeholder="机器名称" />
            </div>
            <div style={styles.formGroup}>
              <label style={labelStyle}>区域</label>
              <input style={inputStyle} value={formData.region} onChange={e => setFormData({ ...formData, region: e.target.value })} placeholder="区域" />
            </div>
            <div style={styles.formGroup}>
              <label style={labelStyle}>状态</label>
              <select style={inputStyle} value={formData.status} onChange={e => setFormData({ ...formData, status: e.target.value })}>
                {STATUS_OPTIONS.filter(s => s.value).map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div style={styles.formGroup}>
              <label style={labelStyle}>OS 类型</label>
              <select style={inputStyle} value={formData.os_type} onChange={e => setFormData({ ...formData, os_type: e.target.value })}>
                {OS_TYPE_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>

          <h3 style={{ ...styles.detailSectionTitle, marginTop: '20px' }}>BMC 信息</h3>
          <div style={styles.formGrid}>
            <div style={styles.formGroup}>
              <label style={labelStyle}>BMC IP *</label>
              <input style={inputStyle} value={formData.bmc_ip} onChange={e => setFormData({ ...formData, bmc_ip: e.target.value })} placeholder="192.168.1.1" />
            </div>
            <div style={styles.formGroup}>
              <label style={labelStyle}>用户名</label>
              <input style={inputStyle} value={formData.bmc_username} onChange={e => setFormData({ ...formData, bmc_username: e.target.value })} />
            </div>
            <div style={styles.formGroup}>
              <label style={labelStyle}>密码 *</label>
              <input type="password" style={inputStyle} value={formData.bmc_password} onChange={e => setFormData({ ...formData, bmc_password: e.target.value })} />
            </div>
          </div>

          <h3 style={{ ...styles.detailSectionTitle, marginTop: '20px' }}>OS 信息</h3>
          <div style={styles.formGrid}>
            <div style={styles.formGroup}>
              <label style={labelStyle}>OS IP *</label>
              <input style={inputStyle} value={formData.os_ip} onChange={e => setFormData({ ...formData, os_ip: e.target.value })} placeholder="192.168.1.2" />
            </div>
            <div style={styles.formGroup}>
              <label style={labelStyle}>用户名</label>
              <input style={inputStyle} value={formData.os_username} onChange={e => setFormData({ ...formData, os_username: e.target.value })} />
            </div>
            <div style={styles.formGroup}>
              <label style={labelStyle}>密码 *</label>
              <input type="password" style={inputStyle} value={formData.os_password} onChange={e => setFormData({ ...formData, os_password: e.target.value })} />
            </div>
          </div>

          <div style={{ ...styles.formGroup, marginTop: '20px' }}>
            <label style={labelStyle}>描述</label>
            <textarea style={{ ...inputStyle, height: '80px', resize: 'vertical' }} value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} />
          </div>
        </div>
        <div style={styles.modalFooter}>
          <button style={styles.cancelBtn} onClick={onClose} disabled={submitting}>取消</button>
          <button style={styles.submitBtn} onClick={handleSubmit} disabled={submitting}>
            {submitting ? '提交中...' : (dut ? '保存' : '创建')}
          </button>
        </div>
      </div>
    </div>
  );
};

// External System Import Modal Component
interface ExternalImportModalProps {
  machines: ExternalMachineItem[];
  regions: string[];
  filters: { region: string; status: string; search: string };
  loading: boolean;
  selectedMachines: Set<string>;
  importResult: ImportExternalMachinesResponse | null;
  importing: boolean;
  onClose: () => void;
  onFiltersChange: (filters: { region: string; status: string; search: string }) => void;
  onRefresh: () => void;
  onToggle: (id: string) => void;
  onSelectAll: () => void;
  onImport: () => void;
}

const ExternalImportModal: React.FC<ExternalImportModalProps> = ({
  machines,
  regions,
  filters,
  loading,
  selectedMachines,
  importResult,
  importing,
  onClose,
  onFiltersChange,
  onRefresh,
  onToggle,
  onSelectAll,
  onImport,
}) => {
  const getStatusLabel = (status: string) => {
    const map: Record<string, string> = {
      available: '可用',
      in_use: '使用中',
      maintenance: '维护中',
      retired: '已退役',
    };
    return map[status] || status;
  };

  const getStatusStyle = (status: string) => {
    const styleMap: Record<string, { bg: string; color: string }> = {
      available: { bg: 'var(--status-success-bg)', color: 'var(--status-success)' },
      in_use: { bg: 'var(--status-info-bg)', color: 'var(--status-info)' },
      maintenance: { bg: 'var(--status-warning-bg)', color: 'var(--status-warning)' },
      retired: { bg: 'var(--surface-tertiary)', color: 'var(--text-tertiary)' },
    };
    return styleMap[status] || { bg: 'var(--surface-tertiary)', color: 'var(--text-secondary)' };
  };

  return (
    <div style={styles.modalOverlay} onClick={onClose}>
      <div style={externalModalStyles.container} onClick={e => e.stopPropagation()}>
        <div style={styles.modalHeader}>
          <h2 style={styles.modalTitle}>从外部系统导入</h2>
          <button style={styles.modalClose} onClick={onClose}>×</button>
        </div>

        {importResult ? (
          <div style={externalModalStyles.resultContainer}>
            <div style={importResult.success ? externalModalStyles.successBanner : externalModalStyles.errorBanner}>
              <span style={externalModalStyles.resultIcon}>{importResult.success ? '✓' : '⚠'}</span>
              <div>
                <div style={externalModalStyles.resultTitle}>{importResult.message}</div>
                <div style={externalModalStyles.resultStats}>
                  <span>成功: {importResult.created_count}</span>
                  <span>跳过: {importResult.skipped_count}</span>
                  {importResult.error_count > 0 && <span style={{ color: 'var(--status-error)' }}>失败: {importResult.error_count}</span>}
                </div>
              </div>
            </div>

            <div style={externalModalStyles.resultsList}>
              <h4 style={externalModalStyles.resultsTitle}>导入结果详情</h4>
              {importResult.results.map((result, idx) => (
                <div key={idx} style={{
                  ...externalModalStyles.resultItem,
                  borderLeftColor: result.status === 'created' ? 'var(--status-success)' :
                                  result.status === 'skipped' ? 'var(--status-warning)' : 'var(--status-error)',
                }}>
                  <span style={externalModalStyles.resultName}>{result.name}</span>
                  <span style={{
                    ...externalModalStyles.resultStatus,
                    color: result.status === 'created' ? 'var(--status-success)' :
                           result.status === 'skipped' ? 'var(--status-warning)' : 'var(--status-error)',
                  }}>
                    {result.status === 'created' ? `已创建 (${result.dut_id})` :
                     result.status === 'skipped' ? '已跳过' : `失败: ${result.reason}`}
                  </span>
                </div>
              ))}
            </div>

            <div style={styles.modalFooter}>
              <button style={styles.submitBtn} onClick={onClose}>关闭</button>
            </div>
          </div>
        ) : (
          <>
            <div style={externalModalStyles.filterBar}>
              <input
                style={styles.filterInput}
                placeholder="搜索名称/型号/区域..."
                value={filters.search}
                onChange={e => onFiltersChange({ ...filters, search: e.target.value })}
              />
              <select
                style={styles.filterSelect}
                value={filters.region}
                onChange={e => onFiltersChange({ ...filters, region: e.target.value })}
              >
                <option value="">全部区域</option>
                {regions.map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
              <select
                style={styles.filterSelect}
                value={filters.status}
                onChange={e => onFiltersChange({ ...filters, status: e.target.value })}
              >
                <option value="">全部状态</option>
                <option value="available">可用</option>
                <option value="in_use">使用中</option>
                <option value="maintenance">维护中</option>
                <option value="retired">已退役</option>
              </select>
              <button style={styles.actionBtn} onClick={onRefresh} disabled={loading}>
                刷新
              </button>
            </div>

            <div style={externalModalStyles.tableWrapper}>
              {loading ? (
                <div style={styles.loadingState}>
                  <div style={styles.spinner} />
                  <span>加载中...</span>
                </div>
              ) : machines.length === 0 ? (
                <div style={styles.emptyState}>
                  <span style={styles.emptyIcon}>📭</span>
                  <p>未找到匹配的机器</p>
                </div>
              ) : (
                <table style={styles.table}>
                  <thead>
                    <tr style={styles.tableHeader}>
                      <th style={{ ...styles.th, width: '40px' }}>
                        <input
                          type="checkbox"
                          checked={selectedMachines.size === machines.length && machines.length > 0}
                          onChange={onSelectAll}
                        />
                      </th>
                      <th style={styles.th}>机器名称</th>
                      <th style={styles.th}>型号</th>
                      <th style={styles.th}>BMC IP</th>
                      <th style={styles.th}>OS IP</th>
                      <th style={styles.th}>区域</th>
                      <th style={styles.th}>OS</th>
                      <th style={styles.th}>状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    {machines.map((machine) => {
                      const statusStyle = getStatusStyle(machine.status);
                      return (
                        <tr key={machine.external_id} style={styles.tr}>
                          <td style={styles.td}>
                            <input
                              type="checkbox"
                              checked={selectedMachines.has(machine.external_id)}
                              onChange={() => onToggle(machine.external_id)}
                            />
                          </td>
                          <td style={styles.td}>
                            <div style={externalModalStyles.machineName}>{machine.name}</div>
                            <div style={externalModalStyles.machineId}>{machine.external_id}</div>
                          </td>
                          <td style={styles.td}>{machine.model || '-'}</td>
                          <td style={styles.td}>
                            <span style={styles.ip}>{machine.bmc_ip}</span>
                          </td>
                          <td style={styles.td}>
                            <span style={styles.ip}>{machine.os_ip}</span>
                          </td>
                          <td style={styles.td}>{machine.region}</td>
                          <td style={styles.td}>{machine.os_type}</td>
                          <td style={styles.td}>
                            <span style={{ ...styles.statusBadge, backgroundColor: statusStyle.bg, color: statusStyle.color }}>
                              {getStatusLabel(machine.status)}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>

            <div style={styles.modalFooter}>
              <div style={externalModalStyles.selectedInfo}>
                已选择 {selectedMachines.size} / {machines.length} 台机器
              </div>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button style={styles.cancelBtn} onClick={onClose}>取消</button>
                <button
                  style={styles.submitBtn}
                  onClick={onImport}
                  disabled={selectedMachines.size === 0 || importing}
                >
                  {importing ? '导入中...' : `导入 ${selectedMachines.size} 台机器`}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const externalModalStyles = {
  container: {
    width: '1000px',
    maxWidth: '95vw',
    maxHeight: '85vh',
    display: 'flex',
    flexDirection: 'column' as const,
    backgroundColor: 'var(--bg-primary)',
    borderRadius: 'var(--radius-xl)',
    boxShadow: 'var(--shadow-lg)',
    animation: 'scaleIn 0.2s ease',
  },
  filterBar: {
    display: 'flex',
    gap: '12px',
    padding: '16px 20px',
    borderBottom: '1px solid var(--border-subtle)',
  },
  tableWrapper: {
    flex: 1,
    overflowY: 'auto' as const,
    backgroundColor: 'var(--bg-secondary)',
    margin: '0 20px',
    borderRadius: 'var(--radius-md)',
  },
  machineName: {
    fontWeight: 500,
    color: 'var(--text-primary)',
  },
  machineId: {
    fontSize: '11px',
    color: 'var(--text-tertiary)',
    fontFamily: "'JetBrains Mono', monospace",
  },
  selectedInfo: {
    fontSize: '14px',
    color: 'var(--text-secondary)',
  },
  resultContainer: {
    flex: 1,
    padding: '20px',
    overflowY: 'auto' as const,
  },
  successBanner: {
    display: 'flex',
    gap: '16px',
    padding: '16px 20px',
    backgroundColor: 'var(--status-success-bg)',
    border: '1px solid var(--status-success)',
    borderRadius: 'var(--radius-md)',
    marginBottom: '20px',
  },
  errorBanner: {
    display: 'flex',
    gap: '16px',
    padding: '16px 20px',
    backgroundColor: 'var(--status-error-bg)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    marginBottom: '20px',
  },
  resultIcon: {
    fontSize: '24px',
    lineHeight: '24px',
  },
  resultTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: '8px',
  },
  resultStats: {
    display: 'flex',
    gap: '20px',
    fontSize: '14px',
    color: 'var(--text-secondary)',
  },
  resultsList: {
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-md)',
    padding: '16px',
    maxHeight: '400px',
    overflowY: 'auto' as const,
  },
  resultsTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    margin: '0 0 12px 0',
  },
  resultItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 12px',
    borderLeft: '3px solid',
    backgroundColor: 'var(--bg-primary)',
    borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
    marginBottom: '8px',
  },
  resultName: {
    fontSize: '13px',
    color: 'var(--text-primary)',
  },
  resultStatus: {
    fontSize: '12px',
  },
};

const styles = {
  container: {
    padding: '32px',
    maxWidth: '1600px',
    margin: '0 auto',
    animation: 'fadeIn 0.4s ease',
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
    margin: 0,
  } as const,
  badge: {
    padding: '0 10px',
    fontSize: '13px',
    fontWeight: 600,
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
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  } as const,
  actionBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 16px',
    fontSize: '13px',
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  } as const,
  createBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 16px',
    fontSize: '13px',
    fontWeight: 500,
    color: '#fff',
    backgroundColor: 'var(--accent-purple)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  } as const,
  filterBar: {
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    padding: '20px',
    marginBottom: '20px',
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
  } as const,
  filterInput: {
    padding: '8px 12px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
  } as const,
  filterSelect: {
    padding: '8px 12px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  } as const,
  filterActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
  } as const,
  resetBtn: {
    padding: '8px 16px',
    fontSize: '13px',
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
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
  } as const,
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '14px 18px',
    backgroundColor: 'var(--status-error-bg)',
    border: '1px solid var(--status-error)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--status-error)',
    fontSize: '14px',
    marginBottom: '20px',
  } as const,
  errorClose: {
    marginLeft: 'auto',
    padding: '0 4px',
    fontSize: '16px',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
  } as const,
  tableWrapper: {
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border-default)',
    overflow: 'hidden',
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
    borderBottom: '1px solid var(--border-default)',
  } as const,
  tr: {
    borderBottom: '1px solid var(--border-muted)',
  } as const,
  td: {
    padding: '12px 16px',
    fontSize: '13px',
    color: 'var(--text-primary)',
  } as const,
  dutId: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
    color: 'var(--accent-purple)',
  } as const,
  ip: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '12px',
    color: 'var(--text-secondary)',
  } as const,
  statusBadge: {
    display: 'inline-flex',
    padding: '3px 8px',
    fontSize: '10px',
    fontWeight: 600,
    borderRadius: '10px',
    textTransform: 'uppercase' as const,
  } as const,
  actionBtns: {
    display: 'flex',
    gap: '8px',
  } as const,
  viewBtn: {
    padding: '4px 10px',
    fontSize: '12px',
    color: 'var(--accent-primary)',
    backgroundColor: 'var(--status-info-bg)',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
  } as const,
  editBtn: {
    padding: '4px 10px',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-tertiary)',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
  } as const,
  deleteBtn: {
    padding: '4px 10px',
    fontSize: '12px',
    color: 'var(--status-error)',
    backgroundColor: 'var(--status-error-bg)',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    cursor: 'pointer',
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
    gap: '8px',
    padding: '60px',
    color: 'var(--text-muted)',
  } as const,
  emptyIcon: {
    fontSize: '48px',
    opacity: 0.3,
  } as const,
  modalOverlay: {
    position: 'fixed' as const,
    inset: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  } as const,
  modal: {
    width: '600px',
    maxWidth: '90vw',
    maxHeight: '85vh',
    display: 'flex',
    flexDirection: 'column' as const,
    backgroundColor: 'var(--bg-primary)',
    borderRadius: 'var(--radius-xl)',
    boxShadow: 'var(--shadow-lg)',
    animation: 'scaleIn 0.2s ease',
  } as const,
  modalHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 20px',
    borderBottom: '1px solid var(--border-subtle)',
  } as const,
  modalTitle: {
    fontSize: '18px',
    fontWeight: 600,
    margin: 0,
  } as const,
  modalClose: {
    fontSize: '24px',
    color: 'var(--text-tertiary)',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
  } as const,
  modalBody: {
    flex: 1,
    padding: '20px',
    overflowY: 'auto' as const,
  } as const,
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    padding: '16px 20px',
    borderTop: '1px solid var(--border-subtle)',
  } as const,
  cancelBtn: {
    padding: '10px 20px',
    fontSize: '14px',
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  } as const,
  submitBtn: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 500,
    color: '#fff',
    backgroundColor: 'var(--accent-purple)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
  } as const,
  detailGrid: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '20px',
  } as const,
  detailSection: {
    padding: '16px',
    backgroundColor: 'var(--bg-secondary)',
    borderRadius: 'var(--radius-md)',
  } as const,
  detailSectionTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    margin: '0 0 12px 0',
  } as const,
  detailRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '8px 0',
    borderBottom: '1px solid var(--border-subtle)',
  } as const,
  detailLabel: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
  } as const,
  detailValue: {
    fontSize: '13px',
    color: 'var(--text-primary)',
    fontWeight: 500,
  } as const,
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
    gap: '16px',
  } as const,
  formGroup: {
    display: 'flex',
    flexDirection: 'column' as const,
  } as const,
  formInput: {
    padding: '10px 12px',
    fontSize: '14px',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-primary)',
    border: '1px solid var(--border-default)',
    borderRadius: 'var(--radius-md)',
    outline: 'none',
  } as const,
};

export default DutManagement;