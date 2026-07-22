import ConfigList from './components/ConfigList';
import './styles/index.css';

const SystemConfigPage = () => {

  return (
    <div className="system-config-page">
      <div className="system-config-header">
        <h2>运行时配置</h2>
        <p className="system-config-subtitle">管理可热更新的LLM服务配置</p>
      </div>

      <ConfigList />
    </div>
  );
};

export default SystemConfigPage;
