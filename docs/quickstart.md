Quickstart — プロトタイプ実行手順

前提

- Python 3.8+
- （オプション）Redis サーバ

インストール

pip install redis pysmi

スキャフォールドの実行

1) サンプル MIB をパースして JSON スキーマを作成
   python scaffold\mib_parser.py example\EXAMPLE-MIB > example\example_schema.json

2) スキーマからハンドラを生成
      python scaffold\generator.py example\example_schema.json scaffold\generated_handlers

3) 生成ハンドラを呼ぶデモ（GET/SET の模擬）
   python scaffold\agentx_demo.py myScalar get
   python scaffold\agentx_demo.py myScalar set 123

4) DB 確認
   data\db.sqlite にテーブルと値が入る

ヒント

- 実際の AgentX 連携はまだ実装されていません。agentx_demo.py はハンドラ呼び出しの模擬です。
- pysmi を導入すると、より正確な MIB 解析が可能です。docs/parser.md を参照してください。