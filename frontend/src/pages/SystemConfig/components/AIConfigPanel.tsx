import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../services/api';
import type { AIConfig, TestConnectionResponse } from '../../../types';

const defaultAIConfig: AIConfig = {
  base_url: 'http://localhost:11434/v1',
  model: 'qwen2.5:latest',
  api_key: '',
  temperature: 0.7,
  max_tokens: 4096,
  timeout: 60,
  enabled: true,
};

interface AIConfigPanelProps {
  onClose?: () => void;
}

const AIConfigPanel: React.FC<AIConfigPanelProps> = ({ onClose }) => {
  const [config, setConfig] = useState<AIConfig>({ ...defaultAIConfig });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestConnectionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // 加载当前配置
  const loadConfig = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getSystemConfigs({ category: 'ai', active_only: true });
      const configs = res.data?.items || [];
      const newConfig = { ...defaultAIConfig };
      configs.forEach((c: any) => {
        switch (c.config_key) {
          case 'ai.base_url': newConfig.base_url = c.config_value; break;
          case 'ai.model': newConfig.model = c.config_value; break;
          case 'ai.api_key': newConfig.api_key = c.config_value; break;
          case 'ai.temperature': newConfig.temperature = parseFloat(c.config_value) || 0.7; break;
          case 'ai.max_tokens': newConfig.max_tokens = parseInt(c.config_value) || 4096; break;
          case 'ai.timeout': newConfig.timeout = parseInt(c.config_value) || 60; break;
          case 'ai.enabled': newConfig.enabled = c.config_value === 'true'; break;
        }
      });
      setConfig(newConfig);
    } catch (err: any) {
      setError('加载配置失败: ' + (err.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadConfig(); }, [loadConfig]);

  const handleChange = (field: keyof AIConfig, value: any) => {
    setConfig(prev => ({ ...prev, [field]: value }));
    setTestResult(null);
    setSuccessMsg(null);
  };

  const validateConfig = (): string[] => {
    const errors: string[] = [];
    if (!config.base_url) errors.push('基础URL不能为空');
    else if (!config.base_url.startsWith('http://') && !config.base_url.startsWith('https://'))
      errors.push('URL必须以http://或https://开头');
    if (!config.model) errors.push('模型名称不能为空');
    if (config.temperature < 0 || config.temperature > 2) errors.push('温度参数必须在0-2之间');
    if (config.max_tokens < 1) errors.push('最大Token不能小于1');
    if (config.timeout < 1 || config.timeout > 600) errors.push('超时时间必须在1-600秒之间');
    return errors;
  };

  const handleTest = async () => {
    const errors = validateConfig();
    if (errors.length > 0) { setError(errors.join('; ')); return; }
    setTesting(true); setError(null); setTestResult(null);
    try {
      const res = await api.testAIConnection({
        base_url: config.base_url, model: config.model, api_key: config.api_key || undefined,
      });
      setTestResult(res.data);
    } catch (err: any) {
      setError('连接测试失败: ' + (err.message || '未知错误'));
    } finally { setTesting(false); }
  };

  const handleSave = async () => {
    const errors = validateConfig();
    if (errors.length > 0) { setError(errors.join('; ')); return; }
    setSaving(true); setError(null); setSuccessMsg(null);
    try {
      await api.batchUpdateSystemConfigs({
        items: [
          { config_key: 'ai.base_url', config_value: config.base_url },
          { config_key: 'ai.model', config_value: config.model },
          { config_key: 'ai.api_key', config_value: config.api_key },
          { config_key: 'ai.temperature', config_value: String(config.temperature) },
          { config_key: 'ai.max_tokens', config_value: String(config.max_tokens) },
          { config_key: 'ai.timeout', config_value: String(config.timeout) },
          { config_key: 'ai.enabled', config_value: String(config.enabled) },
        ],
        remark: '从前端更新LLM配置',
      });
      setSuccessMsg('配置保存成功！');
      await loadConfig();
      onClose?.();
    } catch (err: any) {
      setError('保存配置失败: ' + (err.message || '未知错误'));
    } finally { setSaving(false); }
  };

  const handleReset = async () => {
    if (!window.confirm('确定重置为默认配置吗？')) return;
    setConfig({ ...defaultAIConfig });
    setTestResult(null); setSuccessMsg(null);
  };

  if (loading) return <div className="loading-spinner" />;

  return (
    <div className="ai-config-panel">
      <div className="ai-config-section">
        <h3>LLM 服务配置</h3>
        <p className="ai-config-hint">
          配置大语言模型服务，支持 Ollama（本地）和 OpenAI 兼容API
        </p>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠ {error}</span>
          <button type="button" onClick={() => setError(null)}>×</button>
        </div>
      )}
      {successMsg && (
        <div className="success-banner">
          <span>✅ {successMsg}</span>
          <button type="button" onClick={() => setSuccessMsg(null)}>×</button>
        </div>
      )}

      <div className="ai-config-form">
        {/* 基础参数：URL、模型、密钥 */}
        <div className="form-field">
          <label className="form-field__label">基础 URL *</label>
          <input
            type="text" className="form-input"
            value={config.base_url}
            onChange={e => handleChange('base_url', e.target.value)}
            placeholder="http://localhost:11434/v1"
          />
          <span className="form-hint">Ollama: http://localhost:11434/v1</span>
        </div>

        <div className="form-row">
          <div className="form-field form-field--half">
            <label className="form-field__label">模型名称 *</label>
            <input
              type="text" className="form-input"
              value={config.model}
              onChange={e => handleChange('model', e.target.value)}
              placeholder="qwen2.5:latest"
            />
          </div>

          <div className="form-field form-field--half">
            <label className="form-field__label">API 密钥</label>
            <input
              type="password" className="form-input"
              value={config.api_key}
              onChange={e => handleChange('api_key', e.target.value)}
              placeholder="（Ollama 无需密钥）"
            />
          </div>
        </div>

        {/* 高级参数（可折叠） */}
        <div className="ai-config-advanced">
          <button
            type="button"
            className="ai-config-advanced__toggle"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            <span className={`ai-config-advanced__arrow ${showAdvanced ? 'open' : ''}`}>▶</span>
            高级参数
          </button>

          {showAdvanced && (
            <div className="ai-config-advanced__content">
              <div className="form-row">
                <div className="form-field form-field--half">
                  <label className="form-field__label">温度参数</label>
                  <input
                    type="number" className="form-input"
                    value={config.temperature}
                    onChange={e => handleChange('temperature', parseFloat(e.target.value))}
                    min={0} max={2} step={0.1}
                  />
                  <span className="form-hint">0-2，越高越随机</span>
                </div>

                <div className="form-field form-field--half">
                  <label className="form-field__label">最大 Token</label>
                  <input
                    type="number" className="form-input"
                    value={config.max_tokens}
                    onChange={e => handleChange('max_tokens', parseInt(e.target.value))}
                    min={1}
                  />
                  <span className="form-hint">单次生成上限</span>
                </div>
              </div>

              <div className="form-row">
                <div className="form-field form-field--half">
                  <label className="form-field__label">超时时间（秒）</label>
                  <input
                    type="number" className="form-input"
                    value={config.timeout}
                    onChange={e => handleChange('timeout', parseInt(e.target.value))}
                    min={1} max={600}
                  />
                </div>

                <div className="form-field form-field--half" style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: 8 }}>
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={config.enabled}
                      onChange={e => handleChange('enabled', e.target.checked)}
                    />
                    <span>启用 AI 分析</span>
                  </label>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {testResult && (
        <div className={`test-result ${testResult.success ? 'test-result--success' : 'test-result--error'}`}>
          {testResult.success ? (
            <>
              <span>✅ 连接成功</span>
              {testResult.model && <span className="test-result__model">模型: {testResult.model}</span>}
              {testResult.response_time_ms && <span className="test-result__time">{testResult.response_time_ms}ms</span>}
            </>
          ) : (
            <span>❌ 连接失败: {testResult.error}</span>
          )}
        </div>
      )}

      <div className="ai-config-actions">
        <button type="button" className="btn btn--secondary" onClick={handleTest} disabled={testing}>
          {testing ? '测试中...' : '测试连接'}
        </button>
        <button type="button" className="btn btn--ghost" onClick={handleReset}>
          重置默认
        </button>
        <button type="button" className="btn btn--primary" onClick={handleSave} disabled={saving}>
          {saving ? '保存中...' : '保存配置'}
        </button>
      </div>
    </div>
  );
};

export default AIConfigPanel;
