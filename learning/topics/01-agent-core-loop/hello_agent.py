"""
hello_agent.py — 最小化 AI Agent 的 "Hello World"

这个脚本实现了 Claude Code 最核心的 Agent 循环模式:

    User → messages[] → API → response
      ├─ 模型要调工具? → 执行工具 → 结果追加到 messages[] → 循环
      └─ 模型回答完了   → 输出文本，结束

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

# ╔══════════════════════════════════════════════════════════════╗
# ║  🔑 API 对接点 ①：读取配置文件                                ║
# ║                                                              ║
# ║  你的 API Key 存在 learning/config.json 里                    ║
# ║  这个文件不会被 git 上传                                     ║
# ╚══════════════════════════════════════════════════════════════╝

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
    if not os.path.exists(config_path):
        print("❌ 未找到 config.json")
        print("   请: 复制 config.template.json → config.json，填入你的 API Key")
        exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()


# ╔══════════════════════════════════════════════════════════════╗
# ║  🔑 API 对接点 ②：创建客户端                                  ║
# ║                                                              ║
# ║  api_key  —— 从 config.json 读取，就是你申请的 sk-xxxx       ║
# ║  base_url —— DeepSeek 的 API 地址                            ║
# ║                                                              ║
# ║  这个 client 就是你和 AI 之间的"电话线"                       ║
# ╚══════════════════════════════════════════════════════════════╝

client = OpenAI(
    api_key=CONFIG["api_key"],
    base_url=CONFIG.get("base_url", "https://api.deepseek.com"),
)

print(f"📡 已连接: {CONFIG['base_url']}")
print(f"🧠 模型:   {CONFIG.get('model', 'deepseek-chat')}")


# ──────────────────────────────────────────────────────────────
# 1. 工具定义 — Agent 的"双手"，告诉模型它能做什么
#    OpenAI/DeepSeek 要求用 {"type":"function","function":{...}} 格式
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
                        "description": "时区，比如 Asia/Shanghai",
                    }
                },
            },
        },
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
                        "description": "数学表达式，如 '2 + 3 * 4'",
                    }
                },
                "required": ["expression"],
            },
        },
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
                        "description": "要读取的文件路径",
                    }
                },
                "required": ["path"],
            },
        },
    },
]


# ──────────────────────────────────────────────────────────────
# 2. 工具执行 — 模型说"我要调这个工具"，代码就执行它
# ──────────────────────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict) -> str:
    import datetime

    if tool_name == "get_current_time":
        tz = tool_input.get("timezone", "Asia/Shanghai")
        now = datetime.datetime.now()
        return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"

    elif tool_name == "calculate":
        expr = tool_input["expression"]
        try:
            import re
            if not re.match(r"^[\d\s+\-*/().]+$", expr):
                return f"错误: 非法表达式: {expr}"
            return f"计算结果: {expr} = {eval(expr)}"
        except Exception as e:
            return f"计算错误: {e}"

    elif tool_name == "read_file":
        path = tool_input["path"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"文件内容 ({path}):\n{content[:2000]}"
        except FileNotFoundError:
            return f"错误: 文件不存在: {path}"
        except Exception as e:
            return f"读取错误: {e}"

    return f"未知工具: {tool_name}"


# ╔══════════════════════════════════════════════════════════════╗
# ║                                                              ║
# ║  3. Agent 核心循环 —— 这就是整个 Agent 的"心脏"              ║
# ║                                                              ║
# ║  对应 Claude Code 源码中的 src/query.ts (785KB)              ║
# ║  这里只保留最核心的 ~30 行逻辑                                ║
# ║                                                              ║
# ╚══════════════════════════════════════════════════════════════╝

def run_agent(user_prompt: str, max_turns: int = 10):

    # messages[] — Agent 的"记忆"，所有对话历史都存在这里
    messages = [
        {"role": "system", "content": "你是一个有用的助手。使用中文回答。"},
        {"role": "user", "content": user_prompt},
    ]

    print(f"\n{'='*60}")
    print(f"📝 用户: {user_prompt}")
    print(f"{'='*60}")

    for turn in range(max_turns):
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 🔑 API 对接点 ③：真正发起调用！                    ║
        #                                                    ║
        #  把 messages[] (对话历史) + tools (可用工具)       ║
        #  一起发给 DeepSeek 服务器                          ║
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        response = client.chat.completions.create(
            model=CONFIG.get("model", "deepseek-chat"),
            max_tokens=CONFIG.get("max_tokens", 2048),
            messages=messages,
            tools=TOOLS,
        )

        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        print(f"\n  [第 {turn} 轮] 模型状态: {finish_reason}")

        # ── 情况 A：模型返回了文字，打印出来 ──
        if msg.content:
            print(f"  🤖 AI 回答: {msg.content}")

        # ── 情况 B：模型想调工具了 ──
        if finish_reason == "tool_calls":
            # 先把 assistant 整条消息记到 messages[] 里
            messages.append(msg.model_dump(exclude_none=True))

            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)

                print(f"  🔧 调工具: {name}({json.dumps(args, ensure_ascii=False)})")

                result = execute_tool(name, args)
                print(f"  📋 结果:   {result[:150]}")

                # 工具结果也追加到 messages[]，模型下一轮能看到
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
            # 继续循环，模型会根据工具结果再回答

        elif finish_reason == "stop":
            # 模型认为任务完成了
            break
        else:
            print(f"  ⚠️ 意外的状态: {finish_reason}")
            break

    else:
        print(f"\n  ⚠️ 达到最大轮次 ({max_turns})")

    print(f"{'='*60}")
    print("✅ 会话结束")
    print(f"  messages[] 共 {len(messages)} 条消息")


# ──────────────────────────────────────────────────────────────
# 4. 运行入口
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 👇 改这行 prompt 来测试不同的场景
    run_agent("现在几点了？然后帮我算一下 123 * 456 是多少。")
