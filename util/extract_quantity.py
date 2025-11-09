import ifcopenshell.util.element


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
