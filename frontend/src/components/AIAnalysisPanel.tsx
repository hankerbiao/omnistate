import { useState, useCallback } from 'react';
import { api } from '../services/api';
import type { CollectionAnalysisResult } from '../types';

interface AIAnalysisPanelProps {
  caseIds: string[];
  autoCaseIds: string[];
  collectionId: string;
}

// ── 样式常量 ────────────────────────────────────────────

const colors = {
  green: '#16a34a', greenBg: '#f0fdf4', greenBorder: '#bbf7d0',
  amber: '#d97706', amberBg: '#fffbeb',
  red: '#dc2626', redBg: '#fef2f2',
  blue: '#1d4ed8', blueBg: '#f0f7ff', blueBorder: '#dbeafe',
  gray: '#9ca3af', grayBg: '#f9fafb', grayBorder: '#f3f4f6',
  text: '#374151', textLight: '#6b7280',
} as const;

const CARD = { background: '#fff', borderRadius: 10, border: `1px solid ${colors.grayBorder}`, overflow: 'hidden' as const };
const CARD_HEADER = { display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', background: colors.grayBg, borderBottom: `1px solid ${colors.grayBorder}` };
const SUCCESS_MSG = { padding: '10px 14px', background: colors.greenBg, borderRadius: 8, border: `1px solid ${colors.greenBorder}`, fontSize: 13, color: colors.green };

const sectionLabels = { quality: '质量分析', redundancy: '冗余检测', coverage: '覆盖率分析' } as const;

// ── 工具函数 ────────────────────────────────────────────

function scoreLevel(score: number) {
  if (score >= 80) return { color: colors.green, bg: colors.greenBg, label: '优秀' };
  if (score >= 60) return { color: colors.amber, bg: colors.amberBg, label: '一般' };
  return { color: colors.red, bg: colors.redBg, label: '偏低' };
}

function severityDot(severity: string) {
  if (severity === 'critical') return colors.red;
  if (severity === 'warning') return colors.amber;
  return '#3b82f6';
}

// ── 子组件 ──────────────────────────────────────────────

const ScoreRing = ({ score, size = 68 }: { score: number; size?: number }) => {
  const { color } = scoreLevel(score);
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e5e7eb" strokeWidth={6} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={6}
          strokeDasharray={circ} strokeDashoffset={circ - (score / 100) * circ}
          strokeLinecap="round" style={{ transition: 'stroke-dashoffset 0.6s ease' }} />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: 18, fontWeight: 700, color, lineHeight: 1 }}>{score}</span>
        <span style={{ fontSize: 9, color: colors.gray, lineHeight: 1 }}>综合</span>
      </div>
    </div>
  );
};

const IssueItem = ({ severity, caseId, message }: { severity: string; caseId: string; message: string }) => (
  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '5px 0', borderBottom: `1px solid ${colors.grayBorder}` }}>
    <div style={{ width: 6, height: 6, borderRadius: '50%', background: severityDot(severity), marginTop: 6, flexShrink: 0 }} />
    <div style={{ fontSize: 13, lineHeight: 1.5, color: colors.text }}>
      {caseId && <code style={{ fontSize: 11, background: colors.grayBg, padding: '1px 5px', borderRadius: 3, marginRight: 4 }}>{caseId}</code>}
      {message}
    </div>
  </div>
);

const CardSection = ({ label, count, children, emptyMsg }: {
  label: string; count: number; children: React.ReactNode; emptyMsg?: string;
}) => count > 0 ? (
  <div style={CARD}>
    <div style={CARD_HEADER}>
      <span style={{ fontWeight: 600, fontSize: 13, color: colors.text }}>{label}</span>
      <span style={{ fontSize: 11, color: colors.gray }}>{count}</span>
    </div>
    <div style={{ padding: '4px 14px 8px' }}>{children}</div>
  </div>
) : (
  <div style={SUCCESS_MSG}>{emptyMsg}</div>
);

const SuccessBox = ({ text }: { text: string }) => (
  <div style={SUCCESS_MSG}>{text}</div>
);

// ── 主组件 ──────────────────────────────────────────────

const AIAnalysisPanel: React.FC<AIAnalysisPanelProps> = ({ caseIds, autoCaseIds, collectionId }) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CollectionAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.analyzeCollection(collectionId, ['quality', 'redundancy', 'coverage']);
      setResult(res.data);
    } catch (err: any) {
      setError(err.message || 'AI分析请求失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next && !result && !loading) handleAnalyze();
  };

  // 视图切换
  const renderBody = () => {
    if (loading) return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, padding: '48px 0' }}>
        <div className="loading-spinner" />
        <span style={{ fontSize: 13, color: colors.textLight }}>正在分析 {caseIds.length + autoCaseIds.length} 个用例...</span>
      </div>
    );
    if (error) return <div style={{ padding: 12, background: colors.redBg, borderRadius: 8, border: '1px solid #fecaca', fontSize: 13, color: colors.red }}>⚠ {error}</div>;
    if (!result) return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, padding: '48px 0', color: colors.gray }}>
        <div style={{ fontSize: 32, fontWeight: 200 }}>AI</div>
        <button type="button" className="btn btn--primary btn--sm" onClick={handleAnalyze}>开始分析</button>
      </div>
    );

    // 分析结果
    const dimCards = (['quality', 'redundancy', 'coverage'] as const).map(key => {
      const data = result[key];
      const { color, bg } = scoreLevel(data.score);
      return (
        <div key={key} style={{ flex: 1, background: bg, borderRadius: 8, padding: '8px 10px', textAlign: 'center' }}>
          <div style={{ fontSize: 11, color: colors.textLight, marginBottom: 2 }}>{sectionLabels[key]}</div>
          <div style={{ fontSize: 16, fontWeight: 700, color }}>{data.score}<span style={{ fontSize: 10, fontWeight: 400 }}>分</span></div>
        </div>
      );
    });

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* 综合评分 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, background: colors.grayBg, borderRadius: 10, padding: '14px 18px' }}>
          <ScoreRing score={result.overall_score} />
          {dimCards}
        </div>

        {/* 质量分析 */}
        <CardSection label="质量分析" count={`${result.quality.issues.length} 项问题`} emptyMsg="质量分析通过，未发现问题">
          {result.quality.issues.map((issue, i) => (
            <IssueItem key={i} severity={issue.severity} caseId={issue.case_id} message={issue.message} />
          ))}
        </CardSection>

        {/* 冗余检测 */}
        <CardSection label="冗余检测" count={`${result.redundancy.duplicates.length} 对`} emptyMsg="未检测到冗余用例">
          {result.redundancy.duplicates.map((dup, i) => (
            <div key={i}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 0', borderBottom: `1px solid ${colors.grayBorder}` }}>
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 4, fontSize: 13 }}>
                  <code style={{ fontSize: 11, background: colors.grayBg, padding: '1px 5px', borderRadius: 3 }}>{dup.case_id1}</code>
                  <span style={{ color: colors.gray }}>↔</span>
                  <code style={{ fontSize: 11, background: colors.grayBg, padding: '1px 5px', borderRadius: 3 }}>{dup.case_id2}</code>
                </div>
                <span style={{
                  fontSize: 11, fontWeight: 600, padding: '1px 6px', borderRadius: 4,
                  background: dup.similarity > 0.85 ? colors.redBg : colors.amberBg,
                  color: dup.similarity > 0.85 ? colors.red : colors.amber,
                }}>
                  {(dup.similarity * 100).toFixed(0)}%
                </span>
              </div>
              <div style={{ fontSize: 12, color: colors.textLight, marginTop: 4 }}>{dup.reason}</div>
            </div>
          ))}
        </CardSection>

        {/* 覆盖率分析 */}
        <CardSection label="覆盖率分析" count={`${result.coverage.gaps.length} 项盲区`} emptyMsg="覆盖率良好，未发现明显盲区">
          {result.coverage.gaps.map((gap, i) => (
            <div key={i} style={{ display: 'flex', gap: 6, padding: '5px 0', borderBottom: `1px solid ${colors.grayBorder}`, fontSize: 13, color: colors.text }}>
              <span style={{ color: colors.amber, flexShrink: 0 }}>!</span>
              {gap}
            </div>
          ))}
        </CardSection>

        {/* 改进建议 */}
        {result.recommendations.length > 0 && (
          <div style={{ padding: '12px 14px', background: colors.blueBg, borderRadius: 10, border: `1px solid ${colors.blueBorder}` }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: colors.blue, marginBottom: 6 }}>改进建议</div>
            {result.recommendations.map((rec, i) => (
              <div key={i} style={{ display: 'flex', gap: 6, padding: '3px 0', fontSize: 13, color: colors.text }}>
                <span style={{ color: '#3b82f6', flexShrink: 0 }}>•</span>
                {rec}
              </div>
            ))}
          </div>
        )}

        {/* 操作 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, paddingTop: 4 }}>
          <button type="button" className="btn btn--ghost btn--xs" onClick={() => setOpen(false)}>关闭</button>
          <button type="button" className="btn btn--secondary btn--xs" onClick={handleAnalyze} disabled={loading}>重新分析</button>
        </div>
      </div>
    );
  };

  return (
    <>
      <button type="button" className="btn btn--secondary btn--sm" onClick={toggle}>
        {loading ? '⏳ 分析中...' : 'AI 分析'}
      </button>

      {open && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 999 }} onClick={() => setOpen(false)}>
          <div onClick={e => e.stopPropagation()} style={{
            position: 'absolute', right: 24, top: 60, width: 520,
            background: '#fff', borderRadius: 12,
            boxShadow: '0 8px 30px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.06)',
            border: `1px solid ${colors.grayBorder}`,
            maxHeight: '80vh', overflow: 'hidden', display: 'flex', flexDirection: 'column',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px', borderBottom: `1px solid ${colors.grayBorder}` }}>
              <span style={{ fontSize: 14, fontWeight: 600 }}>AI 分析结果</span>
              <button type="button" onClick={() => setOpen(false)}
                style={{ background: 'none', border: 'none', fontSize: 18, color: colors.gray, cursor: 'pointer', padding: '0 4px', lineHeight: 1 }}>×</button>
            </div>
            <div style={{ padding: '14px 18px 16px', overflowY: 'auto' }}>
              {renderBody()}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default AIAnalysisPanel;
