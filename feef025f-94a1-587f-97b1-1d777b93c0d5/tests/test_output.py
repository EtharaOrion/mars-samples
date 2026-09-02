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
        'delete_replace_directive_from_root_gomod',
        'rename_root_module_to_match_local_target',
        'move_replace_target_off_local_dotdot_mylib',
        'hardcode_go_test_pass_via_stub',
    }
    missing = required - ids
    assert not missing, f'RL red_line coverage: forbidden_shortcut_patterns missing entries {missing}'

def test_invariants_the_fix_must_preserve_cover_full_set():
    g = _grounding_load()
    invariants = g.get('invariants_the_fix_must_preserve') or []
    ids = {row['id'] for row in invariants}
    required = {
        'I1_root_gomod_present',
        'I2_root_module_declaration_unchanged',
        'I3_replace_directive_still_present',
        'I4_local_replace_target_present',
        'I5_local_target_module_declaration_fixed',
        'D1_go_mod_verify_exits_zero',
        'D2_go_build_exits_zero',
        'D3_go_test_exits_zero',
    }
    missing = required - ids
    assert not missing, f'invariants_the_fix_must_preserve missing entries {missing}'

def test_authored_broken_state_matches_grounding():
    g = _grounding_load()
    authored = _EXPECTED['authored_broken_state']
    grounding_authored = g['authored_manifest_of_broken_state']
    assert authored == grounding_authored, (
        f'expected_output.json authored_broken_state drift from grounding.yaml: '
        f'{authored!r} vs {grounding_authored!r}'
    )

def test_local_target_module_path_broken_and_fixed_differ():
    g = _grounding_load()
    broken = g['local_target_module_path_broken']
    fixed = g['local_target_module_path_fixed']
    assert broken != fixed, 'local target broken and fixed module paths must differ'
    assert fixed == g['replaced_module_path'], (
        'fixed local target module must match the replaced_module_path the root project imports'
    )
