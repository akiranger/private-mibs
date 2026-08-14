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
- セキュリティ: SNMP v3 認証/暗号化の設定を検証する。エージェントは可能な限り SNMPv3 を推奨し、pysnmp の USM ユーザ設定を利用して認証/暗号化を必須化すること。
  - 例: USM ユーザは外部シークレットマネージャ経由で読み込み、運用環境ではプレーンテキストのファイルは避ける。
  - このリポジトリの scaffold/pysnmp_agent.py には register_usm_user()/load_usm_users_from_file() の開発向けヘルパがあり、pysnmp の実装側で USM を登録する際の参照に使えます（例を下記に示す）。
- アクセス制御: OID レベルの ACL を用意し、読み取り/書き込み権限をチェックする仕組みを実装する。scaffold/pysnmp_agent.py は簡易 ACL_MAP をサポートしており、実運用では外部ポリシー管理（ファイル/DB/サービス）に置き換えてください。
- 入力検証: handler 層で SNMP 型情報 (SYNTAX / MAX-ACCESS) に基づく入力検証を行い、サイズや範囲を厳密にチェックしてください。生成コードは整数カラムの基本的な検証を追加していますが、完全な対応には各 SNMP 型の仕様に従った検証が必要です。

USM ユーザ登録のサンプル（pysnmp_agent ヘルパ利用 / 開発用）:

```python
from scaffold import pysnmp_agent
# development: load from a JSON file (dev-only)
pysnmp_agent.load_usm_users_from_file('secrets/usm_users.json')
# or register programmatically
pysnmp_agent.register_usm_user('admin', auth_protocol='SHA', auth_key='...secret...', priv_protocol='AES', priv_key='...secret...')
```

pysnmp での本番 USM 登録（概念）:

- pysnmp の UsmUserData を使って各ユーザを登録し、CommandResponder 起動時に USM を組み込む。
- シークレットは OS レベルの keyring / HashiCorp Vault / cloud KMS を利用して配布すること。

このファイルはプロトタイプの設計と実装ガイドを提供します。次のタスクとしては上記雛形を実運用の Secrets 管理に接続し、統合テストを追加します。