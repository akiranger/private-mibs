snmpd.conf と systemd ユニットのサンプル

このファイルは、scaffold/agentx_pass_persist.py を snmpd と一緒に使うための具体例を示します。

1) /etc/snmp/snmpd.conf の最小サンプル

# ローカル読み取り専用（v2c, community=public）
com2sec readonly  default        public
group   MyROGroup v2c            readonly
view    all      included       .1
access  MyROGroup ""  any noauth    exact  all    none   none

# pass_persist でプライベートOIDツリーをヘルパーに委譲する例
# ここでは .1.3.6.1.4.1.53864 以下を当該プロジェクトに割り当て
pass_persist .1.3.6.1.4.1.53864 /usr/bin/python3 /opt/project/scaffold/agentx_pass_persist.py /etc/snmp/agentx_mapping.json

# ロギング（任意）
# logOption -LSyslog:LOG_DAEMON

メモ:
- 実運用では SNMPv3 を利用してください。上は検証用の最小例です。
- snmpd.conf の場所や snmpd 実行ユーザはディストリのパッケージによって異なる場合があります。

2) systemd ユニット例: snmpd（通常 snmpd パッケージにユニットが含まれます。カスタム起動が必要な場合の例）

# /etc/systemd/system/snmpd-pass-persist.service
[Unit]
Description=Net-SNMP Agent (snmpd) with pass_persist
After=network.target

[Service]
Type=simple
# -f フォアグラウンド実行、-Lo ログを標準出力へ、-C 無視既定の設定（必要に応じて調整）
ExecStart=/usr/sbin/snmpd -f -Lo -C -c /etc/snmp/snmpd.conf
Restart=on-failure
User=snmp
LimitNOFILE=4096

[Install]
WantedBy=multi-user.target

注: 多くのディストリでは /lib/systemd/system/snmpd.service が提供されます。上はカスタム構成向けの例です。

3) systemd ユニット例: agentx_pass_persist のデバッグ用（任意）

# /etc/systemd/system/agentx-pass-persist-debug.service
[Unit]
Description=AgentX pass_persist helper (debug)
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/project/scaffold/agentx_pass_persist.py /etc/snmp/agentx_mapping.json
Restart=on-failure
User=snmp
StandardInput=null

[Install]
WantedBy=multi-user.target

使い方（短く）
1. /etc/snmp/agentx_mapping.json を作る（scaffold/agentx_mapping.example.json を参照）
2. /etc/snmp/snmpd.conf に pass_persist 行を追加
3. systemctl daemon-reload
4. systemctl enable --now snmpd-pass-persist.service
5. snmpget -v2c -c public localhost 1.3.6.1.4.1.53864.1.0

トラブルシュート
- /var/log/syslog または journalctl -u snmpd-pass-persist.service を確認
- ヘルパー単体で動作確認: echo -e "PING\nGET 1.3.6.1.4.1.53864.1.0\n" | python3 scaffold/agentx_pass_persist.py scaffold/agentx_mapping.example.json

セキュリティ注意
- 上の snmpd.conf は検証用です。運用は SNMPv3 と適切なアクセス制御を必ず使用してください。
