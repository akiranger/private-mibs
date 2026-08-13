Architecture — 詳細

設計要旨

- MIB -> JSON スキーマ -> ハンドラ生成 -> 永続化/揮発ストア のパイプライン
- 永続ストア: SQLite。テーブルは MIB オブジェクトに対応させる。
- 揮発ストア: Redis。セッションや状態、頻繁更新されるカウンタ等を格納。

データフロー

1) MIB を解析（scaffold/mib_parser.py）してオブジェクト一覧と基本情報を抽出
2) 生成器（scaffold/generator.py）がオブジェクトごとにハンドラを生成
3) サブエージェントが GET/SET を受け取り、ハンドラを呼ぶ。ハンドラは persistence.py を通じて DB を更新/参照
4) Redis はパフォーマンスのためのキャッシュや揮発データに利用

運用考慮

- バックアップ: SQLite ファイルの定期スナップショット + Redis の RDB/AOF
- 可用性: 本番では PostgreSQL + Redis レプリケーションを検討
- セキュリティ: SNMP v3 を使い、認証・暗号化を必須にすることを推奨

拡張ポイント

- pysmi を使った正確な OID / タイプ抽出
- 生成テンプレートを拡張してテーブル/インデックス/ユニーク制約を自動生成
- AgentX と直接結合するためのラッパー（pysnmp or net-snmp subagent）
