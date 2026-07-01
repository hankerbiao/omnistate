/** AI 用例评审面板 — 内嵌在用例详情弹窗中 */
import { useState } from 'react'
import { api } from '../../services/api'
import type { ReviewCaseResponse } from '../../types/ai'

interface Props {
  caseId: string
}

export default function AiCaseReviewPanel({ caseId }: Props) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ReviewCaseResponse | null>(null)
  const [expanded, setExpanded] = useState(false)

  const handleReview = async () => {
    setLoading(true)
    setResult(null)
    try {
      const res = await api.reviewCase(caseId)
      setResult(res.data)
    } catch (e: any) {
      setResult({
        score: 0,
        verdict: 'needs_revision',
        dimensions: {},
        missing_scenarios: [`调用失败: ${e.message}`],
        priority_suggestion: '保持不变',
        summary: '',
      })
    } finally {
      setLoading(false)
    }
  }

  const verdictLabel: Record<string, { label: string; color: string }> = {
    pass: { label: '通过', color: '#16a34a' },
    needs_revision: { label: '需修改', color: '#d97706' },
    reject: { label: '未通过', color: '#dc2626' },
  }

  const dimLabels: Record<string, string> = {
    completeness: '完整性',
    clarity: '清晰度',
    traceability: '可追溯性',
    executability: '可执行性',
  }

  return (
    <div style={{
      marginTop: 12, padding: 12, borderRadius: 8,
      border: '1px solid #e5e7eb', background: '#fafafa',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <strong style={{ fontSize: 13 }}>AI 评审</strong>
        <button
          onClick={expanded && result ? () => setExpanded(false) : handleReview}
          style={{
            padding: '4px 12px', borderRadius: 6, border: 'none',
            background: loading ? '#d1d5db' : result && !loading ? '#e0e7ff' : '#3b82f6',
            color: loading ? '#9ca3af' : result && !loading ? '#4338ca' : '#fff',
            fontSize: 11, cursor: loading ? 'default' : 'pointer',
          }}
        >
          {loading ? '评审中...' : result && !loading ? (expanded ? '收起' : '查看结果') : '开始评审'}
        </button>
      </div>

      {result && expanded && (
        <div>
          {/* 评分 + verdict */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              width: 40, height: 40, borderRadius: '50%',
              background: result.score >= 80 ? '#dcfce7' : result.score >= 50 ? '#fef9c3' : '#fee2e2',
              color: result.score >= 80 ? '#16a34a' : result.score >= 50 ? '#d97706' : '#dc2626',
              fontWeight: 700, fontSize: 16,
            }}>{result.score}</span>
            <span style={{
              padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 500,
              background: `${verdictLabel[result.verdict]?.color || '#6b7280'}20`,
              color: verdictLabel[result.verdict]?.color || '#6b7280',
            }}>{verdictLabel[result.verdict]?.label || result.verdict}</span>
            {result.priority_suggestion !== '保持不变' && (
              <span style={{ padding: '2px 8px', borderRadius: 6, fontSize: 11, background: '#f0fdf4', color: '#16a34a' }}>
                建议优先级: {result.priority_suggestion}
              </span>
            )}
          </div>

          {/* 维度评分 */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 8 }}>
            {Object.entries(result.dimensions).map(([key, dim]) => (
              <div key={key} style={{
                padding: 8, borderRadius: 6,
                background: dim.score >= 80 ? '#f0fdf4' : dim.score >= 50 ? '#fffbeb' : '#fef2f2',
                fontSize: 12,
              }}>
                <div style={{ fontWeight: 500, color: '#374151', marginBottom: 2 }}>
                  {dimLabels[key] || key}
                  <span style={{ marginLeft: 6, color: dim.score >= 80 ? '#16a34a' : dim.score >= 50 ? '#d97706' : '#dc2626' }}>
                    {dim.score}
                  </span>
                </div>
                {dim.issues.map((issue, i) => (
                  <div key={i} style={{ color: '#6b7280', fontSize: 11, marginTop: 1 }}>• {issue}</div>
                ))}
              </div>
            ))}
          </div>

          {/* 缺失场景 */}
          {result.missing_scenarios.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <strong style={{ fontSize: 12, color: '#374151' }}>建议补充场景:</strong>
              <ul style={{ margin: '4px 0', paddingLeft: 16, fontSize: 11, color: '#6b7280' }}>
                {result.missing_scenarios.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 总结 */}
          {result.summary && (
            <div style={{ fontSize: 12, color: '#4b5563', lineHeight: 1.5, padding: 8, background: '#f3f4f6', borderRadius: 6 }}>
              {result.summary}
            </div>
          )}
        </div>
      )}

      {!result && !loading && (
        <div style={{ fontSize: 11, color: '#9ca3af' }}>
          点击「开始评审」按钮，AI 将从完整性、清晰度、可追溯性、可执行性四维度评审此用例
        </div>
      )}
    </div>
  )
}
