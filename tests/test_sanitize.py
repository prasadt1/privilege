from src.sanitize import restore, sanitize


def test_longest_mapping_wins() -> None:
    result = sanitize(
        "Amazon Web Services is separate from Amazon.",
        {"Amazon": "[CLIENT]", "Amazon Web Services": "[PLATFORM]"},
    )

    assert result.text == "[PLATFORM] is separate from [CLIENT]."
    assert result.applied[:2] == [
        {"real": "Amazon Web Services", "placeholder": "[PLATFORM]"},
        {"real": "Amazon", "placeholder": "[CLIENT]"},
    ]


def test_masks_email_phone_and_card_like_values() -> None:
    result = sanitize("Email a@b.example, phone +49 30 1234 5678, card 4111 1111 1111 1111.", {})

    assert result.text == "Email [EMAIL], phone [PHONE], card [CARD]."


def test_restore_declared_placeholders_locally() -> None:
    mappings = {"Amazon": "[CLIENT]", "Berlin": "[REGION]"}

    assert restore("[CLIENT] operates in [REGION].", mappings) == "Amazon operates in Berlin."
