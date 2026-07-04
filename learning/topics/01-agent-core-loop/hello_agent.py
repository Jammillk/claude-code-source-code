"""
hello_agent.py — 最小化 AI Agent 的 "Hello World"

这个脚本实现了 Claude Code 最核心的 Agent 循环模式:

    User → messages[] → API → response
      ├─ finish_reason == "tool_calls"? → execute tools → append → loop
      └─ finish_reason != "tool_calls"  → return

学习目标:
  1. 理解 Agent 循环的本质：while-true + tool dispatch
  2. 理解 tool definition 如何影响模型行为
  3. 理解 messages[] 如何充当 Agent 的"记忆"

运行前:
  1. 复制 config.template.json → config.json
  2. 在 config.json 中填入你的 DeepSeek API Key
  3. 运行: python hello_agent.py
"""

import json
import os
from openai import OpenAI

# ──────────────────────────────────────────────────────────────
# 0. 读取配置
# ──────────────────────────────────────────────────────────────

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    if not os.path.exists(config_path):
        print("❌ 未找到 config.json，请按以下步骤操作：")
        print("   1. 复制 config.template.json → config.json")
        print("   2. 在 config.json 中填入你的 DeepSeek API Key")
        exit(1)
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

CONFIG = load_config()

# ──────────────────────────────────────────────────────────────
# 1. 工具定义 — 这是 Agent 的"手"
#    OpenAI 格式: 每个工具包在 {"type": "function", "function": {...}} 里
# ──────────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前系统时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "时区，默认 Asia/Shanghai"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算，支持 +、-、*、/",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如 '2 + 3 * 4'"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取文件内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要读取的文件路径"
                    }
                },
                "required": ["path"]
            }
        }
    }
]

# ──────────────────────────────────────────────────────────────
# 2. 工具执行 — 把 tool_call 变成 tool_result
# ──────────────────────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """工具分发——对应 Claude Code 中 Tool.call() 的简化版"""
    import datetime

    if tool_name == "get_current_time":
        tz = tool_input.get("timezone", "Asia/Shanghai")
        now = datetime.datetime.now()
        return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"

    elif tool_name == "calculate":
        expr = tool_input["expression"]
        try:
            import re
            if not re.match(r'^[\d\s+\-*/().]+$', expr):
                return f"错误: 表达式包含不允许的字符: {expr}"
            result = eval(expr)
            return f"计算结果: {expr} = {result}"
        except Exception as e:
            return f"计算错误: {e}"

    elif tool_name == "read_file":
        path = tool_input["path"]
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"文件内容 ({path}):\n{content[:2000]}"
        except FileNotFoundError:
            return f"错误: 文件不存在: {path}"
        except Exception as e:
            return f"读取错误: {e}"

    return f"未知工具: {tool_name}"


# ──────────────────────────────────────────────────────────────
# 3. Agent 核心循环 — 阅读这段代码，理解每一步的作用
# ──────────────────────────────────────────────────────────────

def run_agent(user_prompt: str, max_turns: int = 10):
    """
    Agent 主循环 — 对应 Claude Code 的 src/query.ts

    这就是整个 Agent 框架最核心的部分。
    Claude Code 在此基础上加了 50 万行生产代码。
    """

    client = OpenAI(
        api_key=CONFIG["api_key"],
        base_url=CONFIG.get("base_url", "https://api.deepseek.com"),
    )

    # Agent 的"记忆" — 对应 query.ts 中的 messages[]
    # 初始包含 system prompt 和用户输入
    messages = [
        {
            "role": "system",
            "content": "你是一个有用的助手。你可以使用工具来回答问题。回答使用中文。"
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    print(f"🤖 Agent 启动 (模型: {CONFIG.get('model', 'deepseek-chat')})")
    print(f"📝 用户: {user_prompt}")
    print("-" * 50)

    for turn in range(max_turns):
        # ── Step A: 发送请求 ──
        response = client.chat.completions.create(
            model=CONFIG.get("model", "deepseek-chat"),
            max_tokens=CONFIG.get("max_tokens", 2048),
            messages=messages,
            tools=TOOLS,
        )

        choice = response.choices[0]
        msg = choice.message
        finish_reason = choice.finish_reason
        print(f"  [turn={turn}] finish_reason={finish_reason}")

        # ── Step B: 处理文本输出 ──
        if msg.content:
            print(f"🤖 Agent: {msg.content}")

        # ── Step C: 处理工具调用 ──
        if finish_reason == "tool_calls":
            # 将 assistant 消息追加到 messages[]（包含 tool_calls）
            messages.append(msg.model_dump(exclude_none=True))

            # 逐个执行工具，结果追加到 messages[]
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                tool_input = json.loads(tc.function.arguments)

                print(f"🔧 调用工具: {tool_name}({json.dumps(tool_input, ensure_ascii=False)})")

                result = execute_tool(tool_name, tool_input)
                print(f"📋 工具结果: {result[:200]}")

                # 每个工具结果是一条独立的 tool 消息
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            # ── 循环回到 Step A，让模型处理 tool 结果 ──

        elif finish_reason == "stop":
            break  # 模型完成回答

        else:
            print(f"  ⚠️ 未知 finish_reason: {finish_reason}, 停止")
            break

    else:
        print(f"⚠️  达到最大轮次 ({max_turns})，Agent 停止")

    print("-" * 50)
    print("✅ Agent 会话结束")


# ──────────────────────────────────────────────────────────────
# 4. 运行
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_agent("现在几点了？然后帮我算一下 123 * 456 是多少。")
