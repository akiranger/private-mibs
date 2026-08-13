JSON スキーマ仕様（簡易）

このリポジトリで生成される MIB スキーマ JSON のフィールド説明（現状の text-parser/pysmi-parser共通フォーマットの最小仕様）

トップレベル
- mib: MIB ファイル名
- objects: オブジェクト配列

オブジェクト項目（例）
- name: オブジェクト名（文字列）
- kind: 'scalar' | 'table' | 'entry' | 'column'（解析結果により設定）
- raw: 解析したブロックの生テキスト（可能な場合）
- syntax: SYNTAX の文字列表現（Integer32, OCTET STRING, SEQUENCE OF MyEntry など）
- access: MAX-ACCESS を単語で表したもの（read-only, read-write, not-accessible 等）
- description: DESCRIPTION の内容（省略される場合あり）
- oid_assignment: ::= { parent n } の右辺テキスト（名前または数値）
- entry_type: table の場合に参照されるエントリ名（SEQUENCE OF のエントリ）
- fields: entry の場合、配列で各フィールド {name, type}

注記
- この仕様は最小限の互換性を保つ目的で設計されています。pysmi/pysnmp による抽出が成功すれば、より正確な OID（ドット表記）や型オブジェクト情報が追加されます。
- generator は現状このスキーマを元に単純なハンドラを生成します。将来的な拡張で、索引（INDEX）と複数カラムPK、OID順序の考慮を追加します。
