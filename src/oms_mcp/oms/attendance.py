from typing import Any

from oms_mcp.schemas import AttendanceStats


def normalize_attendance(payload: Any) -> AttendanceStats:
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(data, dict):
        return AttendanceStats(raw=payload)
    return AttendanceStats(
        name=data.get("name"),
        designation_name=data.get("designation_name"),
        attendance_list=data.get("attendance_list"),
        raw=payload,
    )
