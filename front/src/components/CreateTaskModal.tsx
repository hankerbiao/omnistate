import { useState, useEffect } from "react";
import { workItemApi, type WorkType } from "../services/api";
import { useUser } from "../context/UserContext";
import "./CreateTaskModal.css";

interface CreateTaskModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

const CreateTaskModal: React.FC<CreateTaskModalProps> = ({
  onClose,
  onSuccess,
}) => {
  const { currentUser } = useUser();
  const [types, setTypes] = useState<WorkType[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    typeCode: "",
    title: "",
    content: "",
  });

  useEffect(() => {
    const fetchTypes = async () => {
      try {
        const data = await workItemApi.getTypes();
        setTypes(data);
        if (data.length > 0) {
          setFormData((prev) => ({ ...prev, typeCode: data[0].code }));
        }
      } catch (err: any) {
        console.error("获取类型失败:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchTypes();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.typeCode || !formData.title) {
      alert("请填写必填字段");
      return;
    }

    setSubmitting(true);
    try {
      await workItemApi.create(
        formData.typeCode,
        formData.title,
        formData.content,
        currentUser.id
      );
      onSuccess();
      onClose();
    } catch (err: any) {
      alert(err.response?.data?.detail || "创建失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content create-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>创建任务</h2>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="create-form">
          <div className="form-group">
            <label>事项类型 *</label>
            <select
              value={formData.typeCode}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, typeCode: e.target.value }))
              }
              disabled={loading}
            >
              {loading ? (
                <option>加载中...</option>
              ) : (
                types.map((type) => (
                  <option key={type.code} value={type.code}>
                    {type.name} ({type.code})
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="form-group">
            <label>标题 *</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, title: e.target.value }))
              }
              placeholder="请输入任务标题"
              required
            />
          </div>

          <div className="form-group">
            <label>内容</label>
            <textarea
              value={formData.content}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, content: e.target.value }))
              }
              placeholder="请输入任务内容"
              rows={4}
            />
          </div>

          <div className="form-group">
            <label>创建者</label>
            <div className="creator-info">
              <img
                src={currentUser.avatar}
                alt={currentUser.name}
                className="creator-avatar"
              />
              <span>
                {currentUser.name} ({currentUser.role})
              </span>
            </div>
          </div>

          <div className="form-actions">
            <button type="button" className="cancel-btn" onClick={onClose}>
              取消
            </button>
            <button
              type="submit"
              className="submit-btn"
              disabled={submitting || loading}
            >
              {submitting ? "创建中..." : "创建"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateTaskModal;