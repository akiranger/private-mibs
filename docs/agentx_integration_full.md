AgentX との統合（詳細ガイド）

このドキュメントは scaffold/agentx_pass_persist.py を用いた net-snmp(pass_persist) と生成ハンドラの連携手順を詳述します。

概要

- 目的: net-snmp (snmpd) と本リポジトリの生成ハンドラ（scaffold/generated_handlers/*）を短期間で連携させ、実運用前に動作確認を容易にする。
- アプローチ: snmpd の pass_persist 機能を利用して、snmpd が標準入出力経由で常駐するヘルパーへリクエストを転送します。

ファイル一覧（本実装）

- scaffold/agentx_pass_persist.py — pass_persist 用ヘルパースクリプト
- scaffold/agentx_mapping.example.json — マッピング例
- scaffold/generated_handlers/<name>.py — 生成ハンドラの設置場所

ヘルパーの役割

- OID -> ハンドラ名 のマッピングを読み、GET/SET コマンドが来たら対応する get_<name>/set_<name> を呼び出す。
- snmpd の pass_persist による簡易テキストプロトコル（PING/GET/SET）を実装している。

mapping.json 形式

{
  "1.3.6.1.4.1.53864.1.0": "myScalar",
  "1.3.6.1.4.1.53864.2.0": "otherScalar"
}

scaffold/agentx_pass_persist.py の使い方

1. マッピングファイルを作成: /etc/snmp/agentx_mapping.json（上の例を参照）
2. snmpd.conf に pass_persist 行を追加:
   pass_persist .1.3.6.1.4.1.53864 /usr/bin/python3 /opt/project/scaffold/agentx_pass_persist.py /etc/snmp/agentx_mapping.json
3. snmpd を再起動
4. snmpget/snmpwalk で確認

生成ハンドラの書式（実装例）

# scaffold/generated_handlers/myScalar.py

def get_myScalar(ctx):
    # 例: 永続化層から読み出す
    return 123

def set_myScalar(ctx, value):
    # 必要な検証と永続化を行う
    return True

テスト（ヘルパー単体）

- ヘルパーを直接呼んで応答を確認:
  echo -e "PING\nGET 1.3.6.1.4.1.53864.1.0\n" | python3 scaffold/agentx_pass_persist.py scaffold/agentx_mapping.example.json

トラブルシューティング

- snmpd のログ (/var/log/syslog や /var/log/snmpd.log) をチェックしてください。
- ヘルパーが起動していない、あるいは権限エラーが出る場合、snmpd の実行ユーザとヘルパーの実行パス/権限を確認します。

注意点と拡張

- pass_persist は即座に導入できる短期的な手段です。高負荷、複雑なトランザクション、AgentX 固有機能が必要な場合は C/C++ サブエージェントの実装や pysnmp ベースの別実装を検討してください。

デプロイ例 (snmpd.conf と systemd ユニット)

- snmpd.conf と systemd ユニットの完全なサンプルは docs/snmpd_systemd_examples.md を参照してください。ここには検証用の最小 snmpd.conf、snmpd を systemd で起動するユニットの例、及び agentx_pass_persist のデバッグ用 systemd ユニット例を含んでいます。

