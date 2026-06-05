"""
语义分块模块
参考 nano-graphrag _splitter.py 的分隔符切分思路，
根据企业制度文档的章节结构定制分割策略，替代微软 GraphRAG 默认的纯 token 硬切分。

核心思路：
1. 按 "第X章"、"第X条"、"第X节" 等章节标题为一级分隔符
2. 按连续空行为二级分隔符
3. 将切出来的短段合并到不超过 max_chunk_chars 的大块
4. 保证每个数据块语义完整，不切断章节内容


"""

import re
import sys
from typing import Any


def chunk_by_corporate_structure(
    text: str,
    doc_id: str = "doc_0",
    max_chunk_chars: int = 1500,
    min_chunk_chars: int = 50,
) -> list[dict[str, Any]]:
    """
    按企业文档章节结构进行语义分块

    Args:
        text: 文档全文
        doc_id: 文档标识
        max_chunk_chars: 单块最大字符数，默认 1500
        min_chunk_chars: 单块最小字符数，低于此值会尝试合并到前一块

    Returns:
        list[dict]: 分块结果列表
            - content: 文本内容
            - doc_id: 文档标识
            - chunk_index: 块序号
            - token_estimate: 预估 token 数
    """
    # ========== 第一步：按章节分隔符切分为原始段 ==========
    # 分隔符优先级：章节标题 > 条款标题 > 空行
    separators = [
        (r"(?:\n|^)第[一二三四五六七八九十百千零]+[章节编]\s*[^\n]*", "chapter"),   # "第一章 总则"
        (r"(?:\n|^)第[一二三四五六七八九十百千零]+[条]\s*[^\n]*", "article"),      # "第一条 为了..."
        (r"\n[-=‾]{5,}\n", "separator_line"),                                         # 分隔线
    ]

    # 先用正则把所有分隔符位置找出来
    raw_segments = []
    last_end = 0

    # 收集所有匹配位置
    matches = []
    for pattern, tag in separators:
        for m in re.finditer(pattern, text):
            matches.append((m.start(), m.end(), tag))

    # 按起始位置排序
    matches.sort(key=lambda x: x[0])

    # 如果没有找到任何分隔符，直接按段落切分
    if not matches:
        raw_segments = [p.strip() for p in text.split("\n\n") if p.strip()]
    else:
        # 把文档开头到第一个分隔符之前的内容作为一个段
        first_start = matches[0][0]
        if first_start > 0:
            head = text[:first_start].strip()
            if head:
                raw_segments.append(head)

        # 按分隔符位置切分：保留分隔符（章节标题/条款标题）作为当前段的开头
        for i, (start, end, tag) in enumerate(matches):
            # 当前分隔符之前的内容
            if start > last_end:
                segment = text[last_end:start].strip()
                if segment:
                    raw_segments.append(segment)

            # 当前分隔符本身（章节标题/条款标题）作为一个段
            raw_segments.append(text[start:end].strip())

            last_end = end

        # 处理最后剩余部分
        if last_end < len(text):
            segment = text[last_end:].strip()
            if segment:
                raw_segments.append(segment)

    # ========== 第二步：将短段合并为语义完整的大块 ==========
    chunks = []
    current_chunk = ""

    for segment in raw_segments:
        if not segment:
            continue

        if not current_chunk:
            current_chunk = segment
        elif len(current_chunk) + len(segment) <= max_chunk_chars:
            current_chunk += "\n" + segment
        else:
            # 当前块已满，开启新块
            if len(current_chunk) >= min_chunk_chars:
                chunks.append(current_chunk)
            else:
                # 当前块太短，继续拼接
                current_chunk += "\n" + segment
                continue
            current_chunk = segment

    # 收尾
    if current_chunk and len(current_chunk) >= min_chunk_chars:
        chunks.append(current_chunk)
    elif current_chunk and chunks:
        # 最后一段太短，合并到前一块
        chunks[-1] += "\n" + current_chunk

    # ========== 第三步：格式化输出 ==========
    result = []
    for i, chunk in enumerate(chunks):
        rough_token_count = max(1, len(chunk) // 2)  # 中文约 2 字符/token
        result.append({
            "content": chunk.strip(),
            "doc_id": doc_id,
            "chunk_index": i,
            "token_estimate": rough_token_count,
        })

    return result


if __name__ == "__main__":
    # 测试
    sys.stdout.reconfigure(encoding="utf-8")
    sample_text = """企业员工手册

第一章 总则

第一条 为了规范公司员工行为，维护公司正常的工作秩序，根据国家相关法律法规，制定本手册。

第二条 本手册适用于公司全体在职员工。

第三条 员工应遵守国家法律法规，遵守公司各项规章制度。

第二章 考勤制度

第四条 公司实行每周五天工作制，工作时间为周一至周五上午9:00至12:00，下午13:00至18:00。

第五条 员工应按时上下班，不得迟到、早退。

第三章 休假制度

第六条 员工连续工作满一年的，享受带薪年休假。
"""

    chunks = chunk_by_corporate_structure(sample_text, doc_id="employee_handbook")
    print(f"共 {len(chunks)} 个数据块\n")
    for c in chunks:
        print(f"--- Chunk {c['chunk_index']} (~{c['token_estimate']} tokens) ---")
        print(c["content"][:1200])
        print()
