from fastapi import Request
from fastapi.responses import JSONResponse
from soorin_stt.core.exceptions import STTError

async def handle_stt_error(request:Request,exc:STTError):
    return JSONResponse(status_code=exc.status,content={'error':{'code':exc.code,'message':str(exc)}})
