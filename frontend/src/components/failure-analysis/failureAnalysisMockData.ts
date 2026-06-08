/** 失效分析 Mock 数据 — 丰富且接近真实场景 */
import type { FailureAnalysisDashboard, FailurePattern } from '../../types'

/** 所有失效模式列表 */
const ALL_PATTERNS: FailurePattern[] = [
  'TIMEOUT', 'ASSERTION_ERROR', 'ENV_SETUP', 'DEPENDENCY',
  'CONFIG_ERROR', 'NETWORK_ERROR', 'HARDWARE_ERROR',
  'MEMORY_ERROR', 'SCRIPT_ERROR', 'UNKNOWN',
]

/** 虚拟执行代理，按 Lab 分组 */
const AGENTS: Record<string, Array<{ agent_id: string; hostname: string }>> = {
  'all': [
    { agent_id: 'ag-001', hostname: 'lab01-agent-01' },
    { agent_id: 'ag-002', hostname: 'lab01-agent-02' },
    { agent_id: 'ag-003', hostname: 'lab02-agent-01' },
    { agent_id: 'ag-004', hostname: 'lab02-agent-02' },
    { agent_id: 'ag-005', hostname: 'lab03-agent-01' },
    { agent_id: 'ag-006', hostname: 'lab03-agent-02' },
  ],
  'lab-ddr5': [
    { agent_id: 'ag-001', hostname: 'ddr5-agent-01' },
    { agent_id: 'ag-002', hostname: 'ddr5-agent-02' },
  ],
  'lab-pcie': [
    { agent_id: 'ag-003', hostname: 'pcie-agent-01' },
    { agent_id: 'ag-004', hostname: 'pcie-agent-02' },
    { agent_id: 'ag-007', hostname: 'pcie-agent-03' },
  ],
  'lab-bmc': [
    { agent_id: 'ag-005', hostname: 'bmc-agent-01' },
    { agent_id: 'ag-006', hostname: 'bmc-agent-02' },
  ],
}

/** 测试用例池，按 Lab 分组 */
const TEST_CASES_BY_LAB: Record<string, Array<{ auto_case_id: string; case_id: string; name: string }>> = {
  'all': [
    { auto_case_id: 'AC-042', case_id: 'TC-128', name: 'DDR5 带宽压力测试' },
    { auto_case_id: 'AC-128', case_id: 'TC-302', name: 'PCIe Gen5 链路稳定性' },
    { auto_case_id: 'AC-067', case_id: 'TC-045', name: '热切换测试 — 内存热插拔' },
    { auto_case_id: 'AC-215', case_id: 'TC-189', name: 'BMC 传感器轮询压测' },
    { auto_case_id: 'AC-034', case_id: 'TC-512', name: 'NVMe 顺序读写性能' },
    { auto_case_id: 'AC-089', case_id: 'TC-178', name: 'DDR5 ECC 纠错测试' },
    { auto_case_id: 'AC-156', case_id: 'TC-267', name: 'CPU C-State 切换测试' },
    { auto_case_id: 'AC-078', case_id: 'TC-134', name: '多 NUMA 节点内存分配' },
    { auto_case_id: 'AC-201', case_id: 'TC-423', name: 'RAID 卡重建压力' },
    { auto_case_id: 'AC-112', case_id: 'TC-056', name: '固件升级回滚测试' },
    { auto_case_id: 'AC-301', case_id: 'TC-602', name: '智能网卡 P4 卸载验证' },
    { auto_case_id: 'AC-099', case_id: 'TC-389', name: 'NVMe-oF TCP 连接稳定性' },
    { auto_case_id: 'AC-177', case_id: 'TC-710', name: 'TPM 2.0 安全启动测试' },
    { auto_case_id: 'AC-233', case_id: 'TC-891', name: 'HBM2e 带宽与延迟测试' },
    { auto_case_id: 'AC-145', case_id: 'TC-445', name: 'GPU 直通 (SR-IOV) 功能验证' },
  ],
  'lab-ddr5': [
    { auto_case_id: 'AC-042', case_id: 'TC-128', name: 'DDR5 带宽压力测试' },
    { auto_case_id: 'AC-089', case_id: 'TC-178', name: 'DDR5 ECC 纠错测试' },
    { auto_case_id: 'AC-067', case_id: 'TC-045', name: '热切换测试 — 内存热插拔' },
    { auto_case_id: 'AC-078', case_id: 'TC-134', name: '多 NUMA 节点内存分配' },
  ],
  'lab-pcie': [
    { auto_case_id: 'AC-128', case_id: 'TC-302', name: 'PCIe Gen5 链路稳定性' },
    { auto_case_id: 'AC-034', case_id: 'TC-512', name: 'NVMe 顺序读写性能' },
    { auto_case_id: 'AC-201', case_id: 'TC-423', name: 'RAID 卡重建压力' },
    { auto_case_id: 'AC-301', case_id: 'TC-602', name: '智能网卡 P4 卸载验证' },
    { auto_case_id: 'AC-233', case_id: 'TC-891', name: 'HBM2e 带宽与延迟测试' },
  ],
  'lab-bmc': [
    { auto_case_id: 'AC-215', case_id: 'TC-189', name: 'BMC 传感器轮询压测' },
    { auto_case_id: 'AC-156', case_id: 'TC-267', name: 'CPU C-State 切换测试' },
    { auto_case_id: 'AC-112', case_id: 'TC-056', name: '固件升级回滚测试' },
    { auto_case_id: 'AC-177', case_id: 'TC-710', name: 'TPM 2.0 安全启动测试' },
    { auto_case_id: 'AC-099', case_id: 'TC-389', name: 'NVMe-oF TCP 连接稳定性' },
    { auto_case_id: 'AC-145', case_id: 'TC-445', name: 'GPU 直通 (SR-IOV) 功能验证' },
  ],
}

/** 随机选择 n 个不重复元素 */
function sample<T>(arr: T[], n: number): T[] {
  const shuffled = [...arr].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, n)
}

/** 随机整数 [min, max] */
function randInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

/** 生成每日趋势 — 周末/工作日模式 */
function genDailyTrend(days: number, step: number) {
  const trend: Array<{
    date: string
    failure_count: number
    patterns: Record<FailurePattern, number>
  }> = []
  const now = new Date()
  for (let i = days; i >= 0; i -= step) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    const dateStr = d.toISOString().slice(0, 10)
    const dayOfWeek = d.getDay()
    // 周末失败率偏高（可能缺乏维护），周五偏低
    const base = dayOfWeek === 0 || dayOfWeek === 6 ? randInt(4, 14) : dayOfWeek === 5 ? randInt(1, 6) : randInt(2, 10)

    const patterns = {
      TIMEOUT: randInt(0, Math.max(1, Math.round(base * 0.35))),
      ASSERTION_ERROR: randInt(0, Math.max(1, Math.round(base * 0.3))),
      ENV_SETUP: randInt(0, Math.max(1, Math.round(base * 0.2))),
      DEPENDENCY: randInt(0, Math.max(1, Math.round(base * 0.15))),
      CONFIG_ERROR: randInt(0, Math.max(1, Math.round(base * 0.15))),
      NETWORK_ERROR: randInt(0, Math.max(1, Math.round(base * 0.1))),
      HARDWARE_ERROR: randInt(0, Math.max(1, Math.round(base * 0.25))),
      MEMORY_ERROR: randInt(0, Math.max(1, Math.round(base * 0.1))),
      SCRIPT_ERROR: randInt(0, Math.max(1, Math.round(base * 0.15))),
      UNKNOWN: randInt(0, Math.max(1, Math.round(base * 0.1))),
    } as Record<FailurePattern, number>

    const actualCount = Object.values(patterns).reduce((a, b) => a + b, 0)

    trend.push({ date: dateStr, failure_count: actualCount, patterns })
  }
  return trend
}

/** 各 Lab 的失败模式权重（不同 Lab 有不同的失败特征） */
const LAB_PATTERN_WEIGHTS: Record<string, Record<FailurePattern, number>> = {
  'all': {
    TIMEOUT: 25, ASSERTION_ERROR: 41, ENV_SETUP: 7,
    DEPENDENCY: 2, CONFIG_ERROR: 3, NETWORK_ERROR: 2,
    HARDWARE_ERROR: 14, MEMORY_ERROR: 1, SCRIPT_ERROR: 4, UNKNOWN: 1,
  },
  'lab-ddr5': {
    TIMEOUT: 30, ASSERTION_ERROR: 25, ENV_SETUP: 5,
    DEPENDENCY: 1, CONFIG_ERROR: 2, NETWORK_ERROR: 1,
    HARDWARE_ERROR: 28, MEMORY_ERROR: 3, SCRIPT_ERROR: 3, UNKNOWN: 2,
  },
  'lab-pcie': {
    TIMEOUT: 18, ASSERTION_ERROR: 52, ENV_SETUP: 3,
    DEPENDENCY: 4, CONFIG_ERROR: 5, NETWORK_ERROR: 2,
    HARDWARE_ERROR: 8, MEMORY_ERROR: 0, SCRIPT_ERROR: 6, UNKNOWN: 2,
  },
  'lab-bmc': {
    TIMEOUT: 35, ASSERTION_ERROR: 18, ENV_SETUP: 15,
    DEPENDENCY: 2, CONFIG_ERROR: 4, NETWORK_ERROR: 8,
    HARDWARE_ERROR: 6, MEMORY_ERROR: 1, SCRIPT_ERROR: 8, UNKNOWN: 3,
  },
}

/** 按时间范围计算缩放因子 */
function timeScale(timeRange: string): number {
  if (timeRange === '7d') return 0.3
  if (timeRange === '90d') return 2.5
  return 1.0
}

/** Lab 基础失败基数（不同 Lab 规模不同） */
const LAB_BASE_FAILURES: Record<string, number> = {
  'all': 167,
  'lab-ddr5': 89,
  'lab-pcie': 142,
  'lab-bmc': 56,
}

export function getFailureAnalysisMockData(timeRange: string, labId = 'all'): FailureAnalysisDashboard {
  const days = timeRange === '7d' ? 7 : timeRange === '90d' ? 90 : 30
  const step = days <= 7 ? 1 : days <= 30 ? 1 : 3
  const scale = timeScale(timeRange)

  const dailyTrend = genDailyTrend(days, step)
  const totalFailures = Math.round((LAB_BASE_FAILURES[labId] || 100) * scale)

  // ── Pattern Distribution ──
  const patternWeights = LAB_PATTERN_WEIGHTS[labId] || LAB_PATTERN_WEIGHTS['all']
  const totalWeight = Object.values(patternWeights).reduce((a, b) => a + b, 0)
  const patternDistribution = ALL_PATTERNS.map(p => ({
    pattern: p as FailurePattern,
    count: Math.max(1, Math.round((patternWeights[p] / totalWeight) * totalFailures)),
    percentage: +(patternWeights[p] / totalWeight * 100).toFixed(1),
  }))

  // ── By Agent ──
  const agentsList = AGENTS[labId] || AGENTS['all']
  const selectedAgents = agentsList.slice(0, Math.min(agentsList.length, timeRange === '7d' ? Math.max(agentsList.length - 1, 1) : agentsList.length))
  const agentRatios = selectedAgents.map((_, i) => 1 / (i + 2)).reverse()
  const agentRatioSum = agentRatios.reduce((a, b) => a + b, 0)
  const byAgent = selectedAgents.map((agent, idx) => {
    const agentFailures = Math.round(totalFailures * (agentRatios[idx] / agentRatioSum))
    const breakdown = {} as Record<FailurePattern, number>
    ALL_PATTERNS.forEach(p => {
      breakdown[p] = Math.round(agentFailures * (patternWeights[p] / totalWeight))
    })
    return { ...agent, failure_count: agentFailures, pattern_breakdown: breakdown }
  })

  // ── Test Cases from selected lab ──
  const labCases = TEST_CASES_BY_LAB[labId] || TEST_CASES_BY_LAB['all']

  // ── Flaky Tests ──
  const flakyCount = timeRange === '7d' ? Math.max(2, Math.min(labCases.length - 1, 3)) : timeRange === '90d' ? Math.min(labCases.length, 8) : Math.min(labCases.length, 5)
  const flakyCases = sample(labCases, flakyCount)
  const flakyTests = flakyCases.map(tc => {
    const runs = randInt(10, 35)
    const ratio = +(Math.random() * 0.35 + 0.12).toFixed(2)
    const results: Array<Record<string, unknown>> = []
    for (let i = 0; i < 10; i++) {
      results.push({ status: Math.random() < ratio ? 'FAILED' : 'PASSED' })
    }
    return { ...tc, total_runs: runs, flaky_ratio: ratio, recent_results: results }
  })

  // ── High Frequency Failures ──
  const hfCount = timeRange === '7d' ? Math.max(1, Math.min(labCases.length - 1, 3)) : timeRange === '90d' ? Math.min(labCases.length, 8) : Math.min(labCases.length, 5)
  const hfCases = sample(labCases, hfCount)
  const highFreqFailures = hfCases.map((tc, idx) => ({
    ...tc,
    failure_count: randInt(4, 15),
    dominant_pattern: ['ASSERTION_ERROR', 'TIMEOUT', 'HARDWARE_ERROR', 'TIMEOUT', 'HARDWARE_ERROR', 'ASSERTION_ERROR'][idx % 6] as FailurePattern,
    latest_failure_at: new Date(Date.now() - randInt(1, 72) * 3600000).toISOString(),
    avg_duration_sec: randInt(120, 2000),
  }))

  return {
    time_range: timeRange,
    total_failures: totalFailures,
    pattern_distribution: patternDistribution,
    by_agent: byAgent,
    daily_trend: dailyTrend,
    flaky_tests: flakyTests,
    high_frequency_failures: highFreqFailures,
  }
}
