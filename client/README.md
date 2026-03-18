# Fake Client

`client/fake_framework_client.py` 是一个极简的假执行框架，用来联调后端执行模块。

它会做 4 件事：

1. 启动本地 HTTP 服务，接收平台下发的任务
2. 自动注册成一个 execution agent
3. 周期性发送心跳
4. 收到任务后，自动上报消费确认、执行事件、case 进度和最终结果

## 运行

```bash
python client/fake_framework_client.py
```

可选参数：

```bash
python client/fake_framework_client.py \
  --platform-url http://127.0.0.1:8000 \
  --agent-id fake-framework-agent \
  --host 127.0.0.1 \
  --port 19090 \
  --step-delay 1
```

## 配套后端配置

后端要用 HTTP 下发模式：

```env
EXECUTION_DISPATCH_MODE=http
EXECUTION_AGENT_DISPATCH_PATH=/api/v1/execution/tasks/dispatch
```

## 如何改虚拟数据

直接改脚本顶部这几段常量即可：

- `DEFAULT_CASE_STEPS`
  控制进度怎么上报，例如 10% -> 50% -> 100%
- `DEFAULT_CASE_RESULT`
  控制 case 最终结果内容
- `DEFAULT_STEP_DELAY_SECONDS`
  控制每步之间的等待时间

如果要模拟失败，最简单的方式是把：

```python
DEFAULT_CASE_RESULT = {
    "status": "FAILED",
    "message": "fake execution failed",
    "artifacts": ["report/fake-report.html"],
}
```

同时把 `DEFAULT_CASE_STEPS` 最后一步的 `status` 改成 `FAILED`。
