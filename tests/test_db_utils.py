import unittest
from pathlib import Path

from db_utils import get_years, run_readonly_query, search_transactions, validate_readonly_sql


DB = Path(__file__).resolve().parents[1] / "data" / "pcards.db"


class DatabaseTests(unittest.TestCase):
    def test_years_are_available_in_descending_order(self):
        self.assertEqual(get_years(DB), [2014, 2013, 2012, 2011, 2010])

    def test_vendor_search_is_field_specific(self):
        total, rows = search_transactions(
            DB, year=2014, field="Vendor", keyword="BROWNS BOTTLE SHOP"
        )
        self.assertGreater(total, 0)
        self.assertFalse(rows.empty)
        self.assertTrue(
            rows["Vendor"].str.contains("BROWNS BOTTLE SHOP", case=False).all()
        )

    def test_unsafe_sql_is_rejected(self):
        unsafe = [
            "DELETE FROM pcards",
            "DROP TABLE pcards",
            "SELECT * FROM pcards; DELETE FROM pcards",
            "PRAGMA table_info(pcards)",
        ]
        for sql in unsafe:
            with self.subTest(sql=sql), self.assertRaises(ValueError):
                validate_readonly_sql(sql)

    def test_safe_query_runs_with_a_limit(self):
        executed, rows = run_readonly_query(DB, "SELECT ID, Amount FROM pcards")
        self.assertIn("LIMIT 500", executed)
        self.assertEqual(len(rows), 500)


if __name__ == "__main__":
    unittest.main()
