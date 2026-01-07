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
      if (reassignUserId) {
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
      await workItemApi.reassign(
        task.id,
        currentUser.id,
        reassignUserId,
        comment || undefined
      );
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
      <div className="modal-content modern-layout" onClick={(e) => e.stopPropagation()}>
        {/* 顶部栏：极简信息 */}
        <header className="modern-header">
          <div className="header-left">
            <span className="task-id">#{task.id}</span>
            <span 
              className="status-badge-large"
              style={{ backgroundColor: stateColors[task.current_state] }}
            >
              {stateLabels[task.current_state] || task.current_state}
            </span>
          </div>
          <div className="header-right">
             <button className="icon-btn delete-btn-simple" onClick={handleDelete} title="删除任务">
               🗑
             </button>
             <button className="icon-btn close-btn-simple" onClick={onClose}>
               ✕
             </button>
          </div>
        </header>

        <div className="modern-body">
          {/* 左侧：核心内容与操作 */}
          <div className="main-column">
            <h1 className="task-title">{task.title}</h1>
            
            <div className="meta-grid">
               <div className="meta-item">
                 <label>类型</label>
                 <span>{task.type_code}</span>
               </div>
               <div className="meta-item">
                 <label>创建人</label>
                 <span>{mockUsers.find((u) => u.id === task.creator_id)?.name || task.creator_id}</span>
               </div>
               <div className="meta-item">
                 <label>当前处理</label>
                 <span className="owner-highlight">
                    {currentOwner ? currentOwner.name : "未指派"}
                 </span>
               </div>
            </div>

            <div className="description-box">
              <label>描述</label>
              <p>{task.content || "无描述内容"}</p>
            </div>

            {/* 操作区域 */}
            <div className="action-section">
              <h3>处理任务</h3>
              {loading ? (
                <div className="loading-dots">加载可用操作...</div>
              ) : (
                <div className="action-buttons-grid">
                  {/* 状态流转按钮 */}
                  {transitions?.available_transitions.map((t) => (
                    <button
                      key={t.action}
                      className={`action-chip ${t.action === "REJECT" ? "reject" : "primary"} ${selectedAction === t.action ? "active" : ""}`}
                      onClick={() => {
                          setSelectedAction(selectedAction === t.action ? null : t.action);
                          setReassignUserId(null);
                          setComment("");
                      }}
                    >
                      {t.action}
                      <span className="arrow">→</span>
                      {stateLabels[t.to_state] || t.to_state}
                    </button>
                  ))}
                  
                  {/* 改派按钮 (作为一种特殊操作) */}
                  {reassignableUsers.length > 0 && task.current_state !== "DONE" && (
                     <button 
                       className={`action-chip secondary ${selectedAction === "REASSIGN" ? "active" : ""}`}
                       onClick={() => {
                         setSelectedAction(selectedAction === "REASSIGN" ? null : "REASSIGN");
                         setReassignUserId(null);
                         setComment("");
                       }}
                     >
                       改派任务
                     </button>
                  )}
                </div>
              )}

              {/* 动态操作表单 (展开式) */}
              {selectedAction && selectedAction !== "REASSIGN" && (
                <div className="action-form-panel">
                  {(() => {
                    const t = transitions?.available_transitions.find(tr => tr.action === selectedAction);
                    if (!t) return null;
                    return (
                      <>
                        <div className="form-row">
                           {t.required_fields.includes("target_owner_id") && (
                            <div className="form-field">
                              <label>指派给</label>
                              <select
                                value={reassignUserId || ""}
                                onChange={(e) => setReassignUserId(Number(e.target.value))}
                              >
                                <option value="">选择处理人...</option>
                                {mockUsers
                                  .filter((u) => u.id !== currentUser.id)
                                  .map((user) => (
                                    <option key={user.id} value={user.id}>{user.name}</option>
                                  ))}
                              </select>
                            </div>
                           )}
                           {t.required_fields.includes("priority") && (
                            <div className="form-field">
                              <label>优先级</label>
                              <select value={priority} onChange={(e) => setPriority(e.target.value)}>
                                <option value="">选择...</option>
                                <option value="P0">P0 - 紧急</option>
                                <option value="P1">P1 - 高</option>
                                <option value="P2">P2 - 中</option>
                              </select>
                            </div>
                           )}
                        </div>
                        <div className="form-field">
                           <input 
                             type="text" 
                             placeholder="添加备注..." 
                             value={comment}
                             onChange={(e) => setComment(e.target.value)}
                             className="simple-input"
                           />
                        </div>
                        <div className="form-actions">
                           <button className="confirm-btn" onClick={() => handleTransition(t.action)} disabled={transitionLoading}>
                             {transitionLoading ? "提交中..." : "确认流转"}
                           </button>
                        </div>
                      </>
                    );
                  })()}
                </div>
              )}

              {/* 改派表单 */}
              {selectedAction === "REASSIGN" && (
                 <div className="action-form-panel">
                    <div className="form-field">
                      <label>改派给</label>
                      <select
                        value={reassignUserId || ""}
                        onChange={(e) => setReassignUserId(Number(e.target.value))}
                      >
                        <option value="">选择新处理人...</option>
                        {reassignableUsers.map((user) => (
                          <option key={user.id} value={user.id}>{user.name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="form-field">
                         <input 
                           type="text" 
                           placeholder="改派备注..." 
                           value={comment}
                           onChange={(e) => setComment(e.target.value)}
                           className="simple-input"
                         />
                    </div>
                    <div className="form-actions">
                       <button className="confirm-btn" onClick={handleReassign} disabled={reassignLoading || !reassignUserId}>
                         {reassignLoading ? "提交中..." : "确认改派"}
                       </button>
                    </div>
                 </div>
              )}
            </div>
          </div>

          {/* 右侧：时间轴 */}
          <div className="timeline-column">
             <h3>流转时间轴</h3>
             <div className="timeline-container">
               {logs.length === 0 ? (
                 <div className="empty-timeline">暂无记录</div>
               ) : (
                 logs.map((log, index) => (
                   <div key={log.id} className="timeline-item">
                     <div className="timeline-line"></div>
                     <div className="timeline-dot" style={{ backgroundColor: stateColors[log.to_state] }}></div>
                     <div className="timeline-content">
                        <div className="timeline-header">
                           <span className="timeline-action">{log.action}</span>
                           <span className="timeline-date">{new Date(log.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                        </div>
                        <div className="timeline-desc">
                           {mockUsers.find((u) => u.id === log.operator_id)?.name || log.operator_id} 
                           <span className="state-arrow"> {stateLabels[log.from_state]} → {stateLabels[log.to_state]}</span>
                        </div>
                        {log.payload?.remark && (
                          <div className="timeline-remark">“{log.payload.remark}”</div>
                        )}
                     </div>
                   </div>
                 ))
               )}
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TaskDetailModal;
