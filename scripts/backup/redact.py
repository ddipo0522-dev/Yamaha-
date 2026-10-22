#!/usr/bin/env python3
"""Secret redaction helpers for Kilo session exports and environment archives.

Every artifact that leaves this machine (git push, release asset) must be
passed through `redact_text` first. The patterns below cover the credential
families that actually appeared in this environment's chat history and tool
output: GitHub OAuth/app tokens, OpenRouter/OpenAI/Anthropic/Google keys,
AWS access keys, bearer tokens, JWTs and PEM private key blocks.
"""

import re
import sys
import pathlib

PLACEHOLDER = "[REDACTED]"

SECRET_PATTERNS = [
    # PEM private key blocks (multi-line)
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
                re.DOTALL), f"-----BEGIN PRIVATE KEY-----{PLACEHOLDER}-----END PRIVATE KEY-----"),
    # GitHub tokens: ghp_ gho_ ghu_ ghs_ ghr_ github_pat_
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,})\b"), PLACEHOLDER),
    # OpenRouter
    (re.compile(r"\bsk-or-v1-[A-Za-z0-9\-_]{16,}\b"), PLACEHOLDER),
    # Anthropic
    (re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{16,}\b"), PLACEHOLDER),
    # OpenAI / xAI / Groq / generic sk- keys
    (re.compile(r"\bsk-[A-Za-z0-9\-_]{20,}\b"), PLACEHOLDER),
    # Google API keys
    (re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"), PLACEHOLDER),
    # AWS access key ids
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), PLACEHOLDER),
    # Fusion dashboard bearer tokens
    (re.compile(r"\bbgp_[A-Za-z0-9]{16,}\b"), PLACEHOLDER),
    # Fusion daemon/api tokens
    (re.compile(r"\bfn_[A-Za-z0-9]{16,}\b"), PLACEHOLDER),
    # JSON Web Tokens
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"), PLACEHOLDER),
    # Bearer headers
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9_\-\.=+/]{16,}"), f"Bearer {PLACEHOLDER}"),
]

# key = value / "key": "value" assignments whose value looks like a credential
_ASSIGNMENT = re.compile(
    r"(?i)([\"']?(?:[A-Za-z0-9_\-]*(?:api[_-]?key|secret|token|password|passwd|authorization|access[_-]?key|private[_-]?key)[A-Za-z0-9_\-]*)[\"']?\s*[:=]\s*[\"']?)"
    r"([^\s\"',;}\]]{12,})"
)

_BENIGN = {
    "none", "null", "true", "false", "undefined", "redacted", "placeholder",
    "your_token_here", "changeme", "example", "dummy",
}

# markers that show the value is documentation, not a live credential
_DOC_MARKERS = ("...", "<", ">", "${", "{{", "%", "example", "sample")


def _redact_assignment(match):
    key, value = match.group(1), match.group(2)
    if value.lower() in _BENIGN or value.startswith(PLACEHOLDER):
        return match.group(0)
    if any(marker in value for marker in _DOC_MARKERS):
        return match.group(0)
    if len(value) < 16:
        return match.group(0)
    if not (re.search(r"\d", value) and re.search(r"[A-Za-z]", value)):
        return match.group(0)
    return key + PLACEHOLDER


def redact_text(text):
    """Return `text` with every recognised credential replaced by a placeholder."""
    if not text:
        return text
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    text = _ASSIGNMENT.sub(_redact_assignment, text)
    return text


def redact_obj(obj):
    """Recursively redact every string inside a JSON-compatible structure."""
    if isinstance(obj, str):
        return redact_text(obj)
    if isinstance(obj, list):
        return [redact_obj(v) for v in obj]
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    return obj


BINARY_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".wal", ".shm"}


def is_binary(path):
    """Only database files are skipped; everything else is redacted in a
    byte-safe way (utf-8 + surrogateescape round-trips arbitrary bytes)."""
    return path.suffix.lower() in BINARY_SUFFIXES or path.name.endswith(("-wal", "-shm"))


def main():
    if len(sys.argv) < 2:
        print("usage: redact.py <file> [file ...]", file=sys.stderr)
        return 1
    for arg in sys.argv[1:]:
        path = pathlib.Path(arg)
        if not path.is_file() or is_binary(path):
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        original = raw.decode("utf-8", errors="surrogateescape")
        cleaned = redact_text(original)
        if cleaned != original:
            path.write_bytes(cleaned.encode("utf-8", errors="surrogateescape"))
            print(f"redacted {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
