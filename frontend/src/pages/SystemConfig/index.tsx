import { useState } from 'react';
import ConfigList from './components/ConfigList';
import AIConfigPanel from './components/AIConfigPanel';
import './styles/index.css';

const SystemConfigPage = () => {
  const [aiConfigOpen, setAiConfigOpen] = useState(false);

  return (
    <div className="system-config-page">
      <div className="system-config-header">
        <h2>系统配置</h2>
        <p className="system-config-subtitle">管理系统参数和LLM服务配置</p>
      </div>

      <ConfigList onOpenAiConfig={() => setAiConfigOpen(true)} />

      {aiConfigOpen && (
        <div className="modal-overlay" onClick={() => setAiConfigOpen(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ width: 640 }}>
            <div className="modal__header">
              <h3 className="modal__title">AI 配置</h3>
              <button type="button" className="modal__close" onClick={() => setAiConfigOpen(false)}>×</button>
            </div>
            <div className="modal__body">
              <AIConfigPanel onClose={() => setAiConfigOpen(false)} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SystemConfigPage;
