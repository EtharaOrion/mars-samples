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
        'rewrite_helpers_to_no_op',
        'remove_orjson_import_and_replace_with_stub',
        'edit_cli_main_signature',
    }
    missing = required - ids
    assert not missing, f'RL red_line coverage: forbidden_shortcut_patterns missing entries {missing}'

def test_invariants_the_fix_must_preserve_cover_helpers_and_cli():
    g = _grounding_load()
    invariants = g.get('invariants_the_fix_must_preserve') or []
    ids = {row['id'] for row in invariants}
    required = {
        'I1_helpers_still_named_from_cli',
        'I2_helpers_still_names_orjson_or_json_as_serializer',
        'I3_process_records_is_a_function',
        'I4_output_bytes_are_valid_json',
        'I5_output_records_match_expected_normalization',
    }
    missing = required - ids
    assert not missing, f'invariants_the_fix_must_preserve missing entries {missing}'

def test_visible_expected_output_matches_grounding_normalization():
    g = _grounding_load()
    visible_expected = _EXPECTED['visible_probe']['expected_output_records']
    grounding_expected = g['visible_probe_expected_output_records']
    assert visible_expected == grounding_expected, (
        f'expected_output.json visible_probe drift from grounding.yaml: '
        f'{visible_expected!r} vs {grounding_expected!r}'
    )
