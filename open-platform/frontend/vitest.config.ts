import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// 测试配置：强制启用 Mock 分支（__USE_MOCK__=true），使用 jsdom 模拟 DOM。
export default defineConfig({
  plugins: [react()],
  define: {
    __USE_MOCK__: JSON.stringify(true),
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
