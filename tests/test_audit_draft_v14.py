"""Constructed V14 audit controls; no benchmark implementation executes."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('independent_draft_v14',ROOT/'paper/audit_draft_v14.py')
auditor=importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)

class V14AuditControls(unittest.TestCase):
    def test_duplicate_and_nonfinite_json_refused(self):
        for raw in [b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":Infinity}']:
            with self.assertRaises(ValueError):auditor.parse(raw)

    def test_canonical_comparison_preserves_integer_boolean_and_float_types(self):
        self.assertFalse(auditor.same({'count':1},{'count':True}))
        self.assertFalse(auditor.same({'count':1},{'count':1.0}))
        self.assertTrue(auditor.same({'count':1},{'count':1}))

    def test_per_profile_inversion_precedes_even_sample_median(self):
        direct=[0.5,1.0]
        ratios=auditor.summarize_ratios([1/v for v in direct])
        self.assertEqual(ratios,{'median_ratio':1.5,'min_ratio':1.0,'max_ratio':2.0,'lower':0,'equal':1,'higher':1})
        self.assertNotEqual(ratios['median_ratio'],1/0.75)

    def test_missing_or_duplicate_table_marker_refused(self):
        for text in ['no table','**Table V14A.**\n**Table V14A.**']:
            with self.assertRaises(ValueError):auditor.table_rows(text,'**Table V14A.')

    def test_malformed_markdown_columns_and_separator_refused(self):
        for text in ['**Table V14A.**\n| A | B |\n| --- | --- |\n| 1 |',
                     '**Table V14A.**\n| A | B |\n| x | --- |\n| 1 | 2 |']:
            with self.assertRaises(ValueError):auditor.table_rows(text,'**Table V14A.')

    def test_invalid_ratio_samples_are_refused(self):
        for samples in [[],[0],[True],[-1]]:
            with self.assertRaises(ValueError):auditor.summarize_ratios(samples)

    def altered_actual_audit(self,transform,expected):
        draft=ROOT/'paper/working-draft-v14.md'
        provenance=ROOT/'paper/working-draft-v14.provenance.json'
        base=ROOT/'runs/common-cost-development/v1/retained-42927208534-1'
        cost_audit=ROOT/'runs/common-cost-development/v1/read-audit-42927208534-3/result.json'
        if not all(p.exists() for p in [draft,provenance,base/'artifact.zip',cost_audit]):
            self.skipTest('Retained development evidence unavailable; no methods rerun')
        text=transform(draft.read_text(encoding='utf-8'))
        meta=deepcopy(json.loads(provenance.read_bytes()))
        meta['paper_sha256']=hashlib.sha256(text.encode()).hexdigest()
        with tempfile.TemporaryDirectory(prefix='v14-audit-constructed-tamper-',dir=ROOT/'paper') as temp:
            folder=Path(temp);d=folder/'draft.md';p=folder/'provenance.json'
            d.write_text(text,encoding='utf-8',newline='\n');p.write_text(json.dumps(meta),encoding='utf-8',newline='\n')
            with self.assertRaisesRegex(ValueError,expected):
                auditor.audit(d,p,base,cost_audit,folder/'audit.json')
            self.assertFalse((folder/'audit.json').exists())

    def test_changed_status_count_refused_despite_rebound_paper_hash(self):
        self.altered_actual_audit(lambda text:text.replace('| legacy_direct | 330 | 270 |','| legacy_direct | 330 | 269 |',1),
                                  'V14A_complete_status_denominators_and_decisions')

    def test_changed_directional_range_refused_despite_rebound_paper_hash(self):
        def changed(text):
            header,rows=auditor.table_rows(text,'**Table V14C.')
            old=rows[0][2];new=old.split(' to ')[0]+' to 999.000000'
            return text.replace(old,new,1)
        self.altered_actual_audit(changed,'V14C_per_profile_inversion_ranges_and_strict_direction')

if __name__=='__main__':
    unittest.main()
