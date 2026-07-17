/**
 * TMMS 服务器服务
 *
 * 下发自动化测试任务时，目标服务器的 BMC IP / 用户名 / 密码由「TMMS 服务」
 * 提供。本文件是该服务的边界封装：当前返回 Mock 数据，后续替换为真实接口即可，
 * 调用方（如 SingleDispatchModal 的服务器资源看板）无需改动。
 *
 * TODO: 替换为真实 TMMS 接口，例如 GET /tmms/server-resources
 */

export type ServerStatus = 'online' | 'offline' | 'maintenance';

export interface ServerResource {
  /** 资源唯一标识 */
  id: string;
  /** 主机名 */
  hostname: string;
  /** 目标 BMC IP 地址 */
  bmc_ip: string;
  /** BMC 用户名 */
  bmc_username: string;
  /** BMC 密码 */
  bmc_password: string;
  /** 机型 */
  model?: string;
  /** 机房 / 位置 */
  location?: string;
  /** 操作系统 */
  os?: string;
  /** 资源所属项目（用于看板按项目分类） */
  project?: string;
  /** 资源状态 */
  status: ServerStatus;
  /** 是否正在执行任务 / 被占用（Mock 数据，后续由 TMMS 提供实时状态） */
  in_use?: boolean;
  /** 当前占用任务信息（in_use 为 true 时有值） */
  current_task?: {
    /** 任务标识 */
    task_id: string;
    /** 任务名称 */
    name: string;
  };
}

const MOCK_SERVERS: ServerResource[] = [
  {
    id: 'srv-1001',
    hostname: 'node-bmc-01',
    bmc_ip: '10.28.13.101',
    bmc_username: 'bmcadmin',
    bmc_password: 'BMC@2024node01',
    model: 'Inspur NF5280M6',
    location: '天津·机房A-07',
    os: 'TencentOS 3.1',
    project: '潮白河项目',
    status: 'online',
  },
  {
    id: 'srv-1002',
    hostname: 'node-bmc-02',
    bmc_ip: '10.28.13.102',
    bmc_username: 'bmcadmin',
    bmc_password: 'BMC@2024node02',
    model: 'Inspur NF5280M6',
    location: '天津·机房A-08',
    os: 'TencentOS 3.1',
    project: '潮白河项目',
    status: 'online',
    in_use: true,
    current_task: { task_id: 'task-2207', name: '潮白河·夜间回归·批次A' },
  },
  {
    id: 'srv-1003',
    hostname: 'node-bmc-03',
    bmc_ip: '10.28.13.103',
    bmc_username: 'root',
    bmc_password: 'Root#bmc03!',
    model: 'H3C R4900 G5',
    location: '天津·机房B-12',
    os: 'openEuler 22.03',
    project: '潮白河项目',
    status: 'maintenance',
  },
  {
    id: 'srv-1004',
    hostname: 'node-bmc-04',
    bmc_ip: '10.28.14.104',
    bmc_username: 'bmcadmin',
    bmc_password: 'BMC@2024node04',
    model: 'Inspur NF5280M7',
    location: '天津·机房B-13',
    os: 'TencentOS 3.2',
    project: '蓟运河项目',
    status: 'offline',
  },
  {
    id: 'srv-1005',
    hostname: 'node-bmc-05',
    bmc_ip: '10.28.14.105',
    bmc_username: 'operator',
    bmc_password: 'Op$bmc05#2024',
    model: 'H3C R4900 G6',
    location: '天津·机房C-21',
    os: 'openEuler 24.03',
    project: '蓟运河项目',
    status: 'online',
  },
  {
    id: 'srv-1006',
    hostname: 'node-bmc-06',
    bmc_ip: '10.28.14.106',
    bmc_username: 'bmcadmin',
    bmc_password: 'BMC@2024node06',
    model: 'Inspur NF5280M7',
    location: '天津·机房C-22',
    os: 'TencentOS 3.2',
    project: '蓟运河项目',
    status: 'online',
    in_use: true,
    current_task: { task_id: 'task-3315', name: '蓟运河·接口压测·批次B' },
  },
  {
    id: 'srv-1007',
    hostname: 'node-bmc-07',
    bmc_ip: '10.28.15.107',
    bmc_username: 'root',
    bmc_password: 'Root#bmc07!',
    model: 'H3C R4900 G5',
    location: '天津·机房A-09',
    os: 'openEuler 22.03',
    project: '永定河项目',
    status: 'maintenance',
    in_use: true,
    current_task: { task_id: 'task-4402', name: '永定河·固件升级验证' },
  },
  {
    id: 'srv-1008',
    hostname: 'node-bmc-08',
    bmc_ip: '10.28.15.108',
    bmc_username: 'operator',
    bmc_password: 'Op$bmc08#2024',
    model: 'Inspur NF5280M6',
    location: '天津·机房B-14',
    os: 'TencentOS 3.1',
    project: '永定河项目',
    status: 'offline',
  },
];

/**
 * 拉取服务器资源列表（当前返回 Mock 数据，模拟 TMMS 服务返回）。
 * 后续替换为真实 TMMS 服务调用即可。
 */
export async function fetchServerResources(): Promise<ServerResource[]> {
  // 模拟网络延迟
  await new Promise((resolve) => setTimeout(resolve, 400));
  return MOCK_SERVERS.map((s) => ({ ...s }));
}

export const SERVER_STATUS_LABEL: Record<ServerStatus, string> = {
  online: '在线',
  offline: '离线',
  maintenance: '维护中',
};
