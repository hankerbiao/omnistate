import type { PageType } from '../types/app';

export type HelpSectionName = '测试资产' | '执行';

export interface HelpSectionDoc {
  title: HelpSectionName;
  summary: string;
  pages: string[];
}

export interface PageHelpDoc {
  page: PageType;
  title: string;
  summary: string;
  scenarios: string[];
  areas: string[];
  actions: string[];
  workflows: string[];
  notes: string[];
  relatedPages: string[];
}

const PAGE_SECTION_MAP: Partial<Record<PageType, HelpSectionName>> = {
  requirements: '测试资产',
  testCases: '测试资产',
  collections: '测试资产',
  projects: '测试资产',
  testPlanStudioDemo: '执行',
  caseGovernance: '执行',
};

export const sectionHelpDocs: Record<HelpSectionName, HelpSectionDoc> = {
  测试资产: {
    title: '测试资产',
    summary: '测试资产分组承载从需求到用例、集合与项目归属的核心资料，帮助团队把“为什么测、测什么、如何复用、归属哪个项目”串起来。',
    pages: ['测试用例编写需求', '用例看板', '预制用例集', '项目'],
  },
  执行: {
    title: '执行',
    summary: '执行分组围绕测试落地闭环展开：先把用例组织成执行计划，再通过治理能力补齐影响执行质量的资产信息。',
    pages: ['执行计划', '用例治理'],
  },
};

export const pageHelpDocs: Partial<Record<PageType, PageHelpDoc>> = {
  myTasks: {
    page: 'myTasks',
    title: '我的任务',
    summary: '聚合当前用户需要处理的执行任务和工作流待办，是日常跟进测试工作的入口。',
    scenarios: [
      '查看分配给自己的用例执行任务。',
      '处理测试用例编写需求相关待办。',
      '快速定位逾期、未排期或正在执行的事项。',
    ],
    areas: [
      '顶部工具栏显示待办统计、刷新入口和视图切换。',
      '任务列表按用例执行任务、工作流待办等类别组织。',
      '详情区展示需求、用例、执行信息和可继续处理的动作。',
    ],
    actions: [
      '刷新任务列表，重新拉取工作流和执行计划任务。',
      '按类别、时间状态或范围筛选待办。',
      '查看任务详情，并根据任务类型创建用例、回填结果或跟进执行状态。',
    ],
    workflows: [
      '先查看顶部统计，判断是否有逾期或待处理任务。',
      '在任务分组中选择一条事项，阅读右侧详情。',
      '根据页面给出的主操作完成创建用例、执行结果回填或流程处理。',
    ],
    notes: [
      '页面展示的是当前账号可见或与当前账号相关的任务。',
      '执行任务和工作流待办来自不同后端模块，刷新时可能存在加载时间差。',
    ],
    relatedPages: ['测试用例编写需求', '执行计划', '用例看板'],
  },
  requirements: {
    page: 'requirements',
    title: '测试用例编写需求',
    summary: '管理测试用例编写需求，并从需求出发创建、查看和跟踪关联测试用例。',
    scenarios: [
      '录入新的测试用例编写需求。',
      '按状态或分类跟踪需求处理进度。',
      '从需求详情中创建或查看关联测试用例。',
    ],
    areas: [
      '左侧列表展示需求摘要、状态、分类和创建信息。',
      '顶部筛选区支持按状态、分类和关键词缩小范围。',
      '右侧详情区展示需求内容、工作流、关联测试用例和操作入口。',
    ],
    actions: [
      '新建、删除或批量管理需求。',
      '查看需求工作流并执行可用流转动作。',
      '在需求详情中创建测试用例，建立需求到用例的关联。',
    ],
    workflows: [
      '通过筛选找到目标需求。',
      '打开详情确认需求描述和当前状态。',
      '根据需求创建测试用例，或查看已有用例覆盖情况。',
    ],
    notes: [
      '需求状态会影响可执行的工作流动作。',
      '删除需求前需要确认其关联用例和后续追溯影响。',
    ],
    relatedPages: ['我的任务', '用例看板', '项目'],
  },
  testCases: {
    page: 'testCases',
    title: '用例看板',
    summary: '统一浏览和管理手工测试用例与自动化测试用例，支持按 Lab、目录、类型、状态和标签筛选。',
    scenarios: [
      '查看某个 Lab 或目录下的全部用例。',
      '创建新的手工用例或自动化用例。',
      '通过搜索、类型和标签快速定位用例。',
    ],
    areas: [
      '左侧目录树用于按 Lab 和目录路径浏览资产。',
      '顶部筛选区提供搜索、类型、状态、标签和刷新操作。',
      '右侧卡片网格展示统一后的用例列表，详情弹窗展示完整信息。',
    ],
    actions: [
      '创建手工用例或自动化用例。',
      '刷新当前用例数据。',
      '清除筛选、选择标签、查看详情或删除目标用例。',
    ],
    workflows: [
      '先选择 Lab 或目录，限定资产范围。',
      '使用搜索和筛选条件定位目标用例。',
      '打开详情检查步骤、状态、标签和自动化信息。',
    ],
    notes: [
      '手工用例和自动化用例的数据来源不同，但会在看板中统一展示。',
      '目录和 Lab 信息缺失的用例可在用例治理页面继续补齐。',
    ],
    relatedPages: ['测试用例编写需求', '预制用例集', '用例治理', '执行计划'],
  },
  collections: {
    page: 'collections',
    title: '预制用例集',
    summary: '维护可复用的测试用例集合，便于在执行计划中批量选取稳定的测试范围。',
    scenarios: [
      '为回归、冒烟或专项测试准备固定用例集合。',
      '维护集合内手工用例和自动化用例。',
      '在创建执行计划前整理可复用的测试范围。',
    ],
    areas: [
      '左侧列表展示集合名称、描述、用例数量和更新时间。',
      '搜索和排序区用于快速定位目标集合。',
      '右侧详情区展示集合统计、集合内用例表格和批量操作。',
    ],
    actions: [
      '新建、编辑或删除预制用例集。',
      '向集合添加用例，或从集合中移除用例。',
      '在集合详情中搜索、批量选择和批量移除用例。',
    ],
    workflows: [
      '新建集合并填写名称与描述。',
      '打开集合详情，添加需要复用的用例。',
      '在执行计划创建时选择该集合中的用例。',
    ],
    notes: [
      '集合只组织用例范围，不直接触发执行。',
      '删除集合不会等同于删除原始测试用例。',
    ],
    relatedPages: ['用例看板', '执行计划', '项目'],
  },
  projects: {
    page: 'projects',
    title: '项目',
    summary: '管理项目基本信息、状态和测试资产统计，作为需求、用例与执行计划的归属视角。',
    scenarios: [
      '创建或维护项目基础信息。',
      '查看项目下需求、用例、自动化和执行计划数量。',
      '从项目详情跳转到关联资产页面继续处理。',
    ],
    areas: [
      '左侧项目列表支持搜索和状态筛选。',
      '右侧详情区展示项目信息、项目进度、统计数据和最近动态。',
      '操作区提供编辑、归档/激活和删除入口。',
    ],
    actions: [
      '新建、编辑、归档、激活或删除项目。',
      '查看需求覆盖率、执行任务进度和执行人分布。',
      '点击需求、用例或计划统计跳转到相关页面。',
    ],
    workflows: [
      '先创建项目并补充计划周期。',
      '在项目详情中观察资产和执行统计。',
      '通过统计入口跳转到需求、用例或执行计划页面继续处理。',
    ],
    notes: [
      '项目统计来自后端聚合数据，刷新详情时可能短暂显示加载状态。',
      '删除项目前需确认是否会影响团队对关联资产的组织视角。',
    ],
    relatedPages: ['测试用例编写需求', '用例看板', '执行计划'],
  },
  testPlanStudioDemo: {
    page: 'testPlanStudioDemo',
    title: '执行计划',
    summary: '把测试用例组织成可执行计划，完成用例选择、执行人分配、排期确认和结果跟踪。',
    scenarios: [
      '创建一次手工或自动化测试执行计划。',
      '给计划条目分配执行人并安排周期。',
      '查看执行结果、重新执行失败或需复测的用例。',
    ],
    areas: [
      '左侧计划列表支持搜索和状态筛选。',
      '右侧详情区展示计划信息、条目列表、看板/表格视图和结果入口。',
      '新建计划向导包含基本信息、选择用例、分配执行人和排期确认。',
    ],
    actions: [
      '新建计划并从用例库或预制集合选择用例。',
      '编辑计划信息、添加用例、批量指派执行人。',
      '查看执行结果、重新执行条目或删除计划。',
    ],
    workflows: [
      '点击新建计划，填写计划名称、描述和周期。',
      '选择测试用例或预制集合，确认执行范围。',
      '分配执行人并创建计划，后续在详情中跟踪结果。',
    ],
    notes: [
      '自动化和手工条目的结果来源不同，详情弹窗会按类型展示。',
      '重新执行会重置条目状态并清理旧结果展示。',
    ],
    relatedPages: ['我的任务', '用例看板', '预制用例集', '项目'],
  },
  caseGovernance: {
    page: 'caseGovernance',
    title: '用例治理',
    summary: '发现并修复影响检索、归类和执行质量的不完整测试用例信息。',
    scenarios: [
      '检查缺失 Lab、目录或标签的测试用例。',
      '补齐手工用例与自动化用例之间的关联。',
      '在执行前提升用例资产的可检索性和可复用性。',
    ],
    areas: [
      '统计卡片展示不同缺失类型的数量。',
      '筛选栏支持按缺失类型和关键词定位问题用例。',
      '列表操作区提供设置 Lab、设置目录、添加 Tag、关联或取消关联自动化用例。',
    ],
    actions: [
      '按缺失类型筛选需要治理的用例。',
      '直接补充 Lab、目录和标签等资产字段。',
      '关联或取消关联对应的自动化用例。',
    ],
    workflows: [
      '先从统计卡片选择数量较高的缺失类型。',
      '在列表中搜索并定位目标用例。',
      '使用行内操作补齐信息，观察统计数量变化。',
    ],
    notes: [
      '治理动作会修改用例资产字段，请确认目标用例后再保存。',
      '自动化关联需要从候选自动化用例中选择匹配项。',
    ],
    relatedPages: ['用例看板', '执行计划', '预制用例集'],
  },
};

export const targetHelpPages: PageType[] = [
  'myTasks',
  'requirements',
  'testCases',
  'collections',
  'projects',
  'testPlanStudioDemo',
  'caseGovernance',
];

export function getPageHelpDoc(page: PageType): PageHelpDoc | undefined {
  return pageHelpDocs[page];
}

export function getSectionHelpDocForPage(page: PageType): HelpSectionDoc | undefined {
  const section = PAGE_SECTION_MAP[page];
  return section ? sectionHelpDocs[section] : undefined;
}
