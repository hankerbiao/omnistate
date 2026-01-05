import { useState } from "react";
import { UserProvider } from "./context/UserContext";
import UserSwitcher from "./components/UserSwitcher";
import TaskList from "./components/TaskList";
import CreateTaskModal from "./components/CreateTaskModal";
import "./App.css";

function App() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [taskListKey, setTaskListKey] = useState(0);

  const handleTaskCreated = () => {
    // 通过改变 key 强制 TaskList 重新渲染和刷新数据
    setTaskListKey((prev) => prev + 1);
  };

  return (
    <UserProvider>
      <div className="app">
        <UserSwitcher />
        <main className="main-content">
          <div className="content-header">
            <h1>工作流测试系统</h1>
            <button
              className="create-btn"
              onClick={() => setShowCreateModal(true)}
            >
              + 创建任务
            </button>
          </div>
          <TaskList key={taskListKey} />
        </main>

        {showCreateModal && (
          <CreateTaskModal
            onClose={() => setShowCreateModal(false)}
            onSuccess={handleTaskCreated}
          />
        )}
      </div>
    </UserProvider>
  );
}

export default App;