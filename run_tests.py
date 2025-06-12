#!/usr/bin/env python3
"""
OpenAPI Diff テスト実行スクリプト
"""

import unittest
import sys
from pathlib import Path

# 親ディレクトリをインポートパスに追加
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

# テストを実行
if __name__ == "__main__":
    # テストディスカバリーを使用して全テストを実行
    unittest.main(module=None, argv=['', 'discover', '--start-directory', 'tests', '--pattern', 'test_*.py'])
