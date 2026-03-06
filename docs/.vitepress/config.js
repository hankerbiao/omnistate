import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'DMLV4 API 文档',
  description: '双栈系统API接口文档，包含工作流、测试管理、资产管理等功能',
  lang: 'zh-CN',
  lastUpdated: true,
  themeConfig: {
    logo: {
      src: '/logo.png',
      alt: 'DMLV4'
    },
    nav: [
      { text: '首页', link: '/' },
      { text: 'API文档', link: '/api/' },
      { text: '架构说明', link: '/architecture/' }
    ],
    sidebar: {
      '/api/': [
        {
          text: 'API 概览',
          collapsed: false,
          items: [
            { text: '接口说明', link: '/api/' },
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
            { text: '认证授权', link: '/api/auth-modules' },
            { text: '系统健康', link: '/api/health' }
          ]
        }
      ]
    },
    socialLinks: [
      {
        icon: 'github',
        link: 'https://github.com/hankerbiao/omnistate'
      }
    ],
    editLink: {
      pattern: 'https://github.com/hankerbiao/omnistate/edit/main/docs/:path',
      text: '在 GitHub 上编辑此页'
    },
    docFooter: {
      prev: '上一篇',
      next: '下一篇'
    },
    outline: {
      label: '页面导航',
      level: 'deep'
    }
  }
})