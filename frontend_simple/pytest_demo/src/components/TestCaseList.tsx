import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { TestCaseResponse } from '../types';
import CreateTestCaseForm from './CreateTestCaseForm';
import CreateAutomationTestCaseForm from './CreateAutomationTestCaseForm';

interface TestCaseListProps {
  onLogout: () => void;
}

const TestCaseList: React.FC<TestCaseListProps> = ({ onLogout }) => {
  const [testCases, setTestCases] = useState<TestCaseResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    ref_req_id: '',
    status: '',
    owner_id: '',
    priority: '',
    is_active: '',
  });
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showCreateAutomationForm, setShowCreateAutomationForm] = useState(false);
  const [selectedCaseIds, setSelectedCaseIds] = useState<Set<string>>(new Set());

  const fetchTestCases = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.listTestCases({
        ref_req_id: filters.ref_req_id || undefined,
        status: filters.status || undefined,
        owner_id: filters.owner_id || undefined,
        priority: filters.priority || undefined,
        is_active: filters.is_active === 'true' ? true : filters.is_active === 'false' ? false : undefined,
        limit: 50,
        offset: 0,
      });
      setTestCases(response.data || []);
    } catch (err) {
      setError('获取测试用例列表失败');
      console.error('Fetch test cases error:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchTestCases();
  }, [fetchTestCases]);

  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSearch = () => {
    fetchTestCases();
  };

  const handleReset = () => {
    setFilters({
      ref_req_id: '',
      status: '',
      owner_id: '',
      priority: '',
      is_active: '',
    });
    fetchTestCases();
  };

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    const checked = e.target.checked;
    if (checked) {
      const allIds = new Set(testCases.map(tc => tc.id));
      setSelectedCaseIds(allIds);
    } else {
      setSelectedCaseIds(new Set());
    }
  };

  const handleSelectCase = (caseId: string) => {
    setSelectedCaseIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(caseId)) {
        newSet.delete(caseId);
      } else {
        newSet.add(caseId);
      }
      return newSet;
    });
  };

  const isAllSelected = testCases.length > 0 && selectedCaseIds.size === testCases.length;

  const handleExecute = async () => {
    if (selectedCaseIds.size === 0) {
      alert('请先选择要执行的测试用例');
      return;
    }

    try {
      const selectedTestCases = testCases.filter(tc => selectedCaseIds.has(tc.id));
      const cases = selectedTestCases.map(tc => ({ case_id: tc.case_id }));
      
      const response = await api.dispatchTask({
        framework: 'pytest',
        trigger_source: 'manual',
        cases: cases,
      });

      console.log('下发测试任务成功:', response);
      alert(`已下发 ${selectedCaseIds.size} 个测试用例，任务ID: ${response.data.task_id}`);
    } catch (err) {
      alert('下发测试用例失败');
      console.error('Dispatch test cases error:', err);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>测试用例列表</h1>
        <div style={styles.headerButtons}>
          <button
            style={styles.createButton}
            onClick={() => setShowCreateForm(true)}
          >
            创建手动测试用例
          </button>
          <button
            style={styles.createAutomationButton}
            onClick={() => setShowCreateAutomationForm(true)}
          >
            创建自动化测试用例
          </button>
          <button
            style={styles.executeButton}
            onClick={handleExecute}
            disabled={selectedCaseIds.size === 0}
          >
            一键执行 ({selectedCaseIds.size})
          </button>
          <button
            style={styles.logoutButton}
            onClick={onLogout}
          >
            退出登录
          </button>
        </div>
      </div>

      {error && (
        <div style={styles.errorMessage}>
          {error}
        </div>
      )}

      <div style={styles.filterSection}>
        <div style={styles.filterRow}>
          <div style={styles.filterGroup}>
            <label style={styles.label}>需求编号</label>
            <input
              type="text"
              name="ref_req_id"
              value={filters.ref_req_id}
              onChange={handleFilterChange}
              style={styles.input}
              placeholder="REQ-001"
            />
          </div>

          <div style={styles.filterGroup}>
            <label style={styles.label}>状态</label>
            <select
              name="status"
              value={filters.status}
              onChange={handleFilterChange}
              style={styles.input}
            >
              <option value="">全部</option>
              <option value="DRAFT">草稿</option>
              <option value="PENDING">待审核</option>
              <option value="APPROVED">已批准</option>
              <option value="REJECTED">已拒绝</option>
            </select>
          </div>

          <div style={styles.filterGroup}>
            <label style={styles.label}>负责人</label>
            <input
              type="text"
              name="owner_id"
              value={filters.owner_id}
              onChange={handleFilterChange}
              style={styles.input}
              placeholder="用户ID"
            />
          </div>

          <div style={styles.filterGroup}>
            <label style={styles.label}>优先级</label>
            <select
              name="priority"
              value={filters.priority}
              onChange={handleFilterChange}
              style={styles.input}
            >
              <option value="">全部</option>
              <option value="P0">P0</option>
              <option value="P1">P1</option>
              <option value="P2">P2</option>
              <option value="P3">P3</option>
            </select>
          </div>

          <div style={styles.filterGroup}>
            <label style={styles.label}>激活状态</label>
            <select
              name="is_active"
              value={filters.is_active}
              onChange={handleFilterChange}
              style={styles.input}
            >
              <option value="">全部</option>
              <option value="true">激活</option>
              <option value="false">未激活</option>
            </select>
          </div>
        </div>

        <div style={styles.buttonGroup}>
          <button style={styles.searchButton} onClick={handleSearch}>
            查询
          </button>
          <button style={styles.resetButton} onClick={handleReset}>
            重置
          </button>
        </div>
      </div>

      {loading ? (
        <div style={styles.loading}>加载中...</div>
      ) : (
        <div style={styles.tableContainer}>
          <table style={styles.table}>
            <thead>
              <tr style={styles.tableHeader}>
                <th style={styles.tableCell}>
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    onChange={handleSelectAll}
                    style={styles.checkbox}
                  />
                </th>
                <th style={styles.tableCell}>用例编号</th>
                <th style={styles.tableCell}>用例名称</th>
                <th style={styles.tableCell}>需求编号</th>
                <th style={styles.tableCell}>状态</th>
                <th style={styles.tableCell}>优先级</th>
                <th style={styles.tableCell}>负责人</th>
                <th style={styles.tableCell}>激活状态</th>
                <th style={styles.tableCell}>创建时间</th>
              </tr>
            </thead>
            <tbody>
              {testCases.length === 0 ? (
                <tr>
                  <td colSpan={9} style={styles.emptyCell}>
                    暂无数据
                  </td>
                </tr>
              ) : (
                testCases.map((testCase) => (
                  <tr key={testCase.id} style={styles.tableRow}>
                    <td style={styles.tableCell}>
                      <input
                        type="checkbox"
                        checked={selectedCaseIds.has(testCase.id)}
                        onChange={() => handleSelectCase(testCase.id)}
                        style={styles.checkbox}
                      />
                    </td>
                    <td style={styles.tableCell}>{testCase.case_id}</td>
                    <td style={styles.tableCell}>{testCase.title}</td>
                    <td style={styles.tableCell}>{testCase.ref_req_id}</td>
                    <td style={styles.tableCell}>{testCase.status}</td>
                    <td style={styles.tableCell}>{testCase.priority || '-'}</td>
                    <td style={styles.tableCell}>{testCase.owner_id || '-'}</td>
                    <td style={styles.tableCell}>
                      {testCase.is_active ? '是' : '否'}
                    </td>
                    <td style={styles.tableCell}>
                      {new Date(testCase.created_at).toLocaleString('zh-CN')}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {showCreateForm && (
        <CreateTestCaseForm
          onClose={() => setShowCreateForm(false)}
          onSuccess={fetchTestCases}
        />
      )}

      {showCreateAutomationForm && (
        <CreateAutomationTestCaseForm
          onClose={() => setShowCreateAutomationForm(false)}
          onSuccess={fetchTestCases}
        />
      )}
    </div>
  );
};

const styles = {
  container: {
    padding: '20px',
    maxWidth: '1400px',
    margin: '0 auto',
  } as const,
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
  } as const,
  title: {
    fontSize: '28px',
    fontWeight: 'bold',
    color: '#333',
    margin: 0,
  } as const,
  createButton: {
    padding: '10px 20px',
    backgroundColor: '#007bff',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
  } as const,
  createAutomationButton: {
    padding: '10px 20px',
    backgroundColor: '#17a2b8',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
  } as const,
  executeButton: {
    padding: '10px 20px',
    backgroundColor: '#28a745',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
  } as const,
  headerButtons: {
    display: 'flex',
    gap: '10px',
  } as const,
  logoutButton: {
    padding: '10px 20px',
    backgroundColor: '#dc3545',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
  } as const,
  errorMessage: {
    padding: '12px',
    backgroundColor: '#fee',
    border: '1px solid #fcc',
    borderRadius: '4px',
    color: '#c33',
    fontSize: '14px',
    marginBottom: '20px',
  } as const,
  filterSection: {
    backgroundColor: '#f8f9fa',
    padding: '20px',
    borderRadius: '8px',
    marginBottom: '20px',
  } as const,
  filterRow: {
    display: 'flex',
    gap: '15px',
    flexWrap: 'wrap' as const,
    marginBottom: '15px',
  } as const,
  filterGroup: {
    flex: '1',
    minWidth: '150px',
  } as const,
  label: {
    display: 'block',
    fontSize: '12px',
    fontWeight: '500',
    color: '#555',
    marginBottom: '5px',
  } as const,
  input: {
    width: '100%',
    padding: '8px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '14px',
  } as const,
  checkbox: {
    width: '18px',
    height: '18px',
    cursor: 'pointer',
  } as const,
  buttonGroup: {
    display: 'flex',
    gap: '10px',
  } as const,
  searchButton: {
    padding: '8px 20px',
    backgroundColor: '#007bff',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
  } as const,
  resetButton: {
    padding: '8px 20px',
    backgroundColor: '#6c757d',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    fontSize: '14px',
    cursor: 'pointer',
  } as const,
  loading: {
    textAlign: 'center' as const,
    padding: '40px',
    fontSize: '16px',
    color: '#666',
  } as const,
  tableContainer: {
    overflowX: 'auto' as const,
    border: '1px solid #ddd',
    borderRadius: '8px',
  } as const,
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
  } as const,
  tableHeader: {
    backgroundColor: '#f8f9fa',
  } as const,
  tableRow: {
    borderBottom: '1px solid #ddd',
  } as const,
  tableCell: {
    padding: '12px',
    textAlign: 'left' as const,
    fontSize: '14px',
  } as const,
  emptyCell: {
    padding: '40px',
    textAlign: 'center' as const,
    color: '#999',
    fontSize: '14px',
  } as const,
};

export default TestCaseList;
