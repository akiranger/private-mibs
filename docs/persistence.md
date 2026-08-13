persistence.py の説明

概要

SQLiteAdapter と RedisAdapter を提供します。

SQLiteAdapter

- デフォルト DB: data/db.sqlite
- create_table_for_object(name, columns): テーブル作成
- upsert(table, data): 単純な挿入（ユニーク制約は未実装）
- query_all(table): 全行取得

RedisAdapter

- redis ライブラリが必要。接続 URL をコンストラクタで指定可能
- set/get: JSON シリアライズして保存/取得

注意点

- 複数 OID の一貫性が必要な更新は SQLite トランザクションで行うべきです。
- Redis は揮発データ（セッションや頻繁更新されるステータス）用に使う想定です。
