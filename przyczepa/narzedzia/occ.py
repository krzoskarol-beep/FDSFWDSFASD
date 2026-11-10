"""Cienkie opakowanie na OpenCascade (pakiet cadquery-ocp) używane przez skrypty v6."""
import numpy as np
from OCP.STEPControl import STEPControl_Reader
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE, TopAbs_REVERSED
from OCP.TopoDS import TopoDS
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse, BRepAlgoAPI_Common
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeRevol, BRepPrimAPI_MakeCylinder
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.gp import gp_Trsf, gp_Vec, gp_Pnt, gp_Ax1, gp_Ax2, gp_Dir
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopLoc import TopLoc_Location
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorType
from OCP.TDataStd import TDataStd_Name
from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB


def read_solids(path):
    r = STEPControl_Reader()
    r.ReadFile(path)
    r.TransferRoots()
    ex = TopExp_Explorer(r.OneShape(), TopAbs_SOLID)
    out = []
    while ex.More():
        out.append(TopoDS.Solid(ex.Current()))
        ex.Next()
    return out


def bbox(s):
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(s, b, False, False)
    p0, p1 = b.CornerMin(), b.CornerMax()
    return np.array([p0.X(), p0.Y(), p0.Z(), p1.X(), p1.Y(), p1.Z()])


def volume(s):
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(s, g)
    c = g.CentreOfMass()
    return g.Mass(), np.array([c.X(), c.Y(), c.Z()])


def translate(s, dx=0, dy=0, dz=0):
    t = gp_Trsf()
    t.SetTranslation(gp_Vec(dx, dy, dz))
    return BRepBuilderAPI_Transform(s, t, True).Shape()


def rotate_z(s, cx, cy, deg):
    t = gp_Trsf()
    t.SetRotation(gp_Ax1(gp_Pnt(cx, cy, 0), gp_Dir(0, 0, 1)), np.radians(deg))
    return BRepBuilderAPI_Transform(s, t, True).Shape()


def revolve_z(s, cx, cy, deg):
    return BRepPrimAPI_MakeRevol(s, gp_Ax1(gp_Pnt(cx, cy, 0), gp_Dir(0, 0, 1)), np.radians(deg)).Shape()


def box(x0, y0, z0, x1, y1, z1):
    return BRepPrimAPI_MakeBox(gp_Pnt(x0, y0, z0), gp_Pnt(x1, y1, z1)).Shape()


def tube_z(cx, cy, z0, z1, ro, ri):
    o = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(cx, cy, z0), gp_Dir(0, 0, 1)), ro, z1 - z0).Shape()
    i = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(cx, cy, z0 - 1), gp_Dir(0, 0, 1)), ri, z1 - z0 + 2).Shape()
    return cut(o, i)


def _clean(s):
    u = ShapeUpgrade_UnifySameDomain(s, True, True, True)
    u.Build()
    return u.Shape()


def cut(a, b):
    return _clean(BRepAlgoAPI_Cut(a, b).Shape())


def fuse(a, b):
    return _clean(BRepAlgoAPI_Fuse(a, b).Shape())


def common_volume(a, b):
    return volume(BRepAlgoAPI_Common(a, b).Shape())[0]


def distance(a, b):
    return BRepExtrema_DistShapeShape(a, b).Value()


def tessellate(s, lin=0.25, ang=0.35):
    """Zwraca (V[n,3] w mm, F[m,3]) z triangulacji B-rep."""
    BRepMesh_IncrementalMesh(s, lin, False, ang, True)
    V, F, off = [], [], 0
    ex = TopExp_Explorer(s, TopAbs_FACE)
    while ex.More():
        f = TopoDS.Face(ex.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(f, loc)
        if tri is not None:
            tr = loc.Transformation()
            pts = []
            for i in range(1, tri.NbNodes() + 1):
                p = tri.Node(i).Transformed(tr)
                pts.append((p.X(), p.Y(), p.Z()))
            rev = f.Orientation() == TopAbs_REVERSED
            for i in range(1, tri.NbTriangles() + 1):
                a, b, c = tri.Triangle(i).Get()
                F.append((a - 1 + off, c - 1 + off, b - 1 + off) if rev else (a - 1 + off, b - 1 + off, c - 1 + off))
            V.extend(pts)
            off += len(pts)
        ex.Next()
    return np.array(V, float), np.array(F, int)


def write_step_named(parts, path, schema_note="przyczepa_v6"):
    """parts: lista (nazwa, solid, (r,g,b)). Zapis STEP AP214 z nazwami i kolorami części."""
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    asm = st.NewShape()
    TDataStd_Name.Set_s(asm, TCollection_ExtendedString(schema_note))
    for name, solid, rgb in parts:
        lab = st.AddShape(solid, False)
        TDataStd_Name.Set_s(lab, TCollection_ExtendedString(name))
        ct.SetColor(lab, Quantity_Color(*rgb, Quantity_TOC_RGB), XCAFDoc_ColorType.XCAFDoc_ColorSurf)
        comp = st.AddComponent(asm, lab, TopLoc_Location())
        TDataStd_Name.Set_s(comp, TCollection_ExtendedString(name))
    st.UpdateAssemblies()
    w = STEPCAFControl_Writer()
    w.SetNameMode(True)
    w.SetColorMode(True)
    w.Transfer(doc, STEPControl_AsIs)
    return int(w.Write(path))


def read_named(path):
    """Części z pliku STEP v6 + nazwy (kolejność komponentów = kolejność PRODUCT).
    Część może być bryłą albo zbiorem brył (np. szczebel podzielony na 3 odcinki)."""
    import re
    from OCP.TopoDS import TopoDS_Iterator
    r = STEPControl_Reader()
    r.ReadFile(path)
    r.TransferRoots()
    root = r.OneShape()
    it = TopoDS_Iterator(root)
    parts = []
    while it.More():
        parts.append(it.Value())
        it.Next()
    if len(parts) == 1:           # jeden poziom zagnieżdżenia (złożenie w złożeniu)
        it = TopoDS_Iterator(parts[0])
        parts = []
        while it.More():
            parts.append(it.Value())
            it.Next()
    txt = open(path, encoding='latin-1').read()
    names = re.findall(r"PRODUCT\('([^']*)'", txt)
    names = [n.encode('latin-1').decode('utf-8', 'replace') for n in names[1:]]
    assert len(names) == len(parts), (len(names), len(parts))
    return dict(zip(names, parts))
