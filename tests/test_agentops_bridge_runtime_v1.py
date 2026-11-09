"""Runtime packaging rejects path escapes and omitted resolution edges."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from agentops_bridge_runtime_archive_v1 import check_graph, safe_name, verify_runtime


class RuntimeGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = json.loads((ROOT / 'runs/agentops-native-eligibility/bridge-runtime-preparation-v1/graph.json').read_bytes())

    def test_pinned_two_bridge_graph_is_complete(self):
        self.assertEqual(len(check_graph(self.graph)), 15)
        self.assertEqual({row['alias'] for row in self.graph['roots']}, {'a2a-to-mcp', 'mcp-a2a'})

    def test_unsafe_archive_names_rejected(self):
        for name in ('../outside', '/absolute', 'C:/absolute', 'a\\b', 'a/./b', 'a//b', ''):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_name(name)

    def test_omitted_dependency_or_optional_absence_rejected(self):
        for field in ('edges', 'missing_optional'):
            graph = copy.deepcopy(self.graph)
            graph[field].pop()
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'dependency resolution'):
                check_graph(graph)

    def test_extra_file_and_unknown_package_reference_rejected(self):
        graph = copy.deepcopy(self.graph)
        graph['files'].append(graph['files'][0])
        with self.assertRaisesRegex(ValueError, 'file list'):
            check_graph(graph)
        graph = copy.deepcopy(self.graph)
        graph['edges'][0]['to'] = 'p999'
        with self.assertRaisesRegex(ValueError, 'resolved/absent edge'):
            check_graph(graph)


@unittest.skipUnless(os.name == 'posix', 'Materialized runtime uses Linux symlinks')
class RuntimeMutationTests(unittest.TestCase):
    def test_live_bytes_extra_files_and_changed_links(self):
        with tempfile.TemporaryDirectory(prefix='runtime-mutation-') as temporary:
            root = Path(temporary)
            graph = {'schema_version': 'agentops-bridge-runtime-graph/1', 'status': 'graph_pinned_not_materialized',
                     'nodes': [], 'roots': [], 'edges': [], 'missing_optional': [], 'files': []}
            links = []
            for i, alias in enumerate(('a2a-to-mcp', 'mcp-a2a')):
                node_id = f'p{i:03d}'
                destination = f'nodes/{node_id}/package'
                raw = json.dumps({'name': alias, 'version': 'test'}).encode()
                row = {'path': 'package.json', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                graph['nodes'].append({'id': node_id, 'destination': destination, 'original_root': alias,
                                       'files': [row], 'declared_dependencies': []})
                graph['files'].append(dict(row, path=destination + '/package.json', source=alias + '/package.json'))
                graph['roots'].append({'alias': alias, 'node': node_id})
                folder = root / destination
                folder.mkdir(parents=True)
                (folder / 'package.json').write_bytes(raw)
                link = root / 'external' / alias
                link.parent.mkdir(exist_ok=True)
                target = '../' + destination
                link.symlink_to(target, target_is_directory=True)
                links.append({'path': 'external/' + alias, 'target': target, 'resolved': destination})
            graph['total_bytes'] = sum(r['bytes'] for r in graph['files'])
            raw_graph = (json.dumps(graph, indent=2) + '\n').encode()
            (root / 'graph.json').write_bytes(raw_graph)
            materialization = {'status': 'materialized_import_check_pending', 'runtime_root': str(root),
                               'graph_sha256': hashlib.sha256(raw_graph).hexdigest(), 'links': links}
            (root / 'materialization.json').write_text(json.dumps(materialization, indent=2) + '\n')
            self.assertEqual(verify_runtime(root, graph, materialization)['files'], 2)
            extra = root / 'extra.txt'
            extra.write_text('unexpected')
            with self.assertRaisesRegex(ValueError, 'enumeration'):
                verify_runtime(root, graph, materialization)
            extra.unlink()
            original = root / graph['files'][0]['path']
            old = original.read_bytes()
            original.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Changed runtime file'):
                verify_runtime(root, graph, materialization)
            original.write_bytes(old)
            link = root / links[0]['path']
            link.unlink()
            link.symlink_to('../nodes/p001/package', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'link target'):
                verify_runtime(root, graph, materialization)


if __name__ == '__main__':
    unittest.main()
