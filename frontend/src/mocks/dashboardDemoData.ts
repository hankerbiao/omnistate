import type {
  AutomationTestCaseResponse,
  ExecutionAgent,
  ExecutionTask,
  RequirementResponse,
  TestCaseResponse,
} from '../types'

const now = Date.now()
const daysAgo = (d: number) => new Date(now - d * 86400000).toISOString()
const isoAt = (d: Date) => d.toISOString()

export interface DemoExecutiveMetrics {
  periodLabel: string
  reportDate: string
  healthScore: number
  healthGrade: string
  healthSummary: string
  kpis: Array<{
    label: string
    value: string
    delta: string
    deltaUp: boolean
    sub: string
    color: string
  }>
  highlights: Array<{ type: 'success' | 'info' | 'warning'; title: string; detail: string }>
  labCoverage: Array<{ name: string; cases: number; automated: number; passRate: number }>
  weeklyQuality: Array<{ week: string; passRate: number; coverage: number; defects: number }>
  teamPerformance: Array<{
    name: string
    role: string
    dept: string
    owned_cases: number
    owned_reqs: number
    reviewed_cases: number
    completionRate: number
  }>
  milestones: Array<{ name: string; progress: number; target: string; status: 'on_track' | 'at_risk' | 'done' }>
}

const REQ_TITLES = [
  'DDR5-6400 双通道稳定性验证',
  'BMC Redfish 传感器采集一致性',
  'PCIe Gen5 热插拔回归测试',
  'NVMe 4.0 长时间读写压力',
  'CXL 内存扩展兼容性',
  '电源冗余切换时序验证',
  '固件 OTA 断点续传可靠性',
  'IPMI SEL 日志完整性审计',
  '多节点集群故障注入',
  '散热策略极限工况评估',
  'RAS 错误注入与恢复',
  'Secure Boot 链完整性',
]

const CASE_CATEGORIES = ['功能', '性能', '稳定性', '兼容性', '安全', '可靠性']
const CASE_STATUSES = ['RELEASED', 'RELEASED', 'RELEASED', 'PENDING_REVIEW', 'DRAFT', 'IN_PROGRESS']
const REQ_STATUSES = ['RELEASED', 'RELEASED', 'PENDING_REVIEW', 'IN_PROGRESS', 'DRAFT']
const PRIORITIES = ['P0', 'P1', 'P1', 'P2', 'P2', 'P3']
const LABS = [
  { id: 'lab-ddr5', name: 'DDR5 内存 Lab' },
  { id: 'lab-bmc', name: 'BMC 固件 Lab' },
  { id: 'lab-pcie', name: 'PCIe/CXL Lab' },
  { id: 'lab-storage', name: '存储 IO Lab' },
  { id: 'lab-ras', name: 'RAS 可靠性 Lab' },
]

const TEAM = [
  { id: 'zhangwei', name: '张伟', role: '测试开发', dept: '内存验证组' },
  { id: 'lina', name: '李娜', role: 'TPM', dept: '平台质量组' },
  { id: 'wanghao', name: '王浩', role: '自动化', dept: '工具链组' },
  { id: 'chenyu', name: '陈雨', role: '测试开发', dept: '固件验证组' },
  { id: 'liuqing', name: '刘青', role: '审核', dept: '质量保障组' },
  { id: 'zhaomin', name: '赵敏', role: '测试开发', dept: '存储验证组' },
  { id: 'sunjie', name: '孙杰', role: 'TPM', dept: '平台质量组' },
  { id: 'huxin', name: '胡欣', role: '自动化', dept: '工具链组' },
]

function buildRequirements(): RequirementResponse[] {
  return REQ_TITLES.map((title, i) => {
    const owner = TEAM[i % TEAM.length]
    const tpm = TEAM[(i + 2) % TEAM.length]
    return {
      id: `req-doc-${i + 1}`,
      req_id: `REQ-2026-${String(i + 1).padStart(4, '0')}`,
      workflow_item_id: `wi-req-${i + 1}`,
      title,
      description: `${title} — 覆盖主流平台与边界场景`,
      category: ['FUNCTIONAL', 'PERFORMANCE', 'STABILITY', 'COMPATIBILITY'][i % 4],
      tags: ['DDR5', 'CPU', 'BMC'].slice(0, (i % 3) + 1),
      source: ['CUSTOMER', 'INTERNAL', 'SPEC'][i % 3],
      acceptance_criteria: `所有测试用例通过，覆盖率达 80% 以上`,
      baseline_version: `v2.${i % 5}.0`,
      target_version: `v2.${(i % 5) + 1}.0`,
      target_components: ['CPU', 'DIMM', 'BMC'],
      firmware_version: `v2.${i % 5}.${i % 3}`,
      priority: PRIORITIES[i % PRIORITIES.length],
      key_parameters: [{ name: 'platform', value: 'Genoa / Sapphire Rapids' }],
      tpm_owner_id: tpm.id,
      tpm_owner_name: tpm.name,
      manual_dev_id: owner.id,
      manual_dev_name: owner.name,
      case_count: Math.floor(Math.random() * 10),
      status: REQ_STATUSES[i % REQ_STATUSES.length],
      attachments: [],
      planned_start_date: daysAgo(30 - i).split('T')[0],
      planned_end_date: daysAgo(-30 + i).split('T')[0],
      created_at: daysAgo(90 - i * 5),
      updated_at: daysAgo(i * 2),
      creator: tpm.id,
      creator_name: tpm.name,
      current_owner: owner.id,
      current_owner_name: owner.name,
    }
  })
}

function buildTestCases(requirements: RequirementResponse[]): TestCaseResponse[] {
  const cases: TestCaseResponse[] = []
  let idx = 0
  requirements.forEach((req, ri) => {
    const count = 8 + (ri % 5) * 4
    const lab = LABS[ri % LABS.length]
    for (let j = 0; j < count; j += 1) {
      idx += 1
      const owner = TEAM[(ri + j) % TEAM.length]
      const reviewer = TEAM[(ri + j + 3) % TEAM.length]
      const automated = j % 3 !== 0
      cases.push({
        id: `case-doc-${idx}`,
        case_id: `TC-2026-${String(idx).padStart(5, '0')}`,
        ref_req_id: req.req_id,
        lab_id: lab.id,
        lab_name: lab.name,
        catalog_path: ['回归', CASE_CATEGORIES[j % CASE_CATEGORIES.length]],
        catalog_breadcrumb: `${lab.name} / 回归 / ${CASE_CATEGORIES[j % CASE_CATEGORIES.length]}`,
        title: `${req.title.slice(0, 12)}… — 场景 ${j + 1}`,
        version: 1 + (j % 3),
        is_active: j % 7 !== 0,
        status: CASE_STATUSES[j % CASE_STATUSES.length],
        workflow_item_id: `wi-case-${idx}`,
        owner_id: owner.id,
        reviewer_id: reviewer.id,
        priority: PRIORITIES[j % PRIORITIES.length],
        required_env: { platform: 'x86_64' },
        tags: [CASE_CATEGORIES[j % CASE_CATEGORIES.length]],
        test_category: CASE_CATEGORIES[j % CASE_CATEGORIES.length],
        is_destructive: j % 11 === 0,
        is_need_auto: true,
        is_automated: automated,
        attachments: [],
        custom_fields: {},
        approval_history: [],
        created_at: daysAgo(60 - (idx % 45)),
        updated_at: daysAgo(idx % 20),
      })
    }
  })
  return cases
}

function buildTasks(): ExecutionTask[] {
  const tasks: ExecutionTask[] = []
  let id = 0
  for (let day = 29; day >= 0; day -= 1) {
    const base = 18 + (day % 7) * 3 + ((day * 3 + id) % 5)
    for (let i = 0; i < base; i += 1) {
      id += 1
      const roll = (day * 17 + i * 13) % 100
      let overall_status = 'PASSED'
      if (roll < 8) overall_status = 'FAILED'
      else if (roll < 14) overall_status = 'RUNNING'
      else if (roll < 18) overall_status = 'PENDING'

      const d = new Date(now - day * 86400000)
      d.setHours(8 + (i % 12), (i * 7) % 60, 0, 0)
      tasks.push({
        task_id: `task-demo-${id}`,
        dispatch_channel: 'agent',
        schedule_type: 'immediate',
        schedule_status: 'done',
        dispatch_status: 'dispatched',
        consume_status: 'consumed',
        overall_status,
        case_count: 1 + (i % 4),
        agent_id: `agent-${(i % 6) + 1}`,
        created_at: isoAt(d),
        updated_at: isoAt(d),
      })
    }
  }
  return tasks
}

function buildAgents(): ExecutionAgent[] {
  const regions = ['北京', '上海', '深圳', '成都']
  return Array.from({ length: 8 }, (_, i) => ({
    agent_id: `agent-${i + 1}`,
    hostname: `srv-test-${String(i + 1).padStart(2, '0')}`,
    ip: `10.17.${150 + i}.${20 + i}`,
    region: regions[i % regions.length],
    status: 'active',
    registered_at: daysAgo(120),
    last_heartbeat_at: daysAgo(0),
    heartbeat_ttl_seconds: 60,
    lease_expires_at: daysAgo(-1),
    is_online: i !== 7,
    created_at: daysAgo(120),
    updated_at: daysAgo(0),
  }))
}

function buildAutomationCases(testCases: TestCaseResponse[]): AutomationTestCaseResponse[] {
  return testCases
    .filter((tc) => tc.is_automated)
    .slice(0, 180)
    .map((tc, i) => ({
      id: `auto-${i + 1}`,
      auto_case_id: `AUTO-${tc.case_id.replace('TC-', '')}`,
      dml_manual_case_id: tc.case_id,
      name: tc.title,
      version: '1.0.0',
      status: 'ACTIVE',
      framework: ['pytest', 'robot', 'custom'][i % 3],
      automation_type: ['CI', 'Nightly', 'Smoke', 'Regression'][i % 4],
      runtime_env: {},
      tags: tc.tags,
      maintainer_id: tc.owner_id,
      reviewer_id: tc.reviewer_id,
      created_at: tc.created_at,
      updated_at: tc.updated_at,
    }))
}

export interface DemoDashboardData {
  requirements: RequirementResponse[]
  testCases: TestCaseResponse[]
  tasks: ExecutionTask[]
  agents: ExecutionAgent[]
  automationCases: AutomationTestCaseResponse[]
}

export function buildDemoDashboardData(): DemoDashboardData {
  const requirements = buildRequirements()
  const testCases = buildTestCases(requirements)
  return {
    requirements,
    testCases,
    tasks: buildTasks(),
    agents: buildAgents(),
    automationCases: buildAutomationCases(testCases),
  }
}

export const DEMO_EXECUTIVE_METRICS: DemoExecutiveMetrics = {
  periodLabel: '2026 Q2 · 近 30 天',
  reportDate: new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' }),
  healthScore: 92,
  healthGrade: '优秀',
  healthSummary: '测试资产持续沉淀，自动化覆盖率稳步提升，核心 Lab 通过率高于目标线。',
  kpis: [
    { label: '用例通过率', value: '94.6%', delta: '+2.3%', deltaUp: true, sub: '目标 ≥ 90%', color: '#22c55e' },
    { label: '自动化覆盖率', value: '68.4%', delta: '+5.1%', deltaUp: true, sub: '较上季度', color: '#06b6d4' },
    { label: '需求交付率', value: '87.5%', delta: '+4.0%', deltaUp: true, sub: '12/12 项里程碑', color: '#3b82f6' },
    { label: '缺陷逃逸率', value: '0.8%', delta: '-0.3%', deltaUp: true, sub: '越低越好', color: '#a855f7' },
    { label: '平均执行时长', value: '42 min', delta: '-8 min', deltaUp: true, sub: '较上月优化', color: '#f59e0b' },
    { label: 'Agent 利用率', value: '76%', delta: '+12%', deltaUp: true, sub: '7/8 在线', color: '#ec4899' },
  ],
  highlights: [
    {
      type: 'success',
      title: 'DDR5-6400 回归套件全绿',
      detail: '连续 14 天 Nightly 通过率 100%，已纳入发布门禁。',
    },
    {
      type: 'info',
      title: '自动化资产 +126 条',
      detail: '本周期新增 pytest 脚本 86 条、Robot 套件 40 条，覆盖 5 个 Lab。',
    },
    {
      type: 'warning',
      title: 'PCIe Gen5 热插拔 2 项 flaky',
      detail: '已指派专人跟进，预计本周内完成稳定性加固。',
    },
  ],
  labCoverage: LABS.map((lab, i) => ({
    name: lab.name,
    cases: 48 + i * 22,
    automated: 32 + i * 18,
    passRate: 91 + (i % 4),
  })),
  weeklyQuality: [
    { week: 'W1', passRate: 89, coverage: 61, defects: 12 },
    { week: 'W2', passRate: 91, coverage: 63, defects: 9 },
    { week: 'W3', passRate: 93, coverage: 66, defects: 7 },
    { week: 'W4', passRate: 94, coverage: 68, defects: 5 },
    { week: 'W5', passRate: 95, coverage: 68, defects: 4 },
  ],
  teamPerformance: TEAM.map((m, i) => ({
    name: m.name,
    role: m.role,
    dept: m.dept,
    owned_cases: 28 + (i * 7) % 35,
    owned_reqs: 1 + (i % 3),
    reviewed_cases: 15 + (i * 5) % 25,
    completionRate: 82 + (i * 3) % 15,
  })),
  milestones: [
    { name: 'Q2 核心平台回归', progress: 92, target: '6月30日', status: 'on_track' },
    { name: 'BMC 固件认证包', progress: 78, target: '7月15日', status: 'on_track' },
    { name: 'DDR5 6400 量产准入', progress: 100, target: '已完成', status: 'done' },
    { name: 'CXL 互操作矩阵', progress: 54, target: '8月01日', status: 'at_risk' },
  ],
}
