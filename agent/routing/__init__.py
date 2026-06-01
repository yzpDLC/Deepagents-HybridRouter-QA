"""
路由层入口：规则引擎 + BERT 分类器 → 仲裁 → 最终意图
"""

from agent.routing.rule_engine import RuleEngine
from agent.routing.bert_classifier import BertIntentClassifier
from agent.routing.arbiter import Arbiter
from agent.routing.context_buffer import ContextBuffer

_rule_engine = RuleEngine()
_bert_classifier = BertIntentClassifier()
_arbiter = Arbiter()
_context_buffer = ContextBuffer()


def route(query: str, thread_id: str | None = None) -> dict:
    """两路并行路由 → 仲裁 → 返回最终意图

    Returns:
        dict: {"intent": str, "confidence": float, "source": str,
               "rule_result": dict, "bert_result": dict,
               "rule_detail": str, "bert_detail": str}
    """
    # 1. 获取多轮上下文
    history = _context_buffer.get_formatted(thread_id)

    # 2. 规则引擎（并行）
    rule_result = _rule_engine.match(query, history)

    # 3. BERT 分类器（并行）
    bert_result = _bert_classifier.predict(query, history)

    # 4. 仲裁
    final_intent, final_confidence = _arbiter.route(rule_result, bert_result)

    # 5. 更新上下文
    _context_buffer.update(thread_id, query, final_intent)

    return {
        "intent": final_intent,
        "confidence": final_confidence,
        "source": _arbiter.last_source,
        "rule_result": rule_result,
        "bert_result": bert_result,
        "rule_detail": f"{rule_result['intent']}({rule_result['confidence']:.2f}) - {rule_result.get('match_detail', '')}",
        "bert_detail": f"{bert_result['intent']}({bert_result['confidence']:.2f})",
    }


def reset_context(thread_id: str | None = None):
    """清空指定会话的上下文"""
    _context_buffer.clear(thread_id)
