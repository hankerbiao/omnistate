import axios from "axios";

const API_BASE = "http://10.2.50.30:8000/api/v1";

// 创建 axios 实例
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

// API 响应类型
export interface WorkType {
  code: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowState {
  code: string;
  name: string;
  is_end: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkflowConfig {
  id: number;
  type_code: string;
  from_state: string;
  action: string;
  to_state: string;
  target_owner_strategy: string;
  required_fields: string[];
  created_at: string;
  updated_at: string;
}

export interface WorkItem {
  id: number;
  type_code: string;
  title: string;
  content: string;
  current_state: string;
  current_owner_id: number | null;
  creator_id: number;
  created_at: string;
  updated_at: string;
}

export interface TransitionRequest {
  action: string;
  operator_id: number;
  form_data: Record<string, any>;
}

export interface TransitionResponse {
  work_item_id: number;
  from_state: string;
  to_state: string;
  action: string;
  new_owner_id: number | null;
  work_item: WorkItem;
}

export interface AvailableTransition {
  action: string;
  to_state: string;
  target_owner_strategy: string;
  required_fields: string[];
}

export interface AvailableTransitionsResponse {
  item_id: number;
  current_state: string;
  available_transitions: AvailableTransition[];
}

export interface TransitionLog {
  id: number;
  work_item_id: number;
  from_state: string;
  to_state: string;
  action: string;
  operator_id: number;
  payload: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// API 方法
export const workItemApi = {
  // 获取事项类型列表
  getTypes: async (): Promise<WorkType[]> => {
    const response = await api.get("/work-items/types");
    return response.data;
  },

  // 获取流程状态列表
  getStates: async (): Promise<WorkflowState[]> => {
    const response = await api.get("/work-items/states");
    return response.data;
  },

  // 获取指定类型的流转配置
  getConfigs: async (typeCode: string): Promise<WorkflowConfig[]> => {
    const response = await api.get("/work-items/configs", {
      params: { type_code: typeCode },
    });
    return response.data;
  },

  // 创建事项
  create: async (
    typeCode: string,
    title: string,
    content: string,
    creatorId: number,
    parentItemId?: string | number
  ): Promise<WorkItem> => {
    const response = await api.post("/work-items", {
      type_code: typeCode,
      title,
      content,
      creator_id: creatorId,
      parent_item_id: parentItemId ?? null,
    });
    return response.data;
  },

  // 获取事项列表
  list: async (filters?: {
    typeCode?: string;
    state?: string;
    ownerId?: number;
    creatorId?: number;
    limit?: number;
    offset?: number;
  }): Promise<WorkItem[]> => {
    const response = await api.get("/work-items", {
      params: {
        type_code: filters?.typeCode,
        state: filters?.state,
        owner_id: filters?.ownerId,
        creator_id: filters?.creatorId,
        limit: filters?.limit || 100,
        offset: filters?.offset || 0,
      },
    });
    return response.data;
  },

  sortedList: async (params?: {
    typeCode?: string;
    state?: string;
    ownerId?: number;
    creatorId?: number;
    limit?: number;
    offset?: number;
    orderBy?: "created_at" | "updated_at" | "title";
    direction?: "asc" | "desc";
  }): Promise<WorkItem[]> => {
    const response = await api.get("/work-items/sorted", {
      params: {
        type_code: params?.typeCode,
        state: params?.state,
        owner_id: params?.ownerId,
        creator_id: params?.creatorId,
        limit: params?.limit ?? 100,
        offset: params?.offset ?? 0,
        order_by: params?.orderBy ?? "created_at",
        direction: params?.direction ?? "desc",
      },
    });
    return response.data;
  },

  search: async (options: {
    keyword: string;
    typeCode?: string;
    state?: string;
    ownerId?: number;
    creatorId?: number;
    limit?: number;
    offset?: number;
  }): Promise<WorkItem[]> => {
    const response = await api.get("/work-items/search", {
      params: {
        keyword: options.keyword,
        type_code: options.typeCode,
        state: options.state,
        owner_id: options.ownerId,
        creator_id: options.creatorId,
        limit: options.limit ?? 100,
        offset: options.offset ?? 0,
      },
    });
    return response.data;
  },

  // 获取事项详情
  get: async (itemId: number): Promise<WorkItem> => {
    const response = await api.get(`/work-items/${itemId}`);
    return response.data;
  },

  listTestCasesForRequirement: async (
    requirementId: string | number
  ): Promise<WorkItem[]> => {
    const response = await api.get(`/work-items/${requirementId}/test-cases`);
    return response.data;
  },

  getRequirementForTestCase: async (
    testCaseId: string | number
  ): Promise<WorkItem | null> => {
    const response = await api.get(`/work-items/${testCaseId}/requirement`);
    return response.data;
  },

  // 执行状态流转
  transition: async (
    itemId: number,
    action: string,
    operatorId: number,
    formData: Record<string, any> = {}
  ): Promise<TransitionResponse> => {
    const response = await api.post(`/work-items/${itemId}/transition`, {
      action,
      operator_id: operatorId,
      form_data: formData,
    });
    return response.data;
  },

  // 获取可用流转动作
  getAvailableTransitions: async (
    itemId: number
  ): Promise<AvailableTransitionsResponse> => {
    const response = await api.get(`/work-items/${itemId}/transitions`);
    return response.data;
  },

  // 获取流转日志
  getLogs: async (itemId: number): Promise<TransitionLog[]> => {
    const response = await api.get(`/work-items/${itemId}/logs`);
    return response.data;
  },

  // 批量获取多个事项的流转日志
  batchGetLogs: async (itemIds: number[]): Promise<Record<number, TransitionLog[]>> => {
    const response = await api.get("/work-items/logs/batch", {
      params: {
        item_ids: itemIds.join(","),
        limit: 20,
      },
    });
    return response.data;
  },

  // 改派任务
  reassign: async (
    itemId: number,
    operatorId: number,
    targetOwnerId: number,
    remark?: string
  ): Promise<WorkItem> => {
    const response = await api.post(`/work-items/${itemId}/reassign`, null, {
      params: {
        operator_id: operatorId,
        target_owner_id: targetOwnerId,
        remark,
      },
    });
    return response.data;
  },

  // 删除任务
  delete: async (itemId: number): Promise<{ message: string; item_id: number }> => {
    const response = await api.delete(`/work-items/${itemId}`);
    return response.data;
  },
};

// 状态颜色映射
export const stateColors: Record<string, string> = {
  DRAFT: "#9ca3af",          // Gray 400
  PENDING_REVIEW: "#f59e0b", // Amber 500 (待评审)
  PENDING_AUDIT: "#f59e0b",  // 兼容旧数据
  PENDING_DEVELOP: "#ec4899",// Pink 500 (待开发)
  DEVELOPING: "#3b82f6",     // Blue 500 (开发中)
  PENDING_TEST: "#8b5cf6",   // Violet 500 (待测试)
  PENDING_UAT: "#f97316",    // Orange 500 (待验收)
  PENDING_RELEASE: "#06b6d4",// Cyan 500 (待上线)
  RELEASED: "#10b981",       // Emerald 500 (已上线)
  DONE: "#10b981",           // 兼容旧数据
  ASSIGNED: "#6366f1",       // Indigo 500
  REJECTED: "#ef4444",       // Red 500
};

// 状态中文映射
export const stateLabels: Record<string, string> = {
  DRAFT: "草稿",
  PENDING_AUDIT: "待审核",
  ASSIGNED: "已指派",
  DEVELOPING: "开发中",
  PENDING_REVIEW: "待评审",
  PENDING_DEVELOP: "待开发",
  PENDING_TEST: "待测试",
  PENDING_UAT: "待验收",
  PENDING_RELEASE: "待上线",
  RELEASED: "已上线",
  DONE: "已完成",
  REJECTED: "已拒绝",
};
