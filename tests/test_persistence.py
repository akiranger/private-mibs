import unittest

from scaffold.persistence import SQLiteAdapter


class TestPersistence(unittest.TestCase):
    def test_upsert_with_unique_update(self):
        db = SQLiteAdapter(':memory:')
        db.create_table_for_object('t', {'k': 'INTEGER', 'v': 'TEXT'}, unique_cols=['k'])
        db.upsert('t', {'k': 1, 'v': 'a'}, unique_cols=['k'])
        rows = db.query_all('t')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['v'], 'a')
        db.upsert('t', {'k': 1, 'v': 'b'}, unique_cols=['k'])
        rows = db.query_all('t')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['v'], 'b')

    def test_upsert_do_nothing_when_only_unique(self):
        db = SQLiteAdapter(':memory:')
        db.create_table_for_object('t2', {'k': 'INTEGER'}, unique_cols=['k'])
        db.upsert('t2', {'k': 1}, unique_cols=['k'])
        db.upsert('t2', {'k': 1}, unique_cols=['k'])
        rows = db.query_all('t2')
        self.assertEqual(len(rows), 1)

    def test_transaction_rollback(self):
        db = SQLiteAdapter(':memory:')
        db.create_table_for_object('t3', {'a': 'INTEGER', 'b': 'TEXT'}, unique_cols=['a'])
        try:
            with db.transaction():
                db.upsert('t3', {'a': 1, 'b': 'x'}, unique_cols=['a'])
                raise ValueError('force')
        except ValueError:
            pass
        rows = db.query_all('t3')
        self.assertEqual(len(rows), 0)


if __name__ == '__main__':
    unittest.main()
