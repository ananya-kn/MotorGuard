"""Parametric CAD for MotorGuard (CadQuery). Run: python build_cad.py  -> out/*.step and out/*.stl
Dimensions are nominal: MEASURE YOUR MODULES with calipers and edit the numbers at the top."""
import cadquery as cq, os

OUT = os.path.join(os.path.dirname(__file__), "out"); os.makedirs(OUT, exist_ok=True)
# --- sensor mount (Al 6061): base block + 30 mm cantilever arm carrying the MPU6050 (GY-521 is ~21 x 16 mm)
W, T, L = 25.0, 4.0, 30.0
base = cq.Workplane("XY").box(W, 20, 10, centered=(True, False, False)).faces(">Z").workplane().hole(5.2)  # M5 stud
arm = cq.Workplane("XY").box(W, L, T, centered=(True, False, False)).translate((0, 20, 6))
mount = base.union(arm).faces(">Z").workplane(offset=0).pushPoints([(-7.5, 38), (7.5, 38)]).hole(3.2)  # M3 sensor holes
# --- node enclosure: 90 x 60 x 30 inside, 2.5 mm walls, 2 x PG7 cable glands, 4 lid screw posts
iw, il, ih, wall = 90.0, 60.0, 30.0, 2.5
box = cq.Workplane("XY").box(iw + 2 * wall, il + 2 * wall, ih + wall, centered=(True, True, False)).faces(">Z").shell(-wall)
for (x, y) in [(-iw / 2 + 4, -il / 2 + 4), (iw / 2 - 4, -il / 2 + 4), (-iw / 2 + 4, il / 2 - 4), (iw / 2 - 4, il / 2 - 4)]:
    box = box.union(cq.Workplane("XY").workplane(offset=wall).center(x, y).circle(3.5).extrude(ih - 2).faces(">Z").workplane().hole(2.6, 12))
box = box.faces("<X").workplane().pushPoints([(-10, 12), (10, 12)]).hole(12.6)  # PG7 glands
lid = cq.Workplane("XY").box(iw + 2 * wall, il + 2 * wall, 2.5, centered=(True, True, False))
lid = lid.faces(">Z").workplane().pushPoints([(-iw / 2 + 4, -il / 2 + 4), (iw / 2 - 4, -il / 2 + 4), (-iw / 2 + 4, il / 2 - 4), (iw / 2 - 4, il / 2 - 4)]).hole(3.4)
# --- test-rig base plate 220 x 120 x 8 with motor slots and corner holes
rig = cq.Workplane("XY").box(220, 120, 8).faces(">Z").workplane().pushPoints([(-100, -50), (100, -50), (-100, 50), (100, 50)]).hole(5.5)
rig = rig.faces(">Z").workplane().center(-20, 0).slot2D(60, 5.5, 90).cutThruAll().faces(">Z").workplane().center(20, 0).slot2D(60, 5.5, 90).cutThruAll()
# --- fault-injection disc: 60 mm, 6 mm bore, ring of M3 holes at r = 22 mm (add a nut/bolt as the offset mass), 1 set-screw
disc = cq.Workplane("XY").circle(30).extrude(8).faces(">Z").workplane().hole(6.0)
disc = disc.faces(">Z").workplane().polarArray(22, 0, 360, 12).hole(3.2)
disc = disc.cut(cq.Workplane("XZ").center(0, 4).circle(1.4).extrude(-30))  # radial M3 set screw hole
parts = dict(sensor_mount=mount, node_enclosure=box, node_lid=lid, rig_base=rig, fault_disc=disc)
for n, p in parts.items():
    cq.exporters.export(p, os.path.join(OUT, n + ".step")); cq.exporters.export(p, os.path.join(OUT, n + ".stl"))
    bb = p.val().BoundingBox(); print(f"{n}: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, volume {p.val().Volume()/1000:.1f} cm3")
