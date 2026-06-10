"""
BERT 分类器独立测试脚本
绕过规则引擎和仲裁器，直接看 BERT 对每条 query 的预测结果和概率分布
运行: python -m agent.routing.train.test_bert
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from agent.routing.bert_classifier import BertIntentClassifier, ID2LABEL


def main():
    classifier = BertIntentClassifier()

    if not classifier._ready:
        classifier._lazy_init()

    if not classifier._ready:
        print("BERT 模型未加载，请先训练")
        return

    # 直接从模型获取概率分布的方法（需要稍微修改原代码，这里用 predict 但额外显示分布）
    print("=" * 60)
    print("BERT 分类器独立测试")
    print("=" * 60)

    test_cases = {
        "NEO4J_QUERY": [
            "公司的请假流程是什么",
            "考勤制度有哪些规定",
            "绩效考核怎么评的",
            "项目立项需要什么材料",
            "保密制度的要求是什么",
            "报销流程怎么走",
            "年假有多少天",
            "人力部的职责是什么",
            "加班怎么申请",
            "员工手册在哪里看",
        ],
        "WEB_QUERY": [
            "今天有什么新闻",
            "搜索一下最近的热点",
            "帮我查一下今天的天气",
            "最新的人工智能新闻",
            "帮我搜索一下行业动态",
            "今天股市行情",
            "查一下这个数据",
            "最近的政策法规",
        ],
        "CHITCHAT": [
            "你好",
            "谢谢",
            "你是谁",
            "再见",
            "好的",
            "哈哈",
            "在吗",
            "辛苦了",
            "拜拜",
            "为什么",
        ],
    }

    total = 0
    correct = 0

    for expected_intent, queries in test_cases.items():
        print(f"\n--- {expected_intent}（期望类别）---")
        for query in queries:
            total += 1
            result = classifier.predict(query)
            predicted = result["intent"]
            confidence = result["confidence"]
            ok = predicted == expected_intent
            if ok:
                correct += 1
            mark = "[OK]" if ok else "[x]"
            print(f"  {mark} 预测={predicted:12s} 置信={confidence:.4f}  |  {query}")

    # 总准确率
    print("\n" + "=" * 60)
    print(f"测试总计: {total} 条, 正确: {correct} 条")
    print(f"准确率: {correct/total*100:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    main()
