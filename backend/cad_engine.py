import os, struct, cadquery as cq
MAX_GLB_BYTES = 25 * 1024 * 1024
def generate_ram_cad_model(module_type="DDR4", ic_count=8, form_factor="DIMM") -> str:
    os.makedirs("/app/static/cad", exist_ok=True)
    dims = (67.6, 30.0, 1.0, 4.0, 16.0, (8.0, 8.0, 1.0), 0.0) if form_factor == "SODIMM" else (133.35, 31.25, 1.57, 5.0, 40.0, (11.0, 9.0, 1.2), 2.0)
    L, H, T, G, N, IC, Y = dims
    pcb = cq.Workplane("XY").box(L, H, T).edges("|Z").fillet(0.5)
    notch = cq.Workplane("XY").box(2.0, 3.0, T*4).translate((-N, -H/2 + 1.5, 0))
    pcb = pcb.cut(notch)
    gold = cq.Workplane("XY").box(L, G, T+0.02).translate((0, -H/2 + G/2, 0)).cut(notch)
    assy = cq.Assembly(pcb, name="PCB", color=cq.Color(0.05, 0.35, 0.15))
    assy.add(gold, name="Gold", color=cq.Color(0.85, 0.65, 0.13))
    sp = L / (ic_count + 1)
    for r, z in enumerate((-1, 1)):
        for i in range(ic_count):
            assy.add(cq.Workplane("XY").box(*IC).translate((-L/2 + (i+1)*sp, Y, z*(T/2+IC[2]/2))), name=f"IC_{r}_{i}", color=cq.Color(0.02, 0.02, 0.02))
    path = f"/app/static/cad/{form_factor.lower()}_{module_type.lower()}.glb"
    assy.save(path, exportType="GLB", tolerance=0.2, angularTolerance=0.2)
    return f"/static/cad/{form_factor.lower()}_{module_type.lower()}.glb"
