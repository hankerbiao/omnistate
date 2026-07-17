import { useState, useEffect } from 'react';
import { api } from '../../../services/api';
import type { SystemConfig } from '../../../types';

interface KafkaConfigModalProps {
  visible: boolean;
  configs: SystemConfig[];
  onClose: () => void;
  onSaved: () => void;
}

interface KafkaFormData {
  bootstrap_servers: string;
  client_id: string;
  result_topic: string;
  dead_letter_topic: string;
  test_events_topic: string;
  execution_result_group_id: string;
  test_events_group_id: string;
  producer_options: string;
  consumer_options: string;
}

type FormSection = 'connection' | 'topics' | 'consumer' | 'advanced';

interface SectionDef {
  key: FormSection;
  label: string;
  hint: string | null;
  fields: (keyof KafkaFormData)[];
}

const SECTIONS: SectionDef[] = [
  {
    key: 'connection',
    label: '连接配置（需重启生效）',
    hint: null,
    fields: ['bootstrap_servers', 'client_id'],
  },
  {
    key: 'topics',
    label: 'Topic 配置',
    hint: '修改后新创建的 Producer/Consumer 自动使用新 Topic',
    fields: ['result_topic', 'dead_letter_topic', 'test_events_topic'],
  },
  {
    key: 'consumer',
    label: 'Consumer Group 配置',
    hint: '修改后新启动的 Consumer 自动使用新 Group ID',
    fields: ['execution_result_group_id', 'test_events_group_id'],
  },
  {
    key: 'advanced',
    label: '高级选项',
    hint: 'JSON 格式，修改后新连接自动生效',
    fields: ['producer_options', 'consumer_options'],
  },
];

const FIELD_LABELS: Record<keyof KafkaFormData, string> = {
  bootstrap_servers: 'Broker 节点',
  client_id: '客户端 ID',
  result_topic: '执行结果 Topic',
  dead_letter_topic: '死信 Topic',
  test_events_topic: '测试事件 Topic',
  execution_result_group_id: '执行结果 Group ID',
  test_events_group_id: '测试事件 Group ID',
  producer_options: 'Producer 选项',
  consumer_options: 'Consumer 选项',
};

const FIELD_PLACEHOLDERS: Record<keyof KafkaFormData, string> = {
  bootstrap_servers: 'host1:9092, host2:9092',
  client_id: 'dmlv4-shard',
  result_topic: 'dmlv4.results',
  dead_letter_topic: 'dmlv4.deadletter',
  test_events_topic: 'dml-test-event',
  execution_result_group_id: 'dmlv4-execution-result-consumers',
  test_events_group_id: 'dmlv4-test-events-consumers',
  producer_options: '{ "acks": "all", "retries": 3 }',
  consumer_options: '{ "auto_offset_reset": "earliest" }',
};

/** 将 JSON 数组字符串转为逗号分隔的显示文本 */
function formatJsonArray(jsonStr: string): string {
  try {
    const arr = JSON.parse(jsonStr);
    return Array.isArray(arr) ? arr.join(', ') : jsonStr;
  } catch {
    return jsonStr;
  }
}

/** 将逗号分隔的文本转为 JSON 数组字符串 */
function parseJsonArray(text: string): string {
  const items = text
    .split(/[,\s]+/)
    .map(s => s.trim())
    .filter(Boolean);
  return JSON.stringify(items);
}

function getConfigValue(configs: SystemConfig[], key: string, defaultValue: string): string {
  return configs.find(c => c.config_key === key)?.config_value ?? defaultValue;
}

const KafkaConfigModal: React.FC<KafkaConfigModalProps> = ({ visible, configs, onClose, onSaved }) => {
  const [form, setForm] = useState<KafkaFormData>({
    bootstrap_servers: '',
    client_id: '',
    result_topic: '',
    dead_letter_topic: '',
    test_events_topic: '',
    execution_result_group_id: '',
    test_events_group_id: '',
    producer_options: '{}',
    consumer_options: '{}',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!visible) return;
    const serversRaw = getConfigValue(configs, 'kafka.bootstrap_servers', '["localhost:9092"]');
    setForm({
      bootstrap_servers: formatJsonArray(serversRaw),
      client_id: getConfigValue(configs, 'kafka.client_id', 'dmlv4-shard'),
      result_topic: getConfigValue(configs, 'kafka.result_topic', 'dmlv4.results'),
      dead_letter_topic: getConfigValue(configs, 'kafka.dead_letter_topic', 'dmlv4.deadletter'),
      test_events_topic: getConfigValue(configs, 'kafka.test_events_topic', 'dml-test-event'),
      execution_result_group_id: getConfigValue(configs, 'kafka.execution_result_group_id', 'dmlv4-execution-result-consumers'),
      test_events_group_id: getConfigValue(configs, 'kafka.test_events_group_id', 'dmlv4-test-events-consumers'),
      producer_options: getConfigValue(configs, 'kafka.producer_options', '{"acks":"all","retries":3}'),
      consumer_options: getConfigValue(configs, 'kafka.consumer_options', '{"auto_offset_reset":"earliest"}'),
    });
    setError(null);
  }, [visible, configs]);

  const handleChange = (field: keyof KafkaFormData, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }));
    setError(null);
  };

  /** 尝试验证 JSON 字符串 */
  const tryParseJson = (label: string, value: string): string | null => {
    if (!value.trim()) return null;
    try {
      JSON.parse(value);
      return null;
    } catch {
      return `${label} 格式无效，请输入合法 JSON`;
    }
  };

  const handleSave = async () => {
    // 基本验证
    if (!form.bootstrap_servers.trim()) {
      setError('Broker 节点不能为空');
      return;
    }
    if (!form.client_id.trim()) {
      setError('客户端 ID 不能为空');
      return;
    }

    // JSON 验证
    const jsonErrors = [
      tryParseJson('Producer 选项', form.producer_options),
      tryParseJson('Consumer 选项', form.consumer_options),
    ].filter(Boolean) as string[];
    if (jsonErrors.length > 0) {
      setError(jsonErrors.join('; '));
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await api.batchUpdateSystemConfigs({
        items: [
          { config_key: 'kafka.bootstrap_servers', config_value: parseJsonArray(form.bootstrap_servers) },
          { config_key: 'kafka.client_id', config_value: form.client_id.trim() },
          { config_key: 'kafka.result_topic', config_value: form.result_topic.trim() },
          { config_key: 'kafka.dead_letter_topic', config_value: form.dead_letter_topic.trim() },
          { config_key: 'kafka.test_events_topic', config_value: form.test_events_topic.trim() },
          { config_key: 'kafka.execution_result_group_id', config_value: form.execution_result_group_id.trim() },
          { config_key: 'kafka.test_events_group_id', config_value: form.test_events_group_id.trim() },
          { config_key: 'kafka.producer_options', config_value: form.producer_options.trim() },
          { config_key: 'kafka.consumer_options', config_value: form.consumer_options.trim() },
        ],
        remark: '从 Kafka 配置弹窗编辑',
      });
      onSaved();
      onClose();
    } catch (err: any) {
      setError('保存失败: ' + (err.message || '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  if (!visible) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content kafka-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Kafka 配置</h3>
          <button type="button" className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          {error && (
            <div className="error-banner">
              <span>⚠ {error}</span>
              <button type="button" onClick={() => setError(null)}>×</button>
            </div>
          )}

          {SECTIONS.map(section => (
            <div className="kafka-section" key={section.key}>
              <h4 className="kafka-section__title">{section.label}</h4>
              {section.hint && (
                <p className="kafka-section__hint">{section.hint}</p>
              )}
              {section.fields.map(field => (
                <div className="form-field" key={field}>
                  <label className="form-field__label">{FIELD_LABELS[field]}</label>
                  {field === 'producer_options' || field === 'consumer_options' ? (
                    <textarea
                      className="form-input form-textarea"
                      value={form[field]}
                      onChange={e => handleChange(field, e.target.value)}
                      placeholder={FIELD_PLACEHOLDERS[field]}
                      rows={4}
                    />
                  ) : (
                    <input
                      type="text"
                      className="form-input"
                      value={form[field]}
                      onChange={e => handleChange(field, e.target.value)}
                      placeholder={FIELD_PLACEHOLDERS[field]}
                    />
                  )}
                  {field === 'bootstrap_servers' && (
                    <span className="form-hint">格式: host1:port1, host2:port2 (逗号或空格分隔)</span>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn--ghost" onClick={onClose}>取消</button>
          <button type="button" className="btn btn--primary" onClick={handleSave} disabled={saving}>
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default KafkaConfigModal;
