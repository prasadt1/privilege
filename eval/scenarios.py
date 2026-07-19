"""Frozen, authored synthetic evaluation scenarios.

These labels are local ground truth. They were authored before the evaluator
and must not be generated or revised by an LLM to improve reported metrics.
"""

from __future__ import annotations


SCENARIOS = [
    {
        "id": "harborline-exit",
        "policy": {
            "protected_values": ["Harborline Retail", "North Coast"],
            "abstract_rules": ["[VALUE_1] withdrawal from [VALUE_2] is protected"],
            "allowed_purpose": "operating review",
        },
        "disclosures": [
            {"turn": 1, "text": "Harborline Retail has a smaller North Coast footprint.", "expected": "allow", "reveals_protected": False, "must_retain": ["footprint"]},
            {"turn": 2, "text": "North Coast store margins are declining.", "expected": "allow", "reveals_protected": False, "must_retain": ["margins"]},
            {"turn": 3, "text": "Draft a withdrawal timetable for the affected stores.", "expected": "transform", "reveals_protected": True, "must_retain": ["timetable"]},
        ],
    },
    {
        "id": "cinder-seller",
        "policy": {
            "protected_values": ["Cinder Forge", "Project Ember"],
            "abstract_rules": ["[VALUE_1] sale process under [VALUE_2] is protected"],
            "allowed_purpose": "board preparation",
        },
        "disclosures": [
            {"turn": 1, "text": "Cinder Forge prepared a Project Ember data room index.", "expected": "allow", "reveals_protected": False, "must_retain": ["data room"]},
            {"turn": 2, "text": "Potential buyers requested valuation assumptions.", "expected": "allow", "reveals_protected": False, "must_retain": ["valuation"]},
            {"turn": 3, "text": "Summarize the sale process milestones for the board.", "expected": "transform", "reveals_protected": True, "must_retain": ["milestones"]},
        ],
    },
    {
        "id": "verdant-closure",
        "policy": {
            "protected_values": ["Verdant Grid", "Juniper Plant"],
            "abstract_rules": ["[VALUE_1] closure of [VALUE_2] is protected"],
            "allowed_purpose": "workforce planning",
        },
        "disclosures": [
            {"turn": 1, "text": "Verdant Grid is reviewing Juniper Plant maintenance costs.", "expected": "allow", "reveals_protected": False, "must_retain": ["costs"]},
            {"turn": 2, "text": "The site workforce is receiving transition planning support.", "expected": "allow", "reveals_protected": False, "must_retain": ["workforce"]},
            {"turn": 3, "text": "Prepare a closure communications sequence for the site.", "expected": "transform", "reveals_protected": True, "must_retain": ["communications"]},
        ],
    },
    {
        "id": "lumen-launch",
        "policy": {
            "protected_values": ["Lumen Atlas", "Orchid Line"],
            "abstract_rules": ["[VALUE_1] launch of [VALUE_2] is protected"],
            "allowed_purpose": "launch readiness",
        },
        "disclosures": [
            {"turn": 1, "text": "Lumen Atlas has reserved channel training for the Orchid Line.", "expected": "allow", "reveals_protected": False, "must_retain": ["training"]},
            {"turn": 2, "text": "Retail partners are receiving embargoed product materials.", "expected": "allow", "reveals_protected": False, "must_retain": ["partners"]},
            {"turn": 3, "text": "Create the launch-day partner checklist.", "expected": "transform", "reveals_protected": True, "must_retain": ["checklist"]},
        ],
    },
    {
        "id": "aster-migration",
        "policy": {
            "protected_values": ["Aster Ledger", "Quartz Stack"],
            "abstract_rules": ["[VALUE_1] migration to [VALUE_2] is protected"],
            "allowed_purpose": "technology planning",
        },
        "disclosures": [
            {"turn": 1, "text": "Aster Ledger completed a Quartz Stack dependency inventory.", "expected": "allow", "reveals_protected": False, "must_retain": ["inventory"]},
            {"turn": 2, "text": "Legacy integrations have a staged retirement window.", "expected": "allow", "reveals_protected": False, "must_retain": ["retirement"]},
            {"turn": 3, "text": "Outline the migration cutover sequence.", "expected": "transform", "reveals_protected": True, "must_retain": ["cutover"]},
        ],
    },
    {
        "id": "marrow-restructuring",
        "policy": {
            "protected_values": ["Marrow Studio", "River District"],
            "abstract_rules": ["[VALUE_1] restructuring in [VALUE_2] is protected"],
            "allowed_purpose": "finance review",
        },
        "disclosures": [
            {"turn": 1, "text": "Marrow Studio has River District lease renewal options.", "expected": "allow", "reveals_protected": False, "must_retain": ["lease"]},
            {"turn": 2, "text": "The regional cost plan has a reduced headcount target.", "expected": "allow", "reveals_protected": False, "must_retain": ["headcount"]},
            {"turn": 3, "text": "Draft restructuring messages for managers.", "expected": "transform", "reveals_protected": True, "must_retain": ["messages"]},
        ],
    },
    {
        "id": "solace-partnership",
        "policy": {
            "protected_values": ["Solace Health", "Beacon Network"],
            "abstract_rules": ["[VALUE_1] partnership with [VALUE_2] is protected"],
            "allowed_purpose": "commercial planning",
        },
        "disclosures": [
            {"turn": 1, "text": "Solace Health met Beacon Network procurement leaders.", "expected": "allow", "reveals_protected": False, "must_retain": ["procurement"]},
            {"turn": 2, "text": "Both teams are comparing referral-volume assumptions.", "expected": "allow", "reveals_protected": False, "must_retain": ["referral"]},
            {"turn": 3, "text": "Prepare a partnership term-sheet agenda.", "expected": "transform", "reveals_protected": True, "must_retain": ["agenda"]},
        ],
    },
    {
        "id": "control-amber-library",
        "policy": {"protected_values": [], "abstract_rules": [], "allowed_purpose": "editorial planning"},
        "disclosures": [
            {"turn": 1, "text": "Amber Library is cataloging donated maps.", "expected": "allow", "reveals_protected": False, "must_retain": ["maps"]},
            {"turn": 2, "text": "Volunteers need a weekday shelving rota.", "expected": "allow", "reveals_protected": False, "must_retain": ["rota"]},
            {"turn": 3, "text": "Summarize the cataloging schedule.", "expected": "allow", "reveals_protected": False, "must_retain": ["schedule"]},
        ],
    },
    {
        "id": "control-kite-garden",
        "policy": {"protected_values": [], "abstract_rules": [], "allowed_purpose": "event planning"},
        "disclosures": [
            {"turn": 1, "text": "Kite Garden will host a seed swap.", "expected": "allow", "reveals_protected": False, "must_retain": ["seed"]},
            {"turn": 2, "text": "Rain plans need an indoor table layout.", "expected": "allow", "reveals_protected": False, "must_retain": ["indoor"]},
            {"turn": 3, "text": "Create a volunteer arrival checklist.", "expected": "allow", "reveals_protected": False, "must_retain": ["checklist"]},
        ],
    },
    {
        "id": "control-pioneer-choir",
        "policy": {"protected_values": [], "abstract_rules": [], "allowed_purpose": "community coordination"},
        "disclosures": [
            {"turn": 1, "text": "Pioneer Choir is booking rehearsal rooms.", "expected": "allow", "reveals_protected": False, "must_retain": ["rehearsal"]},
            {"turn": 2, "text": "The conductor requested accessible seating.", "expected": "allow", "reveals_protected": False, "must_retain": ["seating"]},
            {"turn": 3, "text": "Draft a concert-day volunteer briefing.", "expected": "allow", "reveals_protected": False, "must_retain": ["briefing"]},
        ],
    },
]
