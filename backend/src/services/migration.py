"""旧数据升级：为既有复核补全决定历史、为既有报告补全决定绑定与状态。

幂等执行：已具备新字段的记录不重复处理。升级后原有复核和报告仍可查阅，
旧报告默认继承其复核当前状态对应的可下载性（演示库中的历史批准报告保持有效）。
"""
from src.utils import repository as repo
from src.constants.enums import ReviewStatus, ReportStatus
from src.utils.identity import now


def _legacy_decision_id(review_id: str) -> str:
    return f"dec-legacy-{review_id}"


def migrate():
    upgraded = {"reviews": 0, "reports": 0}
    # 复核：补全 decisions / effective_decision_id / revoked_reason
    for review in repo.all_rows("reviews"):
        changed = False
        review.setdefault("decisions", [])
        review.setdefault("revoked_reason", "")
        review.setdefault("effective_decision_id", "")
        if not review["decisions"] and review["status"] in (
            ReviewStatus.APPROVED.value,
            ReviewStatus.REJECTED.value,
        ):
            decision = {
                "id": _legacy_decision_id(review["id"]),
                "action": review["status"],
                "comment": review.get("comment", "") or "历史数据迁移：保留原复核意见。",
                "actor": review.get("reviewer", "") or "legacy-system",
                "created_at": review.get("created_at") or now(),
            }
            review["decisions"].append(decision)
            changed = True
        if review["status"] == ReviewStatus.APPROVED.value and not review["effective_decision_id"]:
            review["effective_decision_id"] = review["decisions"][-1]["id"]
            changed = True
        if changed:
            repo.put("reviews", review)
            upgraded["reviews"] += 1

    # 报告：补全 decision_id / status / invalid_reason
    effective = {}
    for review in repo.all_rows("reviews"):
        if review.get("effective_decision_id"):
            effective[review["id"]] = review["effective_decision_id"]
    for report in repo.all_rows("reports"):
        changed = False
        report.setdefault("invalid_reason", "")
        if "status" not in report:
            report["status"] = ReportStatus.ACTIVE.value
            changed = True
        if not report.get("decision_id"):
            report["decision_id"] = effective.get(report["review_id"], _legacy_decision_id(report["review_id"]))
            changed = True
        if changed:
            repo.put("reports", report)
            upgraded["reports"] += 1
    return upgraded
