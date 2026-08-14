AgentX との統合（ガイド）

現状

- net-snmp の AgentX と直接接続するコードは含まれていません。agentx_demo.py は生成ハンドラをローカルで呼び出す模擬ツールです。

*updated:* 詳細な pass_persist ベースの統合手順は docs/agentx_integration_full.md を参照してください。

統合の選択肢

1) net-snmp の subagent を C で実装して Python ハンドラを呼ぶ
   - 高性能だが実装が複雑。Python の C 拡張や IPC（UNIX domain socket / stdin/stdout）で連携する。

2) pysnmp で完全 Python 実装のエージェントを作る
   - Agent 機能を Python だけで実装できる。学習コストはあるが移植性が高い。

3) net-snmp の exec/pass/mib mapping を使って外部プログラムを呼ぶ
   - シンプルだがパフォーマンスとスレッド制御に制約あり。

推奨（プロトタイプ）

- まずは pysnmp でプロトタイプエージェントを作り、生成ハンドラをそのまま呼び出す方法を検証する。運用では net-snmp の subagent（C）へ移行する選択肢を残す。

実装メモ

- SNMP v3 の認証/暗号化はエージェント（net-snmp または pysnmp）側で設定する。ハンドラは読取/書込のみを担当する。
- GET/SET のトランザクションは persistence.py 側で実装する（SQLite トランザクション）。
