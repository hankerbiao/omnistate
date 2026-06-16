import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../../../services/api';
import type { SystemConfig, TestConnectionResponse } from '../../../types';

interface AIConfigPanelProps {
  onClose?: () => void;
}

/**
 * AI 配置面板 — 动态表单
 *
 * 所有可配置字段由后端 GET /system-configs?category=ai 动态提供，
 * 前端根据 config_type/is_encrypted 自动选择表单控件。
 * 后端增减 AI 配置字段时，前端无需修改。
 */
const AIConfigPanel: React.FC<AIConfigPanelProps> = ({ onClose }) => {
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestConnectionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // 加载当前 AI 配置
  const loadConfig = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getSystemConfigs({ category: 'ai', active_only: true });
      setConfigs(res.data?.items || []);
    } catch (err: any) {
      setError('加载配置失败: ' + (err.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadConfig(); }, [loadConfig]);

  // 按基础/高级分组
  const { basicConfigs, advancedConfigs } = useMemo(() => {
    const basic: SystemConfig[] = [];
    const advanced: SystemConfig[] = [];
    for (const cfg of configs) {
      // ai.base_url / ai.model / ai.api_key 为基础参数，其余为高级参数
      if (cfg.config_key === 'ai.base_url' || cfg.config_key === 'ai.model' || cfg.config_key === 'ai.api_key') {
        basic.push(cfg);
      } else {
        advanced.push(cfg);
      }
    }
    return { basicConfigs: basic, advancedConfigs: advanced };
  }, [configs]);

  // 获取指定 key 的值（字符串形式）
  const getValue = (key: string): string => {
    return configs.find(c => c.config_key === key)?.config_value ?? '';
  };

  // 更新单个字段
  const handleChange = (configKey: string, value: string) => {
    setConfigs(prev => prev.map(c =>
      c.config_key === configKey ? { ...c, config_value: value } : c
    ));
    setTestResult(null);
    setSuccessMsg(null);
  };

  // 渲染单个配置字段的表单控件
  const renderField = (cfg: SystemConfig) => {
    const value = cfg.config_value;
    const type = cfg.config_type;

    if (type === 'boolean') {
      return (
        <label className="checkbox-label" key={cfg.config_key}>
          <input
            type="checkbox"
            checked={value === 'true'}
            onChange={e => handleChange(cfg.config_key, String(e.target.checked))}
          />
          <span>{cfg.description}</span>
        </label>
      );
    }

    const isNumber = type === 'integer' || type === 'float';
    return (
      <div className="form-field" key={cfg.config_key}>
        <label className="form-field__label">{cfg.description}</label>
        <input
          type={cfg.is_encrypted ? 'password' : isNumber ? 'number' : 'text'}
          className="form-input"
          value={value}
          onChange={e => handleChange(cfg.config_key, e.target.value)}
          placeholder={cfg.description}
          min={isNumber ? 0 : undefined}
          step={type === 'float' ? 0.1 : undefined}
        />
      </div>
    );
  };

  // 前端轻量验证
  const validateConfig = (): string[] => {
    const errors: string[] = [];
    for (const cfg of configs) {
      const key = cfg.config_key;
      const value = cfg.config_value;

      if (key === 'ai.base_url') {
        if (!value) errors.push('基础URL不能为空');
        else if (!value.startsWith('http://') && !value.startsWith('https://'))
          errors.push('URL必须以http://或https://开头');
      } else if (key === 'ai.model') {
        if (!value) errors.push('模型名称不能为空');
      } else if (key === 'ai.temperature') {
        const v = parseFloat(value);
        if (isNaN(v) || v < 0 || v > 2) errors.push('温度参数必须在0-2之间');
      } else if (key === 'ai.max_tokens') {
        const v = parseInt(value);
        if (isNaN(v) || v < 1) errors.push('最大Token不能小于1');
      } else if (key === 'ai.timeout') {
        const v = parseInt(value);
        if (isNaN(v) || v < 1 || v > 600) errors.push('超时时间必须在1-600秒之间');
      }
    }
    return errors;
  };

  // 测试 AI 连接
  const handleTest = async () => {
    const errors = validateConfig();
    if (errors.length > 0) { setError(errors.join('; ')); return; }
    setTesting(true);
    setError(null);
    setTestResult(null);
    try {
      const res = await api.testAIConnection({
        base_url: getValue('ai.base_url'),
        model: getValue('ai.model'),
        api_key: getValue('ai.api_key') || undefined,
      });
      setTestResult(res.data);
    } catch (err: any) {
      setError('连接测试失败: ' + (err.message || '未知错误'));
    } finally {
      setTesting(false);
    }
  };

  // 保存配置
  const handleSave = async () => {
    const errors = validateConfig();
    if (errors.length > 0) { setError(errors.join('; ')); return; }
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await api.batchUpdateSystemConfigs({
        items: configs.map(c => ({
          config_key: c.config_key,
          config_value: c.config_value,
        })),
        remark: '从前端更新LLM配置',
      });
      setSuccessMsg('配置保存成功！');
      await loadConfig();
      onClose?.();
    } catch (err: any) {
      setError('保存配置失败: ' + (err.message || '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  // 重置为默认值（从后端重新加载）
  const handleReset = async () => {
    if (!window.confirm('确定重置为默认配置吗？')) return;
    setTestResult(null);
    setSuccessMsg(null);
    await loadConfig();
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
        {basicConfigs.length > 0 && (
          <div className="ai-config-basic">
            {basicConfigs.map(renderField)}
          </div>
        )}

        {/* 高级参数（可折叠） */}
        {advancedConfigs.length > 0 && (
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
                {advancedConfigs.map(renderField)}
              </div>
            )}
          </div>
        )}
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
