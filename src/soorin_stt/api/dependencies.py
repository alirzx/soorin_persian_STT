from fastapi import Request,HTTPException
from soorin_stt.core.lifecycle import ServiceState

def get_state(request:Request)->ServiceState:
    state=request.app.state.service
    if not state.ready:
        raise HTTPException(status_code=503,detail={'code':'model_unavailable','message':state.load_error or 'model not ready'})
    return state
