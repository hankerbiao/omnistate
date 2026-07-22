// DML V4 开放平台前端 · ESLint 扁平配置（ESLint 10 + typescript-eslint）
import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";

export default tseslint.config(
  { ignores: ["dist", "node_modules", "coverage", ".vite"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.browser, ...globals.node },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      // React Hooks 规则（显式声明，避免依赖插件 configs 导出形态变化）
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      // Fast Refresh 友好提示：组件文件尽量只导出组件
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      // 未使用变量告警（与 tsconfig noUnusedLocals 形成双保险，忽略下划线前缀）
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_", ignoreRestSiblings: true },
      ],
    },
  },
  // 有意多导出 / 入口文件：关闭 react-refresh（Fast Refresh 边界优化对它们无意义）
  {
    files: ["src/main.tsx", "src/components/ui.tsx", "src/components/icons.tsx"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
);
