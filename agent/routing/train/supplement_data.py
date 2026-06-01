"""
补充训练数据：修正有歧义的标注 + 补充 WEB_QUERY 和 CREATE 到平衡分布
运行: python -m agent.routing.train.supplement_data
"""

import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "training_data.jsonl"

# ==========================================
# 需要修正的记录（index → new_intent）
# ==========================================
FIXES = {
    # "北京最近发生过地震吗？" → 需要实时数据，应走 WEB
    "北京最近发生过地震吗？": "WEB_QUERY",
    # "近期图书馆新进了哪些与地震相关的书籍？" → 需实时馆藏数据
    "近期图书馆新进了哪些与地震相关的书籍？": "WEB_QUERY",
}

# ==========================================
# 补充数据
# ==========================================

EXTRA_WEB_QUERIES = [
    # 纯搜索意图（不带地震词）
    "帮我查一下",
    "帮我搜索一下",
    "搜索一下",
    "上网查查",

    # 新闻/实时类
    "今天有什么新闻",
    "最近一周的新闻",
    "最新消息",

    # 地震相关但需要实时数据
    "台湾今天有地震吗",
    "日本最近地震情况",
    "今天哪里地震了",
    "最近全球地震活动情况",
    "查一下最近的地震",
    "最近有没有发生地震",
    "2025年全球大地震统计",
    "中国近期地震灾害报道",
]

EXTRA_CREATE_QUERIES = [
    # 技能/工具创建
    "帮我创建一个新技能",
    "帮我写一个自动化脚本",
    "帮我生成一个报告工具",
    "帮我开发一个小程序",

    # 地震领域专用
    "帮我创建一个地震知识问答机器人",
    "帮我写一个地震数据可视化工具",
    "帮我生成一个地震避险指南生成器",
    "帮我开发一个地震预警模拟程序",
    "帮我创建一个地震应急物资清单生成器",
    "帮我设计一个地震演练评估工具",
    "帮我编写一个地震知识卡片生成脚本",
]


def main():
    # 1. 读取全部现有数据
    records = []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"现有数据: {len(records)} 条")

    # 2. 统计修正前后的分布
    def count_by_intent(recs):
        counts = {}
        for r in recs:
            i = r["intent"]
            counts[i] = counts.get(i, 0) + 1
        return counts

    print(f"修正前分布: {count_by_intent(records)}")

    # 3. 修正有歧义的记录
    fixed = 0
    for rec in records:
        query = rec["query"]
        if query in FIXES:
            old = rec["intent"]
            rec["intent"] = FIXES[query]
            rec["source"] = rec["source"] + "_fixed"
            print(f"  修正: [{old}→{rec['intent']}] {query[:30]}...")
            fixed += 1

    # 4. 去重：避免补充的数据和现有数据重复
    existing_queries = {r["query"] for r in records}

    def add_queries(queries, intent):
        count = 0
        for q in queries:
            if q not in existing_queries:
                records.append({
                    "query": q,
                    "intent": intent,
                    "history_context": "",
                    "source": "manual_supplement",
                })
                existing_queries.add(q)
                count += 1
            else:
                print(f"  跳过重复: {q}")
        return count

    added_web = add_queries(EXTRA_WEB_QUERIES, "WEB_QUERY")
    added_create = add_queries(EXTRA_CREATE_QUERIES, "CREATE")

    # 5. 写回文件
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n修正: {fixed} 条")
    print(f"补充 WEB_QUERY: {added_web} 条")
    print(f"补充 CREATE: {added_create} 条")
    print(f"最终数据: {len(records)} 条")
    print(f"最终分布: {count_by_intent(records)}")


if __name__ == "__main__":
    main()
