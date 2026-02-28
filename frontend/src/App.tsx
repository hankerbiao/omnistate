import React, { useState, useCallback, useEffect } from 'react';
import {
  TestCase,
  TestCaseStatus,
  Priority,
  RiskLevel,
  VisibilityScope,
  TestStep,
  TestCaseCategory,
  Confidentiality,
  TestRequirement,
  RequirementStatus,
  Attachment
} from './types';
import { INITIAL_USERS, ROLES, User } from './constants/config';
import { useLocalAI } from './components/hooks/useLocalAI';
import { isBackendEnabled, testDesignerApi } from './services/api';
import { Login, ReqList, ReqForm, ReqDetail, CaseList, CaseForm, UserMgmt } from './components/views';
import {
  FileText,
  PlayCircle,
  User as UserIcon,
  LogIn,
  Mail,
  Calendar,
  Shield,
  X,
} from 'lucide-react';

type View = 'login' | 'req_list' | 'req_form' | 'req_detail' | 'case_list' | 'case_form' | 'user_mgmt';

export default function App() {
  // Auth state
  const [view, setView] = useState<View>('login');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [users, setUsers] = useState<User[]>(INITIAL_USERS);

  // Login form state
  const [loginForm, setLoginForm] = useState({ user_id: '', password: '', rememberMe: false });
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState('');

  // User management state
  const [showUserForm, setShowUserForm] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [newUser, setNewUser] = useState<Partial<User>>({ status: 'ACTIVE', role_ids: [] });

  // User profile popup state
  const [showUserProfile, setShowUserProfile] = useState(false);

  // Requirements state
  const [requirements, setRequirements] = useState<TestRequirement[]>([
    {
      req_id: 'TR-2026-001',
      title: '下一代服务器 DDR5 内存验证',
      description: '针对新一代服务器平台的 DDR5 内存进行全面的压力与兼容性验证，确保在高温高负载下的稳定性。',
      technical_spec: '符合 JEDEC DDR5 标准，支持 5600MT/s 速率。',
      target_components: ['Memory'],
      firmware_version: 'BIOS v2.1.0',
      priority: Priority.P0,
      key_parameters: [{ key: '电压', value: '1.1V' }, { key: '频率', value: '5600MT/s' }],
      risk_points: '重点验证高温下的 ECC 错误率。',
      tpm_owner_id: 'alice',
      manual_dev_id: 'zhang_san',
      status: RequirementStatus.DEVELOPING,
      attachments: [],
      created_at: '2026-01-15T08:00:00Z',
      updated_at: '2026-02-20T10:30:00Z'
    },
    {
      req_id: 'TR-2026-002',
      title: 'CPU 核心温度监控测试',
      description: '验证服务器 CPU 在高负载运行时的温度监控传感器准确性和过热保护机制。',
      technical_spec: '支持 Intel Xeon Scalable 3rd Gen，温度范围 25°C - 105°C，精度 ±2°C。',
      target_components: ['CPU', 'Thermal Sensor'],
      firmware_version: 'BMC v3.2.1',
      priority: Priority.P1,
      key_parameters: [{ key: '最高温度', value: '95°C' }, { key: '告警阈值', value: '85°C' }],
      risk_points: '需注意不同 CPU 型号的温度特性差异。',
      tpm_owner_id: 'bob',
      manual_dev_id: 'li_si',
      status: RequirementStatus.REVIEWING,
      attachments: [],
      created_at: '2026-01-20T09:00:00Z',
      updated_at: '2026-02-18T14:00:00Z'
    },
    {
      req_id: 'TR-2026-003',
      title: 'NVMe SSD 读写性能基准测试',
      description: '评估企业级 NVMe SSD 在不同工作负载下的顺序和随机读写性能。',
      technical_spec: 'PCIe 4.0 x4，顺序读取 ≥7000MB/s，顺序写入 ≥5000MB/s。',
      target_components: ['Storage', 'NVMe'],
      firmware_version: 'BIOS v2.1.0',
      priority: Priority.P1,
      key_parameters: [{ key: '块大小', value: '4K' }, { key: '队列深度', value: '32' }],
      risk_points: '长时间写入可能导致固态硬盘温度过高。',
      tpm_owner_id: 'alice',
      manual_dev_id: 'wang_wu',
      status: RequirementStatus.CLOSED,
      attachments: [],
      created_at: '2026-01-10T10:00:00Z',
      updated_at: '2026-02-15T16:00:00Z'
    },
    {
      req_id: 'TR-2026-004',
      title: '电源冗余 failover 测试',
      description: '验证双电源冗余系统在单电源故障时的自动切换能力和系统稳定性。',
      technical_spec: '支持 1+1 冗余，切换时间 <20ms，输入电压范围 100-240V AC。',
      target_components: ['Power Supply', 'PSU'],
      firmware_version: 'iDRAC v5.0.0',
      priority: Priority.P0,
      key_parameters: [{ key: '功率', value: '800W' }, { key: '效率', value: '94%' }],
      risk_points: '测试时需确保负载均衡配置正确。',
      tpm_owner_id: 'bob',
      manual_dev_id: 'zhang_san',
      status: RequirementStatus.PENDING,
      attachments: [],
      created_at: '2026-02-01T08:00:00Z',
      updated_at: '2026-02-01T08:00:00Z'
    },
    {
      req_id: 'TR-2026-005',
      title: '网络接口卡兼容性测试',
      description: '验证 100GbE 网卡在不同操作系统和驱动版本下的兼容性和性能。',
      technical_spec: '支持 Intel E810-CQDA2，PCIe 4.0 x16，兼容 Linux/Windows。',
      target_components: ['NIC', 'Network'],
      firmware_version: 'BIOS v2.2.0',
      priority: Priority.P2,
      key_parameters: [{ key: '带宽', value: '100Gbps' }, { key: '延迟', value: '<1μs' }],
      risk_points: '需测试多种驱动版本组合。',
      tpm_owner_id: 'alice',
      manual_dev_id: 'li_si',
      status: RequirementStatus.DEVELOPING,
      attachments: [],
      created_at: '2026-02-10T11:00:00Z',
      updated_at: '2026-02-22T09:00:00Z'
    }
  ]);
  const [selectedReq, setSelectedReq] = useState<TestRequirement | null>(null);

  // Test cases state
  const [testCases, setTestCases] = useState<TestCase[]>([
    {
      case_id: 'TC-2026-001',
      ref_req_id: 'TR-2026-001',
      title: 'DDR5 内存稳定性压力测试',
      test_category: TestCaseCategory.STRESS,
      version: 2,
      is_active: true,
      change_log: '增加高温测试场景，优化测试步骤。',
      status: TestCaseStatus.APPROVED,
      owner_id: 'zhang_san',
      reviewer_id: 'bob',
      priority: Priority.P0,
      estimated_duration_sec: 28800,
      target_components: ['Memory'],
      required_env: { os: 'RHEL 8.6', firmware: 'BIOS v2.1.0', hardware: '2U Server' },
      tags: ['DDR5', '压力测试', '高温'],
      pre_condition: '服务器已完成 BIOS 配置，内存条安装完整。',
      post_condition: '恢复默认 BIOS 设置，清理测试数据。',
      cleanup_steps: [],
      steps: [
        { step_id: 'step-1', name: '系统启动', action: '开机进入 BIOS，配置内存频率为 5600MT/s', expected: '系统正常启动，无 POST 错误' },
        { step_id: 'step-2', name: '运行 memtester', action: '执行 memtester 8G 4', expected: '无 ECC 错误报告' },
        { step_id: 'step-3', name: '高温压力测试', action: '使用烤箱将环境温度升至 45°C，运行 memtester 24小时', expected: '错误率 < 0.01%' }
      ],
      is_need_auto: true,
      is_destructive: false,
      automation_type: 'Shell Script',
      script_entity_id: 'auto-ddr5-stress-001',
      risk_level: RiskLevel.MEDIUM,
      visibility_scope: VisibilityScope.PROJECT,
      confidentiality: Confidentiality.INTERNAL,
      attachments: [],
      custom_fields: {},
      approval_history: [{ approver: 'bob', timestamp: '2026-02-15T10:00:00Z', result: 'approved', comment: '测试用例设计合理，通过审批。' }],
      created_at: '2026-01-20T08:00:00Z',
      updated_at: '2026-02-15T10:00:00Z'
    },
    {
      case_id: 'TC-2026-002',
      ref_req_id: 'TR-2026-001',
      title: 'DDR5 内存兼容性测试',
      test_category: TestCaseCategory.COMPATIBILITY,
      version: 1,
      is_active: true,
      change_log: '初始版本创建。',
      status: TestCaseStatus.REVIEW,
      owner_id: 'zhang_san',
      reviewer_id: 'bob',
      priority: Priority.P1,
      estimated_duration_sec: 14400,
      target_components: ['Memory'],
      required_env: { os: 'Windows Server 2022', firmware: 'BIOS v2.1.0' },
      tags: ['DDR5', '兼容性'],
      pre_condition: '准备不同厂商的 DDR5 内存模组。',
      post_condition: '恢复系统配置。',
      cleanup_steps: [],
      steps: [
        { step_id: 'step-1', name: '安装内存', action: '安装 Samsung DDR5 32GB x 4', expected: '系统识别到 128GB' },
        { step_id: 'step-2', name: '更换内存', action: '更换为 Micron DDR5 32GB x 4', expected: '系统识别到 128GB' }
      ],
      is_need_auto: false,
      is_destructive: false,
      automation_type: '',
      script_entity_id: '',
      risk_level: RiskLevel.LOW,
      visibility_scope: VisibilityScope.TEAM,
      confidentiality: Confidentiality.PUBLIC,
      attachments: [],
      custom_fields: {},
      approval_history: [],
      created_at: '2026-02-01T08:00:00Z',
      updated_at: '2026-02-01T08:00:00Z'
    },
    {
      case_id: 'TC-2026-003',
      ref_req_id: 'TR-2026-002',
      title: 'CPU 温度传感器精度验证',
      test_category: TestCaseCategory.FUNCTIONAL,
      version: 1,
      is_active: true,
      change_log: '初始版本创建。',
      status: TestCaseStatus.DRAFT,
      owner_id: 'li_si',
      reviewer_id: '',
      priority: Priority.P1,
      estimated_duration_sec: 7200,
      target_components: ['CPU', 'Thermal Sensor'],
      required_env: { os: 'Linux', firmware: 'BMC v3.2.1' },
      tags: ['温度监控', '传感器'],
      pre_condition: 'BMC 和 BIOS 已更新至最新固件。',
      post_condition: '恢复 BMC 默认设置。',
      cleanup_steps: [],
      steps: [
        { step_id: 'step-1', name: '读取温度', action: '通过 IPMI 读取 CPU 温度', expected: '与物理温度计误差 < 2°C' }
      ],
      is_need_auto: true,
      is_destructive: false,
      automation_type: 'IPMI Command',
      script_entity_id: 'auto-temp-sensor-001',
      risk_level: RiskLevel.LOW,
      visibility_scope: VisibilityScope.PROJECT,
      confidentiality: Confidentiality.INTERNAL,
      attachments: [],
      custom_fields: {},
      approval_history: [],
      created_at: '2026-02-10T08:00:00Z',
      updated_at: '2026-02-10T08:00:00Z'
    },
    {
      case_id: 'TC-2026-004',
      ref_req_id: 'TR-2026-003',
      title: 'NVMe SSD 顺序读取性能测试',
      test_category: TestCaseCategory.PERFORMANCE,
      version: 3,
      is_active: true,
      change_log: '优化测试方法，增加更多块大小测试。',
      status: TestCaseStatus.APPROVED,
      owner_id: 'wang_wu',
      reviewer_id: 'alice',
      priority: Priority.P1,
      estimated_duration_sec: 3600,
      target_components: ['Storage', 'NVMe'],
      required_env: { os: 'Ubuntu 22.04', hardware: 'Dell PowerEdge R750' },
      tags: ['NVMe', '性能', 'FIO'],
      pre_condition: 'NVMe 硬盘已初始化，创建测试分区。',
      post_condition: '删除测试分区，恢复原始数据。',
      cleanup_steps: [],
      steps: [
        { step_id: 'step-1', name: '运行 FIO', action: 'fio --name=seq_read --ioengine=libaio --direct=1 --bs=1M --iodepth=32 --numjobs=1 --rw=read --size=10G --runtime=60 --group_reporting', expected: '顺序读取带宽 ≥ 6800 MB/s' }
      ],
      is_need_auto: true,
      is_destructive: true,
      automation_type: 'FIO Script',
      script_entity_id: 'auto-nvme-perf-001',
      risk_level: RiskLevel.HIGH,
      visibility_scope: VisibilityScope.GLOBAL,
      confidentiality: Confidentiality.NDA,
      attachments: [],
      custom_fields: {},
      approval_history: [{ approver: 'alice', timestamp: '2026-02-14T14:00:00Z', result: 'approved', comment: '性能指标符合预期。' }],
      created_at: '2026-01-25T08:00:00Z',
      updated_at: '2026-02-14T14:00:00Z'
    },
    {
      case_id: 'TC-2026-005',
      ref_req_id: 'TR-2026-004',
      title: '双电源故障切换测试',
      test_category: TestCaseCategory.STABILITY,
      version: 1,
      is_active: false,
      change_log: '初始版本创建。',
      status: TestCaseStatus.DEPRECATED,
      owner_id: 'zhang_san',
      reviewer_id: 'bob',
      priority: Priority.P0,
      estimated_duration_sec: 1800,
      target_components: ['Power Supply'],
      required_env: { hardware: '2U Server with 2x PSU' },
      tags: ['电源', '冗余', '故障切换'],
      pre_condition: '服务器配置为 1+1 冗余模式，负载均衡已启用。',
      post_condition: '恢复正常电源配置。',
      cleanup_steps: [],
      steps: [
        { step_id: 'step-1', name: '切断电源', action: '关闭 PSU1 电源', expected: 'PSU2 立即接管，无业务中断' }
      ],
      is_need_auto: false,
      is_destructive: true,
      automation_type: '',
      script_entity_id: '',
      risk_level: RiskLevel.HIGH,
      visibility_scope: VisibilityScope.PROJECT,
      confidentiality: Confidentiality.INTERNAL,
      attachments: [],
      custom_fields: { reason: '测试方法需要重新设计' },
      approval_history: [],
      created_at: '2026-02-05T08:00:00Z',
      updated_at: '2026-02-20T08:00:00Z'
    }
  ]);

  useEffect(() => {
    if (!isBackendEnabled || !testDesignerApi) {
      return;
    }

    let isMounted = true;

    const loadInitialData = async () => {
      try {
        const [remoteUsers, remoteRequirements, remoteTestCases] = await Promise.all([
          testDesignerApi.listUsers(),
          testDesignerApi.listRequirements(),
          testDesignerApi.listTestCases(),
        ]);

        if (!isMounted) {
          return;
        }

        setUsers(remoteUsers);
        setRequirements(remoteRequirements);
        setTestCases(remoteTestCases);
      } catch (error) {
        console.error('Failed to load data from backend, fallback to local mock data:', error);
      }
    };

    void loadInitialData();

    return () => {
      isMounted = false;
    };
  }, []);

  // Form data for test case
  const [formData, setFormData] = useState<TestCase>({
    case_id: 'TC-SRV-2024-001',
    ref_req_id: '',
    title: '',
    test_category: TestCaseCategory.STRESS,
    version: 1,
    is_active: true,
    change_log: '初始版本创建。',
    status: TestCaseStatus.DRAFT,
    owner_id: 'eng_zhang_san',
    reviewer_id: 'lead_li_si',
    auto_dev_id: '',
    priority: Priority.P0,
    estimated_duration_sec: 3600,
    target_components: [],
    required_env: { os: 'Redhat', firmware: '', hardware: '', dependencies: [], tooling: [] },
    tags: [],
    pre_condition: '',
    post_condition: '',
    cleanup_steps: [],
    steps: [],
    is_need_auto: true,
    is_destructive: false,
    automation_type: '',
    script_entity_id: '',
    risk_level: RiskLevel.MEDIUM,
    visibility_scope: VisibilityScope.PROJECT,
    confidentiality: Confidentiality.INTERNAL,
    attachments: [],
    custom_fields: {},
    failure_analysis: '',
    approval_history: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  });

  // Form data for requirement
  const [reqFormData, setReqFormData] = useState<TestRequirement>({
    req_id: `TR-${new Date().getFullYear()}-${String(requirements.length + 1).padStart(3, '0')}`,
    title: '',
    description: '',
    technical_spec: '',
    target_components: [],
    firmware_version: '',
    priority: Priority.P1,
    key_parameters: [],
    risk_points: '',
    tpm_owner_id: 'current_user',
    manual_dev_id: '',
    status: RequirementStatus.PENDING,
    attachments: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  });

  // UI state
  const [activeSection, setActiveSection] = useState('basic');
  const [reqActiveSection, setReqActiveSection] = useState('basic');
  const [isPolishing, setIsPolishing] = useState<{ [key: string]: boolean }>({});
  const [isGeneratingSteps, setIsGeneratingSteps] = useState(false);

  // AI hook
  const { polishText: aiPolishText, generateSteps: aiGenerateSteps } = useLocalAI();

  // Login handlers
  const handleLogin = useCallback(() => {
    if (!loginForm.user_id || !loginForm.password) {
      setLoginError('请输入用户ID和密码');
      return;
    }
    const user = users.find(u => u.username === loginForm.user_id && u.status === 'ACTIVE');
    if (user) {
      setCurrentUser(user);
      setIsLoggedIn(true);
      handleViewChange('req_list');
      setLoginError('');
    } else {
      setLoginError('用户ID或密码错误');
    }
  }, [loginForm.user_id, loginForm.password, users]);

  const handleLogout = useCallback(() => {
    setIsLoggedIn(false);
    setCurrentUser(null);
    setView('login');
  }, []);

  const handleQuickLogin = useCallback((user_id: string) => {
    setLoginForm({ ...loginForm, user_id, password: '123456' });
  }, [loginForm]);

  // Close user profile when changing views
  const handleViewChange = useCallback((viewName: View) => {
    setShowUserProfile(false);
    setView(viewName);
  }, []);

  // Requirement form handlers
  const updateReqField = useCallback((field: keyof TestRequirement, value: any) => {
    setReqFormData(prev => ({ ...prev, [field]: value }));
  }, []);

  const toggleReqComponent = useCallback((comp: string) => {
    setReqFormData(prev => {
      const current = prev.target_components;
      if (current.includes(comp)) {
        return { ...prev, target_components: current.filter(c => c !== comp) };
      } else {
        return { ...prev, target_components: [...current, comp] };
      }
    });
  }, []);

  const polishText = useCallback(async (field: 'description' | 'technical_spec') => {
    const text = reqFormData[field];
    if (!text) return;

    setIsPolishing(prev => ({ ...prev, [field]: true }));
    try {
      await aiPolishText(text, field, (resultField, result) => {
        updateReqField(resultField, result);
      });
    } finally {
      setIsPolishing(prev => ({ ...prev, [field]: false }));
    }
  }, [reqFormData.description, reqFormData.technical_spec, aiPolishText, updateReqField]);

  const addReqAttachment = useCallback(() => {
    const newAttachment: Attachment = {
      id: `att-${Date.now()}`,
      name: '需求规范文档.pdf',
      type: 'spec',
      url: '#',
      size: '2.5 MB',
      uploaded_at: new Date().toISOString()
    };
    setReqFormData(prev => ({ ...prev, attachments: [...prev.attachments, newAttachment] }));
  }, []);

  const removeReqAttachment = useCallback((id: string) => {
    setReqFormData(prev => ({ ...prev, attachments: prev.attachments.filter(a => a.id !== id) }));
  }, []);

  const saveRequirement = useCallback(async () => {
    const requirementToSave = { ...reqFormData, updated_at: new Date().toISOString() };

    if (isBackendEnabled && testDesignerApi) {
      try {
        const savedRequirement = await testDesignerApi.createRequirement(requirementToSave);
        setRequirements(prev => [...prev, savedRequirement]);
      } catch (error) {
        console.error('Failed to save requirement to backend:', error);
        alert('需求保存失败，请检查后端服务后重试。');
        return;
      }
    } else {
      setRequirements(prev => [...prev, requirementToSave]);
    }

    setView('req_list');
    // Reset form
    setReqFormData({
      req_id: `TR-${new Date().getFullYear()}-${String(requirements.length + 2).padStart(3, '0')}`,
      title: '',
      description: '',
      technical_spec: '',
      target_components: [],
      firmware_version: '',
      priority: Priority.P1,
      key_parameters: [],
      risk_points: '',
      tpm_owner_id: 'current_user',
      manual_dev_id: '',
      status: RequirementStatus.PENDING,
      attachments: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
  }, [reqFormData, requirements.length]);

  // Case form handlers
  const updateField = useCallback((path: string, value: any) => {
    setFormData(prev => {
      const newData = { ...prev };
      if (path.includes('.')) {
        const [parent, child] = path.split('.');
        (newData as any)[parent] = { ...(newData as any)[parent], [child]: value };
      } else {
        (newData as any)[path] = value;
      }
      return newData;
    });
  }, []);

  const addStep = useCallback(() => {
    const newStep: TestStep = {
      step_id: (formData.steps.length + 1).toString(),
      name: '',
      action: '',
      expected: ''
    };
    setFormData(prev => ({ ...prev, steps: [...prev.steps, newStep] }));
  }, [formData.steps.length]);

  const removeStep = useCallback((id: string) => {
    setFormData(prev => ({ ...prev, steps: prev.steps.filter(s => s.step_id !== id) }));
  }, []);

  const updateStep = useCallback((id: string, field: keyof TestStep, value: string) => {
    setFormData(prev => ({
      ...prev,
      steps: prev.steps.map(s => s.step_id === id ? { ...s, [field]: value } : s)
    }));
  }, []);

  const addAttachment = useCallback(() => {
    const newAttachment: Attachment = {
      id: `att-${Date.now()}`,
      name: '新附件.pdf',
      type: 'spec',
      url: '#',
      size: '1.2 MB',
      uploaded_at: new Date().toISOString()
    };
    setFormData(prev => ({ ...prev, attachments: [...prev.attachments, newAttachment] }));
  }, []);

  const removeAttachment = useCallback((id: string) => {
    setFormData(prev => ({ ...prev, attachments: prev.attachments.filter(a => a.id !== id) }));
  }, []);

  const generateStepsWithAI = useCallback(async () => {
    const linkedReq = requirements.find(r => r.req_id === formData.ref_req_id);
    if (!linkedReq) {
      alert("请先关联有效的测试需求 ID");
      return;
    }

    setIsGeneratingSteps(true);
    try {
      await aiGenerateSteps(
        linkedReq.title,
        linkedReq.description,
        linkedReq.technical_spec,
        linkedReq.key_parameters,
        (steps) => {
          setFormData(prev => ({ ...prev, steps }));
        }
      );
    } finally {
      setIsGeneratingSteps(false);
    }
  }, [requirements, formData.ref_req_id, aiGenerateSteps]);

  const saveTestCase = useCallback(async () => {
    const newCase = { ...formData, case_id: `TC-${Date.now()}`, updated_at: new Date().toISOString() };

    if (isBackendEnabled && testDesignerApi) {
      try {
        const savedTestCase = await testDesignerApi.createTestCase(newCase);
        setTestCases(prev => [...prev, savedTestCase]);
      } catch (error) {
        console.error('Failed to save test case to backend:', error);
        alert('用例保存失败，请检查后端服务后重试。');
        return;
      }
    } else {
      setTestCases(prev => [...prev, newCase]);
    }

    handleViewChange('req_detail');
  }, [formData]);

  // User management handlers
  const handleCreateUser = useCallback(async () => {
    if (!newUser.username || !newUser.email) return;
    const userToCreate: User = {
      user_id: `u-${Math.floor(Math.random() * 10000)}`,
      username: newUser.username,
      email: newUser.email,
      role_ids: newUser.role_ids || [],
      status: 'ACTIVE',
      created_at: new Date().toISOString().split('T')[0]
    };

    if (isBackendEnabled && testDesignerApi) {
      try {
        const createdUser = await testDesignerApi.createUser(userToCreate);
        setUsers(prev => [...prev, createdUser]);
      } catch (error) {
        console.error('Failed to create user in backend:', error);
        alert('用户创建失败，请检查后端服务后重试。');
        return;
      }
    } else {
      setUsers(prev => [...prev, userToCreate]);
    }

    setShowUserForm(false);
    setNewUser({ status: 'ACTIVE', role_ids: [] });
    console.log('Created User Request Example:', JSON.stringify(userToCreate, null, 2));
  }, [newUser]);

  const startEditUser = useCallback((user: User) => {
    setEditingUser({ ...user });
  }, []);

  const saveEditUser = useCallback(async (updatedUser: User) => {
    if (isBackendEnabled && testDesignerApi) {
      try {
        await testDesignerApi.updateUser(updatedUser.user_id, updatedUser);
      } catch (error) {
        console.error('Failed to update user in backend:', error);
        alert('用户更新失败，请检查后端服务后重试。');
        return;
      }
    }

    setUsers(prev => prev.map(u => u.user_id === updatedUser.user_id ? updatedUser : u));
    setEditingUser(null);
  }, []);

  const cancelEditUser = useCallback(() => {
    setEditingUser(null);
  }, []);

  const handleEditFieldChange = useCallback((field: string, value: any) => {
    setEditingUser(prev => {
      if (!prev) return null;
      return { ...prev, [field]: value };
    });
  }, []);

  // Render views based on current view
  if (view === 'login' || !isLoggedIn) {
    return (
      <Login
        loginForm={loginForm}
        showPassword={showPassword}
        loginError={loginError}
        onLoginFormChange={setLoginForm}
        onShowPasswordChange={setShowPassword}
        onLogin={handleLogin}
        onQuickLogin={handleQuickLogin}
      />
    );
  }

  if (view === 'user_mgmt') {
    return (
      <div className="min-h-screen bg-[#F8F9FA] flex">
        {/* Left Sidebar - Navigation */}
        <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
          {/* Logo */}
          <div className="p-6 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-slate-900 rounded-xl flex items-center justify-center shadow-lg shadow-slate-900/20">
                <FileText size={22} className="text-white" />
              </div>
              <div>
                <h1 className="text-sm font-bold text-slate-900">Test Designer</h1>
                <p className="text-[10px] text-slate-400">服务器测试平台</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            <button
              onClick={() => handleViewChange('req_list')}
              className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors"
            >
              <FileText size={18} />
              测试需求
            </button>
            <button
              onClick={() => handleViewChange('case_list')}
              className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:bg-slate-50 rounded-xl text-sm font-bold transition-colors"
            >
              <PlayCircle size={18} />
              测试用例
            </button>
            <button
              onClick={() => {}}
              className="w-full flex items-center gap-3 px-4 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold shadow-lg shadow-slate-900/20"
            >
              <UserIcon size={18} />
              用户管理
            </button>
          </nav>

          {/* Bottom User Info */}
          <div className="p-4 border-t border-slate-100">
            {currentUser && (
              <>
                <button
                  onClick={() => setShowUserProfile(true)}
                  className="w-full flex items-center gap-3 p-3 bg-slate-50 rounded-xl mb-3 hover:bg-slate-100 transition-colors cursor-pointer group"
                >
                  <div className="w-9 h-9 bg-indigo-100 rounded-lg flex items-center justify-center group-hover:bg-indigo-200 transition-colors">
                    <UserIcon size={16} className="text-indigo-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold text-slate-700 truncate">{currentUser.username}</div>
                    <div className="text-[10px] text-slate-400">{currentUser.role_ids[0] === 'ROLE_TPM' ? '测试经理' : '测试工程师'}</div>
                  </div>
                </button>

                {/* User Profile Popup */}
                {showUserProfile && (
                  <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                    <div
                      className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm"
                      onClick={() => setShowUserProfile(false)}
                    />
                    <div className="relative w-full max-w-md bg-white rounded-3xl shadow-2xl overflow-hidden">
                      {/* Header */}
                      <div className="px-6 py-5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white">
                        <div className="flex items-center justify-between">
                          <h2 className="text-lg font-bold">个人信息</h2>
                          <button
                            onClick={() => setShowUserProfile(false)}
                            className="p-1 hover:bg-white/20 rounded-lg transition-colors"
                          >
                            <X size={20} />
                          </button>
                        </div>
                      </div>

                      {/* Content */}
                      <div className="p-6 space-y-5">
                        {/* Avatar and Name */}
                        <div className="flex items-center gap-4">
                          <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center">
                            <UserIcon size={32} className="text-indigo-600" />
                          </div>
                          <div>
                            <div className="text-xl font-bold text-slate-900">{currentUser.username}</div>
                            <div className="text-sm text-slate-500">
                              {currentUser.role_ids[0] === 'ROLE_TPM' ? '测试经理' : '测试工程师'}
                            </div>
                            <span className={`inline-flex items-center mt-2 px-2 py-0.5 rounded-lg text-xs font-bold ${
                              currentUser.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-400'
                            }`}>
                              {currentUser.status === 'ACTIVE' ? '已启用' : '已禁用'}
                            </span>
                          </div>
                        </div>

                        {/* Details */}
                        <div className="space-y-3 pt-4 border-t border-slate-100">
                          <div className="flex items-center gap-3 text-sm">
                            <Mail size={16} className="text-slate-400" />
                            <div>
                              <div className="text-xs text-slate-400">邮箱地址</div>
                              <div className="font-medium text-slate-700">{currentUser.email}</div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3 text-sm">
                            <Shield size={16} className="text-slate-400" />
                            <div>
                              <div className="text-xs text-slate-400">用户角色</div>
                              <div className="flex gap-1.5 mt-1">
                                {currentUser.role_ids.map(rid => (
                                  <span key={rid} className="px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded text-xs font-bold">
                                    {ROLES.find(r => r.id === rid)?.name || rid}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3 text-sm">
                            <Calendar size={16} className="text-slate-400" />
                            <div>
                              <div className="text-xs text-slate-400">创建时间</div>
                              <div className="font-medium text-slate-700">{currentUser.created_at}</div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3 text-sm">
                            <div className="w-4 h-4 flex items-center justify-center">
                              <div className="w-2 h-2 bg-slate-400 rounded-full" />
                            </div>
                            <div>
                              <div className="text-xs text-slate-400">用户 ID</div>
                              <div className="font-mono text-xs text-slate-600">{currentUser.user_id}</div>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Footer */}
                      <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex gap-3">
                        <button
                          onClick={() => setShowUserProfile(false)}
                          className="flex-1 px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-200 rounded-xl transition-all"
                        >
                          关闭
                        </button>
                        <button
                          onClick={() => {
                            setShowUserProfile(false);
                            setView('user_mgmt');
                          }}
                          className="flex-1 px-4 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all"
                        >
                          编辑资料
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-slate-500 hover:bg-rose-50 hover:text-rose-600 rounded-xl text-sm font-bold transition-colors"
            >
              <LogIn size={16} className="rotate-180" />
              退出登录
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          <div className="max-w-full h-full">
            <UserMgmt
              users={users}
              currentUser={currentUser}
              showUserForm={showUserForm}
              editingUser={editingUser}
              newUser={newUser}
              onBack={() => setView('req_list')}
              onShowUserForm={setShowUserForm}
              onNewUserChange={setNewUser}
              onCreateUser={handleCreateUser}
              onStartEditUser={startEditUser}
              onSaveEditUser={saveEditUser}
              onCancelEdit={cancelEditUser}
              onEditFieldChange={handleEditFieldChange}
            />
          </div>
        </main>
      </div>
    );
  }

  if (view === 'req_form') {
    return (
      <ReqForm
        formData={reqFormData}
        activeSection={reqActiveSection}
        isPolishing={isPolishing}
        onFieldChange={updateReqField}
        onSave={saveRequirement}
        onCancel={() => setView('req_list')}
        onAddAttachment={addReqAttachment}
        onRemoveAttachment={removeReqAttachment}
        onToggleComponent={toggleReqComponent}
        onPolishText={polishText}
        onSectionChange={setReqActiveSection}
      />
    );
  }

  if (view === 'req_detail' && selectedReq) {
    return (
      <ReqDetail
        requirement={selectedReq}
        testCases={testCases}
        onBack={() => setView('req_list')}
        onCreateCase={(refReqId) => {
          setFormData(prev => ({ ...prev, ref_req_id: refReqId }));
          handleViewChange('case_form');
        }}
        onSelectCase={(tc) => {
          setFormData(tc);
          handleViewChange('case_form');
        }}
      />
    );
  }

  if (view === 'case_form') {
    return (
      <CaseForm
        formData={formData}
        activeSection={activeSection}
        isGeneratingSteps={isGeneratingSteps}
        onFieldChange={updateField}
        onAddStep={addStep}
        onRemoveStep={removeStep}
        onUpdateStep={updateStep}
        onAddAttachment={addAttachment}
        onRemoveAttachment={removeAttachment}
        onSave={saveTestCase}
        onCancel={() => setView('req_detail')}
        onGenerateSteps={generateStepsWithAI}
        onSectionChange={setActiveSection}
      />
    );
  }

  if (view === 'case_list') {
    return (
      <CaseList
        testCases={testCases}
        currentUser={currentUser}
        onSelectCase={(tc) => {
          setFormData(tc);
          handleViewChange('case_form');
        }}
        onCreateCase={() => {
          setFormData({
            case_id: 'TC-SRV-2024-001',
            ref_req_id: '',
            title: '',
            test_category: TestCaseCategory.STRESS,
            version: 1,
            is_active: true,
            change_log: '初始版本创建。',
            status: TestCaseStatus.DRAFT,
            owner_id: currentUser?.username || '',
            reviewer_id: '',
            auto_dev_id: '',
            priority: Priority.P0,
            estimated_duration_sec: 3600,
            target_components: [],
            required_env: { os: '', firmware: '', hardware: '', dependencies: [], tooling: [] },
            tags: [],
            pre_condition: '',
            post_condition: '',
            cleanup_steps: [],
            steps: [],
            is_need_auto: false,
            is_destructive: false,
            automation_type: '',
            script_entity_id: '',
            risk_level: RiskLevel.MEDIUM,
            visibility_scope: VisibilityScope.PROJECT,
            confidentiality: Confidentiality.INTERNAL,
            attachments: [],
            custom_fields: {},
            failure_analysis: '',
            approval_history: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          });
          handleViewChange('case_form');
        }}
        onNavigateToReqList={() => setView('req_list')}
        onNavigateToUserMgmt={() => setView('user_mgmt')}
        onLogout={handleLogout}
        showUserProfile={showUserProfile}
        onToggleUserProfile={() => setShowUserProfile(!showUserProfile)}
      />
    );
  }

  // Default: req_list view
  return (
    <ReqList
      requirements={requirements}
      currentUser={currentUser}
      onSelectReq={(req) => {
        setSelectedReq(req);
        handleViewChange('req_detail');
      }}
      onCreateReq={() => setView('req_form')}
      onNavigateToCaseList={() => setView('case_list')}
      onNavigateToUserMgmt={() => setView('user_mgmt')}
      onLogout={handleLogout}
      showUserProfile={showUserProfile}
      onToggleUserProfile={() => setShowUserProfile(!showUserProfile)}
    />
  );
}
