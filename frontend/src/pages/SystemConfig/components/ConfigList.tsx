import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../../../services/api';
import type { SystemConfig } from '../../../types';
import RedisConfigModal from './RedisConfigModal';
import KafkaConfigModal from './KafkaConfigModal';

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

function summarizeJsonArray(jsonStr: string): string {
  try {
    const arr = JSON.parse(jsonStr);
    return Array.isArray(arr) ? arr.join(', ') : jsonStr;
  } catch {
    return jsonStr;
  }
}

function latestUpdatedAt(configs: SystemConfig[]): string {
  if (configs.length === 0) return '';
  return configs.reduce((latest, c) => c.updated_at > latest ? c.updated_at : latest, configs[0].updated_at);
}

interface ConfigListProps {}

const ConfigList: React.FC<ConfigListProps> = ({}) => {
  const [allConfigs, setAllConfigs] = useState<SystemConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState<Category>('all');
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);

  // 弹窗状态
  const [redisModalVisible, setRedisModalVisible] = useState(false);
  const [kafkaModalVisible, setKafkaModalVisible] = useState(false);

  // 从 allConfigs 中分离 redis.*、kafka.* 和普通配置
  const { redisConfigs, kafkaConfigs, normalConfigs } = useMemo(() => {
    const redis: SystemConfig[] = [];
    const kafka: SystemConfig[] = [];
    const normal: SystemConfig[] = [];
    for (const cfg of allConfigs) {
      if (cfg.config_key.startsWith('redis.')) {
        redis.push(cfg);
      } else if (cfg.config_key.startsWith('kafka.')) {
        kafka.push(cfg);
      } else {
        normal.push(cfg);
      }
    }
    return { redisConfigs: redis, kafkaConfigs: kafka, normalConfigs: normal };
  }, [allConfigs]);

  // Redis 摘要
  const redisSummary = useMemo(() => {
    const hostsCfg = redisConfigs.find(c => c.config_key === 'redis.sentinel_hosts');
    const masterCfg = redisConfigs.find(c => c.config_key === 'redis.master_name');
    const hosts = hostsCfg ? summarizeJsonArray(hostsCfg.config_value) : '默认';
    const master = masterCfg?.config_value || 'redis_master';
    return `节点: ${hosts} | Master: ${master}`;
  }, [redisConfigs]);

  const redisUpdatedAt = useMemo(() => latestUpdatedAt(redisConfigs), [redisConfigs]);

  // Kafka 摘要
  const kafkaSummary = useMemo(() => {
    const serversCfg = kafkaConfigs.find(c => c.config_key === 'kafka.bootstrap_servers');
    const topicCfg = kafkaConfigs.find(c => c.config_key === 'kafka.result_topic');
    const servers = serversCfg ? summarizeJsonArray(serversCfg.config_value) : '默认';
    const topic = topicCfg?.config_value || 'dmlv4.results';
    return `Broker: ${servers} | Topic: ${topic}`;
  }, [kafkaConfigs]);

  const kafkaUpdatedAt = useMemo(() => latestUpdatedAt(kafkaConfigs), [kafkaConfigs]);

  const fetchConfigs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getSystemConfigs({
        category: category === 'all' ? undefined : category,
        active_only: false,
      });
      setAllConfigs(res.data?.items || []);
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
    if (e.key === 'Enter') handleSave(config);
    else if (e.key === 'Escape') handleCancel();
  };

  const showInTable = category === 'all' || category === 'system';

  return (
    <div className="config-list">
      <div className="config-list__header">
        <h3>配置列表</h3>
        <div className="config-list__actions">
          <button type="button" className="btn btn--secondary btn--sm" onClick={fetchConfigs} disabled={loading}>
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
              {/* ── Redis 合并行 ── */}
              {showInTable && redisConfigs.length > 0 && (
                <tr key="__redis_group__" className="config-row--group">
                  <td>
                    <div className="config-key-cell">
                      <code className="config-key config-key--group">Redis 配置</code>
                      <span className="restart-badge" title="修改后需要重启服务才能生效">需重启</span>
                    </div>
                  </td>
                  <td className="config-value">
                    <span className="config-value__text config-value--summary">{redisSummary}</span>
                  </td>
                  <td><span className="config-type-badge">组合</span></td>
                  <td className="config-desc">Redis 连接参数（节点、用户名、密码等）</td>
                  <td><span className="status-badge status-badge--active">启用</span></td>
                  <td className="config-date">
                    {redisUpdatedAt ? new Date(redisUpdatedAt).toLocaleString('zh-CN') : '-'}
                  </td>
                  <td className="config-actions">
                    <button type="button" className="btn btn--ghost btn--xs" onClick={() => setRedisModalVisible(true)}>编辑</button>
                  </td>
                </tr>
              )}

              {/* ── Kafka 合并行 ── */}
              {showInTable && kafkaConfigs.length > 0 && (
                <tr key="__kafka_group__" className="config-row--group">
                  <td>
                    <div className="config-key-cell">
                      <code className="config-key config-key--group">Kafka 配置</code>
                      <span className="restart-badge" title="bootstrap_servers/client_id 修改后需要重启">需重启</span>
                    </div>
                  </td>
                  <td className="config-value">
                    <span className="config-value__text config-value--summary">{kafkaSummary}</span>
                  </td>
                  <td><span className="config-type-badge">组合</span></td>
                  <td className="config-desc">Kafka 连接参数（Broker、Topic、Consumer Group 等）</td>
                  <td><span className="status-badge status-badge--active">启用</span></td>
                  <td className="config-date">
                    {kafkaUpdatedAt ? new Date(kafkaUpdatedAt).toLocaleString('zh-CN') : '-'}
                  </td>
                  <td className="config-actions">
                    <button type="button" className="btn btn--ghost btn--xs" onClick={() => setKafkaModalVisible(true)}>编辑</button>
                  </td>
                </tr>
              )}

              {/* ── 普通配置项 ── */}
              {normalConfigs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="config-table__empty">
                    {showInTable && (redisConfigs.length > 0 || kafkaConfigs.length > 0)
                      ? '暂无其他配置项'
                      : '暂无配置项'}
                  </td>
                </tr>
              ) : (
                normalConfigs.map(config => (
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
                    <td><span className="config-type-badge">{TYPE_LABELS[config.config_type] || config.config_type}</span></td>
                    <td className="config-desc">{config.description}</td>
                    <td>
                      <span className={config.is_active ? 'status-badge status-badge--active' : 'status-badge status-badge--inactive'}>
                        {config.is_active ? '启用' : '禁用'}
                      </span>
                    </td>
                    <td className="config-date">{new Date(config.updated_at).toLocaleString('zh-CN')}</td>
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

      <RedisConfigModal
        visible={redisModalVisible}
        configs={redisConfigs}
        onClose={() => setRedisModalVisible(false)}
        onSaved={fetchConfigs}
      />
      <KafkaConfigModal
        visible={kafkaModalVisible}
        configs={kafkaConfigs}
        onClose={() => setKafkaModalVisible(false)}
        onSaved={fetchConfigs}
      />
    </div>
  );
};

export default ConfigList;
