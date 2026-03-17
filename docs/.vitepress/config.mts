import { defineConfig } from 'vitepress'

export default defineConfig({
  title: "DMLV4 文档",
  description: "服务器测试用例设计器文档",
  ignoreDeadLinks: true,
  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      { text: '架构规范', link: '/architecture' },
      { text: '认证与登录', link: '/guide/authentication' },
      { text: '测试需求与用例', link: '/guide/test-requirements-cases' },
      { text: '测试执行下发', link: '/guide/test-execution' },
      { text: '入门指南', link: '/guide/getting-started' }
    ],

    sidebar: [
      {
        text: '指南',
        items: [
          { text: '快速开始', link: '/guide/getting-started' },
          { text: '认证与登录', link: '/guide/authentication' },
          { text: '测试需求与用例', link: '/guide/test-requirements-cases' },
          { text: '测试执行下发', link: '/guide/test-execution' },
          { text: '架构规范', link: '/architecture' }
        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/anthropics/claude-code' }
    ],

    footer: {
      message: '基于 MIT 协议发布',
      copyright: 'Copyright © 2024-present'
    }
  }
})