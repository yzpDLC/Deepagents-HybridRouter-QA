"""
仲裁器：合并规则引擎和 BERT 分类器的结果
当两者分歧时，根据置信度做决策
"""

import logging

logger = logging.getLogger(__name__)

# 置信度阈值
HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.60
LOW_CONFIDENCE_THRESHOLD = 0.40

# 默认兜底意图（企业内部知识库查询）
DEFAULT_INTENT = "NEO4J_QUERY"

# 仲裁结果来源标识
SOURCE_RULE = "rule_engine"
SOURCE_BERT = "bert_classifier"
SOURCE_ARBITER = "arbiter"


class Arbiter:
    """仲裁器

    仲裁矩阵：
    ┌──────────────────────────┬──────────────────────────┬──────────────────────┐
    │ 规则置信度                 │ BERT 置信度               │ 决策                  │
    ├──────────────────────────┼──────────────────────────┼──────────────────────┤
    │ > 0.85                   │ 任意                      │ 采纳规则              │
    │ 任意                      │ > 0.85                   │ 采纳 BERT            │
    │ 一致                      │ 一致                     │ 采纳（取高置信度）        │
    │ 分歧, 双方 > 0.6           │ 分歧, 双方 > 0.6         │ 采纳 BERT               │
    │ 分歧, 一方 > 0.6           │ 分歧, 一方 < 0.6         │ 采纳高置信度那方          │
    │ 双方 <= 0.6               │ 双方 <= 0.6              │ 默认 NEO4J_QUERY       │
    └──────────────────────────┴──────────────────────────┴──────────────────────┘
    """

    def __init__(self):
        self.last_source: str = ""

    def route(
        self,
        rule_result: dict,
        bert_result: dict,
    ) -> tuple[str, float]:
        """仲裁两路结果

        Args:
            rule_result: {"intent": str, "confidence": float, ...}
            bert_result: {"intent": str, "confidence": float, ...}

        Returns:
            (final_intent, final_confidence)
        """
        rule_intent = rule_result.get("intent", "")
        rule_conf = rule_result.get("confidence", 0.0)
        rule_matched = rule_result.get("matched", False)

        bert_intent = bert_result.get("intent", "")
        bert_conf = bert_result.get("confidence", 0.0)

        log_data = f"规则=[{rule_intent}({rule_conf:.2f})] BERT=[{bert_intent}({bert_conf:.2f})]"

        # 规则引擎高置信度 → 直接采纳
        if rule_matched and rule_conf >= HIGH_CONFIDENCE_THRESHOLD:
            self.last_source = SOURCE_RULE
            logger.info(f"仲裁: 采纳规则引擎(高置信度) {log_data}")
            return rule_intent, rule_conf

        # BERT 高置信度 → 直接采纳
        if bert_conf >= HIGH_CONFIDENCE_THRESHOLD:
            self.last_source = SOURCE_BERT
            logger.info(f"仲裁: 采纳 BERT(高置信度) {log_data}")
            return bert_intent, bert_conf

        # 两者一致 → 采纳（取高置信度）
        if rule_intent == bert_intent and rule_intent:
            final_conf = max(rule_conf, bert_conf)
            source = SOURCE_RULE if rule_conf >= bert_conf else SOURCE_BERT
            self.last_source = source
            logger.info(f"仲裁: 一致采纳 {log_data}")
            return rule_intent, final_conf

        # 分歧场景
        if rule_intent and bert_intent:
            # 规则引擎未匹配 → 采纳 BERT
            if not rule_matched:
                self.last_source = SOURCE_BERT
                logger.info(f"仲裁: 规则未匹配, 采纳 BERT {log_data}")
                return bert_intent, bert_conf

            # 双方都达到中等置信度 → 采纳 BERT（泛化能力更强）
            if rule_conf >= MEDIUM_CONFIDENCE_THRESHOLD and bert_conf >= MEDIUM_CONFIDENCE_THRESHOLD:
                self.last_source = SOURCE_BERT
                logger.info(f"仲裁: 分歧, 双方中等置信, 采纳 BERT {log_data}")
                return bert_intent, bert_conf

            # 一方高置信度一方低 → 采纳高的
            if rule_conf >= MEDIUM_CONFIDENCE_THRESHOLD and bert_conf < MEDIUM_CONFIDENCE_THRESHOLD:
                self.last_source = SOURCE_RULE
                logger.info(f"仲裁: 分歧, 规则置信更高 {log_data}")
                return rule_intent, rule_conf

            if bert_conf >= MEDIUM_CONFIDENCE_THRESHOLD and rule_conf < MEDIUM_CONFIDENCE_THRESHOLD:
                self.last_source = SOURCE_BERT
                logger.info(f"仲裁: 分歧, BERT 置信更高 {log_data}")
                return bert_intent, bert_conf

        # 双方都低置信度 → 默认兜底
        self.last_source = SOURCE_ARBITER
        fallback_conf = max(rule_conf, bert_conf, 0.3)
        logger.info(f"仲裁: 低置信度兜底 -> {DEFAULT_INTENT} {log_data}")
        return DEFAULT_INTENT, fallback_conf
