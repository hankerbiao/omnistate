import { useUser } from "../context/UserContext";
import "./UserSwitcher.css";

const UserSwitcher: React.FC = () => {
  const { currentUser, users, switchUser } = useUser();

  return (
    <div className="user-switcher">
      <div className="current-user">
        <img
          src={currentUser.avatar}
          alt={currentUser.name}
          className="user-avatar"
        />
        <div className="user-info">
          <span className="user-name">{currentUser.name}</span>
          <span className="user-role">{currentUser.role}</span>
        </div>
      </div>

      <div className="user-list">
        <span className="switch-label">切换用户:</span>
        <div className="avatars">
          {users.map((user) => (
            <button
              key={user.id}
              className={`avatar-btn ${user.id === currentUser.id ? "active" : ""}`}
              onClick={() => switchUser(user.id)}
              title={`${user.name} - ${user.role}`}
            >
              <img src={user.avatar} alt={user.name} />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default UserSwitcher;