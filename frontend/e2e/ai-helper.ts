/**
 * AI 辅助工具 — 调用内部 LLM 服务生成测试数据
 *
 * API: http://10.8.136.35:8881/v1/chat/completions
 * Model: seedcoder
 *
 * 设计原则：
 * - 每个数据生成函数对应一个业务模块
 * - 返回结构化数据，直接用于 Playwright 表单填充
 * - 每次调用的请求/响应自动保存到 ai-logs/ 便于回溯
 * - 标题自动追加时间戳，避免后端唯一约束冲突
 */

import { mkdirSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const AI_API_URL = 'http://10.8.136.35:8881/v1/chat/completions';
const AI_MODEL = 'seedcoder';
const LOG_DIR = join(dirname(fileURLToPath(import.meta.url)), 'ai-logs');

// ══════════════════════════════════════════════════════════════
//  类型定义
// ══════════════════════════════════════════════════════════════

/** 测试需求数据 */
export interface AiRequirementData {
  title: string;
  category: string;
  priority: string;
  acceptanceCriteria: string;
  tags: string[];
  background: string;
  functional: string;
  precondition: string;
  testFocus: string;
}

/** 项目数据 */
export interface AiProjectData {
  name: string;
  key: string;
  description: string;
  priority: string;
  version: string;
}

/** Lab 目录数据 */
export interface AiLabData {
  name: string;
  code: string;
  description: string;
}

/** 测试用例数据 */
export interface AiTestCaseData {
  title: string;
  priority: string;
  category: string;
  precondition: string;
  steps: string;
  expectedResult: string;
  tags: string[];
}

/** 预制用例集数据 */
export interface AiCollectionData {
  name: string;
  description: string;
  tags: string[];
}

// ══════════════════════════════════════════════════════════════
//  日志
// ══════════════════════════════════════════════════════════════

function ensureLogDir() {
  try { mkdirSync(LOG_DIR, { recursive: true }); } catch { /* 已存在 */ }
}

function saveLog(scenario: string, prompt: string, responseContent: string, result: unknown) {
  ensureLogDir();
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const safeName = scenario.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '_').slice(0, 30);
  const filename = `${timestamp}_${safeName}.json`;
  const filepath = join(LOG_DIR, filename);

  writeFileSync(filepath, JSON.stringify({
    timestamp: new Date().toISOString(),
    scenario,
    prompt,
    response: responseContent,
    parsed: result,
  }, null, 2), 'utf-8');

  console.log(`[AI日志] 已保存: ${filepath}`);
}

// ══════════════════════════════════════════════════════════════
//  AI 调用（内部）
// ══════════════════════════════════════════════════════════════

async function callAi(prompt: string): Promise<string> {
  const response = await fetch(AI_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: AI_MODEL,
      messages: [
        {
          role: 'system',
          content: '你是一个测试数据生成器。你的回答必须以 { 开头，以 } 结尾，中间只包含纯 JSON。严禁在 JSON 前后输出任何其他字符、解释或代码块标记。',
        },
        { role: 'user', content: prompt },
      ],
      extra_body: { chat_template_kwargs: { enable_thinking: false } },
    }),
  });

  if (!response.ok) {
    throw new Error(`AI 服务返回异常 (${response.status}): ${await response.text()}`);
  }

  const body = await response.json() as { choices: Array<{ message: { content: string } }> };
  const content = body.choices?.[0]?.message?.content;
  if (!content) throw new Error('AI 响应格式异常，缺少 content');
  return content;
}

/**
 * 解析 AI 返回的 JSON，兼容可能的 markdown 代码块标记
 */
function parseAiJson<T>(raw: string): T {
  // 提取第一个 JSON 对象，兼容 AI 在 JSON 前后输出额外文本
  const start = raw.indexOf('{');
  const end = raw.lastIndexOf('}');
  if (start === -1 || end === -1 || end <= start) {
    throw new Error(`AI 响应中未找到有效的 JSON 对象\n原始响应: ${raw.slice(0, 500)}`);
  }
  const jsonStr = raw.slice(start, end + 1);
  try {
    return JSON.parse(jsonStr) as T;
  } catch (e) {
    throw new Error(
      `AI 响应 JSON 解析失败\n提取 JSON: ${jsonStr.slice(0, 300)}\n原始响应: ${raw.slice(0, 300)}`
    );
  }
}

/**
 * 控制台打印 AI 生成的数据（格式化输出）
 */
function printAiData(title: string, data: Record<string, unknown>) {
  console.log('');
  console.log('═══════════════════════════════════════');
  console.log(`  AI 生成 ${title}`);
  console.log('═══════════════════════════════════════');
  for (const [key, value] of Object.entries(data)) {
    const label = key.padEnd(10);
    console.log(`  ${label}: ${Array.isArray(value) ? value.join(', ') : value}`);
  }
  console.log('═══════════════════════════════════════\n');
}

// ══════════════════════════════════════════════════════════════
//  分类映射 — AI 英文枚举 → 页面 <select> 中文标签
// ══════════════════════════════════════════════════════════════

const CATEGORY_MAP: Record<string, string> = {
  FUNCTIONAL: '功能测试',
  PERFORMANCE: '性能测试',
  STABILITY: '稳定性测试',
  COMPATIBILITY: '兼容性测试',
  SECURITY: '安全测试',
  REGRESSION: '回归测试',
};

/**
 * 将 AI 生成的 category（可能含 pipe 分隔的多值，如 "REGRESSION | SECURITY"）
 * 转为页面 <select> 可用的中文标签，只取第一个有效值。
 */
function mapToChineseCategory(raw: string): string {
  const first = raw.split('|').map(s => s.trim()).find(s => CATEGORY_MAP[s.toUpperCase()]);
  return first ? CATEGORY_MAP[first.toUpperCase()] : '功能测试'; // fallback
}

// ══════════════════════════════════════════════════════════════
//  需求数据生成
// ══════════════════════════════════════════════════════════════

export async function generateRequirementData(scenario: string): Promise<AiRequirementData> {
  const prompt = `你是一个测试需求分析师。请为以下场景生成一条完整的测试用例编写需求数据，只输出 JSON。

场景：${scenario}

输出 JSON 格式：
{
  "title": "需求标题（20字以内，中文）",
  "category": "FUNCTIONAL | PERFORMANCE | STABILITY | COMPATIBILITY | SECURITY | REGRESSION",
  "priority": "P0 | P1 | P2 | P3",
  "acceptanceCriteria": "验收标准（30字以内）",
  "tags": ["推荐标签1", "推荐标签2", "推荐标签3"],
  "background": "业务背景（50字以内）",
  "functional": "功能描述（50字以内）",
  "precondition": "前置条件（50字以内）",
  "testFocus": "测试要点（50字以内）"
}`;

  const raw = await callAi(prompt);
  const data = parseAiJson<Record<string, unknown>>(raw);

  const required = ['title', 'category', 'priority', 'acceptanceCriteria', 'tags', 'background', 'functional', 'precondition', 'testFocus'];
  for (const key of required) {
    if (!data[key]) throw new Error(`AI 返回数据缺少字段: ${key}`);
  }

  const title = `${String(data.title)}-${Date.now()}`;
  const result: AiRequirementData = {
    title,
    category: mapToChineseCategory(String(data.category)),
    priority: String(data.priority),
    acceptanceCriteria: String(data.acceptanceCriteria),
    tags: Array.isArray(data.tags) ? data.tags.map(String) : [],
    background: String(data.background),
    functional: String(data.functional),
    precondition: String(data.precondition),
    testFocus: String(data.testFocus),
  };

  saveLog(scenario, prompt, raw, result);
  printAiData('测试需求数据', { ...result, 场景: scenario });
  return result;
}

// ══════════════════════════════════════════════════════════════
//  项目数据生成
// ══════════════════════════════════════════════════════════════

export async function generateProjectData(scenario: string): Promise<AiProjectData> {
  const prompt = `为以下场景生成项目数据，只输出 JSON。

场景：${scenario}

{
  "name": "项目名称（10字以内，中文）",
  "key": "项目KEY（大写字母缩写，如 PROJ）",
  "description": "项目描述（40字以内）",
  "priority": "P0 | P1 | P2 | P3",
  "version": "版本号（如 v1.2.0）"
}`;

  const raw = await callAi(prompt);
  const data = parseAiJson<Record<string, unknown>>(raw);

  const result: AiProjectData = {
    name: `${String(data.name)}-${Date.now()}`,
    key: String(data.key ?? 'PROJ'),
    description: String(data.description ?? ''),
    priority: String(data.priority ?? 'P2'),
    version: String(data.version ?? 'v1.0.0'),
  };

  saveLog(scenario, prompt, raw, result);
  printAiData('项目数据', { ...result, 场景: scenario });
  return result;
}

// ══════════════════════════════════════════════════════════════
//  Lab 目录数据生成
// ══════════════════════════════════════════════════════════════

export async function generateLabData(scenario: string): Promise<AiLabData> {
  const prompt = `为以下场景生成 Lab 目录数据，只输出 JSON。

场景：${scenario}

{
  "name": "Lab名称（10字以内，中文）",
  "code": "Lab编码（大写英文缩写，如 LAB001）",
  "description": "Lab描述（40字以内）"
}`;

  const raw = await callAi(prompt);
  const data = parseAiJson<Record<string, unknown>>(raw);

  const result: AiLabData = {
    name: `${String(data.name)}-${Date.now()}`,
    code: String(data.code ?? `LAB-${Date.now().toString().slice(-4)}`),
    description: String(data.description ?? ''),
  };

  saveLog(scenario, prompt, raw, result);
  printAiData('Lab目录数据', { ...result, 场景: scenario });
  return result;
}

// ══════════════════════════════════════════════════════════════
//  测试用例数据生成
// ══════════════════════════════════════════════════════════════

export async function generateTestCaseData(scenario: string): Promise<AiTestCaseData> {
  const prompt = `你只输出以下格式的 JSON，不要输出任何其他内容（包括解释、markdown 标记）。

{"title": "用例标题（20字以内，中文）","priority": "P0","category": "FUNCTIONAL","precondition": "前置条件（40字以内）","steps": "测试步骤（60字以内，用一段简洁连续的话描述，不要分点编号）","expectedResult": "预期结果（40字以内）","tags": ["标签1","标签2"]}

场景：${scenario}`;

  const raw = await callAi(prompt);
  const data = parseAiJson<Record<string, unknown>>(raw);

  const required = ['title'];
  for (const key of required) {
    if (!data[key]) throw new Error(`AI 返回数据缺少字段: ${key}`);
  }

  const result: AiTestCaseData = {
    title: `${String(data.title)}-${Date.now()}`,
    priority: String(data.priority ?? 'P2'),
    category: mapToChineseCategory(String(data.category ?? 'FUNCTIONAL')),
    precondition: String(data.precondition ?? ''),
    steps: String(data.steps ?? ''),
    expectedResult: String(data.expectedResult ?? ''),
    tags: Array.isArray(data.tags) ? data.tags.map(String) : [],
  };

  saveLog(scenario, prompt, raw, result);
  printAiData('测试用例数据', { ...result, 场景: scenario });
  return result;
}

// ══════════════════════════════════════════════════════════════
//  预制用例集数据生成
// ══════════════════════════════════════════════════════════════

export async function generateCollectionData(scenario: string): Promise<AiCollectionData> {
  const prompt = `为以下场景生成预制用例集数据，只输出 JSON。

场景：${scenario}

{
  "name": "集合名称（15字以内，中文）",
  "description": "集合描述（40字以内）",
  "tags": ["标签1", "标签2", "标签3"]
}`;

  const raw = await callAi(prompt);
  const data = parseAiJson<Record<string, unknown>>(raw);

  const result: AiCollectionData = {
    name: `${String(data.name)}-${Date.now()}`,
    description: String(data.description ?? ''),
    tags: Array.isArray(data.tags) ? data.tags.map(String) : [],
  };

  saveLog(scenario, prompt, raw, result);
  printAiData('预制用例集数据', { ...result, 场景: scenario });
  return result;
}

// ══════════════════════════════════════════════════════════════
//  用户数据生成
// ══════════════════════════════════════════════════════════════

/** 用户数据 */
export interface AiUserData {
  userId: string;
  username: string;
  email: string;
}

export async function generateUserData(scenario: string): Promise<AiUserData> {
  const prompt = `为以下场景生成用户数据，只输出 JSON。

场景：${scenario}

{
  "userId": "登录ID（英文+数字，如 e2e_test_01）",
  "username": "用户显示名（4字以内，中文，如 张三）",
  "email": "邮箱地址（如 test@example.com）"
}`;

  const raw = await callAi(prompt);
  const data = parseAiJson<Record<string, unknown>>(raw);

  const timestamp = Date.now().toString().slice(-6);
  const result: AiUserData = {
    userId: `${String(data.userId ?? 'e2e_user')}_${timestamp}`,
    username: `${String(data.username ?? 'E2E用户')}`,
    email: String(data.email ?? `e2e_${timestamp}@test.com`),
  };

  saveLog(scenario, prompt, raw, result);
  printAiData('用户数据', { ...result, 场景: scenario });
  return result;
}

// ══════════════════════════════════════════════════════════════
//  执行计划数据生成
// ══════════════════════════════════════════════════════════════

/** 执行计划数据 */
export interface AiPlanData {
  title: string;
  description: string;
}

export async function generatePlanData(scenario: string): Promise<AiPlanData> {
  const prompt = `为以下场景生成执行计划数据，只输出 JSON。

场景：${scenario}

{
  "title": "计划名称（20字以内，中文）",
  "description": "计划描述（60字以内，说明目的和范围）"
}`;

  const raw = await callAi(prompt);
  const data = parseAiJson<Record<string, unknown>>(raw);

  const result: AiPlanData = {
    title: `${String(data.title)}-${Date.now()}`,
    description: String(data.description ?? ''),
  };

  saveLog(scenario, prompt, raw, result);
  printAiData('执行计划数据', { ...result, 场景: scenario });
  return result;
}
