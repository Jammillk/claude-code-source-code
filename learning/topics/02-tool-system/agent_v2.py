"""
agent_v2.py — 用 ToolRegistry 重写的 Agent 循环

对比 hello_agent.py (Topic 01):
  之前: if/elif 硬编码工具分发
  现在: ToolRegistry.dispatch() 自动分发

对应 Claude Code 源码:
  src/query.ts  + src/Tool.ts + src/tools.ts 三者的关系

运行:
  python agent_v2.py
"""

import json, os, sys, datetime, re
from openai import OpenAI

# 把 tool_system.py 加入 path
sys.path.insert(0, os.path.dirname(__file__))
from tool_system import build_tool, ToolRegistry


# ── 0. 配置 ──
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
    if not os.path.exists(config_path):
        print("❌ 未找到 config.json"); exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()
client = OpenAI(
    api_key=CONFIG["api_key"],
    base_url=CONFIG.get("base_url", "https://api.deepseek.com"),
)

# ── 1. 定义 + 注册工具 (一个工具一个对象) ──

registry = ToolRegistry()

registry.register(build_tool(
    name="get_current_time",
    description="获取当前系统时间",
    parameters={"timezone": {"type": "string", "description": "时区"}},
    handler=lambda a: f"当前时间: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
    is_read_only=True,
    is_concurrency_safe=True,
))

registry.register(build_tool(
    name="calculate",
    description="执行数学计算",
    parameters={"expression": {"type": "string", "description": "数学表达式"}},
    required=["expression"],
    handler=lambda a: (
        f"计算结果: {a['expression']} = {eval(a['expression'])}"
        if re.match(r"^[\d\s+\-*/().]+$", a["expression"])
        else f"错误: 非法表达式"
    ),
    is_read_only=True,
    is_concurrency_safe=True,
))

registry.register(build_tool(
    name="read_file",
    description="读取文件内容",
    parameters={"path": {"type": "string", "description": "文件路径"}},
    required=["path"],
    handler=lambda a: (
        open(a["path"], encoding="utf-8").read()[:2000]
        if os.path.exists(a["path"]) else f"文件不存在: {a['path']}"
    ),
    is_read_only=True,
))


# ── 2. Agent 循环 (核心不变，工具分发交给 registry) ──

def run_agent(user_prompt: str, max_turns: int = 10):
    messages = [
        {"role": "system", "content": "你是一个有用的助手。使用中文回答。"},
        {"role": "user", "content": user_prompt},
    ]

    registry.describe()
    print(f"\n{'='*60}")
    print(f"📝 用户: {user_prompt}")
    print(f"{'='*60}")

    for turn in range(max_turns):
        response = client.chat.completions.create(
            model=CONFIG.get("model", "deepseek-chat"),
            max_tokens=CONFIG.get("max_tokens", 2048),
            messages=messages,
            tools=registry.all_openai_schemas(),  # ← 自动生成工具列表
        )

        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        print(f"\n  [第 {turn} 轮] 模型状态: {finish_reason}")

        if msg.content:
            print(f"  🤖 AI: {msg.content}")

        if finish_reason == "tool_calls":
            messages.append(msg.model_dump(exclude_none=True))

            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)

                print(f"  🔧 调工具: {name}({json.dumps(args, ensure_ascii=False)})")

                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                # ← 关键变化: 不再用 if/elif 硬编码分发！
                #   registry.dispatch() 自动找到对应工具执行
                # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                err, result = registry.dispatch(name, args)
                if err:
                    result = f"工具调用失败: {err}"

                print(f"  📋 结果: {result[:200]}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        elif finish_reason == "stop":
            break
        else:
            print(f"  ⚠️ 意外状态: {finish_reason}")
            break
    else:
        print(f"\n  ⚠️ 达到最大轮次 ({max_turns})")

    print(f"{'='*60}")
    print("✅ 会话结束")


# ── 3. 运行 ──
if __name__ == "__main__":
    run_agent("现在几点了？然后帮我算一下 456 * 789 是多少。")
