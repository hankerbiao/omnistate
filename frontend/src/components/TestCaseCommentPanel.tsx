/** 测试用例评论面板 */
import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'
import type { TestCaseComment } from '../types'

interface Props {
  caseId: string
  /** 刷新信号，外部可触发重新加载 */
  refreshSignal?: number
}

export default function TestCaseCommentPanel({ caseId, refreshSignal }: Props) {
  const [comments, setComments] = useState<TestCaseComment[]>([])
  const [loading, setLoading] = useState(true)
  const [newComment, setNewComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')

  const loadComments = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.listComments(caseId, { limit: 100 })
      // API returns items inside data
      const data = res.data as any
      setComments(data.items || [])
    } catch {
      setComments([])
    } finally {
      setLoading(false)
    }
  }, [caseId])

  useEffect(() => {
    loadComments()
  }, [loadComments, refreshSignal])

  const handleSubmit = async () => {
    const content = newComment.trim()
    if (!content) return
    setSubmitting(true)
    setError('')
    try {
      await api.createComment(caseId, { content })
      setNewComment('')
      await loadComments()
    } catch (err) {
      setError('评论发送失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSubmit()
    }
  }

  const handleEdit = async (commentId: string) => {
    const content = editContent.trim()
    if (!content) return
    setSubmitting(true)
    try {
      await api.updateComment(caseId, commentId, { content })
      setEditingId(null)
      await loadComments()
    } catch {
      setError('编辑失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (commentId: string) => {
    if (!confirm('确定删除这条评论？')) return
    try {
      await api.deleteComment(caseId, commentId)
      await loadComments()
    } catch {
      setError('删除失败，请重试')
    }
  }

  const formatTime = (iso: string) => {
    const d = new Date(iso)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 评论列表区域 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 0' }}>
        {loading ? (
          <div style={{ textAlign: 'center', color: '#9ca3af', fontSize: 13, padding: 24 }}>
            加载评论...
          </div>
        ) : comments.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#9ca3af', fontSize: 13, padding: 24 }}>
            暂无评论
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {comments.map(comment => {
              const isEditing = editingId === comment._id
              const isOwner = comment.author_name === localStorage.getItem('username')
              return (
                <div
                  key={comment._id}
                  style={{
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--surface-primary)',
                  }}
                >
                  {/* 头部：作者 + 时间 */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{
                        width: 24, height: 24, borderRadius: '50%',
                        background: 'var(--accent-primary)',
                        color: '#fff', fontSize: 11, fontWeight: 600,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        {(comment.author_name || comment.author_id)[0]?.toUpperCase() || '?'}
                      </div>
                      <span style={{ fontWeight: 500, fontSize: 13 }}>{comment.author_name || comment.author_id}</span>
                    </div>
                    <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                      {formatTime(comment.created_at)}
                      {comment.updated_at && ' (已编辑)'}
                    </span>
                  </div>

                  {/* 内容 */}
                  {isEditing ? (
                    <div>
                      <textarea
                        value={editContent}
                        onChange={e => setEditContent(e.target.value)}
                        style={{
                          width: '100%', minHeight: 60, padding: 8, fontSize: 13,
                          borderRadius: 6, border: '1px solid var(--border-subtle)',
                          resize: 'vertical', fontFamily: 'inherit',
                          background: 'var(--surface-secondary)',
                          color: 'var(--text-primary)',
                        }}
                      />
                      <div style={{ display: 'flex', gap: 6, marginTop: 6, justifyContent: 'flex-end' }}>
                        <button
                          onClick={() => setEditingId(null)}
                          style={btnStyle('secondary')}
                        >取消</button>
                        <button
                          onClick={() => handleEdit(comment._id)}
                          disabled={submitting || !editContent.trim()}
                          style={btnStyle('primary')}
                        >{submitting ? '保存中...' : '保存'}</button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--text-primary)', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {comment.content}
                    </div>
                  )}

                  {/* 操作按钮 */}
                  {!isEditing && isOwner && (
                    <div style={{ display: 'flex', gap: 8, marginTop: 8, justifyContent: 'flex-end' }}>
                      <button
                        onClick={() => { setEditingId(comment._id); setEditContent(comment.content) }}
                        style={actionBtnStyle}
                      >编辑</button>
                      <button
                        onClick={() => handleDelete(comment._id)}
                        style={{ ...actionBtnStyle, color: '#ef4444' }}
                      >删除</button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* 底部：评论输入框 */}
      <div style={{
        borderTop: '1px solid var(--border-subtle)',
        padding: '12px 0',
      }}>
        {error && (
          <div style={{ fontSize: 12, color: '#ef4444', marginBottom: 6 }}>{error}</div>
        )}
        <textarea
          value={newComment}
          onChange={e => setNewComment(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入评论... (Cmd+Enter 发送)"
          rows={3}
          style={{
            width: '100%', padding: 10, fontSize: 13,
            borderRadius: 8, border: '1px solid var(--border-subtle)',
            resize: 'vertical', fontFamily: 'inherit',
            background: 'var(--surface-secondary)',
            color: 'var(--text-primary)',
            boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
          <button
            onClick={handleSubmit}
            disabled={submitting || !newComment.trim()}
            style={{
              ...btnStyle('primary'),
              opacity: submitting || !newComment.trim() ? 0.5 : 1,
              cursor: submitting || !newComment.trim() ? 'not-allowed' : 'pointer',
            }}
          >
            {submitting ? '发送中...' : '发送评论'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Inline styles ── */
const btnStyle = (variant: 'primary' | 'secondary'): React.CSSProperties => ({
  padding: '5px 14px',
  fontSize: 12,
  fontWeight: 500,
  borderRadius: 6,
  border: variant === 'primary' ? 'none' : '1px solid var(--border-subtle)',
  background: variant === 'primary' ? 'var(--accent-primary)' : 'transparent',
  color: variant === 'primary' ? '#fff' : 'var(--text-secondary)',
  cursor: 'pointer',
})

const actionBtnStyle: React.CSSProperties = {
  padding: '2px 8px',
  fontSize: 11,
  borderRadius: 4,
  border: '1px solid var(--border-subtle)',
  background: 'transparent',
  color: 'var(--text-secondary)',
  cursor: 'pointer',
}
