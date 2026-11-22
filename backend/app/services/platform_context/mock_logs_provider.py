from app.models.schemas import (
    LogEvent,
    PlatformContextData,
    PlatformEnvironment,
    PlatformSessionSummary,
)
from app.services.platform_context.base import PlatformContextProvider

_MOCK_SESSIONS: list[tuple[PlatformSessionSummary, PlatformContextData]] = [
    (
        PlatformSessionSummary(
            session_id="PED-9042",
            title="Checkout Web — Divergência cartão vs. timeout",
            application="YouShop Checkout",
            build="v2.14.3",
            summary="Cliente achou que o cartão recusou, mas o log mostra HTTP 504 no gateway.",
        ),
        PlatformContextData(
            session_id="PED-9042",
            source_type="mock_telemetry",
            environment=PlatformEnvironment(
                application="YouShop Checkout",
                platform="Web (Chrome 131)",
                build="v2.14.3",
                os="Windows 11",
                hardware_summary="Desktop Browser",
            ),
            events=[
                LogEvent(
                    timestamp="2026-11-21 11:02:14",
                    level="INFO",
                    component="CheckoutStep",
                    message="PaymentSubmit initiated for order PED-9042 (item=Tenis Runner Pro, method=CREDIT_CARD).",
                ),
                LogEvent(
                    timestamp="2026-11-21 11:02:29",
                    level="ERROR",
                    component="PaymentGateway",
                    message="HTTP 504 Gateway Timeout after 15000ms awaiting acquirer response.",
                    error_code="ERR_GW_504_TIMEOUT",
                ),
                LogEvent(
                    timestamp="2026-11-21 11:02:29",
                    level="WARN",
                    component="OrderService",
                    message="Order PED-9042 marked PENDING_TIMEOUT (not card declined by issuer).",
                ),
            ],
            extracted_error_codes=["ERR_GW_504_TIMEOUT", "HTTP 504"],
            raw_excerpt="11:02:29 ERROR [PaymentGateway] HTTP 504 Gateway Timeout (ERR_GW_504_TIMEOUT); Order marked PENDING_TIMEOUT (not card declined).",
        ),
    ),
    (
        PlatformSessionSummary(
            session_id="SESS-YS-104",
            title="YouShop Checkout — Cupom removido no PIX",
            application="YouShop Checkout",
            build="v2.14.3",
            summary="Estado do cupom BEMVINDO10 resetado ao alternar forma de pagamento para PIX.",
        ),
        PlatformContextData(
            session_id="SESS-YS-104",
            source_type="mock_telemetry",
            environment=PlatformEnvironment(
                application="YouShop Checkout",
                platform="Desktop (Google Chrome)",
                build="v2.14.3",
                os="Windows 11 x64",
                hardware_summary="Desktop Browser x64",
            ),
            events=[
                LogEvent(
                    timestamp="2026-11-21 14:12:03",
                    level="INFO",
                    component="CartService",
                    message="Coupon BEMVINDO10 applied (discount=10%, subtotal=269.91).",
                ),
                LogEvent(
                    timestamp="2026-11-21 14:12:19",
                    level="WARN",
                    component="PaymentSelector",
                    message="PaymentMethod switched to PIX -> recalculateTotals() triggered.",
                ),
                LogEvent(
                    timestamp="2026-11-21 14:12:19",
                    level="ERROR",
                    component="CouponStateReducer",
                    message="Coupon BEMVINDO10 cleared on PIX payload rebuild; subtotal reverted to 299.90.",
                    error_code="ERR_COUPON_RESET_PIX",
                ),
            ],
            extracted_error_codes=["ERR_COUPON_RESET_PIX"],
            raw_excerpt="14:12:19 ERROR [CouponStateReducer] ERR_COUPON_RESET_PIX: Coupon BEMVINDO10 cleared on PIX payload rebuild.",
        ),
    ),
    (
        PlatformSessionSummary(
            session_id="SESS-YS-218",
            title="YouShop Mobile Web — Cópia PIX bloqueada no Safari",
            application="YouShop Mobile Web",
            build="v2.14.3",
            summary="Permissão de clipboard bloqueada no Safari iOS ao tocar em Copiar código PIX.",
        ),
        PlatformContextData(
            session_id="SESS-YS-218",
            source_type="mock_telemetry",
            environment=PlatformEnvironment(
                application="YouShop Mobile Web",
                platform="Mobile (iPhone Safari 18)",
                build="v2.14.3",
                os="iOS 18",
                hardware_summary="iPhone Mobile Web",
            ),
            events=[
                LogEvent(
                    timestamp="2026-11-21 15:20:01",
                    level="INFO",
                    component="PixPaymentService",
                    message="PIX QR Code and EMV payload generated successfully.",
                ),
                LogEvent(
                    timestamp="2026-11-21 15:20:08",
                    level="ERROR",
                    component="ClipboardBridge",
                    message="NotAllowedError: navigator.clipboard.writeText rejected after async PIX fetch in iOS Safari.",
                    error_code="ERR_IOS_CLIPBOARD_DENIED",
                ),
            ],
            extracted_error_codes=["ERR_IOS_CLIPBOARD_DENIED", "NotAllowedError"],
            raw_excerpt="15:20:08 ERROR [ClipboardBridge] ERR_IOS_CLIPBOARD_DENIED NotAllowedError: navigator.clipboard.writeText rejected in iOS Safari.",
        ),
    ),
    (
        PlatformSessionSummary(
            session_id="SESS-YS-309",
            title="YouShop Painel WhatsApp — Erro ao abrir pedido",
            application="YouShop Painel WhatsApp",
            build="v3.8.1",
            summary="TypeError fatal no clique com mouse na linha do pedido dentro do painel WhatsApp.",
        ),
        PlatformContextData(
            session_id="SESS-YS-309",
            source_type="mock_telemetry",
            environment=PlatformEnvironment(
                application="YouShop Painel WhatsApp",
                platform="Desktop (Google Chrome)",
                build="v3.8.1",
                os="Windows 11 x64",
                hardware_summary="Intel Core i7-12700F, 16 GB RAM, 64-bit x64",
            ),
            events=[
                LogEvent(
                    timestamp="2026-11-21 16:04:10",
                    level="INFO",
                    component="WhatsAppQueueUI",
                    message="Agent opened ticket #WA-8821 -> tab PedidoHistory.",
                ),
                LogEvent(
                    timestamp="2026-11-21 16:04:22",
                    level="WARN",
                    component="InputHandler",
                    message="KeyboardArrowNavigation on OrderRow -> preview skipped safely.",
                ),
                LogEvent(
                    timestamp="2026-11-21 16:04:27",
                    level="FATAL",
                    component="OrderRowComponent",
                    message="TypeError in OrderRow.onMouseClick(): orderDetails is undefined -> SessionTerminated(code=500).",
                    error_code="ERR_PANEL_ROW_0x4F",
                ),
            ],
            extracted_error_codes=["ERR_PANEL_ROW_0x4F", "TypeError"],
            raw_excerpt="16:04:27 FATAL [OrderRowComponent] ERR_PANEL_ROW_0x4F TypeError: OrderRow.onMouseClick() -> orderDetails is undefined.",
        ),
    ),
]


class MockLogsProvider(PlatformContextProvider):
    def __init__(self) -> None:
        self._by_id: dict[str, PlatformContextData] = {
            summary.session_id.upper(): data for summary, data in _MOCK_SESSIONS
        }
        self._summaries: list[PlatformSessionSummary] = [
            summary for summary, _ in _MOCK_SESSIONS
        ]

    def list_sessions(self) -> list[PlatformSessionSummary]:
        return list(self._summaries)

    def lookup_session(self, session_id: str) -> PlatformContextData | None:
        cleaned = session_id.strip().upper()
        if not cleaned:
            return None
        return self._by_id.get(cleaned)
