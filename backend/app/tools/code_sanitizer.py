# code_sanitizer.py
"""
代码安全审查层

在代码执行前进行轻量级安全检查，作为防御纵深（defense-in-depth）的一环。
不替代沙箱隔离，而是在沙箱之前提供额外的安全屏障。

注意：数学建模场景需要允许 open()（读写数据文件）、部分网络库（学术搜索），
因此黑名单经过精细调整以避免误杀正常建模代码。
"""

import re

from app.utils.log_util import logger


class CodeSanitizer:
    """
    代码安全审查器

    检测 LLM 生成代码中的危险模式，阻止明显的恶意操作。
    """

    # (正则模式, 风险描述, 严重级别)
    # severity: "block" = 直接拒绝, "warn" = 警告但允许执行
    DANGEROUS_PATTERNS: list[tuple[str, str, str]] = [
        # === 系统命令执行 (block) ===
        (r"\bos\.system\s*\(", "禁止使用 os.system() 执行系统命令", "block"),
        (r"\bsubprocess\s*\.\s*(?:run|call|Popen|check_output|check_call)\s*\(",
         "禁止使用 subprocess 执行外部命令", "block"),
        (r"\bsubprocess\s*\.\s*getoutput\s*\(",
         "禁止使用 subprocess.getoutput()", "block"),
        (r"\bcommands\s*\.\s*getoutput\s*\(",
         "禁止使用 commands.getoutput()", "block"),

        # === 动态代码执行 (block) ===
        (r"\b__import__\s*\(", "禁止使用 __import__() 动态导入", "block"),
        (r"\beval\s*\(\s*(?!\"[^\"]*\bdf\b)",
         "禁止使用 eval()（pandas eval 除外）", "block"),
        (r"\bexec\s*\(\s*(?!\")",
         "禁止使用 exec() 执行动态代码", "block"),
        (r"\bcompile\s*\(.*\bexec\b",
         "禁止使用 compile() + exec 组合", "block"),

        # === 文件系统破坏 (block) ===
        (r"\bshutil\.rmtree\s*\(", "禁止使用 shutil.rmtree() 删除目录树", "block"),
        (r"\bos\.removedirs\s*\(", "禁止使用 os.removedirs()", "block"),
        (r"\bos\.remove\s*\(\s*['\"]\/",
         "禁止删除系统路径下的文件", "block"),
        (r"\bopen\s*\(\s*['\"]\/etc\/", "禁止访问 /etc/ 系统配置", "block"),
        (r"\bopen\s*\(\s*['\"]\/proc\/", "禁止访问 /proc/ 系统信息", "block"),
        (r"\bopen\s*\(\s*['\"]\/sys\/", "禁止访问 /sys/ 系统目录", "block"),
        (r"\bopen\s*\(\s*['\"]C:\\\\Windows",
         "禁止访问 Windows 系统目录", "block"),

        # === 网络风险 (block) ===
        (r"\bsocket\s*\.\s*socket\s*\(", "禁止创建原始 socket 连接", "block"),
        (r"\bhttp\.server\b", "禁止启动 HTTP 服务器", "block"),
        (r"\bsocketserver\b", "禁止使用 socketserver", "block"),
        (r"\bparamiko\b", "禁止使用 SSH 库", "block"),
        (r"\bftplib\b", "禁止使用 FTP 库", "block"),

        # === 反射 / 沙箱逃逸 (block) ===
        (r"\b__builtins__\b", "禁止访问 __builtins__", "block"),
        (r"\b__subclasses__\s*\(", "禁止使用 __subclasses__()", "block"),
        (r"\b__globals__\b", "禁止访问 __globals__", "block"),
        (r"\b__code__\b", "禁止访问 __code__", "block"),
        (r"\bctypes\b", "禁止使用 ctypes 调用 C 函数", "block"),

        # === 资源滥用 (warn) ===
        (r"\bwhile\s+True\s*:", "检测到无限循环 while True", "warn"),
        (r"\bmultiprocessing\s*\.\s*Pool\s*\(",
         "检测到多进程 Pool，注意资源消耗", "warn"),
    ]

    # 预编译正则（性能优化）
    _compiled_patterns: list[tuple[re.Pattern, str, str]] | None = None

    @classmethod
    def _get_compiled_patterns(cls) -> list[tuple[re.Pattern, str, str]]:
        """懒加载编译正则模式"""
        if cls._compiled_patterns is None:
            cls._compiled_patterns = [
                (re.compile(pattern, re.IGNORECASE), desc, severity)
                for pattern, desc, severity in cls.DANGEROUS_PATTERNS
            ]
        return cls._compiled_patterns

    @classmethod
    def sanitize(cls, code: str) -> tuple[bool, str]:
        """
        审查代码安全性

        Args:
            code: 待审查的 Python 代码

        Returns:
            (is_safe, reason)
            - is_safe=True: 代码通过审查
            - is_safe=False: 代码包含危险模式，reason 说明原因
        """
        if not code or not code.strip():
            return True, ""

        blocked_reasons: list[str] = []
        warnings: list[str] = []

        for compiled_re, desc, severity in cls._get_compiled_patterns():
            match = compiled_re.search(code)
            if match:
                matched_text = match.group(0).strip()
                detail = f"  - {desc} (匹配: `{matched_text}`)"

                if severity == "block":
                    blocked_reasons.append(detail)
                elif severity == "warn":
                    warnings.append(detail)

        # 记录警告
        if warnings:
            logger.warning(
                "⚠️ 代码安全审查警告:\n" + "\n".join(warnings)
            )

        # 存在阻断级别的危险模式
        if blocked_reasons:
            reason = (
                "🚫 代码安全审查未通过，检测到以下危险操作:\n"
                + "\n".join(blocked_reasons)
            )
            logger.error(reason)
            return False, reason

        return True, ""

    @classmethod
    def sanitize_or_raise(cls, code: str) -> None:
        """
        审查代码，不安全则抛出异常

        Args:
            code: 待审查的 Python 代码

        Raises:
            ValueError: 代码包含危险模式
        """
        is_safe, reason = cls.sanitize(code)
        if not is_safe:
            raise ValueError(reason)
