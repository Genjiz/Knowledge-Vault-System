"""采集源适配器接口与公共异常（T-1 骨架）。

各采集源（国家哲社文献中心、Elsevier、知网、期刊官网等）通过实现 SourceAdapter
接入；本期现有 NcpssdSource / ElsevierSource 尚未实现该接口，适配工作在 T-1 任务中落地。
"""


class ProviderError(Exception):
    pass


class SourceAdapter:
    """采集源统一接口。"""

    source_id = "base"

    def list_issues(self, journal, **kwargs):
        raise NotImplementedError

    def fetch_issue_metadata(self, issue_ref, **kwargs):
        raise NotImplementedError

    def fetch_paper_metadata(self, paper_ref, **kwargs):
        raise NotImplementedError

    def download_pdf(self, paper_ref, **kwargs):
        raise NotImplementedError
