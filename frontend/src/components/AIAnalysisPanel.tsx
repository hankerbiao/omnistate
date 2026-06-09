import { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import type { TestCaseResponse, AutomationTestCaseResponse } from '../types';
import { getCaseStatusLabel } from './TestCaseBoard/testCaseBoardTypes';

// ═══════════════════════════════════════════════════════════════════════
//  类型
// ═══════════════════════════════════════════════════════════════════════

interface AIAnalysisPanelProps {
  caseIds: string[];
  autoCaseIds: string[];
  manualMap: Map<string, TestCaseResponse>;
  autoMap: Map<string, AutomationTestCaseResponse>;
}

type Severity = 'success' | 'warning' | 'danger' | 'info';

interface AnalysisFinding {
  severity: Severity;
  icon: string;
  title: string;
  detail: string;
}

interface AnalysisResult {
  findings: AnalysisFinding[];
  statusDist: { label: string; count: number; color: string }[];
  coverageRate: number;
  healthLabel: string;
  healthSeverity: Severity;
}

// ═══════════════════════════════════════════════════════════════════════
//  分析逻辑
// ═══════════════════════════════════════════════════════════════════════

const STATUS_COLORS: Record<string, string> = {
  active: '#22c55e',
  draft: '#f59e0b',
  deprecated: '#ef4444',
  review: '#3b82f6',
};

const DEFAULT_STATUS_COLOR = '#6b7280';

function analyze(
  caseIds: string[],
  autoCaseIds: string[],
  manualMap: Map<string, TestCaseResponse>,
  autoMap: Map<string, AutomationTestCaseResponse>,
): AnalysisResult {
  const findings: AnalysisFinding[] = [];
  const statusCount: Record<string, number> = {};

  const missingManual: string[] = [];
  const missingAuto: string[] = [];

  for (const id of caseIds) {
    if (!manualMap.has(id)) {
      missingManual.push(id);
    } else {
      const c = manualMap.get(id)!;
      statusCount[c.status] = (statusCount[c.status] || 0) + 1;
    }
  }

  for (const id of autoCaseIds) {
    if (!autoMap.has(id)) {
      missingAuto.push(id);
    } else {
      const c = autoMap.get(id)!;
      statusCount[c.status] = (statusCount[c.status] || 0) + 1;
    }
  }

  if (missingManual.length > 0) {
    findings.push({
      severity: 'danger', icon: '🗑',
      title: `${missingManual.length} 个手工用例在数据库已不存在`,
      detail: `ID: ${missingManual.slice(0, 5).join(', ')}${missingManual.length > 5 ? ` 等共 ${missingManual.length} 个` : ''}`,
    });
  }

  if (missingAuto.length > 0) {
    findings.push({
      severity: 'danger', icon: '🗑',
      title: `${missingAuto.length} 个自动化用例在数据库已不存在`,
      detail: `ID: ${missingAuto.slice(0, 5).join(', ')}${missingAuto.length > 5 ? ` 等共 ${missingAuto.length} 个` : ''}`,
    });
  }

  const withAutoRef = caseIds.filter(id => {
    const c = manualMap.get(id);
    return c?.is_automated || c?.automation_case_ref;
  });

  if (withAutoRef.length > 0) {
    findings.push({
      severity: 'info', icon: '🔗',
      title: `${withAutoRef.length} 个手工用例有关联的自动化用例`,
      detail: `这些用例已有自动化覆盖，建议关注自动化执行结果`,
    });
  }

  const deprecatedCount = statusCount['deprecated'] || 0;
  if (deprecatedCount > 0) {
    findings.push({
      severity: 'warning', icon: '⚠️',
      title: `${deprecatedCount} 个用例状态为"已废弃"`,
      detail: `建议从集合中移除已废弃的用例，避免执行时产生误报`,
    });
  }

  const draftCount = statusCount['draft'] || 0;
  if (draftCount > 0) {
    findings.push({
      severity: 'warning', icon: '📝',
      title: `${draftCount} 个用例状态为"草稿"`,
      detail: `草稿状态的用例可能尚未完成评审，加入集合可能导致执行结果不可靠`,
    });
  }

  const totalValid = caseIds.length + autoCaseIds.length;
  const totalMissing = missingManual.length + missingAuto.length;
  const coverageRate = totalValid > 0
    ? Math.round(((totalValid - totalMissing) / totalValid) * 100)
    : 0;

  const statusDist = Object.entries(statusCount)
    .sort((a, b) => b[1] - a[1])
    .map(([label, count]) => ({
      label: getCaseStatusLabel(label),
      count,
      color: STATUS_COLORS[label] || DEFAULT_STATUS_COLOR,
    }));

  let healthSeverity: Severity = 'success';
  let healthLabel = '健康';
  if (totalMissing > 0) {
    healthSeverity = 'danger';
    healthLabel = '需修复';
  } else if (deprecatedCount > 0 || draftCount > 0) {
    healthSeverity = 'warning';
    healthLabel = '需关注';
  }

  if (findings.length === 0 && totalValid > 0) {
    findings.push({
      severity: 'success', icon: '✅',
      title: '集合分析通过，未发现异常',
      detail: `共 ${totalValid} 个用例均有效可用`,
    });
  }

  if (totalValid === 0) {
    findings.push({
      severity: 'info', icon: '📋',
      title: '此集合暂无用例',
      detail: '添加用例后可以在此查看 AI 分析',
    });
    healthSeverity = 'info';
    healthLabel = '空集合';
  }

  return { findings, statusDist, coverageRate, healthLabel, healthSeverity };
}

// ═══════════════════════════════════════════════════════════════════════
//  组件 — 触发器按钮 + 弹出面板
// ═══════════════════════════════════════════════════════════════════════

const AIAnalysisPanel: React.FC<AIAnalysisPanelProps> = ({
  caseIds,
  autoCaseIds,
  manualMap,
  autoMap,
}) => {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);

  const result = useMemo(
    () => analyze(caseIds, autoCaseIds, manualMap, autoMap),
    [caseIds, autoCaseIds, manualMap, autoMap],
  );

  // 点击外部关闭
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (
        panelRef.current && !panelRef.current.contains(e.target as Node) &&
        btnRef.current && !btnRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const healthColorClass = `ai-trigger__dot--${result.healthSeverity}`;

  return (
    <div style={{ position: 'relative', display: 'inline-flex' }}>
      {/* 触发器按钮 */}
      <button
        ref={btnRef}
        type="button"
        className={`ai-trigger${open ? ' ai-trigger--active' : ''}`}
        onClick={() => setOpen(v => !v)}
        title="AI 分析"
      >
        <span className="ai-trigger__icon">✨</span>
        <span className="ai-trigger__text">AI 分析</span>
        <span className={`ai-trigger__dot ${healthColorClass}`} />
      </button>

      {/* 弹出面板 */}
      {open && (
        <div ref={panelRef} className="ai-popover">
          {/* 头部摘要 */}
          <div className="ai-popover__summary">
            <span className="ai-popover__health">{result.healthLabel}</span>
            <span className="ai-popover__sep">·</span>
            <span className="ai-popover__rate">覆盖率 {result.coverageRate}%</span>
          </div>

          {/* 状态分布条 */}
          {result.statusDist.length > 0 && (
            <>
              <div className="ai-popover__status-bar">
                {result.statusDist.map(s => (
                  <div key={s.label} className="ai-popover__status-seg" style={{ flex: s.count, backgroundColor: s.color }} title={`${s.label}: ${s.count}`} />
                ))}
              </div>
              <div className="ai-popover__status-legend">
                {result.statusDist.map(s => (
                  <span key={s.label} className="ai-popover__status-item">
                    <span className="ai-popover__status-dot" style={{ backgroundColor: s.color }} />
                    <span>{s.label}</span>
                    <span className="ai-popover__status-count">{s.count}</span>
                  </span>
                ))}
              </div>
            </>
          )}

          {/* 发现项 */}
          {result.findings.length > 0 && (
            <div className="ai-popover__findings">
              {result.findings.map((f, i) => (
                <div key={i} className={`ai-popover__finding ai-popover__finding--${f.severity}`}>
                  <span className="ai-popover__finding-icon">{f.icon}</span>
                  <div className="ai-popover__finding-text">
                    <span className="ai-popover__finding-title">{f.title}</span>
                    <span className="ai-popover__finding-detail">{f.detail}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AIAnalysisPanel;
