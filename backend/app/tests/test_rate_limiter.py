"""
速率限制器单元测试
"""
import asyncio
import unittest
from unittest.mock import MagicMock

from app.utils.rate_limiter import (
    RateLimiter,
    RateLimitRule,
    RateLimitState,
    create_rate_limiter,
)


class TestRateLimitRule(unittest.TestCase):
    """测试速率限制规则"""

    def test_create_rule_with_defaults(self):
        """测试创建带默认值的规则"""
        rule = RateLimitRule(requests=60, window=60)
        self.assertEqual(rule.requests, 60)
        self.assertEqual(rule.window, 60)
        self.assertEqual(rule.burst, 0)

    def test_create_rule_with_burst(self):
        """测试创建带突发值的规则"""
        rule = RateLimitRule(requests=60, window=60, burst=10)
        self.assertEqual(rule.burst, 10)


class TestRateLimitState(unittest.TestCase):
    """测试速率限制状态"""

    def test_default_state(self):
        """测试默认状态"""
        state = RateLimitState()
        self.assertEqual(state.requests, [])
        self.assertEqual(state.blocked_until, 0)


class TestRateLimiter(unittest.TestCase):
    """测试速率限制器"""

    def setUp(self):
        """设置测试环境"""
        self.limiter = RateLimiter(
            default_rule=RateLimitRule(requests=5, window=60, burst=2)
        )

    def test_init_default_rule(self):
        """测试初始化默认规则"""
        limiter = RateLimiter()
        self.assertIsNotNone(limiter.default_rule)
        self.assertEqual(limiter.default_rule.requests, 60)

    def test_add_route_rule(self):
        """测试添加路由规则"""
        rule = RateLimitRule(requests=10, window=30)
        self.limiter.add_route_rule("/api/test", rule)
        self.assertIn("/api/test", self.limiter._route_rules)

    def test_whitelist(self):
        """测试白名单"""
        self.limiter.add_to_whitelist("127.0.0.1")
        self.assertIn("127.0.0.1", self.limiter._whitelist)

    def test_blacklist(self):
        """测试黑名单"""
        self.limiter.add_to_blacklist("192.168.1.100")
        self.assertIn("192.168.1.100", self.limiter._blacklist)

    def test_remove_from_blacklist(self):
        """测试从黑名单移除"""
        self.limiter.add_to_blacklist("192.168.1.100")
        self.limiter.remove_from_blacklist("192.168.1.100")
        self.assertNotIn("192.168.1.100", self.limiter._blacklist)

    def test_get_stats(self):
        """测试获取统计信息"""
        self.limiter.add_to_whitelist("127.0.0.1")
        self.limiter.add_to_blacklist("10.0.0.1")
        stats = self.limiter.get_stats()
        self.assertEqual(stats["whitelisted"], 1)
        self.assertEqual(stats["blacklisted"], 1)

    def test_get_rule_for_path(self):
        """测试获取路径规则"""
        custom_rule = RateLimitRule(requests=10, window=30)
        self.limiter.add_route_rule("/api/custom", custom_rule)

        # 匹配自定义规则
        rule = self.limiter._get_rule_for_path("/api/custom/endpoint")
        self.assertEqual(rule.requests, 10)

        # 使用默认规则
        default_rule = self.limiter._get_rule_for_path("/other/path")
        self.assertEqual(default_rule.requests, 5)


class TestRateLimiterAsync(unittest.TestCase):
    """测试速率限制器异步功能"""

    def setUp(self):
        """设置测试环境"""
        self.limiter = RateLimiter(
            default_rule=RateLimitRule(requests=3, window=60, burst=1)
        )
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """清理测试环境"""
        self.loop.close()

    def _create_mock_request(self, client_ip: str = "127.0.0.1", path: str = "/api/test"):
        """创建模拟请求"""
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = client_ip
        request.headers = {}
        request.url = MagicMock()
        request.url.path = path
        return request

    def test_check_rate_limit_allowed(self):
        """测试允许的请求"""
        async def run_test():
            request = self._create_mock_request()
            allowed, info = await self.limiter.check_rate_limit(request)
            self.assertTrue(allowed)
            self.assertIn("remaining", info)

        self.loop.run_until_complete(run_test())

    def test_check_rate_limit_whitelisted(self):
        """测试白名单客户端"""
        async def run_test():
            self.limiter.add_to_whitelist("127.0.0.1")
            request = self._create_mock_request(client_ip="127.0.0.1")
            allowed, info = await self.limiter.check_rate_limit(request)
            self.assertTrue(allowed)
            self.assertEqual(info, {})

        self.loop.run_until_complete(run_test())

    def test_check_rate_limit_blacklisted(self):
        """测试黑名单客户端"""
        async def run_test():
            self.limiter.add_to_blacklist("192.168.1.100")
            request = self._create_mock_request(client_ip="192.168.1.100")
            allowed, info = await self.limiter.check_rate_limit(request)
            self.assertFalse(allowed)
            self.assertEqual(info["error"], "blocked")

        self.loop.run_until_complete(run_test())

    def test_check_rate_limit_exceeded(self):
        """测试超过限制"""
        async def run_test():
            request = self._create_mock_request(client_ip="10.0.0.1")

            # 发送超过限制的请求 (3 + 1 burst = 4)
            for i in range(5):
                allowed, info = await self.limiter.check_rate_limit(request)
                if i < 4:
                    self.assertTrue(allowed, f"请求 {i+1} 应该被允许")
                else:
                    self.assertFalse(allowed, f"请求 {i+1} 应该被拒绝")

        self.loop.run_until_complete(run_test())

    def test_remaining_decreases(self):
        """测试剩余配额递减"""
        async def run_test():
            request = self._create_mock_request(client_ip="10.0.0.2")

            allowed1, info1 = await self.limiter.check_rate_limit(request)
            allowed2, info2 = await self.limiter.check_rate_limit(request)

            self.assertTrue(allowed1)
            self.assertTrue(allowed2)
            self.assertGreater(info1["remaining"], info2["remaining"])

        self.loop.run_until_complete(run_test())

    def test_x_forwarded_for_header(self):
        """测试X-Forwarded-For头"""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.1, 70.41.3.18"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        client_id = self.limiter._get_client_id(request)
        self.assertEqual(client_id, "203.0.113.1")

    def test_x_real_ip_header(self):
        """测试X-Real-IP头"""
        request = MagicMock()
        request.headers = {"X-Real-IP": "198.51.100.1"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        client_id = self.limiter._get_client_id(request)
        self.assertEqual(client_id, "198.51.100.1")


class TestCreateRateLimiter(unittest.TestCase):
    """测试速率限制器工厂函数"""

    def test_create_with_defaults(self):
        """测试使用默认值创建"""
        limiter = create_rate_limiter()
        self.assertEqual(limiter.default_rule.requests, 60)
        self.assertEqual(limiter.default_rule.burst, 10)

    def test_create_with_custom_values(self):
        """测试使用自定义值创建"""
        limiter = create_rate_limiter(
            requests_per_minute=100,
            burst=20,
            modeling_requests_per_minute=5
        )
        self.assertEqual(limiter.default_rule.requests, 100)
        self.assertEqual(limiter.default_rule.burst, 20)

    def test_modeling_route_rule(self):
        """测试建模路由规则"""
        limiter = create_rate_limiter(modeling_requests_per_minute=5)
        rule = limiter._get_rule_for_path("/api/modeling/start")
        self.assertEqual(rule.requests, 5)

    def test_upload_route_rule(self):
        """测试上传路由规则"""
        limiter = create_rate_limiter()
        rule = limiter._get_rule_for_path("/api/upload/file")
        self.assertEqual(rule.requests, 20)


if __name__ == "__main__":
    unittest.main()
