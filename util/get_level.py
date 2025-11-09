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
