import { defineConfig } from "vitepress";

export default defineConfig({
  title: "DML V4 Backend Docs",
  description: "DML V4 后端开发手册与模块实现文档",
  lang: "zh-CN",
  cleanUrls: true,
  ignoreDeadLinks: true,
  themeConfig: {
    nav: [
      { text: "首页", link: "/" },
      { text: "开发手册", link: "/guide/quick-start" },
      { text: "模块实现", link: "/modules/workflow/" },
      { text: "通用约定", link: "/reference/conventions" },
      { text: "交接手册", link: "/handover/new-engineer-onboarding" },
    ],
    sidebar: [
      {
        text: "开发手册",
        items: [
          { text: "快速开始", link: "/guide/quick-start" },
          { text: "本地开发", link: "/guide/local-development" },
          { text: "架构总览", link: "/guide/architecture-overview" },
          { text: "如何修改后端", link: "/guide/how-to-change-backend" },
          { text: "排障手册", link: "/guide/debugging-playbook" },
        ],
      },
      {
        text: "模块实现",
        items: [
          { text: "Workflow", link: "/modules/workflow/" },
          { text: "Test Specs", link: "/modules/test-specs/" },
          { text: "Execution", link: "/modules/execution/" },
          { text: "Auth", link: "/modules/auth/" },
          { text: "Attachments", link: "/modules/attachments/" },
          { text: "Terminal", link: "/modules/terminal/" },
          { text: "Shared", link: "/modules/shared/" },
        ],
      },
      {
        text: "通用约定",
        items: [
          { text: "开发与架构约定", link: "/reference/conventions" },
          { text: "API 约定", link: "/reference/api-conventions" },
          { text: "数据库表与字段", link: "/reference/database-tables" },
          { text: "数据模型约定", link: "/reference/data-model-conventions" },
          { text: "测试约定", link: "/reference/testing-conventions" },
          { text: "文档编写约定", link: "/reference/doc-writing-rules" },
        ],
      },
      {
        text: "交接手册",
        items: [
          { text: "新工程师上手", link: "/handover/new-engineer-onboarding" },
          { text: "变更检查清单", link: "/handover/change-checklist" },
        ],
      },
    ],
    footer: {
      message: "后端开发文档仅面向开发与交接使用",
      copyright: "DML V4 Backend",
    },
    search: {
      provider: "local",
    },
  },
});
