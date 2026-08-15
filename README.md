# MIB Persistence Framework

MIB（SMIv2）からPythonハンドラを自動生成し、SQLiteとRedisを活用してSNMPエージェント状態を管理するプロトタイプフレームワークです。

## 📋 プロジェクト概要

このプロジェクトは、MIB定義から完全なSNMPエージェントまでの一貫したワークフローを実現します：

1. **MIB解析** - SMIv2ファイルをJSONスキーマに変換
2. **ハンドラ生成** - スキーマからPythonハンドラを自動生成
3. **永続化管理** - SQLiteで耐久的なデータ、Redisで一時的なデータを管理
4. **デプロイ** - net-snmpと連携し、実運用対応

## 🚀 3分でスタート

### 前提条件

- Python 3.8+
- pip

### インストール & 実行

```bash
# 1. 依存パッケージをインストール
pip install pysmi pysnmp redis

# 2. サンプルMIBからスキーマを生成
python src/mib/mib_parser.py src/mib/resources/example/EXAMPLE-MIB \
  > src/mib/resources/example/example_schema.json

# 3. ハンドラを生成
python src/mib/generator.py src/mib/resources/example/example_schema.json \
  src/deploy/generated_handlers

# 4. デモで動作確認（GET/SET模擬）
python src/runtime/agentx_demo.py myScalar get      # 結果: None
python src/runtime/agentx_demo.py myScalar set 123  # 設定
python src/runtime/agentx_demo.py myScalar get      # 結果: 123
```

詳細は [クイックスタート](docs/01_Overview.md) をご覧ください。

## 📁 ディレクトリ構成

| パス | 説明 |
|------|------|
| `src/mib/` | MIB解析、スキーマ生成、ハンドラ生成ツール |
| `src/deploy/` | SNMPエージェント統合（pass_persist、マッピング） |
| `src/runtime/` | デモ、pysnmp連携、永続化ライブラリ |
| `docs/` | ドキュメント（アーキテクチャ、デプロイ、セキュリティ） |
| `tests/` | 単体テスト、統合テスト |

## 📚 ドキュメント

| ドキュメント | 対象者 | 内容 |
|-------------|--------|------|
| [01_Overview.md](docs/01_Overview.md) | 全員 | 全体図、データフロー、主要コンポーネント |
| [02_Architecture.md](docs/02_Architecture.md) | 開発者 | 詳細なアーキテクチャ、拡張ポイント |
| [03_QuickStart.md](docs/03_QuickStart.md) | 初心者 | セットアップ、MIB生成、デモ実行 |
| [04_Components.md](docs/04_Components.md) | 開発者 | Parser、Generator、Persistence API |
| [05_Deployment.md](docs/05_Deployment.md) | 運用者 | pysnmp、pass_persist、systemdでのデプロイ |
| [06_Security.md](docs/06_Security.md) | セキュリティ | SNMPv3、ACL、USM認証、入力検証 |

## 🎯 主要機能

- **自動生成** - MIBからPythonハンドラを自動コード化
- **永続化** - SQLiteによる耐久的なデータ管理
- **一時データ** - Redisによるキャッシュと揮発データ
- **実運用対応** - net-snmpとの統合、pass_persist対応
- **セキュリティ** - SNMPv3、ユーザ認証、ACL対応

## 💡 使用例

### ローカル開発（デモ実行）

生成ハンドラをローカルで実行し、GET/SET動作を検証：

```bash
python src/runtime/agentx_demo.py <object_name> get
python src/runtime/agentx_demo.py <object_name> set <value>
```

### 本番運用（pass_persist統合）

snmpd経由で生成ハンドラを実行：

```bash
# 1. マッピング設定
cp src/deploy/agentx_mapping.example.json /etc/snmp/agentx_mapping.json

# 2. snmpd.confに以下を追加
pass_persist .1.3.6.1.4.1.53864 /usr/bin/python3 \
  /opt/project/src/deploy/agentx_pass_persist.py \
  /etc/snmp/agentx_mapping.json

# 3. 動作確認
snmpget -v2c -c public localhost 1.3.6.1.4.1.53864.1.0
```

詳細は [デプロイメントガイド](docs/05_Deployment.md) 参照。

## 🔐 セキュリティに関する注意

本番環境では以下を必須としてください：

- ✅ **SNMPv3認証** - v1/v2cではなくv3を使用
- ✅ **暗号化** - AESなどのプライバシー設定を有効化
- ✅ **ACL** - 最小権限に基づくアクセス制御
- ✅ **入力検証** - ハンドラで値の型と範囲をチェック

詳細は [セキュリティガイド](docs/06_Security.md) をご覧ください。

## 🛠️ 開発・テスト

```bash
# テスト実行
pytest tests/

# 生成コード検証
python tools/run_unit_gen_tests.py

# パフォーマンステスト
python tools/run_embedded_bench.py
```

## 📝 ライセンス

[LICENSE](LICENSE) 参照

## 🤝 貢献

Issues及びPull Requestは歓迎します。詳細は [SECURITY.md](SECURITY.md) をご覧ください。

---

このプロジェクトはMIBベースのエージェント開発のための軽量で実験的な基盤です。

