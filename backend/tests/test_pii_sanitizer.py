from app.domain.pii_sanitizer import scan_and_sanitize


def test_sanitizer_removes_sensitive_ids_and_preserves_useful_specs() -> None:
    sample = (
        "Outro tester testou esse mesmo bug. As especificações do PC são:\n"
        "Nome do dispositivo\n"
        "QA-PC0036\n"
        "Nome completo do dispositivo\n"
        "[QA-PC0036.exemplo.local](http://QA-PC0036.exemplo.local)\n"
        "Processador\n"
        "12th Gen Intel(R) Core(TM) i7-12700F (2.10 GHz)\n"
        "RAM instalada\n"
        "16,0 GB (utilizável: 15,8 GB)\n"
        "ID do dispositivo\n"
        "00000000-0000-0000-0000-000000000000\n"
        "ID do Produto\n"
        "00000-00000-00000-XXXXX\n"
        "Tipo de sistema\n"
        "Sistema operacional de 64 bits, processador baseado em x64\n"
    )

    result = scan_and_sanitize(sample)

    assert "QA-PC0036" not in result.sanitized_text
    assert "exemplo.local" not in result.sanitized_text
    assert "00000000-0000-0000-0000-000000000000" not in result.sanitized_text
    assert "00000-00000-00000-XXXXX" not in result.sanitized_text

    assert "Intel(R) Core(TM) i7-12700F" in result.sanitized_text
    assert "16,0 GB" in result.sanitized_text
    assert "x64" in result.sanitized_text

    assert len(result.redactions) >= 3
    assert len(result.warnings) >= 3


def test_sanitizer_redacts_inline_email_and_ip() -> None:
    text = "Contato tester@empresa.com no IP 192.168.10.25 na build DEMO 1.0."
    result = scan_and_sanitize(text)

    assert "tester@empresa.com" not in result.sanitized_text
    assert "192.168.10.25" not in result.sanitized_text
    assert "DEMO 1.0" in result.sanitized_text
