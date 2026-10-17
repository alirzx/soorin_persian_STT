from fastapi import APIRouter,Request
from fastapi.responses import JSONResponse
router=APIRouter()
@router.get('/health/live')
def live():
    return {'status':'alive'}
@router.get('/health/ready')
def ready(request:Request):
    state=request.app.state.service
    return JSONResponse(status_code=200 if state.ready else 503,
            content={'ready':state.ready,'model':state.model.name if state.model else None,
                     'error':state.load_error})
@router.get('/v1/models/current')
def current(request:Request):
    state=request.app.state.service
    model=state.model
    return {'ready':state.ready,'name':model.name if model else None,
            'backend':model.backend if model else None,'repo':model.repo if model else None,
            'revision':(state.model_revision or model.revision) if model else None,'license':model.license if model else None,
            'streaming_mode':('native' if state.backend.features.true_streaming else 'buffered') if state.backend else None}
@router.get('/version')
def version():
    from soorin_stt import __version__
    return {'api':'v1','version':__version__}
