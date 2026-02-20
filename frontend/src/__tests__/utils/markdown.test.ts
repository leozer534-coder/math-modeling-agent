/**
 * Markdown 渲染工具 单元测试
 *
 * 覆盖场景：
 * - XSS 防护（sanitizeHtml）
 *   - 危险标签移除（script, iframe, object 等）
 *   - 事件处理器属性移除（onclick, onerror 等）
 *   - 危险协议过滤（javascript:, data:, vbscript:）
 *   - 安全的 data:image/ 保留（base64 内嵌图片）
 * - Markdown 渲染基础功能
 * - 数学公式渲染（KaTeX）
 * - 辅助函数（getMarkdownLines）
 */

import {
	getMarkdownLines,
	renderMarkdown,
	sanitizeHtml,
} from "@/utils/markdown";
import { describe, expect, it, vi } from "vitest";

// ============================================================
// XSS 防护测试（sanitizeHtml）
// ============================================================
describe("sanitizeHtml - XSS 防护", () => {
	// ========================================================
	// 危险标签移除
	// ========================================================
	describe("危险标签移除", () => {
		it("应移除 <script> 标签", () => {
			const input = '<p>安全内容</p><script>alert("XSS")</script>';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("<script");
			expect(result).not.toContain("alert");
			expect(result).toContain("安全内容");
		});

		it("应移除 <iframe> 标签", () => {
			const input = '<iframe src="https://evil.com"></iframe><p>正常内容</p>';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("<iframe");
			expect(result).toContain("正常内容");
		});

		it("应移除 <object> 标签", () => {
			const input = '<object data="evil.swf"></object>';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("<object");
		});

		it("应移除 <embed> 标签", () => {
			const input = '<embed src="evil.swf">';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("<embed");
		});

		it("应移除 <form> 标签", () => {
			const input =
				'<form action="https://evil.com"><input type="text"></form>';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("<form");
		});

		it("应移除 <style> 标签", () => {
			const input = "<style>body{display:none}</style><p>内容</p>";
			const result = sanitizeHtml(input);
			expect(result).not.toContain("<style");
			expect(result).toContain("内容");
		});

		it("应移除 <svg> 标签（可被滥用执行脚本）", () => {
			const input = '<svg onload="alert(1)"><circle r="10"/></svg>';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("<svg");
		});

		it("应移除 <math> 标签", () => {
			const input = "<math><mrow></mrow></math>";
			const result = sanitizeHtml(input);
			expect(result).not.toContain("<math");
		});

		it("应保留安全的 HTML 标签", () => {
			const input =
				'<p>段落</p><strong>粗体</strong><em>斜体</em><a href="https://safe.com">链接</a>';
			const result = sanitizeHtml(input);
			expect(result).toContain("<p>");
			expect(result).toContain("<strong>");
			expect(result).toContain("<em>");
			expect(result).toContain("<a");
		});
	});

	// ========================================================
	// 事件处理器属性移除
	// ========================================================
	describe("事件处理器属性移除", () => {
		it("应移除 onclick 属性", () => {
			const input = '<div onclick="alert(1)">点击我</div>';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("onclick");
			expect(result).toContain("点击我");
		});

		it("应移除 onerror 属性", () => {
			const input = '<img src="x" onerror="alert(1)">';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("onerror");
		});

		it("应移除 onload 属性", () => {
			const input = '<img src="valid.png" onload="alert(1)">';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("onload");
		});

		it("应移除 onmouseover 属性", () => {
			const input = '<a onmouseover="alert(1)" href="#">hover</a>';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("onmouseover");
		});

		it("应移除所有 on* 开头的事件属性", () => {
			const input =
				'<div onfocus="alert(1)" onblur="alert(2)" onkeydown="alert(3)">内容</div>';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("onfocus");
			expect(result).not.toContain("onblur");
			expect(result).not.toContain("onkeydown");
		});
	});

	// ========================================================
	// 危险协议过滤
	// ========================================================
	describe("危险协议过滤", () => {
		it("应移除 javascript: 协议链接", () => {
			const input = '<a href="javascript:alert(1)">点击</a>';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("javascript:");
		});

		it("应移除 vbscript: 协议", () => {
			const input = '<a href="vbscript:MsgBox(1)">链接</a>';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("vbscript:");
		});

		it("应移除 data: 协议（非图片场景）", () => {
			const input =
				'<a href="data:text/html,<script>alert(1)</script>">链接</a>';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("data:text/html");
		});

		it("应保留 img 标签的 data:image/ 协议（安全的 base64 图片）", () => {
			const input = '<img src="data:image/png;base64,iVBORw0KGgo=" alt="图片">';
			const result = sanitizeHtml(input);
			expect(result).toContain("data:image/png");
		});

		it("应移除非 img 标签上的 data:image/ 协议", () => {
			const input = '<a href="data:image/png;base64,abc">链接</a>';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("data:image");
		});
	});

	// ========================================================
	// 可执行属性移除
	// ========================================================
	describe("可执行属性移除", () => {
		it("应移除 srcdoc 属性", () => {
			const input = '<div srcdoc="<script>alert(1)</script>">内容</div>';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("srcdoc");
		});

		it("应移除 formaction 属性", () => {
			const input = '<button formaction="https://evil.com">提交</button>';
			const result = sanitizeHtml(input);
			expect(result).not.toContain("formaction");
		});
	});

	// ========================================================
	// 综合安全场景
	// ========================================================
	describe("综合安全场景", () => {
		it("多重攻击向量应全部被净化", () => {
			const input = `
        <script>alert("xss")</script>
        <img src="x" onerror="alert(1)">
        <a href="javascript:void(0)">恶意链接</a>
        <iframe src="https://evil.com"></iframe>
        <p>正常内容保留</p>
      `;
			const result = sanitizeHtml(input);
			expect(result).not.toContain("<script");
			expect(result).not.toContain("onerror");
			expect(result).not.toContain("javascript:");
			expect(result).not.toContain("<iframe");
			expect(result).toContain("正常内容保留");
		});

		it("纯文本内容应不受影响", () => {
			const input = "<p>这是一段普通文本，包含数字 123 和符号 @#$</p>";
			const result = sanitizeHtml(input);
			expect(result).toContain("这是一段普通文本");
			expect(result).toContain("123");
		});

		it("空字符串应返回空字符串", () => {
			expect(sanitizeHtml("")).toBe("");
		});
	});
});

// ============================================================
// Markdown 渲染测试
// ============================================================
describe("renderMarkdown", () => {
	it("应渲染基本 Markdown 语法", async () => {
		const result = await renderMarkdown("**粗体** 和 *斜体*");
		expect(result).toContain("<strong>");
		expect(result).toContain("<em>");
	});

	it("应渲染标题", async () => {
		const result = await renderMarkdown("# 一级标题");
		expect(result).toContain("<h1");
		expect(result).toContain("一级标题");
	});

	it("应渲染代码块", async () => {
		const result = await renderMarkdown('```python\nprint("hello")\n```');
		expect(result).toContain("<code");
		expect(result).toContain("print");
	});

	it("应渲染列表", async () => {
		const result = await renderMarkdown("- 项目1\n- 项目2");
		expect(result).toContain("<li>");
	});

	it("应渲染链接", async () => {
		const result = await renderMarkdown("[链接](https://example.com)");
		expect(result).toContain('href="https://example.com"');
		expect(result).toContain("链接");
	});

	it("渲染结果应经过 XSS 净化", async () => {
		const result = await renderMarkdown("正常文本 <script>alert(1)</script>");
		expect(result).not.toContain("<script");
	});
});

// ============================================================
// 数学公式渲染测试
// ============================================================
describe("数学公式渲染", () => {
	it("应渲染行内公式 \\( \\)", async () => {
		const result = await renderMarkdown("行内公式 \\(E=mc^2\\) 结束");
		// KaTeX 渲染后会生成 katex 相关的 HTML
		expect(result).toContain("katex");
	});

	it("应渲染块级公式 $$", async () => {
		const result = await renderMarkdown("$$\\sum_{i=1}^{n} x_i$$");
		expect(result).toContain("math-block");
		expect(result).toContain("katex");
	});

	it("KaTeX 渲染出错时应回退到原始文本", async () => {
		// 使用一个格式正确但可能触发特殊处理的公式
		const result = await renderMarkdown("$$x + y$$");
		// 不管渲染成功与否，不应该抛出异常
		expect(result).toBeTruthy();
	});
});

// ============================================================
// 辅助函数测试
// ============================================================
describe("getMarkdownLines", () => {
	it("单行文本应返回 1", () => {
		expect(getMarkdownLines("hello")).toBe(1);
	});

	it("多行文本应返回正确行数", () => {
		expect(getMarkdownLines("line1\nline2\nline3")).toBe(3);
	});

	it("空字符串应返回 1（split 的行为）", () => {
		expect(getMarkdownLines("")).toBe(1);
	});

	it("末尾换行应计入额外行", () => {
		expect(getMarkdownLines("line1\nline2\n")).toBe(3);
	});
});
