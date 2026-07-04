"""
tool_system.py — 工具系统：从 if/elif 到 buildTool() 工厂模式

对应 Claude Code 源码:
  src/Tool.ts      — Tool 接口 + buildTool() 工厂 (第 783 行)
  src/tools.ts     — 工具注册表 + 过滤

学习目标:
  1. 理解为什么要把工具"对象化"
  2. 理解 buildTool() 的默认值策略 (fail-closed)
  3. 理解注册表模式怎么替代 if/elif 分发

运行:
  python tool_system.py
"""

from dataclasses import dataclass, field
from typing import Callable, Any
import json

# ╔══════════════════════════════════════════════════════════════╗
# ║  源码对照: src/Tool.ts 第 707-715 行                         ║
# ║  DefaultableToolKeys — 这些方法 buildTool 会提供默认值       ║
# ║  - isEnabled           → true                               ║
# ║  - isConcurrencySafe   → false  (fail-closed!)             ║
# ║  - isReadOnly          → false                              ║
# ║  - isDestructive       → false                              ║
# ║  - checkPermissions    → allow all                           ║
# ╚══════════════════════════════════════════════════════════════╝

TOOL_DEFAULTS = {
    "is_enabled":       lambda self, **kw: True,
    "is_concurrency_safe": lambda self, **kw: False,   # 默认不能并行
    "is_read_only":     lambda self, **kw: False,      # 默认可能有副作用
    "is_destructive":   lambda self, **kw: False,
    "check_permissions": lambda self, input_data, **kw: {"allowed": True},
    "user_facing_name": lambda self, **kw: "",
}


# ╔══════════════════════════════════════════════════════════════╗
# ║  Tool 类 — 把定义、校验、执行打包在一起                      ║
# ║                                                              ║
# ║  源码对照: src/Tool.ts 的 Tool 接口                          ║
# ║  以前你写一个新工具要改 3 个地方:                             ║
# ║    1. TOOLS 列表 (加定义)                                    ║
# ║    2. execute_tool() (加 elif)                               ║
# ║    3. 记得 required 参数不要写错                             ║
# ║                                                              ║
# ║  现在: 定义一个 Tool 对象 → registry.register() → 完事       ║
# ╚══════════════════════════════════════════════════════════════╝

class Tool:
    """一个工具 = 定义 + 校验 + 执行，全部封装在一起"""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable[[dict], str],
        required: list[str] | None = None,
        # ── 可选覆盖的默认值 ──
        is_read_only: bool | None = None,
        is_destructive: bool | None = None,
        is_concurrency_safe: bool | None = None,
        check_permissions: Callable | None = None,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
        self.required = required or []

        # 如果传了就用传的，否则用 TOOL_DEFAULTS
        self._is_read_only = is_read_only
        self._is_destructive = is_destructive
        self._is_concurrency_safe = is_concurrency_safe
        self._check_permissions = check_permissions

    # ── 生命周期方法 ──

    def validate(self, input_data: dict) -> str | None:
        """校验输入，有问题返回错误信息，没问题返回 None"""
        for field in self.required:
            if field not in input_data or not input_data[field]:
                return f"缺少必填参数: {field}"
        return None

    def call(self, input_data: dict) -> str:
        """执行工具"""
        return self.handler(input_data)

    # ── 能力查询 (默认值来自 TOOL_DEFAULTS，fail-closed) ──

    def is_enabled(self, **kw) -> bool:
        return True

    def is_read_only(self, **kw) -> bool:
        return self._is_read_only if self._is_read_only is not None else False

    def is_destructive(self, **kw) -> bool:
        return self._is_destructive if self._is_destructive is not None else False

    def is_concurrency_safe(self, **kw) -> bool:
        return self._is_concurrency_safe if self._is_concurrency_safe is not None else False

    def check_permissions(self, input_data: dict, **kw) -> dict:
        if self._check_permissions:
            return self._check_permissions(input_data, **kw)
        return {"allowed": True}

    # ── 跨厂商 Schema 生成 ──

    def to_openai_schema(self) -> dict:
        """OpenAI / DeepSeek 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required,
                },
            },
        }

    def to_anthropic_schema(self) -> dict:
        """Anthropic / Claude 格式"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required,
            },
        }


# ╔══════════════════════════════════════════════════════════════╗
# ║  buildTool() 工厂 — 对应 src/Tool.ts 第 783 行              ║
# ║                                                              ║
# ║  源码: return { ...TOOL_DEFAULTS, userFacingName: ..., ...def }  ║
# ║  它的工作: 填默认值 + 返回完整 Tool                          ║
# ╚══════════════════════════════════════════════════════════════╝

def build_tool(**kwargs) -> Tool:
    """工厂函数：给不完整的定义补上安全默认值"""
    return Tool(**kwargs)


# ╔══════════════════════════════════════════════════════════════╗
# ║  ToolRegistry — 对应 src/tools.ts 的工具注册                ║
# ║                                                              ║
# ║  源码里 tools.ts 管理着 60+ 个 tool 的注册、过滤、上下⽂     ║
# ║  这里是最简化的版本                                          ║
# ╚══════════════════════════════════════════════════════════════╝

class ToolRegistry:
    """工具注册表——不再需要 if/elif 分发"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool
        print(f"  [OK] 注册工具: {tool.name}")

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def all_openai_schemas(self) -> list[dict]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def all_anthropic_schemas(self) -> list[dict]:
        return [t.to_anthropic_schema() for t in self._tools.values()]

    def dispatch(self, name: str, input_data: dict) -> tuple[str | None, str]:
        """
        分发执行——替代 if/elif 的关键方法

        返回 (error, result): error 不为 None 表示校验失败
        """
        tool = self.get(name)
        if tool is None:
            return None, f"未知工具: {name}"

        # ① 校验输入
        error = tool.validate(input_data)
        if error:
            return error, ""

        # ② 检查权限 (Topic 03 会展开)
        perm = tool.check_permissions(input_data)
        if not perm.get("allowed"):
            return f"权限拒绝: {perm.get('reason', '未知原因')}", ""

        # ③ 执行
        try:
            result = tool.call(input_data)
            return None, result
        except Exception as e:
            return f"执行错误: {e}", ""

    def describe(self):
        """打印工具清单"""
        print(f"\n[Tools] 已注册 {len(self._tools)} 个工具:")
        for name, tool in self._tools.items():
            flags = []
            if tool.is_read_only(): flags.append("只读")
            if tool.is_destructive(): flags.append("⚠️破坏性")
            if tool.is_concurrency_safe(): flags.append("可并行")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            print(f"  • {name}: {tool.description}{flag_str}")


# ──────────────────────────────────────────────────────────────
# 演示：用新系统重写 hello_agent 的工具部分
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # ── 定义工具 ──
    # 每个工具是一个 Tool 对象，定义 + 校验 + 执行，一次搞定

    time_tool = build_tool(
        name="get_current_time",
        description="获取当前系统时间",
        parameters={
            "timezone": {"type": "string", "description": "时区"},
        },
        handler=lambda args: f"当前时间: 2026-07-04 19:30:00 (模拟)",
        is_read_only=True,
        is_concurrency_safe=True,
    )

    calc_tool = build_tool(
        name="calculate",
        description="执行数学计算",
        parameters={
            "expression": {"type": "string", "description": "数学表达式"},
        },
        required=["expression"],
        handler=lambda args: f"计算结果: {args['expression']} = {eval(args['expression'])}",
        is_read_only=True,
        is_concurrency_safe=True,
    )

    email_tool = build_tool(
        name="send_email",
        description="发送邮件",
        parameters={
            "to":      {"type": "string", "description": "收件人"},
            "subject": {"type": "string", "description": "主题"},
            "body":    {"type": "string", "description": "正文"},
        },
        required=["to", "subject", "body"],
        handler=lambda args: f"邮件已发送至 {args['to']}",
        is_destructive=True,  # 发邮件有副作用
    )

    # ── 注册 ──
    registry = ToolRegistry()
    registry.register(time_tool)
    registry.register(calc_tool)
    registry.register(email_tool)

    registry.describe()

    # ── 用 registry.dispatch() 替代 if/elif ──
    print("\n" + "=" * 60)
    print("测试 dispatch:")

    # 正常调用
    err, result = registry.dispatch("calculate", {"expression": "3 * 7"})
    print(f"  calculate(3*7) → err={err}, result={result}")

    # 缺少必填参数
    err, result = registry.dispatch("calculate", {})
    print(f"  calculate() 缺参数 → err={err}")

    # 未知工具
    err, result = registry.dispatch("fly_to_moon", {})
    print(f"  fly_to_moon → err={err}, result={result}")

    # ── 跨厂商 schema ──
    print("\n" + "=" * 60)
    print("OpenAI/DeepSeek 格式:")
    print(json.dumps(registry.all_openai_schemas(), ensure_ascii=False, indent=2))

    print("\nAnthropic/Claude 格式:")
    print(json.dumps(registry.all_anthropic_schemas(), ensure_ascii=False, indent=2))
