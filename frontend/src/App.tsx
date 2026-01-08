import { useState } from "react";
import { UserProvider } from "./context/UserContext";
import UserSwitcher from "./components/UserSwitcher";
import TaskList from "./components/TaskList";
import CreateTaskModal from "./components/CreateTaskModal";
import "./App.css";

function App() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [taskListKey, setTaskListKey] = useState(0);
  const [filterType, setFilterType] = useState<"all" | "requirement" | "test_case">("all");

  const handleTaskCreated = () => {
    // 通过改变 key 强制 TaskList 重新渲染和刷新数据
    setTaskListKey((prev) => prev + 1);
  };

  return (
    <UserProvider>
      <div className="app">
        <aside className="sidebar">
          <div className="sidebar-brand">
            <div className="logo-placeholder">W</div>
            <h1>工作流测试系统</h1>
          </div>
          
          <nav className="sidebar-nav">
            <button 
              className={`nav-item ${filterType === "all" ? "active" : ""}`}
              onClick={() => setFilterType("all")}
            >
              全部事项
            </button>
            <button 
              className={`nav-item ${filterType === "requirement" ? "active" : ""}`}
              onClick={() => setFilterType("requirement")}
            >
              需求开发
            </button>
            <button 
              className={`nav-item ${filterType === "test_case" ? "active" : ""}`}
              onClick={() => setFilterType("test_case")}
            >
              测试用例
            </button>
          </nav>
        </aside>

        <main className="main-content">
          <header className="main-header">
            <UserSwitcher />
          </header>
          <div className="content-scroll-area">
            <TaskList 
              key={taskListKey} 
              filterType={filterType} 
              onCreateClick={() => setShowCreateModal(true)}
            />
          </div>
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
