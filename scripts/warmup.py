#!/usr/bin/env python3
import asyncio
from soorin_stt.core.config import get_settings
from soorin_stt.core.lifecycle import ServiceState
async def main():
    service=ServiceState(get_settings())
    await service.start()
    print({'ready':service.ready,'error':service.load_error})
    ok=service.ready
    await service.stop()
    if not ok:raise SystemExit(1)
if __name__=='__main__':asyncio.run(main())
