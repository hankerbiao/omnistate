/** 测试血缘图谱页面 - SVG DAG 渲染 */
import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { api } from '../../services/api'
import { getLineageMockData } from './lineageMockData'
import type { LineageNode, LineageEdge, LineageGraphResponse } from '../../types'
import EntityDetailModal from './EntityDetailModal'

const NODE_WIDTH = 180
const NODE_HEIGHT = 72
const LAYER_GAP = 72
const NODE_GAP = 20
const TYPE_COLORS: Record<string, string> = {
  requirement: '#a855f7',
  test_case: '#3b82f6',
  automation_case: '#06b6d4',
  task: '#f59e0b',
  case_result: '#f97316',
  agent: '#22c55e',
}

const STATUS_COLORS: Record<string, string> = {
  PASSED: '#22c55e',
  FAILED: '#ef4444',
  RUNNING: '#3b82f6',
  QUEUED: '#eab308',
  SKIPPED: '#6b7280',
  ERROR: '#ef4444',
  ACTIVE: '#22c55e',
  ONLINE: '#22c55e',
  OFFLINE: '#6b7280',
  DRAFT: '#6b7280',
}

const TYPE_LABELS: Record<string, string> = {
  requirement: '需求',
  test_case: '用例',
  automation_case: '自动',
  task: '任务',
  case_result: '结果',
  agent: '代理',
}

interface LayoutNode {
  node: LineageNode
  x: number
  y: number
}

function computeLayout(nodes: LineageNode[], edges: LineageEdge[], rootId: string) {
  // BFS from root to assign layers
  const adjacency = new Map<string, string[]>()
  for (const edge of edges) {
    if (!adjacency.has(edge.source)) adjacency.set(edge.source, [])
    if (!adjacency.has(edge.target)) adjacency.set(edge.target, [])
    adjacency.get(edge.source)!.push(edge.target)
    adjacency.get(edge.target)!.push(edge.source)
  }

  const nodeIds = new Set(nodes.map(n => n.id))
  const layers = new Map<number, string[]>() // layer → node ids
  const visited = new Set<string>()
  const queue: Array<{ id: string; layer: number }> = [{ id: rootId, layer: 0 }]
  visited.add(rootId)

  while (queue.length > 0) {
    const { id, layer } = queue.shift()!
    if (!layers.has(layer)) layers.set(layer, [])
    layers.get(layer)!.push(id)
    ;(adjacency.get(id) || []).forEach(neighbor => {
      if (!visited.has(neighbor) && nodeIds.has(neighbor)) {
        visited.add(neighbor)
        queue.push({ id: neighbor, layer: layer + 1 })
      }
    })
  }

  // Handle unvisited nodes (disconnected components)
  nodes.forEach(n => {
    if (!visited.has(n.id)) {
      const maxLayer = Math.max(...Array.from(layers.keys()), -1)
      if (!layers.has(maxLayer + 1)) layers.set(maxLayer + 1, [])
      layers.get(maxLayer + 1)!.push(n.id)
      visited.add(n.id)
    }
  })

  const nodeMap = new Map(nodes.map(n => [n.id, n]))
  const positions = new Map<string, { x: number; y: number }>()
  let totalHeight = 0

  const sortedLayers = Array.from(layers.entries()).sort(([a], [b]) => a - b)

  for (const [, layerNodes] of sortedLayers) {
    const layerHeight = layerNodes.length * (NODE_HEIGHT + NODE_GAP) - NODE_GAP
    const startY = totalHeight + (layerNodes.length > 1 ? 0 : NODE_HEIGHT / 2)
    
    layerNodes.forEach((nodeId, idx) => {
      const y = startY + idx * (NODE_HEIGHT + NODE_GAP)
      positions.set(nodeId, { x: (sortedLayers.length - 1) === 0 ? 0 : 0, y })
      // Initially all nodes are at x=0 (layer 0), we'll realign below
    })
    totalHeight += Math.max(layerHeight, NODE_HEIGHT) + LAYER_GAP
  }

  // Assign x positions based on layer index
  let maxWidth = 0
  for (let i = 0; i < sortedLayers.length; i++) {
    const layerX = i * (NODE_WIDTH + LAYER_GAP)
    sortedLayers[i][1].forEach(nodeId => {
      const pos = positions.get(nodeId)
      if (pos) pos.x = layerX
    })
    maxWidth = layerX + NODE_WIDTH
  }

  return {
    positions: Array.from(positions.entries()).map(([id, pos]) => ({
      node: nodeMap.get(id)!,
      x: pos.x,
      y: pos.y,
    })),
    totalWidth: maxWidth + LAYER_GAP,
    totalHeight: Math.max(totalHeight, 400),
    sortedLayers: sortedLayers.map(([l, ids]) => ({ layer: l, nodeIds: ids })),
  }
}

function EdgePath({ source, target, sourcePos, targetPos }: {
  source: string; target: string
  sourcePos: { x: number; y: number }
  targetPos: { x: number; y: number }
}) {
  const sx = sourcePos.x + NODE_WIDTH
  const sy = sourcePos.y + NODE_HEIGHT / 2
  const tx = targetPos.x
  const ty = targetPos.y + NODE_HEIGHT / 2
  const cx = (sx + tx) / 2

  return (
    <path
      d={`M${sx},${sy} C${cx},${sy} ${cx},${ty} ${tx},${ty}`}
      fill="none"
      stroke="#d1d5db"
      strokeWidth={1.5}
      markerEnd="url(#arrowhead)"
    />
  )
}

function NodeCard({ node, x, y, onClick }: { node: LineageNode; x: number; y: number; onClick: () => void }) {
  const statusColor = STATUS_COLORS[node.status || ''] || '#6b7280'
  const typeColor = TYPE_COLORS[node.type] || '#6b7280'

  return (
    <foreignObject x={x} y={y} width={NODE_WIDTH} height={NODE_HEIGHT}>
      <div
        onClick={onClick}
        style={{
          width: NODE_WIDTH - 4,
          height: NODE_HEIGHT - 4,
          background: '#fff',
          border: `1px solid ${typeColor}40`,
          borderLeft: `4px solid ${typeColor}`,
          borderRadius: 8,
          padding: '8px 10px',
          cursor: 'pointer',
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          transition: 'box-shadow 0.15s',
          fontFamily: 'IBM Plex Sans, sans-serif',
        }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)' }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = '0 1px 3px rgba(0,0,0,0.08)' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: statusColor, flexShrink: 0,
          }} />
          <span style={{
            fontSize: 12, fontWeight: 500, color: '#111827',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>{node.label}</span>
        </div>
        {node.subtitle && (
          <span style={{ fontSize: 10, color: '#9ca3af', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {node.subtitle}
          </span>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <span style={{
            fontSize: 9, padding: '1px 6px', borderRadius: 8,
            background: `${typeColor}18`, color: typeColor, fontWeight: 500,
          }}>{TYPE_LABELS[node.type] || node.type}</span>
        </div>
      </div>
    </foreignObject>
  )
}

interface LineageViewPageProps {
  entityType: string
  entityId: string
}

export default function LineageViewPage({ entityType, entityId }: LineageViewPageProps) {
  const [data, setData] = useState<LineageGraphResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<LineageNode | null>(null)
  const [zoom, setZoom] = useState(0.85)
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!entityType || !entityId) return
    setLoading(true)
    setError(null)
    api.getLineageGraph(entityType, entityId)
      .then(res => { setData(res.data) })
      .catch(err => {
        console.warn('API unavailable, using mock data:', err)
        setData(getLineageMockData(entityType, entityId))
      })
      .finally(() => setLoading(false))
  }, [entityType, entityId])

  const layout = useMemo(() => {
    if (!data) return null
    return computeLayout(data.nodes, data.edges, data.root_id)
  }, [data])

  const handleNodeClick = useCallback((node: LineageNode) => {
    setSelectedNode(node)
  }, [])

  const handleOpenLineageAgain = useCallback((type: string, id: string) => {
    setSelectedNode(null)
    setLoading(true)
    api.getLineageGraph(type, id)
      .then(res => { setData(res.data) })
      .catch(err => { setError(err instanceof Error ? err.message : '加载失败') })
      .finally(() => setLoading(false))
  }, [])

  // Build quick edge lookup for rendering
  const edgeSet = useMemo(() => {
    if (!data) return new Set<string>()
    const s = new Set<string>()
    data.edges.forEach(e => s.add(`${e.source}->${e.target}`))
    return s
  }, [data])

  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        <div style={{ textAlign: 'center', padding: 60, color: '#9ca3af' }}>加载血缘图谱...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <div style={{ textAlign: 'center', padding: 60, color: '#ef4444' }}>加载失败：{error}</div>
      </div>
    )
  }

  if (!data || !layout) {
    return (
      <div style={{ padding: 24 }}>
        <div style={{ textAlign: 'center', padding: 60, color: '#9ca3af' }}>未找到血缘数据</div>
      </div>
    )
  }

  const types = [...new Set(data.nodes.map(n => n.type))]
  const rootNode = data.nodes.find(n => n.id === data.root_id)

  return (
    <div style={{ padding: 24 }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 16,
      }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>
            测试血缘图谱
          </div>
          <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>
            从 {data.root_type} [{data.root_id}] {rootNode?.label || ''} 开始追溯
            · 共 {data.nodes.length} 个节点 · {data.edges.length} 条关系
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* Legend */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 11 }}>
            {Object.entries(TYPE_COLORS).filter(([t]) => types.includes(t)).map(([type, color]) => (
              <span key={type} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
                {TYPE_LABELS[type] || type}
              </span>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <button onClick={() => setZoom(z => Math.min(z + 0.1, 2))} style={zoomBtnStyle}>+</button>
            <button onClick={() => setZoom(z => Math.max(z - 0.1, 0.3))} style={zoomBtnStyle}>−</button>
            <button onClick={() => setZoom(0.85)} style={zoomBtnStyle}>重置</button>
          </div>
        </div>
      </div>

      {/* SVG Canvas */}
      <div style={{
        border: '1px solid #e5e7eb',
        borderRadius: 10,
        background: '#fafafa',
        overflow: 'auto',
        height: 'calc(100vh - 200px)',
        minHeight: 400,
      }}>
        <svg
          ref={svgRef}
          width={layout.totalWidth * zoom + 60}
          height={layout.totalHeight * zoom + 60}
          style={{ display: 'block' }}
        >
          <defs>
            <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill="#9ca3af" />
            </marker>
          </defs>
          <g transform={`translate(20, 20) scale(${zoom})`}>
            {/* Edges */}
            {data.edges.map((edge, i) => {
              const src = layout.positions.find(p => p.node.id === edge.source)
              const tgt = layout.positions.find(p => p.node.id === edge.target)
              if (!src || !tgt) return null
              return (
                <EdgePath
                  key={`edge-${i}`}
                  source={edge.source}
                  target={edge.target}
                  sourcePos={{ x: src.x, y: src.y }}
                  targetPos={{ x: tgt.x, y: tgt.y }}
                />
              )
            })}
            {/* Nodes */}
            {layout.positions.map(({ node, x, y }) => (
              <NodeCard key={node.id} node={node} x={x} y={y} onClick={() => handleNodeClick(node)} />
            ))}
          </g>
        </svg>
      </div>

      {/* Detail modal */}
      {selectedNode && (
        <EntityDetailModal
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
          onOpenLineage={handleOpenLineageAgain}
        />
      )}
    </div>
  )
}

const zoomBtnStyle: React.CSSProperties = {
  padding: '6px 12px',
  borderRadius: 6,
  border: '1px solid #d1d5db',
  background: '#fff',
  cursor: 'pointer',
  fontSize: 13,
  color: '#374151',
  lineHeight: 1,
}
