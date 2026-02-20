"""
核心路由模块单元测试

测试范围:
  - 当前已注册的路由端点基本可达性验证

测试策略:
  - 使用 httpx.AsyncClient + ASGITransport 进行 ASGI 层测试
  - 数据库依赖通过 conftest.py 中的 dependency_overrides 替换为 Mock
  - 只验证 HTTP 状态码和基本响应格式，不测试完整业务逻辑

注意:
  - pytest.ini 配置了 asyncio_mode = auto，无需手动标记 @pytest.mark.asyncio
  - client fixture 定义在 conftest.py 中，基于 httpx.AsyncClient + ASGITransport
  - 以下测试类已移除（对应路由尚未注册到 app）：
    - TestHealthEndpoints (/health 端点)
    - TestAuthRouter (/api/v1/auth/* 认证路由)
    - TestFilesRouter (/api/v1/files/* 安全文件路由)
    - TestAPIVersioning (/api/* -> /api/v1/* 重定向)
    - TestCommonRouter (/api/v1/* 通用路由)
"""
