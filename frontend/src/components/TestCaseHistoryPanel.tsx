import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import type { TestCaseChangeLog, WorkflowTransitionLog } from '../types';
import { ChangeLogTimeline, changeLogPanelStyles } from './TestCaseChangeLogPanel';
import { WorkflowLogsTimeline } from './workflow/WorkflowLogsPanel';
import type { WorkflowTypeCode } from '../constants/workflowLabels';

type HistoryTab = 'changes' | 'workflow';

interface TestCaseHistoryPanelProps {
  caseId: string;
  workflowItemId?: string | null;
  typeCode?: WorkflowTypeCode;
  /** 外部递增时刷新（如编辑保存或流转成功后） */
  refreshSignal?: number;
}

const TestCaseHistoryPanel: React.FC<TestCaseHistoryPanelProps> = ({
  caseId,
  workflowItemId,
  typeCode = 'TEST_CASE',
  refreshSignal = 0,
}) => {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<HistoryTab>('changes');

  const [changesLoaded, setChangesLoaded] = useState(false);
  const [changesLoading, setChangesLoading] = useState(false);
  const [changesError, setChangesError] = useState<string | null>(null);
  const [changeLogs, setChangeLogs] = useState<TestCaseChangeLog[]>([]);
  const [changeTotal, setChangeTotal] = useState(0);
  const [openEntryId, setOpenEntryId] = useState<string | null>(null);

  const [workflowLoaded, setWorkflowLoaded] = useState(false);
  const [workflowLoading, setWorkflowLoading] = useState(false);
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [workflowLogs, setWorkflowLogs] = useState<WorkflowTransitionLog[]>([]);

  const hasWorkflowTab = Boolean(workflowItemId);

  const fetchChangeLogs = useCallback(async () => {
    if (!caseId) return;
    setChangesLoading(true);
    setChangesError(null);
    try {
      const res = await api.getTestCaseChangeLogs(caseId, { limit: 50, offset: 0 });
      const data = res.data;
      const items = data?.items || [];
      setChangeLogs(items);
      setChangeTotal(data?.total ?? 0);
      setChangesLoaded(true);
      setOpenEntryId((prev) => prev ?? items[0]?.id ?? null);
    } catch (err) {
      console.error(err);
      setChangesError('加载字段变更失败');
    } finally {
      setChangesLoading(false);
    }
  }, [caseId]);

  const fetchWorkflowLogs = useCallback(async () => {
    if (!workflowItemId) return;
    setWorkflowLoading(true);
    setWorkflowError(null);
    try {
      const res = await api.getWorkflowLogs(workflowItemId, 50);
      setWorkflowLogs(res.data || []);
      setWorkflowLoaded(true);
    } catch (err) {
      console.error(err);
      setWorkflowError('加载状态流转失败');
    } finally {
      setWorkflowLoading(false);
    }
  }, [workflowItemId]);

  const loadTab = useCallback((tab: HistoryTab) => {
    if (tab === 'changes' && !changesLoaded) {
      void fetchChangeLogs();
    }
    if (tab === 'workflow' && hasWorkflowTab && !workflowLoaded) {
      void fetchWorkflowLogs();
    }
  }, [changesLoaded, workflowLoaded, fetchChangeLogs, fetchWorkflowLogs, hasWorkflowTab]);

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    const next = !open;
    setOpen(next);
    if (next) {
      loadTab(activeTab);
    }
  };

  const handleTabChange = (tab: HistoryTab) => {
    setActiveTab(tab);
    loadTab(tab);
  };

  useEffect(() => {
    if (!open || refreshSignal <= 0) return;
    if (activeTab === 'changes' && changesLoaded) {
      void fetchChangeLogs();
    }
    if (activeTab === 'workflow' && workflowLoaded) {
      void fetchWorkflowLogs();
    }
  }, [refreshSignal, open, activeTab, changesLoaded, workflowLoaded, fetchChangeLogs, fetchWorkflowLogs]);

  useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  const badgeCount = (changesLoaded ? changeTotal : 0) + (workflowLoaded ? (workflowLogs?.length ?? 0) : 0);
  const showBadge = (changesLoaded || workflowLoaded) && badgeCount > 0;

  const refreshActiveTab = () => {
    if (activeTab === 'changes') {
      void fetchChangeLogs();
    } else {
      void fetchWorkflowLogs();
    }
  };

  const activeMeta = activeTab === 'changes'
    ? (changesLoaded && !changesLoading ? `${changeTotal} 条` : null)
    : (workflowLoaded && !workflowLoading ? `${workflowLogs?.length ?? 0} 条` : null);

  const activeLoading = activeTab === 'changes'
    ? changesLoading && !changesLoaded
    : workflowLoading && !workflowLoaded;

  const activeError = activeTab === 'changes' ? changesError : workflowError;

  return (
    <div style={changeLogPanelStyles.wrap} ref={wrapRef} onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        className={`btn btn--ghost btn--sm${open ? ' btn--active' : ''}`}
        style={changeLogPanelStyles.triggerBtn}
        onClick={handleToggle}
        title="查看历史记录"
        aria-expanded={open}
      >
        历史
        {showBadge && (
          <span style={changeLogPanelStyles.badge}>{badgeCount}</span>
        )}
      </button>

      {open && (
        <div style={changeLogPanelStyles.popover} role="dialog" aria-label="历史记录">
          <div style={changeLogPanelStyles.popoverHeader}>
            <span style={changeLogPanelStyles.popoverTitle}>历史</span>
            {activeMeta && (
              <span style={changeLogPanelStyles.popoverMeta}>{activeMeta}</span>
            )}
            <button
              type="button"
              style={changeLogPanelStyles.refreshBtn}
              onClick={refreshActiveTab}
              disabled={activeTab === 'changes' ? changesLoading : workflowLoading}
              title="刷新"
            >
              ↻
            </button>
          </div>

          <div style={styles.tabBar}>
            <button
              type="button"
              style={{
                ...styles.tab,
                ...(activeTab === 'changes' ? styles.tabActive : {}),
              }}
              onClick={() => handleTabChange('changes')}
            >
              字段变更
              {changesLoaded && changeTotal > 0 && (
                <span style={styles.tabBadge}>{changeTotal}</span>
              )}
            </button>
            {hasWorkflowTab && (
              <button
                type="button"
                style={{
                  ...styles.tab,
                  ...(activeTab === 'workflow' ? styles.tabActive : {}),
                }}
                onClick={() => handleTabChange('workflow')}
              >
                状态流转
                {workflowLoaded && (workflowLogs?.length ?? 0) > 0 && (
                  <span style={styles.tabBadge}>{workflowLogs?.length}</span>
                )}
              </button>
            )}
          </div>

          <div style={changeLogPanelStyles.popoverBody}>
            {activeError && <div style={changeLogPanelStyles.error}>{activeError}</div>}
            {activeLoading ? (
              <div style={changeLogPanelStyles.loading}>
                <div className="loading-spinner" style={{ width: 22, height: 22 }} />
              </div>
            ) : activeTab === 'changes' ? (
              changeLogs.length === 0 ? (
                <p style={changeLogPanelStyles.empty}>
                  暂无字段变更（自功能上线后的编辑将自动记录）
                </p>
              ) : (
                <ChangeLogTimeline
                  logs={changeLogs}
                  openEntryId={openEntryId}
                  onToggleEntry={(id) => setOpenEntryId((prev) => (prev === id ? null : id))}
                />
              )
            ) : (
              <WorkflowLogsTimeline
                logs={workflowLogs || []}
                loading={workflowLoading && !workflowLoaded}
                typeCode={typeCode}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  tabBar: {
    display: 'flex',
    gap: 4,
    padding: '8px 12px 0',
    borderBottom: '1px solid var(--border-muted)',
    backgroundColor: 'var(--bg-secondary)',
    flexShrink: 0,
  },
  tab: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 12px',
    fontSize: 12,
    fontWeight: 500,
    color: 'var(--text-muted)',
    background: 'none',
    border: 'none',
    borderBottom: '2px solid transparent',
    cursor: 'pointer',
    marginBottom: -1,
  },
  tabActive: {
    color: 'var(--text-primary)',
    borderBottom: '2px solid var(--accent-primary)',
    fontWeight: 600,
  },
  tabBadge: {
    fontSize: 10,
    fontWeight: 600,
    padding: '1px 5px',
    borderRadius: 999,
    backgroundColor: 'var(--surface-tertiary)',
    color: 'var(--text-secondary)',
  },
};

export default TestCaseHistoryPanel;
