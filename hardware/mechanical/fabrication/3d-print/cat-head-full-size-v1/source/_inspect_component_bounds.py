import bpy
from collections import defaultdict
from mathutils import Vector


for object_name in ("right_upper_head", "left_upper_head", "right_lower_face", "left_lower_face"):
    obj = bpy.data.objects.get(object_name)
    if obj is None or obj.type != "MESH":
        continue

    neighbors = defaultdict(set)
    for edge in obj.data.edges:
        first, second = edge.vertices
        neighbors[first].add(second)
        neighbors[second].add(first)

    remaining = set(range(len(obj.data.vertices)))
    components = []
    while remaining:
        start = remaining.pop()
        pending = [start]
        component = [start]
        while pending:
            current = pending.pop()
            for neighbor in neighbors[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    pending.append(neighbor)
                    component.append(neighbor)
        components.append(component)

    print(f"COMPONENT_AUDIT {object_name} count={len(components)}")
    for component_number, component in enumerate(
        sorted(components, key=len, reverse=True), start=1
    ):
        points = [obj.matrix_world @ obj.data.vertices[index].co for index in component]
        low = Vector((min(point[axis] for point in points) for axis in range(3)))
        high = Vector((max(point[axis] for point in points) for axis in range(3)))
        center = sum(points, Vector()) / len(points)
        print(
            "COMPONENT "
            f"{component_number} vertices={len(component)} "
            f"center=({center.x:.3f},{center.y:.3f},{center.z:.3f}) "
            f"bounds=({low.x:.3f},{low.y:.3f},{low.z:.3f}).."
            f"({high.x:.3f},{high.y:.3f},{high.z:.3f})"
        )
