#!/usr/bin/env python3
import yaml
import json
from typing import Dict, Any, List, Set

class OpenAPIAnalyzer:
    """OpenAPI仕様の分析を行うクラス"""
    
    def analyze_schema_impact(self, yaml_content: str, schema_name: str) -> Dict[str, Any]:
        """
        指定されたスキーマが影響するAPIエンドポイントを特定する
        
        Args:
            yaml_content: OpenAPI YAML内容
            schema_name: 分析対象のスキーマ名
            
        Returns:
            影響を受けるAPIエンドポイントと詳細情報を含む辞書
        """
        try:
            spec = yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError as e:
            return {"error": f"YAML解析エラー: {str(e)}"}        # 分析結果を格納する辞書
        result = {
            "schema_name": schema_name,
            "affected_endpoints": [],
            "usage_details": {
                "request_body": [],
                "response": [],
                "parameters": []
            }
        }
        
        # パスが存在しない場合は早期リターン
        if "paths" not in spec:
            return result
            
        paths = spec.get("paths", {})
        
        # 各パスとそのHTTPメソッドを調査
        for path, path_item in paths.items():
            for method, operation in path_item.items():                # HTTPメソッドのみを処理（$refなどの特殊キーは除外）
                if method not in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head', 'trace']:
                    continue
                    
                endpoint_affected = False
                usage_info = {
                    "path": path,
                    "method": method.upper(),
                    "operation_id": operation.get("operationId", ""),
                    "summary": operation.get("summary", ""),
                    "description": operation.get("description", ""),
                    "usage_locations": []
                }
                
                # リクエストボディでのスキーマ使用を確認
                if "requestBody" in operation:
                    request_body = operation["requestBody"]
                    content = request_body.get("content", {})
                    
                    for mime_type, mime_info in content.items():
                        schema_ref = self._get_schema_ref(mime_info.get("schema", {}))
                        
                        if schema_ref == schema_name or self._is_schema_used_in_object(mime_info.get("schema", {}), schema_name, spec, set()):
                            endpoint_affected = True
                            usage_info["usage_locations"].append("requestBody")
                            result["usage_details"]["request_body"].append({
                                "path": path,
                                "method": method.upper(),
                                "mime_type": mime_type,
                                "description": request_body.get("description", ""),
                                "summary": operation.get("summary", ""),
                                "operation_description": operation.get("description", "")
                            })
                
                # レスポンスでのスキーマ使用を確認
                if "responses" in operation:
                    responses = operation["responses"]
                    
                    for status_code, response in responses.items():
                        content = response.get("content", {})
                        
                        for mime_type, mime_info in content.items():
                            schema_ref = self._get_schema_ref(mime_info.get("schema", {}))
                            
                            if schema_ref == schema_name or self._is_schema_used_in_object(mime_info.get("schema", {}), schema_name, spec, set()):
                                endpoint_affected = True
                                usage_info["usage_locations"].append(f"response ({status_code})")
                                result["usage_details"]["response"].append({
                                    "path": path,
                                    "method": method.upper(),
                                    "status_code": status_code,
                                    "mime_type": mime_type,
                                    "description": response.get("description", ""),
                                    "summary": operation.get("summary", ""),
                                    "operation_description": operation.get("description", "")
                                })
                
                # パラメータでのスキーマ使用を確認
                parameters = operation.get("parameters", [])
                for param in parameters:
                    schema_ref = self._get_schema_ref(param.get("schema", {}))
                    
                    if schema_ref == schema_name or self._is_schema_used_in_object(param.get("schema", {}), schema_name, spec, set()):
                        endpoint_affected = True
                        usage_info["usage_locations"].append(f"parameter ({param.get('name', '')})")
                        result["usage_details"]["parameters"].append({
                            "path": path,
                            "method": method.upper(),
                            "parameter_name": param.get("name", ""),
                            "parameter_in": param.get("in", ""),
                            "description": param.get("description", ""),
                            "summary": operation.get("summary", ""),
                            "operation_description": operation.get("description", "")
                        })
                
                # このエンドポイントが影響を受ける場合、結果に追加
                if endpoint_affected:
                    result["affected_endpoints"].append(usage_info)
                    
        return result
    
    def analyze_diff_impact(self, yaml_content: str, diff: Dict[str, Any]) -> Dict[str, Any]:
        """
        差分情報に基づいて影響を受けるAPIエンドポイントを特定する
        
        Args:
            yaml_content: 最新のOpenAPI YAML内容
            diff: 差分情報を含む辞書
            
        Returns:
            影響を受けるAPIエンドポイントと詳細情報を含む辞書
        """
        # 変更されたスキーマを特定
        modified_schemas = diff.get("components", {}).get("schemas", {}).get("modified", {})
        added_schemas = diff.get("components", {}).get("schemas", {}).get("added", {})
        removed_schemas = diff.get("components", {}).get("schemas", {}).get("removed", {})
        
        result = {
            "modified_schemas": {},
            "added_schemas": {},
            "removed_schemas": {}
        }
        
        # 各変更されたスキーマについて影響分析を行う
        for schema_name in modified_schemas:
            schema_impact = self.analyze_schema_impact(yaml_content, schema_name)
            result["modified_schemas"][schema_name] = {
                "changes": modified_schemas[schema_name],
                "impact": schema_impact
            }
        
        # 各追加されたスキーマについて影響分析を行う
        for schema_name in added_schemas:
            schema_impact = self.analyze_schema_impact(yaml_content, schema_name)
            result["added_schemas"][schema_name] = {
                "schema": added_schemas[schema_name],
                "impact": schema_impact
            }
        
        # 各削除されたスキーマについては、現在のYAMLには存在しないため
        # 別の方法で影響を評価する必要がある
        # この実装では、削除されたスキーマの詳細情報のみを返す
        for schema_name in removed_schemas:            result["removed_schemas"][schema_name] = {
                "schema": removed_schemas[schema_name],
                "impact": {
                    "note": "削除されたスキーマのため、現在のAPIとの関連を直接分析できません。"
                }
            }
        
        return result
    
    def _get_schema_ref(self, schema: Dict[str, Any]) -> str:
        """
        スキーマオブジェクトから参照されているスキーマ名を取得する
        
        Args:
            schema: スキーマオブジェクト
            
        Returns:
            スキーマ名（参照がない場合は空文字列）
        """
        if "$ref" in schema:
            ref = schema["$ref"]
            # '#/components/schemas/SchemaName' 形式から 'SchemaName' を抽出
            if ref.startswith("#/components/schemas/"):
                return ref.split("/")[-1]
        return ""
    def _is_schema_used_in_object(self, schema: Dict[str, Any], target_schema: str, full_spec: Dict[str, Any], visited_refs: Set[str] = None) -> bool:
        """
        スキーマオブジェクト内で特定のスキーマが使用されているかを再帰的に確認する
        
        Args:
            schema: 調査対象のスキーマオブジェクト
            target_schema: 検索対象のスキーマ名
            full_spec: OpenAPI仕様全体
            visited_refs: すでに調査済みの参照スキーマ名のセット
            
        Returns:
            スキーマが使用されている場合はTrue、そうでない場合はFalse
        """
        # 訪問済みスキーマを追跡するセットの初期化
        if visited_refs is None:
            visited_refs = set()
            
        # 辞書以外のスキーマは処理しない
        if not isinstance(schema, dict):
            return False
            
        # 直接の参照をチェック
        schema_ref = self._get_schema_ref(schema)
        if schema_ref == target_schema:
            return True
            
        # スキーマがオブジェクトタイプの場合、プロパティを調査
        if schema.get("type") == "object" and "properties" in schema:
            for _, prop_schema in schema["properties"].items():
                if self._is_schema_used_in_object(prop_schema, target_schema, full_spec, visited_refs):
                    return True
        
        # スキーマが配列タイプの場合、items を調査
        if schema.get("type") == "array" and "items" in schema:
            if self._is_schema_used_in_object(schema["items"], target_schema, full_spec, visited_refs):
                return True
        
        # スキーマが$refを持つ場合、その参照先を再帰的に調査（循環参照防止）
        if schema_ref and schema_ref != target_schema:
            # 既に訪問済みのスキーマはスキップ
            if schema_ref in visited_refs:
                return False
                
            # 訪問済みとしてマーク
            visited_refs.add(schema_ref)
            
            ref_schema = full_spec.get("components", {}).get("schemas", {}).get(schema_ref, {})
            if ref_schema:
                if self._is_schema_used_in_object(ref_schema, target_schema, full_spec, visited_refs):
                    return True
        
        # allOf, oneOf, anyOf をチェック
        for composite_key in ["allOf", "oneOf", "anyOf"]:
            if composite_key in schema:
                for sub_schema in schema[composite_key]:
                    if self._is_schema_used_in_object(sub_schema, target_schema, full_spec, visited_refs):
                        return True
        
        return False
    
    def _get_schema_description(self, spec: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
        """
        スキーマ名から説明などの詳細情報を取得する
        
        Args:
            spec: OpenAPI仕様全体
            schema_name: 検索対象のスキーマ名
            
        Returns:
            スキーマの詳細情報を含む辞書
        """
        schema = spec.get("components", {}).get("schemas", {}).get(schema_name, {})
        
        return {
            "title": schema.get("title", ""),
            "description": schema.get("description", ""),
            "type": schema.get("type", ""),
            "properties": self._get_properties_with_descriptions(schema),
            "required": schema.get("required", [])
        }
    
    def _get_properties_with_descriptions(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        スキーマのプロパティから説明を含む情報を取得する
        
        Args:
            schema: スキーマオブジェクト
            
        Returns:
            プロパティ名と説明を含む辞書
        """
        properties = {}
        
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                properties[prop_name] = {
                    "type": prop_schema.get("type", ""),
                    "description": prop_schema.get("description", ""),
                    "format": prop_schema.get("format", ""),
                    "example": prop_schema.get("example", "")
                }
                
        return properties