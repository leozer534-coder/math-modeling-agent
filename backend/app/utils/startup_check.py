"""
启动时的系统检查
在应用启动时执行环境验证和依赖检查
"""
import asyncio
import os
import sys

from app.config.setting import settings
from app.utils.log_util import logger


class StartupChecker:
    """启动检查器"""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def check_all(self) -> bool:
        """
        执行所有检查

        Returns:
            bool: 是否通过检查
        """
        logger.info("=" * 60)
        logger.info("🚀 开始系统启动检查...")
        logger.info("=" * 60)

        # 基础检查
        self._check_python_version()
        self._check_env_variables()
        self._check_directories()
        self._check_required_packages()

        # 输出配置摘要
        logger.info("\n" + settings.summary())

        # 输出检查结果
        self._print_results()

        return len(self.errors) == 0

    def _check_python_version(self):
        """检查Python版本"""
        logger.info("\n🐍 检查Python版本...")

        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 10):
            self.errors.append(
                f"❌ Python版本过低: {version.major}.{version.minor}，需要 >= 3.10"
            )
        else:
            logger.info("  ✅ Python %s.%s.%s", version.major, version.minor, version.micro)

    def _check_env_variables(self):
        """检查环境变量配置"""
        logger.info("\n📋 检查环境变量配置...")

        # 必需的环境变量
        if not settings.ENV:
            self.errors.append("❌ 缺少必需的环境变量: ENV")
        else:
            logger.info("  ✅ ENV: %s", settings.ENV)

        # 检查 API Keys
        api_keys = {
            "COORDINATOR": settings.COORDINATOR_API_KEY,
            "MODELER": settings.MODELER_API_KEY,
            "CODER": settings.CODER_API_KEY,
            "WRITER": settings.WRITER_API_KEY,
        }

        configured_keys = []
        missing_keys = []

        for name, value in api_keys.items():
            if value and value != "your_api_key_here":
                configured_keys.append(name)
            else:
                missing_keys.append(name)

        if configured_keys:
            logger.info("  ✅ 已配置的API Keys: %s", ', '.join(configured_keys))

        if missing_keys:
            self.warnings.append(
                f"⚠️  以下API Key未配置: {', '.join(missing_keys)}\n"
                "   提示: 可以通过前端设置页面配置，或在.env文件中设置"
            )

        # 检查 Redis URL
        if settings.REDIS_URL:
            logger.info("  ✅ REDIS_URL: %s", settings.REDIS_URL)
        else:
            self.errors.append("❌ REDIS_URL 未配置")

        # 检查 CORS 配置
        if settings.CORS_ALLOW_ORIGINS == ["*"]:
            if settings.is_production():
                self.warnings.append(
                    "⚠️  生产环境CORS配置为 *，建议限制具体域名"
                )
            else:
                logger.info("  ⚠️  CORS: * (开发模式)")
        else:
            logger.info("  ✅ CORS: %s", settings.CORS_ALLOW_ORIGINS)

        # 检查 DEBUG 模式
        if settings.DEBUG and settings.is_production():
            self.warnings.append(
                "⚠️  生产环境开启了DEBUG模式，建议设置 DEBUG=false"
            )

    def _check_directories(self):
        """检查必需的目录"""
        logger.info("\n📁 检查必需的目录...")

        required_dirs = [
            "project",
            "project/work_dir",
            "logs",
            "logs/messages",
        ]

        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                logger.info("  📂 创建目录: %s", dir_path)
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    logger.info("  ✅ %s", dir_path)
                except Exception as e:
                    self.errors.append(f"❌ 无法创建目录 {dir_path}: {str(e)}")
            else:
                logger.info("  ✅ %s", dir_path)

    def _check_required_packages(self):
        """检查必需的Python包"""
        logger.info("\n📦 检查必需的依赖包...")

        required_packages = [
            ("pandas", "数据处理"),
            ("numpy", "数值计算"),
            ("matplotlib", "图表绑制"),
            ("scikit-learn", "机器学习"),
            ("fastapi", "Web框架"),
            ("redis", "Redis客户端"),
            ("litellm", "LLM接口"),
        ]

        for package, description in required_packages:
            try:
                __import__(package.replace("-", "_"))
                logger.info("  ✅ %s (%s)", package, description)
            except ImportError:
                self.warnings.append(f"⚠️  {package} 未安装 ({description})")

    def _print_results(self):
        """打印检查结果"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 启动检查结果:")
        logger.info("=" * 60)

        if self.errors:
            logger.error("\n❌ 发现 %s 个错误:", len(self.errors))
            for error in self.errors:
                logger.error("  %s", error)

        if self.warnings:
            logger.warning("\n⚠️  发现 %s 个警告:", len(self.warnings))
            for warning in self.warnings:
                logger.warning("  %s", warning)

        if not self.errors and not self.warnings:
            logger.info("\n✅ 所有检查通过！系统准备就绪。")
        elif not self.errors:
            logger.info("\n✅ 必需检查通过，系统可以启动。")
        else:
            logger.error("\n❌ 启动检查失败！请修复上述错误后重试。")

        logger.info("=" * 60 + "\n")


async def check_redis_connection() -> bool:
    """
    异步检查Redis连接

    Returns:
        bool: 连接是否成功
    """
    try:
        from app.services.redis_manager import redis_manager

        client = await redis_manager.get_client()
        await client.ping()
        logger.info("✅ Redis连接正常")
        return True
    except Exception as e:
        logger.error("❌ Redis连接失败: %s", e)
        return False


def run_startup_checks() -> bool:
    """
    运行启动检查

    Returns:
        bool: 是否通过检查
    """
    checker = StartupChecker()
    passed = checker.check_all()

    if not passed:
        logger.error("🛑 启动检查未通过，请修复错误后重启应用")

        # 在非调试模式下，检查失败则退出
        if not settings.DEBUG:
            logger.critical("生产环境下禁止在检查失败时启动")
            sys.exit(1)

    return passed


def run_async_checks():
    """
    运行异步检查（在事件循环中调用）
    """
    async def _run():
        redis_ok = await check_redis_connection()
        if not redis_ok:
            logger.warning("Redis连接失败，部分功能可能不可用")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_run())
        else:
            loop.run_until_complete(_run())
    except RuntimeError:
        # 如果没有事件循环，创建一个新的
        asyncio.run(_run())
