"""采集源适配器接口与公共异常（T-1）。

必选方法 ``fetch_issue`` 采用现有采集源（NcpssdSource / ElsevierSource）已经在用的
签名，因此接入新源时老源只需补充下面的类属性即可完成能力声明，不必重写内部逻辑。

类属性是对外的「能力声明」，供采集源注册表与前端读取：

- ``source_id``：源的唯一标识，同时作为 raw_issue / crawl_task 的采集身份
- ``region``：期刊来源区域（domestic / foreign），用于语言推断与前端分组
- ``ingest_scope``：采集粒度（issue / year），用于任务参数校验与前端表单切换
- ``capabilities``：可选能力开关；未实现的可选方法必须声明为 False
- ``config_fields``：该源在期刊配置中需要填写的字段，前端据此动态渲染配置表单
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PdfDownload:
    content: bytes
    source_url: str
    content_type: str | None = None


class ProviderError(Exception):
    pass


class SourceAdapter:
    """采集源统一接口。"""

    source_id = "base"
    display_name = ""
    region = ""
    metadata_priority = 100
    ingest_scope = "issue"
    capabilities = {
        "list_issues": False,
        "download_pdf": False,
        "needs_browser": False,
    }
    config_fields = []

    def fetch_issue(self, journal_name, year, issue, **kwargs):
        """采集某一期的题录数据，返回 ``{"issue": {...}, "papers": [...]}``。"""
        raise NotImplementedError

    def list_issues(self, journal_name, year, **kwargs):
        """列出某年全部可用期号。仅 ``capabilities["list_issues"]`` 为真的源需要实现。"""
        raise NotImplementedError

    def download_pdf(self, paper_ref, **kwargs):
        """下载单篇全文 PDF。仅 ``capabilities["download_pdf"]`` 为真的源需要实现。"""
        raise NotImplementedError

    def test_connection(self, **kwargs):
        """校验源配置是否可用，返回 ``check_result`` 结构，供前端「测试连接」使用。"""
        return check_result("warn", "该采集源未提供连通性测试")


def check_result(status, message, checked_at=None):
    """统一测试连接的结果结构。status 取值：ok / warn / failed。"""
    return {
        "status": status,
        "message": message,
        "checked_at": (checked_at or datetime.now()).isoformat(timespec="seconds"),
    }
