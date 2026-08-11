import { useState, useEffect, useCallback } from 'react';
import {
  Bell,
  Bot,
  Database,
  HardDrive,
  KeyRound,
  LayoutGrid,
  Play,
  Radio,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  X,
  type LucideIcon,
} from 'lucide-react';
import { api } from '../../../services/api';
import { getErrorMessage } from '../../../utils/errors';
import type { SystemConfig } from '../../../types';

const CATEGORY_LABELS: Record<string, string> = {
  all: '全部',
  ai: 'AI 配置',
  rabbitmq: 'RabbitMQ',
  kafka: 'Kafka',
  redis: 'Redis',
  minio: 'MinIO',
  jwt: 'JWT',
  execution: '执行配置',
  notification: '通知配置',
  open_platform_gateway_jwt: '开放平台 JWT',
};

const CATEGORY_ORDER = [
  'ai',
  'execution',
  'jwt',
  'open_platform_gateway_jwt',
  'rabbitmq',
  'kafka',
  'redis',
  'minio',
  'notification',
];

const CATEGORY_ICONS: Record<string, LucideIcon> = {
  all: LayoutGrid,
  ai: Bot,
  execution: Play,
  jwt: KeyRound,
  open_platform_gateway_jwt: ShieldCheck,
  rabbitmq: Send,
  kafka: Radio,
  redis: Database,
  minio: HardDrive,
  notification: Bell,
};

const TYPE_LABELS: Record<string, string> = {
  string: '字符串',
  integer: '整数',
  float: '浮点数',
  boolean: '布尔',
  json: 'JSON',
};

const ConfigList: React.FC = () => {
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [environment, setEnvironment] = useState('');
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchConfigs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getSystemConfigs({ active_only: false });
      setConfigs(res.data?.items || []);
      setEnvironment(res.data?.environment || '');
    } catch (err) {
      setError(getErrorMessage(err, '获取配置失败'));
    } finally {
      setLoading(false);
    }
  }, []);

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
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await api.updateSystemConfig(config.config_key, {
        config_value: editValue,
        remark: '从配置列表编辑',
      });
      setSuccess(config.needs_restart ? '配置已保存，重启后端后生效' : '配置已保存并生效');
      setEditingKey(null);
      setEditValue('');
      await fetchConfigs();
    } catch (err) {
      setError(getErrorMessage(err, '保存失败'));
    } finally {
      setSaving(false);
    }
  };

  const availableCategories = new Set(configs.map(item => item.category));
  const knownCategories = CATEGORY_ORDER.filter(item => availableCategories.has(item));
  const unknownCategories = Array.from(availableCategories)
    .filter(item => !CATEGORY_ORDER.includes(item))
    .sort();
  const categories = ['all', ...knownCategories, ...unknownCategories];
  const categoryCounts = configs.reduce<Record<string, number>>((counts, item) => {
    counts[item.category] = (counts[item.category] || 0) + 1;
    return counts;
  }, { all: configs.length });
  const categoryConfigs = category === 'all'
    ? configs
    : configs.filter(item => item.category === category);
  const normalizedSearch = searchQuery.trim().toLocaleLowerCase('zh-CN');
  const visibleConfigs = normalizedSearch
    ? categoryConfigs.filter(item => [
        item.config_key,
        item.description,
        item.category,
        CATEGORY_LABELS[item.category] || '',
      ].some(value => value.toLocaleLowerCase('zh-CN').includes(normalizedSearch)))
    : categoryConfigs;

  const renderEditor = (config: SystemConfig) => {
    if (config.config_type === 'boolean') {
      return (
        <select
          className="form-input form-input--sm"
          value={editValue}
          onChange={event => setEditValue(event.target.value)}
          autoFocus
        >
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      );
    }
    if (config.config_type === 'json') {
      return (
        <textarea
          className="form-input form-input--sm config-json-editor"
          value={editValue}
          onChange={event => setEditValue(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'Escape') handleCancel();
          }}
          autoFocus
        />
      );
    }
    return (
      <input
        type={config.config_type === 'integer' || config.config_type === 'float' ? 'number' : 'text'}
        step={config.config_type === 'float' ? 'any' : undefined}
        className="form-input form-input--sm"
        value={editValue}
        onChange={event => setEditValue(event.target.value)}
        onKeyDown={event => handleKeyDown(event, config)}
        autoFocus
      />
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent, config: SystemConfig) => {
    if (e.key === 'Enter') handleSave(config);
    else if (e.key === 'Escape') handleCancel();
  };

  return (
    <div className="config-list">
      <div className="config-list__header">
        <div className="config-list__title">
          <h3>运行时配置</h3>
          {environment && <span className="environment-badge">{environment}</span>}
        </div>
        <div className="config-list__actions">
          <div className="config-search">
            <Search className="config-search__icon" size={16} aria-hidden="true" />
            <input
              type="search"
              value={searchQuery}
              onChange={event => setSearchQuery(event.target.value)}
              onKeyDown={event => {
                if (event.key === 'Escape') setSearchQuery('');
              }}
              className="config-search__input"
              placeholder="搜索配置键或描述"
              aria-label="搜索配置"
            />
            {searchQuery && (
              <button
                type="button"
                className="config-search__clear"
                onClick={() => setSearchQuery('')}
                title="清除搜索"
                aria-label="清除搜索"
              >
                <X size={15} aria-hidden="true" />
              </button>
            )}
          </div>
          <button type="button" className="btn btn--secondary btn--sm" onClick={fetchConfigs} disabled={loading}>
            刷新
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)}>×</button>
        </div>
      )}

      {success && (
        <div className="success-banner">
          <span>{success}</span>
          <button type="button" onClick={() => setSuccess(null)}>×</button>
        </div>
      )}

      <div className="config-list__tabs">
        {categories.map(cat => {
          const CategoryIcon = CATEGORY_ICONS[cat] || Settings2;
          const isActive = category === cat;
          return (
            <button
              key={cat}
              type="button"
              className={isActive ? 'config-filter-button config-filter-button--active' : 'config-filter-button'}
              onClick={() => setCategory(cat)}
              aria-pressed={isActive}
            >
              <CategoryIcon size={15} aria-hidden="true" />
              <span>{CATEGORY_LABELS[cat] || cat}</span>
              <span className="config-filter-button__count">{categoryCounts[cat] || 0}</span>
            </button>
          );
        })}
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
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {visibleConfigs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="config-table__empty">
                    {normalizedSearch ? '未找到匹配的配置项' : '暂无配置项'}
                  </td>
                </tr>
              ) : (
                visibleConfigs.map(config => (
                  <tr key={config.config_key}>
                    <td>
                      <div className="config-key-cell">
                        <code className="config-key">{config.config_key}</code>
                        {config.pending_restart && <span className="restart-badge">待重启</span>}
                      </div>
                    </td>
                    <td className="config-value">
                      {editingKey === config.config_key ? (
                        renderEditor(config)
                      ) : (
                        <span className="config-value__text">
                          {config.config_value}
                        </span>
                      )}
                    </td>
                    <td><span className="config-type-badge">{TYPE_LABELS[config.config_type] || config.config_type}</span></td>
                    <td className="config-desc">{config.description}</td>
                    <td>
                      <span className={config.is_active ? 'status-badge status-badge--active' : 'status-badge status-badge--inactive'}>
                        {config.is_active ? (config.needs_restart ? '重启生效' : '热更新') : '禁用'}
                      </span>
                    </td>
                    <td className="config-actions">
                      {editingKey === config.config_key ? (
                        <>
                          <button type="button" className="btn btn--primary btn--xs" onClick={() => handleSave(config)} disabled={saving}>
                            {saving ? '保存中...' : '保存'}
                          </button>
                          <button type="button" className="btn btn--ghost btn--xs" onClick={handleCancel}>取消</button>
                        </>
                      ) : (
                        <button type="button" className="btn btn--ghost btn--xs" onClick={() => handleEdit(config)}>编辑</button>
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
