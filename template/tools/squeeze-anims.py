# Shrinks models/ronie-anims.glb after Blender exports it (run it after tools/blender/ronie_anims.py):
#   python -I tools/squeeze-anims.py models/ronie-anims.glb models/ronie-anims.glb 1e-4
"""Shrink models/ronie-anims.glb without changing a single pose.

- drops the channels on non-bone nodes (assistant.js throws those away on load anyway)
- drops keyframes that the interpolation between their neighbours already reproduces (within TOL)
- merges byte-identical accessors and packs everything into one bufferView per kind (a much smaller JSON header)
usage: python -I anim_squeeze.py in.glb out.glb [tol]
"""
import json, struct, sys, gzip, math
import numpy as np

src, out = sys.argv[1], sys.argv[2]
TOL = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-5
b = open(src, 'rb').read()
n = struct.unpack('<I', b[12:16])[0]
j = json.loads(b[20:20 + n])
binc = b[20 + n + 8:]
ncomp = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}


def read(ai):
    a = j['accessors'][ai]
    assert a['componentType'] == 5126 and 'byteStride' not in j['bufferViews'][a['bufferView']]
    bv = j['bufferViews'][a['bufferView']]
    off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    c = ncomp[a['type']]
    return np.frombuffer(binc, '<f4', a['count'] * c, off).reshape(a['count'], c).copy(), a['type']


def slerp(q0, q1, t):
    d = float(np.dot(q0, q1))
    if d < 0: q1, d = -q1, -d
    if d > 0.9995:
        r = q0 + t * (q1 - q0); return r / np.linalg.norm(r)
    th = math.acos(d); s = math.sin(th)
    return (math.sin((1 - t) * th) * q0 + math.sin(t * th) * q1) / s


def simplify(times, vals, path, interp):
    """greedy: keep a key only if dropping it moves the curve more than TOL anywhere it was sampled"""
    if len(times) <= 2:
        return times, vals   # (first and last always stay: they set the clip's length)
    keep = [0]
    for i in range(1, len(times) - 1):
        a = keep[-1]
        # can we go straight from key a to key i+1, skipping i (and everything since a)?
        ok = True
        for k in range(a + 1, i + 1):
            if interp == 'STEP':
                pred = vals[a]
            else:
                t = (times[k] - times[a]) / (times[i + 1] - times[a])
                pred = slerp(vals[a].astype(np.float64), vals[i + 1].astype(np.float64), t) if path == 'rotation' else vals[a] + t * (vals[i + 1] - vals[a])
            v = vals[k]
            if path == 'rotation' and np.dot(pred, v) < 0: v = -v
            if np.max(np.abs(pred - v)) > TOL:
                ok = False; break
        if not ok:
            keep.append(i)
    keep.append(len(times) - 1)
    return times[keep], vals[keep]


new_acc, data, cache = [], [], {}
def add(arr, typ):
    arr = np.ascontiguousarray(arr, '<f4')
    key = (typ, arr.tobytes())
    if key in cache: return cache[key]
    idx = len(new_acc)
    acc = {'componentType': 5126, 'count': int(arr.shape[0]), 'type': typ, '_bytes': arr.tobytes()}
    if typ == 'SCALAR':
        acc['min'] = [float(arr.min())]; acc['max'] = [float(arr.max())]
    new_acc.append(acc); cache[key] = idx
    return idx


keys_in = keys_out = dropped = 0
for anim in j['animations']:
    chans, samps = [], []
    for ch in anim['channels']:
        node = j['nodes'][ch['target']['node']]
        if not node.get('name', '').startswith('CC_Base_'):
            dropped += 1; continue
        s = anim['samplers'][ch['sampler']]
        t, _ = read(s['input']); v, typ = read(s['output'])
        t = t[:, 0]
        keys_in += len(t)
        t2, v2 = simplify(t, v, ch['target']['path'], s.get('interpolation', 'LINEAR'))
        keys_out += len(t2)
        samps.append({'input': add(t2.reshape(-1, 1), 'SCALAR'), 'output': add(v2, typ), 'interpolation': s.get('interpolation', 'LINEAR')})
        chans.append({'sampler': len(samps) - 1, 'target': ch['target']})
    anim['channels'], anim['samplers'] = chans, samps

# pack: all accessors into one bufferView (no stride: animation data)
blob = bytearray()
for a in new_acc:
    while len(blob) % 4: blob.append(0)
    a['byteOffset'] = len(blob); a['bufferView'] = 0
    blob += a.pop('_bytes')
while len(blob) % 4: blob.append(0)
j['accessors'] = new_acc
j['bufferViews'] = [{'buffer': 0, 'byteOffset': 0, 'byteLength': len(blob)}]
j['buffers'] = [{'byteLength': len(blob)}]
js = json.dumps(j, separators=(',', ':')).encode()
while len(js) % 4: js += b' '
glb = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(blob), 0x004E4942) + bytes(blob)
open(out, 'wb').write(glb)
print(f'dropped {dropped} non-bone channels; keys {keys_in} -> {keys_out}; accessors -> {len(new_acc)}; '
      f'bytes {len(b)} -> {len(glb)}; gzip {len(gzip.compress(b, 9))} -> {len(gzip.compress(glb, 9))}')
