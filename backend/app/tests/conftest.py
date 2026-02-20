"""
Pytest配置文件
提供测试所需的共享fixtures和配置

重要: 模块顶部的 Mock 注入必须在所有 app.* 导入之前执行，
解决 redis_manager 全局单例已重构为依赖注入但源代码仍有旧式导入的兼容问题。
"""
import shutil
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

# ================== 关键: 模块级 Mock 注入 ==================
# redis_manager 模块已从全局单例重构为依赖注入模式 (get_redis_manager()),
# 但源代码中多处仍使用 `from app.services.redis_manager import redis_manager` 旧式导入。
# 必须在任何 app.* 模块被导入前注入 mock，否则会触发 ImportError。
#
# 此段代码在 pytest 收集阶段（所有测试之前）执行，确保后续所有
# `from app.services.redis_manager import redis_manager` 都能成功导入。
import app.services.redis_manager as _redis_mod


# 创建完整的 RedisManager mock 实例，覆盖所有公开方法
_global_mock_redis = MagicMock()
_global_mock_redis.publish_message = AsyncMock(return_value=None)
_global_mock_redis.get = AsyncMock(return_value=None)
_global_mock_redis.set = AsyncMock(return_value=True)
_global_mock_redis.delete = AsyncMock(return_value=True)
_global_mock_redis.exists = AsyncMock(return_value=False)
_global_mock_redis.get_client = AsyncMock()
_global_mock_redis.subscribe_to_task = AsyncMock()
_global_mock_redis.get_json = AsyncMock(return_value=None)
_global_mock_redis.set_json = AsyncMock(return_value=True)
_global_mock_redis.lpush = AsyncMock(return_value=1)
_global_mock_redis.lrange = AsyncMock(return_value=[])
_global_mock_redis.push_to_list = AsyncMock(return_value=1)
_global_mock_redis.setnx = AsyncMock(return_value=True)
_global_mock_redis.cache_message = AsyncMock(return_value=None)
_global_mock_redis.get_messages_after_seq = AsyncMock(return_value=[])
_global_mock_redis.close = AsyncMock(return_value=None)
_global_mock_redis.is_healthy.return_value = True
_global_mock_redis.emit_workflow_event = AsyncMock(return_value="mock-event-id")
_global_mock_redis.cleanup_file_lock = AsyncMock(return_value=None)
_global_mock_redis.xadd = AsyncMock(return_value="mock-msg-id")
_global_mock_redis.xread = AsyncMock(return_value=[])
_global_mock_redis.xrange = AsyncMock(return_value=[])
_global_mock_redis.xlen = AsyncMock(return_value=0)
_global_mock_redis.xtrim = AsyncMock(return_value=0)
_global_mock_redis.get_workflow_events = AsyncMock(return_value=[])

# 注入到模块命名空间，使旧式导入生效
_redis_mod.redis_manager = _global_mock_redis

# 同时设置 _redis_manager 使 get_redis_manager() 不抛 RuntimeError
_redis_mod._redis_manager = _global_mock_redis


# ================== 基础Fixtures ==================

# 注意: 不再需要手动定义 event_loop fixture，
# pytest-asyncio>=0.23 在 asyncio_mode=auto 时会自动管理事件循环。
# 旧的 event_loop fixture 已移除，避免 DeprecationWarning。


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """创建临时目录"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_file(temp_dir) -> Generator[Path, None, None]:
    """创建临时文件"""
    file_path = Path(temp_dir) / "test_file.txt"
    file_path.write_text("test content", encoding="utf-8")
    yield file_path


# ================== Mock Fixtures ==================

@pytest.fixture
def mock_api_key():
    """模拟API密钥"""
    return "test_api_key_12345"


@pytest.fixture
def mock_task_id():
    """模拟任务ID"""
    return "test_task_001"


@pytest.fixture
def sample_problem():
    """示例问题数据"""
    return {
        "title": "资源分配优化问题",
        "description": "某公司需要将有限的资源分配给多个项目,以最大化总收益。",
        "type": "optimization",
        "data": {
            "resources": 100,
            "projects": ["A", "B", "C"],
            "returns": [10, 15, 12],
            "requirements": [20, 30, 25],
        },
    }


@pytest.fixture
def sample_code():
    """示例代码"""
    return '''
"""
资源分配优化求解
"""
import numpy as np
from scipy.optimize import linprog

def solve_resource_allocation(resources, returns, requirements):
    """
    求解资源分配问题

    Args:
        resources: 总资源量
        returns: 各项目收益率
        requirements: 各项目资源需求

    Returns:
        最优分配方案
    """
    # 目标函数系数（取负数因为linprog求最小值）
    c = [-r for r in returns]

    # 约束条件
    A_ub = [requirements]
    b_ub = [resources]

    # 变量范围
    bounds = [(0, 1) for _ in returns]

    # 求解
    result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds)

    return result

if __name__ == "__main__":
    result = solve_resource_allocation(100, [10, 15, 12], [20, 30, 25])
    print(f"最优解: {result.x}")
    print(f"最大收益: {-result.fun}")
'''


@pytest.fixture
def sample_paper_content():
    """示例论文内容"""
    return """
# 摘要

本文针对资源分配优化问题进行了研究。采用线性规划模型，建立了资源最优配置的数学模型。
通过求解得到了最优分配方案，结果表明该方法能有效提高资源利用效率。

# 问题重述

某公司拥有有限的资源，需要将资源分配给多个项目，以最大化总收益。
需要确定每个项目的资源分配量。

# 问题分析

这是一个典型的资源分配优化问题。目标是最大化总收益，约束条件是资源总量有限。

# 模型假设

1. 各项目收益与投入资源成正比
2. 资源可以任意分割
3. 项目之间相互独立

# 符号说明

| 符号 | 含义 |
|------|------|
| $x_i$ | 第i个项目的资源分配量 |
| $r_i$ | 第i个项目的收益率 |
| $R$ | 总资源量 |

# 模型建立

目标函数：
$$\\\\max Z = \\\\sum_{i=1}^{n} r_i x_i$$

约束条件：
$$\\\\sum_{i=1}^{n} x_i \\\\leq R$$
$$x_i \\\\geq 0, i = 1, 2, ..., n$$

# 模型求解

使用Python的scipy库进行求解。

# 结果分析

最优方案将资源主要分配给收益率最高的项目。

# 模型评价

## 优点
- 模型简洁明了
- 求解效率高

## 缺点
- 假设收益线性可能与实际不符

# 参考文献

[1] 运筹学教程, 清华大学出版社
"""


# ================== 模型测试数据 ==================

@pytest.fixture
def optimization_data():
    """优化问题测试数据"""
    return {
        "problem_type": "optimization",
        "models": ["线性规划", "整数规划", "动态规划"],
        "expected_metrics": ["目标函数值", "约束满足度"],
    }


@pytest.fixture
def prediction_data():
    """预测问题测试数据"""
    return {
        "problem_type": "prediction",
        "models": ["ARIMA", "回归分析", "神经网络"],
        "expected_metrics": ["RMSE", "MAE", "R²"],
    }


@pytest.fixture
def evaluation_data():
    """评价问题测试数据"""
    return {
        "problem_type": "evaluation",
        "models": ["TOPSIS", "层次分析法", "熵权法"],
        "expected_metrics": ["综合得分", "排名"],
    }


# ================== Redis Mock ==================

@pytest.fixture
def mock_redis():
    """模拟Redis管理器"""
    redis_mock = MagicMock()
    redis_mock.publish = AsyncMock(return_value=None)
    redis_mock.publish_message = AsyncMock(return_value=None)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=True)
    redis_mock.exists = AsyncMock(return_value=False)
    redis_mock.get_client = AsyncMock()
    redis_mock.get_json = AsyncMock(return_value=None)
    redis_mock.set_json = AsyncMock(return_value=True)

    return redis_mock


# ================== HTTP 测试客户端 ==================

@pytest.fixture
async def client():
    """创建异步HTTP测试客户端（用于路由集成测试）。

    使用 httpx.AsyncClient + ASGITransport 直接与 ASGI 应用通信，
    不触发应用 lifespan（不连接真实数据库/Redis）。
    通过 dependency_overrides 覆盖数据库依赖，避免测试依赖外部服务。
    """
    import os

    from httpx import ASGITransport, AsyncClient

    # 确保静态文件目录存在（DEBUG 模式下 main.py 会挂载此目录）
    os.makedirs("project/work_dir", exist_ok=True)

    from app.config.database import get_db
    from app.main import app
    from app.services.redis_manager import get_redis_manager

    # 覆盖数据库依赖，返回 Mock 对象避免真实数据库连接
    async def mock_get_db():
        db = MagicMock()
        try:
            yield db
        finally:
            pass

    # 覆盖 Redis 依赖，返回 mock 实例
    def mock_get_redis():
        return _global_mock_redis

    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_redis_manager] = mock_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    # 清理依赖覆盖，防止影响其他测试模块
    app.dependency_overrides.clear()


# ================== 集成测试 Fixtures ==================

@pytest.fixture
def mock_llm_factory():
    """模拟 LLM 工厂 -- 为每个 Agent 返回预配置的 Mock LLM 实例"""

    def _create_mock_llm(agent_name: str, response_content: str = "mock response"):
        """为指定 Agent 创建 Mock LLM"""
        llm = MagicMock()
        mock_message = MagicMock()
        mock_message.content = response_content
        mock_message.tool_calls = None
        mock_message.model_dump.return_value = {
            "role": "assistant",
            "content": response_content,
        }
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        llm.chat = AsyncMock(return_value=mock_response)
        llm._agent_name = agent_name
        return llm

    return _create_mock_llm


@pytest.fixture
def mock_llm():
    """通用的 Mock LLM 实例 -- 返回可配置响应内容的 LLM"""
    llm = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "mock response"
    mock_message.tool_calls = None
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    llm.chat = AsyncMock(return_value=mock_response)
    return llm


@pytest.fixture
def mock_agents(mock_llm_factory):
    """模拟所有 Agent 的 LLM 响应 -- 构建完整的 Agent 集合

    返回字典: {agent_name: mock_llm}
    每个 mock_llm 预配置了该 Agent 典型的响应格式。
    """
    import json

    coordinator_response = json.dumps({
        "title": "资源分配优化问题",
        "background": "某公司需要将有限资源分配给多个项目",
        "ques_count": 2,
        "ques1": "建立资源分配优化模型",
        "ques2": "分析最优方案的敏感性",
        "is_valid": True,
    }, ensure_ascii=False)

    modeler_response = json.dumps({
        "eda": "对数据进行探索性分析，包括数据概览、缺失值分析、变量分布和相关性分析。重点关注资源约束和收益数据的分布特征。",
        "ques1": "使用线性规划模型求解资源分配问题，目标函数为最大化总收益，约束条件为资源总量限制。使用scipy.optimize.linprog求解。",
        "ques2": "对关键参数（资源总量、收益率）进行敏感性分析，评估参数变动对最优解的影响。",
        "sensitivity_analysis": "使用蒙特卡罗模拟对模型参数进行扰动分析，评估模型稳健性。重点分析资源总量和收益系数的影响。",
    }, ensure_ascii=False)

    return {
        "coordinator": mock_llm_factory("coordinator", coordinator_response),
        "modeler": mock_llm_factory("modeler", modeler_response),
        "coder": mock_llm_factory("coder", "任务完成，代码已执行成功。"),
        "writer": mock_llm_factory("writer", "# 摘要\n\n本文研究了资源分配优化问题..."),
    }


@pytest.fixture
def mock_workflow(mock_agents, temp_dir):
    """模拟完整工作流 -- 提供预装配的工作流上下文

    包含:
    - mock_agents: 所有 Agent 的 Mock LLM
    - work_dir: 临时工作目录
    - questions: 标准化的问题数据
    - coordinator_response: 模拟的协调者输出
    - modeler_response: 模拟的建模者输出
    """
    # 模拟协调者输出
    coordinator_response = MagicMock()
    coordinator_response.questions = {
        "title": "资源分配优化问题",
        "background": "某公司需要将有限资源分配给多个项目",
        "ques_count": 2,
        "ques1": "建立资源分配优化模型",
        "ques2": "分析最优方案的敏感性",
    }
    coordinator_response.ques_count = 2
    coordinator_response.problem_type = "optimization"
    coordinator_response.difficulty_level = "medium"
    coordinator_response.data_dependencies = None
    coordinator_response.recommended_methods = ["线性规划"]
    coordinator_response.sub_problem_dependencies = None

    # 模拟建模者输出
    modeler_response = MagicMock()
    modeler_response.questions_solution = {
        "eda": "数据探索分析方案",
        "ques1": "使用线性规划求解资源分配",
        "ques2": "敏感性分析方案",
        "sensitivity_analysis": "蒙特卡罗模拟",
    }
    modeler_response.model_configs = None

    return {
        "agents": mock_agents,
        "work_dir": temp_dir,
        "questions": coordinator_response.questions,
        "coordinator_response": coordinator_response,
        "modeler_response": modeler_response,
    }


# ================== 认证测试 Fixtures ==================


@pytest.fixture
def valid_token():
    """生成有效的 JWT Token（用于集成测试中的认证请求）。

    使用 auth 模块的 create_access_token 函数生成，
    确保与应用内部的 Token 验证逻辑一致。
    """
    from app.utils.auth import create_access_token

    return create_access_token(
        data={"sub": "test-user-001", "email": "test@example.com"}
    )


@pytest.fixture
def auth_headers(valid_token):
    """预配置的认证请求头。

    返回包含 Bearer Token 的 Authorization 头，
    可直接传入 httpx.AsyncClient 的 headers 参数。
    """
    return {"Authorization": f"Bearer {valid_token}"}


@pytest.fixture
def expired_token():
    """生成已过期的 JWT Token（用于测试 Token 过期场景）。"""
    from datetime import timedelta

    from app.utils.auth import create_access_token

    return create_access_token(
        data={"sub": "test-user-001", "email": "test@example.com"},
        expires_delta=timedelta(seconds=-1),
    )


@pytest.fixture
async def authenticated_client(client, auth_headers):
    """预注入认证头的异步 HTTP 客户端。

    在已有 client fixture 基础上，为每个请求自动附加 Authorization 头，
    简化需要认证的端点测试。

    注意: 此 fixture 依赖 client fixture（conftest 中定义），
    底层 httpx.AsyncClient 的 headers 在创建后不可变，
    因此通过 (client, auth_headers) 元组方式返回。
    """
    return client, auth_headers


# ================== 清理Hooks ==================

def pytest_runtest_teardown(item, nextitem):
    """测试完成后清理"""
    # 清理临时文件等
    pass


def pytest_configure(config):
    """pytest配置"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "websocket: marks tests as websocket tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
