#!/usr/bin/env python3
"""Generate a strong random password. Randomness comes from `secrets`."""

import argparse
import secrets
import string
import sys

LOWER = string.ascii_lowercase
UPPER = string.ascii_uppercase
DIGITS = string.digits
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.<>/?"


def build_pool(lower: bool, upper: bool, digits: bool, symbols: bool) -> tuple[str, list[str]]:
    enabled: list[str] = []
    if lower:
        enabled.append(LOWER)
    if upper:
        enabled.append(UPPER)
    if digits:
        enabled.append(DIGITS)
    if symbols:
        enabled.append(SYMBOLS)
    if not enabled:
        raise ValueError("at least one character class must be enabled")
    return "".join(enabled), enabled


def generate_password(length: int, pool: str, enabled_classes: list[str]) -> str:
    if length < 1:
        raise ValueError("length must be >= 1")

    chars = [secrets.choice(pool) for _ in range(length)]

    # Guarantee at least one char from each enabled class when length allows.
    # Place the picks in the first N slots, then shuffle so positions are random.
    if length >= len(enabled_classes):
        for i, class_pool in enumerate(enabled_classes):
            chars[i] = secrets.choice(class_pool)
        secrets.SystemRandom().shuffle(chars)

    return "".join(chars)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="genpass",
        description=(
            "Generate a strong random password using Python's `secrets` "
            "module for cryptographic randomness."
        ),
    )
    parser.add_argument(
        "--length",
        type=int,
        default=16,
        help="password length (default: 16)",
    )
    parser.add_argument(
        "--lower",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="include lowercase letters (default: on)",
    )
    parser.add_argument(
        "--upper",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="include uppercase letters (default: on)",
    )
    parser.add_argument(
        "--digits",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="include digits (default: on)",
    )
    parser.add_argument(
        "--symbols",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="include symbols (default: on)",
    )
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    try:
        pool, enabled = build_pool(args.lower, args.upper, args.digits, args.symbols)
        password = generate_password(args.length, pool, enabled)
    except ValueError as exc:
        print(f"genpass: error: {exc}", file=sys.stderr)
        return 2
    print(password)
    return 0


if __name__ == "__main__":
    sys.exit(main())
