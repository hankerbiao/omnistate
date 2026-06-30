/** AI 生成用例草稿预览面板 */
import { useState } from 'react'
import api from '../../services/api'
import type { GeneratedCaseDraft } from '../../types/ai'

interface Props {
  requirementId?: string
  requirementText?: string
  onClose: () => void
}

export default function AiCaseDraftPanel({ requirementId, requirementText, onClose }: Props) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ cases: GeneratedCaseDraft[]; reason: string } | null>(null)

  const handleGenerate = async () => {
    setLoading(true)
    try {
      const res = await api.generateCases({
        requirement_id: requirementId,
        requirement_text: requirementText,
        max_cases: 5,
      })
      setResult(res.data)
    } catch (e: any) {
      setResult({ cases: [], reason: `调用失败: ${e.message}` })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.4)',
    }} onClick={onClose}>
      <div style={{
        background: '#fff', borderRadius: 12, width: 720, maxHeight: '80vh',
        overflow: 'auto', padding: 24,
      }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>AI 生成用例草稿</h3>
          <button onClick={onClose} style={{
            width: 28, height: 28, borderRadius: 6, border: '1px solid #e5e7eb',
            background: '#fff', cursor: 'pointer', fontSize: 14, lineHeight: 1,
          }}>✕</button>
        </div>

        {!result && !loading && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
              AI 将根据需求信息自动生成{requirementId ? `（需求 ID: ${requirementId}）` : ''}测试用例草稿
            </p>
            <button onClick={handleGenerate} style={{
              padding: '8px 24px', borderRadius: 8, border: 'none',
              background: '#3b82f6', color: '#fff', fontSize: 14,
              cursor: 'pointer',
            }}>开始生成</button>
          </div>
        )}

        {loading && (
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#6b7280', fontSize: 13 }}>
            正在生成测试用例...
          </div>
        )}

        {result && !loading && (
          <div>
            {result.cases.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: '#6b7280', fontSize: 13 }}>
                {result.reason || 'AI 未生成任何用例'}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {result.cases.map((c, i) => (
                  <div key={i} style={{
                    padding: 12, borderRadius: 8, border: '1px solid #e5e7eb',
                    background: '#fafafa',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <strong style={{ fontSize: 14 }}>{c.title}</strong>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <span style={{
                          padding: '1px 6px', borderRadius: 6, fontSize: 11,
                          background: c.priority === 'P0' ? '#fef2f2' : c.priority === 'P1' ? '#fffbeb' : '#f0fdf4',
                          color: c.priority === 'P0' ? '#dc2626' : c.priority === 'P1' ? '#d97706' : '#16a34a',
                        }}>{c.priority}</span>
                        <span style={{ padding: '1px 6px', borderRadius: 6, fontSize: 11, background: '#e0e7ff', color: '#4338ca' }}>{c.test_category}</span>
                      </div>
                    </div>
                    {c.pre_condition && <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>前置: {c.pre_condition}</div>}
                    <ol style={{ margin: '4px 0', paddingLeft: 18, fontSize: 12, color: '#374151' }}>
                      {c.steps.map((s, si) => (
                        <li key={si} style={{ marginBottom: 2 }}>
                          <strong>{s.name}</strong>: {s.action} → <em style={{ color: '#6b7280' }}>{s.expected}</em>
                        </li>
                      ))}
                    </ol>
                    {c.rationale && <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>{c.rationale}</div>}
                    {c.tags.length > 0 && (
                      <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                        {c.tags.map((t, ti) => (
                          <span key={ti} style={{ padding: '0 6px', borderRadius: 4, fontSize: 10, background: '#f3f4f6', color: '#6b7280' }}>{t}</span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
              <button onClick={handleGenerate} style={{
                padding: '6px 16px', borderRadius: 6, border: '1px solid #d1d5db',
                background: '#fff', cursor: 'pointer', fontSize: 12, marginRight: 8,
              }}>重新生成</button>
              <button onClick={onClose} style={{
                padding: '6px 16px', borderRadius: 6, border: 'none',
                background: '#3b82f6', color: '#fff', fontSize: 12, cursor: 'pointer',
              }}>关闭</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
