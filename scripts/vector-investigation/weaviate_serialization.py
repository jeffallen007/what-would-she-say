"""Reproduce the text2vec-openai object text used by this live schema.

This is deliberately a small implementation of Weaviate's shared object
vectorizer behavior, not a generic document-chunking function.  The live
collections all use ``vectorizeClassName=true``, no ``properties`` allow-list,
``skip=false``, and ``vectorizePropertyName=false``.  Under that combination,
Weaviate sorts property names, appends only string (or string-array) values,
and joins every corpus element with one space.  Numeric and boolean properties
are not included because there is no collection-level ``properties`` allow-list.
"""

from __future__ import annotations

import re
from typing import Any, Iterable


CAMEL_PART = re.compile(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+")


def separate_camel_case(value: str) -> str:
    """Match Weaviate's class/property-name splitting for this schema."""
    return " ".join(CAMEL_PART.findall(value))


def serialized_text(collection: str, properties: dict[str, Any]) -> str:
    """Return the exact text2vec-openai input for the verified live settings.

    Algorithm: ``splitCamelCase(collection) + sorted textual property values``.
    Property names are omitted; strings retain case and whitespace exactly.
    """
    corpi = [separate_camel_case(collection)]  # vectorizeClassName=true
    for name in sorted(properties):
        value = properties[name]
        if isinstance(value, str):
            corpi.append(value)
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            corpi.extend(value)
        # Number/bool values are intentionally excluded: no source-properties allow-list.
    return " ".join(corpi)


def serialization_description() -> str:
    return (
        "splitCamelCase(collection) + ' ' + textual property values in lexical property-name "
        "order; omit property names, numbers, and booleans; preserve text case and whitespace"
    )
