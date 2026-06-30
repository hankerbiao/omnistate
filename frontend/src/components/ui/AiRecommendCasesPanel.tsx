/** AI 智能推荐用例面板 — 内嵌在创建计划向导的「选择用例」步骤 */
import { useState } from 'react'
import api from '../../services/api'
import type { RecommendedCase, ExcludedCase } from '../../types/ai'

interface Props {
  projectId?: string
  onSelectCases: (caseIds: string[]) => void
  onClose: () => void
}

export default function AiRecommendCasesPanel({ projectId, onSelectCases, onClose }: Props) {
  const [changeDesc, setChangeDesc] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{
    recommended: RecommendedCase[]
    excluded: ExcludedCase[]
    coverage_note: string
    estimated_runtime_min: number
  } | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const handleRecommend = async () => {
    if (!changeDesc.trim()) return
    setLoading(true)
    setResult(null)
    try {
      const res = await api.recommendCases({
        project_id: projectId,
        change_description: changeDesc,
        max_recommend: 20,
      })
      setResult(res.data)
      setSelectedIds(new Set(res.data.recommended.map(r => r.case_id)))
    } catch (e: any) {
      setResult({
        recommended: [],
        excluded: [],
        coverage_note: `调用失败: ${e.message}`,
        estimated_runtime_min: 0,
      })
    } finally {
      setLoading(false)
    }
  }

  const toggleCase = (caseId: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(caseId)) next.delete(caseId)
      else next.add(caseId)
      return next
    })
  }

  const handleApply = () => {
    onSelectCases(Array.from(selectedIds))
    onClose()
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.4)',
    }} onClick={onClose}>
      <div style={{
        background: '#fff', borderRadius: 12, width: 680, maxHeight: '80vh',
        overflow: 'auto', padding: 24,
      }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>AI 推荐用例</h3>
          <button onClick={onClose} style={{
            width: 28, height: 28, borderRadius: 6, border: '1px solid #e5e7eb',
            background: '#fff', cursor: 'pointer', fontSize: 14, lineHeight: 1,
          }}>✕</button>
        </div>

        <div style={{ marginBottom: 12 }}>
          <label style={{ display: 'block', fontSize: 12, color: '#374151', marginBottom: 4 }}>变更描述</label>
          <textarea
            value={changeDesc}
            onChange={e => setChangeDesc(e.target.value)}
            placeholder="描述本次变更内容，例如：修改了登录接口的 session 处理逻辑、新增了密码加密功能..."
            rows={3}
            style={{
              width: '100%', padding: '8px 10px', fontSize: 12, borderRadius: 6,
              border: '1px solid #d1d5db', resize: 'vertical',
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <button onClick={handleRecommend} disabled={loading || !changeDesc.trim()} style={{
            padding: '6px 16px', borderRadius: 6, border: 'none',
            background: loading || !changeDesc.trim() ? '#d1d5db' : '#3b82f6',
            color: '#fff', fontSize: 12, cursor: loading || !changeDesc.trim() ? 'default' : 'pointer',
          }}>{loading ? '分析中...' : 'AI 推荐'}</button>
          {result && (
            <button onClick={handleApply} style={{
              padding: '6px 16px', borderRadius: 6, border: 'none',
              background: '#7c3aed', color: '#fff', fontSize: 12, cursor: 'pointer',
            }}>添加选定用例（{selectedIds.size}）</button>
          )}
        </div>

        {loading && (
          <div style={{ textAlign: 'center', padding: 40, color: '#6b7280', fontSize: 13 }}>
            AI 正在分析变更范围和用例关联...
          </div>
        )}

        {result && !loading && (
          <div>
            {result.recommended.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: '#6b7280', fontSize: 13 }}>
                没有推荐用例
              </div>
            ) : (
              <>
                <div style={{ marginBottom: 8, fontSize: 12, color: '#6b7280' }}>
                  推荐 {result.recommended.length} 条，预估执行 {result.estimated_runtime_min} 分钟
                  {result.coverage_note && (
                    <span style={{ display: 'block', marginTop: 4, padding: 8, background: '#fffbeb', borderRadius: 6, color: '#92400e', lineHeight: 1.4 }}>
                      {result.coverage_note}
                    </span>
                  )}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {result.recommended.sort((a, b) => a.priority_order - b.priority_order).map(rec => (
                    <label key={rec.case_id} style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      padding: '8px 12px', borderRadius: 6,
                      border: selectedIds.has(rec.case_id) ? '1px solid #818cf8' : '1px solid #e5e7eb',
                      background: selectedIds.has(rec.case_id) ? '#eef2ff' : '#fff',
                      cursor: 'pointer',
                    }}>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(rec.case_id)}
                        onChange={() => toggleCase(rec.case_id)}
                      />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 13, fontWeight: 500 }}>{rec.case_id}</div>
                        <div style={{ fontSize: 11, color: '#6b7280' }}>{rec.reason}</div>
                      </div>
                      <span style={{ fontSize: 11, color: '#9ca3af' }}>#{rec.priority_order}</span>
                    </label>
                  ))}
                </div>
              </>
            )}

            {result.excluded.length > 0 && (
              <details style={{ marginTop: 12 }}>
                <summary style={{ fontSize: 12, color: '#6b7280', cursor: 'pointer' }}>
                  已排除 {result.excluded.length} 条用例
                </summary>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 8 }}>
                  {result.excluded.map(rec => (
                    <div key={rec.case_id} style={{ padding: '6px 12px', fontSize: 12, color: '#9ca3af', borderBottom: '1px solid #f3f4f6' }}>
                      {rec.case_id}: {rec.reason}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
