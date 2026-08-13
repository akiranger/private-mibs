mib_parser の説明

目的

MIB (SMIv2) ファイルを読み取り、内部的に扱いやすい JSON スキーマへ変換するための最小限の実装です。将来的には pysmi を用いて堅牢な変換を行うことを想定しています。

使い方

python scaffold\mib_parser.py path/to/MIB > path/to/schema.json

現状の挙動

- pysmi がインストールされていない場合は、簡易的に "OBJECT-TYPE" を検出してオブジェクト名リストを生成します。
- pysmi を導入すると、より詳細な型情報や OID 情報を抽出できます。

pysmi を使うには

pip install pysmi

pysmi を使って正確にパースする実装例は scaffold/mib_parser.py にコメントでヒントを残しています。
