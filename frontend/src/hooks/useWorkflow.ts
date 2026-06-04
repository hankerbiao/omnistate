import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import type { WorkflowTransition, WorkflowTransitionLog } from '../types';

export interface UseWorkflowResult {
  currentState: string;
  transitions: WorkflowTransition[];
  logs: WorkflowTransitionLog[];
  creator?: string;
  currentOwner?: string;
  loading: boolean;
  logsLoading: boolean;
  transitioning: boolean;
  reassigning: boolean;
  error: string | null;
  successMessage: string | null;
  refresh: () => Promise<void>;
  refreshLogs: () => Promise<void>;
  executeTransition: (action: string, formData: Record<string, string>) => Promise<boolean>;
  reassign: (targetOwnerId: string, remark?: string) => Promise<boolean>;
  clearMessages: () => void;
}

export function useWorkflow(workflowItemId: string | null | undefined): UseWorkflowResult {
  const [currentState, setCurrentState] = useState('');
  const [transitions, setTransitions] = useState<WorkflowTransition[]>([]);
  const [logs, setLogs] = useState<WorkflowTransitionLog[]>([]);
  const [creator, setCreator] = useState<string>();
  const [currentOwner, setCurrentOwner] = useState<string>();
  const [loading, setLoading] = useState(false);
  const [logsLoading, setLogsLoading] = useState(false);
  const [transitioning, setTransitioning] = useState(false);
  const [reassigning, setReassigning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const refreshLogs = useCallback(async () => {
    if (!workflowItemId) {
      setLogs([]);
      return;
    }
    setLogsLoading(true);
    try {
      const response = await api.getWorkflowLogs(workflowItemId, 50);
      setLogs(response.data || []);
    } catch (err) {
      console.error('Fetch workflow logs error:', err);
    } finally {
      setLogsLoading(false);
    }
  }, [workflowItemId]);

  const refresh = useCallback(async () => {
    if (!workflowItemId) {
      setCurrentState('');
      setTransitions([]);
      setCreator(undefined);
      setCurrentOwner(undefined);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await api.getWorkflowTransitions(workflowItemId);
      setCurrentState(response.data.current_state);
      setTransitions(response.data.available_transitions || []);
      setCreator(response.data.creator);
      setCurrentOwner(response.data.current_owner);
    } catch (err) {
      setCurrentState('');
      setTransitions([]);
      setError(err instanceof Error ? err.message : '获取工作流信息失败');
    } finally {
      setLoading(false);
    }
  }, [workflowItemId]);

  useEffect(() => {
    refresh();
    refreshLogs();
  }, [refresh, refreshLogs]);

  const executeTransition = useCallback(
    async (action: string, formData: Record<string, string>): Promise<boolean> => {
      if (!workflowItemId) return false;
      setTransitioning(true);
      setError(null);
      setSuccessMessage(null);
      try {
        const response = await api.transitionWorkflow(workflowItemId, { action, form_data: formData });
        const data = response.data;
        setSuccessMessage(
          `流转成功：${data.from_state} → ${data.to_state}（${action}）`,
        );
        await refresh();
        await refreshLogs();
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : '工作流流转失败');
        return false;
      } finally {
        setTransitioning(false);
      }
    },
    [workflowItemId, refresh, refreshLogs],
  );

  const reassign = useCallback(
    async (targetOwnerId: string, remark?: string): Promise<boolean> => {
      if (!workflowItemId) return false;
      setReassigning(true);
      setError(null);
      setSuccessMessage(null);
      try {
        await api.reassignWorkItem(workflowItemId, targetOwnerId, remark);
        setSuccessMessage(`已改派给 ${targetOwnerId}`);
        await refresh();
        await refreshLogs();
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : '改派失败');
        return false;
      } finally {
        setReassigning(false);
      }
    },
    [workflowItemId, refresh, refreshLogs],
  );

  const clearMessages = useCallback(() => {
    setError(null);
    setSuccessMessage(null);
  }, []);

  return {
    currentState,
    transitions,
    logs,
    creator,
    currentOwner,
    loading,
    logsLoading,
    transitioning,
    reassigning,
    error,
    successMessage,
    refresh,
    refreshLogs,
    executeTransition,
    reassign,
    clearMessages,
  };
}
