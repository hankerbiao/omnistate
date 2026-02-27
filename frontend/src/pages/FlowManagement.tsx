import TaskList from "../components/TaskList";
import "./FlowManagement.css";

interface FlowManagementProps {
  filterType: "all" | "requirement" | "test_case";
  onCreateClick: () => void;
}

function FlowManagement({ filterType, onCreateClick }: FlowManagementProps) {
  return (
    <div className="flow-management">
      <div className="page-header">
        <div className="page-title-section">
          <h2 className="page-title">
            {filterType === "all"
              ? "全部事项"
              : filterType === "requirement"
              ? "需求开发"
              : "测试用例"}
          </h2>
          <p className="page-subtitle">管理您的工作事项和流程状态</p>
        </div>
        <button className="btn btn-primary" onClick={onCreateClick}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
          >
            <path
              d="M8 3V13M3 8H13"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
          新建事项
        </button>
      </div>

      <div className="page-content">
        <TaskList
          filterType={filterType}
          onCreateClick={onCreateClick}
        />
      </div>
    </div>
  );
}

export default FlowManagement;