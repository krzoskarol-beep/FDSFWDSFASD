import json,struct,sys,numpy as np
def load(p):
    d=open(p,"rb").read()
    L=struct.unpack('<I',d[12:16])[0]
    j=json.loads(d[20:20+L])
    off=20+L; BL=struct.unpack('<I',d[off:off+4])[0]; buf=d[off+8:off+8+BL]
    def acc(i):
        a=j['accessors'][i]; bv=j['bufferViews'][a['bufferView']]
        dt={5126:np.float32,5125:np.uint32,5123:np.uint16,5121:np.uint8}[a['componentType']]
        n={'SCALAR':1,'VEC3':3,'VEC2':2,'VEC4':4}[a['type']]
        o=bv.get('byteOffset',0)+a.get('byteOffset',0)
        return np.frombuffer(buf,dtype=dt,count=a['count']*n,offset=o).reshape(-1,n) if n>1 else np.frombuffer(buf,dtype=dt,count=a['count'],offset=o)
    parts=[]
    for nd in j['nodes']:
        if 'mesh' not in nd: continue
        m=j['meshes'][nd['mesh']]
        for pr in m['primitives']:
            V=acc(pr['attributes']['POSITION']).astype(float)
            F=acc(pr['indices']).reshape(-1,3) if 'indices' in pr else np.arange(len(V)).reshape(-1,3)
            M=np.eye(4)
            if 'matrix' in nd: M=np.array(nd['matrix']).reshape(4,4).T
            if 'translation' in nd: M[:3,3]=nd['translation']
            V=(np.c_[V,np.ones(len(V))]@M.T)[:,:3]
            parts.append(dict(name=nd['name'],V=V,F=F,mat=j['materials'][pr['material']]['name'] if 'material' in pr else None))
    return j,parts


def materials(j):
    """Lista materiałów glTF (dict) w kolejności z pliku."""
    return j.get('materials', [])
