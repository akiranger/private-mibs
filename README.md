AgentX MIB 永続化フレームワーク（プロトタイプ）

概要

SMIv2 MIB からスキーマを生成し、SQLite（永続）＋Redis（揮発）で管理する AgentX サブエージェント向けのプロトタイプです。
詳細は docs/ 以下にまとめています。

クイックスタート

前提: Python 3.8+

1) （任意）依存を入れる
   pip install redis pysmi pysnmp

2) サンプルMIBをパースしてスキーマ生成
   python scaffold\mib_parser_text_advanced.py example\EXAMPLE-MIB > docs\schema_example_text.json

3) スキーマからハンドラを生成
   python scaffold\generator.py docs\schema_example_text.json scaffold\generated_handlers_improved

4) デモ（GET/SET を模擬）
   python scaffold\agentx_demo.py myScalar get
   python scaffold\agentx_demo.py myScalar set 123

運用ノート

- 生成物（scaffold/generated_handlers*）は Git 管理対象外です（.gitignore）。空フォルダ保持のため .gitkeep を置いてあります。
- pysmi/pysnmp を導入するとより正確な MIB 抽出が可能ですが、標準MIBの配置が必要です。詳しくは docs/parser.md と docs/agentx_integration.md を参照してください。

ドキュメント

主なドキュメント: docs/overview.md, docs/quickstart.md, docs/parser.md, docs/persistence.md, docs/generator.md, docs/architecture.md

貢献

Issue/PR を歓迎します。