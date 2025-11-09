from typing import Union
from xml.parsers.expat import model
import ifcopenshell
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
import tempfile
import shutil
import os
from typing import List, Dict
import io

from util import get_level, get_model_data_summery

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
@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/file/{file}")
def read_item(file: str, q: Union[str, None] = None):
    model = ifcopenshell.open(file)
    table = get_model_data_summery(model)

    return {"file": file, "data": table}


@app.get('/object_info/{element_id}/{level}')
def get_object_info(element_id: str, level: str):
    return {"element_id": element_id, "level": level}

@app.post("/upload_ifc/")
async def upload_ifc(ifc_file: UploadFile = File(...)) -> Dict:
    if not ifc_file.filename.lower().endswith(".ifc"):
        raise HTTPException(status_code=400, detail="Uploaded file must be .ifc")

    tmp_dir = tempfile.mkdtemp()
    file_path = os.path.join(tmp_dir, ifc_file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(ifc_file.file, buffer)

    try:
        model = ifcopenshell.open(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open IFC: {str(e)}")

    # Optionally: delete the temp file if you don’t need it
    try:
        ifc_file.file.close()
        os.remove(file_path)
        os.rmdir(tmp_dir)
    except Exception:
        pass

    return {
        "file": ifc_file.filename,
        'data': get_model_data_summery(model)
    }


@app.post("/get_guids/")
async def get_guids(
    element_type: str = Form(...),
    level_name: str = Form(...),
    ifc_file: UploadFile = File(...)
) -> Dict:

    if not ifc_file.filename.lower().endswith(".ifc"):
        raise HTTPException(status_code=400, detail="Uploaded file must be .ifc")

    tmp_dir = tempfile.mkdtemp()
    file_path = os.path.join(tmp_dir, ifc_file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(ifc_file.file, buffer)

    model = ifcopenshell.open(file_path)

    guids = []

    for el in model.by_type("IfcProduct"):
        if el.ObjectType == element_type or el.Name == element_type:
            lvl = get_level(el)
            if lvl == level_name:
                guids.append(el.GlobalId)

    # cleanup
    ifc_file.file.close()
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return {
        "element_type": element_type,
        "level_name": level_name,
        "guids": guids,
        "count": len(guids)
    }