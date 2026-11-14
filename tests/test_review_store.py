import pytest

from src.review_ui.store import Review, ReviewStore


def test_override_and_edit_metrics(tmp_path):
    s = ReviewStore(tmp_path / "reviews.jsonl")
    s.add(Review("A", "v1", "fight", "drafted", "approve", "Letter text.", "Letter text."))
    s.add(Review("B", "v1", "fight", "drafted", "accept_loss", "Letter.", ""))           # override
    s.add(Review("C", "v1", "escalate", "brief_only", "accept_loss"))                     # resolution, not override
    s.add(Review("D", "v1", "escalate", "drafted", "edit_and_approve", "Old wording here.", "New wording entirely."))
    s.add(Review("A", "v1", "fight", "drafted", "edit_and_approve", "Letter text.", "Letter text, edited."))  # latest wins
    m = s.metrics()
    assert m["reviewed"] == 4 and m["fights_reversed"] == 1 and m["override_rate"] == 0.25
    assert m["letters_sent"] == 2 and m["letter_edit_rate"] == 1.0
    assert m["escalations_accepted"] == 1 and m["escalations_contested"] == 1


def test_unknown_action_rejected():
    with pytest.raises(ValueError):
        Review("A", "v1", "fight", "drafted", "submit")
