import type { TestCaseResponse, AutomationTestCaseResponse, ExecutionStatsResponse } from '../../types';
import type { UnifiedCaseItem, DetailTab } from './testCaseBoardTypes';
import {
  getManualDot, getManualLabel, getAutoDot, getAutoLabel,
  PRIORITY_COLORS, fwIcon, fwColor,
} from './testCaseBoardTypes';
import { boardStyles as S } from './testCaseBoardStyles';
import TestCaseStepList from '../TestCaseStepList';
import { api } from '../../services/api';
import { useState, useCallback, useEffect } from 'react';

/* ═══════════════════════════════════════════════════════════════════
   Props
   ═══════════════════════════════════════════════════════════════════ */

interface TestCaseBoardDetailProps {
  item: UnifiedCaseItem | null;
  activeTab: DetailTab;
  onTabChange: (t: DetailTab) => void;
  onOpenDispatch: () => void;
  onRefresh: () => void;
}

/* ═══════════════════════════════════════════════════════════════════
   Shared Sub-components
   ═══════════════════════════════════════════════════════════════════ */

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div style={{ marginBottom: 20 }}>
    <span style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 10 }}>{title}</span>
    {children}
  </div>
);

const Field: React.FC<{ label: string; mono?: boolean; children: React.ReactNode }> = ({ label, mono, children }) => (
  <div>
    <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', display: 'block', marginBottom: 2 }}>{label}</span>
    <span style={{ fontSize: 13, color: 'var(--text-primary)', fontFamily: mono ? 'monospace' : undefined, wordBreak: 'break-word' }}>{children}</span>
  </div>
);

const SnapshotField: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div style={{ padding: '8px 12px', background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-muted)' }}>
    <span style={{ display: 'block', fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 2 }}>{label}</span>
    <span style={{ fontSize: 12, color: 'var(--text-primary)', fontFamily: 'monospace' }}>{value}</span>
  </div>
);

/* ═══════════════════════════════════════════════════════════════════
   Info Content Components
   ═══════════════════════════════════════════════════════════════════ */

const ManualInfoContent: React.FC<{ d: TestCaseResponse }> = ({ d }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
    <Section title="基本属性">
      <div style={S.grid2}>
        <Field label="目录">{d.catalog_breadcrumb || d.catalog_path?.join(' / ') || '-'}</Field>
        <Field label="Lab">{d.lab_name || d.lab_id || '-'}</Field>
        <Field label="负责人">{d.owner_id || '-'}</Field>
        <Field label="审核人">{d.reviewer_id || '-'}</Field>
        <Field label="优先级">{d.priority || '-'}</Field>
        <Field label="预估耗时">{d.estimated_duration_sec ? `${Math.round(d.estimated_duration_sec / 60)} 分钟` : '-'}</Field>
        <Field label="是否激活">{d.is_active ? '\u2705 是' : '\u274C 否'}</Field>
        <Field label="是否需要自动化">{d.is_need_auto ? '\u2705 是' : '\u274C 否'}</Field>
      </div>
    </Section>
    {d.tags?.length > 0 && (
      <Section title="标签">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {d.tags.map((t, i) => (
            <span key={i} style={S.tagPill}>{t}</span>
          ))}
        </div>
      </Section>
    )}
    {d.ref_req_id && (
      <Section title="关联需求">
        <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-muted)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 16 }}>{'\uD83D\uDCD0'}</span>
          <span style={{ fontSize: 13, fontFamily: 'monospace', color: 'var(--accent-cyan)', fontWeight: 600 }}>{d.ref_req_id}</span>
        </div>
      </Section>
    )}
  </div>
);

const ManualStepsContent: React.FC<{ d: TestCaseResponse }> = ({ d }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
    {d.pre_condition && <Section title="前置条件"><div style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.6, padding: 12, background: 'var(--bg-secondary)', borderRadius: 8 }}>{d.pre_condition}</div></Section>}
    {d.steps?.length ? (
      <Section title={`测试步骤 (${d.steps.length})`}>
        <TestCaseStepList steps={d.steps} />
      </Section>
    ) : (
      <Section title="测试步骤"><p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>暂无步骤</p></Section>
    )}
    {d.post_condition && <Section title="后置条件"><div style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.6, padding: 12, background: 'var(--bg-secondary)', borderRadius: 8 }}>{d.post_condition}</div></Section>}
  </div>
);

const ManualMetaContent: React.FC<{ d: TestCaseResponse }> = ({ d }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
    <Section title="审计">
      <div style={S.grid2}>
        <Field label="创建时间" mono>{new Date(d.created_at).toLocaleString('zh-CN')}</Field>
        <Field label="更新时间" mono>{new Date(d.updated_at).toLocaleString('zh-CN')}</Field>
        <Field label="变更日志">{d.change_log || '-'}</Field>
        <Field label="废弃原因">{d.deprecation_reason || '-'}</Field>
      </div>
    </Section>
    <Section title="高级属性">
      <div style={S.grid2}>
        <Field label="风险等级">{d.risk_level || '-'}</Field>
        <Field label="保密级别">{d.confidentiality || '-'}</Field>
        <Field label="可见范围">{d.visibility_scope || '-'}</Field>
        <Field label="测试类别">{d.test_category || '-'}</Field>
        <Field label="是否破坏性">{d.is_destructive ? '\u2705 是' : '\u274C 否'}</Field>
      </div>
    </Section>
  </div>
);

const AutoInfoContent: React.FC<{ d: AutomationTestCaseResponse }> = ({ d }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
    <Section title="基本属性">
      <div style={S.grid2}>
        <Field label="框架">{d.framework || '-'}</Field>
        <Field label="自动化类型">{d.automation_type || '-'}</Field>
        <Field label="维护人">{d.maintainer_id || '-'}</Field>
        <Field label="审核人">{d.reviewer_id || '-'}</Field>
      </div>
    </Section>
    {d.description && (
      <Section title="描述">
        <div style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.6, padding: 12, background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-muted)' }}>{d.description}</div>
      </Section>
    )}
    {d.tags?.length > 0 && (
      <Section title="标签">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {d.tags.map((t, i) => (
            <span key={i} style={S.tagPill}>{t}</span>
          ))}
        </div>
      </Section>
    )}
  </div>
);

const AutoCodeContent: React.FC<{ d: AutomationTestCaseResponse }> = ({ d }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
    <Section title="仓库">
      <div style={S.grid2}>
        <Field label="地址" mono>{d.repo_url || '-'}</Field>
        <Field label="分支" mono>{d.repo_branch || '-'}</Field>
        <Field label="脚本路径" mono>{d.script_path || '-'}</Field>
        <Field label="脚本名称">{d.script_name || '-'}</Field>
        <Field label="脚本实体 ID" mono>{d.script_entity_id || '-'}</Field>
        <Field label="执行命令" mono>{d.entry_command || '-'}</Field>
      </div>
    </Section>
    {d.code_snapshot && (
      <Section title="代码快照">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          <SnapshotField label="分支" value={d.code_snapshot.branch || '-'} />
          <SnapshotField label="Commit" value={(d.code_snapshot.commit_short_id || d.code_snapshot.commit_id || '-').slice(0, 12)} />
          <SnapshotField label="作者" value={d.code_snapshot.author || '-'} />
          <SnapshotField label="提交时间" value={d.code_snapshot.commit_time ? new Date(d.code_snapshot.commit_time).toLocaleString('zh-CN') : '-'} />
        </div>
        {d.code_snapshot.message && (
          <div style={{ marginTop: 8, padding: '8px 12px', background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-muted)' }}>
            <span style={{ display: 'block', fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 4 }}>提交信息</span>
            <pre style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', fontFamily: 'monospace', lineHeight: 1.5 }}>{d.code_snapshot.message}</pre>
          </div>
        )}
      </Section>
    )}
    {d.script_ref && (
      <Section title="脚本引用">
        <div style={S.grid2}>
          <Field label="实体 ID" mono>{d.script_ref.entity_id || '-'}</Field>
          <Field label="模块">{d.script_ref.module || '-'}</Field>
          <Field label="项目标签">{d.script_ref.project_tag || '-'}</Field>
          <Field label="项目范围">{d.script_ref.project_scope || '-'}</Field>
        </div>
      </Section>
    )}
  </div>
);

const AutoParamsContent: React.FC<{ d: AutomationTestCaseResponse }> = ({ d }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
    {d.param_spec?.length ? (
      <Section title={`配置参数 (${d.param_spec.length})`}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {d.param_spec.map((p, i) => (
            <div key={i} style={{ padding: '10px 12px', background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-muted)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 13, fontWeight: 600, fontFamily: 'monospace', color: 'var(--accent-purple)' }}>{p.name}</span>
                {p.label && <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{p.label}</span>}
                <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--accent-cyan)', padding: '2px 6px', borderRadius: 4, background: 'rgba(57,208,214,0.15)' }}>{p.type}</span>
                {p.required && <span style={{ fontSize: 10, color: 'var(--accent-red)', fontWeight: 600, padding: '2px 6px', borderRadius: 4, background: 'rgba(219,68,68,0.15)' }}>必填</span>}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <div><span style={S.miniLabel}>默认值</span><span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-primary)' }}>{p.default !== undefined ? String(p.default) : '-'}</span></div>
                {p.description && <div style={{ gridColumn: '1/-1' }}><span style={S.miniLabel}>描述</span><span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{p.description}</span></div>}
              </div>
            </div>
          ))}
        </div>
      </Section>
    ) : null}
    {d.runtime_env && Object.keys(d.runtime_env).length > 0 && (
      <Section title={`运行环境 (${Object.keys(d.runtime_env).length})`}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 8 }}>
          {Object.entries(d.runtime_env).map(([k, v]) => (
            <div key={k} style={{ padding: '8px 10px', background: 'var(--bg-secondary)', borderRadius: 6, border: '1px solid var(--border-muted)' }}>
              <span style={{ display: 'block', fontSize: 11, fontFamily: 'monospace', color: 'var(--accent-purple)', fontWeight: 500, marginBottom: 2 }}>{k}</span>
              <span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-primary)', wordBreak: 'break-all' }}>{String(v)}</span>
            </div>
          ))}
        </div>
      </Section>
    )}
    {(!d.param_spec?.length && (!d.runtime_env || Object.keys(d.runtime_env).length === 0)) && (
      <p style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', padding: 32, margin: 0 }}>暂无配置参数与运行环境</p>
    )}
  </div>
);

const AutoRelationsContent: React.FC<{ d: AutomationTestCaseResponse }> = ({ d }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
    <Section title="关联链路">
      <div style={S.relationChain}>
        <div style={S.relationNode}>
          <span style={S.relationIcon}>{'\u26A1'}</span>
          <div>
            <span style={S.relationLabel}>自动化用例</span>
            <span style={S.relationValue}>{d.auto_case_id}</span>
          </div>
        </div>
        <span style={S.relationArrow}>{'\u2192'}</span>
        <div style={{ ...S.relationNode, ...(d.linked_manual_case_id ? {} : { opacity: 0.4 }) }}>
          <span style={S.relationIcon}>{'\uD83D\uDCCB'}</span>
          <div>
            <span style={S.relationLabel}>手工用例</span>
            {d.linked_manual_case_id ? (
              <span style={S.relationValue}>{d.linked_manual_case_id}</span>
            ) : (
              <span style={{ fontSize: 12, color: 'var(--text-tertiary)', fontStyle: 'italic' }}>未关联</span>
            )}
          </div>
        </div>
        <span style={S.relationArrow}>{'\u2192'}</span>
        <div style={{ ...S.relationNode, opacity: d.linked_manual_case_id ? 0.65 : 0.3 }}>
          <span style={S.relationIcon}>{'\uD83D\uDCD0'}</span>
          <div>
            <span style={S.relationLabel}>关联需求</span>
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)', fontStyle: 'italic' }}>
              {d.linked_manual_case_id ? '通过手工用例关联' : '待关联手工用例'}
            </span>
          </div>
        </div>
      </div>
    </Section>
  </div>
);

const AutoMetaContent: React.FC<{ d: AutomationTestCaseResponse }> = ({ d }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
    <Section title="时间">
      <div style={S.grid2}>
        <Field label="创建时间" mono>{new Date(d.created_at).toLocaleString('zh-CN')}</Field>
        <Field label="更新时间" mono>{new Date(d.updated_at).toLocaleString('zh-CN')}</Field>
      </div>
    </Section>
  </div>
);

/* ═══════════════════════════════════════════════════════════════════
   Manual Detail Panel
   ═══════════════════════════════════════════════════════════════════ */

const ManualDetailPanel: React.FC<{
  item: UnifiedCaseItem;
  activeTab: DetailTab;
  onTabChange: (t: DetailTab) => void;
  tabs: { id: DetailTab; label: string }[];
}> = ({ item, activeTab, onTabChange, tabs }) => {
  const d = item.manualData!;
  const dotColor = getManualDot(d.status);

  return (
    <>
      <div style={S.detailHeader}>
        <div style={S.detailHeaderMeta}>
          <span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--accent-purple)', fontWeight: 500 }}>{d.case_id}</span>
          <span style={{ fontSize: 11, padding: '1px 8px', borderRadius: 6, background: 'rgba(163,113,247,0.15)', color: '#a371f7', fontWeight: 600 }}>{'\uD83D\uDCCB'} 手工用例</span>
          <span style={S.statusDot(dotColor)} />
          <span style={{ fontSize: 12, color: dotColor, fontWeight: 600 }}>{getManualLabel(d.status)}</span>
          {d.priority && <span style={{ fontSize: 11, color: PRIORITY_COLORS[d.priority] || '#d29922', fontWeight: 600 }}>{d.priority}</span>}
          <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-tertiary)', padding: '1px 6px', borderRadius: 4, background: 'var(--surface-tertiary)' }}>v{d.version}</span>
          {d.ref_req_id && <span style={{ fontSize: 11, color: 'var(--accent-cyan)' }}>{'\uD83D\uDCD0'} {d.ref_req_id}</span>}
        </div>
        <h2 style={S.detailTitle}>{d.title}</h2>
      </div>

      {tabs.length > 1 && (
        <div style={S.detailTabBar}>
          {tabs.map(t => (
            <button key={t.id} type="button" style={S.detailTab(activeTab === t.id)} onClick={() => onTabChange(t.id)}>{t.label}</button>
          ))}
        </div>
      )}

      <div style={S.detailBody}>
        {activeTab === 'info' && <ManualInfoContent d={d} />}
        {activeTab === 'steps' && <ManualStepsContent d={d} />}
        {activeTab === 'meta' && <ManualMetaContent d={d} />}
        {activeTab === 'stats' && <StatsContent caseId={d.case_id} />}
      </div>
    </>
  );
};

/* ═══════════════════════════════════════════════════════════════════
   Auto Detail Panel
   ═══════════════════════════════════════════════════════════════════ */

const AutoDetailPanel: React.FC<{
  item: UnifiedCaseItem;
  activeTab: DetailTab;
  onTabChange: (t: DetailTab) => void;
  tabs: { id: DetailTab; label: string }[];
  onOpenDispatch: () => void;
  onRefresh: () => void;
}> = ({ item, activeTab, onTabChange, tabs, onOpenDispatch, onRefresh }) => {
  const d = item.autoData!;
  const dotColor = getAutoDot(d.status);

  return (
    <>
      <div style={S.detailHeader}>
        <div style={S.detailHeaderMeta}>
          <span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--accent-purple)', fontWeight: 500 }}>{d.auto_case_id}</span>
          {d.framework && (
            <span style={{ fontSize: 11, padding: '1px 8px', borderRadius: 6, background: `${fwColor(d.framework)}18`, color: fwColor(d.framework), fontWeight: 600 }}>
              {fwIcon(d.framework)} {d.framework}
            </span>
          )}
          <span style={{ fontSize: 11, padding: '1px 8px', borderRadius: 6, background: 'rgba(57,208,214,0.15)', color: '#39d0d6', fontWeight: 600 }}>{'\u26A1'} 自动化</span>
          <span style={S.statusDot(dotColor)} />
          <span style={{ fontSize: 12, color: dotColor, fontWeight: 600 }}>{getAutoLabel(d.status)}</span>
          <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-tertiary)', padding: '1px 6px', borderRadius: 4, background: 'var(--surface-tertiary)' }}>v{d.version}</span>
          {d.automation_type && <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{d.automation_type}</span>}
          <div style={{ flex: 1 }} />
          <button className="btn btn--primary btn--sm" onClick={onOpenDispatch}>{'\u25B6'} 下发执行</button>
          <button className="btn btn--ghost btn--sm" onClick={onRefresh}>{'\u21BB'}</button>
        </div>
        <h2 style={S.detailTitle}>{d.name}</h2>
      </div>

      {tabs.length > 1 && (
        <div style={S.detailTabBar}>
          {tabs.map(t => (
            <button key={t.id} type="button" style={S.detailTab(activeTab === t.id)} onClick={() => onTabChange(t.id)}>{t.label}</button>
          ))}
        </div>
      )}

      <div style={S.detailBody}>
        {activeTab === 'info' && <AutoInfoContent d={d} />}
        {activeTab === 'code' && <AutoCodeContent d={d} />}
        {activeTab === 'params' && <AutoParamsContent d={d} />}
        {activeTab === 'relations' && <AutoRelationsContent d={d} />}
        {activeTab === 'meta' && <AutoMetaContent d={d} />}
        {activeTab === 'stats' && <StatsContent caseId={d.auto_case_id} isAuto />}
      </div>
    </>
  );
};

/* ═══════════════════════════════════════════════════════════════════
   Execution Stats
   ═══════════════════════════════════════════════════════════════════ */

const StatsContent: React.FC<{ caseId: string; isAuto?: boolean }> = ({ caseId, isAuto }) => {
  const [data, setData] = useState<ExecutionStatsResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.getCaseExecutionStats(caseId)
      .then(res => setData(res.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [caseId]);

  if (loading) {
    return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>加载中...</div>;
  }
  if (!data) {
    return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>暂无执行数据</div>;
  }

  // 近 10 次执行结果柱状条（绿色通过 / 红色失败）
  const recentResults = [...data.recent].reverse().slice(-10);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* 统计卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8 }}>
        {[
          { label: '总次数', value: data.total, color: '#3b82f6' },
          { label: '通过', value: data.passed, color: '#16a34a' },
          { label: '失败', value: data.failed, color: '#dc2626' },
          { label: '通过率', value: `${data.pass_rate}%`, color: data.pass_rate >= 80 ? '#16a34a' : '#d97706' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{
            background: 'var(--bg-secondary)', borderRadius: 10, padding: '14px 16px',
            border: '1px solid var(--border-muted)', textAlign: 'center',
          }}>
            <div style={{ fontSize: 22, fontWeight: 700, color, lineHeight: 1.2 }}>{value}</div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* 最近执行趋势 */}
      {recentResults.length > 0 && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>最近执行趋势（近 {recentResults.length} 次）</div>
          <div style={{ display: 'flex', gap: 3, alignItems: 'flex-end', height: 40 }}>
            {recentResults.map((r, i) => (
              <div key={r.result_id || i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                <div style={{
                  width: '100%', height: r.passed ? 28 : 28, borderRadius: 3,
                  background: r.passed ? '#16a34a' : '#dc2626',
                  opacity: 0.85,
                  transition: 'opacity 0.15s',
                }} title={r.passed ? '通过' : '失败'} />
                <span style={{ fontSize: 8, color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}>
                  {r.executed_at ? new Date(r.executed_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit' }) : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 最近执行记录 */}
      {data.recent.length > 0 && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>最近执行记录</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {data.recent.slice(0, 10).map((r) => (
              <div key={r.result_id} style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '8px 12px', background: 'var(--bg-secondary)',
                borderRadius: 8, border: '1px solid var(--border-muted)',
                fontSize: 12, color: 'var(--text-primary)',
              }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', flexShrink: 0, background: r.passed ? '#16a34a' : '#dc2626' }} />
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.notes || (r.passed ? '通过' : '失败')}
                </span>
                <span style={{ color: 'var(--text-tertiary)', whiteSpace: 'nowrap' }}>
                  {new Date(r.executed_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                </span>
                <span style={{ color: 'var(--text-tertiary)', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 11 }}>
                  {r.executed_by}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.last_executed_at && (
        <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
          最近执行：{new Date(data.last_executed_at).toLocaleString('zh-CN')}
        </div>
      )}
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════════
   Main Detail Component
   ═══════════════════════════════════════════════════════════════════ */

const TestCaseBoardDetail: React.FC<TestCaseBoardDetailProps> = ({
  item,
  activeTab,
  onTabChange,
  onOpenDispatch,
  onRefresh,
}) => {
  if (!item) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)', fontSize: 14, gap: 8 }}>
        {'\u2190'} 从左侧选择一个用例查看详情
      </div>
    );
  }

  /* Compute tabs */
  const isManual = item.type === 'manual';
  const allTabs: { id: DetailTab; label: string; show: boolean }[] = [
    { id: 'info', label: '基本信息', show: true },
    { id: 'steps', label: '测试步骤', show: isManual && Boolean((item.manualData?.steps?.length ?? 0) > 0 || (item.manualData?.pre_condition || item.manualData?.post_condition)) },
    { id: 'code', label: '代码与脚本', show: !isManual },
    { id: 'params', label: '参数与环境', show: !isManual && Boolean(item.autoData?.param_spec?.length || (item.autoData?.runtime_env && Object.keys(item.autoData.runtime_env).length > 0)) },
    { id: 'relations', label: '关联', show: !isManual },
    { id: 'workflow', label: '工作流', show: isManual && Boolean(item.manualData?.workflow_item_id) },
    { id: 'stats', label: '执行统计', show: true },
    { id: 'meta', label: '元数据', show: true },
  ];
  const tabs = allTabs.filter(t => t.show);

  if (isManual) {
    return (
      <ManualDetailPanel item={item} activeTab={activeTab} onTabChange={onTabChange} tabs={tabs} />
    );
  }

  return (
    <AutoDetailPanel item={item} activeTab={activeTab} onTabChange={onTabChange} tabs={tabs} onOpenDispatch={onOpenDispatch} onRefresh={onRefresh} />
  );
};

export default TestCaseBoardDetail;
