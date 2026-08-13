generator.py の説明

目的

JSON スキーマを受け取り、各 MIB オブジェクトに対応する Python のハンドラ骨格を生成します。生成モジュールは scaffold/generated_handlers/ に出力されます。

挙動

- 現状はスカラー向けの単純なテーブルを作成し、get_<name>/set_<name> 関数を出力します。
- 生成テンプレートは scaffold/generator.py の HANDLER_TMPL に定義されています。用途に応じて拡張してください。

カスタマイズ

- テーブル/カラムのマッピングルールを実装して、テーブル構造やインデックスを MIB の SEQUENCE/INDEX 情報から自動生成できます。
- SNMP のゲッターは OID ベースの検索が必要です。現状テンプレートでは簡易化しています。
