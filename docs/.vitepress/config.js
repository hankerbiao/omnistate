import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'DMLV4 文档',
  description: 'DMLV4 项目文档站点，包含架构、接口、后端设计与阶段变更说明',
  lang: 'zh-CN',
  lastUpdated: true,
  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      { text: '总览', link: '/README' },
      { text: 'API', link: '/api/' },
      { text: 'Backend', link: '/backend/' },
      { text: '变更', link: '/changes/2026-03-02_03_阶段变更汇总' }
    ],
    sidebar: {
      '/': [
        {
          text: '文档总览',
          collapsed: false,
          items: [
            { text: '首页', link: '/' },
            { text: 'README', link: '/README' }
          ]
        },
        {
          text: '根目录文档',
          collapsed: false,
          items: [
            { text: '文档治理与重构方案', link: '/文档治理与重构方案' },
            { text: '项目架构规范', link: '/项目架构规范' },
            { text: '接口与认证说明', link: '/接口与认证说明' },
            { text: '测试对象与字段规范', link: '/测试对象与字段规范' },
            { text: '测试设计与 BOM 关联方案', link: '/测试设计与BOM关联方案' },
            { text: '测试执行集成方案', link: '/测试执行集成方案' }
          ]
        },
        {
          text: '目录入口',
          collapsed: false,
          items: [
            { text: 'API 文档', link: '/api/' },
            { text: 'Backend 文档', link: '/backend/' },
            { text: '阶段变更', link: '/changes/2026-03-02_03_阶段变更汇总' }
          ]
        }
      ],
      '/api/': [
        {
          text: 'API 概览',
          collapsed: false,
          items: [
            { text: '接口总览', link: '/api/' },
            { text: '认证说明', link: '/api/auth' }
          ]
        },
        {
          text: '核心模块',
          collapsed: false,
          items: [
            { text: '工作流管理', link: '/api/workflow' },
            { text: '测试需求', link: '/api/requirements' },
            { text: '测试用例', link: '/api/test-cases' },
            { text: '测试执行', link: '/api/execution' }
          ]
        },
        {
          text: '支撑模块',
          collapsed: false,
          items: [
            { text: '资产管理', link: '/api/assets' },
            { text: '认证授权模块', link: '/api/auth-modules' },
            { text: '系统健康', link: '/api/health' }
          ]
        }
      ],
      '/backend/': [
        {
          text: 'Backend 总览',
          collapsed: false,
          items: [
            { text: '入口', link: '/backend/' },
            { text: '鉴权设计', link: '/backend/authorization_design' },
            { text: '权限校验模式', link: '/backend/permission_validation_patterns' },
            { text: 'RBAC 设计', link: '/backend/rbac_design' },
            { text: '导航管理实现', link: '/backend/navigation_page_backend_impl' },
            { text: '需求与用例关系', link: '/backend/requirement_testcase_relation_design' }
          ]
        }
      ],
      '/changes/': [
        {
          text: '阶段变更',
          collapsed: false,
          items: [
            { text: '2026-03-02 阶段变更汇总', link: '/changes/2026-03-02_03_阶段变更汇总' }
          ]
        }
      ]
    },
    editLink: {
      pattern: 'https://github.com/libiao/dmlv4/edit/main/docs/:path',
      text: '在 GitHub 上编辑此页'
    },
    docFooter: {
      prev: '上一篇',
      next: '下一篇'
    },
    outline: {
      label: '页面导航',
      level: 'deep'
    },
    search: {
      provider: 'local'
    }
  }
})
