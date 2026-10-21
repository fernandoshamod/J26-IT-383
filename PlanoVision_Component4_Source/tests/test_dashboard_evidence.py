import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from component4.dashboard_evidence import ROOT, FILES, evidence_summary, verified_bytes
from component4.planner_dashboard_http import create_server


class EvidenceTests(unittest.TestCase):
    def test_actual_archived_results(self):
        d=evidence_summary()
        self.assertEqual(d['errors']['Budget_Overrun']['counts']['FN'],17)
        self.assertEqual(len(d['curves']['Profit_Margin_Risk']),5)
        self.assertAlmostEqual(d['robustness']['coupled_adverse']['Profit_Margin_Risk']['metrics']['recall'],.3729060451565914)

    def test_all_evidence_hashes(self):
        for key, (_, digest) in FILES.items():
            self.assertEqual(hashlib.sha256(verified_bytes(key)).hexdigest(),digest)

    def test_tampering_and_missing_blocked(self):
        (ROOT/'work').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as temporary:
            root=Path(temporary)
            with self.assertRaises(OSError):evidence_summary(root)
            destination=root/FILES['errors'][0]
            destination.parent.mkdir(parents=True)
            destination.write_text('{}')
            with self.assertRaisesRegex(ValueError,'checksum_mismatch'):evidence_summary(root)
        with self.assertRaises(KeyError):verified_bytes('../../config')

    def test_http_allowlist(self):
        server=create_server(0,dashboard=object())
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            for path,status,kind in [('/api/planner/model-evidence',200,'application/json'),
                                    ('/api/planner/evidence-image/learning-curves.png',200,'image/png'),
                                    ('/api/planner/evidence-image/../../config.json',404,'application/json')]:
                conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
                conn.request('GET',path);r=conn.getresponse();body=r.read()
                self.assertEqual(r.status,status);self.assertIn(kind,r.getheader('Content-Type'))
                if path.endswith('model-evidence'):self.assertEqual(json.loads(body)['model_run'],'expense_risk_v3_1_20261016')
                conn.close()
        finally:server.shutdown();server.server_close();thread.join()
