import React, { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { type User, mockUsers } from "../services/mockUsers";

interface UserContextType {
  currentUser: User;
  users: User[];
  switchUser: (userId: number) => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const UserProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<User>(mockUsers[0]);
  const [users] = useState<User[]>(mockUsers);

  const switchUser = useCallback((userId: number) => {
    const user = mockUsers.find((u) => u.id === userId);
    if (user) {
      setCurrentUser(user);
    }
  }, []);

  return (
    <UserContext.Provider value={{ currentUser, users, switchUser }}>
      {children}
    </UserContext.Provider>
  );
};

export const useUser = (): UserContextType => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return context;
};