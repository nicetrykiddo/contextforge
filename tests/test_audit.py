import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

p = Path(__file__).resolve().parents[1] / 'ctx.py'
spec = importlib.util.spec_from_file_location('cf_audit', p)
cf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf)

class AuditTest(unittest.TestCase):
    def test_audit_catches_unfilled_mission_and_missing_proof(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with contextlib.redirect_stdout(io.StringIO()):
                cf.init(type('Args', (), {'root': str(root), 'name': None,
                                         'scope': '.', 'mode': 'general'})())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                cf.audit(type('Args', (), {'root': str(root)})())
            self.assertIn('Original mission is not anchored', output.getvalue())
            self.assertIn('No verified observations', output.getvalue())
            self.assertIn('RETHINK CHECKLIST', output.getvalue())

if __name__ == '__main__':
    unittest.main()
