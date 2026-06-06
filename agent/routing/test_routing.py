"""
路由层测试脚本
在终端中运行: python -m agent.routing.test_routing
"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from agent.routing import route, reset_context


def test_route(query: str, expected_intent: str = None):
    try:
        result = route(query)
    except Exception as e:
        print(f"  [ERR] route() failed: {e}")
        return {"intent": "ERROR", "confidence": 0.0, "source": "error"}
    intent = result["intent"]
    confidence = result["confidence"]
    source = result["source"]
    ok = expected_intent is None or intent == expected_intent
    mark = "[OK]" if ok else "[FAIL]"
    status = f" (期望={expected_intent})" if expected_intent else ""
    print(f"  {mark} [{source:15s}] {intent:12s} conf={confidence:.2f}{status}")
    print(f"      规则: {result['rule_detail']}")
    print(f"      BERT: {result['bert_detail']}")
    return result


def main():
    print("=" * 60)
    print("路由层测试")
    print("=" * 60)

    print("\n1. NEO4J_QUERY 测试")
    test_route("地震时应该怎么做？", "NEO4J_QUERY")
    test_route("什么是地震预警系统", "NEO4J_QUERY")
    test_route("汶川地震的基本信息", "NEO4J_QUERY")
    test_route("地震应急演练有哪些内容", "NEO4J_QUERY")
    test_route("地震的成因是什么", "NEO4J_QUERY")
    test_route("震级和烈度有什么区别", "NEO4J_QUERY")
    test_route("地震时在室内应该躲在哪里", "NEO4J_QUERY")
    test_route("天津地震应急演练指南要求了什么", "NEO4J_QUERY")

    print("\n2. WEB_QUERY 测试")
    test_route("今天的最新新闻", "WEB_QUERY")
    test_route("今天天气怎么样", "WEB_QUERY")
    test_route("最近有什么热点新闻", "WEB_QUERY")
    test_route("帮我搜索一下网络信息", "WEB_QUERY")

    print("\n3. 多轮上下文测试")
    print("  第1轮: 地震预警是什么")
    r1 = route("地震预警是什么", thread_id="test_session")
    print(f"  → {r1['intent']}")
    print("  第2轮: 它的工作原理呢")
    r2 = route("它的工作原理呢", thread_id="test_session")
    print(f"  → {r2['intent']}")
    print(f"  上下文: {r2['rule_detail']}")

    print("\n4. 边界情况测试")
    test_route("你好", "CHITCHAT")  # 日常问候，走闲聊
    test_route("今天天气真不错", None)
    test_route("帮我查一下", None)

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
