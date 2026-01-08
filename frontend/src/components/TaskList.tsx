import { useState, useEffect } from "react";
import {
  workItemApi,
  type WorkItem,
  stateLabels,
  stateColors,
} from "../services/api";
import { useUser } from "../context/UserContext";
import { mockUsers } from "../services/mockUsers";
import TaskDetailModal from "./TaskDetailModal";
import "./TaskList.css";

interface TaskListProps {
  filterType: "all" | "requirement" | "test_case";
  onCreateClick: () => void;
}

const TaskList: React.FC<TaskListProps> = ({ filterType, onCreateClick }) => {
  const { currentUser } = useUser();
  const [tasks, setTasks] = useState<WorkItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<WorkItem | null>(null);
  const [searchKeyword, setSearchKeyword] = useState<string>("");

  const loadTasks = async (fetcher: () => Promise<WorkItem[]>) => {
    try {
      setLoading(true);
      const data = await fetcher();
      setTasks(data);
      setError(null);
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

  useEffect(() => {
    fetchTasks();
  }, [currentUser.id]);

  const handleDeleteTask = async (e: React.MouseEvent, task: WorkItem) => {
    e.stopPropagation();
    if (!confirm(`确定要删除任务「${task.title}」吗？此操作不可恢复。`)) {
      return;
    }
    try {
      await workItemApi.delete(task.id);
      fetchTasks();
    } catch (err: any) {
      alert(err.response?.data?.detail || "删除失败");
    }
  };

  const filteredTasks = tasks.filter((t) => {
    const matchesType = 
      filterType === "all" ? true : 
      filterType === "requirement" ? t.type_code === "REQUIREMENT" :
      t.type_code === "TEST_CASE";
      
    const matchesSearch = searchKeyword 
      ? (t.title.toLowerCase().includes(searchKeyword.toLowerCase()) || 
         t.content.toLowerCase().includes(searchKeyword.toLowerCase()))
      : true;
      
    return matchesType && matchesSearch;
  });

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="task-list-container">
      <div className="task-toolbar">
         <div className="search-box">
           <span className="search-icon">🔍</span>
           <input 
             type="text" 
             placeholder="搜索标题或内容..." 
             value={searchKeyword}
             onChange={(e) => setSearchKeyword(e.target.value)}
           />
         </div>
         <button className="btn btn-primary" onClick={onCreateClick}>
           + 创建任务
         </button>
      </div>

      <div className="task-table-wrapper">
        <table className="task-table">
          <thead>
            <tr>
              <th className="th-type">类型</th>
              <th className="th-info">事项详情</th>
              <th className="th-status">状态</th>
              <th className="th-owner">处理人</th>
              <th className="th-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredTasks.length === 0 ? (
              <tr>
                <td colSpan={5} className="empty-cell">暂无任务</td>
              </tr>
            ) : (
              filteredTasks.map(task => {
                const isCreator = task.creator_id === currentUser.id;
                const currentOwner = task.current_owner_id
                    ? mockUsers.find((u) => u.id === task.current_owner_id)
                    : null;
                
                return (
                  <tr key={task.id} onClick={() => setSelectedTask(task)} className="task-tr">
                     <td className="td-type">
                       <span className={`type-badge ${task.type_code.toLowerCase()}`}>
                         {task.type_code === "REQUIREMENT" ? "需求" : "用例"}
                       </span>
                     </td>
                     <td className="td-info">
                       <div className="info-title">
                         {task.title}
                         {isCreator && <span className="creator-badge">我创建的</span>}
                       </div>
                       <div className="info-content">
                         {task.content || "无详细描述"}
                       </div>
                     </td>
                     <td className="td-status">
                       <div className="status-cell">
                         <span 
                           className="status-dot" 
                           style={{ backgroundColor: stateColors[task.current_state] }}
                         />
                         {stateLabels[task.current_state] || task.current_state}
                       </div>
                     </td>
                     <td className="td-owner">
                       <div className="owner-cell">
                         <div className="avatar-sm">
                           {currentOwner?.name?.[0] || "?"}
                         </div>
                         <span>{currentOwner?.name || "未分配"}</span>
                       </div>
                     </td>
                     <td className="td-actions">
                       <button
                          className="icon-btn delete-btn-table"
                          onClick={(e) => handleDeleteTask(e, task)}
                          title="删除任务"
                        >
                          🗑
                        </button>
                     </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      
      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
          onRefresh={fetchTasks}
          onOpenTask={(task) => setSelectedTask(task)}
        />
      )}
    </div>
  );
};

export default TaskList;
