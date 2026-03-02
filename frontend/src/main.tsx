/**
 * @fileoverview 应用入口文件
 * React应用的启动入口，配置了StrictMode和全局样式
 */

import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import './index.css';

// 启动React应用
// StrictMode用于在开发模式下检测潜在问题
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
