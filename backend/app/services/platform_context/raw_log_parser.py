import re
from typing import Literal

from app.domain.pii_sanitizer import scan_and_sanitize
from app.models.schemas import LogEvent, PlatformContextData, PlatformEnvironment

_TIMESTAMP_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}|\d{2}:\d{2}:\d{2})\b"
)
_LEVEL_RE = re.compile(r"\b(FATAL|ERROR|WARN(?:ING)?|INFO)\b", re.IGNORECASE)
_COMPONENT_RE = re.compile(r"\[([A-Za-z0-9_./:-]+)\]|([A-Za-z][A-Za-z0-9_./-]+):")
_ERR_CODE_RE = re.compile(
    r"\b(?:ERR_[A-Z0-9_]+|HTTP\s+[45]\d{2}|[A-Za-z]+Exception|exitCode=-?\d+)\b",
    re.IGNORECASE,
)
_BUILD_RE = re.compile(
    r"\b(?:(?:build|vers[aã]o)\s*[:=]?\s*(?:\[([^\]]+)\]|([A-Za-z0-9_.\-]+))|v\d+\.\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)
_PLATFORM_RE = re.compile(
    r"\b(Web|Desktop|Mobile|Chrome(?:\s*\d+)?|Safari(?:\s*\d+)?|Firefox|Edge|iPhone|iOS(?:\s*\d+)?|Android|WhatsApp|Windows\s*\d+(?:\s*x64)?|macOS)\b",
    re.IGNORECASE,
)


def _normalize_level(raw_level: str) -> Literal["INFO", "WARN", "ERROR", "FATAL"]:
    upper = raw_level.upper()
    if upper.startswith("WARN"):
        return "WARN"
    if upper == "FATAL":
        return "FATAL"
    if upper == "ERROR":
        return "ERROR"
    return "INFO"


def parse_raw_log(raw_text: str) -> PlatformContextData:
    pii_result = scan_and_sanitize(raw_text)
    cleaned_text = pii_result.sanitized_text

    events: list[LogEvent] = []
    error_codes: list[str] = []
    detected_build = ""
    detected_platform = ""
    detected_os = ""

    for line in cleaned_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if not detected_build:
            b_match = _BUILD_RE.search(stripped)
            if b_match:
                detected_build = (b_match.group(1) or b_match.group(2) or b_match.group(0)).strip()

        for p_match in _PLATFORM_RE.finditer(stripped):
            token = p_match.group(1).strip()
            if token.lower().startswith("windows") and not detected_os:
                detected_os = token
            elif not detected_platform:
                detected_platform = token

        line_codes: list[str] = []
        for c_match in _ERR_CODE_RE.finditer(stripped):
            code = c_match.group(0).strip()
            if code not in line_codes:
                line_codes.append(code)
            if code not in error_codes:
                error_codes.append(code)

        ts_match = _TIMESTAMP_RE.search(stripped)
        lvl_match = _LEVEL_RE.search(stripped)
        if ts_match or lvl_match or line_codes:
            timestamp = ts_match.group(1) if ts_match else "N/A"
            level = _normalize_level(lvl_match.group(1)) if lvl_match else (
                "ERROR" if line_codes else "INFO"
            )
            remainder = stripped
            if ts_match:
                remainder = remainder.replace(ts_match.group(0), "", 1).strip()
            if lvl_match:
                remainder = remainder.replace(lvl_match.group(0), "", 1).strip()

            comp = "System"
            comp_match = _COMPONENT_RE.search(remainder)
            if comp_match:
                comp = (comp_match.group(1) or comp_match.group(2) or "System").strip()

            events.append(
                LogEvent(
                    timestamp=timestamp,
                    level=level,
                    component=comp,
                    message=remainder[:320],
                    error_code=line_codes[0] if line_codes else "",
                )
            )

    return PlatformContextData(
        session_id="RAW-LOG",
        source_type="raw_log",
        environment=PlatformEnvironment(
            platform=detected_platform,
            build=detected_build,
            os=detected_os,
        ),
        events=events[:20],
        extracted_error_codes=error_codes,
        raw_excerpt=cleaned_text[:1200],
        pii_redactions=pii_result.redactions,
    )


def merge_platform_contexts(
    primary: PlatformContextData | None,
    secondary: PlatformContextData | None,
) -> PlatformContextData | None:
    if primary is None:
        return secondary
    if secondary is None:
        return primary

    merged_codes = list(primary.extracted_error_codes)
    for code in secondary.extracted_error_codes:
        if code not in merged_codes:
            merged_codes.append(code)

    merged_redactions = list(primary.pii_redactions)
    for red in secondary.pii_redactions:
        if red not in merged_redactions:
            merged_redactions.append(red)

    env = PlatformEnvironment(
        application=primary.environment.application or secondary.environment.application,
        platform=primary.environment.platform or secondary.environment.platform,
        build=primary.environment.build or secondary.environment.build,
        os=primary.environment.os or secondary.environment.os,
        hardware_summary=primary.environment.hardware_summary or secondary.environment.hardware_summary,
    )

    excerpts = [p for p in (primary.raw_excerpt, secondary.raw_excerpt) if p]

    return PlatformContextData(
        session_id=f"{primary.session_id}+{secondary.session_id}",
        source_type=primary.source_type,
        environment=env,
        events=[*primary.events, *secondary.events][:25],
        extracted_error_codes=merged_codes,
        raw_excerpt="\n---\n".join(excerpts)[:1800],
        pii_redactions=merged_redactions,
    )
