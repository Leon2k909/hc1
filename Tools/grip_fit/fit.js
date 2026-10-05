// Weapon.left_grip (port_kastov.Kastov.pose) applied to an exported clip's frames, as the port would have:
// - weight: 1 with the left hand within GRIP_FADE[0] of its idle grip on tag_sling, 0 past GRIP_FADE[1];
// - the whole left arm moves by tag_sling's rotation times weight * shift (clavicle_L hangs off root);
// - ik_hand_L, which holds the hand's place on the gun, moves by weight * shift in tag_sling's axes;
// - each left finger joint but the metacarpals keeps 1 - weight * (fingers or thumb) of its bend.
// The sway clip's arms are its rest pose's in every frame (port_kastov.m4_sway), so they take frame 0's move.
const d = require('./dmx.js');
const GRIP_FADE = [1.0, 3.0];
const FINGERS = { index: 'fingers', middle: 'fingers', ring: 'fingers', pinky: 'fingers', thumb: 'thumb' };

function scaleQuat(q, f) {
    let [x, y, z, w] = q;
    if (w < 0) { x = -x; y = -y; z = -z; w = -w; }
    const half = Math.acos(Math.min(1, w));
    if (half < 1e-9) return [0, 0, 0, 1];
    const s = Math.sin(half), h = half * f;
    return [x / s * Math.sin(h), y / s * Math.sin(h), z / s * Math.sin(h), Math.cos(h)];
}

// tracks: Map bone -> {p: [[x,y,z] per frame], o: [[x,y,z,w] per frame]}
function readTracks(c) {
    const tracks = new Map();
    const byTransform = new Map(c.sk.joints.map(j => [j.attrs.transform.value, j.name]));
    for (const el of c.doc.order) {
        if (el.kind !== 'DmeChannel') continue;
        const bone = byTransform.get(el.attrs.toElement.value);
        const layer = c.doc.elements.get(c.doc.elements.get(el.attrs.log.value).attrs.layers.value[0]);
        const t = tracks.get(bone) || {}; t[el.attrs.toAttribute.value === 'position' ? 'p' : 'o'] = layer.attrs.values.value.map(d.vec);
        tracks.set(bone, t);
    }
    return tracks;
}

const at = (track, f) => track[Math.min(f, track.length - 1)];

function gripRef(idleClip) {
    return at(readTracks(idleClip).get('ik_hand_L').p, 0);
}

function apply(c, tracks, fit, ref, clipName) {
    const out = new Map([...tracks].map(([k, v]) => [k, { p: v.p.map(x => x.slice()), o: v.o.map(x => x.slice()) }]));
    const count = Math.max(...[...tracks.values()].map(t => t.p.length));
    const sway = clipName === 'sway';
    const weightAt = f => {
        const ik = at(tracks.get('ik_hand_L').p, f);
        const dist = Math.hypot(ik[0] - ref[0], ik[1] - ref[1], ik[2] - ref[2]);
        return Math.min(1, Math.max(0, (GRIP_FADE[1] - dist) / (GRIP_FADE[1] - GRIP_FADE[0])));
    };
    const worldOf = (f, bone) => { // world matrix of a bone from the original tracks
        let m = null; let b = bone; const chain = [];
        while (b) { chain.unshift(b); b = c.sk.parent.get(b); }
        for (const n of chain) {
            const t = tracks.get(n); const l = d.fromPQ(at(t.p, f), at(t.o, f));
            m = m ? d.mul(m, l) : l;
        }
        return m;
    };
    const ensure = (bone, f) => { // a track as long as the clip
        const t = out.get(bone);
        while (t.p.length < count) t.p.push(t.p[t.p.length - 1].slice());
        while (t.o.length < count) t.o.push(t.o[t.o.length - 1].slice());
    };
    for (const bone of ['clavicle_L', 'ik_hand_L', ...Object.keys(FINGERS).flatMap(fi => (fi === 'thumb' ? [0, 1, 2] : [0, 1, 2]).map(j => `finger_${fi}_${j}_L`))]) ensure(bone);
    for (let f = 0; f < count; f++) {
        const armFrame = sway ? 0 : f;
        const w = weightAt(f), wa = weightAt(armFrame);
        // ik_hand_L: += w * shift in tag_sling's axes.
        const ikp = out.get('ik_hand_L').p[f];
        for (let i = 0; i < 3; i++) ikp[i] += w * fit.shift[i];
        // The arm: tag_sling's rotation times wa * shift, into root's frame for clavicle_L.
        const sling = worldOf(armFrame, 'tag_sling'), root = worldOf(armFrame, 'root');
        const world = d.rot(sling, fit.shift.map(v => v * wa));
        const inRoot = d.rot(d.inv(root), world);
        const cp = out.get('clavicle_L').p[f];
        for (let i = 0; i < 3; i++) cp[i] += inRoot[i];
        // The fingers open.
        for (const [finger, kind] of Object.entries(FINGERS)) {
            const opening = wa * fit[kind];
            if (opening <= 0) continue;
            for (const j of [0, 1, 2]) {
                const t = out.get(`finger_${finger}_${j}_L`);
                t.o[f] = scaleQuat(at(tracks.get(`finger_${finger}_${j}_L`).o, armFrame), 1 - opening);
            }
        }
    }
    return out;
}

// Locals (matrices) of one frame from tracks.
function frameLocals(c, tracks, f) {
    const local = new Map();
    for (const j of c.sk.joints) { const t = tracks.get(j.name); local.set(j.name, d.fromPQ(at(t.p, f), at(t.o, f))); }
    return local;
}

module.exports = { apply, readTracks, gripRef, frameLocals, scaleQuat, at };
