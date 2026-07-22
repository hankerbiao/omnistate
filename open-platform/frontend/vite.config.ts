import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// 开放平台前端独立 Vite 配置；dev / preview 端口使用 8808。
export default defineConfig(({ mode }) => {
  // 读取 .env 中的 VITE_ 前缀变量，决定是否注入 Mock 分支
  const env = loadEnv(mode, process.cwd(), "VITE");
  const useMock = env.VITE_OPEN_PLATFORM_USE_MOCK === "true";

  return {
    plugins: [react()],
    define: {
      // 构建期常量：生产构建未显式开启时，api.ts 内的 Mock 分支会被判为死代码并剔除
      __USE_MOCK__: JSON.stringify(useMock),
    },
    server: {
      host: "0.0.0.0",
      port: 8808,
    },
    preview: {
      host: "0.0.0.0",
      port: 8808,
    },
  };
});
