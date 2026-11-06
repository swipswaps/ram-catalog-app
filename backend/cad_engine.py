import os
import struct

import cadquery as cq

MAX_GLB_BYTES = 25 * 1024 * 1024


def _is_valid_glb(path: str) -> bool:
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < 12:
        return False
    with open(path, "rb") as handle:
        magic, version, length = struct.unpack("<4sII", handle.read(12))
    return magic == b"glTF" and version == 2 and length > 0


def generate_ram_cad_model(module_type: str = "DDR4", ic_count: int = 8) -> str:
    output_dir = "/app/static/cad"
    os.makedirs(output_dir, exist_ok=True)

    pcb_length = 133.35
    pcb_height = 31.25
    pcb_thickness = 1.27

    pcb = (
        cq.Workplane("XY")
        .box(pcb_length, pcb_height, pcb_thickness)
        .edges("|Z")
        .fillet(1.0)
    )

    spacing = pcb_length / (ic_count + 1)
    assembly = cq.Assembly(pcb, name="DIMM_Board")

    for i in range(ic_count):
        x_pos = -pcb_length / 2 + (i + 1) * spacing
        ic_package = (
            cq.Workplane("XY")
            .box(11.0, 9.0, 1.2)
            .translate((x_pos, 2.0, pcb_thickness / 2 + 0.6))
        )
        assembly.add(ic_package, name=f"IC_{i + 1}")

    glb_filename = f"{module_type.lower()}_module.glb"
    glb_path = os.path.join(output_dir, glb_filename)

    assembly.save(glb_path, exportType="GLB", tolerance=0.2, angularTolerance=0.2)

    if not _is_valid_glb(glb_path):
        raise RuntimeError(f"invalid GLB at {glb_path}")
    if os.path.getsize(glb_path) > MAX_GLB_BYTES:
        raise RuntimeError(f"GLB exceeds {MAX_GLB_BYTES} bytes")

    return f"/static/cad/{glb_filename}"
