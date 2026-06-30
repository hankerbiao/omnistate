import { useState } from 'react';
import ConfigList from './components/ConfigList';
import './styles/index.css';

const SystemConfigPage = () => {

  return (
    <div className="system-config-page">
      <div className="system-config-header">
        <h2>系统配置</h2>
        <p className="system-config-subtitle">管理系统参数和LLM服务配置</p>
      </div>

      <ConfigList />
    </div>
  );
};

export default SystemConfigPage;
