from fastapi import HTTPException
from src.constants.enums import ReviewStatus, DecisionAction
from src.models.entities import AlignmentReview
from src.utils import repository as repo
from src.utils.identity import new_id, now


def list_reviews():
    return repo.all_rows("reviews")


def _normalize(review: dict) -> dict:
    review.setdefault("decisions", [])
    review.setdefault("effective_decision_id", "")
    review.setdefault("revoked_reason", "")
    return review


def create(data, user):
    run = repo.get("runs", data.run_id)
    if run["status"] != "completed":
        raise ValueError("只有已完成的运行可提交复核")
    # 待审复核不可重复提审；已批准（有效批准）复核必须先撤销才能重新提审；
    # 已退回或已撤销的复核允许重新提审，形成新一轮完整决定链。
    blocked = [
        r for r in repo.all_rows("reviews")
        if r["run_id"] == data.run_id and r["status"] in (
            ReviewStatus.PENDING.value, ReviewStatus.APPROVED.value,
        )
    ]
    if blocked:
        raise HTTPException(409, "该运行已有待审或通过的复核")
    item = AlignmentReview(new_id("rev"), data.run_id, data.comment, created_at=now())
    return repo.put("reviews", item)


def decide(id, data, user):
    with repo.transaction() as (conn, q):
        item = _normalize(repo.tx_get(conn, q, "reviews", id))
        if item["status"] != ReviewStatus.PENDING.value:
            raise HTTPException(409, "该复核已处理，不能重复决定")
        if data.status not in (DecisionAction.APPROVE.value, DecisionAction.REJECT.value):
            raise ValueError("复核决定只能是批准或退回")
        decision = {
            "id": new_id("dec"),
            "action": data.status,
            "comment": data.comment,
            "actor": user["email"],
            "created_at": now(),
        }
        item["decisions"].append(decision)
        item["status"] = data.status
        item["comment"] = data.comment
        item["reviewer"] = user["email"]
        if data.status == DecisionAction.APPROVE.value:
            item["effective_decision_id"] = decision["id"]
        repo.tx_put(conn, q, "reviews", item)
        return item


def revoke(id, data, user):
    """撤销有效批准并填写原因；同一事务内将关联有效报告全部置为失效。"""
    with repo.transaction() as (conn, q):
        item = _normalize(repo.tx_get(conn, q, "reviews", id))
        if item["status"] != ReviewStatus.APPROVED.value:
            raise HTTPException(409, "只有已通过且仍有效的复核可以撤销")
        reason = (data.reason or "").strip()
        if len(reason) < 5:
            raise ValueError("撤销原因至少 5 个字符，须留档可追查")
        decision = {
            "id": new_id("dec"),
            "action": DecisionAction.REVOKE.value,
            "comment": reason,
            "actor": user["email"],
            "created_at": now(),
        }
        item["decisions"].append(decision)
        item["status"] = ReviewStatus.REVOKED.value
        item["reviewer"] = user["email"]
        item["effective_decision_id"] = ""
        item["revoked_reason"] = reason
        repo.tx_put(conn, q, "reviews", item)

        invalidated = 0
        for report in repo.tx_all_rows(conn, q, "reports"):
            if report["review_id"] == id and report.get("status", "active") == "active":
                report["status"] = "invalid"
                report["invalid_reason"] = f"批准已撤销：{reason}"
                repo.tx_put(conn, q, "reports", report)
                invalidated += 1
        return {"review": item, "invalidated_reports": invalidated}
