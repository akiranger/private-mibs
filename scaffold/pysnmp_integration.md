pysnmp 統合プロトタイプ

目的

pysnmp を使ってプロトタイプの SNMP エージェントを作り、生成されたハンドラ (scaffold/generated_handlers/*.py) を呼び出す検証を行うための手順とサンプルコードのテンプレート。

前提

- pysnmp がインストールされていること: pip install pysnmp
- 生成ハンドラは scaffold/generated_handlers/{name}.py に出力されること

アプローチ

1. MIB の各オブジェクトに対応する OID -> handler 名のマッピングを用意する（小規模なら dict）。
2. pysnmp の CommandResponder や Agent を起動し、要求(OID) を受け取ったらマッピングからハンドラ名を引き、該当モジュールの get_/set_ 関数を呼ぶ。
3. handler の戻り値/例外を SNMP 応答に変換して返す。

サンプルテンプレート (pseudocode)

```python
# scaffold/pysnmp_agent.py (雛形)
import importlib.util
import os
from pysnmp.hlapi import *  # pysnmp の適切な API を使って下さい

# 簡易 OID -> handler 名マップ
OID_MAP = {
    '1.3.6.1.4.1.99999.1.1': 'myScalar',
}

# モジュール読み込みユーティリティ
def load_handler(name):
    modpath = os.path.join(os.path.dirname(__file__), 'generated_handlers', f'{name}.py')
    spec = importlib.util.spec_from_file_location(f'scaffold.generated_handlers.{name}', modpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# psuedocode: pysnmp のリスナで OID を受け取ったら
# oid_str = '1.3.6.1.4.1.99999.1.1'
# handler_name = OID_MAP[oid_str]
# mod = load_handler(handler_name)
# val = mod.get_myScalar(None)  # 実装に合わせて引数を調整
# return SNMP response with val
```

注意点 / 次の実装ステップ

- 実装時は pysnmp の具体的な API (CommandResponder/Context/Managed Objects) を利用し、GET/SET/GETNEXT を正しくサポートすること。
- パフォーマンスを考慮してハンドラモジュールのキャッシュを行う。
- セキュリティ: SNMPv3 認証/暗号化の設定を検証する。実運用では必須。推奨項目:
  1. pysnmp での USM (ユーザ名、認証アルゴリズム、プライバシー暗号) の設定例を提供すること
  2. エージェント側で principal/user 情報を取得して ACL に紐付ける（scaffold/pysnmp_agent.py の ctx 引数を利用）
  3. 管理トラフィックは管理専用ネットワークか制限されたACL経由のみ許可する
  4. SNMPv1/2c は運用では無効化を推奨し、どうしても必要な場合は読み取り専用にする

追加: pysnmp_integration での実装ガイドライン
- CommandResponder あるいは Agent/Context を構築して SNMPv3 の USM ユーザを登録する例を README に追加する。
- pysnmp の Context から principal 情報を抽出して、pysnmp_agent.handle_get/handle_set に ctx={'principal': username} のように渡すことで ACL を評価できる。

このファイルはプロトタイプの設計と実装ガイドを提供します。次のタスクとしては上記雛形を実装し、簡単な GET/SET の統合テストを追加します。

このファイルはプロトタイプの設計と実装ガイドを提供します。次のタスクとしては上記雛形を実装し、簡単な GET/SET の統合テストを追加します。