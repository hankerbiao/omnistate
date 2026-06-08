/** 节点详情弹窗 - 在血缘图谱中点击节点时展示 */
import { useState, useEffect } from 'react'
import { api } from '../../services/api'
import type { LineageNode, LineageEdge, LineageGraphResponse } from '../../types'

interface EntityDetailModalProps {
  node: LineageNode | null
  onClose: () => void
  onOpenLineage: (type: string, id: string) => void
}

const NODE_TYPE_LABELS: Record<string, string> = {
  requirement: '测试需求',
  test_case: '测试用例',
  automation_case: '自动化用例',
  task: '执行任务',
  case_result: '用例结果',
  agent: '执行代理',
}

const NODE_TYPE_COLORS: Record<string, string> = {
  requirement: '#a855f7',
  test_case: '#3b82f6',
  automation_case: '#06b6d4',
  task: '#f59e0b',
  case_result: '#f97316',
  agent: '#22c55e',
}

export default function EntityDetailModal({ node, onClose, onOpenLineage }: EntityDetailModalProps) {
  if (!node) return null

  const handleOpenLineage = () => {
    const typeMap: Record<string, string> = {
      requirement: 'requirement',
      test_case: 'test_case',
      automation_case: 'auto_case',
      task: 'task',
      case_result: 'case_result',
    }
    const apiType = typeMap[node.type] || node.type
    onOpenLineage(apiType, node.id)
    onClose()
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,0.3)',
      zIndex: 1000,
      display: 'flex',
      justifyContent: 'flex-end',
    }} onClick={onClose}>
      <div style={{
        width: 420,
        background: '#fff',
        height: '100%',
        overflow: 'auto',
        padding: 24,
        boxShadow: '-4px 0 24px rgba(0,0,0,0.1)',
      }} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 10, height: 10, borderRadius: '50%',
              background: NODE_TYPE_COLORS[node.type] || '#6b7280',
            }} />
            <span style={{ fontSize: 13, color: '#6b7280' }}>{NODE_TYPE_LABELS[node.type] || node.type}</span>
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: '#6b7280',
          }}>✕</button>
        </div>

        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 4 }}>{node.label}</h2>
        {node.subtitle && <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 24 }}>{node.subtitle}</p>}

        {/* Status badge */}
        {node.status && (
          <div style={{ marginBottom: 24 }}>
            <span style={{
              padding: '4px 12px', borderRadius: 12, fontSize: 12,
              background: node.status === 'PASSED' ? '#dcfce7' :
                          node.status === 'FAILED' ? '#fee2e2' :
                          node.status === 'RUNNING' ? '#dbeafe' : '#f3f4f6',
              color: node.status === 'PASSED' ? '#16a34a' :
                     node.status === 'FAILED' ? '#dc2626' :
                     node.status === 'RUNNING' ? '#2563eb' : '#6b7280',
              fontWeight: 500,
            }}>{node.status}</span>
          </div>
        )}

        {/* Meta fields */}
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: '#111827', marginBottom: 8 }}>详细信息</h3>
          <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
            <tbody>
              {Object.entries(node.meta).filter(([_, v]) => v !== null && v !== undefined && v !== '').map(([key, value]) => (
                <tr key={key} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '6px 0', color: '#6b7280', width: '40%' }}>{key}</td>
                  <td style={{ padding: '6px 0', color: '#111827' }}>
                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Open Lineage button */}
        <button onClick={handleOpenLineage} style={{
          width: '100%',
          padding: '10px 16px',
          borderRadius: 8,
          border: '1px solid #2563eb',
          background: '#dbeafe',
          color: '#2563eb',
          fontWeight: 500,
          fontSize: 13,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 6,
        }}>
          ◈ 从当前节点查看血缘
        </button>
      </div>
    </div>
  )
}
