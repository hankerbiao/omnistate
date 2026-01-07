import { useState, useEffect } from "react";
import {
  workItemApi,
  type WorkItem,
  type TransitionLog,
  stateLabels,
  stateColors,
} from "../services/api";
import { useUser } from "../context/UserContext";
import { mockUsers } from "../services/mockUsers";
import TaskDetailModal from "./TaskDetailModal";
import "./TaskList.css";

const TaskList: React.FC = () => {
  const { currentUser } = useUser();
  const [tasks, setTasks] = useState<WorkItem[]>([]);
  const [logsMap, setLogsMap] = useState<Record<number, TransitionLog[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<WorkItem | null>(null);
  const [filterState, setFilterState] = useState<string>("all");
  const [expandedTasks, setExpandedTasks] = useState<Set<number>>(new Set());
  const [sortField, setSortField] = useState<"created_at" | "updated_at" | "title">(
    "created_at"
  );
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [searchKeyword, setSearchKeyword] = useState<string>("");

  const loadTasks = async (fetcher: () => Promise<WorkItem[]>) => {
    try {
      setLoading(true);
      const data = await fetcher();
      setTasks(data);
      setError(null);

      if (data.length > 0) {
        const itemIds = data.map((t) => t.id);
        const logs = await workItemApi.batchGetLogs(itemIds);
        setLogsMap(logs);
      }
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message || "获取任务列表失败");
      } else {
        setError("获取任务列表失败");
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchTasks = async () => {
    await loadTasks(() =>
      workItemApi.list({
        ownerId: currentUser.id,
        creatorId: currentUser.id,
        limit: 100,
      })
    );
  };

  const applySortedQuery = async () => {
    await loadTasks(() =>
      workItemApi.sortedList({
        ownerId: currentUser.id,
        creatorId: currentUser.id,
        limit: 100,
        orderBy: sortField,
        direction: sortDirection,
      })
    );
  };

  const applySearch = async () => {
    const keyword = searchKeyword.trim();
    if (!keyword) {
      return;
    }
    await loadTasks(() =>
      workItemApi.search({
        keyword,
        ownerId: currentUser.id,
        creatorId: currentUser.id,
        limit: 100,
      })
    );
  };

  useEffect(() => {
    fetchTasks();
  }, [currentUser.id]);

  const filteredTasks =
    filterState === "all"
      ? tasks
      : tasks.filter((t) => t.current_state === filterState);

  const taskCounts = tasks.reduce(
    (acc, task) => {
      acc[task.current_state] = (acc[task.current_state] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  // 展开/收起任务详情
  const toggleExpand = (e: React.MouseEvent, taskId: number) => {
    e.stopPropagation();
    setExpandedTasks((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(taskId)) {
        newSet.delete(taskId);
      } else {
        newSet.add(taskId);
      }
      return newSet;
    });
  };

  // 构建状态流转路径（从创建到当前）
  const getStateFlow = (task: WorkItem): { state: string; label: string }[] => {
    const logs = logsMap[task.id] || [];
    const flow: { state: string; label: string }[] = [];

    // 初始状态是 DRAFT
    flow.push({ state: "DRAFT", label: "草稿" });

    // 按时间顺序添加所有流转记录
    for (const log of logs) {
      flow.push({ state: log.to_state, label: stateLabels[log.to_state] || log.to_state });
    }

    // 如果当前状态不是最后一个（有可能有并发操作），确保包含当前状态
    if (flow.length === 0 || flow[flow.length - 1].state !== task.current_state) {
      // 检查是否已存在
      if (!flow.some((f) => f.state === task.current_state)) {
        flow.push({
          state: task.current_state,
          label: stateLabels[task.current_state] || task.current_state,
        });
      }
    }

    return flow;
  };

  // 格式化时间
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "刚刚";
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays < 7) return `${diffDays}天前`;
    return date.toLocaleDateString("zh-CN");
  };

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="task-list">
      <div className="task-header">
        <h2>我的任务</h2>
        <div className="task-stats">
          <span className="stat-item">
            全部: <strong>{tasks.length}</strong>
          </span>
          {Object.entries(taskCounts).map(([state, count]) => (
            <span
              key={state}
              className="stat-item"
              style={{ color: stateColors[state] }}
            >
              {stateLabels[state] || state}: <strong>{count}</strong>
            </span>
          ))}
        </div>
      </div>

      <div className="filter-bar">
        <button
          className={`filter-btn ${filterState === "all" ? "active" : ""}`}
          onClick={() => setFilterState("all")}
        >
          全部
        </button>
        {Object.keys(stateLabels).map((state) => (
          <button
            key={state}
            className={`filter-btn ${filterState === state ? "active" : ""}`}
            style={{
              borderColor: filterState === state ? stateColors[state] : undefined,
            }}
            onClick={() => setFilterState(state)}
          >
            {stateLabels[state]}
          </button>
        ))}

        <input
          className="search-input"
          type="text"
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          placeholder="按标题或内容搜索"
        />
        <button className="filter-btn" onClick={applySearch}>
          搜索
        </button>

        <select
          className="filter-select"
          value={sortField}
          onChange={(e) =>
            setSortField(
              e.target.value as "created_at" | "updated_at" | "title"
            )
          }
        >
          <option value="created_at">按创建时间</option>
          <option value="updated_at">按更新时间</option>
          <option value="title">按标题</option>
        </select>
        <select
          className="filter-select"
          value={sortDirection}
          onChange={(e) =>
            setSortDirection(e.target.value as "asc" | "desc")
          }
        >
          <option value="desc">降序</option>
          <option value="asc">升序</option>
        </select>
        <button className="filter-btn" onClick={applySortedQuery}>
          应用排序
        </button>
      </div>

      {filteredTasks.length === 0 ? (
        <div className="empty-state">暂无任务</div>
      ) : (
        <div className="task-grid">
          {filteredTasks.map((task) => {
            const isCreator = task.creator_id === currentUser.id;
            const currentOwner = task.current_owner_id
              ? mockUsers.find((u) => u.id === task.current_owner_id)
              : null;
            const logs = logsMap[task.id] || [];
            const isExpanded = expandedTasks.has(task.id);
            const stateFlow = getStateFlow(task);

            return (
              <div
                key={task.id}
                className={`task-card ${isCreator ? "task-created-by-me" : ""}`}
                onClick={() => setSelectedTask(task)}
              >
                <div className="task-card-header">
                  <div className="header-tags">
                    <span className="task-type">{task.type_code}</span>
                    {isCreator && <span className="task-badge">我创建的</span>}
                  </div>
                  <span
                    className="task-state-badge"
                    style={{ backgroundColor: stateColors[task.current_state] }}
                  >
                    {stateLabels[task.current_state] || task.current_state}
                  </span>
                </div>
                
                <h3 className="task-title">{task.title}</h3>
                <p className="task-content">{task.content}</p>

                {/* 状态流转时间线 */}
                {isExpanded && (
                  <div className="state-timeline">
                    <div className="timeline-header">状态流转历程</div>
                    <div className="timeline-flow">
                      {stateFlow.map((item, index) => (
                        <div key={item.state} className="timeline-item">
                          <div
                            className="timeline-dot"
                            style={{
                              backgroundColor:
                                index === stateFlow.length - 1
                                  ? stateColors[item.state]
                                  : "#d1d5db",
                            }}
                          />
                          <span
                            className="timeline-state"
                            style={{
                              color:
                                index === stateFlow.length - 1
                                  ? stateColors[item.state]
                                  : "#6b7280",
                              fontWeight:
                                index === stateFlow.length - 1 ? 600 : 400,
                            }}
                          >
                            {item.label}
                          </span>
                          {index < stateFlow.length - 1 && (
                            <div className="timeline-line" />
                          )}
                        </div>
                      ))}
                    </div>
                    {logs.length > 0 && (
                      <div className="timeline-logs">
                        {logs.slice(0, 3).map((log) => {
                          const operator = mockUsers.find(
                            (u) => u.id === log.operator_id
                          );
                          return (
                            <div key={log.id} className="timeline-log-item">
                              <span className="log-time">
                                {formatTime(log.created_at)}
                              </span>
                              <span className="log-action">
                                {operator?.name || `用户 ${log.operator_id}`}
                              </span>
                              <span className="log-arrow">
                                {stateLabels[log.from_state]} →{" "}
                                {stateLabels[log.to_state]}
                              </span>
                              {log.payload && Object.keys(log.payload).length > 0 && (
                                <span className="log-detail">
                                  {JSON.stringify(log.payload)}
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                <div className="task-meta">
                  <span className="task-owner">
                    当前: {currentOwner?.name || `用户 ${task.current_owner_id}` || "无"}
                  </span>
                </div>
                
                <div className="task-footer">
                  <span className="task-id">#{task.id}</span>
                  <button
                    className={`expand-btn ${isExpanded ? "expanded" : ""}`}
                    onClick={(e) => toggleExpand(e, task.id)}
                  >
                    {isExpanded ? "收起" : "查看流程"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
          onRefresh={fetchTasks}
        />
      )}
    </div>
  );
};

export default TaskList;
