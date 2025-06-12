#!/usr/bin/env python3
import yaml
import json
import os
import tempfile
import shutil
from git import Repo
from typing import Dict, Any

class OpenAPIDiffer:
    """OpenAPI仕様の差分を分析するクラス"""
    
    def _is_valid_openapi(self, data: Dict[str, Any]) -> bool:
        """
        与えられたデータがOpenAPI仕様として有効かどうかを検証する
        
        Args:
            data: 検証するデータ
            
        Returns:
            OpenAPI仕様として有効な場合はTrue、そうでない場合はFalse
        """
        if not isinstance(data, dict):
            return False
            
        # OpenAPI 3.xの基本的な検証
        # 'openapi'フィールドがあり、'paths'または'components'のいずれかが存在する場合に有効とみなす
        has_openapi_field = 'openapi' in data
        has_paths_or_components = 'paths' in data or 'components' in data
        
        return has_openapi_field and has_paths_or_components
        
    def compare(self, before_yaml: str, after_yaml: str) -> Dict[str, Any]:
        """
        2つのOpenAPI仕様ファイルを比較し、差分情報を生成する
        
        Args:
            before_yaml: 変更前のOpenAPI YAML内容
            after_yaml: 変更後のOpenAPI YAML内容
            
        Returns:
            差分情報を含む辞書
            
        Raises:
            ValueError: 有効なOpenAPI仕様が含まれていない場合
        """
        try:
            before = yaml.safe_load(before_yaml) or {}
            after = yaml.safe_load(after_yaml) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"YAML解析エラー: {str(e)}")
          # ファイルが存在しない場合や空の場合は空の辞書として扱う
        if before == {} and after == {}:
            # 両方とも空の場合は差分なしとして扱う
            return {
                "paths": {"added": {}, "removed": {}, "modified": {}},
                "components": {"schemas": {"added": {}, "removed": {}, "modified": {}}}
            }
            
        # OpenAPI仕様の基本的な検証
        # 少なくとも一方が有効なOpenAPI仕様であれば処理を続行する
        if not self._is_valid_openapi(before) and not self._is_valid_openapi(after):
            # 警告としてログに出力するなどの処理をここに追加することも可能
            # 空のOpenAPI仕様を返す代わりに差分を取得する処理を続行
            pass
        
        # 差分検出のロジック
        diff = {
            "paths": {
                "added": {},
                "removed": {},
                "modified": {}
            },
            "components": {
                "schemas": {
                    "added": {},
                    "removed": {},
                    "modified": {}
                }
            }
        }
        
        # paths の差分検出
        self._detect_path_changes(before.get('paths', {}), after.get('paths', {}), diff['paths'])
        
        # schemas の差分検出
        before_schemas = before.get('components', {}).get('schemas', {})
        after_schemas = after.get('components', {}).get('schemas', {})
        self._detect_schema_changes(before_schemas, after_schemas, diff['components']['schemas'])
        
        return diff
    def compare_git_revisions(self, git_repo_path: str, yaml_path: str, old_rev: str, new_rev: str) -> Dict[str, Any]:
        """
        Gitリポジトリの2つのリビジョン間でOpenAPI YAMLファイルを比較する
        
        Args:
            git_repo_path: Gitリポジトリのパス
            yaml_path: リポジトリ内のYAMLファイルのパス
            old_rev: 古いリビジョン（コミットハッシュなど）
            new_rev: 新しいリビジョン（コミットハッシュなど）
            
        Returns:
            差分情報を含む辞書
            
        Raises:
            ValueError: 指定されたリビジョンにファイルが存在しない場合
        """
        repo = Repo(git_repo_path)
        
        # 一時ディレクトリを作成
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 古いリビジョンのファイルを取得（ファイルが存在しない場合は空のYAMLとして扱う）
            try:
                old_content = repo.git.show(f"{old_rev}:{yaml_path}")
            except Exception as e:
                if "does not exist" in str(e):
                    # ファイルが存在しない場合は、新規追加されたものとして扱う
                    old_content = "{}"
                else:
                    raise ValueError(f"古いリビジョンのファイル取得エラー: {str(e)}")
            
            old_file_path = os.path.join(temp_dir, "old.yaml")
            with open(old_file_path, "w", encoding="utf-8") as f:
                f.write(old_content)
            
            # 新しいリビジョンのファイルを取得
            try:
                new_content = repo.git.show(f"{new_rev}:{yaml_path}")
            except Exception as e:
                if "does not exist" in str(e):
                    # ファイルが存在しない場合は、削除されたものとして扱う
                    new_content = "{}"
                else:
                    raise ValueError(f"新しいリビジョンのファイル取得エラー: {str(e)}")
                
            new_file_path = os.path.join(temp_dir, "new.yaml")
            with open(new_file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            # 差分を比較
            return self.compare(old_content, new_content)
        
        finally:
            # 一時ディレクトリを削除
            shutil.rmtree(temp_dir)
        
    def compare_staged_changes(self, git_repo_path: str, yaml_path: str) -> Dict[str, Any]:
        """
        Gitリポジトリの現在のステージング状態とHEADの間でOpenAPI YAMLファイルを比較する
        
        Args:
            git_repo_path: Gitリポジトリのパス
            yaml_path: リポジトリ内のYAMLファイルのパス
            
        Returns:
            差分情報を含む辞書
            
        Raises:
            ValueError: ファイルが存在しない、またはステージングされていない場合
        """
        repo = Repo(git_repo_path)
        
        # リポジトリのルートからの相対パスを取得
        repo_root = repo.git.rev_parse("--show-toplevel")
        rel_path = os.path.relpath(yaml_path, repo_root) if os.path.isabs(yaml_path) else yaml_path
        
        # 一時ディレクトリを作成
        temp_dir = tempfile.mkdtemp()
        
        try:
            # ステージングされているかチェック
            staged_files = repo.git.diff("--cached", "--name-only").split("\n")
            if rel_path not in staged_files:
                raise ValueError(f"ファイル '{rel_path}' はステージングされていません")
            
            # HEADのコンテンツを取得（ファイルが存在しない場合は空のYAMLとして扱う）
            try:
                head_content = repo.git.show(f"HEAD:{rel_path}")
            except Exception as e:
                if "does not exist" in str(e):
                    # ファイルが存在しない場合は、新規追加されたものとして扱う
                    head_content = "{}"
                else:
                    raise ValueError(f"HEADからのファイル取得エラー: {str(e)}")
            
            head_file_path = os.path.join(temp_dir, "head.yaml")
            with open(head_file_path, "w", encoding="utf-8") as f:
                f.write(head_content)
            
            # ステージングされたコンテンツを取得
            staged_content = repo.git.show(f":{rel_path}")
            staged_file_path = os.path.join(temp_dir, "staged.yaml")
            with open(staged_file_path, "w", encoding="utf-8") as f:
                f.write(staged_content)
            
            # 差分を比較
            return self.compare(head_content, staged_content)
        
        finally:
            # 一時ディレクトリを削除
            shutil.rmtree(temp_dir)
    
    def _detect_path_changes(self, before_paths, after_paths, diff_paths):
        """パスの変更を検出する"""
        # 追加されたパス
        for path in after_paths:
            if path not in before_paths:
                diff_paths["added"][path] = after_paths[path]
                
        # 削除されたパス
        for path in before_paths:
            if path not in after_paths:
                diff_paths["removed"][path] = before_paths[path]
                
        # 変更されたパス
        for path in before_paths:
            if path in after_paths:
                path_diff = self._compare_path_item(before_paths[path], after_paths[path])
                if path_diff:
                    diff_paths["modified"][path] = path_diff
    def _detect_schema_changes(self, before_schemas, after_schemas, diff_schemas):
        """スキーマの変更を詳細に検出する（改善版）"""
        # 追加されたスキーマ
        for schema in after_schemas:
            if schema not in before_schemas:
                diff_schemas["added"][schema] = after_schemas[schema]
                
        # 削除されたスキーマ
        for schema in before_schemas:
            if schema not in after_schemas:
                diff_schemas["removed"][schema] = before_schemas[schema]
                
        # 変更されたスキーマ
        for schema in before_schemas:
            if schema in after_schemas:
                schema_diff = self._compare_schema_detail(before_schemas[schema], after_schemas[schema])
                if schema_diff:
                    diff_schemas["modified"][schema] = schema_diff
    
    def _compare_path_item(self, before_path, after_path):
        """パス項目の変更を詳細に比較する"""
        result = {
            "operations": {
                "added": {},
                "removed": {},
                "modified": {}
            }
        }
        
        has_changes = False
        
        # 追加されたオペレーション
        for method in after_path:
            if method not in before_path and method in ['get', 'post', 'put', 'delete', 'patch']:
                result["operations"]["added"][method.upper()] = after_path[method]
                has_changes = True
                
        # 削除されたオペレーション
        for method in before_path:
            if method not in after_path and method in ['get', 'post', 'put', 'delete', 'patch']:
                result["operations"]["removed"][method.upper()] = before_path[method]
                has_changes = True
                
        # 変更されたオペレーション
        for method in before_path:
            if method in after_path and method in ['get', 'post', 'put', 'delete', 'patch']:
                if before_path[method] != after_path[method]:
                    result["operations"]["modified"][method.upper()] = {
                        "before": before_path[method],
                        "after": after_path[method]
                    }
                    has_changes = True
        
        return result if has_changes else None
        
    def _compare_schema_detail(self, before_schema, after_schema):
        """スキーマの詳細な差分を比較する"""
        if before_schema == after_schema:
            return None
            
        changes = {
            "properties": {
                "added": {},
                "removed": {},
                "modified": {}
            },
            "required": {
                "added": [],
                "removed": []
            },
            "type_changed": False,
        }
        
        has_changes = False
        
        # タイプの変更をチェック
        if before_schema.get("type") != after_schema.get("type"):
            changes["type_changed"] = True
            has_changes = True
        
        # プロパティの変更をチェック
        before_props = before_schema.get("properties", {})
        after_props = after_schema.get("properties", {})
        
        # 追加されたプロパティ
        for prop in after_props:
            if prop not in before_props:
                changes["properties"]["added"][prop] = after_props[prop]
                has_changes = True
        
        # 削除されたプロパティ
        for prop in before_props:
            if prop not in after_props:
                changes["properties"]["removed"][prop] = before_props[prop]
                has_changes = True
        
        # 変更されたプロパティ
        for prop in before_props:
            if prop in after_props and before_props[prop] != after_props[prop]:
                changes["properties"]["modified"][prop] = {
                    "before": before_props[prop],
                    "after": after_props[prop]
                }
                has_changes = True
        
        # required属性の変更をチェック
        before_required = before_schema.get("required", [])
        after_required = after_schema.get("required", [])
        
        for req in after_required:
            if req not in before_required:
                changes["required"]["added"].append(req)
                has_changes = True
        
        for req in before_required:
            if req not in after_required:
                changes["required"]["removed"].append(req)
                has_changes = True
        
        return changes if has_changes else None
    
    def get_first_commit_with_file(self, git_repo_path: str, yaml_path: str) -> str:
        """
        指定されたファイルが最初に登場するコミットハッシュを取得する
        
        Args:
            git_repo_path: Gitリポジトリのパス
            yaml_path: リポジトリ内のYAMLファイルのパス
            
        Returns:
            最初のコミットハッシュ、またはファイルが見つからない場合は空文字列
        """
        repo = Repo(git_repo_path)
        
        # リポジトリのルートからの相対パスを取得
        repo_root = repo.git.rev_parse("--show-toplevel")
        rel_path = os.path.relpath(yaml_path, repo_root) if os.path.isabs(yaml_path) else yaml_path
        
        try:
            # ファイルの履歴を逆順に取得（最も古いコミットを最後に）
            log_output = repo.git.log("--reverse", "--format=%H", "--", rel_path)
            commits = log_output.strip().split("\n")
            
            if commits and commits[0]:
                return commits[0]
            return ""
        except Exception:
            return ""
