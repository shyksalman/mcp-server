from typing import Any

from oms_mcp.schemas import AttendanceStats


def normalize_attendance(payload: Any) -> AttendanceStats:
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(data, dict):
        return AttendanceStats(raw=payload)
    return AttendanceStats(
        present=data.get("present") or data.get("total_present"),
        absent=data.get("absent") or data.get("total_absent"),
        name=data.get("name"),
        designation_name=data.get("designation_name"),
        attendance_list=data.get("attendance_list"),
        raw=payload,
    )
