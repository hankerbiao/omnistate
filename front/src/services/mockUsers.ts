// Mock 用户数据
export interface User {
  id: number;
  name: string;
  avatar: string;
  role: string;
}

export const mockUsers: User[] = [
  {
    id: 1,
    name: "张三",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=ZhangSan",
    role: "产品经理",
  },
  {
    id: 2,
    name: "李四",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=LiSi",
    role: "开发工程师",
  },
  {
    id: 3,
    name: "王五",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=WangWu",
    role: "测试工程师",
  },
  {
    id: 4,
    name: "赵六",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=ZhaoLiu",
    role: "项目经理",
  },
];

export const getUserById = (id: number): User | undefined => {
  return mockUsers.find((user) => user.id === id);
};