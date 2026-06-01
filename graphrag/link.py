import json

import pandas as pd
from neo4j import GraphDatabase

from config.settings import settings

URI = settings.neo4j_uri
USER = settings.neo4j_user
PASSWORD = settings.neo4j_password

print("=" * 60)
print("GraphRAG 完整数据导入 Neo4j（包含社区）")
print("=" * 60)


# 查找所有相关文件
def find_all_files():
    files = {}

    # 实体和关系
    if os.path.exists("output/extract_graph/entities.parquet"):
        files['entities'] = "output/extract_graph/entities.parquet"
    elif os.path.exists("output/entities.parquet"):
        files['entities'] = "output/entities.parquet"

    if os.path.exists("output/extract_graph/relationships.parquet"):
        files['relationships'] = "output/extract_graph/relationships.parquet"
    elif os.path.exists("output/relationships.parquet"):
        files['relationships'] = "output/relationships.parquet"

    # 社区数据（重要！）
    if os.path.exists("output/create_communities/communities.parquet"):
        files['communities'] = "output/create_communities/communities.parquet"
    elif os.path.exists("output/communities.parquet"):
        files['communities'] = "output/communities.parquet"

    # 社区报告（最重要！）
    if os.path.exists("output/create_community_reports/community_reports.parquet"):
        files['community_reports'] = "output/create_community_reports/community_reports.parquet"
    elif os.path.exists("output/community_reports.parquet"):
        files['community_reports'] = "output/community_reports.parquet"

    # 节点-社区映射
    if os.path.exists("output/create_communities/entity_communities.parquet"):
        files['entity_communities'] = "output/create_communities/entity_communities.parquet"
    elif os.path.exists("output/entity_communities.parquet"):
        files['entity_communities'] = "output/entity_communities.parquet"

    return files


files = find_all_files()

print("\n📁 找到的文件:")
for key, path in files.items():
    print(f"   ✅ {key}: {path}")

if 'entities' not in files or 'relationships' not in files:
    print("\n❌ 找不到实体或关系文件！")
    exit(1)

# 读取数据
print("\n📖 读取 parquet 文件...")
entities_df = pd.read_parquet(files['entities'])
relationships_df = pd.read_parquet(files['relationships'])

print(f"\n✅ 实体: {len(entities_df)} 个")
print(f"✅ 关系: {len(relationships_df)} 个")

if 'communities' in files:
    communities_df = pd.read_parquet(files['communities'])
    print(f"✅ 社区: {len(communities_df)} 个")

if 'community_reports' in files:
    reports_df = pd.read_parquet(files['community_reports'])
    print(f"✅ 社区报告: {len(reports_df)} 个")

if 'entity_communities' in files:
    entity_comm_df = pd.read_parquet(files['entity_communities'])
    print(f"✅ 实体-社区映射: {len(entity_comm_df)} 条")

# 显示数据结构
print("\n📋 数据结构:")
print(f"   实体列: {entities_df.columns.tolist()}")
print(f"   关系列: {relationships_df.columns.tolist()}")
if 'communities' in files:
    print(f"   社区列: {communities_df.columns.tolist()}")
if 'community_reports' in files:
    print(f"   社区报告列: {reports_df.columns.tolist()}")

# 连接到 Neo4j
print("\n🔌 连接到 Neo4j...")
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

with driver.session() as session:
    result = session.run("RETURN 'Connected!' AS message")
    print(f"✅ {result.single()['message']}")

# 询问是否清空旧数据
response = input("\n是否清空 Neo4j 中的旧数据？(y/N): ")
if response.lower() == 'y':
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        print("✅ 已清空现有数据")

# ==================== 1. 导入实体 ====================
print("\n" + "=" * 60)
print("1. 导入实体")
print("=" * 60)

with driver.session() as session:
    # 创建索引
    session.run("CREATE INDEX entity_id IF NOT EXISTS FOR (e:Entity) ON (e.id)")
    session.run("CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)")

    name_col = 'name' if 'name' in entities_df.columns else 'title'
    id_col = 'id' if 'id' in entities_df.columns else name_col
    type_col = 'type' if 'type' in entities_df.columns else 'entity_type'

    for idx, row in entities_df.iterrows():
        session.run("""
            CREATE (e:Entity {
                id: $id,
                name: $name,
                type: $type,
                description: $description,
                rank: $rank
            })
        """,
                    id=str(row[id_col]),
                    name=str(row[name_col]),
                    type=str(row[type_col]),
                    description=str(row.get('description', ''))[:500] if pd.notna(row.get('description')) else "",
                    rank=float(row.get('rank', 0)) if pd.notna(row.get('rank')) else 0)

        if idx < 5:
            print(f"   ✅ 实体: {row[name_col]} ({row[type_col]})")

    print(f"✅ 导入 {len(entities_df)} 个实体")

# ==================== 2. 导入关系 ====================
print("\n" + "=" * 60)
print("2. 导入关系")
print("=" * 60)

with driver.session() as session:
    success = 0
    for idx, row in relationships_df.iterrows():
        result = session.run("""
            MATCH (s:Entity {name: $source})
            MATCH (t:Entity {name: $target})
            CREATE (s)-[r:RELATED_TO {
                description: $description,
                weight: $weight
            }]->(t)
            RETURN s.name, t.name
        """,
                             source=str(row['source']),
                             target=str(row['target']),
                             description=str(row.get('description', ''))[:200] if pd.notna(
                                 row.get('description')) else "",
                             weight=float(row.get('weight', 1.0)) if pd.notna(row.get('weight')) else 1.0)

        if result.single():
            success += 1
            if idx < 5:
                print(f"   ✅ 关系: {row['source']} -> {row['target']}")

    print(f"✅ 导入 {success}/{len(relationships_df)} 个关系")

# ==================== 3. 导入社区（关键！）====================
if 'communities' in files:
    print("\n" + "=" * 60)
    print("3. 导入社区")
    print("=" * 60)

    with driver.session() as session:
        session.run("CREATE INDEX community_id IF NOT EXISTS FOR (c:Community) ON (c.community_id)")

        for idx, row in communities_df.iterrows():
            # 根据实际列名调整
            comm_id_col = 'community' if 'community' in communities_df.columns else 'id'
            level_col = 'level' if 'level' in communities_df.columns else 'hierarchy_level'

            community_id = str(row[comm_id_col])
            level = int(row[level_col]) if pd.notna(row.get(level_col)) else 0

            session.run("""
                CREATE (c:Community {
                    community_id: $community_id,
                    level: $level
                })
            """, community_id=community_id, level=level)

            if idx < 5:
                print(f"   ✅ 社区: ID={community_id}, Level={level}")

        print(f"✅ 导入 {len(communities_df)} 个社区")

# ==================== 4. 导入社区报告（最重要！）====================
if 'community_reports' in files:
    print("\n" + "=" * 60)
    print("4. 导入社区报告（查询时使用）")
    print("=" * 60)

    with driver.session() as session:
        for idx, row in reports_df.iterrows():
            # 根据实际列名调整
            comm_id_col = 'community' if 'community' in reports_df.columns else 'community_id'
            title_col = 'title' if 'title' in reports_df.columns else 'community_title'
            summary_col = 'summary' if 'summary' in reports_df.columns else 'full_content'

            community_id = str(row[comm_id_col])
            title = str(row.get(title_col, '')) if pd.notna(row.get(title_col)) else ""
            summary = str(row.get(summary_col, ''))[:2000] if pd.notna(row.get(summary_col)) else ""
            rank = float(row.get('rank', 0)) if pd.notna(row.get('rank')) else 0
            level = int(row.get('level', 0)) if pd.notna(row.get('level')) else 0

            # 合并到 Community 节点
            session.run("""
                MATCH (c:Community {community_id: $community_id})
                SET c.title = $title,
                    c.summary = $summary,
                    c.rank = $rank,
                    c.level = $level
            """, community_id=community_id, title=title,
                        summary=summary, rank=rank, level=level)

            if idx < 5:
                print(f"   ✅ 社区报告: ID={community_id}, Title={title[:50]}...")

        print(f"✅ 导入 {len(reports_df)} 个社区报告")

# ==================== 5. 连接实体到社区 ====================
print("\n" + "=" * 60)
print("5. 连接实体到社区")
print("=" * 60)

with driver.session() as session:
    success = 0

    # 方法1: 如果有专门的实体-社区映射文件
    if 'entity_communities' in files and 'entity_comm_df' in locals():
        print("   使用方法1: 从 entity_communities 文件读取...")
        for idx, row in entity_comm_df.iterrows():
            entity_id = str(row.get('entity_id', row.get('id', '')))
            community_id = str(row.get('community', row.get('community_id', '')))

            if entity_id and community_id:
                result = session.run("""
                    MATCH (e:Entity {id: $entity_id})
                    MATCH (c:Community {community_id: $community_id})
                    CREATE (e)-[:BELONGS_TO]->(c)
                    RETURN e.name
                """, entity_id=entity_id, community_id=community_id)

                if result.single():
                    success += 1

        print(f"   ✅ 从映射文件连接了 {success} 个实体到社区")

    # 方法2: 从 communities.parquet 的 entity_ids 列解析（主要方法）
    if 'communities' in files:
        print("   使用方法2: 从 communities.parquet 的 entity_ids 解析...")
        success2 = 0

        for idx, row in communities_df.iterrows():
            community_id = str(row['community'] if 'community' in communities_df.columns else row['id'])
            entity_ids = row.get('entity_ids', [])

            # 检查 entity_ids 是否为空（兼容各种类型）
            is_empty = False
            if entity_ids is None:
                is_empty = True
            elif hasattr(entity_ids, '__len__') and len(entity_ids) == 0:
                is_empty = True
            elif isinstance(entity_ids, (str, bytes)) and len(entity_ids) == 0:
                is_empty = True

            if is_empty and 'node_ids' in communities_df.columns:
                entity_ids = row.get('node_ids', [])

            # entity_ids 可能是字符串形式的列表，需要转换
            if isinstance(entity_ids, str):
                try:
                    import ast

                    entity_ids = ast.literal_eval(entity_ids)
                except:
                    entity_ids = []

            # 确保 entity_ids 是可迭代的列表（不判断真值，只判断类型）
            if isinstance(entity_ids, (str, bytes)):
                entity_ids = [entity_ids] if len(entity_ids) > 0 else []
            elif not hasattr(entity_ids, '__len__'):
                entity_ids = [entity_ids] if entity_ids is not None else []
            # 如果是 numpy 数组或其他序列类型，保持原样

            # 转换为列表以便遍历
            if hasattr(entity_ids, '__iter__') and not isinstance(entity_ids, str):
                entity_list = list(entity_ids) if hasattr(entity_ids, '__iter__') else []
            else:
                entity_list = [entity_ids] if entity_ids else []

            for entity_id in entity_list:
                if entity_id is not None and str(entity_id).strip():
                    try:
                        result = session.run("""
                            MATCH (e:Entity {id: $entity_id})
                            MATCH (c:Community {community_id: $community_id})
                            CREATE (e)-[:BELONGS_TO]->(c)
                            RETURN e.name
                        """, entity_id=str(entity_id), community_id=community_id)

                        if result.single():
                            success2 += 1
                    except Exception as e:
                        # 忽略单个连接错误，继续处理
                        pass

            if idx < 3:
                print(f"   ✅ 社区 {community_id}: 连接了 {len(entity_list)} 个实体")

        print(f"   ✅ 从 community 文件连接了 {success2} 个实体到社区")
        total_success = success + success2
    else:
        total_success = success

    print(f"✅ 共连接 {total_success} 个实体到社区")

# ==================== 验证导入结果 ====================
print("\n" + "=" * 60)
print("6. 验证导入结果")
print("=" * 60)

with driver.session() as session:
    # 统计
    result = session.run("""
        MATCH (n:Entity) RETURN count(n) as entity_count
    """)
    print(f"📊 实体节点: {result.single()['entity_count']}")

    result = session.run("""
        MATCH (c:Community) RETURN count(c) as community_count
    """)
    print(f"📊 社区节点: {result.single()['community_count']}")

    result = session.run("""
        MATCH ()-[r:RELATED_TO]->() RETURN count(r) as rel_count
    """)
    print(f"📊 关系: {result.single()['rel_count']}")

    result = session.run("""
        MATCH (e:Entity)-[:BELONGS_TO]->(c:Community) 
        RETURN count(*) as membership_count
    """)
    print(f"📊 实体-社区归属: {result.single()['membership_count']}")

    # 显示社区示例
    result = session.run("""
        MATCH (c:Community) 
        WHERE c.title IS NOT NULL
        RETURN c.community_id, c.level, c.title, c.summary
        LIMIT 5
    """)

    print("\n🏘️ 社区示例:")
    for record in result:
        print(f"   - 社区 {record['c.community_id']} (Level {record['c.level']})")
        print(f"     标题: {record['c.title'][:80] if record['c.title'] else 'N/A'}")
        print(f"     摘要: {record['c.summary'][:100] if record['c.summary'] else 'N/A'}...")

driver.close()

print("\n" + "=" * 60)
print("🎉 完整数据导入完成！")
print("=" * 60)
print("\n💡 在 Neo4j Browser 中运行查询:")
print("   MATCH (c:Community) RETURN c LIMIT 10")
print("   MATCH (e:Entity)-[:BELONGS_TO]->(c:Community) RETURN e, c LIMIT 25")