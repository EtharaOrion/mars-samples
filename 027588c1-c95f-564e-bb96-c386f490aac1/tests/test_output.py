# GENERATED SECTION. DO NOT HAND-EDIT.
# Compiled from solution/rubrics.json per seed/contract.yaml#rubric.
# Generator: solution/recompute.py.
import json
import pathlib
import pytest

try:
    import yaml
except ImportError:
    pytest.skip('pyyaml missing; rubric grounding-consistency check unavailable', allow_module_level=True)

HERE = pathlib.Path(__file__).resolve().parent
RUBRICS_JSON = HERE.parent / 'solution' / 'rubrics.json'
GROUNDING_YAML = HERE.parent / 'solution' / 'grounding.yaml'
EXPECTED_OUTPUT_JSON = HERE / 'expected_output.json'

if not RUBRICS_JSON.exists():
    pytest.skip(f'rubrics.json absent at {RUBRICS_JSON}; run solution/recompute.py first', allow_module_level=True)
if not GROUNDING_YAML.exists():
    pytest.skip(f'grounding.yaml absent at {GROUNDING_YAML}', allow_module_level=True)
if not EXPECTED_OUTPUT_JSON.exists():
    pytest.skip(f'expected_output.json absent at {EXPECTED_OUTPUT_JSON}; run solution/recompute.py first', allow_module_level=True)

_RUBRIC_DOC = json.loads(RUBRICS_JSON.read_text())
_ITEMS = _RUBRIC_DOC['items']
_COMPILED = [i for i in _ITEMS if i['mode'] == 'compiled']
_EXPECTED = json.loads(EXPECTED_OUTPUT_JSON.read_text())

def _grounding_load():
    g = yaml.safe_load(GROUNDING_YAML.read_text())
    if isinstance(g, dict) and len(g) == 1 and 'grounding' in g:
        g = g['grounding']
    return g

def _walk_path(g, path_steps):
    node = g
    for step in path_steps:
        node = node[step]
    return node

@pytest.mark.parametrize('item', _COMPILED, ids=lambda i: i['id'])
def test_compiled_rubric_item_grounding_consistency(item):
    g = _grounding_load()
    actual = _walk_path(g, item['grounding_path'])
    expected = item['expected_literal']
    display = item.get('grounding_path_display', item['grounding_path'])
    assert actual == expected, (
        f"{item['id']} at grounding path {display}: "
        f"expected {expected!r}, got {actual!r}"
    )

def test_compilation_floor_holds():
    total = len(_ITEMS)
    if total == 0:
        pytest.skip('rubric has zero items')
    compiled = len(_COMPILED)
    share = compiled / total
    floor = _RUBRIC_DOC.get('compilation_floor', 0.80)
    assert share >= floor, (
        f'compiled weight share {share:.3f} below contract floor {floor:.3f}; '
        f'{compiled} compiled of {total} items'
    )

def test_every_deterministically_reducible_item_is_compiled():
    for item in _ITEMS:
        if item['mode'] == 'judged':
            assert 'semantic_residue' in item, (
                f"{item['id']}: judged item must name its semantic_residue per invariant 24"
            )

def test_red_line_forbidden_shortcut_patterns_are_enumerated():
    g = _grounding_load()
    forbidden = g.get('forbidden_shortcut_patterns') or []
    ids = {row['id'] for row in forbidden}
    required = {
        'shortcut_delete_top_level_await_from_src_index_ts',
        'shortcut_flip_package_type_to_commonjs',
        'shortcut_hardcode_dist_cjs_index_cjs_to_fake_the_expected_values',
        'shortcut_declare_require_condition_that_points_at_the_esm_entry_directly',
    }
    missing = required - ids
    assert not missing, f'RL red_line coverage: forbidden_shortcut_patterns missing entries {missing}'

def test_invariants_the_fix_must_preserve_cover_source_and_exports():
    g = _grounding_load()
    invariants = g.get('invariants_the_fix_must_preserve') or []
    ids = {row['id'] for row in invariants}
    required = {
        'I1_source_bytes_unchanged',
        'C1_consumer_bytes_unchanged',
        'I3_typescript_version_unchanged',
        'P2_package_type_module',
        'P3_exports_dual_conditions',
        'S2_cjs_entry_uses_dynamic_import',
    }
    missing = required - ids
    assert not missing, f'invariants_the_fix_must_preserve missing entries {missing}'

def test_expected_stdout_matches_grounding_lines():
    g = _grounding_load()
    lines = _EXPECTED['expected_stdout_lines']
    assert lines[0] == g['expected_stdout_line_1']
    assert lines[1] == g['expected_stdout_line_2']
    assert lines[2] == g['expected_stdout_line_3']
    assert lines[3] == g['expected_stdout_line_4']
    assert lines[4] == g['expected_stdout_line_5']
    assert _EXPECTED['expected_stdout_bytes_utf8'] == g['expected_stdout_bytes_utf8']

def test_verifier_gates_cover_source_exports_dynamic_import_and_consumer_runtime():
    g = _grounding_load()
    gates = g.get('verifier_gates_ordered') or []
    ids = {row['gate_id'] for row in gates}
    required = {
        'I1_source_bytes_sha256_check',
        'C1_consumer_bytes_sha256_check',
        'I3_typescript_version_probe',
        'P1_package_json_parseable',
        'P2_package_type_module',
        'P3_exports_dot_object',
        'E1_esm_entry_file_exists',
        'E2_cjs_entry_file_exists',
        'S2_cjs_entry_source_contains_dynamic_import_call',
        'S3_cjs_entry_source_free_of_hardcoded_output_markers',
        'R1_esm_consumer_returncode_zero',
        'R2_esm_consumer_stdout_bytes_exact',
        'R3_cjs_consumer_returncode_zero',
        'R4_cjs_consumer_stdout_bytes_exact',
    }
    missing = required - ids
    assert not missing, f'verifier_gates_ordered missing entries {missing}'
