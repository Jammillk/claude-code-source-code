"""
tool_system_exercise.py — 动手练习：实现 Tool 类 + ToolRegistry

你的任务：补全下面标记了 TODO 的方法。

核心学习目标（理解这些就算掌握本章）:
  1. 为什么要把工具"对象化"——一个 Tool = 定义 + 校验 + 执行，全封装
  2. Registry 的 dispatch map 怎么替代 if/elif 硬编码
  3. build_tool() 工厂的 fail-closed 默认值策略

Python 速查（Java 对照）:
  self.xxx        = Java 的 this.xxx（且 self 必须显式写在参数列表第一位）
  dict            = HashMap       例: {"key": "value"}
  list[str]       = List<String>  例: ["a", "b"]
  str | None      = Optional<String>  返回 str 或 None
  f"...{var}..."  = String.format("...%s...", var)
  value or default = value != null ? value : default  (None/""/[]/0 都是 falsy)
  **kwargs         打包/解包关键字参数（Java 没有，见下面具体说明）

运行验证:
  python tool_system_exercise.py
  输出末尾看到 "✅ 全部测试通过" 就说明实现正确。

完整的参考答案在 tool_system.py，建议先自己写，实在卡住了再看。
"""

from typing import Callable
import json

# ═══════════════════════════════════════════════════════════════
# 第一部分：Tool 类 — 把"一个工具"封装成对象
# ═══════════════════════════════════════════════════════════════

class Tool:
    """
    一个工具 = 定义(name/description/parameters) + 校验(validate) + 执行(call)

    思考：hello_agent.py 里定义一个新工具要改几个地方？这里又要改几个地方？
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable[[dict], str],
        required: list[str] | None = None,
        is_read_only: bool | None = None,
        is_destructive: bool | None = None,
    ):
        # ┌─────────────────────────────────────────────┐
        # │ TODO 1: 把 5 个参数存到 self 上             │
        # │                                              │
        # │ 提示:                                        │
        # │   self.name = name      ← 基本赋值          │
        # │   self.required = required or []             │
        # │        ↑ Python 惯用法: None 时用空列表兜底 │
        # │                                              │
        # │ 需要存的字段: name, description, parameters, │
        # │   handler, required                          │
        # │   _is_read_only, _is_destructive             │
        # │   (前缀 _ 表示"内部使用"，是 Python 约定)    │
        # └─────────────────────────────────────────────┘
        #pass  # ← 删掉这行，写你的代码
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
        self.required = required or []
        self._is_read_only = is_read_only
        self._is_destructive = is_destructive
        


    # ── 生命周期方法 ──

    def validate(self, input_data: dict) -> str | None:
        """
        校验输入参数。遍历 required 列表，检查每个字段:
          - 是否存在于 input_data 中？
          - 值是否非空？

        返回: 错误信息字符串（校验失败）或 None（通过）
        """
        # ┌─────────────────────────────────────────────┐
        # │ TODO 2: 实现参数校验                         │
        # │                                              │
        # │ 伪代码:                                      │
        # │   for field in self.required:               │
        # │       if field 不在 input_data 或 值为空:    │
        # │           return f"缺少必填参数: {field}"     │
        # │   return None                               │
        # │                                              │
        # │ Python 提示:                                 │
        # │   field not in input_data  ← 检查 key 存在   │
        # │   not input_data[field]    ← 检查值非空      │
        # │   (None, "", [], 0 都是 falsy)               │
        # └─────────────────────────────────────────────┘
        for field in self.required:
            if field not in input_data or not input_data[field]:
                return f"no param: {field}"
        return None

    def call(self, input_data: dict) -> str:
        """执行工具：调用创建时传入的 handler 函数"""
        # ┌─────────────────────────────────────────────┐
        # │ TODO 3: 一行代码——调用 handler 并返回结果    │
        # └─────────────────────────────────────────────┘
        return self.handler(input_data)

    # ── 能力标记 ──

    def is_read_only(self) -> bool:
        # ┌─────────────────────────────────────────────┐
        # │ TODO 4: 如果 _is_read_only 不为 None，返回它 │
        # │         否则返回 False (fail-closed)         │
        # │                                              │
        # │ 提示: x if condition else y  (三元表达式)   │
        # └─────────────────────────────────────────────┘
        # if self._is_read_only is None:
        #     return False
        # return True
        return self._is_read_only if self._is_read_only is not None else False

    def is_destructive(self) -> bool:
        #pass  # ← TODO 5: 同上逻辑，检查 _is_destructive
        return self._is_destructive if self._is_destructive is not None else False

    # ── 跨厂商 Schema ──
    # 思考：为什么要把格式生成放在 Tool 类里，而不是放在 API 调用处？

    def to_openai_schema(self) -> dict:
        """生成 OpenAI / DeepSeek 格式的工具定义"""
        # ┌─────────────────────────────────────────────┐
        # │ TODO 6: 返回符合 OpenAI function calling    │
        # │         格式的字典                           │
        # │                                              │
        # │ 目标输出格式:                                │
        # │   {                                         │
        # │     "type": "function",                     │
        # │     "function": {                           │
        # │       "name": ...,                          │
        # │       "description": ...,                   │
        # │       "parameters": {                       │
        # │         "type": "object",                   │
        # │         "properties": ...,  # self.parameters│
        # │         "required": ...,     # self.required │
        # │       }                                     │
        # │     }                                       │
        # │   }                                         │
        # └─────────────────────────────────────────────┘
        return {
            "type": "function",  
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required
                }
            }
        }


# ═══════════════════════════════════════════════════════════════
# 第二部分：build_tool() 工厂
# 思考：为什么不直接 Tool(...)，要包一层 build_tool(...)？
# 提示：看 Claude Code 源码 src/Tool.ts 第 783 行
# ═══════════════════════════════════════════════════════════════

def build_tool(**kwargs) -> Tool:
    """
    工厂函数。目前一行代码，但它是一个"语义锚点"。
    未来所有工具的统一预处理（日志、默认值注入、监控）都加在这里。

    Python 提示:
      **kwargs 在参数位置 = "把所有 key=value 打包成 dict"
      **kwargs 在调用位置 = "把 dict 展开成 key=value"
      所以 build_tool(name="x", ...) → kwargs={"name":"x", ...}
      然后 Tool(**kwargs) → Tool(name="x", ...)
    """
    # ┌─────────────────────────────────────────────┐
    # │ TODO 7: 把 kwargs 展开传给 Tool 构造函数    │
    # │          并返回创建的 Tool 对象              │
    # │                                              │
    # │ 提示: 就一行 return Tool(???)                │
    # └─────────────────────────────────────────────┘
    return Tool(**kwargs)


# ═══════════════════════════════════════════════════════════════
# 第三部分：ToolRegistry — 用字典 dispatch 替代 if/elif
#
# 这是本章最核心的抽象。
# hello_agent.py 的 execute_tool() 用 if/elif 硬编码 4 个工具，
# 加到 60 个工具时会变成一屏又一屏的 if/elif。
# Registry 用一个 dict 解决问题：
#   self._tools[name] → Tool 对象 → 校验 → 执行
# ═══════════════════════════════════════════════════════════════

class ToolRegistry:
    """工具注册表——O(1) 字典查找替代 O(n) if/elif 链"""

    def __init__(self):
        # ┌─────────────────────────────────────────────┐
        # │ TODO 8: 初始化一个空字典存放工具            │
        # │         提示: self._tools: dict[str, Tool] = {} │
        # └─────────────────────────────────────────────┘
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        """注册一个工具到字典中，key=工具名, value=Tool 对象"""
        # ┌─────────────────────────────────────────────┐
        # │ TODO 9: 把 tool 存入 self._tools 字典       │
        # │         提示: self._tools[tool.name] = tool │
        # └─────────────────────────────────────────────┘
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """获取工具，不存在返回 None"""
        # ┌─────────────────────────────────────────────┐
        # │ TODO 10: 从字典取工具                       │
        # │          提示: dict.get(key) 不存在返回 None │
        # └─────────────────────────────────────────────┘
        # 已知key存在，就可以用self._tools[name]，否则用get
        return self._tools.get(name)

    def all_openai_schemas(self) -> list[dict]:
        """返回所有工具的 OpenAI schema 列表，用于传给 API"""
        # ┌─────────────────────────────────────────────┐
        # │ TODO 11: 遍历所有工具，调用 to_openai_schema() │
        # │                                              │
        # │ 提示: 列表推导式                             │
        # │   [tool.to_openai_schema()                   │
        # │    for tool in self._tools.values()]         │
        # └─────────────────────────────────────────────┘
        # 这段代码很有java味= =
        # results = []
        # for tool in self._tools.values():
        #     result = tool.to_openai_schema()
        #     results.append(result)
        # return results
        return [tool.to_openai_schema() for tool in self._tools.values()]

    # ── 核心：dispatch —— 替代 if/elif 的关键 ──

    def dispatch(self, name: str, input_data: dict) -> tuple[str | None, str]:
        """
        分发工具调用。三步走:
          ① 查找工具 → ② 校验输入 → ③ 执行

        返回: (error, result)
              正常: (None, "执行结果")
              错误: ("错误信息", "")
        """
        # ┌─────────────────────────────────────────────┐
        # │ TODO 12: 实现三步 dispatch                  │
        # │                                              │
        # │ 伪代码:                                      │
        # │   tool = self.get(name)                     │
        # │   if tool is None:                          │
        # │       返回 ("未知工具", "")                  │
        # │                                              │
        # │   error = tool.validate(input_data)         │
        # │   if error:                                 │
        # │       返回 (error, "")                       │
        # │                                              │
        # │   try:                                      │
        # │       result = tool.call(input_data)        │
        # │       返回 (None, result)                    │
        # │   except Exception as e:                    │
        # │       返回 (f"执行错误: {e}", "")            │
        # │                                              │
        # │ 对比 hello_agent.py 的 execute_tool():      │
        # │   if/elif 4 个分支 → 这里 0 个分支          │
        # │   加新工具: 改 3 处 → 这里 register() 就行  │
        # └─────────────────────────────────────────────┘
        tool = self._tools.get(name)
        if tool is None:
            return ("未知工具", "")
        error = tool.validate(input_data)
        if error is not None:
            return (error, "")  
        try:
            result = tool.call(input_data)
            return (None, result)
        except Exception as e:
            return (f"handle error: {e}", "")


# ═══════════════════════════════════════════════════════════════
# 第四部分：你自己定义两个工具
# ═══════════════════════════════════════════════════════════════

# TODO 13: 用 build_tool() 定义一个 "get_weather" 工具
#   参数: city (string, 必填)
#   行为: 返回模拟天气字符串，如 f"{city}天气: 晴, 25°C"
#   标记: is_read_only=True
weather_tool = build_tool(
      name="get_weather",
      description="获取指定城市的天气",
      parameters={
          "city": {"type": "string", "description": "城市名称"},
      },
      required=["city"],
      handler=lambda args: f"{args['city']}北京天气: 晴, 25°C",
      is_read_only=True
  )

# TODO 14: 用 build_tool() 定义一个 "translate" 工具
#   参数: text (string, 必填), target_lang (string, 非必填, 默认中文)
#   行为: 返回模拟翻译结果，如 f"'{text}' 翻译为{target_lang}: [模拟翻译]"
#   标记: is_read_only=True
translate_tool = build_tool(
    name="translate",
    description="翻译下面语句为英文",
    parameters={
          "text": {"type": "string", "description": "要翻译的语句"},
    },
    required=["text"],
    handler=lambda args: f"{args['text']}翻译完了，it's English",
    is_read_only=True
)

# ═══════════════════════════════════════════════════════════════
# 测试：运行后看到 "✅ 全部测试通过" 说明实现正确
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    passed = 0
    failed = 0

    def check(name, condition):
        global passed, failed
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name} — 检查你的实现")

    # ── 测试 Tool 类 ──
    print("=" * 50)
    print("测试 Tool 类")

    t = Tool(
        name="test_tool",
        description="测试工具",
        parameters={"x": {"type": "integer"}},
        handler=lambda args: f"结果: {args['x'] * 2}",
        required=["x"],
    )

    check("Tool.__init__ 存 name", t.name == "test_tool")
    check("Tool.__init__ 存 required", t.required == ["x"])

    check("validate 通过", t.validate({"x": 5}) is None)
    check("validate 拒绝缺参数", t.validate({}) is not None)
    check("validate 拒绝空值", t.validate({"x": None}) is not None)

    check("call 执行 handler", t.call({"x": 5}) == "结果: 10")

    schema = t.to_openai_schema()
    check("to_openai_schema type", schema.get("type") == "function")
    check("to_openai_schema name", schema["function"]["name"] == "test_tool")
    check("to_openai_schema required", "required" in schema["function"]["parameters"])
    check("is_read_only 默认 False", t.is_read_only() is False)
    check("is_destructive 默认 False", t.is_destructive() is False)

    t2 = Tool("ro", "只读工具", {}, lambda a: "ok", is_read_only=True)
    check("is_read_only 覆盖为 True", t2.is_read_only() is True)

    print(f"\n  Tool: {passed}/{passed + failed} 通过")

    # ── 测试 build_tool ──
    print("\n" + "=" * 50)
    print("测试 build_tool")

    bt = build_tool(name="factory_test", description="工厂测试", parameters={}, handler=lambda a: "ok")
    check("build_tool 创建 Tool", isinstance(bt, Tool))
    check("build_tool 传递 name", bt.name == "factory_test")

    print(f"\n  build_tool: {passed}/{passed + failed} 通过 (累计)")

    # ── 测试 ToolRegistry ──
    print("\n" + "=" * 50)
    print("测试 ToolRegistry")

    r = ToolRegistry()
    r.register(t)
    r.register(t2)

    check("register + get", r.get("test_tool") is t)
    check("get 不存在的工具返回 None", r.get("no_such_tool") is None)

    schemas = r.all_openai_schemas()
    check("all_openai_schemas 数量", len(schemas) == 2)

    err, result = r.dispatch("test_tool", {"x": 10})
    check("dispatch 正常执行", err is None and result == "结果: 20")

    err, result = r.dispatch("test_tool", {})
    check("dispatch 校验失败", err is not None and result == "")

    err, result = r.dispatch("does_not_exist", {})
    check("dispatch 未知工具", err is not None)

    print(f"\n  Registry: {passed}/{passed + failed} 通过 (累计)")

    # ── 测试你自己定义的工具是否注册了 ──
    print("\n" + "=" * 50)
    print("测试自定义工具（在 r 上注册你的 get_weather 和 translate）")

    # 如果你还没写 TODO 13/14，这两行会报 NameError
    try:
        r.register(weather_tool)
        w = r.get("get_weather")
        if w:
            check("get_weather 已注册", True)
            result = w.call({"city": "北京"})
            check("get_weather 可调用", "北京" in result and "25" in result)
        else:
            check("get_weather 已注册", False)
    except NameError:
        print("  ⏭️  跳过: weather_tool 尚未定义 (TODO 13)")

    try:
        r.register(translate_tool)
        tr = r.get("translate")
        if tr:
            check("translate 已注册", True)
            # 测试必填+非必填参数
            result_default = tr.call({"text": "hello"})
            check("translate 可调用(默认lang)", "hello" in result_default)
        else:
            check("translate 已注册", False)
    except NameError:
        print("  ⏭️  跳过: translate_tool 尚未定义 (TODO 14)")

    # ── 结果 ──
    print("\n" + "=" * 50)
    if failed == 0:
        print("✅ 全部测试通过！你已经实现了一个工具系统。")
        print()
        print("回顾一下你学到了什么:")
        print("  1. Tool 对象 = 定义 + 校验 + 执行，一包搞定")
        print("  2. Registry.dispatch() = 用字典替代 if/elif")
        print("  3. build_tool() = 工厂模式 + fail-closed 默认值")
        print("  4. to_openai_schema() = 工具定义和 API 格式解耦")
        print()
        print("下一步: 打开 agent_v2.py，看这个 Registry 如何在 Agent 循环里使用。")
    else:
        print(f"⚠️  {failed} 个测试未通过，继续修改，或查看 tool_system.py 参考答案。")
