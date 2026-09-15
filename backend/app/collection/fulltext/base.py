"""全文提供器合同与可持久化错误分类。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FullTextReference:
    provider_id: str
    paper_ref: dict
    action_url: str | None = None


class FullTextProviderError(Exception):
    code = "remote_error"
    requires_user_action = False

    def __init__(self, message, action_url=None):
        super().__init__(message)
        self.action_url = action_url


class HumanVerificationRequired(FullTextProviderError):
    code = "verification_required"
    requires_user_action = True


class AccessBlockedError(FullTextProviderError):
    code = "access_blocked"
    requires_user_action = True


class AccessDeniedError(FullTextProviderError):
    code = "access_denied"


class NotPdfError(FullTextProviderError):
    code = "not_pdf"


class TooLargeError(FullTextProviderError):
    code = "too_large"


class NetworkError(FullTextProviderError):
    code = "network_error"
