import { useCallback, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
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

interface UseWorkflowOptions {
  loadLogs?: boolean;
}

export function useWorkflow(
  workflowItemId: string | null | undefined,
  options: UseWorkflowOptions = {},
): UseWorkflowResult {
  const { loadLogs = false } = options;
  const [transitioning, setTransitioning] = useState(false);
  const [reassigning, setReassigning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const transitionsQuery = useQuery({
    queryKey: ['workflow', workflowItemId, 'transitions'],
    queryFn: async () => {
      if (!workflowItemId) throw new Error('missing workflow item id');
      const response = await api.getWorkflowTransitions(workflowItemId);
      return response.data;
    },
    enabled: Boolean(workflowItemId),
    staleTime: 30_000,
  });

  const logsQuery = useQuery({
    queryKey: ['workflow', workflowItemId, 'logs'],
    queryFn: async () => {
      if (!workflowItemId) throw new Error('missing workflow item id');
      const response = await api.getWorkflowLogs(workflowItemId, 50);
      return response.data || [];
    },
    enabled: Boolean(workflowItemId) && loadLogs,
    staleTime: 30_000,
  });

  const refreshLogs = useCallback(async () => {
    if (!workflowItemId || !loadLogs) return;
    await logsQuery.refetch();
  }, [loadLogs, logsQuery, workflowItemId]);

  const refresh = useCallback(async () => {
    if (!workflowItemId) return;
    setError(null);
    const result = await transitionsQuery.refetch();
    if (result.error) {
      setError(result.error instanceof Error ? result.error.message : '获取工作流信息失败');
    }
  }, [transitionsQuery, workflowItemId]);

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
    currentState: transitionsQuery.data?.current_state || '',
    transitions: transitionsQuery.data?.available_transitions || [],
    logs: logsQuery.data || [],
    creator: transitionsQuery.data?.creator,
    currentOwner: transitionsQuery.data?.current_owner,
    loading: transitionsQuery.isFetching,
    logsLoading: logsQuery.isFetching,
    transitioning,
    reassigning,
    error: error || (transitionsQuery.error instanceof Error ? transitionsQuery.error.message : null),
    successMessage,
    refresh,
    refreshLogs,
    executeTransition,
    reassign,
    clearMessages,
  };
}
