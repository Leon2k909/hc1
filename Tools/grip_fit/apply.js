// Applies a GripFit (kastov_weapons.Weapon.left_grip) to a gun's exported clip DMXs in place, as port_kastov.py's
// Kastov.pose would: for a session without the CoD rips (or numpy). Run it once, on clips exported without the fit:
// a second run adds the fit again. Then put the same GripFit in kastov_weapons.py, so a port from the rips matches.
// Only the channels the fit moves are rewritten: clavicle_L's and ik_hand_L's positions and the opened fingers' bends.
// node Tools/grip_fit/apply.js <Folder> <shift forward> <shift left> <shift up> <fingers> <thumb> [--dry]
// ANIMS=<dir> applies it to a copy of the anims folder instead.
const fs = require('fs');
const path = require('path');
const d = require('./dmx.js');
const F = require('./fit.js');
const [folder, sx, sy, sz, fingers, thumb, dry] = process.argv.slice(2);
if (thumb === undefined) { console.log('node apply.js <Folder> <shift forward> <shift left> <shift up> <fingers> <thumb> [--dry]'); process.exit(1); }
const fit = { shift: [Number(sx), Number(sy), Number(sz)], fingers: Number(fingers), thumb: Number(thumb) };
const dir = process.env.ANIMS || path.join(__dirname, '..', '..', 'Assets', 'Weapons', folder, 'models', 'anims');
const ref = F.gripRef(d.clip(`${dir}/idle.dmx`)); // the idle grip, from the clips as exported (unfitted)

// rotation_to_quaternion (kastov_dmx.py) of a quaternion's rotation, so signs come out as the writer picks them.
function canonical(q) {
    const m = d.fromPQ([0, 0, 0], q);
    const r = (i, j) => m[i * 4 + j];
    const tr = r(0, 0) + r(1, 1) + r(2, 2);
    let w, x, y, z, s;
    if (tr > 0) { s = 0.5 / Math.sqrt(tr + 1); w = 0.25 / s; x = (r(2, 1) - r(1, 2)) * s; y = (r(0, 2) - r(2, 0)) * s; z = (r(1, 0) - r(0, 1)) * s; }
    else if (r(0, 0) > r(1, 1) && r(0, 0) > r(2, 2)) { s = 2 * Math.sqrt(1 + r(0, 0) - r(1, 1) - r(2, 2)); w = (r(2, 1) - r(1, 2)) / s; x = 0.25 * s; y = (r(0, 1) + r(1, 0)) / s; z = (r(0, 2) + r(2, 0)) / s; }
    else if (r(1, 1) > r(2, 2)) { s = 2 * Math.sqrt(1 + r(1, 1) - r(0, 0) - r(2, 2)); w = (r(0, 2) - r(2, 0)) / s; x = (r(0, 1) + r(1, 0)) / s; y = 0.25 * s; z = (r(1, 2) + r(2, 1)) / s; }
    else { s = 2 * Math.sqrt(1 + r(2, 2) - r(0, 0) - r(1, 1)); w = (r(1, 0) - r(0, 1)) / s; x = (r(0, 2) + r(2, 0)) / s; y = (r(1, 2) + r(2, 1)) / s; z = 0.25 * s; }
    const n = Math.hypot(x, y, z, w);
    return [x / n, y / n, z / n, w / n];
}
const fmt = v => v.map(x => (Math.abs(x) < 5e-7 ? 0 : x).toFixed(6)).join(' ');

const CHANGED = ['clavicle_L', 'ik_hand_L', ...['index', 'middle', 'ring', 'pinky', 'thumb'].flatMap(f => [0, 1, 2].map(j => `finger_${f}_${j}_L`))];

for (const file of fs.readdirSync(dir).filter(f => f.endsWith('.dmx'))) {
    const name = file.replace('.dmx', '');
    const path = `${dir}/${file}`;
    const c = d.clip(path);
    const before = F.readTracks(c);
    const after = F.apply(c, before, fit, ref, name);
    const lines = c.doc.lines;
    // Element start lines: each element's "{" follows its kind line; find attributes by scanning from there.
    const starts = new Map();
    for (let i = 0; i < lines.length; i++) {
        const m = lines[i].match(/^\t"id" "elementid" "([^"]+)"/);
        if (m) starts.set(m[1], i);
    }
    const findAttr = (id, attr) => {
        for (let i = starts.get(id); i < lines.length && lines[i] !== '}'; i++)
            if (lines[i].startsWith(`\t"${attr}" `)) return i;
        throw new Error(`${attr} not found in ${id}`);
    };
    const byTransform = new Map(c.sk.joints.map(j => [j.attrs.transform.value, j.name]));
    const weights = [];
    let changed = 0;
    for (const el of c.doc.order) {
        if (el.kind !== 'DmeChannel') continue;
        const bone = byTransform.get(el.attrs.toElement.value);
        if (!CHANGED.includes(bone)) continue;
        const kind = el.attrs.toAttribute.value === 'position' ? 'p' : 'o';
        // Only what the fit moves: the arm's and the IK target's places, and the opened fingers' bends.
        const moved = fit.shift.some(v => v !== 0);
        const opening = bone.startsWith('finger_thumb') ? fit.thumb : fit.fingers;
        if (kind === 'p' ? !(moved && (bone === 'clavicle_L' || bone === 'ik_hand_L')) : !(bone.startsWith('finger_') && opening > 0)) continue;
        let values = after.get(bone)[kind];
        if (kind === 'o') { // the writer's signs: canonical, then kept continuous
            let prev = null;
            values = values.map(q => { let r = canonical(q); if (prev && r.reduce((s, v, i) => s + v * prev[i], 0) < 0) r = r.map(v => -v); prev = r; return r; });
        }
        const layerId = c.doc.elements.get(el.attrs.log.value).attrs.layers.value[0];
        const at = findAttr(layerId, 'values');
        const count = c.doc.elements.get(layerId).attrs.values.value.length;
        if (count !== values.length) throw new Error(`${file} ${bone}: ${count} keys, ${values.length} values`);
        for (let k = 0; k < count; k++) lines[at + 2 + k] = `\t\t"${fmt(values[k])}"${k < count - 1 ? ',' : ''}`;
        // The joint's own transform is frame 0's.
        const tl = findAttr(el.attrs.toElement.value, el.attrs.toAttribute.value);
        lines[tl] = lines[tl].replace(/"[^"]*"$/, `"${fmt(values[0])}"`);
        changed++;
    }
    const ik = before.get('ik_hand_L').p;
    const w = ik.map(p => Math.min(1, Math.max(0, (3 - Math.hypot(p[0] - ref[0], p[1] - ref[1], p[2] - ref[2])) / 2)));
    console.log(file.padEnd(18), `${changed} channels`, `weight ${Math.min(...w).toFixed(2)}-${Math.max(...w).toFixed(2)}`);
    if (!dry) fs.writeFileSync(path, lines.join('\n'));
}
