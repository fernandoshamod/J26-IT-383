import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

path=Path(__file__).resolve().parents[1]/'scripts/research_pipeline/launch_financial_dashboard.py'
spec=importlib.util.spec_from_file_location('dashboard_launcher_test',path)
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def test_old_server_not_considered_ready(self):
        with patch.object(launcher,'urlopen',side_effect=[io.BytesIO(json.dumps({'version':'lkr-dashboard.0.1','mode':'research_only'}).encode()),OSError('old_server_missing_evidence')]):
            self.assertFalse(launcher.ready(8765))

    def test_current_build_and_evidence_required(self):
        responses=[io.BytesIO(json.dumps({'version':'lkr-dashboard.0.1','mode':'research_only','app_revision':'planner-extended-scope.20261019','model_run':'expense_risk_v3_1_20261016'}).encode()),
                   io.BytesIO(json.dumps({'version':'v3.1-frozen-diagnostics','model_run':'expense_risk_v3_1_20261016'}).encode()),
                   io.BytesIO((launcher.ROOT/'frontend/dist/index.html').read_bytes()),
                   io.BytesIO(json.dumps({'version':'planner-records.1'}).encode())]
        with patch.object(launcher,'urlopen',side_effect=responses):self.assertTrue(launcher.ready(8765))

    def test_old_revision_cannot_masquerade_as_current_build(self):
        responses=[io.BytesIO(json.dumps({'version':'lkr-dashboard.0.1','mode':'research_only','model_run':'expense_risk_v3_1_20261016'}).encode()),
                   io.BytesIO(json.dumps({'version':'v3.1-frozen-diagnostics','model_run':'expense_risk_v3_1_20261016'}).encode()),
                   io.BytesIO((launcher.ROOT/'frontend/dist/index.html').read_bytes()),
                   io.BytesIO(json.dumps({'version':'planner-records.1'}).encode())]
        with patch.object(launcher,'urlopen',side_effect=responses):self.assertFalse(launcher.ready(8765))
