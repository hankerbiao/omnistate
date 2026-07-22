/// <reference types="vite/client" />

// 由 vite.config.ts / vitest.config.ts 通过 define 注入的构建期常量，
// 控制是否启用 Mock 分支（生产构建默认 false，便于死代码剔除）。
declare const __USE_MOCK__: boolean;
