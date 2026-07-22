import { defineConfig } from "vitepress";

export default defineConfig({
  title: "DML V4 开放平台",
  description: "DML V4 Open Platform design and usage documentation",
  lang: "zh-CN",
  cleanUrls: true,
  themeConfig: {
    logo: "/logo.svg",
    nav: [
      { text: "指南", link: "/guide/quick-start" },
      { text: "设计", link: "/design/architecture" },
      { text: "接口", link: "/reference/api" },
      { text: "运维", link: "/operations/deploy" }
    ],
    sidebar: [
      {
        text: "指南",
        items: [
          { text: "快速开始", link: "/guide/quick-start" },
          { text: "使用手册", link: "/guide/user-guide" },
          { text: "本地联调", link: "/guide/local-debug" }
        ]
      },
      {
        text: "设计文档",
        items: [
          { text: "总体架构", link: "/design/architecture" },
          { text: "网关设计", link: "/design/gateway" },
          { text: "前端设计", link: "/design/frontend" }
        ]
      },
      {
        text: "模块说明",
        items: [
          { text: "后端网关", link: "/backend/gateway-service" },
          { text: "前端控制台", link: "/frontend/console" }
        ]
      },
      {
        text: "参考",
        items: [
          { text: "API 参考", link: "/reference/api" },
          { text: "配置参考", link: "/reference/configuration" },
          { text: "扩展指南", link: "/reference/extension" }
        ]
      },
      {
        text: "运维",
        items: [
          { text: "部署运行", link: "/operations/deploy" },
          { text: "测试与质量", link: "/operations/testing" },
          { text: "故障排查", link: "/operations/troubleshooting" }
        ]
      }
    ],
    search: {
      provider: "local"
    },
    outline: {
      level: [2, 3],
      label: "本页目录"
    },
    docFooter: {
      prev: "上一页",
      next: "下一页"
    },
    lastUpdated: {
      text: "最后更新",
      formatOptions: {
        dateStyle: "medium",
        timeStyle: "short"
      }
    },
    socialLinks: []
  },
  lastUpdated: true
});
