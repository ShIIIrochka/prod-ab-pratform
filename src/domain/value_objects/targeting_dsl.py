"""DSL for targeting rules. Missing attribute in comparison → false (per task 2.7)."""

from __future__ import annotations

import re

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class _Token:
    kind: str
    value: Any = None

    def __repr__(self) -> str:
        return f"_Token({self.kind!r}, {self.value!r})"


def _tokenize(expression: str) -> list[_Token]:
    """Tokenize rule expression. Supports ==, !=, IN, NOT IN, >, >=, <, <=, AND, OR, NOT."""
    tokens: list[_Token] = []
    s = expression.strip()
    i = 0
    n = len(s)

    while i < n:
        while i < n and s[i].isspace():
            i += 1
        if i >= n:
            break

        # Two-char ops first
        if i + 1 < n:
            two = s[i : i + 2]
            if two == ">=":
                tokens.append(_Token("OP", ">="))
                i += 2
                continue
            if two == "<=":
                tokens.append(_Token("OP", "<="))
                i += 2
                continue
            if two == "!=":
                tokens.append(_Token("OP", "!="))
                i += 2
                continue
            if two == "==":
                tokens.append(_Token("OP", "=="))
                i += 2
                continue

        # Single-char op
        if s[i] == ">":
            tokens.append(_Token("OP", ">"))
            i += 1
            continue
        if s[i] == "<":
            tokens.append(_Token("OP", "<"))
            i += 1
            continue
        if s[i] == "(":
            tokens.append(_Token("LPAREN"))
            i += 1
            continue
        if s[i] == ")":
            tokens.append(_Token("RPAREN"))
            i += 1
            continue
        if s[i] == "[":
            tokens.append(_Token("LBRACKET"))
            i += 1
            continue
        if s[i] == "]":
            tokens.append(_Token("RBRACKET"))
            i += 1
            continue
        if s[i] == ",":
            tokens.append(_Token("COMMA"))
            i += 1
            continue

        # String literal "..."

        if s[i] == '"' or s[i] == "'":
            quote = s[i]
            i += 1
            start = i
            while i < n and s[i] != quote:
                if s[i] == "\\":
                    i += 1
                i += 1
            value = s[start:i].replace("\\" + quote, quote)
            i += 1  # skip closing quote
            tokens.append(_Token("VALUE", value))
            continue

        # Number or identifier or true/false
        start = i
        if s[i] == "-":
            i += 1
        while i < n and (s[i].isalnum() or s[i] in "._-"):
            i += 1
        word = s[start:i]

        if word.lower() == "true":
            tokens.append(_Token("VALUE", True))
        elif word.lower() == "false":
            tokens.append(_Token("VALUE", False))
        elif re.match(r"^-?\d+\.?\d*$", word):
            if "." in word:
                tokens.append(_Token("VALUE", float(word)))
            else:
                tokens.append(_Token("VALUE", int(word)))
        elif re.match(r"^\d{4}-\d{2}-\d{2}$", word):
            try:
                tokens.append(
                    _Token("VALUE", datetime.strptime(word, "%Y-%m-%d").date())
                )
            except ValueError:
                tokens.append(_Token("IDENT", word))
        elif word.upper() == "IN":
            tokens.append(_Token("IN"))
        elif word.upper() == "AND":
            tokens.append(_Token("AND"))
        elif word.upper() == "OR":
            tokens.append(_Token("OR"))
        elif word.upper() == "NOT":
            tokens.append(_Token("NOT"))
        else:
            tokens.append(_Token("IDENT", word))
    return tokens


def _parse_value_list(tokens: list[_Token], pos: int) -> tuple[list[Any], int]:
    if pos >= len(tokens) or tokens[pos].kind != "LBRACKET":
        return [], pos
    pos += 1
    values: list[Any] = []
    while pos < len(tokens) and tokens[pos].kind != "RBRACKET":
        if tokens[pos].kind != "VALUE" and tokens[pos].kind != "IDENT":
            pos += 1
            continue
        values.append(tokens[pos].value)
        pos += 1
        if pos < len(tokens) and tokens[pos].kind == "COMMA":
            pos += 1
    if pos < len(tokens) and tokens[pos].kind == "RBRACKET":
        pos += 1
    return values, pos


def _eval_comparison(
    attr_value: Any,
    op: str,
    right: Any,
) -> bool:
    """Compare attr_value with right using op. Handles type coercion for strings (e.g. version)."""
    if op == "==":
        return attr_value == right
    if op == "!=":
        return attr_value != right
    if op == ">":
        return attr_value > right
    if op == ">=":
        return attr_value >= right
    if op == "<":
        return attr_value < right
    if op == "<=":
        return attr_value <= right
    return False


def evaluate_expression(expression: str, attributes: dict[str, Any]) -> bool:
    """
    Evaluate a targeting rule expression against attributes.
    If an attribute is missing from attributes, the comparison yields False (per task 2.7).
    """
    tokens = _tokenize(expression)
    if not tokens:
        return True

    pos, result = _parse_expr(tokens, 0, attributes)
    return result


def _parse_expr(
    tokens: list[_Token],
    pos: int,
    attributes: dict[str, Any],
) -> tuple[int, bool]:
    """Parse AND-level expression. Returns (new_pos, value)."""
    pos, lhs = _parse_term(tokens, pos, attributes)
    while pos < len(tokens):
        if tokens[pos].kind == "AND":
            pos += 1
            if pos >= len(tokens):
                return pos, lhs
            pos, rhs = _parse_term(tokens, pos, attributes)
            lhs = lhs and rhs
        else:
            break
    return pos, lhs


def _parse_term(
    tokens: list[_Token],
    pos: int,
    attributes: dict[str, Any],
) -> tuple[int, bool]:
    """Parse OR-level expression."""
    pos, lhs = _parse_factor(tokens, pos, attributes)
    while pos < len(tokens):
        if tokens[pos].kind == "OR":
            pos += 1
            if pos >= len(tokens):
                return pos, lhs
            pos, rhs = _parse_factor(tokens, pos, attributes)
            lhs = lhs or rhs
        else:
            break
    return pos, lhs


def _parse_factor(
    tokens: list[_Token],
    pos: int,
    attributes: dict[str, Any],
) -> tuple[int, bool]:
    """Parse NOT or primary."""
    if pos >= len(tokens):
        return pos, False
    if tokens[pos].kind == "NOT":
        pos += 1
        pos, inner = _parse_factor(tokens, pos, attributes)
        return pos, not inner
    return _parse_primary(tokens, pos, attributes)


def _parse_primary(
    tokens: list[_Token],
    pos: int,
    attributes: dict[str, Any],
) -> tuple[int, bool]:
    """Parse comparison or parenthesized expression."""
    if pos >= len(tokens):
        return pos, False
    if tokens[pos].kind == "LPAREN":
        pos += 1
        pos, val = _parse_expr(tokens, pos, attributes)
        if pos < len(tokens) and tokens[pos].kind == "RPAREN":
            pos += 1
        return pos, val

    if tokens[pos].kind != "IDENT":
        return pos + 1, False
    attr_name = tokens[pos].value
    pos += 1

    # Missing attribute → false (task 2.7)
    if attr_name not in attributes:
        # Consume rest of this comparison (op + value or IN [])
        if pos < len(tokens) and tokens[pos].kind == "OP":
            pos += 1
            if pos < len(tokens):
                pos += 1
        elif (
            pos + 1 < len(tokens)
            and tokens[pos].kind == "NOT"
            and tokens[pos + 1].kind == "IN"
        ):
            pos += 2
            _, pos = _parse_value_list(tokens, pos)
        elif pos < len(tokens) and tokens[pos].kind == "IN":
            pos += 1
            _, pos = _parse_value_list(tokens, pos)
        return pos, False

    attr_value = attributes[attr_name]

    if pos >= len(tokens):
        return pos, False

    # IN [ ... ] or NOT IN [ ... ]
    if (
        tokens[pos].kind == "NOT"
        and pos + 1 < len(tokens)
        and tokens[pos + 1].kind == "IN"
    ):
        pos += 2
        values, pos = _parse_value_list(tokens, pos)
        return pos, attr_value not in values
    if tokens[pos].kind == "IN":
        pos += 1
        values, pos = _parse_value_list(tokens, pos)
        return pos, attr_value in values

    if tokens[pos].kind != "OP":
        return pos, False
    op = tokens[pos].value
    pos += 1
    if pos >= len(tokens):
        return pos, False
    if tokens[pos].kind == "VALUE":
        right = tokens[pos].value
    elif tokens[pos].kind == "IDENT":
        right = attributes.get(tokens[pos].value)
        if right is None:
            return pos + 1, False
    else:
        return pos, False
    pos += 1
    return pos, _eval_comparison(attr_value, op, right)
