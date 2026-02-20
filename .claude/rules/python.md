# Python 开发规则 (MathModelAgent 项目适配)

> 融合 everything-claude-code 精华 + 项目特定约束

## 编码风格

### 强制标准
- 遵循 **PEP 8**，行长 88 字符（Black 风格）
- 所有函数签名必须使用**完整类型注解**，包括返回类型
- 所有类和公开方法必须有**中文 docstring**
- Import 排序：future → stdlib → third-party → first-party → local（Ruff isort）

### 不可变性优先
```python
# ✅ 正确: 不可变数据结构
from dataclasses import dataclass

@dataclass(frozen=True)
class AgentConfig:
    model: str
    temperature: float = 0.7

# ✅ 正确: 使用 tuple 替代 list 作为常量
FLOW_STAGES = ("coordinator", "modeler", "coder", "writer")

# ❌ 错误: 可变类变量
class Flows:
    _FLOW_PREFIX = ["stage1", "stage2"]  # 应改为 tuple
```

### 代码质量检查清单（每次编辑后自查）
- [ ] 函数体 < 50 行，超过则拆分
- [ ] 文件 < 800 行，超过则拆分模块
- [ ] 嵌套 ≤ 4 层，超过则提取函数
- [ ] 无硬编码魔术值，使用常量/配置
- [ ] 无裸 `except`，必须捕获具体异常类型
- [ ] 无 `print()` 语句，使用 `logger` 替代
- [ ] 无模块内 `import`（方法内导入），移到文件顶部

## 设计模式

### Protocol 接口（依赖倒置）
```python
from typing import Protocol

class CodeExecutor(Protocol):
    """代码执行器协议，支持多种后端实现。"""
    async def execute(self, code: str, timeout: int = 300) -> ExecutionResult: ...
    async def cleanup(self) -> None: ...

# 具体实现: LocalExecutor, DockerExecutor, E2BExecutor
# 业务代码依赖 Protocol，不依赖具体实现
```

### Pydantic 作为 DTO（本项目已采用，保持一致）
```python
from pydantic import BaseModel, Field

class ModelingRequest(BaseModel):
    """建模任务请求。"""
    problem: str = Field(..., min_length=10, max_length=50000, description="问题描述")
    files: list[str] = Field(default_factory=list, description="附件列表")
    workflow_mode: WorkflowMode = Field(default=WorkflowMode.STANDARD)
```

### 上下文管理器（资源管理）
```python
# ✅ 正确: 资源管理用 contextmanager
from contextlib import asynccontextmanager

@asynccontextmanager
async def sandbox_session(config: SandboxConfig):
    """沙箱会话上下文管理。"""
    sandbox = await create_sandbox(config)
    try:
        yield sandbox
    finally:
        await sandbox.cleanup()
```

## 错误处理

### 分层错误处理（本项目已有，强化规范）
```python
# ✅ 正确: 每层都有显式错误处理
async def process_task(task_id: str, request: ModelingRequest) -> ModelingResponse:
    """处理建模任务。"""
    try:
        result = await agent.run(request.problem)
        return ModelingResponse(task_id=task_id, result=result)
    except AgentError as e:
        logger.error("Agent 执行失败", extra={"task_id": task_id, "error": str(e)})
        raise  # 保持异常链
    except LLMException as e:
        logger.warning("LLM 调用异常，触发降级", extra={"task_id": task_id})
        return await fallback_handler(task_id, request)

# ❌ 错误: 静默吞掉错误
except Exception:
    return None  # 禁止！
```

### 输入验证（系统边界）
- 所有用户输入经过 Pydantic Schema 验证
- API 路由层使用 `Depends` 注入验证逻辑
- Agent 层对输入长度设上限，防止 context window 溢出
- 永远不信任外部数据（LLM 响应、用户输入、文件内容）

## 安全规范

### 安全检查清单（每次提交前必查）
- [ ] 无硬编码密钥/Token（使用环境变量 + Pydantic Settings）
- [ ] 用户输入已验证（Pydantic + 自定义 validator）
- [ ] 参数化查询（如涉及 SQL）
- [ ] 文件上传已验证（魔术字节 + 扩展名 + 内容扫描）
- [ ] 用户代码在沙箱中执行（network=none, readonly, cap_drop ALL）
- [ ] 日志中无敏感信息（使用 DataMasker 脱敏）
- [ ] 错误消息不暴露内部实现细节

### 密钥管理
```python
# ✅ 正确: 启动时验证，缺失即报错
from app.config.setting import settings

api_key = settings.COORDINATOR_API_KEY
if not api_key:
    raise ValueError("COORDINATOR_API_KEY 未配置，请检查 .env 文件")

# ❌ 错误: 硬编码
api_key = "sk-proj-xxxxx"

# ❌ 错误: 静默使用空值
api_key = os.environ.get("API_KEY", "")
```

## 测试规范

### 框架: pytest + pytest-asyncio
```bash
# 运行全部测试（带覆盖率）
cd backend && uv run pytest app/tests/ --cov=app --cov-report=term-missing

# 只运行单元测试
cd backend && uv run pytest app/tests/ -m unit -v

# 只运行集成测试
cd backend && uv run pytest app/tests/ -m integration -v
```

### 测试分类标记
```python
import pytest

@pytest.mark.unit
async def test_coordinator_parse_input():
    """单元测试: CoordinatorAgent 解析用户输入。"""
    ...

@pytest.mark.integration
async def test_full_modeling_pipeline():
    """集成测试: 完整建模流程 Coordinator → Writer。"""
    ...

@pytest.mark.slow
async def test_large_dataset_processing():
    """慢速测试: 大数据集处理性能。"""
    ...
```

### 覆盖率目标
| 模块 | 最低覆盖率 |
|------|-----------|
| `core/agents/` | 80% |
| `core/flows.py` | 85% |
| `routers/` | 75% |
| `services/` | 80% |
| `tools/` | 70% |

## 工具链

```bash
# 格式化 + Lint（每次提交前）
cd backend && uv run ruff format app/ && uv run ruff check app/ --fix

# 类型检查（渐进式引入）
cd backend && uv run mypy app/ --ignore-missing-imports

# 安全扫描
cd backend && uv run ruff check app/ --select S
```
