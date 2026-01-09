import { useState } from "react";
import { UserProvider } from "./context/UserContext";
import UserSwitcher from "./components/UserSwitcher";
import Sidebar from "./components/Sidebar";
import FlowManagement from "./pages/FlowManagement";
import CreateTaskModal from "./components/CreateTaskModal";
import "./App.css";

function App() {
  const [activeModule, setActiveModule] = useState("workflow");
  const [activePage, setActivePage] = useState("all");
  const [showCreateModal, setShowCreateModal] = useState(false);

  const handleNavigate = (moduleId: string, pageId: string) => {
    setActiveModule(moduleId);
    setActivePage(pageId);
  };

  const filterType = activePage as "all" | "requirement" | "test_case";

  const renderPage = () => {
    // 流程管理模块
    if (activeModule === "workflow") {
      return (
        <FlowManagement
          filterType={filterType}
          onCreateClick={() => setShowCreateModal(true)}
        />
      );
    }

    // 其他模块的占位页面
    return (
      <div className="coming-soon-page">
        <div className="coming-soon-content">
          <div className="coming-soon-icon">
            <svg
              width="48"
              height="48"
              viewBox="0 0 48 48"
              fill="none"
            >
              <rect
                x="8"
                y="8"
                width="32"
                height="32"
                rx="8"
                stroke="currentColor"
                strokeWidth="2"
              />
              <path
                d="M16 24L22 30L32 18"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <h3>功能开发中</h3>
          <p>该功能模块正在建设中，敬请期待...</p>
        </div>
      </div>
    );
  };

  return (
    <UserProvider>
      <div className="app">
        <Sidebar
          activeModule={activeModule}
          activePage={activePage}
          onNavigate={handleNavigate}
        />

        <main className="main-content">
          <header className="main-header">
            <UserSwitcher />
          </header>
          <div className="content-scroll-area">{renderPage()}</div>
        </main>

        {showCreateModal && (
          <CreateTaskModal
            onClose={() => setShowCreateModal(false)}
            onSuccess={() => {}}
          />
        )}
      </div>
    </UserProvider>
  );
}

export default App;