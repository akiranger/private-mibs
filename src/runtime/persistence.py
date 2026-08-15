"""
SQLite + Redis の軽量アダプタ。環境に合わせて拡張して使う。
依存: redis (pip install redis)
"""
import sqlite3
import json
import os
from contextlib import contextmanager

try:
    import redis
except Exception:
    redis = None


class SQLiteAdapter:
    def __init__(self, path='data/db.sqlite', pragmas=None):
        """Initialize SQLite adapter.

        pragmas: optional dict of PRAGMA names to values, e.g.
          {'journal_mode': 'WAL', 'synchronous': 'NORMAL', 'busy_timeout': 30000}
        If not provided, sane defaults for embedded use are applied.
        """
        self.path = path
        dirpath = os.path.dirname(self.path)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        # enable connection with a reasonable timeout
        self._conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        self._conn.row_factory = sqlite3.Row
        self._in_transaction = False

        # default pragmatic settings suitable for many embedded deployments
        default_pragmas = {
            'busy_timeout': 30000,    # milliseconds
            'journal_mode': 'WAL',    # allow concurrent readers during writes
            'synchronous': 'NORMAL',  # trade durability for speed on flash devices
        }
        if pragmas is None:
            pragmas = default_pragmas
        else:
            # merge defaults with provided ones
            merged = dict(default_pragmas)
            merged.update(pragmas)
            pragmas = merged

        try:
            cur = self._conn.cursor()
            # apply provided pragmas
            for k, v in pragmas.items():
                if isinstance(v, int):
                    cur.execute(f'PRAGMA {k} = {v}')
                else:
                    cur.execute(f"PRAGMA {k} = {v}")
            self._conn.commit()
        except Exception:
            # If pragmas fail, continue with defaults but log silently
            pass

    def set_pragmas(self, pragmas: dict):
        """Apply PRAGMA settings at runtime. pragmas is a dict of name->value."""
        cur = self._conn.cursor()
        for k, v in pragmas.items():
            if isinstance(v, int):
                cur.execute(f'PRAGMA {k} = {v}')
            else:
                cur.execute(f"PRAGMA {k} = {v}")
        self._conn.commit()

    def execute(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(sql, params)
        self._conn.commit()
        return cur

    def create_table_for_object(self, object_name, columns, unique_cols=None):
        """Create table for an object.

        columns: dict of name -> type (e.g. {'ifIndex': 'INTEGER'})
        unique_cols: optional list of column names that should be declared UNIQUE together
        """
        cols = ', '.join([f'"{k}" {v}' for k, v in columns.items()])
        unique_sql = ''
        if unique_cols:
            uc = ','.join([f'"{c}"' for c in unique_cols])
            unique_sql = f', UNIQUE({uc})'
        sql = f'CREATE TABLE IF NOT EXISTS "{object_name}" (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols}{unique_sql})'
        self.execute(sql)

    @contextmanager
    def transaction(self):
        cur = self._conn.cursor()
        try:
            self._in_transaction = True
            cur.execute('BEGIN')
            yield cur
        except Exception:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()
        finally:
            self._in_transaction = False

    def upsert(self, table, data, unique_cols=None):
        """Insert or update a row. If unique_cols is provided, uses ON CONFLICT to update.

        data: dict of column -> value
        unique_cols: list of column names that form the conflict target
        """
        keys = list(data.keys())
        placeholders = ','.join('?' for _ in keys)
        cols_join = ','.join([f'"{k}"' for k in keys])
        params = tuple(data[k] for k in keys)

        if unique_cols:
            uc = ','.join([f'"{c}"' for c in unique_cols])
            update_cols = [k for k in keys if k not in unique_cols]
            if update_cols:
                set_clause = ','.join([f'"{k}" = excluded."{k}"' for k in update_cols])
                sql = f'INSERT INTO "{table}" ({cols_join}) VALUES ({placeholders}) ON CONFLICT({uc}) DO UPDATE SET {set_clause}'
            else:
                # nothing to update on conflict
                sql = f'INSERT INTO "{table}" ({cols_join}) VALUES ({placeholders}) ON CONFLICT({uc}) DO NOTHING'
        else:
            sql = f'INSERT INTO "{table}" ({cols_join}) VALUES ({placeholders})'

        cur = self._conn.cursor()
        cur.execute(sql, params)
        if not getattr(self, '_in_transaction', False):
            self._conn.commit()
        return cur

    def bulk_upsert(self, table, rows, unique_cols=None):
        """Upsert multiple rows inside a single transaction to ensure atomicity."""
        if not isinstance(rows, (list, tuple)):
            raise ValueError('rows must be a list of dicts')
        with self.transaction():
            for r in rows:
                self.upsert(table, r, unique_cols=unique_cols)
        return True

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
