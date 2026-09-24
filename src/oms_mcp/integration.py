"""Manual live OMS smoke test. Requires credentials; never prints tokens."""

import asyncio
import json

from oms_mcp.config import load_settings
from oms_mcp.exceptions import OMSError
from oms_mcp.oms.client import OMSClient


async def run() -> None:
    settings = load_settings()
    settings.require_credentials()
    async with OMSClient(settings) as client:
        for name, operation in (
            ("attendance", client.get_attendance_stats),
            ("leaves", lambda: client.get_leaves(size=5)),
            ("leave_summary", client.get_leave_summary),
        ):
            try:
                result = await operation()
                output = result.model_dump(exclude={"raw": True, "requests": {"__all__": {"raw"}}})
                print(f"{name}: {json.dumps(output, default=str)}")
            except OMSError as exc:
                print(f"{name}: {exc}")


if __name__ == "__main__":
    asyncio.run(run())
