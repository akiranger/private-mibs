# デプロイメントガイド

本番環境での運用方法。3つの実行パターンから選択してください。

## 🎯 実行パターンの比較

| パターン | 難易度 | 性能 | 本番対応 | 推奨用途 |
|---------|--------|------|---------|---------|
| **パターン1: ローカル実行** | ⭐ | 低 | ❌ | 開発・デバッグ |
| **パターン2: pysnmp** | ⭐⭐ | 中 | ⭐ | プロトタイプ検証 |
| **パターン3: pass_persist** | ⭐⭐⭐ | 高 | ✅ | 本番運用 |

---

## 📌 パターン1: ローカル実行（開発向け）

### セットアップ不要

```bash
python src/runtime/agentx_demo.py myScalar get
```

**メリット**:
- セットアップ簡単
- デバッグ容易

**デメリット**:
- ネットワークアクセス不可
- SNMP 対応なし
- 本番では使用不可

---

## 🐍 パターン2: pysnmp エージェント（プロトタイプ向け）

### 2.1 インストール

```bash
pip install pysnmp redis
```

### 2.2 プロトタイプエージェント起動

```bash
python src/runtime/pysnmp_agent.py --port 161 --addr 0.0.0.0
```

**オプション**:

| オプション | 説明 | 例 |
|-----------|------|-----|
| `--port` | バインドポート（デフォルト161） | `--port 1611` |
| `--addr` | バインドアドレス | `--addr 127.0.0.1` |
| `--snmpv3` | SNMPv3 を有効化 | `--snmpv3` |

### 2.3 SNMP クライアントからアクセス

#### SNMPv2c（デバッグ用）

```bash
# GET
snmpget -v2c -c public localhost 1.3.6.1.4.1.XXXXX.1.0

# GETNEXT
snmpgetnext -v2c -c public localhost 1.3.6.1.4.1.XXXXX

# WALK
snmpwalk -v2c -c public localhost 1.3.6.1.4.1.XXXXX
```

#### SNMPv3（推奨）

```bash
# ユーザを事前登録（詳細: 06_Security.md）
python -c "
from src.runtime import pysnmp_agent
pysnmp_agent.register_usm_user(
    'admin', 
    auth_protocol='SHA', 
    auth_key='password123', 
    priv_protocol='AES', 
    priv_key='secret_key456'
)
"

# GET（SNMPv3）
snmpget -v3 -u admin -a SHA -A password123 \
  -x AES -X secret_key456 \
  localhost 1.3.6.1.4.1.XXXXX.1.0
```

### 2.4 pysnmp エージェント設定例

**ファイル**: `src/runtime/pysnmp_agent.py`

```python
import logging
from pysnmp.hlapi import *
from src.runtime.persistence import SQLiteAdapter

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('pysnmp_agent')

def setup_agent(port=161, addr='0.0.0.0', snmpv3=False):
    """pysnmp エージェントのセットアップ"""
    
    # DB 初期化
    db = SQLiteAdapter('data/db.sqlite')
    
    # OID → ハンドラマッピング
    OID_MAP = {
        '1.3.6.1.4.1.XXXXX.1.0': 'myScalar',
        '1.3.6.1.4.1.XXXXX.2': 'myTable',
    }
    
    # エージェント起動
    from pysnmp.entity import engine, config
    from pysnmp.entity.rfc3413 import cmdrsp, context
    
    snmpEngine = engine.SnmpEngine()
    
    if snmpv3:
        # SNMPv3 ユーザ登録
        config.addV3User(
            snmpEngine, 'admin',
            config.usmHMACSHAAuthProtocol, 'password123',
            config.usmAesCfb128Protocol, 'secret_key456'
        )
    else:
        # SNMPv2c コミュニティ設定
        config.addV1System(snmpEngine, 'public', 'public')
    
    # リスナ設定
    config.addSocketTransport(
        snmpEngine,
        udpTransport.UdpTransport().openServerMode(
            ('0.0.0.0', port)
        )
    )
    
    # コンテキスト設定
    snmpContext = context.SnmpContext(snmpEngine)
    
    # レスポンダ設定
    cmdrsp.GetCommandResponder(snmpEngine, snmpContext)
    cmdrsp.SetCommandResponder(snmpEngine, snmpContext)
    
    logger.info(f"Agent started on {addr}:{port}")
    snmpEngine.transportDispatcher.jobStarted(1)
    snmpEngine.transportDispatcher.runDispatcher()

if __name__ == '__main__':
    setup_agent(port=161, snmpv3=False)
```

---

## 🔌 パターン3: pass_persist（本番向け）

net-snmp(snmpd)と連携する本番向けセットアップ。

### 3.1 環境準備

#### Linux（Debian/Ubuntu）

```bash
# net-snmp をインストール
sudo apt-get install snmpd snmp-mibs-downloader

# サービスを停止（設定中）
sudo systemctl stop snmpd
```

#### Linux（Red Hat/CentOS）

```bash
sudo yum install net-snmp net-snmp-utils
sudo systemctl stop snmpd
```

### 3.2 マッピングファイルを作成

**ファイル**: `/etc/snmp/agentx_mapping.json`

```json
{
  "1.3.6.1.4.1.53864.1.0": "myScalar",
  "1.3.6.1.4.1.53864.2.0": "otherScalar"
}
```

リポジトリの例をコピー：

```bash
sudo cp src/deploy/agentx_mapping.example.json \
  /etc/snmp/agentx_mapping.json

# OID を編集
sudo vim /etc/snmp/agentx_mapping.json
```

### 3.3 snmpd.conf を設定

**ファイル**: `/etc/snmp/snmpd.conf`

基本設定：

```bash
# アクセス制御（v2c）
com2sec readonly default public
group MyROGroup v2c readonly
view all included .1
access MyROGroup "" any noauth exact all none none

# pass_persist 設定
pass_persist .1.3.6.1.4.1.53864 \
  /usr/bin/python3 /opt/project/src/deploy/agentx_pass_persist.py \
  /etc/snmp/agentx_mapping.json
```

### 3.4 ハンドラをデプロイ

```bash
# ハンドラを生成
python src/mib/generator.py src/mib/resources/example/example_schema.json \
  src/deploy/generated_handlers

# ハンドラディレクトリをコピー
sudo cp -r src/deploy/generated_handlers \
  /opt/project/src/deploy/

# 権限設定
sudo chown -R snmp:snmp /opt/project/src/deploy
```

### 3.5 ヘルパースクリプトの動作確認

**ローカルテスト**:

```bash
# スタンドアロン実行で確認
echo -e "PING\nGET 1.3.6.1.4.1.53864.1.0\n" | \
  python3 src/deploy/agentx_pass_persist.py \
  /etc/snmp/agentx_mapping.json
```

**期待される出力**:
```
PONG
0
value
100
```

### 3.6 snmpd を起動

```bash
# 設定をテスト
sudo snmpd -T -C -c /etc/snmp/snmpd.conf

# 起動
sudo systemctl start snmpd

# ステータス確認
sudo systemctl status snmpd
```

### 3.7 動作確認

```bash
# ローカルでテスト（SNMPv2c）
snmpget -v2c -c public localhost 1.3.6.1.4.1.53864.1.0

# 期待される出力:
# iso.3.6.1.4.1.53864.1.0 = INTEGER: 100
```

### 3.8 systemd での自動起動

```bash
# systemd ユニットを作成
sudo tee /etc/systemd/system/snmpd-custom.service > /dev/null <<EOF
[Unit]
Description=Net-SNMP Agent with pass_persist
After=network.target

[Service]
Type=forking
ExecStart=/usr/sbin/snmpd -c /etc/snmp/snmpd.conf
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=5s
User=snmp
Group=snmp

[Install]
WantedBy=multi-user.target
EOF

# 有効化
sudo systemctl daemon-reload
sudo systemctl enable snmpd-custom.service
sudo systemctl start snmpd-custom.service

# ステータス確認
sudo systemctl status snmpd-custom.service
```

---

## 🔐 セキュリティ設定（本番必須）

詳細は [06_Security.md](06_Security.md) を参照。

### 最小要件

```bash
# SNMPv3 ユーザ登録（snmpusm コマンド）
sudo snmpusm -v3 -u root -a SHA -A password123 \
  localhost create admin

# ACL 設定
sudo vim /etc/snmp/snmpd.conf
# view adminView included .1
# access adminGroup "" usm auth-crypt exact adminView none none
```

---

## 📊 本番環境チェックリスト

```
本番デプロイ前チェックリスト
================================

□ セキュリティ
  □ SNMPv3 認証・暗号化を有効化
  □ ACL でアクセス制御を設定
  □ 管理ネットワークを隔離
  
□ 性能・運用
  □ DB バックアップ戦略を定義
  □ ログローテーション設定
  □ 監視・アラート設定
  
□ テスト
  □ 本番環境で動作確認
  □ フェイルオーバーテスト
  □ 性能テスト実施

□ ドキュメント
  □ 運用マニュアル作成
  □ トラブルシューティング記載
  □ 緊急連絡先明記
```

---

## 🐛 トラブルシューティング

### Q: pass_persist が起動しない

**A**: ログを確認：

```bash
# snmpd ログ確認
sudo journalctl -u snmpd -f

# ヘルパー直接実行
python3 src/deploy/agentx_pass_persist.py /etc/snmp/agentx_mapping.json
```

### Q: OID が見つからない

**A**: マッピングファイルと snmpd.conf を確認：

```bash
# マッピング確認
cat /etc/snmp/agentx_mapping.json

# OID プレフィックス確認
snmpwalk -v2c -c public localhost 1.3.6.1.4.1.53864
```

### Q: 権限エラー

**A**: ファイル権限を確認：

```bash
# ハンドラディレクトリ
ls -la /opt/project/src/deploy/generated_handlers/

# snmp ユーザで実行可能か
sudo -u snmp python3 /opt/project/src/deploy/agentx_pass_persist.py \
  /etc/snmp/agentx_mapping.json
```

### Q: レスポンスが遅い

**A**: パフォーマンス最適化：

```bash
# DB のインデックスを確認
sqlite3 /data/db.sqlite ".indices"

# 遅いクエリを特定
sqlite3 /data/db.sqlite "EXPLAIN QUERY PLAN SELECT ..."

# インデックスを追加
sqlite3 /data/db.sqlite "CREATE INDEX idx_status ON myTable(status)"
```

---

## 📈 監視・保守

### ログ管理

```bash
# snmpd ログを syslog へ
sudo vim /etc/snmp/snmpd.conf
# logOption -LSyslog:LOG_DAEMON

# ログレベル調整
# logOption -Lf /var/log/snmpd.log
# logOption -Le
```

### バックアップ戦略

```bash
# 日次バックアップ
0 2 * * * cp /data/db.sqlite /backup/db-$(date +\%Y\%m\%d).sqlite

# 7 日分保持
find /backup -name "db-*.sqlite" -mtime +7 -delete
```

### 監視スクリプト（例）

```bash
#!/bin/bash
# snmpd ヘルスチェック

TIMEOUT=5
OID="1.3.6.1.4.1.53864.1.0"
COMMUNITY="public"

if timeout $TIMEOUT snmpget -v2c -c $COMMUNITY localhost $OID > /dev/null; then
    echo "OK"
    exit 0
else
    echo "CRITICAL: snmpd not responding"
    systemctl restart snmpd
    exit 2
fi
```

---

**関連**: [06_Security.md](06_Security.md) / [04_Components.md](04_Components.md)  
**最終更新**: 2026年8月
