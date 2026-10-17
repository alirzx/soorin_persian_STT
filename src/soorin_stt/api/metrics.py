from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import Response
from prometheus_client import generate_latest,CONTENT_TYPE_LATEST
router=APIRouter()
@router.get('/metrics')
def metrics(request:Request):
    if not request.app.state.service.settings.metrics_enabled:
        raise HTTPException(status_code=404)
    return Response(generate_latest(),media_type=CONTENT_TYPE_LATEST)
