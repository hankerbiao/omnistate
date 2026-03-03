/**
 * @fileoverview 类型定义文件
 * 定义了测试需求管理系统的所有核心数据类型
 */

/**
 * 测试用例状态枚举
 * 定义测试用例的生命周期状态
 */
export enum TestCaseStatus {
  DRAFT = 'DRAFT',           // 草稿状态 - 刚创建或编辑中
  ASSIGNED = 'ASSIGNED',     // 已指派 - 已分配给开发人员
  DEVELOPING = 'DEVELOPING', // 开发中 - 正在实施测试
  PENDING_REVIEW = 'PENDING_REVIEW', // 待评审 - 待技术评审
  DONE = 'DONE',            // 已完成 - 测试执行完毕
}

/**
 * 优先级枚举
 * 用于标记需求或用例的重要性等级
 */
export enum Priority {
  P0 = 'P0',  // 最高优先级 - 关键功能，必须完成
  P1 = 'P1',  // 高优先级 - 重要功能，建议完成
  P2 = 'P2'   // 低优先级 - 一般功能，可延后
}

/**
 * 风险等级枚举
 * 标识测试用例执行的风险程度
 */
export enum RiskLevel {
  LOW = 'low',    // 低风险 - 标准测试操作
  MEDIUM = 'medium', // 中等风险 - 需谨慎操作
  HIGH = 'high'   // 高风险 - 可能影响系统稳定性
}

/**
 * 可见性范围枚举
 * 控制测试用例的可见性和访问权限
 */
export enum VisibilityScope {
  TEAM = 'team',     // 团队范围 - 仅团队成员可见
  PROJECT = 'project', // 项目范围 - 项目内可见
  GLOBAL = 'global'  // 全局范围 - 所有用户可见
}

/**
 * 测试步骤接口
 * 定义单个测试步骤的结构
 */
export interface TestStep {
  step_id: string;    // 步骤唯一标识符
  name: string;       // 步骤名称
  action: string;     // 具体操作步骤描述
  expected: string;   // 预期结果描述
}

/**
 * 审批记录接口
 * 记录需求或用例的审批历史
 */
export interface ApprovalRecord {
  approver: string;           // 审批人用户ID
  timestamp: string;          // 审批时间戳
  result: 'approved' | 'rejected' | 'commented'; // 审批结果
  comment: string;            // 审批意见或评论
}

/**
 * 测试用例分类枚举
 * 按测试类型对用例进行分类
 */
export enum TestCaseCategory {
  FUNCTIONAL = 'functional',   // 功能测试
  STRESS = 'stress',           // 压力测试
  PERFORMANCE = 'performance', // 性能测试
  COMPATIBILITY = 'compatibility', // 兼容性测试
  STABILITY = 'stability',     // 稳定性测试
  SECURITY = 'security'        // 安全测试
}

/**
 * 机密等级枚举
 * 控制测试内容的访问权限级别
 */
export enum Confidentiality {
  PUBLIC = 'public',     // 公开 - 无访问限制
  INTERNAL = 'internal', // 内部 - 仅内部员工可访问
  NDA = 'nda'           // 保密 - 需签署保密协议
}

/**
 * 测试需求状态枚举
 * 定义需求从创建到发布的完整生命周期
 */
export enum RequirementStatus {
  DRAFT = 'DRAFT',                 // 草稿 - 需求创建或编辑中
  PENDING_REVIEW = 'PENDING_REVIEW', // 待评审 - 等待技术评审
  PENDING_DEVELOP = 'PENDING_DEVELOP', // 待开发 - 评审通过，等待开发
  DEVELOPING = 'DEVELOPING',       // 开发中 - 正在开发实现
  PENDING_TEST = 'PENDING_TEST',   // 待测试 - 开发完成，等待测试
  PENDING_UAT = 'PENDING_UAT',     // 待验收 - 测试完成，等待用户验收
  PENDING_RELEASE = 'PENDING_RELEASE', // 待发布 - 验收完成，等待正式发布
  RELEASED = 'RELEASED',          // 已发布 - 需求已正式发布
}

/**
 * 测试需求接口
 * 定义服务器硬件测试需求的完整数据结构
 */
export interface TestRequirement {
  req_id: string;                    // 需求唯一标识符
  title: string;                     // 需求标题
  description?: string;              // 需求详细描述
  technical_spec?: string;           // 技术规格说明
  target_components: string[];       // 目标硬件组件列表（Memory、CPU、GPU等）
  firmware_version?: string;         // 目标固件版本
  priority: Priority;               // 需求优先级
  key_parameters: { key: string; value: string }[]; // 关键参数键值对
  risk_points?: string;             // 潜在风险点描述
  manual_dev_id?: string;           // 手动测试开发人员ID
  auto_dev_id?: string;             // 自动化测试开发人员ID
  current_owner_id?: string;        // 当前负责人ID
  status: RequirementStatus;        // 当前状态
  attachments: Attachment[];        // 附件列表
  created_at: string;               // 创建时间戳
  updated_at: string;               // 最后更新时间戳
}

/**
 * 附件接口
 * 定义文件附件的元数据信息
 */
export interface Attachment {
  id: string;                           // 附件唯一标识符
  name: string;                         // 文件名称
  type: 'image' | 'video' | 'spec' | 'log' | 'other'; // 文件类型
  url: string;                          // 文件访问地址
  size?: string;                        // 文件大小（可选）
  uploaded_at: string;                  // 上传时间戳
}

/**
 * 测试用例接口
 * 定义单个测试用例的完整信息结构
 */
export interface TestCase {
  case_id: string;                      // 用例唯一标识符
  ref_req_id: string;                   // 关联的需求ID
  title: string;                        // 用例标题
  test_category?: TestCaseCategory;     // 测试分类（功能、性能等）
  version: number;                      // 用例版本号
  is_active: boolean;                   // 是否激活状态
  change_log?: string;                  // 版本变更日志
  status: TestCaseStatus;               // 当前状态
  owner_id?: string;                    // 负责人用户ID
  reviewer_id?: string;                 // 评审人用户ID
  auto_dev_id?: string;                 // 自动化开发人员ID
  priority?: Priority;                  // 优先级（可选）
  estimated_duration_sec?: number;      // 预估执行时长（秒）
  target_components: string[];          // 目标组件列表
  required_env: {                       // 测试环境要求
    os?: string;                        // 操作系统版本
    firmware?: string;                  // 固件版本
    hardware?: string;                  // 硬件配置要求
    dependencies?: string[];            // 依赖组件列表
  };
  tags: string[];                       // 标签列表
  tooling_req: string[];                // 工具链要求
  pre_condition?: string;               // 前置条件
  post_condition?: string;              // 后置条件
  cleanup_steps: TestStep[];            // 清理步骤
  steps: TestStep[];                    // 测试步骤
  is_need_auto: boolean;                // 是否需要自动化
  is_automated: boolean;                // 是否已实现自动化
  is_destructive: boolean;              // 是否为破坏性测试
  automation_type?: string;             // 自动化类型
  script_entity_id?: string;            // 脚本实体ID
  risk_level?: RiskLevel;               // 风险等级（可选）
  visibility_scope?: VisibilityScope;   // 可见性范围（可选）
  confidentiality?: Confidentiality;    // 机密等级（可选）
  attachments: Attachment[];            // 附件列表
  custom_fields: Record<string, string>; // 自定义字段
  failure_analysis?: string;            // 失败分析记录
  deprecation_reason?: string;          // 废弃原因
  approval_history: ApprovalRecord[];   // 审批历史记录
  created_at: string;                   // 创建时间戳
  updated_at: string;                   // 最后更新时间戳
}

/**
 * 创建测试需求的负载类型
 * ⚠️ 重要说明：
 * - 不包含 status、created_at、updated_at 字段（由系统自动生成）
 * - ⚠️ 不包含 req_id 字段！前端绝对不能传递此字段，必须由后端自动生成以保证全局唯一性
 * - 即使尝试传递 req_id，后端也会忽略并重新生成
 */
export type CreateRequirementPayload = Omit<
  TestRequirement,
  'status' | 'created_at' | 'updated_at' | 'req_id'
>;

/**
 * 创建测试用例的负载类型
 * 创建时不需要传入status、created_at、updated_at字段
 */
export type CreateTestCasePayload = Omit<
  TestCase,
  'status' | 'created_at' | 'updated_at'
>;

/**
 * 测试用例详情页-快速创建用例负载
 * 用于“创建测试用例”弹窗提交基础信息并关联任务流
 */
export interface QuickCreateCasePayload {
  title: string;                        // 用例标题
  ref_req_id: string;                   // 关联需求ID
  owner_id: string;                     // 指派开发人
  reviewer_id?: string;                 // 评审人
  is_need_auto: boolean;                // 是否需要自动化
  auto_dev_id?: string;                 // 自动化负责人
  workflow_note?: string;               // 任务流备注
  planned_due_date?: string;            // 计划完成时间（YYYY-MM-DD）
  automation_case_id?: string;          // 自动化用例库ID（关联）
  automation_case_version?: string;     // 自动化用例版本
  source_case_id?: string;              // 来源测试用例ID（从详情页创建时回填）
}

// ========== 工作流相关类型定义 ==========

/**
 * 工作项类型枚举
 */
export enum WorkItemType {
  REQUIREMENT = 'REQUIREMENT',  // 需求
  TEST_CASE = 'TEST_CASE',      // 测试用例
}

/**
 * 工作项状态枚举
 */
export enum WorkItemState {
  DRAFT = 'DRAFT',                    // 草稿
  PENDING_REVIEW = 'PENDING_REVIEW',  // 待评审
  PENDING_DEVELOP = 'PENDING_DEVELOP', // 待开发
  DEVELOPING = 'DEVELOPING',          // 开发中
  PENDING_TEST = 'PENDING_TEST',      // 待测试
  PENDING_UAT = 'PENDING_UAT',        // 待验收
  PENDING_RELEASE = 'PENDING_RELEASE', // 待发布
  RELEASED = 'RELEASED',             // 已发布
  DONE = 'DONE',                     // 已完成
}

/**
 * 工作项接口
 * 定义工作流中业务事项的完整信息
 */
export interface WorkItem {
  item_id: string;              // 工作项唯一标识符
  type_code: WorkItemType;      // 类型代码（REQUIREMENT/TEST_CASE）
  title: string;                // 标题
  content?: string;             // 内容描述
  current_state: WorkItemState; // 当前状态
  current_owner_id: string;     // 当前负责人ID
  creator_id: string;           // 创建人ID
  parent_item_id?: string;      // 父事项ID（可选）
  is_deleted: boolean;          // 是否已删除
  form_data?: Record<string, any>; // 表单数据
  created_at: string;           // 创建时间
  updated_at: string;           // 更新时间
}

/**
 * 流转动作接口
 */
export interface TransitionAction {
  action: string;              // 动作代码（如SUBMIT, APPROVE等）
  label: string;               // 动作显示名称
  target_state: string;        // 目标状态
  required_fields?: string[];  // 必需字段列表
}

/**
 * 可用流转接口
 */
export interface AvailableTransition {
  action: string;              // 动作代码
  target_state: string;        // 目标状态
  label?: string;              // 动作标签
}

/**
 * 可用流转响应接口
 */
export interface AvailableTransitionsResponse {
  item_id: string;                           // 工作项ID
  current_state: string;                     // 当前状态
  available_transitions: AvailableTransition[]; // 可用流转列表
}

/**
 * 导航页面接口
 * 定义导航页面的完整数据结构
 */
export interface NavigationPage {
  view: string;              // 导航唯一标识（唯一索引）
  label: string;             // 导航展示名称
  permission?: string;       // 访问该导航所需权限码（可为空）
  description?: string;      // 导航说明
  order?: number;            // 排序（越小越靠前）
  is_active: boolean;        // 是否启用
  is_deleted: boolean;       // 逻辑删除标记
  created_at?: string;       // 创建时间
  updated_at?: string;       // 更新时间
}

/**
 * 资产部件字典接口（用于 DUT 设备录入时选择/维护部件）
 * 对应后端：CreateComponentRequest / ComponentResponse
 */
export interface AssetComponent {
  id?: string;                           // 文档ID（响应字段）
  part_number: string;                   // 唯一物料编号（PN）
  category: string;                      // 大类（必填）
  subcategory?: string;                  // 子类
  vendor?: string;                       // 厂商
  model?: string;                        // 型号
  revision?: string;                     // 修订版本
  form_factor?: string;                  // 外形规格
  interface_type?: string;               // 接口类型（如 PCIe）
  interface_gen?: string;                // 接口代际（如 Gen5）
  protocol?: string;                     // 协议（如 NVMe）
  attributes: Record<string, unknown>;   // 动态属性
  power_watt?: number;                   // 功耗（W）
  firmware_baseline?: string;            // 固件基线版本
  spec: Record<string, unknown>;         // 规格参数
  datasheet_url?: string;                // 数据手册地址
  lifecycle_status?: string;             // 生命周期状态
  aliases: string[];                     // 别名列表
  created_at?: string;                   // 创建时间（响应字段）
  updated_at?: string;                   // 更新时间（响应字段）
}

/**
 * DUT 服务器资产接口（用于 DUT 录入中心）
 * 对应后端：CreateDutRequest / DutResponse
 */
export interface DutAsset {
  id?: string;               // 文档ID（响应字段）
  asset_id: string;          // 资产编号或 SN（唯一）
  model: string;             // 服务器型号
  status: string;            // 设备状态
  owner_team?: string;       // 归属团队
  owner?: string;            // 机器负责人/使用者
  rack_location?: string;    // 机房/机柜/机位
  bmc_ip?: string;           // BMC IP
  bmc_port?: number;         // BMC 端口
  os_ip?: string;            // OS IP
  os_port?: number;          // OS 端口
  login_username?: string;   // 登录用户名
  login_password?: string;   // 登录密码
  health_status?: string;    // 健康状态
  notes?: string;            // 备注
  created_at?: string;       // 创建时间（响应字段）
  updated_at?: string;       // 更新时间（响应字段）
}
