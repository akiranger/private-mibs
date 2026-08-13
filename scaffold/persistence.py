"""
SQLite + Redis の軽量アダプタ。環境に合わせて拡張して使う。
依存: redis (pip install redis)
"""
import sqlite3
import json
import os

try:
    import redis
except Exception:
    redis = None


class SQLiteAdapter:
    def __init__(self, path='data/db.sqlite'):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def execute(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(sql, params)
        self._conn.commit()
        return cur

    def create_table_for_object(self, object_name, columns):
        cols = ', '.join([f'"{k}" {v}' for k, v in columns.items()])
        sql = f'CREATE TABLE IF NOT EXISTS "{object_name}" (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})'
        self.execute(sql)

    def upsert(self, table, data, unique_cols=None):
        keys = list(data.keys())
        placeholders = ','.join('?' for _ in keys)
        sql = f'INSERT INTO "{table}" ({",".join(keys)}) VALUES ({placeholders})'
        return self.execute(sql, tuple(data[k] for k in keys))

    def query_all(self, table):
        cur = self.execute(f'SELECT * FROM "{table}"')
        return [dict(row) for row in cur.fetchall()]


class RedisAdapter:
    def __init__(self, url='redis://localhost:6379/0'):
        if redis is None:
            raise RuntimeError('redis library not installed')
        self.client = redis.from_url(url)

    def set(self, key, value):
        self.client.set(key, json.dumps(value))

    def get(self, key):
        v = self.client.get(key)
        if not v:
            return None
        return json.loads(v)


if __name__ == '__main__':
    # quick demo
    db = SQLiteAdapter(':memory:')
    db.create_table_for_object('ifTable', {'ifIndex': 'INTEGER', 'ifDescr': 'TEXT'})
    db.upsert('ifTable', {'ifIndex': 1, 'ifDescr': 'eth0'})
    print(db.query_all('ifTable'))
