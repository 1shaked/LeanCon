from typing import Union
from xml.parsers.expat import model
import ifcopenshell
import ifcopenshell.util.element
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
import tempfile
import ifcopenshell
import shutil
import os
from typing import List, Dict
from fastapi import FastAPI
import io

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






def get_level(element):
    """Return level name from spatial containment"""
    try:
        for rel in element.ContainedInStructure:
            storey = rel.RelatingStructure
            if storey and storey.is_a("IfcBuildingStorey"):
                return storey.Name
    except:
        pass
    return "UNKNOWN"

def extract_quantity(element):
    """Return (quantity_value, unit_string) or (None, None)"""
    qtos = ifcopenshell.util.element.get_psets(element, qtos_only=True)

    # The most common quantity set for structural elements:
    q = qtos.get("Qto_ColumnBaseQuantities", {}) \
        or qtos.get("Qto_BeamBaseQuantities", {}) \
        or qtos.get("Qto_WallBaseQuantities", {}) \
        or qtos.get("Qto_SlabBaseQuantities", {})

    # Priority: Volume → Area → Length
    if "GrossVolume" in q:
        return q["GrossVolume"], "m³"
    if "NetVolume" in q:
        return q["NetVolume"], "m³"
    if "CrossSectionArea" in q:
        return q["CrossSectionArea"], "m²"
    if "OuterSurfaceArea" in q:
        return q["OuterSurfaceArea"], "m²"
    if "Length" in q:
        return q["Length"], "m"
    
    return None, None


def get_model_data_summery(model):
    data = {}

    for element in model.by_type("IfcProduct"):
        quantity, unit = extract_quantity(element)
        if quantity is None:
            continue

        # Determine type name (row identifier)
        element_type = element.ObjectType or element.Name or element.is_a()

        level = get_level(element)

        # Initialize if not exists
        if element_type not in data:
            data[element_type] = {
                "unit": unit,
                "project_total": 0.0,
                "levels": {}
            }

        # Update totals
        data[element_type]["project_total"] += quantity
        data[element_type]["levels"][level] = data[element_type]["levels"].get(level, 0.0) + quantity
    table = []
    for element_type, info in data.items():
        for level, qty in info["levels"].items():
            row = {
                "Element_Type": element_type,
                "Unit": info["unit"],
                "Project_Total": info["project_total"],
                "Level": level,
                'Quantity': qty,
            }
            table.append(row)
    return table

@app.get("/file/{file}")
def read_item(file: str, q: Union[str, None] = None):
    model = ifcopenshell.open(file)
    table = get_model_data_summery(model)

    return {"file": file, "data": table}


@app.get('/object_info/{element_id}/{level}')
def get_object_info(element_id: str, level: str):
    return {"element_id": element_id, "level": level}

# @app.post("/upload_ifc/")
# async def upload_ifc(ifc_file: UploadFile = File(...)) -> Dict:
#     # 2. Save the file temporarily
#     tmp_dir = tempfile.mkdtemp()
#     file_path = os.path.join(tmp_dir, ifc_file.filename)
#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(ifc_file.file, buffer)

#     # 3. Try opening with IfcOpenShell
#     try:
#         model = ifcopenshell.open(file_path)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to open IFC file: {str(e)}")

#     # 4. Extract file schema (header schema line)
#     schema = None
#     try:
#         schema = model.schema()  # returns e.g. "IFC4" or "IFC2X3"
#     except Exception:
#         # fallback: inspect header
#         schema = getattr(model, "schema", None) or "unknown"

#     # 5. Extract all walls (IfcWall) GUIDs
#     walls = model.by_type("IfcWall")
#     wall_guids: List[str] = [w.GlobalId for w in walls if hasattr(w, "GlobalId")]

#     # 6. Clean up temp files
#     try:
#         ifc_file.file.close()
#         os.remove(file_path)
#         os.rmdir(tmp_dir)
#     except Exception:
#         pass

#     # 7. Return results
#     return {
#         "filename": ifc_file.filename,
#         "schema": schema,
#         "wall_count": len(wall_guids),
#         "wall_guids": wall_guids,
#     }

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
        'table': get_model_data_summery(model)
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