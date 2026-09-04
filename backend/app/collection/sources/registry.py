"""采集源注册表。

注册表是 source_id 与采集源实现之间的唯一映射：服务层据此构造源实例，
API 据此校验与向前端描述源能力。新增采集源时在这里登记即可全链路生效。
"""
from app.collection.sources.elsevier import ElsevierSource
from app.collection.sources.magtech import MagtechSource
from app.collection.sources.ncpssd import NcpssdSource

SOURCE_CLASSES = {
    "ncpssd": NcpssdSource,
    "magtech": MagtechSource,
    "elsevier": ElsevierSource,
}


def source_ids():
    """全部已注册的 source_id 集合。"""
    return set(SOURCE_CLASSES)


def get_source(source_id, config=None):
    """按 source_id 与期刊级配置构造采集源实例。

    配置项只透传该源在 ``config_fields`` 中声明过的键，未声明字段一律忽略，
    避免期刊配置里的脏数据传入源构造函数。
    """
    cls = SOURCE_CLASSES.get(source_id)
    if cls is None:
        raise ValueError(f"Unsupported source id: {source_id}")

    config = dict(config or {})
    kwargs = {
        field["key"]: config[field["key"]]
        for field in cls.config_fields
        if field["key"] in config
    }
    return cls(**kwargs)


def describe_source(source_id):
    """单个源的元信息，未知 source_id 返回 None。"""
    cls = SOURCE_CLASSES.get(source_id)
    if cls is None:
        return None
    return {
        "source_id": cls.source_id,
        "display_name": cls.display_name,
        "region": cls.region,
        "capabilities": dict(cls.capabilities),
        "config_fields": [dict(field) for field in cls.config_fields],
    }


def describe_sources():
    """返回给前端的源元信息与能力清单。"""
    return [describe_source(source_id) for source_id in SOURCE_CLASSES]
