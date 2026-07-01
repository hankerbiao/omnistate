/**
 * AI 辅助工具 — 调用内部 LLM 服务生成测试数据
 *
 * API: http://10.8.136.35:8881/v1/chat/completions
 * Model: seedcoder
 *
 * 每次调用 AI 的请求和响应会自动保存到 ai-logs/ 目录下，
 * 方便调试和回溯。
 */

import { mkdirSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const AI_API_URL = 'http://10.8.136.35:8881/v1/chat/completions';
const AI_MODEL = 'seedcoder';
const LOG_DIR = join(dirname(fileURLToPath(import.meta.url)), 'ai-logs');

// ── 类型定义 ────────────────────────────────────────

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

// ── 日志 ────────────────────────────────────────────

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

// ── AI 调用 ─────────────────────────────────────────

async function callAi(prompt: string): Promise<string> {
  const response = await fetch(AI_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: AI_MODEL,
      messages: [
        {
          role: 'user',
          content: prompt,
        },
      ],
      extra_body: {
        chat_template_kwargs: { enable_thinking: false },
      },
    }),
  });

  if (!response.ok) {
    throw new Error(`AI 服务返回异常 (${response.status}): ${await response.text()}`);
  }

  const body = await response.json() as {
    choices: Array<{ message: { content: string } }>;
  };

  const content = body.choices?.[0]?.message?.content;
  if (!content) {
    throw new Error('AI 响应格式异常，缺少 content');
  }
  return content;
}

// ── 生成需求测试数据 ────────────────────────────────

/**
 * 调用 AI 为指定场景生成一条完整的测试需求数据。
 * AI 返回 JSON 格式，由本函数解析后返回结构化对象。
 *
 * 每次调用的请求、响应和解析结果都会保存到 ai-logs/ 目录下。
 */
export async function generateRequirementData(scenario: string): Promise<AiRequirementData> {
  const prompt = `你是一个测试需求分析师。请为以下场景生成一条完整的测试用例编写需求数据，**只输出 JSON**，不要任何解释、不要 markdown 代码块标记。

场景：${scenario}

输出 JSON 格式要求：
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
}

只输出 JSON，不要其他内容。`;

  const raw = await callAi(prompt);

  // 尝试解析 JSON（AI 可能带 markdown 代码块标记，做兼容）
  const jsonStr = raw
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/\s*```$/i, '')
    .trim();

  const data = JSON.parse(jsonStr) as Record<string, unknown>;

  // 校验
  const required = ['title', 'category', 'priority', 'acceptanceCriteria', 'tags', 'background', 'functional', 'precondition', 'testFocus'];
  for (const key of required) {
    if (!data[key]) throw new Error(`AI 返回数据缺少字段: ${key}`);
  }

  const result: AiRequirementData = {
    title: String(data.title),
    category: String(data.category),
    priority: String(data.priority),
    acceptanceCriteria: String(data.acceptanceCriteria),
    tags: Array.isArray(data.tags) ? data.tags.map(String) : [],
    background: String(data.background),
    functional: String(data.functional),
    precondition: String(data.precondition),
    testFocus: String(data.testFocus),
  };

  // 保存日志
  saveLog(scenario, prompt, raw, result);

  // 控制台输出 AI 生成结果
  console.log('');
  console.log('═══════════════════════════════════════');
  console.log('  AI 生成测试数据');
  console.log('═══════════════════════════════════════');
  console.log(`  标题:     ${result.title}`);
  console.log(`  分类:     ${result.category}`);
  console.log(`  优先级:   ${result.priority}`);
  console.log(`  验收标准: ${result.acceptanceCriteria}`);
  console.log(`  标签:     ${result.tags.join(', ')}`);
  console.log(`  业务背景: ${result.background}`);
  console.log(`  功能描述: ${result.functional}`);
  console.log(`  前置条件: ${result.precondition}`);
  console.log(`  测试要点: ${result.testFocus}`);
  console.log('═══════════════════════════════════════\n');

  return result;
}
