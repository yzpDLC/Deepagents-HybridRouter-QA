"""
规则引擎：关键词 + 正则匹配
无模型调用，零延迟，完全可控
"""

import re
from dataclasses import dataclass

# ==========================================
# 关键词表（优先级从高到低）
# ==========================================

# NEO4J_QUERY：企业知识库相关
NEO4J_KEYWORDS = {
    # 核心文档类
    "制度", "流程", "规范", "方案", "指南", "办法", "规定", "条款", "标准",
    "手册", "模板", "文档", "文件", "资料", "政策", "规则", "细则",
    # 管理职能
    "请假", "考勤", "薪酬", "绩效", "福利", "报销", "预算", "审批",
    "申请", "考核", "培训", "入职", "离职", "转正", "调岗",
    # 项目与技术
    "项目", "需求", "架构", "设计", "开发", "测试", "上线",
    "运维", "部署", "迭代", "版本", "发布",
    # 组织与安全
    "部门", "岗位", "职责", "权限", "组织", "架构",
    "保密", "安全", "合规", "审计", "风险", "内控",
}

# WEB_QUERY：实时信息/新闻相关
WEB_KEYWORDS = {
    # 时效性触发词
    "今天", "昨天", "明天", "最新", "近期", "近日", "当前",
    "本月", "本周", "今年", "去年",
    "现在", "此刻", "实时",
    # 新闻触发词
    "新闻", "报道", "快讯", "消息", "通报", "公告", "通知",
    "动态", "进展", "最新消息", "最新进展",
    "路况", "天气", "交通",
    # 搜索意图
    "搜索", "搜一下", "查一下", "查查", "查询",

}

# 正则模式
NEO4J_PATTERNS = [
    r"什么[是叫].*[制度流程规范指南]",
    r"[如何怎么怎样].*[制度流程规范]",
    r".*[制度流程规范].*[内容要求]",
    r"[哪哪儿].*[制度流程规范]",
]

WEB_PATTERNS = [
    r"最新.*新闻",
    r".*最新.*消息",
    r"今天.*[新闻动态]",
    r"\d{4}年.*[新闻动态]",
]



def keyword_match(query: str) -> tuple[str, float, str]:
    """关键词精确匹配

    Returns:
        (intent, confidence, matched_keyword)
    """
    q = query.strip()

    # 检查 NEO4J_QUERY
    matched_neo4j = []
    for kw in NEO4J_KEYWORDS:
        if kw in q:
            matched_neo4j.append(kw)

    # 检查 WEB_QUERY
    matched_web = []
    for kw in WEB_KEYWORDS:
        if kw in q:
            matched_web.append(kw)

    # 取匹配数多的
    if len(matched_neo4j) > len(matched_web):
        confidence = min(0.95, 0.65 + len(matched_neo4j) * 0.05)
        return ("NEO4J_QUERY", confidence, f"关键词匹配: {matched_neo4j[:3]}")
    elif len(matched_web) > len(matched_neo4j):
        confidence = min(0.90, 0.60 + len(matched_web) * 0.05)
        return ("WEB_QUERY", confidence, f"关键词匹配: {matched_web[:3]}")
    elif len(matched_neo4j) > 0 and len(matched_web) > 0:
        # 数量相等时，NEO4J 优先（知识库优先于联网搜索）
        return ("NEO4J_QUERY", 0.55, f"关键词冲突,取NEO4J: {matched_neo4j[:2]} vs {matched_web[:2]}")

    return ("", 0.0, "")


def regex_match(query: str) -> tuple[str, float, str]:
    """正则模式匹配"""
    for pattern in NEO4J_PATTERNS:
        if re.search(pattern, query):
            return ("NEO4J_QUERY", 0.80, f"正则匹配: /{pattern}/")
    for pattern in WEB_PATTERNS:
        if re.search(pattern, query):
            return ("WEB_QUERY", 0.75, f"正则匹配: /{pattern}/")
    return ("", 0.0, "")


def _merge_results(
    kw_intent: str, kw_conf: float, kw_detail: str,
    re_intent: str, re_conf: float, re_detail: str,
) -> tuple[str, float, str]:
    """合并关键词和正则的结果：取高置信度"""
    candidates = []
    if kw_conf > 0:
        candidates.append((kw_intent, kw_conf, kw_detail))
    if re_conf > 0:
        candidates.append((re_intent, re_conf, re_detail))
    if not candidates:
        return ("", 0.0, "无匹配")
    # 取最高置信度
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0]


class RuleEngine:
    """规则引擎：关键词 + 正则匹配"""

    def match(self, query: str, history_context: str = "") -> dict:
        """执行规则匹配

        Args:
            query: 当前用户输入
            history_context: 历史上下文（目前未用于规则引擎，保留接口一致性）

        Returns:
            dict: {"intent": str, "confidence": float, "match_detail": str, "matched": bool}
        """
        kw_intent, kw_conf, kw_detail = keyword_match(query)
        re_intent, re_conf, re_detail = regex_match(query)

        intent, confidence, detail = _merge_results(
            kw_intent, kw_conf, kw_detail,
            re_intent, re_conf, re_detail,
        )

        return {
            "intent": intent,
            "confidence": confidence,
            "match_detail": detail,
            "matched": confidence > 0,
        }
