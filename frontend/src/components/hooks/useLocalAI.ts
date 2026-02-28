import { useState, useCallback } from 'react';
import { LOCAL_AI_BASE_URL, LOCAL_AI_MODEL } from '../../constants/config';

export function useLocalAI() {
  const [isLoading, setIsLoading] = useState(false);

  const callLocalAI = useCallback(async (prompt: string, systemPrompt?: string): Promise<string> => {
    const response = await fetch(`${LOCAL_AI_BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: LOCAL_AI_MODEL,
        messages: [
          ...(systemPrompt ? [{ role: 'system', content: systemPrompt }] : []),
          { role: 'user', content: prompt }
        ],
        temperature: 0.7,
      })
    });
    const data = await response.json();
    return data.choices?.[0]?.message?.content || '';
  }, []);

  const polishText = useCallback(async (
    text: string,
    field: 'description' | 'technical_spec',
    onResult: (field: 'description' | 'technical_spec', result: string) => void
  ) => {
    if (!text) return;

    setIsLoading(true);
    try {
      const result = await callLocalAI(
        `请作为一名资深的服务器硬件测试专家，润色以下测试需求描述，使其更加专业、准确且符合行业规范。保持原意不变，但优化措辞和结构：\n\n${text}`,
        '你是一个专业的技术文档润色助手。'
      );

      if (result) {
        onResult(field, result.trim());
      }
    } catch (error) {
      console.error("AI Polish failed:", error);
      alert("AI 润色失败，请稍后重试。");
    } finally {
      setIsLoading(false);
    }
  }, [callLocalAI]);

  const generateSteps = useCallback(async (
    reqTitle: string,
    reqDescription: string,
    reqTechSpec: string | undefined,
    reqKeyParams: { key: string; value: string }[],
    onResult: (steps: { step_id: string; name: string; action: string; expected: string }[]) => void
  ) => {
    setIsLoading(true);
    try {
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

      const result = await callLocalAI(prompt, '你是一个专业的测试用例生成助手。请根据需求生成测试步骤，返回纯JSON数组。');

      if (result) {
        const steps = JSON.parse(result);
        const formattedSteps = steps.map((s: any, i: number) => ({
          ...s,
          step_id: `step-${Date.now()}-${i}`
        }));
        onResult(formattedSteps);
      }
    } catch (error) {
      console.error("AI Generation failed:", error);
      alert("AI 生成步骤失败，请检查需求内容或重试。");
    } finally {
      setIsLoading(false);
    }
  }, [callLocalAI]);

  return {
    isLoading,
    callLocalAI,
    polishText,
    generateSteps,
  };
}