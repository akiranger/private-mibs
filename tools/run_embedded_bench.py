#!/usr/bin/env python
"""Simple embedded benchmark helpers: startup time and sqlite write latency."""
import time
import tracemalloc
import sqlite3
import os

def measure_startup(import_fn):
    start = time.time()
    tracemalloc.start()
    import_fn()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return time.time() - start, current, peak


def sqlite_write_benchmark(db_path='data/bench.sqlite', rows=1000):
    dirpath = os.path.dirname(db_path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    # connect and set pragmas favorable to embedded measurement
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('PRAGMA journal_mode = WAL')
    cur.execute('PRAGMA synchronous = NORMAL')
    cur.execute('CREATE TABLE IF NOT EXISTS bench (id INTEGER PRIMARY KEY, val TEXT)')
    conn.commit()
    start = time.time()
    with conn:
        for i in range(rows):
            cur.execute('INSERT INTO bench (id, val) VALUES (?, ?)', (i, 'x'*50))
    elapsed = time.time() - start
    return elapsed, rows, elapsed/rows


if __name__ == '__main__':
    print('Embedded bench: startup + sqlite write')

    def dummy_import():
        # lightweight import path: simulate agent import
        import src.runtime.pysnmp_agent as agent
        # warm a small function
        agent.OID_MAP.clear()

    t, cur, peak = measure_startup(dummy_import)
    print('startup_time_s:', t)
    print('memory_current_bytes:', cur)
    print('memory_peak_bytes:', peak)

    elapsed, rows, per = sqlite_write_benchmark(rows=200)
    print('sqlite_total_s:', elapsed, 'rows:', rows, 'per_row_s:', per)
