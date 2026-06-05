/** 测试用例字段中文标签（变更记录展示） */
export const TEST_CASE_FIELD_LABELS: Record<string, string> = {
  title: '标题',
  lab_id: '所属 Lab',
  catalog_path: '分类目录',
  ref_req_id: '关联需求',
  owner_id: '负责人',
  reviewer_id: '审核人',
  auto_dev_id: '自动化开发',
  version: '版本号',
  is_active: '是否激活',
  change_log: '版本说明',
  priority: '优先级',
  estimated_duration_sec: '预估耗时(秒)',
  required_env: '运行环境',
  tags: '标签',
  test_category: '测试类别',
  is_destructive: '破坏性测试',
  pre_condition: '前置条件',
  post_condition: '后置条件',
  risk_level: '风险等级',
  failure_analysis: '失败分析',
  confidentiality: '机密等级',
  visibility_scope: '可见范围',
  attachments: '附件',
  custom_fields: '自定义字段',
  deprecation_reason: '废弃原因',
  steps: '执行步骤',
  cleanup_steps: '清理步骤',
  is_deleted: '已删除',
  automation_link: '自动化关联',
};

export const CHANGE_LOG_ACTION_LABELS: Record<string, string> = {
  CREATE: '创建',
  UPDATE: '更新内容',
  ASSIGN_OWNERS: '分配负责人',
  MOVE_REQUIREMENT: '变更关联需求',
  LINK_AUTOMATION: '关联自动化',
  DELETE: '删除',
};

export function formatChangeValue(field: string, value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return '（空）';
  }
  if (field === 'catalog_path' && Array.isArray(value)) {
    return value.join(' / ');
  }
  if (field === 'tags' && Array.isArray(value)) {
    return value.length ? value.join(', ') : '（空）';
  }
  if ((field === 'steps' || field === 'cleanup_steps') && Array.isArray(value)) {
    if (value.length === 0) return '（空）';
    const names = value
      .map((item) => (typeof item === 'object' && item !== null && 'name' in item ? String((item as { name?: string }).name || '') : ''))
      .filter(Boolean);
    if (names.length > 0) {
      const preview = names.slice(0, 3).join('、');
      return names.length > 3 ? `共 ${value.length} 步（${preview}…）` : `共 ${value.length} 步（${preview}）`;
    }
    return `共 ${value.length} 步`;
  }
  if (field === 'is_active' || field === 'is_destructive' || field === 'is_deleted') {
    return value ? '是' : '否';
  }
  if (field === 'automation_link' && typeof value === 'object' && value !== null) {
    const v = value as { auto_case_id?: string; version?: string };
    return [v.auto_case_id, v.version ? `v${v.version}` : ''].filter(Boolean).join(' · ');
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value, null, 0);
    } catch {
      return String(value);
    }
  }
  return String(value);
}
