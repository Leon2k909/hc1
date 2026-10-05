// A small keyvalues2 DMX reader for the layout kastov_dmx.py writes (meshes, skeletons and clips), with rigid 4x4
// maths (row-major arrays of 16) for the grip tools. Node rather than Python: cloud sessions have no numpy.
const fs = require('fs');

function parse(path) {
    const text = fs.readFileSync(path, 'utf8');
    const lines = text.split('\n');
    const elements = new Map();
    const order = [];
    let i = 0;
    const str = s => { const m = s.match(/"((?:[^"\\]|\\.)*)"/g); return m ? m.map(x => x.slice(1, -1)) : []; };
    while (i < lines.length) {
        const line = lines[i].trim();
        if (line.startsWith('"') && lines[i + 1] && lines[i + 1].trim() === '{') {
            const kind = str(line)[0];
            const el = { kind, attrs: {} };
            i += 2;
            while (i < lines.length && lines[i].trim() !== '}') {
                const t = str(lines[i].trim());
                if (t.length === 2 && t[1].endsWith('_array')) {
                    const items = [];
                    i += 2; // skip '['
                    while (lines[i].trim() !== ']') {
                        const v = str(lines[i].trim());
                        items.push(v.length === 2 ? v[1] : v[0]);
                        i++;
                    }
                    el.attrs[t[0]] = { type: t[1], value: items };
                } else if (t.length >= 3) {
                    el.attrs[t[0]] = { type: t[1], value: t[2] };
                }
                i++;
            }
            if (el.attrs.id) { el.id = el.attrs.id.value; elements.set(el.id, el); }
            el.name = el.attrs.name ? el.attrs.name.value : '';
            order.push(el);
        }
        i++;
    }
    return { elements, order, lines };
}

const vec = s => s.split(' ').map(Number);

// Matrices are 4x4 row-major arrays [16].
function fromPQ(p, q) {
    const [x, y, z, w] = q;
    return [
        1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), p[0],
        2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), p[1],
        2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), p[2],
        0, 0, 0, 1];
}
function mul(a, b) {
    const r = new Array(16).fill(0);
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) {
        let s = 0; for (let k = 0; k < 4; k++) s += a[i * 4 + k] * b[k * 4 + j]; r[i * 4 + j] = s;
    }
    return r;
}
function inv(m) { // rigid
    const r = [m[0], m[4], m[8], 0, m[1], m[5], m[9], 0, m[2], m[6], m[10], 0, 0, 0, 0, 1];
    const t = [m[3], m[7], m[11]];
    for (let i = 0; i < 3; i++) r[i * 4 + 3] = -(r[i * 4] * t[0] + r[i * 4 + 1] * t[1] + r[i * 4 + 2] * t[2]);
    return r;
}
const apply = (m, p) => [m[0] * p[0] + m[1] * p[1] + m[2] * p[2] + m[3], m[4] * p[0] + m[5] * p[1] + m[6] * p[2] + m[7], m[8] * p[0] + m[9] * p[1] + m[10] * p[2] + m[11]];
const rot = (m, p) => [m[0] * p[0] + m[1] * p[1] + m[2] * p[2], m[4] * p[0] + m[5] * p[1] + m[6] * p[2], m[8] * p[0] + m[9] * p[1] + m[10] * p[2]];
const pos = m => [m[3], m[7], m[11]];

// The skeleton: joints in jointList order with parents (from the DmeModel/DmeJoint children arrays) and their DmeTransforms.
function skeleton(doc) {
    const model = doc.order.find(e => e.kind === 'DmeModel');
    const joints = []; const parent = new Map();
    const visit = (el, p) => {
        for (const id of (el.attrs.children ? el.attrs.children.value : [])) {
            const c = doc.elements.get(id);
            if (!c || c.kind !== 'DmeJoint') continue;
            parent.set(c.name, p);
            joints.push(c);
            visit(c, c.name);
        }
    };
    visit(model, null);
    const list = model.attrs.jointList ? model.attrs.jointList.value.map(id => doc.elements.get(id)) : null;
    return { model, joints, parent, list };
}

function bindLocals(doc, sk) {
    const local = new Map();
    for (const j of sk.joints) {
        const t = doc.elements.get(j.attrs.transform.value);
        local.set(j.name, fromPQ(vec(t.attrs.position.value), vec(t.attrs.orientation.value)));
    }
    return local;
}

function worlds(sk, local) {
    const world = new Map();
    for (const j of sk.joints) { // parents come first
        const p = sk.parent.get(j.name);
        world.set(j.name, p ? mul(world.get(p), local.get(j.name)) : local.get(j.name));
    }
    return world;
}

// An animation clip: frames of local transforms per bone (transform element id -> bone).
function clip(path) {
    const doc = parse(path);
    const sk = skeleton(doc);
    const bindLocal = bindLocals(doc, sk);
    const byTransform = new Map(sk.joints.map(j => [j.attrs.transform.value, j.name]));
    const tracks = new Map(); // bone -> {p: [[t, v]], o: [...]}
    for (const el of doc.order) {
        if (el.kind !== 'DmeChannel') continue;
        const bone = byTransform.get(el.attrs.toElement.value);
        const log = doc.elements.get(el.attrs.log.value);
        const layer = doc.elements.get(log.attrs.layers.value[0]);
        const times = layer.attrs.times.value.map(Number);
        const values = layer.attrs.values.value.map(vec);
        const tr = tracks.get(bone) || {}; tr[el.attrs.toAttribute.value === 'position' ? 'p' : 'o'] = { times, values };
        tracks.set(bone, tr);
    }
    const count = Math.max(...[...tracks.values()].map(t => t.p.times.length));
    const frames = [];
    for (let f = 0; f < count; f++) {
        const local = new Map();
        for (const j of sk.joints) {
            const tr = tracks.get(j.name);
            if (!tr) { local.set(j.name, bindLocal.get(j.name)); continue; }
            const p = tr.p.values[Math.min(f, tr.p.values.length - 1)], o = tr.o.values[Math.min(f, tr.o.values.length - 1)];
            local.set(j.name, fromPQ(p, o));
        }
        frames.push(local);
    }
    return { doc, sk, frames };
}

// A mesh DMX: its vertices skinned at bind (model space), each with its joints and weights, and its triangles.
function mesh(path) {
    const doc = parse(path);
    const sk = skeleton(doc);
    const names = sk.list.map(j => j.name); // jointList[0] is the model itself
    const vd = doc.order.find(e => e.kind === 'DmeVertexData');
    const P = vd.attrs['position$0'].value.map(vec);
    const PI = vd.attrs['position$0Indices'].value.map(Number);
    const perVertex = Number(vd.attrs.jointCount.value);
    const W = vd.attrs['blendweights$0'].value.map(Number);
    const J = vd.attrs['blendindices$0'].value.map(Number);
    const faces = [];
    for (const el of doc.order) if (el.kind === 'DmeFaceSet') {
        const material = doc.elements.get(el.attrs.material.value).attrs.mtlName.value;
        let poly = [];
        for (const v of el.attrs.faces.value.map(Number)) {
            if (v < 0) { for (let k = 1; k + 1 < poly.length; k++) faces.push([PI[poly[0]], PI[poly[k]], PI[poly[k + 1]], material]); poly = []; }
            else poly.push(v);
        }
    }
    const bind = worlds(sk, bindLocals(doc, sk));
    return { doc, sk, names, P, W, J, perVertex, faces, bind };
}

module.exports = { parse, skeleton, bindLocals, worlds, clip, mesh, mul, inv, apply, rot, pos, fromPQ, vec };
