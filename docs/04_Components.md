# コンポーネント詳細ガイド

各モジュールのAPI詳細とカスタマイズガイド。

## 1️⃣ MIB Parser（解析エンジン）

**ファイル**: `src/mib/mib_parser.py`, `src/mib/mib_parser_pysmi.py`

### 機能

MIB（SMIv2）テキストファイルを解析し、JSON スキーマに変換。

### 使用方法

```bash
python src/mib/mib_parser.py <mib_file> > output.json
```

### 出力スキーマ形式

```json
{
  "mib": "MIB名",
  "objects": [
    {
      "name": "オブジェクト名",
      "kind": "scalar | table | entry | column",
      "syntax": "Integer32 | OCTET STRING | ...",
      "access": "read-only | read-write | not-accessible",
      "description": "説明文",
      "oid_assignment": "親オブジェクト名 N",
      "raw": "解析元テキスト（フォールバック時）"
    }
  ]
}
```

### フィールド説明

| フィールド | 説明 | 例 |
|-----------|------|-----|
| `name` | オブジェクト識別子 | `sysUpTime` |
| `kind` | MIB オブジェクト型 | `scalar`, `table`, `column` |
| `syntax` | SNMP データ型 | `Integer32`, `OCTET STRING`, `DisplayString` |
| `access` | アクセス権限 | `read-only`, `read-write` |
| `oid_assignment` | OID 割り当て（親 番号） | `system 3` |
| `description` | 仕様書記述 | 日本語対応 |

### 解析エンジン（2段構成）

#### モード1: pysmi（推奨）

```bash
pip install pysmi pysnmp
```

**動作**:
- 公式 MIB リポジトリから依存 MIB を自動ダウンロード
- OID ドット表記を自動抽出
- 型情報を正確に解析

**出力例**:
```json
{
  "name": "sysUpTime",
  "oid_assignment": "1.3.6.1.2.1.1.3"
}
```

#### モード2: テキスト解析（フォールバック）

pysmi 未インストール時に自動切り替え。

**動作**:
- OBJECT-TYPE ブロックを正規表現で検出
- 型と説明を抽出
- OID は相対形式で記録

**出力例**:
```json
{
  "name": "sysUpTime",
  "oid_assignment": "system 3",
  "raw": "解析元の生テキスト"
}
```

### カスタマイズ

#### 独自の MIB を解析

```bash
# ステップ1: MIB ファイルを配置
cp my-custom.mib src/mib/resources/custom/

# ステップ2: パース実行
python src/mib/mib_parser.py src/mib/resources/custom/my-custom.mib \
  > my-schema.json

# ステップ3: スキーマ確認
cat my-schema.json | python3 -m json.tool
```

#### MIB リポジトリをカスタマイズ

pysmi が MIB を検索するパス：

```python
# src/mib/mib_parser_pysmi.py (一部)

# MIB ソースパス
MIB_SOURCES = [
    'file:///usr/share/snmp/mibs',  # システム MIB
    'file://./mibs',                 # ローカルディレクトリ
    'http://oid-info.com/download/mib/',  # リモートリポジトリ
]
```

---

## 2️⃣ Generator（コード生成エンジン）

**ファイル**: `src/mib/generator.py`

### 機能

JSON スキーマから Python ハンドラを自動生成。

### 使用方法

```bash
python src/mib/generator.py <schema.json> <output_directory>
```

### 生成されるコード構造

```
src/deploy/generated_handlers/
├── myScalar.py           # スカラー型
├── myTable.py            # テーブル型（将来）
└── __init__.py          # パッケージ初期化
```

### 生成ハンドラの例

```python
# src/deploy/generated_handlers/myScalar.py

def get_myScalar(ctx):
    """読取ハンドラ"""
    db = ctx.get('db')
    if not db:
        return None
    
    # テーブル操作
    result = db.query('myScalar_table', 'id=1')
    return result['value'] if result else None

def set_myScalar(ctx, value):
    """書込ハンドラ"""
    # 入力検証
    if not isinstance(value, int):
        raise TypeError(f"Expected int, got {type(value).__name__}")
    
    # 範囲チェック（型情報があれば）
    if value < 0 or value > 2147483647:  # Int32
        raise ValueError(f"Value {value} out of range")
    
    # DB 更新
    db = ctx.get('db')
    db.upsert('myScalar_table', {
        'id': 1,
        'value': value
    })
    return True
```

### ハンドラシグネチャ

| メソッド | 引数 | 戻り値 | 説明 |
|---------|------|--------|------|
| `get_<name>(ctx)` | `ctx`: コンテキスト | 値 / None | 読取 |
| `set_<name>(ctx, value)` | `ctx`, `value` | True / False | 書込 |

### テンプレートのカスタマイズ

```python
# src/mib/generator.py (HANDLER_TMPL)

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
    if not isinstance(value, {type}):
        raise TypeError(f"Expected {type}, got {type(value).__name__}")
    db = ctx.get('db')
    db.upsert('{table}', {{'value': value}})
    return True
'''
```

**テンプレート変数**:
- `{name}` - オブジェクト名
- `{table}` - テーブル名（スキーマから自動生成）
- `{type}` - Pythonデータ型（int, str等）

### テーブル型のカスタマイズ（今後）

```python
# 将来実装予定
{
  "name": "myTable",
  "kind": "table",
  "entry": "myEntry",
  "index": ["id"],  # インデックスカラム
  "columns": [
    {"name": "id", "type": "Integer32", "index": true},
    {"name": "name", "type": "OCTET STRING"},
    {"name": "status", "type": "Integer32"}
  ]
}
```

生成ハンドラ：

```python
def get_myTable(ctx, index=None):
    """テーブル読取"""
    db = ctx['db']
    if index:
        return db.query('myTable', f'id={index}')
    else:
        return db.query_all('myTable')

def set_myTableStatus(ctx, index, value):
    """特定行の status を更新"""
    db = ctx['db']
    db.upsert('myTable', {'id': index, 'status': value})
    return True
```

---

## 3️⃣ Persistence Layer（永続化層）

**ファイル**: `src/runtime/persistence.py`

### 3.1 SQLiteAdapter

#### 初期化

```python
from src.runtime.persistence import SQLiteAdapter

db = SQLiteAdapter(db_path='data/db.sqlite')
```

#### テーブル作成

```python
# スカラー型
db.create_table_for_object('myScalar', [
    ('id', 'INTEGER PRIMARY KEY'),
    ('value', 'INTEGER'),
])

# テーブル型（今後）
db.create_table_for_object('myTable', [
    ('id', 'INTEGER PRIMARY KEY'),
    ('name', 'TEXT'),
    ('status', 'INTEGER'),
])
```

#### 主要 API

```python
# ① UPSERT（挿入または更新）
db.upsert('myScalar', {'id': 1, 'value': 42})

# 一意制約指定で重複チェック
db.upsert('myScalar', 
    {'id': 1, 'value': 42},
    unique_cols=['id']
)

# ② 全行取得
all_rows = db.query_all('myScalar')
# [{'id': 1, 'value': 42}]

# ③ WHERE 条件で検索
rows = db.query('myTable', 'status=1')
# [{'id': 1, 'name': 'device1', 'status': 1}]

# ④ 削除
db.delete('myScalar', where='id=1')

# ⑤ トランザクション
with db.transaction():
    db.upsert('table1', {'value': 100})
    db.upsert('table2', {'value': 200})
    # コミット（正常終了時）
    # ロールバック（例外発生時）
```

#### パフォーマンスチューニング

```python
# プラグマ設定（初期化時）
db = SQLiteAdapter('data/db.sqlite')

# WAL モード（並行読取対応）
db.execute('PRAGMA journal_mode = WAL')

# ページサイズ最適化
db.execute('PRAGMA page_size = 4096')

# キャッシュサイズ
db.execute('PRAGMA cache_size = 10000')  # 10000 ページ

# インデックス作成（クエリ高速化）
db.execute('CREATE INDEX idx_status ON myTable(status)')
```

#### マイグレーション例

```python
def migrate_v1_to_v2(db):
    """スキーマバージョン1→2"""
    try:
        with db.transaction():
            # 新カラムを追加
            db.execute('ALTER TABLE myTable ADD COLUMN created_at TEXT')
            
            # 既存行に初期値を設定
            db.execute('''
                UPDATE myTable 
                SET created_at = datetime('now')
                WHERE created_at IS NULL
            ''')
    except Exception as e:
        print(f"Migration failed: {e}")
        # ロールバック（自動）

# 実行
migrate_v1_to_v2(db)
```

### 3.2 RedisAdapter

#### 初期化

```python
from src.runtime.persistence import RedisAdapter

cache = RedisAdapter(url='redis://localhost:6379/0')
```

#### 主要 API

```python
# ① キーと値を設定（TTL付き）
cache.set('user:1:name', 'Alice', ttl=3600)
cache.set('counter', 0)

# ② キーを取得
name = cache.get('user:1:name')
# 'Alice'

# ③ キーが存在するか確認
if cache.exists('user:1:name'):
    print("キーが存在します")

# ④ キーを削除
cache.delete('user:1:name')

# ⑤ インクリメント（カウンタ用）
cache.incr('counter')  # 0 → 1
count = cache.get('counter')  # 1

# ⑥ TTL を確認
ttl = cache.ttl('user:1:name')  # 残り秒数

# ⑦ ハッシュ操作（複数フィールド）
cache.hset('session:1', 'user', 'admin')
cache.hset('session:1', 'ip', '192.168.1.1')

user = cache.hget('session:1', 'user')  # 'admin'
session = cache.hgetall('session:1')  # {'user': 'admin', 'ip': '192.168.1.1'}

# ⑧ リスト操作（キュー用）
cache.lpush('queue', 'job1')
cache.rpush('queue', 'job2')
job = cache.lpop('queue')  # 'job1'
```

#### 活用パターン

```python
# パターン1: キャッシュ（L1 は Redis、L2 は DB）
def get_config_with_cache(key, db, cache):
    # L1: Redis キャッシュ確認
    val = cache.get(f'config:{key}')
    if val:
        return val
    
    # L2: DB から取得
    result = db.query('config', f"key='{key}'")
    val = result['value'] if result else None
    
    # キャッシュに保存（TTL=1時間）
    if val:
        cache.set(f'config:{key}', val, ttl=3600)
    
    return val

# パターン2: カウンタ
def increment_request_count(client_ip, cache):
    key = f'req_count:{client_ip}'
    count = cache.incr(key)
    
    # 初回アクセス時のみ TTL を設定
    if count == 1:
        cache.expire(key, 3600)  # 1 時間後に削除
    
    return count

# パターン3: セッション管理
def create_session(user_id, cache):
    session_id = str(uuid.uuid4())
    cache.hset(f'session:{session_id}', 'user_id', user_id)
    cache.hset(f'session:{session_id}', 'created_at', time.time())
    cache.expire(f'session:{session_id}', 1800)  # 30分有効
    return session_id
```

#### 接続プーリング

```python
from src.runtime.persistence import RedisAdapter

# 複数接続の管理
class RedisPool:
    def __init__(self, url, pool_size=10):
        import redis
        self.pool = redis.ConnectionPool.from_url(url, max_connections=pool_size)
    
    def get_connection(self):
        import redis
        return redis.Redis(connection_pool=self.pool)

# 使用例
pool = RedisPool('redis://localhost:6379', pool_size=10)
conn = pool.get_connection()
conn.set('key', 'value')
```

---

## 4️⃣ Agent Integration（エージェント統合）

### 4.1 ローカル実行（agentx_demo.py）

```bash
python src/runtime/agentx_demo.py <object_name> <operation> [value]
```

| 操作 | コマンド | 例 |
|------|---------|-----|
| **読取** | `get <name>` | `python ... myScalar get` |
| **書込** | `set <name> <value>` | `python ... myScalar set 100` |

### 4.2 pysnmp エージェント

詳細は [05_Deployment.md](05_Deployment.md) を参照。

### 4.3 pass_persist ヘルパー

詳細は [05_Deployment.md](05_Deployment.md) を参照。

---

## 🎯 統合例：カスタムハンドラ

生成ハンドラを拡張して、外部 API を呼び出す例：

```python
# src/deploy/generated_handlers/temperatureValue.py

import requests
from datetime import datetime

def get_temperatureValue(ctx):
    """温度センサーから値を取得"""
    try:
        # 外部 API から気温を取得
        response = requests.get('https://api.weather.example.com/temp')
        temp = response.json()['temperature']
        
        # キャッシュに保存
        cache = ctx.get('cache')
        cache.set('temperature:latest', temp, ttl=300)
        
        # DB に履歴を記録
        db = ctx.get('db')
        db.upsert('temperature_history', {
            'timestamp': datetime.now().isoformat(),
            'value': temp
        })
        
        return temp
    except Exception as e:
        print(f"Error: {e}")
        return None

def set_temperatureValue(ctx, value):
    """温度閾値を設定（例）"""
    db = ctx.get('db')
    db.upsert('temperature_config', {
        'threshold': value
    })
    return True
```

---

**関連**: [02_Architecture.md](02_Architecture.md) / [05_Deployment.md](05_Deployment.md)  
**最終更新**: 2026年8月
