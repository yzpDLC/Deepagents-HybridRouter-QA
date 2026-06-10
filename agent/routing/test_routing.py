"""
路由层测试脚本
测试三类意图（NEO4J_QUERY / WEB_QUERY / CHITCHAT）的规则引擎 + BERT 分类效果
在终端中运行: python -m agent.routing.test_routing
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from agent.routing import route

# 测试统计
_total = 0
_passed = 0
_failed = 0


def test_route(query: str, expected_intent: str = None):
    """测试单条 query 的路由结果"""
    global _total, _passed, _failed
    _total += 1

    try:
        result = route(query)
    except Exception as e:
        print(f"  [ERR] route() 抛出异常: {e}")
        _failed += 1
        return result

    intent = result["intent"]
    confidence = result["confidence"]
    source = result["source"]

    ok = expected_intent is None or intent == expected_intent
    mark = "[OK]" if ok else "[FAIL]"
    status = f" (期望={expected_intent})" if expected_intent else ""

    if ok:
        _passed += 1
    else:
        _failed += 1

    print(f"  {mark} [{source:15s}] {intent:12s} conf={confidence:.2f}{status}")
    print(f"      规则: {result['rule_detail']}")
    print(f"      BERT: {result['bert_detail']}")
    return result


def main():
    print("=" * 60)
    print("路由层测试——三类意图分类效果")
    print("=" * 60)

    # ========== 1. NEO4J_QUERY：企业知识库查询 ==========
    print("\n1. NEO4J_QUERY（企业知识库查询）")
    test_route("公司的请假流程是什么", "NEO4J_QUERY")
    test_route("考勤制度有哪些规定", "NEO4J_QUERY")
    test_route("绩效考核怎么评的", "NEO4J_QUERY")
    test_route("项目立项需要什么材料", "NEO4J_QUERY")
    test_route("保密制度的要求是什么", "NEO4J_QUERY")
    test_route("网络安全制度有哪些", "NEO4J_QUERY")
    test_route("报销流程怎么走", "NEO4J_QUERY")
    test_route("年假有多少天", "NEO4J_QUERY")
    test_route("人力部的职责是什么", "NEO4J_QUERY")

    # ========== 2. WEB_QUERY：网络搜索 ==========
    print("\n2. WEB_QUERY（网络实时搜索）")
    test_route("今天有什么新闻", "WEB_QUERY")
    test_route("搜索一下最近的热点", "WEB_QUERY")
    test_route("帮我查一下今天的天气", "WEB_QUERY")
    test_route("最新的人工智能新闻", "WEB_QUERY")
    test_route("帮我搜索一下行业动态", "WEB_QUERY")
    test_route("今天股市行情怎么样", "WEB_QUERY")

    # ========== 3. CHITCHAT：闲聊 ==========
    print("\n3. CHITCHAT（闲聊）")
    test_route("你好", "CHITCHAT")
    test_route("谢谢", "CHITCHAT")
    test_route("你是谁", "CHITCHAT")
    test_route("再见", "CHITCHAT")
    test_route("好的", "CHITCHAT")
    test_route("哈哈", "CHITCHAT")

    # ========== 4. 多轮上下文历史测试 ==========
    print("\n4. 多轮历史上下文测试")
    print("  第1轮: 请假流程是什么")
    r1 = route("请假流程是什么", thread_id="test_session_memory")
    print(f"  → {r1['intent']} (conf={r1['confidence']:.2f})")
    print("  第2轮: 那需要审批吗（应保持 NEO4J_QUERY）")
    r2 = route("那需要审批吗", thread_id="test_session_memory")
    print(f"  → {r2['intent']} (conf={r2['confidence']:.2f})")
    print("  第3轮: 谢谢你（应切为 CHITCHAT）")
    r3 = route("谢谢你", thread_id="test_session_memory")
    print(f"  → {r3['intent']} (conf={r3['confidence']:.2f})")

    # ========== 5. 边界模糊测试 ==========
    print("\n5. 边界模糊测试（无明确意图的 query）")
    test_route("为什么叫这个名字", None)  # 可能被归为 CHITCHAT 或 NEO4J
    test_route("什么意思", None)
    test_route("你觉得呢", None)

    # ========== 6. 统计结果 ==========
    print("\n" + "=" * 60)
    print(f"测试总计: {_total} 条")
    print(f"通过: {_passed} 条 ({_passed/_total*100:.0f}%)")
    print(f"失败: {_failed} 条")
    print("=" * 60)

    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
