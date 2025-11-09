from .extract_quantity import extract_quantity
from .get_level import get_level


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
