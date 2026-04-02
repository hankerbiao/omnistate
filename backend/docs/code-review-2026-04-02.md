# DML V4 Backend 严厉代码评审

评审日期：2026-04-02

评审范围：当前 `backend` 仓库的结构、核心模块、测试现状、静态检查结果。

评审基调：按严格代码 review 口径，不做“能跑就行”的情绪安慰。

## 一句话结论

这项目**还没彻底烂成不可维护的终极屎山**，但已经明显进入了“**表面分层、内部缠绕、核心文件持续增肥、测试严重失血**”阶段。

如果继续按当前节奏堆功能，不做结构治理，半年内大概率会从“偏脏”升级为“正式屎山”。

## 含屎量评级

- 结论：**中高含屎量**
- 含屎量：**72 / 100**
- 当前判定：**不是废墟，但已经是危险建筑**

评分依据：

- Python 代码约 **15215** 行，`app/` 下 **149** 个 `.py` 文件。
- `tests/` 下只有 **1** 个测试文件，实际只跑了 **7** 个测试。
- 最大核心文件达到：
  - `app/modules/workflow/service/workflow_service.py`：**780 行**
  - `app/modules/workflow/api/routes.py`：**566 行**
  - `app/modules/auth/api/routes.py`：**528 行**
  - `app/modules/test_specs/service/test_case_service.py`：**473 行**
  - `app/modules/execution/application/event_ingest_service.py`：**428 行**
- `flake8` 当前直接报出 **31** 条问题。

这不是“小瑕疵”，这是很明确的维护性预警。

## 总体判断

### 1. 结构不是完全乱写，但“名义分层”已经开始失真

仓库目录看起来是 `api / service / application / domain / repository` 的标准分层，但实际代码里已经出现明显穿透：

- `workflow service` 直接回写 `TestRequirementDoc` 和 `TestCaseDoc`，把 workflow 与 test_specs 强耦合在一起，见：
  - `app/modules/workflow/service/workflow_service.py:577`
  - `app/modules/workflow/service/workflow_service.py:588`
  - `app/modules/workflow/service/workflow_service.py:692`
  - `app/modules/workflow/service/workflow_service.py:713`
- `test_specs` 在创建测试用例时直接 new `AsyncWorkflowService()` 并参与事务，见：
  - `app/modules/test_specs/service/test_case_service.py:356`
  - `app/modules/test_specs/service/test_case_service.py:375`
- `execution` 的事件消费服务内部又直接 new `ExecutionService()` 推进任务，见：
  - `app/modules/execution/application/event_ingest_service.py:421`

这类写法的本质不是“复用”，而是**模块互相知道对方太多内部细节**。目录分层还在，边界已经开始塌。

### 2. 核心模块已经出现“上帝文件”

几个核心文件已经承担了过多职责：

- `workflow_service.py` 同时负责：
  - 查询
  - 创建
  - 状态机流转
  - 事务兼容
  - 日志写入
  - 级联同步 requirement/test_case 投影状态
  - 删除约束
  - 改派
- `workflow/api/routes.py` 和 `auth/api/routes.py` 也明显过胖，已经不是“路由声明文件”，而是“大号接口集市”。

这会带来几个必然后果：

- 读代码成本越来越高
- 改一个功能更容易误伤别的分支逻辑
- reviewer 无法快速建立局部正确性
- 测试无法细粒度覆盖，只能靠手工回归碰运气

### 3. 数据一致性靠“人工双写”维持，风险很高

最危险的一类问题不是文件长，而是**状态双写**：

- 工作流状态存在 `BusWorkItemDoc.current_state`
- 同时 requirement/test case 文档上又维护 `status` 投影
- 流转时靠 service 手工同步，见：
  - `app/modules/workflow/service/workflow_service.py:563`
  - `app/modules/workflow/service/workflow_service.py:586`
  - `app/modules/workflow/service/workflow_service.py:597`

`test_case_service.py` 自己也承认“status 是投影字段”，见：

- `app/modules/test_specs/service/test_case_service.py:208`

但代码依然保留这套双写模型。这意味着：

- 任何一个绕过 workflow 的写路径，都可能制造脏数据
- 后续加新业务类型时，极容易忘记补同步逻辑
- “真实状态源”虽然口头上是 workflow，代码上却仍在多个集合里重复存储

这是典型的“现在能跑，未来难修”的屎味来源。

### 4. 测试不是薄弱，是接近没有

实际情况：

- `tests/` 目录下只有 **1** 个 Python 测试文件
- 只覆盖 terminal 模块
- `pytest -q` 实际执行仅 **7** 个测试

而当前项目承载了：

- workflow 状态机
- test_specs 业务规则
- execution 串行调度
- auth/RBAC
- attachments
- infrastructure 生命周期

这套系统在业务复杂度上已经明显超过“可以靠人工心证维护”的级别，但测试密度完全不匹配。

更讽刺的是，pytest 还给了一个 collection warning：

- `app/modules/test_specs/domain/exceptions.py:16`

`TestCaseNotFoundError` 这种异常类命名，会被 pytest 当成测试类候选去收集。不是大 bug，但它说明项目对测试生态的基本卫生都没有持续维护。

### 5. 静态检查不过，说明日常工程纪律也偏松

`flake8` 当前报 **31** 条问题，主要包括：

- unused imports
- no newline at end of file
- module import 不在文件顶部
- 语法层面的低级问题

典型例子：

- `app/modules/attachments/api/routes.py:3`
- `app/modules/attachments/service/attachment_service.py:5`
- `scripts/create_token.py:29`
- `app/shared/rabbitmq/consumer.py:345`

如果一个项目连基础 lint 都长期不收敛，通常意味着：

- 合并门槛偏低
- 提交前没有统一质量门禁
- 工程质量主要靠人肉自觉

这种团队习惯，和屎山是高度正相关的。

## 重点问题清单

### P0：伪分层，真耦合

核心问题：

- `workflow` 直接依赖 `test_specs` 文档模型并做联动更新
- `test_specs` 再反向直接调用 workflow service
- `execution` 的事件服务又直接实例化执行服务推进编排

证据：

- `app/modules/workflow/service/workflow_service.py:577`
- `app/modules/workflow/service/workflow_service.py:588`
- `app/modules/test_specs/service/test_case_service.py:356`
- `app/modules/execution/application/event_ingest_service.py:421`

评价：

这不是清晰边界，这是**业务规则散在多个模块里互相补洞**。一旦再加模块，只会越来越像意大利面。

### P0：状态投影双写，数据一致性脆弱

证据：

- `app/modules/workflow/service/workflow_service.py:563`
- `app/modules/workflow/service/workflow_service.py:586`
- `app/modules/workflow/service/workflow_service.py:597`
- `app/modules/test_specs/service/test_case_service.py:167`
- `app/modules/test_specs/service/test_case_service.py:208`

评价：

“单一真实来源”只写在注释里，代码实现仍然是多点存储、人工同步。只要漏掉一条更新路径，就会产生状态漂移。

### P1：路由层过胖，正在向 controller-script 化退化

证据：

- `app/modules/workflow/api/routes.py:1`
- `app/modules/auth/api/routes.py:1`

这两个文件都超过 500 行，而且包含大量重复模式：

- service 构造
- 当前用户获取
- try/except 转 HTTPException
- response_model/summary/permission 声明堆叠

评价：

这类文件短期看“集中”，长期看就是**改动冲突高发区**。继续长下去以后，每次加接口都像在公共厨房里插队做饭。

### P1：事务与基础设施管理方式偏硬编码，扩展性一般

`app/main.py` 把所有 document model 初始化集中硬编码在入口：

- `app/main.py:87`

`InfrastructureRegistry` 既管 RabbitMQ/Kafka，又管调度循环，又管健康状态，又管懒初始化：

- `app/shared/infrastructure/registry.py:31`
- `app/shared/infrastructure/registry.py:62`
- `app/shared/infrastructure/registry.py:171`
- `app/shared/infrastructure/registry.py:207`

评价：

现在功能还没炸，是因为规模还没再扩大。继续加消息组件、消费者、后台任务，这块会很快变成新的核心屎坑。

### P1：权限判断存在粗暴实现

管理员判断是字符串包含：

- `app/modules/auth/api/routes.py:52`
- `app/shared/auth/jwt_auth.py:87`

实现方式是：

- 角色 ID 里只要包含 `"ADMIN"` 就视为管理员

评价：

这写法过于土法。`SUPER_ADMIN`, `NOT_ADMIN_BUT_HAS_ADMIN_WORDING` 这类命名都可能触发语义歧义。权限系统不该靠 substring 猜测角色语义。

### P1：仓库文档与代码现实已有偏差

README 还提到了 `assets` 模块，但当前后端目录里并无对应 `app/modules/assets/`：

- `README.md:23`
- `README.md:65`
- 实际目录扫描无该模块

评价：

文档过期本身不是大罪，但它通常是“架构设计曾经想过，后来实现漂移，没人系统回收”的信号。屎山前兆之一，就是文档开始和现实分叉。

### P2：代码卫生偏松，坏味道零散分布

例子包括：

- 空 `__init__` 只写 `pass`
  - `app/modules/workflow/service/workflow_service.py:47`
  - `app/modules/test_specs/domain/exceptions.py:6`
- 宽泛异常捕获较多
  - `app/modules/workflow/service/workflow_service.py:475`
  - `app/shared/infrastructure/registry.py:81`
  - `app/shared/rabbitmq/consumer.py:226`
- 预留接口直接挂在线上主路由中
  - `app/modules/attachments/api/routes.py:180`
  - `app/modules/attachments/api/routes.py:191`

评价：

这些问题单看都不致命，但堆起来会持续抬高理解成本，降低“代码可信度”。

## 不是屎的部分

也得说句公道话，项目并非一无是处：

- 目录结构总体还是有组织，不是单目录乱炖
- 有统一异常处理、统一 API Response 包装
  - `app/shared/api/errors/handlers.py:19`
- 生命周期管理、Mongo 初始化、基础设施启动收口都集中在入口
  - `app/main.py:72`
- workflow 至少在尝试做事务边界和规则封装
  - `app/modules/workflow/service/workflow_service.py:479`
- execution 模块拆成 mixin，比直接一个 1000 行 service 稍微克制一点

所以结论不是“纯屎”，而是：

**这是一个已经写出业务结构、但工程治理明显跟不上业务膨胀速度的项目。**

## 屎山趋势判断

如果不治理，后续最可能恶化的点：

1. `workflow_service.py` 继续吸业务逻辑，成为全局规则垃圾桶。
2. `auth/api/routes.py` 和 `workflow/api/routes.py` 继续膨胀，进入修改高冲突状态。
3. `execution` 继续通过服务互相实例化方式推进流程，边界越来越难说清。
4. 状态双写继续扩散到更多业务实体，脏数据排查成本指数上升。
5. 因为没有像样测试，任何一次重构都只能“祈祷上线别炸”。

## 建议优先级

### 必须尽快做

1. 给 `workflow / execution / auth / test_specs` 补核心单元测试和最小集成测试。
2. 拆 `workflow_service.py`，至少拆成 query / command / transition / delete 四块。
3. 终止状态双写扩散，明确唯一状态源；能删投影字段就删，删不掉也要集中封装同步出口。
4. 把 `auth/api/routes.py`、`workflow/api/routes.py` 做子路由拆分。
5. 把 flake8 收敛到 0，建立提交前门禁。

### 应该尽快做

1. 把 “服务里直接 new 另一个服务” 改为依赖注入或显式 orchestration。
2. 把管理员判定从 substring 逻辑改为明确角色码匹配。
3. 清理 README 与真实目录结构偏差。
4. 给 infrastructure registry 再拆职责，不要继续长成全局神对象。

## 最终结论

严格说，这项目**还不是彻底没救的屎山**。

但它已经具备屎山的几个关键前兆：

- 核心文件过胖
- 模块边界穿透
- 状态靠人工双写
- 测试近乎空白
- 工程纪律松散

所以我的结论是：

**现在是“有明显屎味的可救项目”，不是“纯屎山”，但再不治理，很快就会转正。**

