"""
多轮对话上下文管理
为每个会话维护最近 N 轮的 query 和 intent，用于 BERT 分类器的历史感知
"""

from collections import deque


class ContextBuffer:
    """线程安全的上下文缓冲区（内存级，重启后丢失）"""

    def __init__(self, max_turns: int = 3):
        self._max_turns = max_turns
        self._store: dict[str, deque] = {}  # thread_id -> deque of (query, intent)

    def update(self, thread_id: str | None, query: str, intent: str):
        """记录一轮对话的 query 和路由结果"""
        tid = thread_id or "_default_"
        if tid not in self._store:
            self._store[tid] = deque(maxlen=self._max_turns)
        self._store[tid].append((query, intent))

    def get_raw(self, thread_id: str | None) -> list[tuple[str, str]]:
        """获取原始历史列表 [(query, intent), ...]"""
        tid = thread_id or "_default_"
        if tid not in self._store:
            return []
        return list(self._store[tid])

    def get_formatted(self, thread_id: str | None) -> str:
        """获取格式化后的历史文本，供 BERT 输入使用

        格式:
        [历史]query:地震时怎么办 intent:NEO4J_QUERY
        [历史]query:那预警呢 intent:NEO4J_QUERY
        """
        history = self.get_raw(thread_id)
        if not history:
            return ""
        lines = []
        for q, i in history:
            lines.append(f"[历史]query:{q} intent:{i}")
        return "\n".join(lines)

    def clear(self, thread_id: str | None = None):
        """清空上下文

        Args:
            thread_id: 指定会话。None 表示清空所有。
        """
        if thread_id is None:
            self._store.clear()
        else:
            self._store.pop(thread_id, None)

    @property
    def active_sessions(self) -> list[str]:
        return list(self._store.keys())
