import pytest

from ads import GuardError, check_copy, check_no_budget, check_targeting


def test_budget_fields_are_refused():
    with pytest.raises(GuardError):
        check_no_budget({"optimization_goal": "LEAD_GENERATION", "daily_budget": 5000})
    check_no_budget({"optimization_goal": "OFFSITE_CONVERSIONS", "targeting": "{}"})


def test_special_ad_category_targeting():
    with pytest.raises(GuardError):
        check_targeting({"genders": [2]})
    with pytest.raises(GuardError):
        check_targeting({"age_min": 45})
    with pytest.raises(GuardError):
        check_targeting({"custom_audiences": [{"id": "1"}]})
    check_targeting({"geo_locations": {"countries": ["US"]}, "publisher_platforms": ["facebook"]})


@pytest.mark.parametrize("bad", [
    "We guarantee results",
    "Cut your debt by 50%",
    "Struggling with credit card debt?",
    "If you're behind on payments, we can help",
    "We understand your stress",
    "Debt-free in 24 months",
])
def test_copy_gate_blocks(bad):
    with pytest.raises(GuardError):
        check_copy(bad)


@pytest.mark.parametrize("ok", [
    "Find out if debt settlement could lower what's owed on credit cards.",
    "A free, no-obligation review of unsecured debt options. About 60 seconds.",
    "Debt settlement, explained in plain English.",
])
def test_copy_gate_allows(ok):
    check_copy(ok)
