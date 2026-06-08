/** 血缘图谱 Mock 数据 */
import type { LineageGraphResponse, LineageNode, LineageEdge } from '../../types'

const now = new Date()
function ago(h: number) { return new Date(now.getTime() - h * 3600000).toISOString() }

export function getLineageMockData(entityType: string, entityId: string): LineageGraphResponse {
  if (entityType === 'task' && entityId === 'ET-2026-000042') {
    return getTaskLineage()
  }
  if (entityType === 'requirement') {
    return getRequirementLineage()
  }
  return getDefaultLineage()
}

function getTaskLineage(): LineageGraphResponse {
  const nodes: LineageNode[] = [
    {
      id: 'DML-042', type: 'requirement', label: 'DDR5 6400MHz 带宽验证',
      status: 'ACTIVE', subtitle: 'DML-042 · TPM: zhang.san',
      meta: { priority: 'P1', category: '性能验证', target_version: 'v2.3', created_at: '2026-05-10' },
    },
    {
      id: 'TC-128', type: 'test_case', label: 'DDR5 带宽压力测试',
      status: 'DONE', subtitle: 'TC-128 · 手工用例',
      meta: { priority: 'P0', lab: 'DDR5 Lab', owner_id: 'li.si', estimated_duration_sec: 1800 },
    },
    {
      id: 'AC-042', type: 'automation_case', label: 'ddr5_bandwidth_stress_test',
      status: 'ACTIVE', subtitle: 'AC-042 · pytest',
      meta: { framework: 'pytest', script_path: 'tests/ddr5/bandwidth/test_stress.py', repo_branch: 'main' },
    },
    {
      id: 'ET-2026-000042', type: 'task', label: 'DDR5 带宽压测任务',
      status: 'RUNNING', subtitle: 'ET-2026-000042 · 串行下发',
      meta: {
        schedule_type: 'immediate', case_count: 5, started_at: ago(4),
        progress_percent: 60, passed_case_count: 2, failed_case_count: 1,
      },
    },
    {
      id: 'CR-001', type: 'case_result', label: 'TC-128 第 3 次执行',
      status: 'FAILED', subtitle: 'case_id: TC-128',
      meta: {
        order_no: 3, started_at: ago(3), finished_at: ago(2),
        failure_message: 'AssertionError: expected bandwidth >= 64GB/s, got 52.3GB/s',
        dispatch_attempts: 1,
      },
    },
    {
      id: 'ag-003', type: 'agent', label: 'lab02-agent-01',
      status: 'ONLINE', subtitle: '192.168.1.103 · lab02',
      meta: { hostname: 'lab02-agent-01', region: 'lab02', last_heartbeat_at: ago(0.1) },
    },
    {
      id: 'CR-002', type: 'case_result', label: 'TC-128 第 4 次执行',
      status: 'RUNNING', subtitle: 'case_id: TC-128',
      meta: {
        order_no: 4, started_at: ago(1), finished_at: null,
        progress_percent: 45, event_count: 12,
      },
    },
  ]

  const edges: LineageEdge[] = [
    { source: 'DML-042', target: 'TC-128', label: 'contains' },
    { source: 'TC-128', target: 'AC-042', label: 'automated_by' },
    { source: 'AC-042', target: 'ET-2026-000042', label: 'executed_in' },
    { source: 'ET-2026-000042', target: 'CR-001', label: 'produced' },
    { source: 'ET-2026-000042', target: 'CR-002', label: 'produced' },
    { source: 'CR-001', target: 'ag-003', label: 'ran_on' },
    { source: 'CR-002', target: 'ag-003', label: 'ran_on' },
  ]

  return { nodes, edges, root_id: 'ET-2026-000042', root_type: 'task' }
}

function getRequirementLineage(): LineageGraphResponse {
  const nodes: LineageNode[] = [
    {
      id: 'DML-088', type: 'requirement', label: 'PCIe Gen5 链路稳定性验证',
      status: 'ACTIVE', subtitle: 'DML-088 · TPM: wang.wu',
      meta: { priority: 'P1', category: '兼容性', target_version: 'v2.3' },
    },
    {
      id: 'TC-302', type: 'test_case', label: 'PCIe Gen5 链路稳定性',
      status: 'PENDING_REVIEW', subtitle: 'TC-302 · 手工用例',
      meta: { priority: 'P0', lab: 'PCIe Lab', owner_id: 'li.si' },
    },
    {
      id: 'AC-128', type: 'automation_case', label: 'pcie_gen5_link_stability',
      status: 'ACTIVE', subtitle: 'AC-128 · pytest',
      meta: { framework: 'pytest', script_path: 'tests/pcie/gen5/test_link_stability.py' },
    },
    {
      id: 'ET-2026-000088', type: 'task', label: 'PCIe 链路压测任务',
      status: 'FAILED', subtitle: 'ET-2026-000088 · 串行下发',
      meta: {
        schedule_type: 'immediate', case_count: 3, finished_at: ago(12),
        passed_case_count: 1, failed_case_count: 2,
      },
    },
    {
      id: 'CR-088-1', type: 'case_result', label: 'AC-128 第 1 轮',
      status: 'FAILED', subtitle: 'case_id: AC-128',
      meta: {
        order_no: 1, finished_at: ago(14),
        failure_message: 'Link training failed: expected GEN5 (32GT/s), got GEN4 (16GT/s)',
      },
    },
    {
      id: 'CR-088-2', type: 'case_result', label: 'AC-128 第 2 轮',
      status: 'FAILED', subtitle: 'case_id: AC-128',
      meta: {
        order_no: 2, finished_at: ago(12),
        failure_message: 'AssertionError: BER exceeded threshold 1e-12, actual 3.2e-10',
      },
    },
    {
      id: 'ag-001', type: 'agent', label: 'lab01-agent-01',
      status: 'ONLINE', subtitle: '192.168.1.101 · lab01',
      meta: { hostname: 'lab01-agent-01', region: 'lab01', ip: '192.168.1.101' },
    },
    {
      id: 'TC-303', type: 'test_case', label: 'PCIe Gen5 功耗测试',
      status: 'DRAFT', subtitle: 'TC-303 · 手工用例',
      meta: { priority: 'P2', lab: 'PCIe Lab' },
    },
    {
      id: 'AC-129', type: 'automation_case', label: 'pcie_gen5_power_consumption',
      status: 'DRAFT', subtitle: 'AC-129 · pytest',
      meta: { framework: 'pytest', script_path: 'tests/pcie/gen5/test_power.py' },
    },
  ]

  const edges: LineageEdge[] = [
    { source: 'DML-088', target: 'TC-302', label: 'contains' },
    { source: 'DML-088', target: 'TC-303', label: 'contains' },
    { source: 'TC-302', target: 'AC-128', label: 'automated_by' },
    { source: 'TC-303', target: 'AC-129', label: 'automated_by' },
    { source: 'AC-128', target: 'ET-2026-000088', label: 'executed_in' },
    { source: 'ET-2026-000088', target: 'CR-088-1', label: 'produced' },
    { source: 'ET-2026-000088', target: 'CR-088-2', label: 'produced' },
    { source: 'CR-088-1', target: 'ag-001', label: 'ran_on' },
    { source: 'CR-088-2', target: 'ag-001', label: 'ran_on' },
  ]

  return { nodes, edges, root_id: 'DML-088', root_type: 'requirement' }
}

function getDefaultLineage(): LineageGraphResponse {
  return {
    nodes: [
      {
        id: 'DML-042', type: 'requirement', label: 'DDR5 6400MHz 带宽验证',
        status: 'ACTIVE', subtitle: 'DML-042',
        meta: { priority: 'P1' },
      },
      {
        id: 'TC-128', type: 'test_case', label: 'DDR5 带宽压力测试',
        status: 'DONE', subtitle: 'TC-128',
        meta: { lab: 'DDR5 Lab' },
      },
      {
        id: 'AC-042', type: 'automation_case', label: 'ddr5_bandwidth_stress',
        status: 'ACTIVE', subtitle: 'AC-042',
        meta: {},
      },
      {
        id: 'ET-2026-000001', type: 'task', label: '带宽压测任务',
        status: 'RUNNING', subtitle: 'ET-2026-000001',
        meta: {},
      },
      {
        id: 'CR-001', type: 'case_result', label: 'CR-001',
        status: 'FAILED', subtitle: '失败: 断言带宽不足',
        meta: {},
      },
      {
        id: 'ag-001', type: 'agent', label: 'lab01-agent-01',
        status: 'ONLINE', subtitle: '192.168.1.101',
        meta: {},
      },
    ],
    edges: [
      { source: 'DML-042', target: 'TC-128', label: 'contains' },
      { source: 'TC-128', target: 'AC-042', label: 'automated_by' },
      { source: 'AC-042', target: 'ET-2026-000001', label: 'executed_in' },
      { source: 'ET-2026-000001', target: 'CR-001', label: 'produced' },
      { source: 'CR-001', target: 'ag-001', label: 'ran_on' },
    ],
    root_id: 'ET-2026-000001',
    root_type: 'task',
  }
}
