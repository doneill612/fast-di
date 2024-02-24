from fastapi import FastAPI
import fastdi

from .router import router

app = FastAPI()
fastdi.init(app)

app.include_router(router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='localhost', port=8000)