import { useState, useEffect } from "react";
import {
  workItemApi,
  type WorkItem,
  type AvailableTransitionsResponse,
  type TransitionLog,
  stateLabels,
  stateColors,
} from "../services/api";
import { useUser } from "../context/UserContext";
import { mockUsers } from "../services/mockUsers";
import "./TaskDetailModal.css";

interface TaskDetailModalProps {
  task: WorkItem;
  onClose: () => void;
  onRefresh: () => void;
}

const TaskDetailModal: React.FC<TaskDetailModalProps> = ({
  task,
  onClose,
  onRefresh,
}) => {
  const { currentUser } = useUser();
  const [transitions, setTransitions] = useState<AvailableTransitionsResponse | null>(null);
  const [logs, setLogs] = useState<TransitionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [transitionLoading, setTransitionLoading] = useState(false);
  const [reassignLoading, setReassignLoading] = useState(false);
  const [selectedAction, setSelectedAction] = useState<string | null>(null);
  const [reassignUserId, setReassignUserId] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [priority, setPriority] = useState<string>("");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [transData, logData] = await Promise.all([
          workItemApi.getAvailableTransitions(task.id),
          workItemApi.getLogs(task.id),
        ]);
        setTransitions(transData);
        setLogs(logData);
      } catch (err: any) {
        console.error("获取数据失败:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [task.id]);

  const handleTransition = async (action: string) => {
    setTransitionLoading(true);
    try {
      const formData: Record<string, any> = {};
      if (reassignUserId && action !== "REJECT") {
        formData.target_owner_id = reassignUserId;
      }
      if (comment) {
        formData.comment = comment;
      }
      if (priority) {
        formData.priority = priority;
      }

      await workItemApi.transition(task.id, action, currentUser.id, formData);
      onRefresh();
      onClose();
    } catch (err: any) {
      alert(err.response?.data?.detail || "操作失败");
    } finally {
      setTransitionLoading(false);
    }
  };

  // 获取目标处理人显示名称
  const getTargetOwnerDisplay = (strategy: string, selectedId?: number): string => {
    switch (strategy) {
      case "KEEP":
        return currentOwner ? currentOwner.name : "当前处理人";
      case "TO_CREATOR":
        const creator = mockUsers.find((u) => u.id === task.creator_id);
        return creator ? creator.name : "创建者";
      case "TO_SPECIFIC_USER":
        if (selectedId) {
          const user = mockUsers.find((u) => u.id === selectedId);
          return user ? user.name : `用户 ${selectedId}`;
        }
        return "(请选择)";
      default:
        return "未知";
    }
  };

  const handleReassign = async () => {
    if (!reassignUserId) {
      alert("请选择要改派给的用户");
      return;
    }
    setReassignLoading(true);
    try {
      await workItemApi.reassign(task.id, currentUser.id, reassignUserId);
      onRefresh();
      onClose();
    } catch (err: any) {
      alert(err.response?.data?.detail || "改派失败");
    } finally {
      setReassignLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`确定要删除任务「${task.title}」吗？此操作不可恢复。`)) {
      return;
    }
    try {
      await workItemApi.delete(task.id);
      onRefresh();
      onClose();
    } catch (err: any) {
      alert(err.response?.data?.detail || "删除失败");
    }
  };

  // 获取当前处理人
  const currentOwner = task.current_owner_id
    ? mockUsers.find((u) => u.id === task.current_owner_id)
    : null;

  // 可以改派给的用户（排除当前处理人）
  const reassignableUsers = mockUsers.filter(
    (u) => u.id !== currentUser.id && u.id !== task.current_owner_id
  );

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>任务详情</h2>
          <div className="header-actions">
            <button className="delete-btn" onClick={handleDelete}>
              删除任务
            </button>
            <button className="close-btn" onClick={onClose}>
              ×
            </button>
          </div>
        </div>

        <div className="modal-body">
          {/* 基本信息 */}
          <div className="task-info">
            <div className="info-row">
              <span className="label">ID:</span>
              <span>#{task.id}</span>
            </div>
            <div className="info-row">
              <span className="label">类型:</span>
              <span>{task.type_code}</span>
            </div>
            <div className="info-row">
              <span className="label">状态:</span>
              <span
                className="state-badge"
                style={{ backgroundColor: stateColors[task.current_state] }}
              >
                {stateLabels[task.current_state] || task.current_state}
              </span>
            </div>
            <div className="info-row">
              <span className="label">标题:</span>
              <span>{task.title}</span>
            </div>
            <div className="info-row">
              <span className="label">内容:</span>
              <p>{task.content}</p>
            </div>
            <div className="info-row">
              <span className="label">当前处理人:</span>
              <span>
                {currentOwner
                  ? `${currentOwner.name} (${currentOwner.role})`
                  : `用户 ${task.current_owner_id}`}
              </span>
            </div>
            <div className="info-row">
              <span className="label">创建者:</span>
              <span>
                {mockUsers.find((u) => u.id === task.creator_id)?.name ||
                  `用户 ${task.creator_id}`}
              </span>
            </div>
          </div>

          {/* 改派操作（独立区域，不走工作流配置） */}
          {reassignableUsers.length > 0 && task.current_state !== "DONE" && (
            <div className="reassign-section">
              <h3>改派任务</h3>
              <div className="reassign-form">
                <div className="form-group">
                  <label>指派给:</label>
                  <select
                    value={reassignUserId || ""}
                    onChange={(e) => setReassignUserId(Number(e.target.value))}
                  >
                    <option value="">请选择用户</option>
                    {reassignableUsers.map((user) => (
                      <option key={user.id} value={user.id}>
                        {user.name} - {user.role}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  className="submit-btn reassign-btn"
                  onClick={handleReassign}
                  disabled={reassignLoading || !reassignUserId}
                >
                  {reassignLoading ? "改派中..." : "确认改派"}
                </button>
              </div>
            </div>
          )}

          {/* 可执行操作 */}
          {loading ? (
            <div className="loading">加载中...</div>
          ) : (
            <div className="transitions-section">
              <h3>状态流转</h3>
              {transitions?.available_transitions.length === 0 ? (
                <p className="no-action">当前状态无可执行操作</p>
              ) : (
                <div className="action-list">
                  {transitions?.available_transitions.map((t) => (
                    <div key={t.action} className="action-item">
                      <button
                        className={`action-btn ${
                          selectedAction === t.action ? "selected" : ""
                        } ${t.action === "REJECT" ? "action-reject" : ""}`}
                        onClick={() => {
                          setSelectedAction(t.action);
                          // 重置相关字段
                          setReassignUserId(null);
                          setComment("");
                        }}
                      >
                        <span className="action-main">
                          {t.action} → {stateLabels[t.to_state] || t.to_state}
                        </span>
                        <span className="action-owner">
                          → {getTargetOwnerDisplay(t.target_owner_strategy, reassignUserId || undefined)}
                        </span>
                      </button>
                      {selectedAction === t.action && (
                        <div className="action-form">
                          {t.required_fields.includes("target_owner_id") && (
                            <div className="form-group">
                              <label>指派给:</label>
                              <select
                                value={reassignUserId || ""}
                                onChange={(e) =>
                                  setReassignUserId(Number(e.target.value))
                                }
                              >
                                <option value="">请选择用户</option>
                                {mockUsers
                                  .filter((u) => u.id !== currentUser.id)
                                  .map((user) => (
                                    <option key={user.id} value={user.id}>
                                      {user.name} - {user.role}
                                    </option>
                                  ))}
                              </select>
                            </div>
                          )}
                          {t.required_fields.includes("priority") && (
                            <div className="form-group">
                              <label>优先级:</label>
                              <select
                                value={priority}
                                onChange={(e) => setPriority(e.target.value)}
                              >
                                <option value="">请选择优先级</option>
                                <option value="P0">P0 - 紧急</option>
                                <option value="P1">P1 - 高</option>
                                <option value="P2">P2 - 中</option>
                                <option value="P3">P3 - 低</option>
                              </select>
                            </div>
                          )}
                          {t.required_fields.includes("comment") && (
                            <div className="form-group">
                              <label>备注:</label>
                              <textarea
                                value={comment}
                                onChange={(e) => setComment(e.target.value)}
                                placeholder="请输入备注"
                              />
                            </div>
                          )}
                          <button
                            className="submit-btn"
                            onClick={() => handleTransition(t.action)}
                            disabled={transitionLoading}
                          >
                            {transitionLoading ? "处理中..." : "确认执行"}
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 操作历史 */}
          <div className="logs-section">
            <h3>操作历史</h3>
            {logs.length === 0 ? (
              <p className="no-logs">暂无操作记录</p>
            ) : (
              <div className="log-list">
                {logs.map((log) => (
                  <div key={log.id} className="log-item">
                    <div className="log-header">
                      <span
                        className="log-state"
                        style={{ backgroundColor: stateColors[log.from_state] }}
                      >
                        {stateLabels[log.from_state] || log.from_state}
                      </span>
                      <span className="log-action">{log.action}</span>
                      <span
                        className="log-state"
                        style={{ backgroundColor: stateColors[log.to_state] }}
                      >
                        {stateLabels[log.to_state] || log.to_state}
                      </span>
                    </div>
                    <div className="log-meta">
                      <span>
                        操作人:{" "}
                        {mockUsers.find((u) => u.id === log.operator_id)?.name ||
                          `用户 ${log.operator_id}`}
                      </span>
                      <span>
                        {new Date(log.created_at).toLocaleString("zh-CN")}
                      </span>
                    </div>
                    {log.payload && Object.keys(log.payload).length > 0 && (
                      <pre className="log-payload">
                        {JSON.stringify(log.payload, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TaskDetailModal;