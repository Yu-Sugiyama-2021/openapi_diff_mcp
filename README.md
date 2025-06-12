# OpenAPI 差分解析ツール

OpenAPI 仕様書の差分を解析し、APIの変更内容を詳細に分析するMCPサーバーです。Git リポジトリ内のOpenAPI YAML仕様の変更を追跡し、エンドポイントやスキーマの追加・削除・変更を検出します。

## 📋 機能概要

- **Git変更差分の解析**: ステージングされた変更とHEADの間のOpenAPI仕様の差分を検出
- **スキーマ影響分析**: 特定のスキーマが使用されているAPIエンドポイントを特定
- **MCPインターフェース**: Model Context Protocolを使用した対話型インターフェース

## 🚀 使い方

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/Yu-Sugiyama-2021/openapi_diff_mcp.git
cd openapi_diff_mcp

# 依存関係のインストール
pip install -r requirements.txt
```

### mcp設定

### mcp設定

```json
{
    "mcp": {
        "servers": {
            "openapi_diff": {
                "command": "<paste $which fastmcp>",
                "args": [
                    "run",
                    "<path-to-project>\\main.py"
                ]
            }
        }
    }
}
```

MCP設定のパスは環境に合わせて適宜変更してください。
```

### ツール

#### 1. Git差分の解析

Gitリポジトリのステージング状態とHEADの間でOpenAPI YAMLファイルを比較します。

```
analyze_staged_git_diff(repo_path: str, yaml_path: str)
```

- `repo_path`: Gitリポジトリのパス
- `yaml_path`: リポジトリ内のYAMLファイルのパス

#### 2. スキーマ利用箇所の検索

特定のスキーマが使用されているAPIエンドポイントを検索します。

```
find_schema_usages(repo_path: str, yaml_path: str, schema_name: str)
```

- `repo_path`: Gitリポジトリのパス
- `yaml_path`: リポジトリ内のYAMLファイルのパス
- `schema_name`: 検索対象のスキーマ名

## 🧰 技術スタック

- **Python**: 実装言語
- **fastMcp**: Model Context Protocolインターフェース
- **pyyaml**: YAML解析
- **gitpython**: Git操作

## 📁 プロジェクト構成

```
openapi_diff/
├── main.py           # MCPサーバーのエントリーポイント
├── requirements.txt  # 依存ライブラリ
├── run_tests.py      # テスト実行スクリプト
└── tools/            # 内部処理ロジック
    ├── __init__.py
    ├── analyzer.py   # OpenAPI仕様の分析ロジック
    └── differ.py     # 差分検出ロジック
```

## ⚙️ 設定

特別な設定は必要ありません。依存ライブラリをインストールするだけで利用できます。

## 📝 ライセンス

Copyright © 2025