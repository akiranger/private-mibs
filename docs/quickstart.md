Quickstart — プロトタイプ実行手順

前提（必須 / 推奨）

- 必須: Python 3.8+
- 推奨: pip install --user pysmi pysnmp
- オプション: Redis サーバ（キャッシュ用）

インストール（最小）

pip install pysmi pysnmp
# Redis を使う場合: pip install redis

スキャフォールドの実行（サンプルワークフロー）

1) サンプル MIB をパースして JSON スキーマを作成
   python scaffold\mib_parser.py example\EXAMPLE-MIB > example\example_schema.json

2) スキーマからハンドラを生成
   python scaffold\generator.py example\example_schema.json scaffold\generated_handlers

3) 生成ハンドラを呼ぶデモ（GET/SET の模擬）
   # agentx_demo はローカルで生成ハンドラを直接呼ぶ模擬ツールです
   python scaffold\agentx_demo.py myScalar get
   python scaffold\agentx_demo.py myScalar set 123

4) pysnmp を使ったプロトタイプ統合（実運用検証用）
   - pysnmp をインストールすると scaffold/pysnmp_agent.py を使って簡易エージェントを起動できます。
   - 詳細は scaffold/pysnmp_integration.md を参照してください。

5) DB 確認
   data\db.sqlite にテーブルと値が入る

ヒント / 注意点

- agentx_demo.py は "模擬" ツールです。net-snmp の AgentX サブエージェントを置き換えるものではなく、生成ハンドラの動作確認用です。
- 実際に SNMP エージェントと接続するには:
  - pysnmp でプロトタイプ検証を行い、期待通りに GET/SET がハンドラへルーティングされることを確認する
  - 運用では net-snmp の subagent を用いる（C ラッパーや IPC）などを検討する
- 依存関係は環境により変わるため、仮想環境（venv）での実行を推奨します。

期待されるコマンド出力例

# デモ: 値が設定されていない場合の get
$ python scaffold\agentx_demo.py myScalar get
GET result: None

# デモ: set 後の get
$ python scaffold\agentx_demo.py myScalar set 123
SET invoked
$ python scaffold\agentx_demo.py myScalar get
GET result: 123

詳細とトラブルシュートは docs/parser.md と scaffold/pysnmp_integration.md を参照してください。