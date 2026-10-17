from contextlib import asynccontextmanager
from fastapi import FastAPI,Request,WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from soorin_stt.api import health,metrics,transcription,websocket
from soorin_stt.core.config import Settings,get_settings
from soorin_stt.core.lifecycle import ServiceState
from soorin_stt.core.logging import setup_logging
from soorin_stt.core.exceptions import STTError
from soorin_stt.api.errors import handle_stt_error

def create_app(settings: Settings|None=None) -> FastAPI:
    settings=settings or get_settings()
    setup_logging(settings.log_level)
    @asynccontextmanager
    async def lifespan(app:FastAPI):
        await app.state.service.start()
        yield
        await app.state.service.stop()
    app=FastAPI(title='Soorin Persian STT',version='0.1.0',lifespan=lifespan,
                description='Local, offline-first, pluggable speech-to-text API')
    app.state.service=ServiceState(settings)
    app.add_middleware(CORSMiddleware,allow_origins=settings.allowed_origins,
                       allow_methods=['GET','POST'],allow_headers=['Content-Type','X-API-Key'])
    app.add_exception_handler(STTError,handle_stt_error)
    @app.middleware('http')
    async def key_guard(req:Request,call_next):
        public={'/health/live','/health/ready','/version'}
        if settings.app_api_key and req.url.path not in public and req.headers.get('x-api-key')!=settings.app_api_key:
            return JSONResponse({'error':{'code':'unauthorized','message':'Missing/invalid X-API-Key'}},status_code=401)
        return await call_next(req)
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(transcription.router)
    app.include_router(websocket.router)
    return app

app=create_app()

def serve():
    import uvicorn
    settings=get_settings()
    uvicorn.run('soorin_stt.main:app',host=settings.app_host,port=settings.app_port,workers=1)
