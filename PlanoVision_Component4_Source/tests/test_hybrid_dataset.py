from copy import deepcopy
from datetime import date
import unittest

from component4.hybrid_dataset import (FEATURES, FORBIDDEN, TARGETS,
    historical_selection, chronological_audit, graph_nodes, NODE_FEATURES)


class HybridDatasetTests(unittest.TestCase):
    def test_evidence_footer_is_not_a_record(self):
        from openpyxl import Workbook
        from scripts.research_pipeline.create_hybrid_dataset import worksheet_records
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['Evidence_ID', 'Rate_LKR'])
        sheet.append(['E001', 100])
        sheet.append(['Blank means unknown, not zero'])
        self.assertEqual(worksheet_records(sheet, 'E'), [{'Evidence_ID': 'E001', 'Rate_LKR': 100}])
        terms = workbook.create_sheet('terms')
        terms.append(['Source_ID', 'Provider'])
        terms.append(['P01', 'Test provider'])
        terms.append(['Derived illustration'])
        self.assertEqual(len(worksheet_records(terms, 'P')), 1)
        workbook.close()

    def history(self):
        rows, partitions = [], []
        for i in range(40):
            year, month = 2020 + i // 12, i % 12 + 1
            rows.append({'observation_id': str(i), 'ds': f'{year:04d}-{month:02d}-01', 'y': '1',
                         'series_id': 'index', 'source_id': 'S001', 'unit': 'index', 'currency': '', 'source_quality_review': '0'})
            partitions.append({'observation_id': str(i), 'partition': 'train' if i < 28 else 'validation' if i < 34 else 'test'})
        return rows, partitions

    def test_no_outcome_or_target_in_allowlist(self):
        self.assertFalse(set(FEATURES) & (FORBIDDEN | set(TARGETS)))
        self.assertFalse(set(NODE_FEATURES) & (FORBIDDEN | set(TARGETS)))

    def test_valid_chronology(self):
        rows, partitions = self.history()
        self.assertEqual(chronological_audit(rows, partitions)[0]['train'], 28)

    def test_duplicate_date_rejected(self):
        rows, partitions = self.history()
        rows[1]['ds'] = rows[0]['ds']
        with self.assertRaises(ValueError):
            chronological_audit(rows, partitions)

    def test_missing_month_rejected(self):
        rows, partitions = self.history()
        rows.pop(15)
        partitions.pop(15)
        with self.assertRaises(ValueError):
            chronological_audit(rows, partitions)

    def test_future_train_assignment_rejected(self):
        rows, partitions = self.history()
        partitions[30]['partition'] = 'train'
        with self.assertRaises(ValueError):
            chronological_audit(rows, partitions)

    def test_mixed_units_rejected(self):
        rows, partitions = self.history()
        rows[12]['currency'] = 'LKR'
        rows[12]['unit'] = 'LKR/kg'
        with self.assertRaises(ValueError):
            chronological_audit(rows, partitions)

    def test_split_missing_observation_rejected(self):
        rows, partitions = self.history()
        with self.assertRaises(ValueError):
            chronological_audit(rows, partitions[:-1])

    def test_graph_disjoint_expenses_and_missing_masks(self):
        p = {'guests': 60, 'event_hours': 3, 'event_type': 'Corporate', 'usable_area_m2': 400,
             'seats': 60, 'tables': 10, 'stage_width_m': 3, 'stage_length_m': 3,
             'staff': 4, 'paid_hours_per_staff': 5, 'budget_score': 3,
             'retained_receipts_score': 4, 'reserve_score': .7, 'planned_cost_score': 7,
             'used_area_m2': 183}
        m = {'venue_width_m': 24, 'venue_length_m': 18, 'capacity_persons': 180,
             'seat_zone_m2': 1.5, 'minimum_margin_points': 10, 'excluded_area_m2': 32,
             'service_area_m2': 24, 'circulation_area_m2': 60}
        ledger = [{'service': name, 'planned_score': 1, 'quantity': value}
                  for name, value in [('venue_fixed', 1), ('chairs', 60), ('tables', 10),
                                       ('stage', 9), ('catering', 60), ('av', 1), ('labour', 20)]]
        nodes = graph_nodes(p, m, ledger)
        self.assertEqual(nodes[7]['planned_charge_score'], 2)
        self.assertIsNone(nodes[2]['planned_charge_score'])
        self.assertIsNone(nodes[4]['budget_score'])
        self.assertEqual(sum(r['planned_charge_score'] or 0 for r in nodes), 7)
        ledger[1]['planned_score'] = 2
        with self.assertRaises(ValueError):
            graph_nodes(p, m, ledger)


if __name__ == '__main__':
    unittest.main()
