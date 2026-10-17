from soorin_stt.streaming.stabilizer import stable_prefix
from soorin_stt.streaming.backpressure import SessionCapacity
import pytest
from soorin_stt.core.exceptions import Overloaded

def test_stable():
    assert stable_prefix('روی سرور ویندوز','روی سرور لینوکس')=='روی سرور'

@pytest.mark.asyncio
async def test_capacity():
    limit=SessionCapacity(1)
    await limit.enter()
    with pytest.raises(Overloaded):await limit.enter()
    await limit.leave()
    await limit.enter()
    await limit.leave()
