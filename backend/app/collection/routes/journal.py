"""期刊与采集源配置 API（T-1/T-5 数据基础）。

期刊是一等实体，落在 papers 域；采集源相关的配置、测试与期号探测属于 collection 域，
依赖方向保持 collection → papers。源动作经 SourceRunner 执行，测试可整体注入替换。
"""
import json
from datetime import UTC, datetime

from flask import Blueprint, current_app, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.collection.models.raw_issue import RawIssue
from app.collection.services.source_runner import SourceRunner
from app.collection.sources.registry import describe_source, source_ids
from app.core import error_response, success_response
from app.core.extensions import db
from app.papers.models import Journal, JournalSourceConfig

journal_bp = Blueprint("journal", __name__, url_prefix="/api/journals")

# 期刊区域值域：决定可选采集源范围与论文语言语义
VALID_REGIONS = {"domestic", "foreign"}

DEFAULT_STATS = {"issue_count": 0, "last_collected_at": None}


def _runner():
    """取源动作执行器；测试可用 app.config["JOURNAL_SOURCE_RUNNER"] 注入。"""
    return current_app.config.get("JOURNAL_SOURCE_RUNNER") or SourceRunner()


def _collect_stats():
    """按期刊名汇总已采集期数与最近采集时间，一次查询避免逐刊回表。"""
    rows = (
        db.session.query(
            RawIssue.journal_name,
            func.count(RawIssue.id),
            func.max(RawIssue.created_at),
        )
        .group_by(RawIssue.journal_name)
        .all()
    )
    return {
        name: {
            "issue_count": count,
            "last_collected_at": collected_at.replace(tzinfo=UTC).isoformat(timespec="seconds")
            if collected_at
            else None,
        }
        for name, count, collected_at in rows
    }


def _journal_payload(journal, stats):
    payload = journal.to_dict()
    payload["stats"] = stats.get(journal.name, dict(DEFAULT_STATS))
    return payload


def _get_journal(journal_id):
    return db.session.get(Journal, journal_id)


def _load_config(row):
    if not row.config_json:
        return {}
    try:
        return json.loads(row.config_json)
    except (TypeError, ValueError):
        return {}


def _dump_config(config):
    return json.dumps(config, ensure_ascii=False) if config else None


def _normalize_config(meta, raw_config):
    """只保留源声明过的配置键，避免脏数据进入源构造与落库。"""
    config = dict(raw_config or {})
    declared = [field["key"] for field in meta["config_fields"]]
    return {key: config[key] for key in declared if key in config}


def _missing_required(meta, config):
    return [
        field["key"]
        for field in meta["config_fields"]
        if field.get("required") and not str(config.get(field["key"]) or "").strip()
    ]


def _clean_region(value):
    """region 入参校验：空值放行（允许暂不设置），非空必须是合法值域。"""
    region = (value or "").strip()
    if not region:
        return None
    if region not in VALID_REGIONS:
        return False
    return region


@journal_bp.route("", methods=["GET"])
def list_journals():
    stats = _collect_stats()
    journals = Journal.query.order_by(Journal.name).all()
    return success_response([_journal_payload(journal, stats) for journal in journals])


@journal_bp.route("", methods=["POST"])
def create_journal():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return error_response("期刊名称为必填项")

    if Journal.query.filter_by(name=name).first():
        return error_response("期刊已存在", 409)

    region = _clean_region(data.get("region"))
    if region is False:
        return error_response(f"region 取值不合法，可选值：{sorted(VALID_REGIONS)}")

    journal = Journal(
        name=name,
        issn=data.get("issn"),
        publisher=data.get("publisher"),
        region=region,
    )
    db.session.add(journal)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response("期刊已存在", 409)
    return success_response(_journal_payload(journal, _collect_stats()))


@journal_bp.route("/<int:journal_id>", methods=["PUT"])
def update_journal(journal_id):
    journal = _get_journal(journal_id)
    if journal is None:
        return error_response("期刊不存在", 404)

    data = request.get_json() or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return error_response("期刊名称为必填项")
        duplicated = Journal.query.filter(Journal.name == name, Journal.id != journal_id).first()
        if duplicated:
            return error_response("期刊已存在", 409)
        journal.name = name
    if "issn" in data:
        journal.issn = data.get("issn")
    if "publisher" in data:
        journal.publisher = data.get("publisher")
    if "region" in data:
        region = _clean_region(data.get("region"))
        if region is False:
            return error_response(f"region 取值不合法，可选值：{sorted(VALID_REGIONS)}")
        journal.region = region

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response("期刊已存在", 409)
    return success_response(_journal_payload(journal, _collect_stats()))


@journal_bp.route("/<int:journal_id>", methods=["DELETE"])
def delete_journal(journal_id):
    journal = _get_journal(journal_id)
    if journal is None:
        return error_response("期刊不存在", 404)

    db.session.delete(journal)
    db.session.commit()
    return success_response({"id": journal_id})


@journal_bp.route("/<int:journal_id>/sources", methods=["PUT"])
def replace_journal_sources(journal_id):
    """整体替换该期刊的采集源配置。

    提交该期刊全部源配置，未提交的源视为不再可用并删除；同一期刊至多一个默认源，
    显式标记时以最后提交者为准，均未标记时取第一个已启用源，避免采集台无默认可选。
    """
    journal = _get_journal(journal_id)
    if journal is None:
        return error_response("期刊不存在", 404)

    data = request.get_json() or {}
    items = data.get("sources")
    if not isinstance(items, list):
        return error_response("sources 必须为数组")

    known = source_ids()
    desired = []
    seen = set()
    for item in items:
        source_id = (item.get("source_id") or "").strip()
        if not source_id:
            return error_response("每项配置都必须提供 source_id")
        if source_id not in known:
            return error_response(f"不支持的采集源：{source_id}，可选值：{sorted(known)}")
        if source_id in seen:
            return error_response(f"采集源重复提交：{source_id}")
        seen.add(source_id)

        meta = describe_source(source_id)
        enabled = bool(item.get("enabled", True))
        # 采集源有区域归属，与期刊区域不一致的源没有采集意义（国内期刊用不了 Elsevier）
        if journal.region and meta["region"] and meta["region"] != journal.region:
            return error_response(
                f"{meta['display_name']} 属于{'国内' if meta['region'] == 'domestic' else '国外'}源，"
                f"与期刊区域（{'国内' if journal.region == 'domestic' else '国外'}）不符，请先调整期刊区域"
            )
        config = _normalize_config(meta, item.get("config"))
        missing = _missing_required(meta, config)
        # 未启用的源允许先占位、稍后补配置，因此只在启用时校验必填项
        if enabled and missing:
            return error_response(
                f"{meta['display_name']} 缺少必填配置项：{', '.join(missing)}"
            )
        if enabled and meta["ingest_scope"] == "year" and not (journal.issn or "").strip():
            return error_response(
                f"{meta['display_name']} 按 ISSN 检索，请先填写期刊 ISSN"
            )
        desired.append(
            {
                "source_id": source_id,
                "enabled": enabled,
                "is_default": bool(item.get("is_default", False)),
                "config": config,
            }
        )

    default_source_id = None
    for item in desired:
        if item["is_default"] and item["enabled"]:
            default_source_id = item["source_id"]
    if default_source_id is None:
        for item in desired:
            if item["enabled"]:
                default_source_id = item["source_id"]
                break

    existing = {row.source_id: row for row in journal.source_configs}
    for source_id, row in existing.items():
        if source_id not in seen:
            db.session.delete(row)

    for item in desired:
        row = existing.get(item["source_id"])
        if row is None:
            row = JournalSourceConfig(journal_id=journal_id, source_id=item["source_id"])
            db.session.add(row)
        row.enabled = item["enabled"]
        row.is_default = item["source_id"] == default_source_id
        row.config_json = _dump_config(item["config"])

    db.session.commit()
    db.session.refresh(journal)
    return success_response(_journal_payload(journal, _collect_stats()))


@journal_bp.route("/<int:journal_id>/sources/<source_id>/test", methods=["POST"])
def test_journal_source(journal_id, source_id):
    """测试该期刊某个源的配置是否可用，结果落库供列表页直接展示。"""
    journal = _get_journal(journal_id)
    if journal is None:
        return error_response("期刊不存在", 404)

    row = JournalSourceConfig.query.filter_by(journal_id=journal_id, source_id=source_id).first()
    if row is None:
        return error_response("该期刊尚未配置此采集源", 404)

    config = _load_config(row)
    try:
        result = _runner().test_connection(
            source_id,
            config,
            journal_name=journal.name,
            issn=journal.issn,
        )
    except Exception as exc:  # 源实现抛出的任何异常都按失败落库，不向上冒泡
        result = {"status": "failed", "message": str(exc)}

    row.last_check_status = result.get("status") or "failed"
    row.last_check_message = result.get("message")
    row.last_checked_at = datetime.now(UTC)
    db.session.commit()
    return success_response(row.to_dict())


@journal_bp.route("/<int:journal_id>/issues", methods=["GET"])
def probe_issues(journal_id):
    """探测某期刊在某源下指定年份的可用期号，供采集台点选。"""
    journal = _get_journal(journal_id)
    if journal is None:
        return error_response("期刊不存在", 404)

    source_id = (request.args.get("source_id") or "").strip()
    year = request.args.get("year", type=int)
    if not source_id:
        return error_response("source_id 为必填项")
    if year is None:
        return error_response("year 为必填项")

    meta = describe_source(source_id)
    if meta is None:
        return error_response(f"不支持的采集源：{source_id}，可选值：{sorted(source_ids())}")
    if not meta["capabilities"].get("list_issues"):
        return error_response(f"{meta['display_name']} 不支持列期号，请手工填写期号")

    row = JournalSourceConfig.query.filter_by(journal_id=journal_id, source_id=source_id).first()
    if row is None:
        return error_response("该期刊尚未配置此采集源", 404)

    config = _load_config(row)
    try:
        issues = _runner().list_issues(source_id, config, year, journal_name=journal.name)
    except Exception as exc:
        return error_response(f"探测期号失败：{exc}")

    return success_response(
        {
            "journal_name": journal.name,
            "source_id": source_id,
            "year": year,
            "capabilities": meta["capabilities"],
            "issues": issues,
        }
    )
