import os
import struct

import cadquery as cq

MAX_GLB_BYTES = 25 * 1024 * 1024

# JEDEC DDR4 UDIMM nominal dimensions.
# Source: Wikipedia DDR4 (133.35 x 31.25 mm), Molex 787261048 (1.57 mm PCB, 288 pins).
DIMM_LENGTH = 133.35
DIMM_HEIGHT = 31.25
PCB_THICKNESS = 1.57
GOLD_FINGER_DEPTH = 5.0
NOTCH_OFFSET = 40.0     # approximate; real DDR4 key position varies by spec
NOTCH_WIDTH = 2.0
NOTCH_HEIGHT = 1.5
IC_COUNT = 8
IC_BODY = (11.0, 9.0, 1.2)
IC_Y_OFFSET = 2.0       # same on both ranks; distance from board centre along Y


def _is_valid_glb(path: str) -> bool:
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < 12:
        return False
    with open(path, "rb") as handle:
        magic, version, length = struct.unpack("<4sII", handle.read(12))
    return magic == b"glTF" and version == 2 and length > 0


def generate_ram_cad_model(module_type: str = "DDR4", ic_count: int = IC_COUNT) -> str:
    output_dir = "/app/static/cad"
    os.makedirs(output_dir, exist_ok=True)

    # 1. PCB base
    pcb = (
        cq.Workplane("XY")
        .box(DIMM_LENGTH, DIMM_HEIGHT, PCB_THICKNESS)
        .edges("|Z")
        .fillet(0.5)
    )

    # 2. Notch cutter: rectangular slot, penetrates the -Y edge by ~2.25 mm,
    #    extrudes through the full thickness (and beyond, to cut the gold strip).
    notch_cutter = (
        cq.Workplane("XY")
        .box(NOTCH_WIDTH, NOTCH_HEIGHT * 2, PCB_THICKNESS * 4)
        .translate((-NOTCH_OFFSET, -DIMM_HEIGHT / 2 + NOTCH_HEIGHT / 2, 0))
    )

    # 3. Cut the notch from the PCB.
    pcb = pcb.cut(notch_cutter)

    # 4. Gold-finger strip: wraps the -Y edge, sits 0.01 mm proud on each face
    #    (avoids z-fighting); notch cut from it as well.
    gold_finger = (
        cq.Workplane("XY")
        .box(DIMM_LENGTH, GOLD_FINGER_DEPTH, PCB_THICKNESS + 0.02)
        .translate((0, -DIMM_HEIGHT / 2 + GOLD_FINGER_DEPTH / 2, 0))
    )
    gold_finger = gold_finger.cut(notch_cutter)

    assembly = cq.Assembly(pcb, name="DIMM_PCB", color=cq.Color(0.05, 0.35, 0.15))
    assembly.add(gold_finger, name="Gold_Fingers", color=cq.Color(0.85, 0.65, 0.13))

    # 5. Two ranks of IC packages: same Y offset, opposite Z sides of the PCB.
    spacing = DIMM_LENGTH / (ic_count + 1)
    for rank, z_sign in enumerate((-1, 1)):
        for i in range(ic_count):
            x_pos = -DIMM_LENGTH / 2 + (i + 1) * spacing
            z_pos = z_sign * (PCB_THICKNESS / 2 + IC_BODY[2] / 2)
            ic = (
                cq.Workplane("XY")
                .box(IC_BODY[0], IC_BODY[1], IC_BODY[2])
                .translate((x_pos, IC_Y_OFFSET, z_pos))
            )
            assembly.add(ic, name=f"IC_{rank}_{i + 1}", color=cq.Color(0.02, 0.02, 0.02))

    glb_filename = f"{module_type.lower()}_module.glb"
    glb_path = os.path.join(output_dir, glb_filename)

    assembly.save(
        glb_path,
        exportType="GLB",
        tolerance=0.2,
        angularTolerance=0.2,
    )

    if not _is_valid_glb(glb_path):
        raise RuntimeError(f"invalid GLB at {glb_path}")
    if os.path.getsize(glb_path) > MAX_GLB_BYTES:
        raise RuntimeError(f"GLB exceeds {MAX_GLB_BYTES} bytes")

    return f"/static/cad/{glb_filename}"
