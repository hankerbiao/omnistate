/**
 * useEnums — 系统枚举 Hook
 *
 * 从后端 GET /api/v1/enums 获取系统全部枚举值列表。
 * 展示样式（标签文本、颜色等）由前端各组件自行管理。
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import type { EnumMap } from '../types';

export function useEnums() {
  const { data, isLoading, error } = useQuery<EnumMap>({
    queryKey: ['enums'],
    queryFn: async () => {
      const res = await api.getAllEnums();
      return res.data as unknown as EnumMap;
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  return { enums: data ?? emptyEnumMap, isLoading, error };
}

export const emptyEnumMap: EnumMap = {
  workflow_states: [],
  owner_strategies: [],
  priority: [],
  requirement_category: [],
  requirement_source: [],
  automation_case_status: [],
  manual_case_status: [],
  confidentiality: [],
  visibility_scope: [],
  risk_level: [],
  test_category: [],
  execution_overall_status: [],
  execution_case_status: [],
  execution_dispatch_status: [],
  execution_schedule_status: [],
  execution_consume_status: [],
  execution_agent_status: [],
  execution_final_statuses: [],
  plan_item_status: [],
  plan_status: [],
  task_to_item_status: {},
  config_types: [],
  config_categories: [],
};
