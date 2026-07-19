"""Engagement policy definitions kept and interpreted locally."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class EngagementPolicy:
    """Local policy facts and the safe abstract rules used by a remote judge."""

    protected_values: list[str] = field(default_factory=list)
    aliases: dict[str, str] = field(default_factory=dict)
    abstract_rules: list[str] = field(default_factory=list)
    allowed_purpose: str = ""
    strictness: str = "normal"

    def __post_init__(self) -> None:
        if self.strictness not in {"normal", "strict"}:
            raise ValueError("strictness must be 'normal' or 'strict'")
        if any(not value for value in self.protected_values):
            raise ValueError("protected_values cannot contain empty values")
        unknown = set(self.aliases.values()) - set(self.protected_values)
        if unknown:
            raise ValueError("each alias must point to a protected value")

    def assign_placeholders(self) -> dict[str, str]:
        """Return stable local value-to-placeholder mappings, including aliases."""
        placeholders: dict[str, str] = {}
        for index, value in enumerate(self.protected_values, start=1):
            placeholders[value] = f"[VALUE_{index}]"
        for alias, canonical in self.aliases.items():
            placeholders[alias] = placeholders[canonical]
        return placeholders

    def to_abstract_for_judge(self) -> list[str]:
        """Produce rules safe for OpenAI: no protected value or alias is retained."""
        mappings = self.assign_placeholders()
        rules: list[str] = []
        for rule in self.abstract_rules:
            abstract = rule
            for value in sorted(mappings, key=len, reverse=True):
                abstract = abstract.replace(value, mappings[value])
            rules.append(abstract)
        return rules

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "EngagementPolicy":
        return cls(
            protected_values=list(data.get("protected_values", [])),
            aliases=dict(data.get("aliases", {})),
            abstract_rules=list(data.get("abstract_rules", [])),
            allowed_purpose=str(data.get("allowed_purpose", "")),
            strictness=str(data.get("strictness", "normal")),
        )
