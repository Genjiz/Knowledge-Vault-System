"""采集源动作执行器。

把「测试连接」「探测期号」这类需要落到具体采集源的动作收口在一处，
路由层只依赖本执行器的调用契约，测试可整体注入替换，不必发起真实网络请求。
"""
from app.collection.sources.registry import describe_source, get_source


class SourceRunner:
    """按注册表构造源实例并执行动作。

    调用契约为 ``test_connection(source_id, config, journal_name=None)`` 与
    ``list_issues(source_id, config, year, journal_name=None)``，
    与具体采集源的类结构解耦，便于测试与未来替换为异步执行器。
    """

    def test_connection(self, source_id, config, journal_name=None):
        source = get_source(source_id, config)
        return source.test_connection(journal_name=journal_name)

    def list_issues(self, source_id, config, year, journal_name=None):
        source = get_source(source_id, config)
        return source.list_issues(journal_name or "", year)

    def describe(self, source_id):
        return describe_source(source_id)
