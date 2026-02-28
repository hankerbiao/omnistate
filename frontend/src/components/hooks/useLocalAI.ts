/**
 * @fileoverview 本地AI服务Hook
 * 集成AI辅助功能，提供文本润色和测试步骤生成能力
 */

import { useState, useCallback } from 'react';
import { LOCAL_AI_BASE_URL, LOCAL_AI_MODEL } from '../../constants/config';

/**
 * 本地AI服务管理Hook
 * 提供与本地AI服务的交互功能，包括：
 * - 直接调用AI API
 * - 文本润色优化
 * - 智能生成测试步骤
 * @returns AI服务方法和状态
 */
export function useLocalAI() {
  // ========== 状态定义 ==========

  /** AI请求加载状态 */
  const [isLoading, setIsLoading] = useState(false);

  // ========== 核心方法 ==========

  /**
   * 直接调用本地AI服务
   * 通用方法，可用于自定义AI交互场景
   * @param prompt 用户输入的提示词
   * @param systemPrompt 系统提示词（可选，用于设定AI角色）
   * @returns Promise<string> AI生成的文本内容
   */
  const callLocalAI = useCallback(
    async (prompt: string, systemPrompt?: string): Promise<string> => {
      // 发起POST请求到AI服务的聊天完成接口
      const response = await fetch(`${LOCAL_AI_BASE_URL}/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: LOCAL_AI_MODEL,              // 使用的AI模型
          messages: [
            // 系统提示词（可选，用于设定AI角色和行为）
            ...(systemPrompt ? [{ role: 'system', content: systemPrompt }] : []),
            // 用户提示词
            { role: 'user', content: prompt }
          ],
          temperature: 0.7,                   // 生成随机性参数（0-1）
        })
      });

      // 解析AI响应数据
      const data = await response.json();
      // 返回AI生成的文本内容（第一个选择的结果）
      return data.choices?.[0]?.message?.content || '';
    },
    []
  );

  // ========== 文本润色功能 ==========

  /**
   * 使用AI润色文本内容
   * 将技术文档优化为更专业、规范的表达方式
   * @param text 要润色的原始文本
   * @param field 文本字段类型（描述或技术规范）
   * @param onResult 润色完成后的回调函数
   */
  const polishText = useCallback(
    async (
      text: string,
      field: 'description' | 'technical_spec',
      onResult: (field: 'description' | 'technical_spec', result: string) => void
    ) => {
      // 空文本跳过处理
      if (!text) return;

      setIsLoading(true); // 开始加载状态
      try {
        // 调用AI进行文本润色
        const result = await callLocalAI(
          // 专业的提示词，要求AI扮演资深测试专家
          `请作为一名资深的服务器硬件测试专家，润色以下测试需求描述，使其更加专业、准确且符合行业规范。保持原意不变，但优化措辞和结构：\n\n${text}`,
          // 设定AI为专业的技术文档润色助手
          '你是一个专业的技术文档润色助手。'
        );

        // 将润色结果通过回调返回
        if (result) {
          onResult(field, result.trim());
        }
      } catch (error) {
        // 错误处理
        console.error("AI Polish failed:", error);
        alert("AI 润色失败，请稍后重试。");
      } finally {
        setIsLoading(false); // 结束加载状态
      }
    },
    [callLocalAI]
  );

  // ========== 测试步骤生成功能 ==========

  /**
   * 使用AI生成测试步骤
   * 基于测试需求自动生成详细的测试执行步骤
   * @param reqTitle 需求标题
   * @param reqDescription 需求描述
   * @param reqTechSpec 技术规格（可选）
   * @param reqKeyParams 关键参数列表
   * @param onResult 生成完成后的回调函数
   */
  const generateSteps = useCallback(
    async (
      reqTitle: string,
      reqDescription: string,
      reqTechSpec: string | undefined,
      reqKeyParams: { key: string; value: string }[],
      onResult: (steps: { step_id: string; name: string; action: string; expected: string }[]) => void
    ) => {
      setIsLoading(true); // 开始加载状态
      try {
        // 构建详细的测试步骤生成提示词
        const prompt = `
          作为服务器硬件测试专家，请根据以下测试需求生成详细的测试步骤。
          需求标题: ${reqTitle}
          需求描述: ${reqDescription}
          技术规范: ${reqTechSpec || '无'}
          关键参数: ${JSON.stringify(reqKeyParams)}

          请返回一个 JSON 数组，格式如下：
          [
            { "name": "步骤名称", "action": "具体操作步骤", "expected": "预期结果" }
          ]
          仅返回 JSON，不要有其他解释文字。
        `;

        // 调用AI生成测试步骤
        const result = await callLocalAI(
          prompt,
          '你是一个专业的测试用例生成助手。请根据需求生成测试步骤，返回纯JSON数组。'
        );

        if (result) {
          // 解析AI返回的JSON结果
          const steps = JSON.parse(result);
          // 为每个步骤添加唯一标识符
          const formattedSteps = steps.map((s: any, i: number) => ({
            ...s,
            step_id: `step-${Date.now()}-${i}` // 时间戳+索引生成唯一ID
          }));
          // 通过回调返回格式化的步骤数组
          onResult(formattedSteps);
        }
      } catch (error) {
        // 错误处理
        console.error("AI Generation failed:", error);
        alert("AI 生成步骤失败，请检查需求内容或重试。");
      } finally {
        setIsLoading(false); // 结束加载状态
      }
    },
    [callLocalAI]
  );

  // ========== 返回值 ==========

  return {
    isLoading,       // 加载状态
    callLocalAI,     // 直接调用AI的方法
    polishText,      // 文本润色功能
    generateSteps,   // 测试步骤生成功能
  };
}