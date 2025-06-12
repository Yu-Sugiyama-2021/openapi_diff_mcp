#!/usr/bin/env python3
"""
OpenAPI YAML Analyzer MCP Server

このサーバーは、OpenAPI YAML仕様の差分を分析し、結果を返すMCPサーバーです。
Model Context Protocolを使用して、APIの変更を検出し、詳細な分析結果を提供します。
"""

import os
import sys
import json
from pathlib import Path
from fastmcp import FastMCP

# ツールディレクトリをインポートパスに追加
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# 自作ツールのインポート
from tools.differ import OpenAPIDiffer
from tools.analyzer import OpenAPIAnalyzer

# MCPアプリケーションの作成
app = FastMCP("OpenAPI YAML Analyzer 🔍")

@app.tool
def analyze_staged_git_diff(repo_path: str, yaml_path: str) -> dict:
    """
    Gitリポジトリのステージング状態とHEADの間でOpenAPI YAMLファイルを比較する
    
    Args:
        repo_path: Gitリポジトリのパス
        yaml_path: リポジトリ内のYAMLファイルのパス
        
    Returns:
        差分情報を含む辞書
    """
    try:
        # Gitリポジトリが存在することを確認
        if not os.path.exists(os.path.join(repo_path, ".git")):
            return {"error": f"Gitリポジトリが見つかりません: {repo_path}"}
        
        differ = OpenAPIDiffer()
        diff = differ.compare_staged_changes(
            git_repo_path=repo_path,
            yaml_path=yaml_path
        )
        return diff
    except Exception as e:
        return {"error": f"エラーが発生しました: {str(e)}"}

@app.tool
def find_schema_usages(repo_path: str, yaml_path: str, schema_name: str) -> dict:
    """
    特定のスキーマが使用されているAPIエンドポイントを検索する
    
    Args:
        repo_path: Gitリポジトリのパス
        yaml_path: リポジトリ内のYAMLファイルのパス
        schema_name: 検索対象のスキーマ名
        
    Returns:
        スキーマが使用されているAPIエンドポイントと詳細情報を含む辞書
    """
    try:
        # YAMLファイルのフルパスを構築
        full_yaml_path = os.path.join(repo_path, yaml_path)
        
        # YAMLファイルの内容を読み込む
        if not os.path.exists(full_yaml_path):
            return {"error": f"YAMLファイルが見つかりません: {full_yaml_path}"}
            
        with open(full_yaml_path, 'r', encoding='utf-8') as file:
            yaml_content = file.read()
        
        analyzer = OpenAPIAnalyzer()
        result = analyzer.analyze_schema_impact(yaml_content, schema_name)
        
        # 結果を見やすい形式に整形
        formatted_result = {
            "schema_name": schema_name,
            "yaml_path": yaml_path,
            "total_affected_endpoints": len(result["affected_endpoints"]),
            "affected_endpoints": result["affected_endpoints"],
            "usage_details": result["usage_details"]
        }
        
        return formatted_result
    except Exception as e:
        return {"error": f"エラーが発生しました: {str(e)}"}

def main():
    app.run()

if __name__ == "__main__":
    main()
