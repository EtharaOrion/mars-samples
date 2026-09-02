# GENERATED SECTION. DO NOT HAND-EDIT.
# Compiled from solution/rubrics.json per seed/contract.yaml#rubric.
# Generator: solution/recompute.py extended by FORGE update-run inv31.
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

if not RUBRICS_JSON.exists():
    pytest.skip(f'rubrics.json absent at {RUBRICS_JSON}; run solution/recompute.py first', allow_module_level=True)
if not GROUNDING_YAML.exists():
    pytest.skip(f'grounding.yaml absent at {GROUNDING_YAML}', allow_module_level=True)

_RUBRIC_DOC = json.loads(RUBRICS_JSON.read_text())
_ITEMS = _RUBRIC_DOC['items']
_COMPILED = [i for i in _ITEMS if i['mode'] == 'compiled']

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
