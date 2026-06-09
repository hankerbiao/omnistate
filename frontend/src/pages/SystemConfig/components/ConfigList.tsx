import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../services/api';
import type { SystemConfig } from '../../../types';

type Category = 'all' | 'ai' | 'system' | 'general';

const CATEGORY_LABELS: Record<Category, string> = {
  all: '全部',
  ai: 'AI 配置',
  system: '系统配置',
  general: '通用配置',
};

const TYPE_LABELS: Record<string, string> = {
  string: '字符串',
  integer: '整数',
  float: '浮点数',
  boolean: '布尔',
  json: 'JSON',
};

interface ConfigListProps {
  onOpenAiConfig?: () => void;
}

const ConfigList: React.FC<ConfigListProps> = ({ onOpenAiConfig }) => {
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState<Category>('all');
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchConfigs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getSystemConfigs({
        category: category === 'all' ? undefined : category,
        active_only: false,
      });
      setConfigs(res.data?.items || []);
    } catch (err: any) {
      setError('获取配置失败: ' + (err.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  }, [category]);

  useEffect(() => {
    fetchConfigs();
  }, [fetchConfigs]);

  const handleEdit = (config: SystemConfig) => {
    setEditingKey(config.config_key);
    setEditValue(config.config_value);
  };

  const handleCancel = () => {
    setEditingKey(null);
    setEditValue('');
  };

  const handleSave = async (config: SystemConfig) => {
    if (!editValue.trim()) {
      setError('配置值不能为空');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.updateSystemConfig(config.config_key, {
        config_value: editValue.trim(),
        remark: '从配置列表编辑',
      });
      setEditingKey(null);
      setEditValue('');
      await fetchConfigs();
    } catch (err: any) {
      setError('保存失败: ' + (err.message || '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, config: SystemConfig) => {
    if (e.key === 'Enter') {
      handleSave(config);
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  return (
    <div className="config-list">
      <div className="config-list__header">
        <h3>配置列表</h3>
        <div className="config-list__actions">
          <button
            type="button"
            className="btn btn--primary btn--sm"
            onClick={onOpenAiConfig}
          >
            AI 配置
          </button>
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={fetchConfigs}
            disabled={loading}
          >
            刷新
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠ {error}</span>
          <button type="button" onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="config-list__tabs">
        {(Object.keys(CATEGORY_LABELS) as Category[]).map(cat => (
          <button
            key={cat}
            type="button"
            className={category === cat ? 'tab-btn tab-btn--active' : 'tab-btn'}
            onClick={() => setCategory(cat)}
          >
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading-spinner" />
      ) : (
        <div className="config-table-wrap">
          <table className="config-table">
            <thead>
              <tr>
                <th>配置项</th>
                <th>值</th>
                <th>类型</th>
                <th>描述</th>
                <th>状态</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {configs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="config-table__empty">
                    暂无配置项
                  </td>
                </tr>
              ) : (
                configs.map(config => (
                  <tr key={config.config_key}>
                    <td>
                      <div className="config-key-cell">
                        <code className="config-key">{config.config_key}</code>
                        {config.needs_restart && (
                          <span className="restart-badge" title="修改后需要重启服务才能生效">需重启</span>
                        )}
                      </div>
                    </td>
                    <td className="config-value">
                      {editingKey === config.config_key ? (
                        <input
                          type={config.is_encrypted ? 'password' : 'text'}
                          className="form-input form-input--sm"
                          value={editValue}
                          onChange={e => setEditValue(e.target.value)}
                          onKeyDown={e => handleKeyDown(e, config)}
                          autoFocus
                        />
                      ) : (
                        <span className="config-value__text">
                          {config.is_encrypted ? '••••••••' : config.config_value}
                        </span>
                      )}
                    </td>
                    <td>
                      <span className="config-type-badge">
                        {TYPE_LABELS[config.config_type] || config.config_type}
                      </span>
                    </td>
                    <td className="config-desc">{config.description}</td>
                    <td>
                      <span className={config.is_active ? 'status-badge status-badge--active' : 'status-badge status-badge--inactive'}>
                        {config.is_active ? '启用' : '禁用'}
                      </span>
                    </td>
                    <td className="config-date">
                      {new Date(config.updated_at).toLocaleString('zh-CN')}
                    </td>
                    <td className="config-actions">
                      {editingKey === config.config_key ? (
                        <>
                          <button
                            type="button"
                            className="btn btn--primary btn--xs"
                            onClick={() => handleSave(config)}
                            disabled={saving}
                          >
                            {saving ? '保存中...' : '保存'}
                          </button>
                          <button
                            type="button"
                            className="btn btn--ghost btn--xs"
                            onClick={handleCancel}
                          >
                            取消
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          className="btn btn--ghost btn--xs"
                          onClick={() => handleEdit(config)}
                        >
                          编辑
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ConfigList;
