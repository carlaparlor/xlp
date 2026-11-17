"""Unit and schema tests for the built-in Draft 2020-12 JSON Schema validator.

@category: unit
@category: schema
"""

from __future__ import annotations

import unittest

from tools.xlp_gate.schema_validator import validate_schema


class TestSchemaValidator(unittest.TestCase):
    def test_valid_object_with_formats_and_refs(self) -> None:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["version", "date", "uid", "url", "items"],
            "$defs": {"tag": {"type": "string", "minLength": 2}},
            "properties": {
                "version": {"type": "string", "format": "semver"},
                "date": {"type": "string", "format": "date"},
                "uid": {"type": "string", "format": "uuid"},
                "url": {"type": "string", "format": "uri"},
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "uniqueItems": True,
                    "items": {"$ref": "#/$defs/tag"},
                },
            },
        }
        payload = {
            "version": "1.2.3-beta.1",
            "date": "2026-11-15",
            "uid": "123e4567-e89b-12d3-a456-426614174000",
            "url": "https://example.org/spec",
            "items": ["vst3", "clap"],
        }
        self.assertEqual(validate_schema(payload, schema), [])

    def test_rejects_bad_formats_types_and_additional_properties(self) -> None:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["version", "count"],
            "properties": {
                "version": {"type": "string", "format": "semver"},
                "count": {"type": "integer", "minimum": 1, "maximum": 10},
            },
        }
        # Booleans must NOT be accepted as integers in JSON Schema.
        errors = validate_schema({"version": "not-semver", "count": True, "extra": 1}, schema)
        self.assertGreaterEqual(len(errors), 3)
        self.assertTrue(any("semver" in e for e in errors))
        self.assertTrue(any("expected type integer" in e for e in errors))
        self.assertTrue(any("additional property 'extra'" in e for e in errors))

    def test_combinators_and_unique_items(self) -> None:
        schema = {
            "allOf": [
                {"type": "array", "uniqueItems": True, "minItems": 2},
                {"not": {"const": ["forbidden", "pair"]}},
            ]
        }
        self.assertEqual(validate_schema(["a", "b"], schema), [])
        dup_errors = validate_schema(["a", "a"], schema)
        self.assertTrue(any("duplicate item" in e for e in dup_errors))
        neg_errors = validate_schema(["forbidden", "pair"], schema)
        self.assertTrue(any("negated schema" in e for e in neg_errors))


if __name__ == "__main__":
    unittest.main()
