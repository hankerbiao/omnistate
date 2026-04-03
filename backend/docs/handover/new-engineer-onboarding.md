# 新工程师上手

## 第一天要完成什么

1. 跑通本地服务
2. 知道主要模块分别负责什么
3. 能定位自己要改的模块入口
4. 能独立执行基本测试与排障

## 推荐阅读顺序

1. `guide/quick-start`
2. `guide/local-development`
3. `guide/architecture-overview`
4. `guide/how-to-change-backend`
5. 进入对应模块文档

## 上手时最容易踩的坑

- 只看目录，不看真实调用链
- 把 `status` 当成持久化字段修改
- 改了 workflow 配置但没同步初始化数据
- 改 execution 时没看 task / task_case / event 三层数据
