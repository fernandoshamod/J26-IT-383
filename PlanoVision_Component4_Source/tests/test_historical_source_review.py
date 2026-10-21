import unittest
from component4.historical_source_review import index_values,retail_value

def source(**changes):return {**dict(reported_week='2023-01-W4',item_raw='Anamalu',unit_raw='1 Kg.',source_file='DCSB-WRP-2023-01-W4.pdf'),**changes}
def text(row):return '4th Week of January 2023\nMain Markets in Colombo District\nAvg.Price (Rs.cts.)\n'+row

class HistoricalSourceReviewTests(unittest.TestCase):
    def test_current_price_not_change_percentage_or_previous_price(self):
        found,reason=retail_value(text('Anamalu 1 Kg. 196.32 309.52 316.50 61.2% 2.3% 250.00 350.00'),source())
        self.assertEqual(found['value'],316.50);self.assertEqual(reason,'')

    def test_unit_and_item_are_not_loosely_matched(self):
        for row in ['Anamalu 750 ml 196.32 309.52 316.50','Other Anamalu 1 Kg. 196.32 309.52 316.50']:
            self.assertIsNone(retail_value(text(row),source())[0])

    def test_duplicates_and_missing_current_value_are_unresolved(self):
        row='Anamalu 1 Kg. 196.32 309.52 316.50'
        self.assertIsNone(retail_value(text(row+'\n'+row),source())[0])
        self.assertIsNone(retail_value(text('Anamalu 1 Kg. 196.32 309.52 n.a 61.2%'),source())[0])

    def test_wrong_period_is_not_automatically_accepted(self):
        self.assertIsNone(retail_value(text('Anamalu 1 Kg. 196.32 309.52 316.50'),source(reported_week='2025-01-W4'))[0])

    def test_named_title_conflict_requires_all_current_column_evidence(self):
        body=text('Jan. Jan. 2024 Jan. 2024 Jan. Jan. 2024\nAnamalu 1 Kg. 307.54 318.00 292.61\n4th week of\nJan. 2024 compared to :')
        s=source(reported_week='2024-01-W4',source_file='DCSB-WRP-2024-01-W4.pdf')
        found,_=retail_value(body,s);self.assertEqual(found['value'],292.61);self.assertIn('conflict_retained',found['period_resolution'])
        self.assertIsNone(retail_value(body.replace('compared to','different wording'),s)[0])
        self.assertIsNone(retail_value(body,source(reported_week='2024-01-W4',source_file='other.pdf'))[0])

    def test_index_value_and_year_do_not_use_percentage_columns(self):
        rows=index_values('MOVEMENTS OF THE CCPI (Base : 2021 = 100)\n2022 January 124.3\nFebruary 125.8 1.2\n2023 January 188.6 0.5','CCPI')
        self.assertEqual(rows['2022-02-01']['value'],125.8);self.assertEqual(rows['2023-01-01']['value'],188.6)
        with self.assertRaises(ValueError):index_values('CCPI\n2022 January 124.3','CCPI')
