from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.ifc_router import router as ifc_router

app = FastAPI()
origins = [
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ifc_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}
