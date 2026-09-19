"""The JSON Schema is generated from this small, closed schema vocabulary."""


def obj(properties, required=None):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": False,
    }


def array(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}


TEXT = {"type": "string", "minLength": 1}
ID = {"type": "string", "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$"}
NUMBER = {"type": "number"}
REF = obj({"ref": ID})
ASSIGNMENT = {"type": "object", "additionalProperties": TEXT}
PROVENANCE = obj(
    {
        "source_type": {
            "enum": [
                "elicited",
                "reference_class",
                "registered_forecast",
                "modeled",
                "literature",
                "assumption",
            ]
        },
        "source_refs": array(ID),
        "owner": TEXT,
        "rationale": TEXT,
        "evidence_population": {"enum": ["human", "simulated", "not_applicable"]},
        "review_status": {"enum": ["proposed", "accepted", "rejected"]},
    }
)
EXPRESSION = {
    "oneOf": [
        REF,
        {"type": "number", "enum": [0, 1]},
        obj(
            {
                "op": {"enum": ["add", "subtract", "multiply", "divide", "negate"]},
                "args": array({"$ref": "#/$defs/expression"}, 1),
            }
        ),
    ]
}
PARAMETER = obj(
    {
        "id": ID,
        "kind": {"enum": ["probability", "payoff", "cost", "constant"]},
        "unit": TEXT,
        "value": NUMBER,
        "expression": {"$ref": "#/$defs/expression"},
        "provenance": PROVENANCE,
        "bounds": array(NUMBER),
    },
    ["id", "kind", "unit"],
)
PARAMETER["oneOf"] = [
    {"required": ["value"], "not": {"required": ["expression"]}},
    {"required": ["expression"], "not": {"required": ["value"]}},
]
DECISION = obj(
    {
        "id": ID,
        "kind": {"const": "decision"},
        "actions": array(ID, 1),
        "stage": {"type": "integer", "minimum": 0},
        "observes": array(ID),
    }
)
CHANCE = obj(
    {
        "id": ID,
        "kind": {"const": "chance"},
        "outcomes": array(ID, 1),
        "parents": array(ID),
        "cpt": array(
            obj(
                {
                    "when": ASSIGNMENT,
                    "probabilities": {"type": "object", "additionalProperties": REF},
                }
            ),
            1,
        ),
    }
)
VALUE = obj(
    {
        "id": ID,
        "kind": {"const": "value"},
        "parents": array(ID),
        "unit": TEXT,
        "table": array(obj({"when": ASSIGNMENT, "value": REF}), 1),
    }
)
SOURCE = obj(
    {
        "id": ID,
        "package": TEXT,
        "object_type": TEXT,
        "object_id": TEXT,
        "revision": TEXT,
        "artifact_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "path": TEXT,
        "locator": TEXT,
        "captured_at": TEXT,
        "claim_refs": array(TEXT),
    },
    [
        "id",
        "package",
        "object_type",
        "object_id",
        "revision",
        "artifact_sha256",
        "path",
        "locator",
        "captured_at",
    ],
)
STUDY = obj(
    {
        "id": ID,
        "targets": array(ID, 1),
        "outcomes": array(ID, 1),
        "likelihood": CHANCE["properties"]["cpt"],
        "before": ID,
        "cost": REF,
        "design": TEXT,
        "provenance": PROVENANCE,
    }
)
SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://expectedparrot.github.io/raiffa/schemas/model-2.0.json",
    "title": "Raiffa finite decision model",
    "$defs": {"expression": EXPRESSION},
    **obj(
        {
            "schema_version": {"const": "raiffa.model/2.0"},
            "id": ID,
            "title": TEXT,
            "decision_maker": TEXT,
            "objective": obj(
                {
                    "direction": {"const": "maximize"},
                    "value_nodes": array(ID, 1),
                    "aggregation": {"const": "sum"},
                    "preference_ref": ID,
                }
            ),
            "valuation_context": obj(
                {
                    "unit": TEXT,
                    "valuation_date": TEXT,
                    "price_basis": TEXT,
                    "timing": {"const": "single_date"},
                }
            ),
            "decision_order": array(ID, 1),
            "nodes": array({"oneOf": [DECISION, CHANCE, VALUE]}, 2),
            "arcs": array(
                obj(
                    {
                        "from": ID,
                        "to": ID,
                        "kind": {"enum": ["dependency", "information", "value"]},
                    }
                )
            ),
            "parameters": array(PARAMETER, 1),
            "sources": array(SOURCE),
            "studies": array(STUDY),
        }
    ),
}
