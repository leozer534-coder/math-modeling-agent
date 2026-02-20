/**
 * Vitest 全局测试配置
 *
 * 在每个测试文件运行前自动执行，用于：
 * 1. 初始化 DOM 环境模拟（localStorage、sessionStorage 等）
 * 2. 设置全局 mock（如 import.meta.env）
 * 3. 清理每次测试后的副作用
 */

import { afterEach, beforeEach, vi } from "vitest";

// ============================================================
// 环境变量模拟
// ============================================================

// 模拟 import.meta.env，提供默认的开发环境变量
vi.stubGlobal("import.meta", {
	env: {
		VITE_WS_URL: "ws://localhost:8000",
		VITE_API_BASE_URL: "http://localhost:8000",
		MODE: "test",
		DEV: true,
		PROD: false,
	},
});

// ============================================================
// 全局生命周期钩子
// ============================================================

beforeEach(() => {
	// 每个测试前清空 localStorage，避免测试间互相干扰
	localStorage.clear();
	sessionStorage.clear();
});

afterEach(() => {
	// 每个测试后清除所有定时器（避免 setTimeout / setInterval 泄漏）
	vi.clearAllTimers();
	// 恢复所有被 mock 的模块和函数
	vi.restoreAllMocks();
});
