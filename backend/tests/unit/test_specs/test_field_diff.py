"""field_diff 单元测试"""
from app.modules.test_specs.domain.field_diff import compute_field_changes


def test_compute_field_changes_modified():
    old = {"title": "A", "priority": "P2"}
    new = {"title": "B", "priority": "P2"}
    changes = compute_field_changes(old, new)
    assert len(changes) == 1
    assert changes[0]["field"] == "title"
    assert changes[0]["change_type"] == "modified"
    assert changes[0]["old_value"] == "A"
    assert changes[0]["new_value"] == "B"


def test_compute_field_changes_create():
    new = {"title": "New case", "priority": "P1", "tags": ["a"]}
    changes = compute_field_changes(None, new)
    fields = {c["field"] for c in changes}
    assert "title" in fields
    assert "priority" in fields
    assert "tags" in fields
    assert all(c["change_type"] == "added" for c in changes)


def test_compute_field_changes_tags_list():
    old = {"tags": ["a", "b"]}
    new = {"tags": ["a", "c"]}
    changes = compute_field_changes(old, new)
    assert len(changes) == 1
    assert changes[0]["field"] == "tags"
    assert changes[0]["change_type"] == "modified"


def test_compute_field_changes_catalog_path():
    old = {"catalog_path": ["regression", "perf"]}
    new = {"catalog_path": ["regression", "stress"]}
    changes = compute_field_changes(old, new)
    assert len(changes) == 1
    assert changes[0]["field"] == "catalog_path"


def test_compute_field_changes_steps_reorder():
    step_a = {"step_id": "a", "name": "A", "action": "do", "expected": "ok"}
    step_b = {"step_id": "b", "name": "B", "action": "do", "expected": "ok"}
    old = {"steps": [step_a, step_b]}
    new = {"steps": [step_b, step_a]}
    changes = compute_field_changes(old, new)
    assert len(changes) == 1
    assert changes[0]["field"] == "steps"
    assert changes[0]["change_type"] == "modified"


def test_compute_field_changes_steps_added_on_create():
    new = {
        "title": "case",
        "steps": [{"step_id": "s1", "name": "N", "action": "A", "expected": "E"}],
    }
    changes = compute_field_changes(None, new)
    assert any(c["field"] == "steps" and c["change_type"] == "added" for c in changes)
