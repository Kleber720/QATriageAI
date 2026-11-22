import re
from dataclasses import dataclass, field


@dataclass
class PIISanitizationResult:
    sanitized_text: str
    redactions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


_LABELED_TWO_LINE_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(
            r"(?im)^[ \t]*Nome completo do dispositivo\s*[:\-]?\s*\r?\n[ \t]*[^\r\n]+(?:\r?\n|$)"
        ),
        "Nome completo / domínio corporativo do dispositivo",
        "Nome completo e domínio do dispositivo removidos por privacidade.",
    ),
    (
        re.compile(
            r"(?im)^[ \t]*Nome do dispositivo\s*[:\-]?\s*\r?\n[ \t]*[^\r\n]+(?:\r?\n|$)"
        ),
        "Nome do dispositivo",
        "Nome identificador do dispositivo removido por privacidade.",
    ),
    (
        re.compile(
            r"(?im)^[ \t]*ID do dispositivo\s*[:\-]?\s*\r?\n[ \t]*[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}[ \t]*(?:\r?\n|$)"
        ),
        "ID do dispositivo (UUID)",
        "ID único do dispositivo (UUID) removido para evitar exposição.",
    ),
    (
        re.compile(
            r"(?im)^[ \t]*ID do Produto\s*[:\-]?\s*\r?\n[ \t]*[A-Z0-9]{4,6}-[A-Z0-9]{4,6}-[A-Z0-9]{4,6}-[A-Z0-9]{4,6}[ \t]*(?:\r?\n|$)"
        ),
        "ID do Produto (Windows)",
        "ID do Produto do sistema operacional removido por segurança.",
    ),
]

_INLINE_LABELED_PATTERNS: list[tuple[re.Pattern[str], str, str, str]] = [
    (
        re.compile(
            r"(?im)^([ \t]*Nome completo do dispositivo\s*[:\-]\s*)([^\r\n]+)$"
        ),
        r"\1[DOMÍNIO REMOVIDO]",
        "Nome completo / domínio corporativo do dispositivo",
        "Domínio completo do dispositivo removido por privacidade.",
    ),
    (
        re.compile(
            r"(?im)^([ \t]*Nome do dispositivo\s*[:\-]\s*)([^\r\n]+)$"
        ),
        r"\1[DISPOSITIVO REMOVIDO]",
        "Nome do dispositivo",
        "Nome do dispositivo removido por privacidade.",
    ),
    (
        re.compile(
            r"(?im)^([ \t]*ID do dispositivo\s*[:\-]\s*)([0-9A-Fa-f-]{16,})$"
        ),
        r"\1[UUID REMOVIDO]",
        "ID do dispositivo (UUID)",
        "ID do dispositivo (UUID) removido para evitar exposição.",
    ),
    (
        re.compile(
            r"(?im)^([ \t]*ID do Produto\s*[:\-]\s*)([A-Z0-9-]{15,})$"
        ),
        r"\1[ID REMOVIDO]",
        "ID do Produto (Windows)",
        "ID do Produto removido por segurança.",
    ),
]

_RAW_PATTERNS: list[tuple[re.Pattern[str], str, str, str]] = [
    (
        re.compile(
            r"\[[A-Za-z0-9_-]+\.(?:ptw-i\.com|exemplo\.local|corp|internal|local)\]\(https?://[^)]+\)",
            re.IGNORECASE,
        ),
        "[HOST CORPORATIVO REMOVIDO]",
        "Hostname / domínio corporativo em link",
        "Link de domínio corporativo removido por privacidade.",
    ),
    (
        re.compile(
            r"\b[A-Za-z0-9_-]+\.(?:ptw-i\.com|exemplo\.local|corp|internal)\b",
            re.IGNORECASE,
        ),
        "[DOMÍNIO CORPORATIVO REMOVIDO]",
        "Domínio corporativo",
        "Domínio interno corporativo removido por privacidade.",
    ),
    (
        re.compile(r"\b(?:SPO|QA|DEV|CORP)-PC[0-9A-Za-z_-]+\b", re.IGNORECASE),
        "[PC-ID REMOVIDO]",
        "Identificador de estação de trabalho",
        "Identificador de máquina (hostname) removido por privacidade.",
    ),
    (
        re.compile(
            r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b"
        ),
        "[UUID REMOVIDO]",
        "Identificador único (UUID)",
        "UUID de sistema removido por privacidade.",
    ),
    (
        re.compile(r"\b\d{5}-\d{5}-\d{5}-[A-Z0-9]{5}\b"),
        "[PRODUCT-ID REMOVIDO]",
        "Product ID do Windows",
        "Product ID do sistema operacional removido por segurança.",
    ),
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[EMAIL REMOVIDO]",
        "Endereço de e-mail",
        "Endereço de e-mail removido por privacidade.",
    ),
    (
        re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
        "[CPF REMOVIDO]",
        "CPF",
        "CPF removido por privacidade.",
    ),
    (
        re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"),
        "[IP REMOVIDO]",
        "Endereço IP",
        "Endereço IPv4 removido por privacidade.",
    ),
]


def _append_unique(target: list[str], value: str) -> None:
    if value not in target:
        target.append(value)


def scan_and_sanitize(text: str) -> PIISanitizationResult:
    if not text:
        return PIISanitizationResult(sanitized_text="")

    current = text
    redactions: list[str] = []
    warnings: list[str] = []

    for pattern, redaction_label, warning_msg in _LABELED_TWO_LINE_PATTERNS:
        if pattern.search(current):
            current = pattern.sub("", current)
            _append_unique(redactions, redaction_label)
            _append_unique(warnings, warning_msg)

    for pattern, replacement, redaction_label, warning_msg in _INLINE_LABELED_PATTERNS:
        if pattern.search(current):
            current = pattern.sub(replacement, current)
            _append_unique(redactions, redaction_label)
            _append_unique(warnings, warning_msg)

    for pattern, replacement, redaction_label, warning_msg in _RAW_PATTERNS:
        if pattern.search(current):
            current = pattern.sub(replacement, current)
            _append_unique(redactions, redaction_label)
            _append_unique(warnings, warning_msg)

    current = re.sub(r"\n{3,}", "\n\n", current).strip()
    return PIISanitizationResult(
        sanitized_text=current,
        redactions=redactions,
        warnings=warnings,
    )
