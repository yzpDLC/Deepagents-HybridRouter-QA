"""系统指令层——构建意图路由、安全限制等 system message"""


def build_system_message(
    intent: str,
    intent_desc: str,
    confidence: float,
) -> list[str]:
    """构建系统指令列表

    Args:
        intent: 意图名称
        intent_desc: 意图中文描述
        confidence: 置信度

    Returns:
        list[str]: 系统指令字符串列表，每条对应一个 system message
    """
    system_message = []

    # 意图路由指令
    system_message.append(
        f"外部意图分析结果:\n"
        f"意图: {intent}\n"
        f"意图描述: {intent_desc}\n"
        f"置信度: {confidence:.2f}\n\n"
        f"请根据以上意图分类，将用户问题转发给对应的子Agent执行。"
    )

    # 未来可扩展：安全限制、角色定义等
    # parts.append("【安全限制】不得回答敏感信息...")

    return system_message
