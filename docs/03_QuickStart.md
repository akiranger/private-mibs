# クイックスタートガイド

5分で動かす最小構成ガイド。詳細は [アーキテクチャ](02_Architecture.md) を参照してください。

## 📋 前提条件

- **OS**: Linux / macOS / Windows(WSL)
- **Python**: 3.8 以上
- **Git**: リポジトリ管理用（任意）

## 🚀 ステップ1: セットアップ

### 1.1 リポジトリをクローン

```bash
git clone https://github.com/akiranger/private-mibs.git
cd private-mibs
```

### 1.2 Python 環境を構築

```bash
# 仮想環境の作成（推奨）
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 依存パッケージをインストール
pip install --upgrade pip
pip install pysmi pysnmp redis
```

| パッケージ | 用途 | 必須 |
|-----------|------|------|
| `pysmi` | 正確なMIB解析 | ❌ |
| `pysnmp` | Pythonエージェント | ❌ |
| `redis` | 一時キャッシュ | ❌ |

**注**: 全て任意。テキスト解析フォールバックあり。

### 1.3 ディレクトリ確認

```bash
ls -la
# README.md
# src/              # ソースコード
# docs/             # ドキュメント
# tests/            # テスト
# data/             # DB置き場（生成される）
```

## 📝 ステップ2: サンプル MIB をパース

### 2.1 MIB ファイルを確認

```bash
cat src/mib/resources/example/EXAMPLE-MIB
```

**出力例**:
```
EXAMPLE-MIB DEFINITIONS ::= BEGIN
  myScalar OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-write
    ::= { myCompany 1 }
END
```

### 2.2 JSON スキーマを生成

```bash
python src/mib/mib_parser.py src/mib/resources/example/EXAMPLE-MIB \
  > src/mib/resources/example/example_schema.json

# 生成確認
cat src/mib/resources/example/example_schema.json
```

**出力例**:
```json
{
  "mib": "EXAMPLE-MIB",
  "objects": [
    {
      "name": "myScalar",
      "kind": "scalar",
      "syntax": "Integer32",
      "access": "read-write"
    }
  ]
}
```

## ⚙️ ステップ3: ハンドラを生成

### 3.1 ハンドラディレクトリを作成

```bash
mkdir -p src/deploy/generated_handlers
```

### 3.2 ハンドラを生成

```bash
python src/mib/generator.py src/mib/resources/example/example_schema.json \
  src/deploy/generated_handlers

# 生成確認
ls -la src/deploy/generated_handlers/
# myScalar.py（生成されたハンドラ）
```

### 3.3 生成ハンドラを確認

```bash
cat src/deploy/generated_handlers/myScalar.py
```

**出力例**:
```python
def get_myScalar(ctx):
    """Read handler"""
    db = ctx.get('db')
    if not db:
        return None
    result = db.query('myScalar_table', 'id=1')
    return result['value'] if result else None

def set_myScalar(ctx, value):
    """Write handler"""
    if not isinstance(value, int):
        raise TypeError("Expected int")
    db = ctx.get('db')
    db.upsert('myScalar_table', {'value': value})
    return True
```

## 🧪 ステップ4: デモで動作確認

### 4.1 ローカル実行（デモ）

```bash
# DB初期化
rm -f data/db.sqlite  # 前回の実行をクリア

# GET操作（値が無い状態）
python src/runtime/agentx_demo.py myScalar get
# 出力: GET result: None
```

### 4.2 SET 操作

```bash
python src/runtime/agentx_demo.py myScalar set 42
# 出力: SET invoked for myScalar
```

### 4.3 GET 操作（値あり）

```bash
python src/runtime/agentx_demo.py myScalar get
# 出力: GET result: 42
```

### 4.4 DB を確認

```bash
sqlite3 data/db.sqlite ".tables"
sqlite3 data/db.sqlite "SELECT * FROM myScalar_table;"
# id | value
# 1  | 42
```

## ✅ 次のステップ

### 👤 初心者向け

✅ ここまで終了。以下、プロトタイプ検証へ進む：

1. **独自 MIB を試す** - 別の MIB ファイルを `src/mib/resources/` に配置
2. **ハンドラをカスタマイズ** - 生成コードを手動編集して動作確認
3. **pysnmp で実行** - [5. デプロイメント](05_Deployment.md) の pysnmp セクション参照

### 👨‍💻 開発者向け

🔧 以下の資料で詳細を理解：

1. **コンポーネント詳細** - [04_Components.md](04_Components.md)
   - Parser API
   - Generator テンプレート
   - Persistence ライブラリ

2. **アーキテクチャ** - [02_Architecture.md](02_Architecture.md)
   - データフロー
   - ハンドラ間通信
   - 拡張ポイント

### 🚀 運用者向け

📦 本番デプロイへ：

1. **pysnmp プロトタイプ** - [05_Deployment.md](05_Deployment.md) の pysnmp セクション参照
2. **net-snmp + pass_persist** - [05_Deployment.md](05_Deployment.md) の pass_persist セクション参照
3. **セキュリティ設定** - [06_Security.md](06_Security.md) で SNMPv3 を有効化

### 🔐 セキュリティ担当向け

🛡️ 本番環境チェックリスト：

- [ ] [06_Security.md](06_Security.md) を読了
- [ ] SNMPv3 認証・暗号化を有効化
- [ ] ACL でアクセス制御を実装
- [ ] 入力検証をハンドラに追加
- [ ] 監査ログを記録

## 🐛 トラブルシューティング

### Q: `ImportError: No module named 'pysmi'`

**A**: `pysmi` はオプション。なくても動作します（テキスト解析フォールバック）。

```bash
# 必要なら手動インストール
pip install pysmi
```

### Q: `sqlite3.OperationalError: database is locked`

**A**: DB が他プロセスからアクセス中。以下で確認：

```bash
# DB ファイルの所有者確認
ls -l data/db.sqlite

# DB をリセット
rm -f data/db.sqlite
python src/runtime/agentx_demo.py myScalar get  # 再初期化
```

### Q: MIB ファイルが見つからない

**A**: パスを確認。絶対パスまたは相対パスが正しいか：

```bash
# カレントディレクトリ確認
pwd
# /home/user/private-mibs

# 相対パス確認
ls src/mib/resources/example/EXAMPLE-MIB
```

### Q: ハンドラ生成後、変更が反映されない

**A**: キャッシュをクリア：

```bash
# Python キャッシュをクリア
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete

# 再実行
python src/runtime/agentx_demo.py myScalar get
```

## 📚 参考コマンド集

| 用途 | コマンド |
|------|---------|
| **MIBをパース** | `python src/mib/mib_parser.py <mib_file> \| jq` |
| **ハンドラを生成** | `python src/mib/generator.py <schema.json> <output_dir>` |
| **デモ GET** | `python src/runtime/agentx_demo.py <name> get` |
| **デモ SET** | `python src/runtime/agentx_demo.py <name> set <value>` |
| **テスト実行** | `pytest tests/` |
| **DB 確認** | `sqlite3 data/db.sqlite ".schema"` |

## 🎯 よくある活用例

### 例1: センサー値の管理

```bash
# 1. MIB定義（温度センサー）
# temperatureValue OBJECT-TYPE SYNTAX Integer32

# 2. ハンドラを生成
python src/mib/generator.py schema.json src/deploy/generated_handlers

# 3. ハンドラをカスタマイズ
vim src/deploy/generated_handlers/temperatureValue.py
# → センサーAPIを呼び出すコードに編集

# 4. デモで確認
python src/runtime/agentx_demo.py temperatureValue get
```

### 例2: SNMP v3 アクセス制御

```bash
# 1. pysnmp でプロトタイプエージェントを起動
python src/runtime/pysnmp_agent.py --port 161 --snmpv3

# 2. SNMPv3 ユーザを登録（詳細: 06_Security.md）

# 3. クライアントからアクセス
snmpget -v3 -u admin -a SHA -A password localhost temperatureValue
```

### 例3: pass_persist で net-snmp と統合

```bash
# 1. マッピングファイルを作成
vim src/deploy/agentx_mapping.json
# { "1.3.6.1.4.1.XXX.1.0": "myScalar" }

# 2. snmpd.conf に pass_persist 行を追加
# pass_persist .1.3.6.1.4.1.XXX python3 agentx_pass_persist.py

# 3. 本番デプロイメント（詳細: 05_Deployment.md）
```

## 🔗 リンク集

| リソース | 説明 |
|---------|------|
| [01_Overview.md](01_Overview.md) | プロジェクト全体像 |
| [02_Architecture.md](02_Architecture.md) | 詳細アーキテクチャ |
| [04_Components.md](04_Components.md) | API リファレンス |
| [05_Deployment.md](05_Deployment.md) | 本番デプロイ |
| [06_Security.md](06_Security.md) | セキュリティガイド |

---

**最終更新**: 2026年8月  
**難易度**: ⭐ 初級
