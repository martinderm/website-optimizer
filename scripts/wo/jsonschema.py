"""A small, dependency-free JSON Schema validator.

Why this exists: the authoring guide mandates Python 3 standard library only, so
`jsonschema` is not available, yet run artifacts still have to be validated
against their schemas. This implements the subset those schemas actually use:

    type (incl. union lists), required, properties, additionalProperties: false,
    enum, const, items, pattern, minLength, allOf, if/then

That is deliberately less than the full specification. Anything outside the
subset is ignored rather than guessed, and `SUPPORTED` names what is covered so
a caller can state the limit instead of implying more than is enforced.

The full artifact schemas remain the authority. This validator proves that an
artifact matches the keywords it declares; it does not define new ones.
"""

from __future__ import annotations

import re
from typing import Any

SUPPORTED = (
    "type", "required", "properties", "additionalProperties", "enum", "const",
    "items", "pattern", "minLength", "allOf", "if", "then", "$ref",
)

_PY_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def inline_refs(schema: dict[str, Any], loader, _seen: frozenset = frozenset()) -> dict[str, Any]:
    """Resolve local `$ref`s by loading and inlining them.

    Capability reports share a base schema, so a local reference is the cheapest
    way to state that once. References are inlined rather than resolved at
    validation time because this validator has no document root to resolve
    against. A reference cycle is an error, not something to silently truncate.
    """
    if isinstance(schema, list):
        return [inline_refs(item, loader, _seen) for item in schema]
    if not isinstance(schema, dict):
        return schema

    ref = schema.get("$ref")
    if ref is not None:
        if ref in _seen:
            raise ValueError(f"Circular $ref detected: {ref}")
        target = loader(ref)
        merged = inline_refs(target, loader, _seen | {ref})
        extra = {k: v for k, v in schema.items() if k != "$ref"}
        if extra:
            merged = {**merged, **extra}
        return merged

    return {k: inline_refs(v, loader, _seen) for k, v in schema.items()}


def load_schema(path) -> dict[str, Any]:
    """Load a capability schema from disk with its local refs resolved."""
    import json
    from pathlib import Path

    base = Path(path)

    def loader(ref: str) -> dict[str, Any]:
        target = (base.parent / ref).resolve()
        if not target.is_file():
            raise ValueError(f"Schema reference not found: {ref} (from {base.name})")
        return json.loads(target.read_text(encoding="utf-8"))

    return inline_refs(json.loads(base.read_text(encoding="utf-8")), loader)


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    py = _PY_TYPES.get(expected)
    if py is None:
        return True  # unknown type keyword: do not invent a failure
    if py is str and isinstance(value, bool):
        return False
    return isinstance(value, py)


def validate(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Return a list of error strings. Empty list means valid."""
    errors: list[str] = []

    if "allOf" in schema:
        for index, sub in enumerate(schema["allOf"]):
            errors += validate(instance, sub, f"{path}.allOf[{index}]")

    if "if" in schema:
        if _matches(instance, schema["if"]):
            if "then" in schema:
                errors += validate(instance, schema["then"], path)
        elif "else" in schema:
            errors += validate(instance, schema["else"], path)

    if "type" in schema:
        expected = schema["type"]
        options = expected if isinstance(expected, list) else [expected]
        if not any(_type_ok(instance, option) for option in options):
            errors.append(f"{path}: expected type {expected}, got {type(instance).__name__}")
            return errors

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} is not one of {schema['enum']}")

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: does not match pattern {schema['pattern']!r}")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required property {key!r}")
        props = schema.get("properties", {})
        for key, value in instance.items():
            if key in props:
                errors += validate(value, props[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected property {key!r}")

    if isinstance(instance, list) and "items" in schema:
        for index, item in enumerate(instance):
            errors += validate(item, schema["items"], f"{path}[{index}]")

    return errors


def _matches(instance: Any, schema: dict[str, Any]) -> bool:
    """Cheap positive test used by if/then: no errors means it matches."""
    return not validate(instance, schema)


def assert_valid(instance: Any, schema: dict[str, Any], label: str) -> None:
    """Raise ValueError listing every violation, or return None."""
    errors = validate(instance, schema)
    if errors:
        listed = "\n  - ".join(errors)
        raise ValueError(f"{label} does not conform to its schema:\n  - {listed}")