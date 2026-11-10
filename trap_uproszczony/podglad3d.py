# -*- coding: utf-8 -*-
"""
Podgląd 3D trapu V2.
  python3 podglad3d.py  ->  podglad_3d.html (otwórz w przeglądarce, działa offline),
                            trap_v2_rozlozony.glb, trap_v2_do_jazdy.glb
Wymaga: pip install trimesh   (three.js jest wklejony do HTML z pliku three.min.js obok, albo pobierany z CDN)
Geometria bierze wymiary z generuj.py.
"""
import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generuj as g

OUT = os.path.dirname(os.path.abspath(__file__))

C_LANE, C_WALK, C_CROSS = "#8fa9c9", "#c9cfd6", "#d8b98a"
C_MESH, C_GUIDE, C_STEEL, C_TRAILER = "#5f6b78", "#3f6fb0", "#3a3a3a", "#b04a3a"


def rect(s0, s1, z0, z1):
    return [(s0, z0), (s1, z0), (s1, z1), (s0, z1)]


def parts():
    """lista brył: grupa (A/B/T), wielokąt (s,z) lub (y,z) dla T, zakres x, kolor"""
    P = []

    def add(grp, poly, x0, x1, col, name, mirror=True, op=1.0):
        P.append(dict(g=grp, p=poly, x0=x0, x1=x1, c=col, n=name, o=op))
        if mirror and not (x0 <= 0 <= x1):
            P.append(dict(g=grp, p=poly, x0=-x1, x1=-x0, c=col, n=name, o=op))

    L, SK = g.L_SEC, g.SKOS
    for x in (g.X_LANE_IN, g.X_LANE_OUT, g.X_WALK, g.X_EDGE):
        col = C_LANE if x < 200 else C_WALK
        nm = "rura jezdna 100×40×3 (6082)" if x < 200 else "podłużnica 100×40×2"
        add("A", rect(0, L, 0, 100), x - 20, x + 20, col, nm)
        add("B", [(0, 0), (L - SK, 0), (L, 100), (0, 100)], x - 20, x + 20, col, nm)
    for s in g.CROSS_A:
        add("A", rect(s - 20, s + 20, -60, 0), -g.WIDTH / 2, g.WIDTH / 2, C_CROSS, "poprzeczka 60×40×3", False)
    for s in g.CROSS_B:
        add("B", rect(s - 20, s + 20, -60, 0), -g.WIDTH / 2, g.WIDTH / 2, C_CROSS, "poprzeczka 60×40×3", False)
    add("B", rect(g.TIE_B - 20, g.TIE_B + 20, -5, 0), -g.WIDTH / 2, g.WIDTH / 2, C_WALK, "listwa T 40×5", False)
    for grp in "AB":
        add(grp, rect(0, L, 100, 103), -g.WIDTH / 2, g.WIDTH / 2, C_MESH, "siatka Al", False, 0.45)
    xo = g.X_LANE_OUT + 20
    for grp, (a, b) in (("A", g.GUIDE_A), ("B", g.GUIDE_B)):
        add(grp, rect(a, b, 103, 107), xo - 40, xo, C_GUIDE, "prowadnica 40×40×4")
        add(grp, rect(a, b, 107, 143), xo - 4, xo, C_GUIDE, "prowadnica 40×40×4")
    # plyty H (obie strony rury L1)
    hp = rect(g.H_PL["s0"], g.H_PL["s0"] + g.H_PL["w"], g.H_PL["z0"], g.H_PL["z0"] + g.H_PL["h"])
    add("A", hp, xo, xo + 6, C_STEEL, "płyta H")
    add("A", hp, xo - 46, xo - 40, C_STEEL, "płyta H")
    # plyty Z: A na rurze, B na zewnatrz (podkladka 6)
    zA = rect(L - 140, L + 30, -60, 40)
    add("A", zA, xo, xo + 6, C_STEEL, "płyta Z (A)")
    add("A", zA, xo - 46, xo - 40, C_STEEL, "płyta Z (A)")
    zB = rect(-30, 140, -60, 40)
    add("B", zB, xo + 6, xo + 12, C_STEEL, "płyta Z (B)")
    add("B", zB, xo - 52, xo - 46, C_STEEL, "płyta Z (B)")
    # plyta S na podluznicy chodnika
    add("A", rect(g.S_PL["s0"], g.S_PL["s0"] + 80, -50, 100), g.X_WALK + 20, g.X_WALK + 28, C_STEEL, "płyta S (sprężyna)")
    # przyczepa (y od tylnej sciany belki do tylu, z od podlogi)
    add("T", rect(-1400, 0, -18, 0), -650, 650, "#9a8f80", "podłoga przyczepy", False)
    add("T", rect(-50, 0, -75, -18), -700, 700, "#7d7d7d", "tylna belka (przykład 50×75)", False)
    add("T", rect(-1400, -40, 0, 350), 650, 670, "#9a8f80", "burta", True, 0.35)
    add("T", rect(-1100, -700, -480, -150), 700, 880, "#222222", "koło przyczepy", True, 0.9)
    for xa in (152.0, 369.0):        # wsporniki K: ramie odstajace + ramie na belce
        add("T", rect(0, 100, -130, 0), xa, xa + 10, C_TRAILER, "wspornik K 100×100×10")
        add("T", rect(0, 10, -130, 0), xa, xa + 100, C_TRAILER, "wspornik K 100×100×10")
    return P


def prism(poly, x0, x1, tf):
    """wierzcholki i trojkaty graniastoslupa (wielokat wypukly) po transformacji tf(x,a,b)->(X,Y,Z)"""
    n = len(poly)
    V = [tf(x0, a, b) for (a, b) in poly] + [tf(x1, a, b) for (a, b) in poly]
    F = []
    for i in range(1, n - 1):
        F.append((0, i + 1, i))
        F.append((n, n + i, n + i + 1))
    for i in range(n):
        j = (i + 1) % n
        F.append((i, j, n + j))
        F.append((i, n + j, n + i))
    return V, F


def pose(t):
    """t: 0 = rozlozony, 1 = do jazdy  ->  (theta, phi_rel)"""
    (mA, cAs, cAz), (mB, cBs, cBz) = g.masses()
    zg = -(g.H_FLOOR + g.PIN_Z)
    uM, vM = g.L_SEC + 25.0, -110.0
    cBu, cBv = cBs, cBz + 35.0
    tipu, tipv = g.L_SEC, 135.0
    lift = g.lift_table(mA, cAs, cAz, mB, cBs, cBz, False)
    th0 = math.radians(lift[0]["deg"])
    th = th0 + (math.radians(90) - th0) * t
    pm = g.rot(th, uM, vM)
    ph = math.atan2(cBu, cBv)
    if g.rot(ph, cBu, cBv)[1] > 0:
        ph += math.pi
    ph = math.atan2(math.sin(ph), math.cos(ph))
    if pm[1] + g.rot(ph, tipu, tipv)[1] <= zg:
        a, b = 1e-5, abs(ph)
        for _ in range(80):
            m = (a + b) / 2
            if pm[1] + g.rot(-m, tipu, tipv)[1] - zg > 0:
                a = m
            else:
                b = m
        ph = -(a + b) / 2
    rel = ph - th
    while rel > 0:
        rel -= 2 * math.pi
    rel = max(rel, -math.pi)
    return th, rel, th0, dict(uM=uM, vM=vM, cBu=cBu, cBv=cBv, tipu=tipu, tipv=tipv, zg=zg)


def to_world(grp, th, rel):
    """funkcja (x, a, b) -> (X, Y, Z) w ukladzie Y do gory (X = x, Y = z, Z = -y)"""
    uM, vM = g.L_SEC + 25.0, -110.0

    def T(x, a, b):
        return (x, b, -a)

    def A(x, s, z):
        y, zz = g.rot(th, s + 25.0, z - 75.0)
        return (x, g.PIN_Z + zz, -(g.PIN_Y + y))

    def B(x, s, z):
        du, dv = g.rot(rel, s, z + 35.0)
        y, zz = g.rot(th, uM + du, vM + dv)
        return (x, g.PIN_Z + zz, -(g.PIN_Y + y))
    return {"T": T, "A": A, "B": B}[grp]


def write_glb(t, fname):
    import numpy as np
    import trimesh
    th, rel, _, _ = pose(t)
    scene = trimesh.Scene()
    for i, p in enumerate(parts()):
        V, F = prism(p["p"], p["x0"], p["x1"], to_world(p["g"], th, rel))
        Va = np.array(V) / 1000.0
        Fa = np.array(F)
        c = Va.mean(axis=0)
        tri = Va[Fa]
        nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        if np.sum(np.einsum("ij,ij->i", nrm, tri.mean(axis=1) - c)) < 0:
            Fa = Fa[:, ::-1]
        m = trimesh.Trimesh(vertices=Va, faces=Fa, process=False)
        rgb = [int(p["c"][k:k + 2], 16) for k in (1, 3, 5)]
        mat = trimesh.visual.material.PBRMaterial(baseColorFactor=rgb + [int(255 * p["o"])], metallicFactor=0.3,
                                                  roughnessFactor=0.6, doubleSided=True,
                                                  alphaMode="BLEND" if p["o"] < 1 else "OPAQUE")
        m.visual = trimesh.visual.TextureVisuals(material=mat)
        scene.add_geometry(m, node_name=f"{i:03d}_{p['n']}")
    scene.export(os.path.join(OUT, fname))


def write_html():
    th0 = pose(0)[2]
    _, _, _, geo = pose(0)
    data = dict(parts=parts(), th0=th0, pin=[g.PIN_Y, g.PIN_Z], L=g.L_SEC, geo=geo,
                spring=dict(low=list(g.SPRING["eye_low"]), up=[g.SPRING["eye_up_sz"][0] + 25.0, g.SPRING["eye_up_sz"][1] - 75.0],
                            x=396.0),
                info=dict(alpha=round(g.ALPHA, 1)))
    three = os.path.join(OUT, "three.min.js")
    if os.path.exists(three):
        lib = "<script>" + open(three, encoding="utf-8").read() + "</script>"
    else:
        lib = '<script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>'
    html = HTML.replace("/*DATA*/", json.dumps(data, ensure_ascii=False)).replace("<!--THREE-->", lib)
    with open(os.path.join(OUT, "podglad_3d.html"), "w", encoding="utf-8") as f:
        f.write(html)


HTML = r"""<!DOCTYPE html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trap V2 – podgląd 3D</title>
<style>
 html,body{margin:0;height:100%;overflow:hidden;font-family:system-ui,sans-serif;background:#eef1f5}
 #ui{position:absolute;left:10px;top:10px;background:rgba(255,255,255,.92);padding:10px 12px;border-radius:8px;
     box-shadow:0 1px 4px rgba(0,0,0,.2);font-size:13px;max-width:330px}
 #ui h1{font-size:15px;margin:0 0 6px}
 #ui button{margin:2px 4px 2px 0;padding:5px 9px;border:1px solid #889;border-radius:5px;background:#fff;cursor:pointer}
 #ui input[type=range]{width:100%}
 .lg{display:inline-block;width:11px;height:11px;margin-right:5px;vertical-align:-1px;border:1px solid #555}
 #tip{position:absolute;pointer-events:none;background:#222;color:#fff;font-size:12px;padding:3px 6px;border-radius:4px;display:none}
 small{color:#555}
</style></head><body>
<div id="ui">
 <h1>Trap aluminiowy V2 – bez spawania</h1>
 <div><button id="b0">Rozłożony</button><button id="b1">Do jazdy</button><button id="ba">▶ Składanie</button></div>
 <div>Pozycja: <input id="sl" type="range" min="0" max="1" step="0.005" value="0"></div>
 <div><label><input id="cm" type="checkbox" checked> siatka</label>
      <label><input id="ct" type="checkbox" checked> przyczepa</label>
      <button id="bv">widok z boku</button><button id="bt">z góry</button></div>
 <div style="margin-top:6px;line-height:1.6">
  <span class="lg" style="background:#8fa9c9"></span>rury jezdne 100×40×3 6082-T6<br>
  <span class="lg" style="background:#c9cfd6"></span>podłużnice 100×40×2<br>
  <span class="lg" style="background:#d8b98a"></span>poprzeczki 60×40×3<br>
  <span class="lg" style="background:#3f6fb0"></span>prowadnice koła 40×40×4<br>
  <span class="lg" style="background:#3a3a3a"></span>płyty stalowe H / Z / S<br>
  <span class="lg" style="background:#b04a3a"></span>wsporniki K na belce<br>
  <span class="lg" style="background:#111"></span>sprężyny gazowe
 </div>
 <small>Obracaj: przeciągnij · przybliżaj: kółko / 2 palce · przesuwaj: prawy przycisk / Shift.<br>
 Najedź na element, by zobaczyć nazwę.</small>
</div>
<div id="tip"></div>
<!--THREE-->
<script>
const D = /*DATA*/;
const W = innerWidth, H = innerHeight;
const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.setSize(W,H);
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0xeef1f5);
const camera = new THREE.PerspectiveCamera(40, W/H, 10, 50000);
scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8a7a, 1.1));
const sun = new THREE.DirectionalLight(0xffffff, 1.4); sun.position.set(1500,3000,-2000); scene.add(sun);
const sun2 = new THREE.DirectionalLight(0xffffff, 0.5); sun2.position.set(-2000,1000,2000); scene.add(sun2);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(9000,9000), new THREE.MeshLambertMaterial({color:0xcfd8c3}));
ground.rotation.x = -Math.PI/2; ground.position.y = D.pin[1] + D.geo.zg - 1; scene.add(ground);
const grid = new THREE.GridHelper(9000, 90, 0xa0ab98, 0xb8c2b0); grid.position.y = ground.position.y + 1; scene.add(grid);

function prism(poly, x0, x1, tf){
  const n = poly.length, V = [], I = [];
  for (const x of [x0,x1]) for (const [a,b] of poly) V.push(...tf(x,a,b));
  for (let i=1;i<n-1;i++){ I.push(0,i+1,i, n,n+i,n+i+1); }
  for (let i=0;i<n;i++){ const j=(i+1)%n; I.push(i,j,n+j, i,n+j,n+i); }
  const gm = new THREE.BufferGeometry();
  gm.setAttribute('position', new THREE.Float32BufferAttribute(V,3)); gm.setIndex(I);
  return gm.toNonIndexed();
}
const local = (x,a,b)=>[x, b, -a];
const T = new THREE.Group(), A = new THREE.Group(), B = new THREE.Group();
scene.add(T); scene.add(A);
A.position.set(0, D.pin[1], -D.pin[0]);
B.position.set(0, D.geo.vM, -D.geo.uM); A.add(B);
const meshParts = [], pickables = [];
for (const p of D.parts){
  const tf = p.g==='T' ? local : (p.g==='A' ? (x,s,z)=>[x, z-75, -(s+25)] : (x,s,z)=>[x, z+35, -s]);
  const gm = prism(p.p, p.x0, p.x1, tf); gm.computeVertexNormals();
  const mat = new THREE.MeshStandardMaterial({color:p.c, metalness:0.25, roughness:0.6, side:THREE.DoubleSide,
      transparent:p.o<1, opacity:p.o, depthWrite:p.o>=0.5});
  const m = new THREE.Mesh(gm, mat); m.userData.name = p.n;
  if (p.o >= 0.5){ const e = new THREE.LineSegments(new THREE.EdgesGeometry(gm, 30), new THREE.LineBasicMaterial({color:0x333333, transparent:true, opacity:0.35})); m.add(e); }
  ({T,A,B})[p.g].add(m); meshParts.push({m,p}); pickables.push(m);
}
// sworznie
function pin(group, y, z, x0, x1, r){
  const c = new THREE.Mesh(new THREE.CylinderGeometry(r,r,x1-x0,16), new THREE.MeshStandardMaterial({color:0xd0d0d0, metalness:0.8, roughness:0.3}));
  c.rotation.z = Math.PI/2; c.position.set((x0+x1)/2, y, z); c.userData.name = 'sworzeń M20 (śruba 8.8)'; group.add(c); pickables.push(c);
  const c2 = c.clone(); c2.position.x = -c.position.x; group.add(c2); pickables.push(c2);
}
pin(A, 0, 0, 99, 162, 10);
pin(A, D.geo.vM, -D.geo.uM, 93, 157, 10);
// sprezyny
const springs = [-1,1].map(sg=>{
  const body = new THREE.Mesh(new THREE.CylinderGeometry(14,14,1,16), new THREE.MeshStandardMaterial({color:0x151515, metalness:0.5, roughness:0.4}));
  const rod = new THREE.Mesh(new THREE.CylinderGeometry(7,7,1,12), new THREE.MeshStandardMaterial({color:0xe0e0e0, metalness:0.9, roughness:0.2}));
  body.userData.name = rod.userData.name = 'sprężyna gazowa 460/200 mm, 1600 N';
  scene.add(body); scene.add(rod); pickables.push(body, rod); return {sg, body, rod};
});
const rot = (th,u,v)=>[u*Math.cos(th)-v*Math.sin(th), u*Math.sin(th)+v*Math.cos(th)];
function placeCyl(c, p0, p1){
  const d = new THREE.Vector3().subVectors(p1,p0); const L = d.length();
  c.scale.set(1, L, 1); c.position.copy(p0).addScaledVector(d, 0.5);
  c.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), d.normalize());
}
function poseB(th){
  const G = D.geo, pm = rot(th, G.uM, G.vM);
  let ph = Math.atan2(G.cBu, G.cBv);
  if (rot(ph, G.cBu, G.cBv)[1] > 0) ph += Math.PI;
  ph = Math.atan2(Math.sin(ph), Math.cos(ph));
  if (pm[1] + rot(ph, G.tipu, G.tipv)[1] <= G.zg){
    let a=1e-5, b=Math.abs(ph);
    for (let k=0;k<70;k++){ const m=(a+b)/2; if (pm[1] + rot(-m, G.tipu, G.tipv)[1] - G.zg > 0) a=m; else b=m; }
    ph = -(a+b)/2;
  }
  let rel = ph - th; while (rel > 0) rel -= 2*Math.PI; return Math.max(rel, -Math.PI);
}
function setPose(t){
  const th = D.th0 + (Math.PI/2 - D.th0)*t;
  A.rotation.x = th; B.rotation.x = poseB(th);
  for (const s of springs){
    const lo = new THREE.Vector3(s.sg*D.spring.x, D.pin[1]+D.spring.low[1], -(D.pin[0]+D.spring.low[0]));
    const up = rot(th, D.spring.up[0], D.spring.up[1]);
    const hi = new THREE.Vector3(s.sg*D.spring.x, D.pin[1]+up[1], -(D.pin[0]+up[0]));
    const mid = new THREE.Vector3().lerpVectors(lo, hi, 0.55);
    placeCyl(s.body, lo, mid); placeCyl(s.rod, mid, hi);
  }
}
// kamera / sterowanie
let tgt = new THREE.Vector3(0, -150, -1100), rad = 5200, az = -2.35, el = 0.42;
function cam(){ camera.position.set(tgt.x + rad*Math.cos(el)*Math.sin(az), tgt.y + rad*Math.sin(el), tgt.z + rad*Math.cos(el)*Math.cos(az)); camera.lookAt(tgt); }
let drag=null, pts=new Map();
const el_ = renderer.domElement;
el_.addEventListener('contextmenu', e=>e.preventDefault());
el_.addEventListener('pointerdown', e=>{ el_.setPointerCapture(e.pointerId); pts.set(e.pointerId,[e.clientX,e.clientY]);
  drag={x:e.clientX,y:e.clientY,pan:e.button===2||e.shiftKey, d:null}; });
el_.addEventListener('pointerup', e=>{ pts.delete(e.pointerId); if(!pts.size) drag=null; });
el_.addEventListener('pointermove', e=>{
  if (pts.has(e.pointerId)) pts.set(e.pointerId,[e.clientX,e.clientY]);
  if (pts.size===2){ const [a,b]=[...pts.values()]; const d=Math.hypot(a[0]-b[0],a[1]-b[1]);
    if (drag && drag.d) rad = Math.min(20000, Math.max(800, rad*drag.d/d)); if (drag) drag.d=d; cam(); return; }
  if (drag){ const dx=e.clientX-drag.x, dy=e.clientY-drag.y; drag.x=e.clientX; drag.y=e.clientY;
    if (drag.pan){ const r = new THREE.Vector3().setFromMatrixColumn(camera.matrix,0), u = new THREE.Vector3().setFromMatrixColumn(camera.matrix,1);
      tgt.addScaledVector(r, -dx*rad/1000).addScaledVector(u, dy*rad/1000); }
    else { az -= dx*0.006; el = Math.min(1.5, Math.max(-0.2, el + dy*0.006)); }
    cam(); return; }
  hover(e);
});
el_.addEventListener('wheel', e=>{ e.preventDefault(); rad = Math.min(20000, Math.max(800, rad*Math.exp(e.deltaY*0.001))); cam(); }, {passive:false});
const ray = new THREE.Raycaster(), tip = document.getElementById('tip');
function hover(e){
  ray.setFromCamera({x:e.clientX/innerWidth*2-1, y:-e.clientY/innerHeight*2+1}, camera);
  const hit = ray.intersectObjects(pickables.filter(o=>o.visible && (!o.parent || o.parent.visible)), false)[0];
  if (hit){ tip.style.display='block'; tip.textContent = hit.object.userData.name; tip.style.left=(e.clientX+12)+'px'; tip.style.top=(e.clientY+12)+'px'; }
  else tip.style.display='none';
}
addEventListener('resize', ()=>{ camera.aspect=innerWidth/innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth,innerHeight); });
const sl = document.getElementById('sl'); let anim = null, tcur = 0;
function go(t){ tcur=t; sl.value=t; setPose(t); }
sl.oninput = ()=>{ anim=null; go(+sl.value); };
document.getElementById('b0').onclick = ()=>{ anim=null; go(0); };
document.getElementById('b1').onclick = ()=>{ anim=null; go(1); };
document.getElementById('ba').onclick = ()=>{ anim = {dir: tcur>0.5?-1:1}; };
document.getElementById('cm').onchange = e=>meshParts.filter(q=>q.p.n==='siatka Al').forEach(q=>q.m.visible=e.target.checked);
document.getElementById('ct').onchange = e=>{ T.visible = e.target.checked; };
document.getElementById('bv').onclick = ()=>{ az=-Math.PI/2; el=0.02; rad=5200; tgt.set(0,-100,-1100); cam(); };
document.getElementById('bt').onclick = ()=>{ az=-Math.PI/2+0.001; el=1.5; rad=4800; tgt.set(0,-200,-1300); cam(); };
const q = new URLSearchParams(location.search);
if (q.has('t')) go(+q.get('t')); else go(0);
if (q.has('az')) az=+q.get('az'); if (q.has('el')) el=+q.get('el'); if (q.has('r')) rad=+q.get('r');
cam();
(function loop(){ requestAnimationFrame(loop);
  if (anim){ let t = tcur + anim.dir*0.004; if (t>=1||t<=0){ t=Math.min(1,Math.max(0,t)); anim=null; } go(t); }
  renderer.render(scene, camera); })();
</script></body></html>
"""

if __name__ == "__main__":
    write_html()
    write_glb(0.0, "trap_v2_rozlozony.glb")
    write_glb(1.0, "trap_v2_do_jazdy.glb")
    print("podglad_3d.html, trap_v2_rozlozony.glb, trap_v2_do_jazdy.glb")
