# 詳細アーキテクチャガイド

## 🏛️ システムアーキテクチャ

### レイヤー構成

```
┌─────────────────────────────────────┐
│      SNMP クライアント層             │
│   (snmpget, snmpwalk, 監視ツール)   │
└────────────────┬────────────────────┘
                 │ SNMPv3(推奨)/v2c
┌────────────────▼────────────────────┐
│    エージェント層                    │
│  ┌─────────────┐  ┌───────────────┐ │
│  │  pysnmp     │  │ pass_persist  │ │
│  │  (Python)   │  │(net-snmp)     │ │
│  └──────┬──────┘  └───────┬───────┘ │
└─────────┼──────────────────┼────────┘
          │ 標準Pythonモジュール
┌─────────▼──────────────────▼────────┐
│    ハンドラ層                        │
│  ┌────────────────────────────────┐ │
│  │ get_<name>(...) / set_<name>   │ │
│  │(生成コード)                     │ │
│  └─────────────┬──────────────────┘ │
└────────────────┼───────────────────┘
                 │
┌────────────────▼───────────────────┐
│    永続化層                        │
│  ┌──────────────┐ ┌────────────┐  │
│  │ SQLiteAdapter│ │RedisAdapter│  │
│  │(耐久データ)  │ │(一時ハッシュ)│  │
│  └──────┬───────┘ └────────┬───┘  │
└─────────┼────────────────────┼────┘
          │                    │
┌─────────▼────────┐  ┌───────▼──────┐
│  SQLite DB       │  │  Redis KV    │
│ /data/db.sqlite  │  │ localhost:6379
└──────────────────┘  └──────────────┘
```

## 🔄 MIBパイプライン（詳細フロー）

### 1️⃣ 入力: MIB ファイル（SMIv2 テキスト）

```
myMIB DEFINITIONS ::= BEGIN
  IMPORTS ...
  
  myObject OBJECT-TYPE
    SYNTAX      Integer32
    MAX-ACCESS  read-write
    DESCRIPTION "説明"
    ::= { myCompany 1 }
END
```

### 2️⃣ 中間: JSON スキーマ

```json
{
  "mib": "myMIB",
  "objects": [
    {
      "name": "myObject",
      "kind": "scalar",
      "oid_assignment": "1.3.6.1.4.1.XXXXX.1",
      "syntax": "Integer32",
      "access": "read-write",
      "description": "説明"
    }
  ]
}
```

### 3️⃣ 出力: Python ハンドラ

```python
# src/deploy/generated_handlers/myObject.py

def get_myObject(ctx):
    """読取ハンドラ"""
    # 1. DB からデータ取得
    # 2. 型チェック・範囲チェック
    # 3. 値を返す
    pass

def set_myObject(ctx, value):
    """書込ハンドラ"""
    # 1. 入力値を検証
    # 2. DB へ保存
    # 3. 成功/失敗を返す
    pass
```

## 🔌 ハンドラ間通信

### コンテキストオブジェクト（ctx）

各ハンドラに渡される `ctx` パラメータは、実行環境情報を含みます：

```python
ctx = {
    'user': 'admin',           # SNMPv3 ユーザ名（pysnmp）
    'client_addr': ('10.0.0.1', 12345),  # クライアント情報
    'db': SQLiteAdapter(...),  # DB アダプタ参照
    'cache': RedisAdapter(...),# キャッシュ参照
}
```

### 例: OID ベース検索

```python
def get_myObject(ctx):
    # OID: 1.3.6.1.4.1.XXXXX.1.0
    # テーブルの場合は OID の末尾インデックスを抽出
    db = ctx.get('db')
    if not db:
        return None
    
    # テーブルの場合（OID suffix から INDEX 値を抽出）
    value = db.query_by_oid('myTable', oid_suffix=1)
    return value
```

## 💾 永続化層の詳細

### SQLiteAdapter

**ファイル**: `src/runtime/persistence.py`

**主要メソッド**:

| メソッド | 説明 | 例 |
|---------|------|-----|
| `create_table_for_object(name, columns)` | テーブル作成 | `create_table_for_object('myScalar', [('value', 'INTEGER')])` |
| `upsert(table, data, unique_cols)` | INSERT ON CONFLICT | `upsert('myScalar', {'value': 100}, unique_cols=['id'])` |
| `query_all(table)` | テーブル全行取得 | `query_all('myScalar')` |
| `query(table, where_clause)` | WHERE 条件で検索 | `query('myTable', 'id=1')` |
| `transaction()` | トランザクション開始 | `with db.transaction(): ...` |

**設定**（`pragma`）:

```python
# WAL モード（並行読取対応）
PRAGMA journal_mode = WAL

# ビジー時のタイムアウト (30秒)
PRAGMA busy_timeout = 30000

# 同期レベル（バランス型）
PRAGMA synchronous = NORMAL
```

### RedisAdapter

**ファイル**: `src/runtime/persistence.py`

**主要メソッド**:

| メソッド | 説明 | 例 |
|---------|------|-----|
| `set(key, value, ttl)` | キー設定（TTL付き） | `set('counter', 100, ttl=3600)` |
| `get(key)` | キー取得 | `get('counter')` |
| `delete(key)` | キー削除 | `delete('counter')` |
| `incr(key)` | インクリメント | `incr('counter')` |
| `hset(key, field, value)` | ハッシュ設定 | `hset('session:1', 'user', 'admin')` |

**活用例**:

```python
# セッション情報（TTL付き）
cache.hset('session:1', 'principal', 'admin', ttl=1800)

# アクセスカウンタ（揮発性）
cache.incr('access_count')

# キャッシュ（失敗時フォールバック）
val = cache.get('slow_query')
if not val:
    val = compute_expensive()
    cache.set('slow_query', val, ttl=300)
```

## 🔐 データ整合性

### トランザクション（複数 OID の一貫性）

複数の MIB オブジェクトを一度に更新する場合：

```python
def set_complex_state(ctx, values):
    """複数 OID を整合性を保って更新"""
    db = ctx['db']
    
    try:
        with db.transaction():
            # 全ての更新をトランザクション内で実行
            db.upsert('table1', {'value': values['obj1']})
            db.upsert('table2', {'value': values['obj2']})
            # コミット（トランザクション終了）
        return True
    except Exception as e:
        # ロールバック（自動）
        return False
```

### ログと監査

**推奨事項**:
- 重要な SET 操作を SQLite へ記録
- タイムスタンプと実行者（principal）を含める
- 定期的に監査ログをローテーション

```python
def audit_log(ctx, operation, oid, old_value, new_value):
    """監査ログ記録"""
    db = ctx['db']
    db.upsert('audit_log', {
        'timestamp': time.time(),
        'principal': ctx.get('user', 'unknown'),
        'operation': operation,
        'oid': oid,
        'old_value': old_value,
        'new_value': new_value,
    })
```

## 🛠️ ハンドラ生成テンプレート

**ファイル**: `src/mib/generator.py`

生成されるハンドラはテンプレートから自動生成されます：

```python
HANDLER_TMPL = '''
def get_{name}(ctx):
    """Get handler for {name}"""
    db = ctx.get('db')
    if not db:
        return None
    
    result = db.query('{table}', 'id=1')
    return result['value'] if result else None

def set_{name}(ctx, value):
    """Set handler for {name}"""
    # 入力検証
    if not isinstance(value, {type}):
        raise TypeError(f"Expected {type}, got {type(value)}")
    
    db = ctx.get('db')
    db.upsert('{table}', {{'value': value}})
    return True
'''
```

## 🚀 拡張ポイント

### 1. テーブル型のサポート

現状はスカラー型のみ。テーブル型（SEQUENCE）対応：

```json
{
  "name": "myTable",
  "kind": "table",
  "entry": "myEntry",
  "fields": [
    {"name": "id", "type": "Integer32", "index": true},
    {"name": "name", "type": "OCTET STRING"},
    {"name": "status", "type": "Integer32"}
  ]
}
```

生成ハンドラは `getbulk`、テーブルスキャンに対応：

```python
def get_myTable(ctx):
    """テーブル全行を取得"""
    db = ctx['db']
    return db.query_all('myTable')

def get_myTableEntry(ctx, index):
    """特定行を取得"""
    db = ctx['db']
    return db.query('myTable', f'id={index}')
```

### 2. OID ベース検索の実装

MIB の OID を自動抽出し、OID → ハンドラマッピング：

```python
OID_HANDLER_MAP = {
    '1.3.6.1.4.1.XXXXX.1.0': 'myScalar',
    '1.3.6.1.4.1.XXXXX.2': 'myTable',
}

# エージェント側でOID検索
oid = '1.3.6.1.4.1.XXXXX.1.0'
handler_name = OID_HANDLER_MAP.get(oid)
handler = load_handler(handler_name)
value = handler.get_xxx(ctx)
```

### 3. レプリケーション対応

本番環境での高可用性：

```python
class ReplicatedSQLiteAdapter:
    def __init__(self, primary_db, standby_db):
        self.primary = primary_db
        self.standby = standby_db
    
    def upsert(self, table, data):
        # プライマリに書込
        self.primary.upsert(table, data)
        # スタンバイにもレプリケーション
        self.standby.upsert(table, data)
```

## 📊 パフォーマンス考慮

### 1. ハンドラ読み込みキャッシュ

```python
# モジュールキャッシュ
_handler_cache = {}

def load_handler(name):
    if name not in _handler_cache:
        # 初回のみインポート
        mod = importlib.import_module(f'src.deploy.generated_handlers.{name}')
        _handler_cache[name] = mod
    return _handler_cache[name]
```

### 2. DB接続プーリング

```python
class SQLiteAdapter:
    def __init__(self, db_path, pool_size=5):
        self.pool = queue.Queue(maxsize=pool_size)
        for _ in range(pool_size):
            conn = sqlite3.connect(db_path)
            self.pool.put(conn)
```

### 3. クエリ最適化

```python
# インデックス作成（自動生成）
db.execute('CREATE INDEX idx_myTable_id ON myTable(id)')

# EXPLAIN QUERY PLAN で確認
db.execute('EXPLAIN QUERY PLAN SELECT * FROM myTable WHERE id=1')
```

## 🔄 ライフサイクル

### 起動フェーズ

1. **エージェント起動** - pysnmp/pass_persist プロセス開始
2. **ハンドラロード** - 生成ハンドラを `sys.path` に追加
3. **DB 初期化** - テーブル作成、スキーマ検証
4. **準備完了** - SNMP リクエスト受付開始

### 実行フェーズ

1. **リクエスト受信** - OID、操作タイプを認識
2. **ハンドラ呼び出し** - get/set 関数を実行
3. **応答返却** - 値またはエラーコード

### シャットダウンフェーズ

1. **リクエスト停止** - 新規接続を拒否
2. **処理完了待機** - 進行中の操作を完了
3. **クリーンアップ** - DB コミット、接続クローズ
4. **プロセス終了**

---

**ステータス**: 実装完了（レプリケーション機能は今後）  
**関連**: [コンポーネント詳細](04_Components.md) / [セキュリティ](06_Security.md)
