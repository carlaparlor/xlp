"""Zero-dependency JSON Schema validator (Draft 2020-12 core subset)."""

from __future__ import annotations

import datetime
import json
import re
from typing import Any

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
URI_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://\S+$")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return (isinstance(value, (int, float))) and not isinstance(value, bool)


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "integer":
        return _is_int(value)
    if expected_type == "number":
        return _is_number(value)
    if expected_type == "null":
        return value is None
    return False


def _validate_format(value: str, fmt: str, path: str) -> list[str]:
    if fmt == "semver":
        if not SEMVER_RE.match(value):
            return [f"{path}: '{value}' is not a valid semantic version (X.Y.Z)"]
    elif fmt == "date":
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            return [f"{path}: '{value}' is not a valid ISO-8601 date (YYYY-MM-DD)"]
    elif fmt == "uuid":
        if not UUID_RE.match(value):
            return [f"{path}: '{value}' is not a valid UUID"]
    elif fmt == "uri":
        if not URI_RE.match(value):
            return [f"{path}: '{value}' is not a valid URI"]
    return []


def _resolve_ref(ref: str, root_schema: dict[str, Any]) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"Only local JSON pointer $ref supported, got: {ref}")
    current: Any = root_schema
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"Unresolvable $ref pointer: {ref}")
        current = current[part]
    if not isinstance(current, dict):
        raise ValueError(f"$ref target is not a schema object: {ref}")
    return current


def validate_schema(
    instance: Any,
    schema: dict[str, Any],
    *,
    path: str = "$",
    root_schema: dict[str, Any] | None = None,
) -> list[str]:
    """Validate `instance` against `schema` and return a list of error strings."""
    root = root_schema if root_schema is not None else schema
    errors: list[str] = []

    if "$ref" in schema:
        target = _resolve_ref(schema["$ref"], root)
        errors.extend(validate_schema(instance, target, path=path, root_schema=root))

    if "allOf" in schema:
        for sub in schema["allOf"]:
            errors.extend(validate_schema(instance, sub, path=path, root_schema=root))

    if "anyOf" in schema:
        if not any(
            len(validate_schema(instance, sub, path=path, root_schema=root)) == 0
            for sub in schema["anyOf"]
        ):
            errors.append(f"{path}: value does not satisfy anyOf schema alternatives")

    if "oneOf" in schema:
        matches = sum(
            1
            for sub in schema["oneOf"]
            if len(validate_schema(instance, sub, path=path, root_schema=root)) == 0
        )
        if matches != 1:
            errors.append(f"{path}: expected value to match exactly 1 oneOf schema, matched {matches}")

    if "not" in schema:
        if len(validate_schema(instance, schema["not"], path=path, root_schema=root)) == 0:
            errors.append(f"{path}: value must not match negated schema")

    if "const" in schema:
        expected = schema["const"]
        if instance != expected or type(instance) is not type(expected):
            errors.append(f"{path}: expected const {expected!r}, got {instance!r}")

    if "enum" in schema:
        if not any(
            instance == candidate and type(instance) is type(candidate)
            for candidate in schema["enum"]
        ):
            errors.append(f"{path}: value {instance!r} not in allowed enum {schema['enum']!r}")

    if "type" in schema:
        expected_types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_matches_type(instance, t) for t in expected_types):
            errors.append(
                f"{path}: expected type {'|'.join(expected_types)}, got {type(instance).__name__}"
            )
            return errors

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: string length {len(instance)} < minLength {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: string length {len(instance)} > maxLength {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: string {instance!r} does not match pattern {schema['pattern']!r}")
        if "format" in schema:
            errors.extend(_validate_format(instance, schema["format"], path))

    if _is_number(instance):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: value {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: value {instance} > maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errors.append(
                f"{path}: value {instance} <= exclusiveMinimum {schema['exclusiveMinimum']}"
            )
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            errors.append(
                f"{path}: value {instance} >= exclusiveMaximum {schema['exclusiveMaximum']}"
            )

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: array length {len(instance)} < minItems {schema['minItems']}")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: array length {len(instance)} > maxItems {schema['maxItems']}")
        if schema.get("uniqueItems"):
            seen: set[str] = set()
            for idx, item in enumerate(instance):
                canonical = json.dumps(item, sort_keys=True)
                if canonical in seen:
                    errors.append(f"{path}[{idx}]: duplicate item in uniqueItems array")
                seen.add(canonical)
        if "items" in schema and isinstance(schema["items"], dict):
            for idx, item in enumerate(instance):
                errors.extend(
                    validate_schema(item, schema["items"], path=f"{path}[{idx}]", root_schema=root)
                )

    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                errors.append(f"{path}: missing required property '{req}'")

        props = schema.get("properties", {})
        pattern_props = schema.get("patternProperties", {})
        additional = schema.get("additionalProperties", True)

        for key, val in instance.items():
            matched = False
            child_path = f"{path}.{key}"
            if key in props:
                matched = True
                errors.extend(validate_schema(val, props[key], path=child_path, root_schema=root))
            for pat, sub_schema in pattern_props.items():
                if re.search(pat, key):
                    matched = True
                    errors.extend(validate_schema(val, sub_schema, path=child_path, root_schema=root))
            if not matched:
                if additional is False:
                    errors.append(f"{path}: unexpected additional property '{key}'")
                elif isinstance(additional, dict):
                    errors.extend(validate_schema(val, additional, path=child_path, root_schema=root))

    return errors
