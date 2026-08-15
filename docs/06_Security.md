# セキュリティガイド

本番環境での必須セキュリティ設定。

## ⚠️ 重要な原則

**本番環境では以下を必須としてください**:

```
✅ SNMPv3 を使用（v1/v2c は使用禁止）
✅ 認証・暗号化を有効化
✅ ACL でアクセス制御を実装
✅ 入力検証をハンドラで実装
✅ 監査ログを記録
✅ 定期的なセキュリティ監査を実施
```

---

## 1️⃣ SNMPv3 認証・暗号化

### 1.1 SNMPv1/v2c の危険性

| プロトコル | 認証 | 暗号化 | 推奨 |
|-----------|------|--------|------|
| **v1** | なし | なし | ❌ 廃止推奨 |
| **v2c** | コミュニティ文字列 | なし | ❌ テスト用のみ |
| **v3** | ユーザ認証 | サポート | ✅ 本番必須 |

### 1.2 SNMPv3 セットアップ

#### モード1: pysnmp エージェント

```bash
# ユーザ登録（開発用）
python -c "
from src.runtime import pysnmp_agent

# 認証のみ（MD5 + 認証）
pysnmp_agent.register_usm_user(
    username='monitor',
    auth_protocol='MD5',
    auth_key='monitor123'
)

# 認証 + 暗号化（推奨）
pysnmp_agent.register_usm_user(
    username='admin',
    auth_protocol='SHA',     # SHA > MD5
    auth_key='SecurePass123',
    priv_protocol='AES',     # AES > DES
    priv_key='PrivateKey456'
)
"

# エージェント起動
python src/runtime/pysnmp_agent.py --port 161 --snmpv3

# クライアントからアクセス
snmpget -v3 -u admin -a SHA -A SecurePass123 \
  -x AES -X PrivateKey456 \
  localhost 1.3.6.1.4.1.XXXXX.1.0
```

#### モード2: snmpusm コマンド（net-snmp）

```bash
# ローカルでユーザを登録
sudo snmpusm -v3 -u root -a SHA -A root_auth_key \
  localhost create admin

# エンジン ID を確認
snmpget -v3 -u admin -a SHA -A admin_auth_key \
  localhost 1.3.6.1.2.1.1.1.0

# ローカルでセキュア設定
echo "usmUserEngineID 0x80004fb8057c7f" | \
  snmpusm -v3 -u root localhost delete admin

# 暗号化を有効化
snmpusm -v3 -u root -x AES \
  localhost create admin
```

#### モード3: snmpd.conf（静的ユーザ）

```bash
# /etc/snmp/snmpd.conf に追加

# USM ユーザ登録
usmUser 1 3 0x80001f888005 admin auth 0x12345678901234567890 priv 0xabcdef
# パラメータ:
#   1           = engineID version
#   3           = SNMP version
#   0x80001f... = エンジンID
#   admin       = ユーザ名
#   auth        = 認証パスワード（16進数）
#   priv        = プライバシーパスワード（16進数）
```

### 1.3 認証・暗号化プロトコルの選択

#### 認証プロトコル

| プロトコル | 強度 | 推奨 | 互換性 |
|-----------|------|------|--------|
| **NONE** | - | ❌ | - |
| **MD5** | 弱 | ⚠️ | 高 |
| **SHA** | 中 | ✅ | 中 |
| **SHA-224/256** | 強 | ✅ | 低 |

#### 暗号化プロトコル

| プロトコル | 強度 | 推奨 | 備考 |
|-----------|------|------|------|
| **NONE** | - | ❌ | - |
| **DES** | 弱 | ❌ | 廃止推奨 |
| **AES** | 強 | ✅ | 現代標準 |
| **AES-192/256** | 非常に強 | ✅ | サーバ負荷注意 |

**推奨組み合わせ**:
```
認証: SHA
暗号化: AES-128

最高セキュリティ:
認証: SHA-256
暗号化: AES-256
```

---

## 2️⃣ アクセス制御（ACL）

### 2.1 snmpd.conf での ACL 設定

#### パターン1: 読取専用（監視用）

```bash
# /etc/snmp/snmpd.conf

# コミュニティ定義
com2sec readonly_users 192.168.1.0/24 public

# グループ定義
group ROGroup v2c readonly_users

# ビュー定義（読取範囲）
view system_view included .1.3.6.1.2.1.1
view system_view included .1.3.6.1.2.1.25

# アクセス制御
access ROGroup "" any noauth exact system_view none none
```

#### パターン2: 読取・書込（管理用）

```bash
# SNMPv3 用 ACL

# ユーザ定義
usmUser 1 3 0x80001f888005 admin auth 0x... priv 0x...

# グループ定義
group RWGroup usm admin

# ビュー定義（書込可能な範囲）
view admin_view included .1.3.6.1.4.1.XXXXX

# アクセス制御
access RWGroup "" usm auth auth admin_view admin_view admin_view
#                                 ↑読取  ↑書込  ↑作成
```

#### パターン3: OID レベルの制御

```bash
# 特定 OID のみ読取許可

view monitoring included .1.3.6.1.4.1.XXXXX.1  # 読取許可
view monitoring excluded .1.3.6.1.4.1.XXXXX.2  # 読取拒否

access ROGroup "" any noauth exact monitoring none none
```

### 2.2 ハンドラレベルの ACL（Python）

```python
# src/deploy/generated_handlers/myScalar.py

# ACL マッピング
ACL_RULES = {
    'monitor': {'read': ['myScalar'], 'write': []},
    'admin': {'read': ['myScalar'], 'write': ['myScalar']},
}

def check_acl(ctx, operation='read'):
    """アクセス制御チェック"""
    principal = ctx.get('user', 'unknown')
    rules = ACL_RULES.get(principal, {})
    
    if operation == 'read':
        return 'myScalar' in rules.get('read', [])
    elif operation == 'write':
        return 'myScalar' in rules.get('write', [])
    
    return False

def get_myScalar(ctx):
    """読取ハンドラ（ACL チェック付き）"""
    if not check_acl(ctx, 'read'):
        raise PermissionError(f"User {ctx.get('user')} cannot read myScalar")
    
    db = ctx.get('db')
    result = db.query('myScalar_table', 'id=1')
    return result['value'] if result else None

def set_myScalar(ctx, value):
    """書込ハンドラ（ACL チェック付き）"""
    if not check_acl(ctx, 'write'):
        raise PermissionError(f"User {ctx.get('user')} cannot write myScalar")
    
    # 入力検証
    if not isinstance(value, int):
        raise TypeError(f"Expected int, got {type(value).__name__}")
    
    db = ctx.get('db')
    db.upsert('myScalar_table', {'value': value})
    
    # 監査ログ
    audit_log(ctx, 'SET', 'myScalar', None, value)
    
    return True
```

---

## 3️⃣ 入力検証

### 3.1 型チェック

```python
def validate_integer(value, min_val=None, max_val=None):
    """整数値の検証"""
    if not isinstance(value, int):
        raise TypeError(f"Expected int, got {type(value).__name__}")
    
    if min_val is not None and value < min_val:
        raise ValueError(f"Value {value} < minimum {min_val}")
    
    if max_val is not None and value > max_val:
        raise ValueError(f"Value {value} > maximum {max_val}")
    
    return True

def validate_string(value, max_length=None, pattern=None):
    """文字列の検証"""
    if not isinstance(value, str):
        raise TypeError(f"Expected str, got {type(value).__name__}")
    
    if max_length and len(value) > max_length:
        raise ValueError(f"String length {len(value)} > {max_length}")
    
    if pattern:
        import re
        if not re.match(pattern, value):
            raise ValueError(f"String does not match pattern {pattern}")
    
    return True

# 使用例
def set_deviceName(ctx, value):
    """デバイス名を設定（検証付き）"""
    validate_string(value, max_length=256, pattern=r'^[a-zA-Z0-9_-]+$')
    
    db = ctx['db']
    db.upsert('config', {'key': 'device_name', 'value': value})
    return True
```

### 3.2 SQL インジェクション対策

```python
# ❌ 危険: SQL インジェクション脆弱性あり
def get_bad(ctx, username):
    db = ctx['db']
    # 直接文字列連結は危険!
    query = f"SELECT * FROM users WHERE name='{username}'"
    return db.execute(query)

# ✅ 安全: プリペアドステートメント使用
def get_good(ctx, username):
    db = ctx['db']
    # SQLiteAdapter はプリペアドステートメント対応
    return db.query('users', f"name=?", (username,))
```

### 3.3 コマンドインジェクション対策

```python
# ❌ 危険: コマンドインジェクション脆弱性
def get_bad_exec(ctx):
    import subprocess
    user_input = ctx.get('param')
    cmd = f"ls {user_input}"
    subprocess.run(cmd, shell=True)  # 危険!

# ✅ 安全: 引数を分離
def get_good_exec(ctx):
    import subprocess
    user_input = ctx.get('param')
    subprocess.run(['ls', user_input], shell=False)  # 安全
```

---

## 4️⃣ 監査ログ

### 4.1 ハンドラレベルのログ

```python
# src/runtime/persistence.py に追加

def audit_log(ctx, operation, oid, old_value, new_value):
    """監査ログ記録"""
    from datetime import datetime
    
    db = ctx.get('db')
    principal = ctx.get('user', 'unknown')
    client_addr = ctx.get('client_addr', 'unknown')
    
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'principal': principal,
        'client_addr': str(client_addr),
        'operation': operation,
        'oid': oid,
        'old_value': str(old_value),
        'new_value': str(new_value),
    }
    
    # audit_log テーブルに記録
    db.upsert('audit_log', log_entry)
    
    # ログレベル INFO で出力
    import logging
    logger = logging.getLogger('snmp_agent')
    logger.info(f"AUDIT: {operation} {oid} by {principal}")

# 使用例
def set_myScalar(ctx, value):
    db = ctx['db']
    old_result = db.query('myScalar_table', 'id=1')
    old_value = old_result['value'] if old_result else None
    
    # 更新
    db.upsert('myScalar_table', {'value': value})
    
    # 監査ログ記録
    audit_log(ctx, 'SET', '1.3.6.1.4.1.XXXXX.1.0', old_value, value)
    
    return True
```

### 4.2 ログローテーション

```bash
# /etc/logrotate.d/snmp-audit に設定

/var/log/snmp-audit.log {
    daily                   # 日次ローテーション
    rotate 30              # 30 日分保持
    compress               # gzip 圧縮
    delaycompress         # 遅延圧縮
    notifempty            # 空ファイルはスキップ
    create 0600 snmp snmp # ファイル再作成
}
```

### 4.3 ログ分析

```bash
# 監査ログをクエリ
sqlite3 /data/db.sqlite \
  "SELECT timestamp, principal, operation, oid FROM audit_log WHERE timestamp > datetime('now', '-1 day')"

# 失敗したアクセスを監視
sqlite3 /data/db.sqlite \
  "SELECT * FROM audit_log WHERE operation='DENIED' ORDER BY timestamp DESC LIMIT 10"
```

---

## 5️⃣ ネットワークセキュリティ

### 5.1 ファイアウォール設定

```bash
# SNMP ポート（161/UDP）を制限

# iptables 例
sudo iptables -A INPUT -p udp --dport 161 \
  -s 192.168.1.0/24 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 161 -j DROP

# firewalld 例
sudo firewall-cmd --permanent --add-rich-rule=\
'rule family="ipv4" protocol="udp" port protocol="udp" port="161" source address="192.168.1.0/24" accept'
```

### 5.2 VPN/SSH トンネル

```bash
# SNMP をローカルホストに限定し、SSH トンネル経由でアクセス

# snmpd.conf
agentAddress udp:127.0.0.1:161

# クライアント側で SSH トンネル作成
ssh -L 1161:localhost:161 remote_host

# トンネル経由でアクセス
snmpget -v3 -u admin localhost:1161 ...
```

---

## 6️⃣ 本番環境チェックリスト

```yaml
セキュリティチェックリスト:

認証・暗号化:
  ✅ SNMPv3 を有効化
  ✅ SHA 以上の認証プロトコルを使用
  ✅ AES 以上の暗号化プロトコルを使用
  ✅ デフォルト認証情報を変更

アクセス制御:
  ✅ snmpd.conf で ACL を設定
  ✅ ハンドラレベルの ACL を実装
  ✅ 最小権限の原則を適用
  ✅ 定期的に権限を見直し

入力検証:
  ✅ 全ハンドラで型チェック
  ✅ 範囲チェック実装
  ✅ SQL インジェクション対策
  ✅ コマンドインジェクション対策

ログ・監査:
  ✅ 監査ログを全ハンドラで記録
  ✅ ログローテーション設定
  ✅ 失敗のログ記録
  ✅ 定期的にログを分析

ネットワーク:
  ✅ ファイアウォール設定
  ✅ 管理ネットワークを隔離
  ✅ SSH トンネルでアクセス制御
  ✅ DDoS 対策を実装

運用・保守:
  ✅ セキュリティパッチ適用計画
  ✅ 侵入検知システムを導入
  ✅ セキュリティ監査を定期実施
  ✅ インシデント対応計画作成
```

---

## 7️⃣ よくある脆弱性と対策

| 脆弱性 | 原因 | 対策 |
|--------|------|------|
| **認証なし** | v1/v2c使用 | SNMPv3 を有効化 |
| **SQL インジェクション** | 直接文字列連結 | プリペアドステートメント |
| **コマンドインジェクション** | shell=True | subprocess に引数リスト |
| **権限昇格** | デフォルト認証情報 | 強力なパスワード設定 |
| **情報漏洩** | 暗号化なし | AES 暗号化を有効化 |
| **ログ改ざん** | ローカルストレージのみ | リモートログサーバへ送信 |

---

## 📞 緊急時対応

### セキュリティインシデント発生時

```bash
# 1. サービス停止
sudo systemctl stop snmpd

# 2. ログ収集
sudo journalctl -u snmpd > incident_log.txt
sqlite3 /data/db.sqlite ".dump audit_log" > audit_dump.sql

# 3. ネットワーク隔離
sudo iptables -A INPUT -p udp --dport 161 -j DROP

# 4. 調査
# ログを分析してインシデント原因を特定

# 5. 復旧
# パッチ適用 → サービス再起動 → 監視強化
```

---

**最終更新**: 2026年8月  
**関連**: [05_Deployment.md](05_Deployment.md)  
**責任**: 運用・セキュリティチーム
