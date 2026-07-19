from src.policy import EngagementPolicy


def test_abstract_rules_never_include_raw_values() -> None:
    policy = EngagementPolicy(
        protected_values=["Amazon Web Services", "Nordics"],
        aliases={"AWS": "Amazon Web Services"},
        abstract_rules=["AWS exit from Nordics is protected"],
        allowed_purpose="strategy review",
    )

    rules = policy.to_abstract_for_judge()

    assert rules == ["[VALUE_1] exit from [VALUE_2] is protected"]
    assert all(value not in rules[0] for value in ["Amazon Web Services", "AWS", "Nordics"])


def test_aliases_receive_the_canonical_placeholder() -> None:
    policy = EngagementPolicy(protected_values=["Amazon"], aliases={"AWS": "Amazon"})

    assert policy.assign_placeholders() == {"Amazon": "[VALUE_1]", "AWS": "[VALUE_1]"}
