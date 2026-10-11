# Author Ronie's extra animations in Blender, starting from his idle pose (frame at 12.8 s of the source clip).
# Poses are written as world-space rotations ("turn the head 25° to his left"), so the rig's bone axes don't matter.
import bpy, sys, math
from mathutils import Vector, Matrix, Quaternion

args = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = args[0], args[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
scene = bpy.context.scene
FPS = scene.render.fps / scene.render.fps_base
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
src_action = arm.animation_data.action
pb = arm.pose.bones
for p in pb: p.rotation_mode = 'QUATERNION'

B = lambda s: next(n for n in pb.keys() if n.startswith('CC_Base_' + s + '_') or n == 'CC_Base_' + s)
HIP, PELVIS, WAIST, SP1, SP2 = B('Hip'), B('Pelvis'), B('Waist'), B('Spine01'), B('Spine02')
NK1, NK2, HEAD = B('NeckTwist01'), B('NeckTwist02'), B('Head')
CL_L, UA_L, FA_L, HD_L = B('L_Clavicle'), B('L_Upperarm'), B('L_Forearm'), B('L_Hand')
CL_R, UA_R, FA_R, HD_R = B('R_Clavicle'), B('R_Upperarm'), B('R_Forearm'), B('R_Hand')
LEGS = [n for n in pb.keys() if any(k in n for k in ('Thigh', 'Calf', 'Foot', 'Toe', 'Knee'))]
LEG = {s: (B(f'{s}_Thigh'), B(f'{s}_Calf'), B(f'{s}_Foot')) for s in ('L', 'R')}
ORDER = [HIP, PELVIS, WAIST, SP1, SP2, NK1, NK2, HEAD, CL_L, UA_L, FA_L, HD_L, CL_R, UA_R, FA_R, HD_R]

# world axes → armature space.  He faces -Y in Blender; his right is -X.
mw3 = arm.matrix_world.to_3x3()
toArm = lambda v: (mw3.inverted() @ Vector(v)).normalized()
AX = {'up': toArm((0, 0, 1)), 'right': toArm((-1, 0, 0)), 'fwd': toArm((0, -1, 0))}
# conventions (degrees): up+ = turn to HIS left; right+ = top tips back / a hanging limb swings forward;
#                        fwd+ = top tilts to HIS right / a hanging limb swings to his left

def frame_of(t): return t * FPS

def basis_at(action_time):
    scene.frame_set(int(math.floor(frame_of(action_time))), subframe=frame_of(action_time) % 1)
    return {n: (p.location.copy(), p.rotation_quaternion.copy(), p.scale.copy()) for n, p in pb.items()}

BASE = basis_at(12.8)
JUMP = {k: basis_at(13.1 + k / FPS) for k in range(0, int(2.2 * FPS) + 2)}   # the source clip's clean hop
arm.animation_data.action = None

def set_basis(snap, names=None):
    for n, (loc, q, sc) in snap.items():
        if names is None or n in names:
            pb[n].location = loc; pb[n].rotation_quaternion = q; pb[n].scale = sc
    bpy.context.view_layer.update()

def rot_world(name, axis, deg, pivot=None):
    p = pb[name]
    M = p.matrix.copy()
    c = pivot if pivot is not None else M.translation.copy()
    R = Matrix.Rotation(math.radians(deg), 4, AX[axis])
    sc = p.scale.copy()
    p.matrix = Matrix.Translation(c) @ R @ Matrix.Translation(-c) @ M
    p.scale = sc                                     # a rotation must never change the bone's size
    bpy.context.view_layer.update()

def ease(x): return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, x)))

def mix(x, y, f):
    """Blend two values; either may be a number or a per-joint tuple (a missing value counts as 0)."""
    if isinstance(x, tuple) or isinstance(y, tuple):
        size = len(x) if isinstance(x, tuple) else len(y)
        x = x if isinstance(x, tuple) else (x,) * size
        y = y if isinstance(y, tuple) else (y,) * size
        return tuple(p * (1 - f) + q * f for p, q in zip(x, y))
    return x * (1 - f) + y * f

def offsets_at(keys, t):
    """keys: [(time, {bone: {axis: deg}})] → interpolated {bone: {axis: deg}} with ease in/out."""
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            f = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1
            out = {}
            for bone in set(a) | set(b):
                axes = set(a.get(bone, {})) | set(b.get(bone, {}))
                out[bone] = {ax: mix(a.get(bone, {}).get(ax, 0), b.get(bone, {}).get(ax, 0), f) for ax in axes}
            return out
    return keys[-1][1] if t >= keys[-1][0] else keys[0][1]

FEET_MID = None
REACH_TARGET = {}
FOOT_REF = {}          # each foot's idle position and orientation (armature space): a crouch keeps them planted
def apply(offs):
    def turn(bone):
        for ax in ('up', 'right', 'fwd'):
            d = offs[bone].get(ax, 0)
            if abs(d) > 1e-4:
                rot_world(bone, ax, d, FEET_MID if bone == HIP else None)
    cr = offs.get('CR')
    crouching = bool(cr) and (cr.get('d', 0) > 1e-4 or abs(cr.get('b', 0)) > 1e-4)
    if crouching: drop_hips(cr.get('d', 0), cr.get('b', 0))
    for bone in ORDER:
        if bone in offs and bone not in (HD_L, HD_R): turn(bone)
    if crouching: plant_legs()
    for side in ('L', 'R'):
        r = offs.get('R' + side)
        if r and r.get('w', 0) > 1e-3 and side in REACH_TARGET: reach(side, REACH_TARGET[side], r['w'])
    r = offs.get('RS')                       # the right hand out in front, showing something ('show')
    if r and r.get('w', 0) > 1e-3: reach('R', 'show', r['w'])
    for bone in (HD_L, HD_R):
        if bone in offs: turn(bone)
    for side in ('L', 'R'):
        h = offs.get('F' + side)
        if h and FINGERS: curl(side, h.get('f', 0), h.get('t', 0))
        if h and h.get('palm', 0) > 1e-3: palm_to_camera(side, h['palm'])   # after the fingers, so it sees the final hand
        if h and abs(h.get('tilt', 0)) > 1e-3: rot_world(HD_R if side == 'R' else HD_L, 'right', h['tilt'])   # fingers tip up
        if h and abs(h.get('opp', 0)) > 1e-3:                       # the thumb swings round in front of the palm
            t1 = FING[side][1][0]
            rot_axis(t1, pb[t1].matrix.to_3x3().col[2].normalized(), h['opp'])

# Hands: four fingers driven as one block by the Index1-3 chain, plus a thumb (Thumb1-3).
# Pseudo-bones 'FL'/'FR' in a pose: {'f': finger curl, 't': thumb curl} in degrees. + closes towards a fist,
# - opens past the relaxed idle curl. Curl axis = across the knuckles, from the palm plane (fingers × thumb).
FING = {s: ([B(f'{s}_Index{i}') for i in (1, 2, 3)], [B(f'{s}_Thumb{i}') for i in (1, 2, 3)]) for s in ('L', 'R')}
FINGER_BONES = [n for s in FING.values() for chain in s for n in chain]
SPREAD = (1.0, 1.0, 0.8)                         # how a curl is shared along each chain (knuckle → tip)
FINGERS = False                                  # finger poses switched off (hands keep their relaxed idle pose)

def rot_axis(name, axis, deg):
    p = pb[name]; M = p.matrix.copy(); c = M.translation.copy(); sc = p.scale.copy()
    p.matrix = Matrix.Translation(c) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-c) @ M
    p.scale = sc
    bpy.context.view_layer.update()

def curl(side, f, t):
    """Bend the finger block and thumb. f / t: one angle for all three joints, or a (knuckle, middle, tip) tuple.
    Each joint bends about its own bone axis (fingers: local Z, thumb: local X) — measured on this rig to give
    clean, untwisted motion. + closes, - opens. Checked on the right hand (the only one posed so far)."""
    idx, thb = FING[side]
    for chain, deg, a in ((idx, f, 2), (thb, -t if isinstance(t, (int, float)) else tuple(-x for x in t), 0)):
        degs = deg if isinstance(deg, tuple) else tuple(deg * share for share in SPREAD)
        for n, d in zip(chain, degs):
            if abs(d) > 1e-3: rot_axis(n, pb[n].matrix.to_3x3().col[a].normalized(), d)

def palm_to_camera(side, w):
    """Turn the hand so its palm faces the viewer and the hand continues the line of the forearm (w: 0..1)."""
    sign = 1 if side == 'R' else -1
    idx, thb = FING[side]
    hand, fore = (HD_R, FA_R) if side == 'R' else (HD_L, FA_L)
    palm = -sign * pb[idx[0]].matrix.to_3x3().col[0].normalized()   # fingers curl towards their local -X: the palm
    cx = (pb[hand].tail - pb[hand].head).normalized()
    cy = (palm - palm.dot(cx) * cx).normalized(); cz = cx.cross(cy)
    # the hand points halfway between the forearm's line and straight up, so the palm stays upright as it waves
    tx = ((pb[fore].tail - pb[fore].head).normalized() + AX['up']).normalized()
    front = AX['fwd']
    ty = (front - front.dot(tx) * tx).normalized(); tz = tx.cross(ty)
    C = Matrix((cx, cy, cz)).transposed(); T = Matrix((tx, ty, tz)).transposed()
    q = Quaternion().slerp((T @ C.transposed()).to_quaternion(), w)
    axis, ang = q.to_axis_angle()
    if abs(ang) > 1e-4: rot_axis(hand, axis, math.degrees(ang))

# ---- reaching: put a wrist on a point (analytic two-bone IK, elbow bent towards a pole), blended by weight.
# Joints are measured head to head (shoulder → elbow → wrist): this rig's bone tails don't point at their children.
mwi = arm.matrix_world.inverted()
wvec = lambda x, y, z: mw3.inverted() @ Vector((x, y, z))         # a world-space offset (metres) in armature space
REACH_POLE = {'R': (-1.0, 0.7, -0.6), 'L': (1.0, 0.7, -0.6)}       # default: elbows point out, back and down
# up at the face the elbow drops down and in front, so the forearm comes up to it (not across the chest)
REACH_POLE_FACE = {'R': (-0.35, -0.5, -1.0), 'L': (0.35, -0.5, -1.0)}
# wrist targets, as offsets (world metres, he faces -Y) from a bone that moves with him
REACH = {
    'chin':    (HEAD, (-0.03, -0.21, -0.17)),
    'face':    (HEAD, (-0.02, -0.27, -0.04)),
    'scratch': (HEAD, (-0.21, 0.09, -0.04)),
    'chest':   (SP2, (-0.02, -0.30, 0.02)),
    # the photo on the floor, in front of and just outside his right foot (the feet stay planted, so this holds still)
    'floor':   (B('R_Foot'), (-0.07, -0.34, -0.06)),
    # a hand resting on top of the left knee while he crouches
    'knee':    (B('L_Calf'), (0.03, -0.12, 0.10)),
    # holding a card out to the viewer: arm's length in front, out to his right, chest high
    'show':    (SP2, (-0.30, -0.42, -0.05)),
}
REACH_POLE_DOWN = {'R': (-1.0, 0.4, 0.5), 'L': (1.0, 0.4, 0.5)}   # reaching down: elbows out, back and up
def reach(side, where, w):
    UA, FA, HD = (UA_R, FA_R, HD_R) if side == 'R' else (UA_L, FA_L, HD_L)
    bone, off = REACH[where]
    T = pb[bone].head + wvec(*off)
    fk = {n: pb[n].rotation_quaternion.copy() for n in (UA, FA)}
    S, E, W = pb[UA].head.copy(), pb[FA].head.copy(), pb[HD].head.copy()
    a, b = (E - S).length, (W - E).length
    d = max(abs(a - b) + 1e-3, min(a + b - 1e-3, (T - S).length))
    n = (T - S).normalized(); T = S + n * d
    x = (a * a - b * b + d * d) / (2 * d); h = math.sqrt(max(0.0, a * a - x * x))
    poles = REACH_POLE_FACE if where in ('chin', 'face') else REACH_POLE_DOWN if where in ('floor', 'knee') else REACH_POLE
    pole = wvec(*poles[side]).normalized()
    perp = (pole - n * pole.dot(n)).normalized()
    E2 = S + n * x + perp * h
    q = (E - S).normalized().rotation_difference((E2 - S).normalized())
    axis, ang = q.to_axis_angle()
    if abs(ang) > 1e-5: rot_axis(UA, axis, math.degrees(ang))
    E, W = pb[FA].head.copy(), pb[HD].head.copy()
    q = (W - E).normalized().rotation_difference((T - E).normalized())
    axis, ang = q.to_axis_angle()
    if abs(ang) > 1e-5: rot_axis(FA, axis, math.degrees(ang))
    if w < 0.999:
        ik = {n: pb[n].rotation_quaternion.copy() for n in (UA, FA)}
        for n in (UA, FA): pb[n].rotation_quaternion = fk[n].slerp(ik[n], max(0.0, w))
        bpy.context.view_layer.update()

# ---- crouching: the hips go down (and back); each leg is re-solved so its foot stays exactly where it stood
KNEE_POLE = {'R': (-0.3, -1.0, 0.1), 'L': (0.3, -1.0, 0.1)}           # knees bend forward and a little outward
def drop_hips(d, back):
    p = pb[HIP]; M = p.matrix.copy(); sc = p.scale.copy()
    M.translation = M.translation + wvec(0, back, -d)
    p.matrix = M; p.scale = sc
    bpy.context.view_layer.update()

def plant_legs():
    for side in ('L', 'R'):
        TH, CA, FT = LEG[side]
        T, FM = FOOT_REF[side]
        S, E, W = pb[TH].head.copy(), pb[CA].head.copy(), pb[FT].head.copy()
        a, b = (E - S).length, (W - E).length
        d = max(abs(a - b) + 1e-3, min(a + b - 1e-3, (T - S).length))
        n = (T - S).normalized()
        x = (a * a - b * b + d * d) / (2 * d); h = math.sqrt(max(0.0, a * a - x * x))
        pole = wvec(*KNEE_POLE[side]).normalized()
        perp = (pole - n * pole.dot(n)).normalized()
        E2 = S + n * x + perp * h
        q = (E - S).normalized().rotation_difference((E2 - S).normalized())
        axis, ang = q.to_axis_angle()
        if abs(ang) > 1e-5: rot_axis(TH, axis, math.degrees(ang))
        E, W = pb[CA].head.copy(), pb[FT].head.copy()
        q = (W - E).normalized().rotation_difference((S + n * d - E).normalized())
        axis, ang = q.to_axis_angle()
        if abs(ang) > 1e-5: rot_axis(CA, axis, math.degrees(ang))
        # the foot keeps its idle orientation: flat on the floor
        f = pb[FT]; M = FM.copy(); M.translation = f.matrix.translation.copy(); sc = f.scale.copy()
        f.matrix = M; f.scale = sc
        bpy.context.view_layer.update()

LASTQ = {}
KEY_ALL = set()
def key(names, f):
    for n in names:
        # keep each bone's quaternion on the same side as its previous key (q and -q are the same rotation,
        # but interpolating between them swings the bone the long way round)
        q = pb[n].rotation_quaternion
        if n in LASTQ and q.dot(LASTQ[n]) < 0: pb[n].rotation_quaternion = -q
        LASTQ[n] = pb[n].rotation_quaternion.copy()
        pb[n].keyframe_insert('rotation_quaternion', frame=f)
        pb[n].keyframe_insert('location', frame=f)
        if f in KEY_ALL: pb[n].keyframe_insert('scale', frame=f)

def make(name, length, keys, touched, legs_from_jump=False, step=2, fingers=None, reach_to=None):
    global FINGERS
    keep = FINGERS
    REACH_TARGET.clear()
    if reach_to: REACH_TARGET.update(reach_to)
    if fingers is not None: FINGERS = fingers
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data.action = act
    global FEET_MID
    LASTQ.clear()
    KEY_ALL.clear(); KEY_ALL.update({0, int(round(length * FPS))})
    set_basis(BASE)
    FEET_MID = (pb[B('L_Foot')].head + pb[B('R_Foot')].head) / 2
    for side in ('L', 'R'): FOOT_REF[side] = (pb[LEG[side][2]].head.copy(), pb[LEG[side][2]].matrix.copy())
    names = set(touched) | set(FINGER_BONES) | ({HIP, PELVIS, WAIST, SP1, SP2} | set(LEGS) if legs_from_jump else set())
    n = int(round(length * FPS))
    for f in list(range(0, n, step)) + [n]:
        t = f / FPS
        set_basis(BASE)
        if legs_from_jump:
            set_basis(JUMP[min(f, max(JUMP))], names={HIP, PELVIS, WAIST, SP1, SP2, *LEGS})
        apply(offsets_at(keys, t))
        # every other bone holds the idle pose (keyed at both ends), so the clip never falls back to the rest pose
        key(set(pb.keys()) if f in (0, n) else names, f)
    for fc in getattr(act, 'fcurves', []):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    arm.animation_data.action = None
    FINGERS = keep
    print('MADE', name, n, 'frames', len(names), 'bones')

Z = {}
# ---------------- idle variations ----------------
look_l = {HEAD: {'up': 13, 'right': 4}, NK2: {'up': 19}, SP2: {'up': 7}, 'FL': {'f': 8, 't': 6}, 'FR': {'f': -6}}
look_r = {HEAD: {'up': -12, 'right': 2, 'fwd': 3}, NK2: {'up': -18}, SP2: {'up': -7}, 'FL': {'f': -5}, 'FR': {'f': 10, 't': 8}}
make('idle_look', 6.0, [(0, Z), (1.1, look_l), (2.3, {**look_l, HEAD: {'up': 15, 'right': 2}}), (3.3, look_r),
                        (4.5, {**look_r, HEAD: {'up': -14, 'right': 0, 'fwd': 3}}), (5.6, Z), (6.0, Z)],
     [HEAD, NK2, SP2])

sway_r = {HIP: {'fwd': 2.2}, SP1: {'fwd': -1.6}, NK2: {'fwd': -1.0}, HEAD: {'fwd': 1.5},
          UA_R: {'fwd': -2}, UA_L: {'fwd': -2}, 'FR': {'f': 14, 't': 10}, 'FL': {'f': -6}}
sway_l = {HIP: {'fwd': -2.2}, SP1: {'fwd': 1.6}, NK2: {'fwd': 1.0}, HEAD: {'fwd': -1.5},
          UA_R: {'fwd': 2}, UA_L: {'fwd': 2}, 'FL': {'f': 14, 't': 10}, 'FR': {'f': -6}}
make('idle_sway', 6.4, [(0, Z), (1.6, sway_r), (2.4, sway_r), (4.0, sway_l), (4.8, sway_l), (6.4, Z)],
     [HIP, SP1, NK2, HEAD, UA_L, UA_R])

spread = {'f': -28, 't': -32}
stretch = {SP2: {'right': 10}, NK2: {'right': 9}, HEAD: {'right': 9}, CL_L: {'fwd': 7, 'right': -6}, CL_R: {'fwd': -7, 'right': -6},
           UA_L: {'fwd': 18, 'right': -24}, UA_R: {'fwd': -18, 'right': -24}, FA_L: {'right': 10}, FA_R: {'right': 10},
           'FL': spread, 'FR': spread}
stretch2 = {**stretch, UA_L: {'fwd': 22, 'right': -30}, UA_R: {'fwd': -22, 'right': -30}, SP2: {'right': 12}, HEAD: {'right': 11},
            NK2: {'right': 11}}
make('idle_stretch', 5.6, [(0, Z), (1.1, stretch), (1.9, stretch2),
                           (2.8, {HEAD: {'fwd': 7}, NK2: {'fwd': 12}, 'FL': {'f': 10}, 'FR': {'f': 10}}),
                           (3.6, {HEAD: {'fwd': -7}, NK2: {'fwd': -12}}),
                           (4.6, Z), (5.6, Z)],
     [SP2, NK2, HEAD, CL_L, CL_R, UA_L, UA_R, FA_L, FA_R])

check = {SP2: {'up': -5, 'right': -3}, HEAD: {'up': -8, 'right': -11}, NK2: {'up': -8, 'right': -10},
         UA_R: {'right': 32, 'fwd': 14}, FA_R: {'right': 78}, HD_R: {'up': 0}}
make('idle_hand', 5.6, [(0, Z), (1.0, {**check, 'FR': {'f': -26, 't': -28}}),            # opens the hand…
                        (1.8, {**check, HD_R: {'fwd': 28}, 'FR': {'f': 62, 't': 42}}),    # …makes a fist…
                        (2.6, {**check, HD_R: {'fwd': -22}, 'FR': {'f': -24, 't': -26}}), # …opens again…
                        (3.4, {**check, 'FR': {'f': 30, 't': 18}}), (4.5, Z), (5.6, Z)],  # …and relaxes
     [SP2, NK2, HEAD, UA_R, FA_R, HD_R])

fist = {'f': 64, 't': 44}
arms_back = {UA_L: {'right': -14}, UA_R: {'right': -14}, 'FL': {'f': 20, 't': 10}, 'FR': {'f': 20, 't': 10}}
arms_up = {UA_L: {'fwd': 115, 'right': 30}, UA_R: {'fwd': -115, 'right': 30}, FA_L: {'right': 25}, FA_R: {'right': 25},
           SP2: {'right': 8}, HEAD: {'right': 7}, NK2: {'right': 7}, 'FL': fist, 'FR': fist}
pump = {UA_L: {'right': 55, 'fwd': 10}, UA_R: {'right': 55, 'fwd': -10}, FA_L: {'right': 105}, FA_R: {'right': 105},
        SP2: {'right': -4}, HEAD: {'right': 3}, NK2: {'right': 3}, 'FL': {'f': 70, 't': 48}, 'FR': {'f': 70, 't': 48}}
make('excited', 2.2, [(0, Z), (0.45, arms_back), (0.8, arms_up), (1.05, arms_up), (1.35, pump), (1.6, pump), (2.2, Z)],
     [SP2, NK2, HEAD, UA_L, UA_R, FA_L, FA_R], legs_from_jump=True, step=1)

palms = {'f': -26, 't': -34}
shrug = {HEAD: {'fwd': 10, 'up': 4}, NK2: {'fwd': 14, 'up': 4}, SP2: {'right': 4},
         CL_L: {'fwd': 9}, CL_R: {'fwd': -9},
         UA_L: {'fwd': 4, 'right': 8}, UA_R: {'fwd': -4, 'right': 8}, FA_L: {'right': 75, 'up': 22}, FA_R: {'right': 75, 'up': -22},
         HD_L: {'fwd': -55}, HD_R: {'fwd': 55}, 'FL': palms, 'FR': palms}
hmm = {**shrug, HEAD: {'fwd': -6, 'up': -3, 'right': -3}, NK2: {'fwd': -9, 'up': -3, 'right': -3}, 'FL': {'f': -10, 't': -14}, 'FR': {'f': -10, 't': -14}}
make('confused', 3.4, [(0, Z), (0.55, shrug), (1.2, shrug), (1.8, hmm), (2.5, hmm), (3.4, Z)],
     [HEAD, NK2, SP2, CL_L, CL_R, UA_L, UA_R, FA_L, FA_R, HD_L, HD_R])

# ---------------- wave: the hello after the wake-up leap ----------------
# right arm up and out, forearm upright, swinging side to side; a little lean away and a head tilt into it
hello = {'palm': 1, 'f': (-30, -30, -25), 't': (-15, -15, -15)}   # open hand, thumb out, palm to the viewer
up = {UA_R: {'fwd': -100, 'right': 14}, FA_R: {'fwd': -58},
      SP2: {'fwd': 4}, SP1: {'fwd': 2}, NK2: {'fwd': -7}, HEAD: {'fwd': -6}, UA_L: {'fwd': 6}, 'FR': hello}
swing = lambda a, bob: {**up, FA_R: {'fwd': -58 + a}, SP1: {'fwd': 2, 'right': bob}}
make('wave', 2.7, [(0, Z), (0.35, up), (0.6, swing(-24, 2)), (0.85, swing(20, -1)), (1.1, swing(-24, 2)),
                   (1.35, swing(20, -1)), (1.6, swing(-22, 2)), (1.85, swing(16, -1)), (2.1, up), (2.7, Z)],
     [SP1, SP2, NK2, HEAD, UA_R, FA_R, HD_R, UA_L], fingers=True)

# ---------------- conversational moves (the chat picks one per reply) ----------------
ARM_R = [CL_R, UA_R, FA_R, HD_R]
ARM_L = [CL_L, UA_L, FA_L, HD_L]
nod = lambda d: {HEAD: {'right': d}, NK2: {'right': d * 0.4}}
make('nod', 1.7, [(0, Z), (0.25, nod(-15)), (0.5, nod(3)), (0.78, nod(-12)), (1.05, nod(1)), (1.7, Z)], [HEAD, NK2])

shk = lambda d: {HEAD: {'up': d}, NK2: {'up': d * 0.5}}
make('shake', 1.9, [(0, Z), (0.25, shk(16)), (0.55, shk(-16)), (0.85, shk(13)), (1.15, shk(-9)), (1.9, Z)], [HEAD, NK2])

think = {HEAD: {'fwd': 8, 'right': -6}, NK2: {'fwd': 4}, SP2: {'right': -3}, 'RR': {'w': 1}, HD_R: {'right': -20}}
make('think', 3.6, [(0, Z), (0.6, think), (2.0, {**think, HEAD: {'fwd': 10, 'right': -4, 'up': 4}}), (2.9, think), (3.6, Z)],
     [HEAD, NK2, SP2, *ARM_R], reach_to={'R': 'chin'})

point = {UA_R: {'right': 72, 'fwd': 12}, FA_R: {'right': 14}, SP2: {'up': -6}, HEAD: {'right': -4}}
make('point', 2.3, [(0, Z), (0.45, point), (0.62, {**point, UA_R: {'right': 80, 'fwd': 12}}), (0.8, point), (1.7, point), (2.3, Z)],
     [HEAD, SP2, *ARM_R])

lb = lambda k: {SP2: {'right': 4 + 6 * k}, HEAD: {'right': 9 + 7 * k}, NK2: {'right': 4}, CL_L: {'fwd': 5 * k}, CL_R: {'fwd': -5 * k}}
make('laugh', 2.6, [(0, Z), (0.3, lb(1)), (0.45, lb(0)), (0.6, lb(1)), (0.75, lb(0)), (0.9, lb(1)), (1.05, lb(0.3)),
                    (1.45, {SP2: {'right': -8}, SP1: {'right': -4}, HEAD: {'right': -10}}), (1.9, {SP2: {'right': -6}, HEAD: {'right': -8}}), (2.6, Z)],
     [SP1, SP2, NK2, HEAD, CL_L, CL_R])

bow = {SP1: {'right': -14}, SP2: {'right': -16}, NK2: {'right': -4}, HEAD: {'right': -12}, UA_L: {'right': 8}, UA_R: {'right': 8}}
make('bow', 2.4, [(0, Z), (0.6, bow), (1.3, bow), (2.4, Z)], [SP1, SP2, NK2, HEAD, UA_L, UA_R])

ta = {UA_L: {'fwd': 38, 'right': 28}, UA_R: {'fwd': -38, 'right': 28}, FA_L: {'right': 35}, FA_R: {'right': 35},
      HD_L: {'fwd': -45}, HD_R: {'fwd': 45}, SP2: {'right': 5}, HEAD: {'right': 6}}
make('present', 2.6, [(0, Z), (0.5, ta), (1.8, {**ta, UA_L: {'fwd': 42, 'right': 30}, UA_R: {'fwd': -42, 'right': 30}}), (2.6, Z)],
     [SP2, HEAD, *ARM_L, *ARM_R])

sc = lambda k: {HEAD: {'right': -10, 'fwd': 8}, NK2: {'fwd': 5}, 'RR': {'w': 1}, HD_R: {'fwd': 10 * k}}
make('scratch', 3.2, [(0, Z), (0.6, sc(0)), (0.8, sc(1)), (1.0, sc(-1)), (1.2, sc(1)), (1.4, sc(-1)), (1.6, sc(1)), (1.8, sc(0)),
                      (2.5, sc(0)), (3.2, Z)], [HEAD, NK2, *ARM_R], reach_to={'R': 'scratch'})

fp = lambda u: {'RR': {'w': 1}, HEAD: {'right': -14, 'up': u}, NK2: {'right': -5}, SP2: {'right': -5}}
make('facepalm', 2.8, [(0, Z), (0.45, fp(0)), (1.0, fp(5)), (1.3, fp(-5)), (1.6, fp(4)), (1.9, fp(0)), (2.8, Z)],
     [HEAD, NK2, SP2, *ARM_R], reach_to={'R': 'face'})

flex = {UA_R: {'fwd': -88, 'right': 10}, FA_R: {'fwd': -95}, HEAD: {'up': -22}, NK2: {'up': -8}, SP2: {'right': 5, 'up': -4}}
make('flex', 2.6, [(0, Z), (0.5, flex), (0.8, {**flex, UA_R: {'fwd': -93, 'right': 10}}), (1.1, flex), (1.9, flex), (2.6, Z)],
     [HEAD, NK2, SP2, *ARM_R])

chest = {'RR': {'w': 1}, HEAD: {'right': -4, 'fwd': 4}, SP2: {'right': 2}}
make('chest', 2.4, [(0, Z), (0.5, chest), (1.7, chest), (2.4, Z)], [HEAD, SP2, *ARM_R], reach_to={'R': 'chest'})

# ---------------- the mind-reading game: pick up a photo of the guess, show it, throw it away ----------------
# pickup: he crouches, grabs the photo off the floor with his right hand (GRAB s), stands and holds it up by his face.
# It ends in HOLD, and the page holds that last frame until one of the throws (which all start from HOLD) takes over.
LEGS_IK = [HIP, PELVIS, *LEG['L'], *LEG['R']]
GRAB = 1.0
HOLD = {UA_R: {'right': 52, 'fwd': 26}, FA_R: {'right': 90}, HD_R: {'right': -10},
        SP2: {'up': 6, 'right': 2}, HEAD: {'fwd': 7, 'up': 5}, NK2: {'up': 3}, UA_L: {'fwd': 4}}
# (a desktop frames him from the hips up, so the crouch only has to read from there: the hand heads for the floor,
#  but he stays deep enough in shot that his head and shoulders never leave the frame)
squat = {'CR': {'d': 0.4, 'b': 0.14}, WAIST: {'right': -8}, SP1: {'right': -18}, SP2: {'right': -20},
         NK2: {'right': -4}, HEAD: {'right': -16}, CL_R: {'right': 10}, 'RR': {'w': 1}, 'RL': {'w': 1}}
peek = {HEAD: {'right': -14}, NK2: {'right': -6}, SP2: {'right': -4}}
make('pickup', 2.6, [(0, Z), (0.3, peek), (0.85, squat), (1.1, {**squat, HEAD: {'right': -10}}),
                     (1.9, HOLD), (2.2, {**HOLD, UA_R: {'right': 58, 'fwd': 26}, SP2: {'up': 6, 'right': 5}}), (2.6, HOLD)],
     [*LEGS_IK, WAIST, SP1, SP2, NK2, HEAD, *ARM_R, *ARM_L], step=1, reach_to={'R': 'floor', 'L': 'knee'})

# pickup_show: the same pickup, but he comes up holding the card out to the viewer at arm's length, gripping it by its
# bottom-left corner the way you'd show someone a card: fingers curled round the corner, thumb over the front, the card
# standing up and away from the hand (a project card, shown while he talks about it)
SHOW = {SP2: {'up': 4}, HEAD: {'fwd': 4, 'up': 5}, NK2: {'up': 3}, 'RS': {'w': 1},
        'FR': {'palm': 0.4, 'f': (55, 55, 40), 't': (0, 10, 10), 'opp': 30}}
make('pickup_show', 2.6, [(0, Z), (0.3, peek), (0.85, squat), (1.1, {**squat, HEAD: {'right': -10}}),
                          (1.9, SHOW), (2.2, {**SHOW, SP2: {'up': 6, 'right': 2}, HEAD: {'fwd': 5, 'up': 7}}), (2.6, SHOW)],
     [*LEGS_IK, WAIST, SP1, SP2, NK2, HEAD, *ARM_R, *ARM_L], step=1, reach_to={'R': 'floor', 'L': 'knee'}, fingers=True)

# toss_happy: fling the photo high into the air (released at 0.5 s), then both arms up and a hop of joy
fling_back = {**HOLD, UA_R: {'right': 40, 'fwd': 6}, FA_R: {'right': 100}, SP2: {'right': -4}, HEAD: {'right': -4}}
fling = {UA_R: {'right': 165, 'fwd': -10}, FA_R: {'right': 10}, SP2: {'right': 8}, HEAD: {'right': 10}, NK2: {'right': 5}}
make('toss_happy', 2.6, [(0, HOLD), (0.28, fling_back), (0.5, fling), (0.62, fling), (0.95, arms_up), (1.2, arms_up),
                         (1.5, pump), (1.75, pump), (2.6, Z)],
     [SP2, NK2, HEAD, UA_L, UA_R, FA_L, FA_R, HD_R], legs_from_jump=True, step=1)

# toss_angry: wind up over his head, hurl it down at the floor (released at 0.52 s), then a frustrated head shake
windup = {UA_R: {'right': 150, 'fwd': -25}, FA_R: {'right': 70}, SP1: {'right': 6, 'up': 8}, SP2: {'right': 8, 'up': 6},
          HEAD: {'right': 6}, UA_L: {'right': -12}}
hurl = {UA_R: {'right': 25, 'fwd': 10}, FA_R: {'right': 10}, SP1: {'right': -14, 'up': -6}, SP2: {'right': -18, 'up': -6},
        HEAD: {'right': -14}, NK2: {'right': -4}, UA_L: {'right': -18}}
fume = lambda u: {SP1: {'right': -6}, SP2: {'right': -8}, HEAD: {'right': -10, 'up': u}, NK2: {'up': u * 0.5},
                  UA_L: {'fwd': 10}, UA_R: {'fwd': -10}}
make('toss_angry', 2.8, [(0, HOLD), (0.38, windup), (0.52, {**hurl, UA_R: {'right': 70, 'fwd': 0}}), (0.66, hurl), (0.9, hurl),
                         (1.15, fume(16)), (1.4, fume(-16)), (1.65, fume(13)), (1.9, fume(-9)), (2.8, Z)],
     [SP1, SP2, NK2, HEAD, *ARM_R, UA_L])

# toss: a casual flick out to his right when the game stops mid-guess (released at 0.42 s)
across = {**HOLD, UA_R: {'right': 50, 'fwd': 22}, FA_R: {'right': 85}, SP2: {'up': 12}}
flick = {UA_R: {'right': 55, 'fwd': -55}, FA_R: {'right': 25}, SP2: {'up': -10}, HEAD: {'up': -8}}
make('toss', 1.7, [(0, HOLD), (0.26, across), (0.42, flick), (0.6, flick), (1.7, Z)], [SP2, HEAD, NK2, *ARM_R, UA_L])

# where the photo has to lie for his hand to find it (printed for js/assistant.js, in glTF coordinates: x, y up, z)
arm.animation_data.action = bpy.data.actions['pickup']
scene.frame_set(int(round(GRAB * FPS)))
mw = arm.matrix_world
for label, bone in (('wrist', HD_R), ('finger', B('R_Index1'))):
    w = mw @ pb[bone].head
    print(f'GRAB_{label} gltf=({w.x:.4f}, {w.z:.4f}, {-w.y:.4f})')
tb, off = REACH['floor']
tw = mw @ (pb[tb].head + wvec(*off))
print(f'GRAB_target gltf=({tw.x:.4f}, {tw.z:.4f}, {-tw.y:.4f})  miss={(mw @ pb[HD_R].head - tw).length:.3f}')
arm.animation_data.action = None

# drop the source clip; export only the skeleton and the new actions
bpy.data.actions.remove(src_action)
for o in bpy.data.objects: o.select_set(False)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.wm.save_as_mainfile(filepath=OUT.replace('.glb', '.blend'))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_animations=True,
                          export_animation_mode='ACTIONS', export_def_bones=False, export_skins=False,
                          export_optimize_animation_size=True, export_force_sampling=True)
print('EXPORTED', OUT)
