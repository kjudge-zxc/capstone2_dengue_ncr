from src.priority import assign_priority_tier


def test_priority_when_both_conditions_are_true():
    assert assign_priority_tier(True, True) == "Priority"


def test_watch_when_only_top_third_is_true():
    assert assign_priority_tier(True, False) == "Watch"


def test_watch_when_only_incidence_condition_is_true():
    assert assign_priority_tier(False, True) == "Watch"


def test_stable_when_both_conditions_are_false():
    assert assign_priority_tier(False, False) == "Stable"