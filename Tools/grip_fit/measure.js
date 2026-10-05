// How close a ported gun's left hand comes to the gun, from the exported DMXs: sample points along the palm (hand_L to
// each knuckle) and each finger (its bones and an estimated tip) against the gun's mesh skinned to a clip frame. Each
// line is a sample group's lowest signed distance (negative: inside, by winding number) from the bone axis, so it
// leaves out the flesh: compare guns with each other, as the MCX was against the verified Kastov 762 (2026-10-05).
// node Tools/grip_fit/measure.js <Folder> <model> <clip> [frame] [bodygroup mesh dmx files...]
//   e.g. node Tools/grip_fit/measure.js MCX mcx ads 1 v_mcx_iron_sights.dmx v_mcx_muzzle_tip.dmx
const path = require('path');
const d = require('./dmx.js');
const ROOT = path.join(__dirname, '..', '..', 'Assets', 'Weapons');

function gunTriangles(folder, model, frameLocal, clipSk, extras) {
    const worldPose = d.worlds(clipSk, frameLocal);
    const tris = [];
    for (const file of [`v_${model}.dmx`, ...extras]) {
        const m = d.mesh(`${ROOT}/${folder}/models/${file}`);
        const skin = m.names.map(n => worldPose.has(n) && m.bind.has(n) ? d.mul(worldPose.get(n), d.inv(m.bind.get(n))) : null);
        const V = m.P.map((p, i) => {
            const out = [0, 0, 0]; let total = 0;
            for (let k = 0; k < m.perVertex; k++) {
                const w = m.W[i * m.perVertex + k], j = m.J[i * m.perVertex + k];
                if (w <= 0 || !skin[j]) continue;
                const q = d.apply(skin[j], p); out[0] += w * q[0]; out[1] += w * q[1]; out[2] += w * q[2]; total += w;
            }
            return total > 0 ? out.map(v => v / total) : p;
        });
        for (const [a, b, c, mat] of m.faces) tris.push([V[a], V[b], V[c], mat, file]);
    }
    return { tris, worldPose };
}

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const scale = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const len = a => Math.sqrt(dot(a, a));

// Closest point on a triangle (Ericson).
function closest(p, a, b, c) {
    const ab = sub(b, a), ac = sub(c, a), ap = sub(p, a);
    const d1 = dot(ab, ap), d2 = dot(ac, ap);
    if (d1 <= 0 && d2 <= 0) return a;
    const bp = sub(p, b), d3 = dot(ab, bp), d4 = dot(ac, bp);
    if (d3 >= 0 && d4 <= d3) return b;
    const vc = d1 * d4 - d3 * d2;
    if (vc <= 0 && d1 >= 0 && d3 <= 0) return add(a, scale(ab, d1 / (d1 - d3)));
    const cp = sub(p, c), d5 = dot(ab, cp), d6 = dot(ac, cp);
    if (d6 >= 0 && d5 <= d6) return c;
    const vb = d5 * d2 - d1 * d6;
    if (vb <= 0 && d2 >= 0 && d6 <= 0) return add(a, scale(ac, d2 / (d2 - d6)));
    const va = d3 * d6 - d5 * d4;
    if (va <= 0 && d4 - d3 >= 0 && d5 - d6 >= 0) {
        const w = (d4 - d3) / ((d4 - d3) + (d5 - d6));
        return add(b, scale(sub(c, b), w));
    }
    const denom = 1 / (va + vb + vc);
    return add(a, add(scale(ab, vb * denom), scale(ac, vc * denom)));
}

// Generalized winding number of the gun's triangles round p (> 0.5: inside), plus the nearest surface.
function probe(p, tris) {
    let best = Infinity, bestTri = null, wind = 0;
    for (const t of tris) {
        const q = closest(p, t[0], t[1], t[2]);
        const dd = len(sub(p, q));
        if (dd < best) { best = dd; bestTri = t; }
        if (dd < 6) { // solid angle (Van Oosterom & Strackee), local triangles only
            const a = sub(t[0], p), b = sub(t[1], p), c = sub(t[2], p);
            const la = len(a), lb = len(b), lc = len(c);
            const num = dot(a, cross(b, c));
            const den = la * lb * lc + dot(a, b) * lc + dot(a, c) * lb + dot(b, c) * la;
            wind += 2 * Math.atan2(num, den);
        }
    }
    return { dist: best, tri: bestTri, wind: wind / (4 * Math.PI) };
}

const FINGERS = ['index', 'middle', 'ring', 'pinky', 'thumb'];
// Sample points: along each finger's bones to an estimated tip, and across the palm.
function samples(world, local) {
    const out = [];
    const P = n => d.pos(world.get(n));
    for (const f of FINGERS) {
        const chain = f === 'thumb' ? ['finger_thumb_0_L', 'finger_thumb_1_L', 'finger_thumb_2_L'] :
            [`finger_${f}_meta_L`, `finger_${f}_0_L`, `finger_${f}_1_L`, `finger_${f}_2_L`];
        // The last bone's tip: its parent's child offset again, in its own frame, at 0.8 the length.
        const lastLocal = d.pos(local.get(chain[chain.length - 1]));
        const tip = d.apply(world.get(chain[chain.length - 1]), scale(lastLocal, 0.8));
        const pts = chain.map(P).concat([tip]);
        for (let s = f === 'thumb' ? 0 : 1; s + 1 < pts.length; s++)
            for (let k = 0; k <= 4; k++) out.push({ name: `${f}${s}`, p: add(pts[s], scale(sub(pts[s + 1], pts[s]), k / 4)) });
    }
    // The palm: hand_L to each knuckle (finger_*_0).
    for (const f of ['index', 'middle', 'ring', 'pinky'])
        for (let k = 0; k <= 4; k++) out.push({ name: `palm-${f}`, p: add(P('hand_L'), scale(sub(P(`finger_${f}_0_L`), P('hand_L')), k / 4)) });
    return out;
}

function report(folder, model, clipName, frame, extras) {
    const c = d.clip(`${ROOT}/${folder}/models/anims/${clipName}.dmx`);
    const local = c.frames[Math.min(frame, c.frames.length - 1)];
    const { tris, worldPose } = gunTriangles(folder, model, local, c.sk, extras);
    const rows = {};
    for (const s of samples(worldPose, local)) {
        const r = probe(s.p, tris);
        const inside = r.wind > 0.5;
        const signed = inside ? -r.dist : r.dist;
        const row = rows[s.name] || (rows[s.name] = { min: Infinity, mat: '' });
        if (signed < row.min) { row.min = signed; row.mat = r.tri[3]; }
    }
    return rows;
}

if (require.main === module) {
    const [folder, model, clipName, frame = '0', ...extras] = process.argv.slice(2);
    const rows = report(folder, model, clipName, Number(frame), extras);
    for (const [k, v] of Object.entries(rows)) console.log(k.padEnd(14), v.min.toFixed(3).padStart(7), v.mat);
}
module.exports = { report, samples, probe, gunTriangles };
