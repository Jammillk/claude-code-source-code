"""
hello_agent.py — 最小化 AI Agent 的 "Hello World"

这个脚本实现了 Claude Code 最核心的 Agent 循环模式:

    User → messages[] → API → response
      ├─ stop_reason == "tool_use"? → execute → append → loop
      └─ stop_reason != "tool_use"  → return

学习目标:
  1. 理解 Agent 循环的本质：while-true + tool dispatch
  2. 理解 tool definition 如何影响模型行为
  3. 理解 messages[] 如何充当 Agent 的"记忆"

运行:
  pip install anthropic
  set ANTHROPIC_API_KEY=your-key
  python hello_agent.py
"""

import os
import json
from anthropic import Anthropic

# ──────────────────────────────────────────────────────────────
# 1. 工具定义 — 这是 Agent 的"手"
# ──────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "get_current_time",
        "description": "获取当前系统时间",
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "时区，默认 Asia/Shanghai"
                }
            },
            "required": []
        }
    },
    {
        "name": "calculate",
        "description": "执行数学计算，支持 +、-、*、/",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '2 + 3 * 4'"
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "read_file",
        "description": "读取文件内容",
        "input_schema": {
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
]

# ──────────────────────────────────────────────────────────────
# 2. 工具执行 — 把 tool_use 变成 tool_result
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
            # 安全计算：只允许数字和基本运算符
            import re
            if not re.match(r'^[\d\s+\-*/().]+$', expr):
                return f"错误: 表达式包含不允许的字符: {expr}"
            result = eval(expr)  # 生产环境应使用安全的 parser
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

    这就是整个 Agent 框架最核心的部分，只有约 30 行。
    Claude Code 在此基础上加了 50 万行生产代码。
    """

    client = Anthropic()
    messages = []  # <-- Agent 的"记忆"，对应 query.ts 中的 messages[]

    print(f"🤖 Agent 启动")
    print(f"📝 用户: {user_prompt}")
    print("-" * 50)

    for turn in range(max_turns):
        # ── Step A: 发送请求 ──
        # 对应 Claude Code 中 fetchSystemPromptParts() + API call
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system="你是一个有用的助手。你可以使用工具来回答问题。回答使用中文。",
            tools=TOOLS,
            messages=messages + [{"role": "user", "content": user_prompt}]
            if turn == 0 else messages,
        )

        # ── Step B: 处理响应 ──
        for block in response.content:
            if block.type == "text":
                print(f"🤖 Agent: {block.text}")

            elif block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                tool_id = block.id

                print(f"🔧 调用工具: {tool_name}({json.dumps(tool_input, ensure_ascii=False)})")

                # 执行工具 — 对应 Claude Code 的 tool.call()
                result = execute_tool(tool_name, tool_input)
                print(f"📋 工具结果: {result[:200]}")

                # 追加到消息历史 — 这是 Agent 记忆的关键
                messages.append({
                    "role": "assistant",
                    "content": [block.model_dump()]
                })
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result,
                    }]
                })

        # ── Step C: 检查是否继续 ──
        # 对应 query.ts 中检查 stop_reason
        if response.stop_reason != "tool_use":
            break

    else:
        print(f"⚠️  达到最大轮次 ({max_turns})，Agent 停止")

    print("-" * 50)
    print("✅ Agent 会话结束")


# ──────────────────────────────────────────────────────────────
# 4. 运行
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 你可以修改这个 prompt 来测试不同的场景
    run_agent("现在几点了？然后帮我算一下 123 * 456 是多少。")
