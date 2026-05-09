# genpass — Secure Password Generator CLI

A small, dependency-free command-line tool that generates cryptographically
secure random passwords. It is designed to be a safe, scriptable replacement
for ad-hoc password generation (online generators, `openssl rand`, or — worst
of all — Python's `random` module).

---

## Table of Contents

1. [Project Description & Problem It Solves](#project-description--problem-it-solves)
2. [Architecture Overview](#architecture-overview)
3. [Tech Stack](#tech-stack)
4. [Setup & Run Instructions](#setup--run-instructions)
5. [Usage & Examples](#usage--examples)
6. [Screenshots / Diagrams](#screenshots--diagrams)
7. [Exit Codes](#exit-codes)
8. [Security Notes](#security-notes)

---

## Project Description & Problem It Solves

Generating a strong password sounds simple, but it is easy to get wrong:

- **Online generators** require trusting a third party with the very thing
  you are about to use as a secret.
- **`random.choice`** in Python uses the Mersenne Twister, which is
  deterministic and predictable from observed output — unsuitable for
  anything security-related.
- **Naive samplers** can produce passwords that fail site policies (e.g. no
  digit, no uppercase letter), forcing the user to regenerate.

**genpass** addresses all three concerns:

- Runs locally — no network calls, no third party.
- Uses `secrets`, the standard library's CSPRNG-backed module, for all
  randomness.
- Guarantees at least one character from every enabled class (when the
  requested length permits), so the output reliably meets common password
  policies on the first try.

It is intended for developers, sysadmins, and security-conscious users who
want a tiny, auditable script they can drop into a shell, a `Makefile`, a
provisioning playbook, or a CI pipeline.

---

## Architecture Overview

The tool is a single Python file (`genpass.py`) organised as a small,
linear pipeline. Each stage has one responsibility and is independently
testable.

```
        ┌──────────────────────┐
        │       argv           │
        │  (command-line args) │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │     parse_args()     │   argparse + BooleanOptionalAction
        │  --length, --lower,  │   → produces a Namespace of flags
        │  --upper, --digits,  │
        │  --symbols           │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │     build_pool()     │   Selects character classes
        │  LOWER / UPPER /     │   → returns (pool, enabled_classes)
        │  DIGITS / SYMBOLS    │   → raises ValueError if all are off
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  generate_password() │   secrets.choice() per character
        │  - draw N chars      │   then enforce one-of-each-class
        │  - inject 1/class    │   via SystemRandom().shuffle()
        │  - shuffle           │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │        main()        │   prints to stdout, returns exit code
        └──────────────────────┘
```

**Key design decisions**

| Decision | Rationale |
|---|---|
| Single-file script, no dependencies | Auditable in one read; trivially portable. |
| `secrets` over `random` | Cryptographically secure source backed by the OS CSPRNG. |
| Custom `SYMBOLS` set instead of `string.punctuation` | Excludes characters (`'`, `"`, `\`, `` ` ``) that frequently break shells, SQL clients, and copy-paste workflows. |
| Guarantee-and-shuffle strategy | Ensures policy compliance without biasing character distribution beyond the deliberate one-per-class injection. |
| Errors on stderr, exit code 2 | Matches conventional CLI behaviour and keeps stdout clean for piping. |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.9+ |
| Randomness | `secrets` (stdlib, CSPRNG-backed) |
| Argument parsing | `argparse` with `BooleanOptionalAction` |
| Character sets | `string` (stdlib) |
| Runtime dependencies | **None** |
| Packaging | None — distributed as a single script |
| Supported platforms | macOS, Linux, Windows (anywhere CPython 3.9+ runs) |

---

## Setup & Run Instructions

### Prerequisites

- Python **3.9** or newer (`BooleanOptionalAction` was added in 3.9).

Verify your interpreter:

```bash
python3 --version
```

### Get the script

Clone or download the repository:

```bash
git clone <repo-url> secure-password-generator-cli
cd secure-password-generator-cli
```

### Run it

The simplest invocation prints a 16-character password drawn from all four
character classes:

```bash
python3 genpass.py
```

### Optional: install as a local command

Make the script executable and place it on your `PATH`:

```bash
chmod +x genpass.py
ln -s "$(pwd)/genpass.py" /usr/local/bin/genpass
```

You can then run it as:

```bash
genpass --length 24
```

---

## Usage & Examples

### Synopsis

```
genpass [--length N]
        [--lower | --no-lower]
        [--upper | --no-upper]
        [--digits | --no-digits]
        [--symbols | --no-symbols]
        [-h]
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--length N` | `16` | Number of characters in the output. Must be `>= 1`. |
| `--lower` / `--no-lower` | on | Include lowercase letters `a-z`. |
| `--upper` / `--no-upper` | on | Include uppercase letters `A-Z`. |
| `--digits` / `--no-digits` | on | Include digits `0-9`. |
| `--symbols` / `--no-symbols` | on | Include `!@#$%^&*()-_=+[]{};:,.<>/?`. |
| `-h`, `--help` | — | Show usage and exit. |

### Examples

```bash
# Default: 16 chars, all classes
python3 genpass.py

# Long passphrase-style password, all classes
python3 genpass.py --length 32

# Site that rejects symbols
python3 genpass.py --length 20 --no-symbols

# Numeric PIN
python3 genpass.py --length 6 --no-lower --no-upper --no-symbols

# Lowercase + digits only (e.g. for legacy systems)
python3 genpass.py --no-upper --no-symbols
```

---

## Screenshots / Diagrams

### Sample terminal session

```
$ python3 genpass.py
gT4!xQp9aL#bM2vR

$ python3 genpass.py --length 24 --no-symbols
3kLp9aQrT8vXz1MnB7yWeJfH

$ python3 genpass.py --length 6 --no-lower --no-upper --no-symbols
492817

$ python3 genpass.py --no-lower --no-upper --no-digits --no-symbols
genpass: error: at least one character class must be enabled

$ python3 genpass.py --length 0
genpass: error: length must be >= 1
```

### Data flow

```
    user flags ──▶ build_pool ──▶ ┌─────────────┐
                                   │   pool +    │
                                   │ class list  │
                                   └──────┬──────┘
                                          │
                       length ────────────┤
                                          ▼
                                ┌──────────────────┐
                                │ secrets.choice × │
                                │     length       │
                                └────────┬─────────┘
                                          │
                                  one-of-each-class
                                  injection + shuffle
                                          │
                                          ▼
                                      password
```

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success — password printed to stdout. |
| `2` | Invalid input (e.g. `--length 0`, or every class disabled). Message goes to stderr. |

This makes the tool safe to use in shell pipelines:

```bash
pw=$(python3 genpass.py --length 32 --no-symbols) || exit 1
```

---

## Security Notes

- All randomness comes from `secrets`, which is backed by the operating
  system's CSPRNG (`/dev/urandom` on Unix, `BCryptGenRandom` on Windows).
- The tool performs **no network I/O** and writes the password only to
  stdout. Be mindful of shell history (`HISTCONTROL=ignorespace` or piping
  directly into a clipboard utility such as `pbcopy` / `xclip` is
  recommended for interactive use).
- The custom symbol set deliberately excludes quote and backslash
  characters that tend to break shell quoting, SQL string literals, and
  CSV columns. If your target system requires those, you can extend the
  `SYMBOLS` constant at the top of `genpass.py`.
- For very short passwords (length less than the number of enabled
  classes), the one-of-each-class guarantee is silently skipped — there is
  simply not enough room. Prefer a length of at least 12 for human
  accounts and 24+ for machine credentials.
