#!/usr/bin/env python3
"""
地震知识图谱查询工具 - 独立运行版本
直接调用 GraphRAG 进行地震安全知识查询
"""

import asyncio
import os
import sys
from typing import Literal, Dict, Any

# 添加脚本目录到路径
sys.path.insert(0, '/skills/neo4j_query/scripts')

import pandas as pd
from graphrag.api import local_search as api_local_search
from graphrag.config.load_config import load_config


def _get_graphrag_root() -> str:
    """获取 GraphRAG 项目根目录"""
    # 尝试从环境变量或默认路径获取
    env_path = os.environ.get('GRAPHRAG_ROOT', None)
    if env_path and os.path.exists(env_path):
        return env_path
    
    # 默认路径：当前目录下的 graphrag 子目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    default_path = os.path.join(current_dir, '../graphrag')
    
    if os.path.exists(default_path):
        return default_path
    
    # 其他可能路径
    alternative_paths = [
        '/graphrag',
        './graphrag',
        '/earthquake_agent/graphrag'
    ]
    
    for path in alternative_paths:
        if os.path.exists(path):
            return path
    
    raise FileNotFoundError("无法找到 GraphRAG 项目目录，请设置 GRAPHRAG_ROOT 环境变量或确保 graphrag 目录存在")


def graphrag_earthquake_search(
    query: str,
    community_level: int = 2,
    response_type: Literal["Multiple Paragraphs", "Single Paragraph", "Single Sentence"] = "Multiple Paragraphs"
) -> Dict[str, Any]:
    """
    基于 GraphRAG 的地震知识图谱查询工具
    
    Args:
        query: 查询问题字符串
        community_level: 社区响应精细度 (1-5)，默认 2
        response_type: 回答格式
        
    Returns:
        dict: 包含查询结果的字典
    """
    try:
        graphrag_root = _get_graphrag_root()
        
        # 验证必要文件存在
        settings_path = os.path.join(graphrag_root, "settings.yaml")
        output_path = os.path.join(graphrag_root, "output")
        
        if not os.path.exists(settings_path):
            return {
                "success": False,
                "query": query,
                "answer": "",
                "error": f"配置文件不存在：{settings_path}"
            }
        
        if not os.path.exists(output_path):
            return {
                "success": False,
                "query": query,
                "answer": "",
                "error": f"输出目录不存在：{output_path}，请先运行 graphrag index 构建索引"
            }
        
        # 加载配置
        config = load_config(graphrag_root)
        
        # 读取必要的 parquet 文件
        parquet_dir = os.path.join(output_path)
        
        required_files = [
            'entities.parquet',
            'communities.parquet',
            'community_reports.parquet',
            'text_units.parquet',
            'relationships.parquet'
        ]
        
        for file_name in required_files:
            file_path = os.path.join(parquet_dir, file_name)
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "query": query,
                    "answer": "",
                    "error": f"缺失索引文件：{file_path}"
                }
        
        entities_df = pd.read_parquet(os.path.join(parquet_dir, 'entities.parquet'))
        communities_df = pd.read_parquet(os.path.join(parquet_dir, 'communities.parquet'))
        community_reports_df = pd.read_parquet(os.path.join(parquet_dir, 'community_reports.parquet'))
        text_units_df = pd.read_parquet(os.path.join(parquet_dir, 'text_units.parquet'))
        relationships_df = pd.read_parquet(os.path.join(parquet_dir, 'relationships.parquet'))
        
        # covariates 是可选的
        covariates_df = None
        covariates_path = os.path.join(parquet_dir, 'covariates.parquet')
        if os.path.exists(covariates_path):
            covariates_df = pd.read_parquet(covariates_path)
        
        # 执行本地搜索
        result = asyncio.run(api_local_search(
            config=config,
            entities=entities_df,
            communities=communities_df,
            community_reports=community_reports_df,
            text_units=text_units_df,
            relationships=relationships_df,
            covariates=covariates_df,
            community_level=community_level,
            response_type=response_type,
            query=query,
        ))
        
        # 处理返回结果
        if isinstance(result, tuple):
            answer = result[0]
        else:
            answer = result
        
        return {
            "success": True,
            "query": query,
            "answer": answer,
            "metadata": {
                "community_level": community_level,
                "response_type": response_type,
                "source": "GraphRAG+Neo4j 地震知识图谱"
            }
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "query": query,
            "answer": "",
            "error": f"查询失败：{str(e)}\n\n详细错误:\n{traceback.format_exc()}"
        }


if __name__ == "__main__":
    import json
    
    print("=" * 60)
    print("地震知识图谱查询系统")
    print("=" * 60)
    
    # 测试查询
    test_query = "地震发生时需要注意些什么"
    
    print(f"\n🔍 查询问题：{test_query}")
    print("-" * 60)
    
    result = graphrag_earthquake_search(
        query=test_query,
        community_level=2,
        response_type="Multiple Paragraphs"
    )
    
    if result["success"]:
        print("\n✅ 查询成功!")
        print(f"\n核心回答:")
        print(result["answer"])
        print(f"\n查询信息:")
        print(f"- 社区等级：{result['metadata']['community_level']}")
        print(f"- 响应格式：{result['metadata']['response_type']}")
        print(f"- 数据来源：{result['metadata']['source']}")
    else:
        print(f"\n❌ 查询失败!")
        print(f"错误信息：{result['error']}")
