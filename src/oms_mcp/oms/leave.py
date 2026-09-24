from typing import Any

from oms_mcp.schemas import LeaveList, LeaveRequest, LeaveSummary


def normalize_leaves(payload: Any, page: int, size: int) -> LeaveList:
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    items = data if isinstance(data, list) else next(
        (data[k] for k in ("results", "items", "leaves", "rows") if isinstance(data, dict) and isinstance(data.get(k), list)), []
    )
    requests = [LeaveRequest(
        id=item.get("id"), status=item.get("status"),
        start_date=item.get("start_date", item.get("startDate")),
        end_date=item.get("end_date", item.get("endDate")), raw=item,
    ) for item in items if isinstance(item, dict)]
    return LeaveList(requests=requests, page=page, size=size, raw=payload)


def normalize_leave_summary(payload: Any) -> LeaveSummary:
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(data, dict):
        return LeaveSummary(raw=payload)
    return LeaveSummary(
        available=data.get("available", data.get("total_available")),
        consumed=data.get("consumed", data.get("used")),
        remaining=data.get("remaining", data.get("balance")), raw=payload,
    )
