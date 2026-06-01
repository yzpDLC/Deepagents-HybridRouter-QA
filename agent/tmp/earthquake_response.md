# 地震知识图谱查询说明

## 当前状态

由于系统未配置完整的 GraphRAG 地震知识图谱索引环境，无法直接执行知识图谱查询。

## 可用资源

### Neo4j Query Skill
- 位置：`/skills/neo4j_query/`
- 功能：提供 GraphRAG+Neo4j 地震知识图谱查询能力
- 主要函数：`graphrag_earthquake_search()`
- 支持参数：
  - `query`: 查询问题（必填）
  - `community_level`: 社区响应精细度 1-5（可选，默认 2）
  - `response_type`: 回答格式（Multiple Paragraphs/Single Paragraph/Single Sentence，可选）

### 已实现的功能
- GraphRAG 本地搜索 API 集成
- 知识图谱多粒度检索（基于 community_level）
- 结构化结果返回
- 批量查询支持

## 需要完成的工作

### 1. 建立 GraphRAG 索引
```bash
# 在项目根目录执行
cd /earthquake_agent/graphrag
python -m graphrag.index --root . --input-type glob --input-path ./data
```

### 2. 配置环境变量
```bash
export GRAPHRAG_ROOT=/path/to/graphrag
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=your_password
```

### 3. Agent 技能注册
需要在 `deep_agent.py`中添加 neo4j_query skill:

```python
subagents = [web_search_subagent, neo4j_subagent]

deep_agent = create_deep_agent(
    model=chat_model,
    skills=["./skills/skill-creator", "./skills/neo4j_query"],  # 添加此技能
    backend=backend,
    system_prompt=load_prompt("intent_recognition"),
    subagents=subagents,
)
```

## 预期输出格式

成功查询后的标准输出格式：

```markdown
## 地震知识图谱查询结果

### 核心回答
[GraphRAG 返回的专业回答]

### 查询信息
- 查询问题：[用户问题]
- 社区等级：[community_level]
- 响应格式：[response_type]
- 数据来源：GraphRAG+Neo4j 地震知识图谱
```

## 典型应用场景

| 用户问题 | 推荐参数 | 预期内容 |
|---------|---------|---------|
| 地震时如何自救 | community_level=2 | 通用自救知识 |
| 学校地震演练流程 | community_level=3 | 具体演练步骤 |
| 地震预警系统原理 | community_level=2 | 技术原理解析 |
| 某地区抗震措施对比 | batch_search | 多地区对比分析 |

## 知识边界说明

当前知识图谱包含：
- ✅ 地震安全基础知识
- ✅ 应急演练规范
- ✅ 预警系统科普
- ✅ 应急物资储备指南
- ❌ 实时地震新闻
- ❌ 特定个人/地点的详细记录（需补充文档后索引）

---
*本系统依赖 GraphRAG 构建的地震领域专业知识图谱，所有回答均来源于本地索引数据，确保信息的准确性和可靠性*
