"""
MIB から得たスキーマ（JSON）を受け取り、ハンドラ骨格（Pythonモジュール）を生成する簡易ジェネレータ。

使い方例:
  python generator.py schema.json outdir/
"""
import sys
import os
import json

HANDLER_TMPL = '''"""Generated handler skeleton for {name}

This module provides:
- init_table() to ensure DDL exists
- get_{name}(oid=None)
- set_{name}(oid_or_index, value)
- next_oid(current_oid) : simple next-row support for GETNEXT
"""

from ..persistence import SQLiteAdapter
import datetime

DB_PATH = 'data/db.sqlite'

def _ensure_db():
    global db
    try:
        db
    except NameError:
        db = SQLiteAdapter(DB_PATH)

# ensure table exists when module imported
try:
    _ensure_db()
    db.create_table_for_object('{name}', {columns})
except Exception:
    pass


def init_table():
    _ensure_db()
    db.create_table_for_object('{name}', {columns})


def get_{name}(oid=None, ctx=None):
    """Return value by oid/index or latest for scalars"""
    _ensure_db()
    if oid is None:
        rows = db.query_all('{name}')
        if not rows:
            return None
        return rows[-1].get('value') if 'value' in rows[-1] else rows[-1]
    # For tables, assume oid is a numeric index
    cur = db.execute('SELECT * FROM "{name}" WHERE id=?', (int(oid),))
    r = cur.fetchone()
    return dict(r) if r else None


def set_{name}(oid, value, ctx=None):
    """Insert or update. For scalars, oid may be ignored."""
    _ensure_db()
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    if {is_scalar}:
        db.upsert('{name}', {{'value': str(value), 'updated_at': now}})
        return True
    else:
        # tables: expect dict or simple value
        if isinstance(value, dict):
            db.upsert('{name}', value)
            return True
        else:
            # set single column 'value' if present
            try:
                db.upsert('{name}', {{'value': str(value), 'updated_at': now}})
                return True
            except Exception:
                return False


def next_oid_{name}(current_oid=None):
    """Return next row id after current_oid. If current_oid is None, return first id."""
    _ensure_db()
    rows = db.query_all('{name}')
    if not rows:
        return None
    ids = [r['id'] for r in rows]
    ids.sort()
    if current_oid is None:
        return ids[0]
    try:
        cur = int(current_oid)
    except Exception:
        return ids[0]
    for i in ids:
        if i > cur:
            return i
    return None
'''



def _snmp_type_to_sql(snmp_type):
    t = (snmp_type or '').lower()
    if 'integer' in t or 'int' in t:
        return 'INTEGER'
    if 'octet' in t or 'string' in t or 'oid' in t:
        return 'TEXT'
    if 'counter' in t or 'timeticks' in t or 'gauge' in t:
        return 'INTEGER'
    return 'TEXT'


def generate_handlers(schema_path, outdir):
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    os.makedirs(outdir, exist_ok=True)
    mib = os.path.splitext(os.path.basename(schema_path))[0]

    # Helper: find entry definition by name
    entries = {o.get('name'): o for o in schema.get('objects', []) if o.get('kind') in ('entry','table','scalar','column')}

    for obj in schema.get('objects', []):
        name = obj.get('name', 'unknown')
        # sanitize name to be filename-friendly
        safe_name = ''.join(c if c.isalnum() or c=='_' else '_' for c in name)
        is_scalar = (obj.get('kind') == 'scalar')
        columns = {}
        if obj.get('kind') == 'table' and obj.get('entry_type'):
            entry = entries.get(obj.get('entry_type'))
            if entry and entry.get('fields'):
                for f in entry.get('fields'):
                    col_name = f.get('name')
                    col_type = _snmp_type_to_sql(f.get('type'))
                    columns[col_name] = col_type
                # ensure id primary key
                columns = {'id': 'INTEGER PRIMARY KEY AUTOINCREMENT', **columns}
            else:
                # generic table
                columns = {'id': 'INTEGER PRIMARY KEY AUTOINCREMENT', 'value': 'TEXT', 'updated_at': 'TEXT'}
        elif obj.get('kind') == 'entry' and obj.get('fields'):
            # entry as standalone table
            cols = {}
            for f in obj.get('fields'):
                cols[f.get('name')] = _snmp_type_to_sql(f.get('type'))
            columns = {'id': 'INTEGER PRIMARY KEY AUTOINCREMENT', **cols}
            is_scalar = False
        else:
            # scalar or unknown -> single-value table
            columns = {'value': 'TEXT', 'updated_at': 'TEXT'}
            is_scalar = True

        cols_literal = '{' + ', '.join(f"'{k}': '{v}'" for k, v in columns.items()) + '}'

        fname = os.path.join(outdir, f'{safe_name}.py')
        with open(fname, 'w', encoding='utf-8') as fh:
            fh.write(HANDLER_TMPL.format(name=safe_name, columns=cols_literal, is_scalar=str(is_scalar)))

    # If no objects, create a placeholder
    if not schema.get('objects'):
        with open(os.path.join(outdir, f'{mib}_placeholder.py'), 'w', encoding='utf-8') as fh:
            fh.write(HANDLER_TMPL.format(name='placeholder', columns="{'value':'TEXT','updated_at':'TEXT'}", is_scalar='True'))


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python generator.py schema.json outdir', file=sys.stderr)
        sys.exit(2)
    generate_handlers(sys.argv[1], sys.argv[2])
