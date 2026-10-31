# Pull the old cloud grenade out of its compiled files, only to render a fair "before".
# Nothing here is shipped. Writes an OBJ per mesh, its names and its textures to the work folder.
#   python read_old.py
import json
import os
import struct
import sys

import numpy as np
from PIL import Image

CLOUD = "C:/sbox-projects/hc1/forked-shooter-main/.sbox/cloud/models/weapons/sbox_grenade_flash"
OUT = "C:/sbox-projects/hc1/forked-shooter-main/output/asset-improvement-20261030/flashbang/old"


def blocks(d):
    _, _, _, boff, count = struct.unpack_from("<IHHII", d, 0)
    base = 8 + boff
    out = []
    for i in range(count):
        o = base + i * 12
        rel, size = struct.unpack_from("<II", d, o + 4)
        out.append((d[o:o + 4].decode("latin1"), o + 4 + rel, size))
    return out


def lz4_block(src, size):
    out = bytearray()
    i = 0
    while i < len(src) and len(out) < size:
        token = src[i]
        i += 1
        n = token >> 4
        if n == 15:
            while True:
                b = src[i]
                i += 1
                n += b
                if b != 255:
                    break
        out += src[i:i + n]
        i += n
        if i >= len(src) or len(out) >= size:
            break
        off = src[i] | src[i + 1] << 8
        i += 2
        m = token & 15
        if m == 15:
            while True:
                b = src[i]
                i += 1
                m += b
                if b != 255:
                    break
        m += 4
        for _ in range(m):
            out.append(out[-off])
    return bytes(out)


def kv3_strings(d, start, size):
    # Only the names matter here, so unpack the block and list the printable runs.
    raw = d[start:start + size]
    method, = struct.unpack_from("<I", raw, 20)
    usize, csize = struct.unpack_from("<II", raw, 48)
    body = raw[64:64 + csize]
    data = lz4_block(body, usize) if method == 1 else body
    found, run = [], bytearray()
    for c in data:
        if 32 <= c < 127:
            run.append(c)
        else:
            if len(run) >= 3:
                found.append(run.decode())
            run = bytearray()
    return method, usize, found


def unzig8(v):
    return (-(v & 1) ^ (v >> 1)) & 255


def decode_group(data, p, out, at, bits):
    if bits == 0:
        return p
    if bits == 3:
        out[at:at + 16] = data[p:p + 16]
        return p + 16
    width, shifts = (2, (6, 4, 2, 0)) if bits == 1 else (4, (4, 0))
    sentinel = (1 << width) - 1
    head = 4 if bits == 1 else 8
    q = p + head
    k = at
    for i in range(head):
        byte = data[p + i]
        for s in shifts:
            e = (byte >> s) & sentinel
            if e == sentinel:
                out[k] = data[q]
                q += 1
            else:
                out[k] = e
            k += 1
    return q


def decode_vertices(data, count, size):
    assert data[0] >> 4 == 0xA, hex(data[0])
    assert data[0] & 15 == 0, "only meshopt vertex codec 0 is read here"
    tail = max(size, 32)
    last = bytearray(data[len(data) - size:])
    limit = min(8192 // size, 256) & ~15
    result = bytearray(count * size)
    p = 1
    for start in range(0, count, limit):
        n = min(limit, count - start)
        aligned = (n + 15) & ~15
        for k in range(size):
            buf = bytearray(aligned)
            head = (aligned // 16 + 3) // 4
            header = data[p:p + head]
            p += head
            for g in range(aligned // 16):
                bits = (header[g // 4] >> ((g % 4) * 2)) & 3
                p = decode_group(data, p, buf, g * 16, bits)
            prev = last[k]
            at = start * size + k
            for i in range(n):
                prev = (unzig8(buf[i]) + prev) & 255
                result[at] = prev
                at += size
            last[k] = prev
    return bytes(result)


def vbyte(data, p):
    v, s = 0, 0
    while True:
        b = data[p]
        p += 1
        v |= (b & 127) << s
        s += 7
        if b < 128:
            return v, p


def decode_indices(data, count, index_size):
    assert data[0] >> 4 == 0xE, hex(data[0])
    version = data[0] & 15
    tris = count // 3
    code = 1
    p = 1 + tris
    table = len(data) - 16
    edges = [(-1, -1)] * 16
    verts = [-1] * 16
    eo = vo = 0
    nxt = last = 0
    fecmax = 13 if version >= 1 else 15
    out = []

    def pe(a, b):
        nonlocal eo
        edges[eo] = (a, b)
        eo = (eo + 1) & 15

    def pv(v, cond=True):
        nonlocal vo
        verts[vo] = v
        if cond:
            vo = (vo + 1) & 15

    def free(p, last):
        v, p = vbyte(data, p)
        return (last + ((v >> 1) ^ -(v & 1))) & 0xFFFFFFFF, p

    for _ in range(tris):
        c0 = data[code]
        code += 1
        if c0 < 0xF0:
            a, b = edges[(eo - 1 - (c0 >> 4)) & 15]
            fec = c0 & 15
            if fec < fecmax:
                cf = verts[(vo - 1 - fec) & 15]
                c = nxt if fec == 0 else cf
                z = fec == 0
                if z:
                    nxt += 1
                pv(c, z)
            else:
                if fec != 15:
                    c = last + (fec - (fec ^ 3))
                else:
                    c, p = free(p, last)
                last = c
                pv(c)
            out += (a, b, c)
            pe(c, b)
            pe(a, c)
        elif c0 < 0xFE:
            aux = data[table + (c0 & 15)]
            feb, fec = aux >> 4, aux & 15
            a = nxt
            nxt += 1
            b = nxt if feb == 0 else verts[(vo - feb) & 15]
            if feb == 0:
                nxt += 1
            c = nxt if fec == 0 else verts[(vo - fec) & 15]
            if fec == 0:
                nxt += 1
            out += (a, b, c)
            pv(a)
            pv(b, feb == 0)
            pv(c, fec == 0)
            pe(b, a)
            pe(c, b)
            pe(a, c)
        else:
            aux = data[p]
            p += 1
            fea = 0 if c0 == 0xFE else 15
            feb, fec = aux >> 4, aux & 15
            if aux == 0:
                nxt = 0
            if fea == 0:
                a = nxt
                nxt += 1
            else:
                a = 0
            if feb == 0:
                b = nxt
                nxt += 1
            else:
                b = verts[(vo - feb) & 15]
            if fec == 0:
                c = nxt
                nxt += 1
            else:
                c = verts[(vo - fec) & 15]
            if fea == 15:
                a, p = free(p, last)
                last = a
            if feb == 15:
                b, p = free(p, last)
                last = b
            if fec == 15:
                c, p = free(p, last)
                last = c
            out += (a, b, c)
            pv(a)
            pv(b, feb == 0 or feb == 15)
            pv(c, fec == 0 or fec == 15)
            pe(b, a)
            pe(c, b)
            pe(a, c)
    return np.array(out, dtype=np.int64).reshape(-1, 3)


def read_buffer_header(d, o):
    count, size = struct.unpack_from("<II", d, o)
    a_rel, a_count = struct.unpack_from("<II", d, o + 8)
    b_rel, b_size = struct.unpack_from("<II", d, o + 16)
    attrs = []
    a = o + 8 + a_rel
    for i in range(a_count):
        q = a + i * 56
        name = d[q:q + 32].split(b"\0")[0].decode()
        sem, fmt, off, slot, slot_type, step = struct.unpack_from("<iiIiii", d, q + 32)
        attrs.append((name, sem, fmt, off))
    return count, size & 0xFFFFFF, attrs, o + 16 + b_rel, b_size


def read_mbuf(d, start, size):
    vb_rel, vb_n, ib_rel, ib_n = struct.unpack_from("<IIII", d, start)
    vbs = []
    for i in range(vb_n):
        o = start + vb_rel + i * 24
        count, esize, attrs, data_at, data_size = read_buffer_header(d, o)
        raw = d[data_at:data_at + data_size]
        if data_size != count * esize:
            raw = decode_vertices(raw, count, esize)
        vbs.append((count, esize, attrs, raw))
    ibs = []
    for i in range(ib_n):
        o = start + 8 + ib_rel + i * 24
        count, esize, attrs, data_at, data_size = read_buffer_header(d, o)
        raw = d[data_at:data_at + data_size]
        if data_size != count * esize:
            ibs.append(decode_indices(raw, count, esize))
        else:
            ibs.append(np.frombuffer(raw, dtype=np.uint16 if esize == 2 else np.uint32).reshape(-1, 3))
    return vbs, ibs


def decompress_normals(raw, count, stride, off):
    dtype = np.dtype({"names": ["v"], "formats": [("u1", (4,))], "offsets": [off], "itemsize": stride})
    b = np.frombuffer(raw, dtype=dtype, count=count)["v"].astype(np.float64)
    x, y = b[:, 0] - 128.0, b[:, 1] - 128.0
    zb, tb = (x < 0) * 1.0, (y < 0) * 1.0
    zs, ts = 1 - 2 * zb, 1 - 2 * tb
    x, y = x * zs - zb - 64, y * ts - tb - 64
    xb, yb = (x < 0) * 1.0, (y < 0) * 1.0
    xs, ys = 1 - 2 * xb, 1 - 2 * yb
    x, y = (x * xs - xb) / 63.0, (y * ys - yb) / 63.0
    z = 1.0 - x - y
    n = np.stack((x * xs, y * ys, z * zs), 1)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)


FLOAT_OF = {6: (3, "f"), 16: (2, "f"), 34: (2, "e"), 10: (4, "e"), 2: (4, "f")}


def column(raw, count, stride, off, fmt):
    n, kind = FLOAT_OF[fmt]
    dtype = np.dtype({"names": ["v"], "formats": [(("<" + kind), (n,))], "offsets": [off], "itemsize": stride})
    return np.frombuffer(raw, dtype=dtype, count=count)["v"].astype(np.float64)


def write_textures():
    for f in sorted(os.listdir(CLOUD)):
        if not f.endswith(".vtex_c"):
            continue
        d = open(os.path.join(CLOUD, f), "rb").read()
        bl = dict((b[0], b) for b in blocks(d))
        _, s, size = bl["DATA"]
        version, flags = struct.unpack_from("<HH", d, s)
        w, h, depth = struct.unpack_from("<HHH", d, s + 20)
        fmt, mips = d[s + 26], d[s + 27]
        print(f, "size", w, h, "format", fmt, "mips", mips, "flags", flags, "file", len(d), "data at", s + size)
        extra_off, extra_n = struct.unpack_from("<II", d, s + 32)
        extras = []
        q = s + 32
        for i in range(extra_n):
            t = q + extra_off + i * 12
            kind, rel, sz = struct.unpack_from("<III", d, t)
            extras.append((kind, t + 4 + rel, sz))
        print("  extras", extras)
        name = f.split("_png")[0]
        yield name, d, s + size, w, h, fmt, mips, extras


DDS_FORMATS = {1: ("DXT1", 8), 2: ("DXT5", 16)}


def dds(w, h, fourcc=None, dxgi=None, payload=b""):
    flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x80000
    pitch = len(payload)
    head = struct.pack("<I6I", 124, flags, h, w, pitch, 0, 1) + b"\0" * 44
    pf = struct.pack("<II4s5I", 32, 4, (fourcc or "DX10").encode(), 0, 0, 0, 0, 0)
    head += pf + struct.pack("<5I", 0x1000, 0, 0, 0, 0)
    ext = struct.pack("<5I", dxgi, 3, 0, 1, 0) if dxgi else b""
    return b"DDS " + head + ext + payload


def mip_bytes(w, h, block):
    return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * block


def save_textures():
    import io
    formats = {1: ("DXT1", None, 8), 2: ("DXT5", None, 16), 20: (None, 98, 16), 21: (None, 83, 16), 27: (None, 80, 8)}
    for name, d, at, w, h, fmt, mips, extras in write_textures():
        fourcc, dxgi, blockbytes = formats[fmt]
        comp = next((e for e in extras if e[0] == 4), None)
        sizes = None
        if comp:
            # Per-mip sizes: a flag, an offset relative to itself, a count, indexed by mip level.
            flag, rel, count = struct.unpack_from("<III", d, comp[1])
            sizes = struct.unpack_from("<%dI" % count, d, comp[1] + 4 + rel)
        p = at
        mip0 = None
        for m in range(mips - 1, -1, -1):
            raw = mip_bytes(max(1, w >> m), max(1, h >> m), blockbytes)
            size = sizes[m] if sizes else raw
            if m == 0:
                chunk = d[p:p + size]
                mip0 = chunk if size == raw else lz4_block(chunk, raw)
            p += size
        im = Image.open(io.BytesIO(dds(w, h, fourcc=fourcc, dxgi=dxgi, payload=mip0)))
        im.load()
        im.save(os.path.join(OUT, name + ".png"))
        arr = np.asarray(im.convert("RGBA"), dtype=np.float64)
        print("  saved", name, im.size, im.mode, "mean", arr.reshape(-1, 4).mean(0).round(1), "std", arr.reshape(-1, 4).std(0).round(1))


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(CLOUD, "w_flash_grenade.vmdl_c")
    d = open(path, "rb").read()
    bl = blocks(d)
    info = {"meshes": []}
    for tag in ("DATA", "CTRL", "PHYS"):
        for name, s, size in bl:
            if name == tag:
                method, usize, strings = kv3_strings(d, s, size)
                info[tag] = strings
                print(tag, "method", method, "unpacked", usize)
                print("  ", strings[:80])
    mesh = 0
    for i, (name, s, size) in enumerate(bl):
        if name != "MBUF":
            continue
        _, ms, msize = bl[i - 1]
        _, _, strings = kv3_strings(d, ms, msize)
        vbs, ibs = read_mbuf(d, s, size)
        count, stride, attrs, raw = vbs[0]
        print("mesh", mesh, "verts", count, "stride", stride, "tris", sum(len(x) for x in ibs), attrs, strings[:14])
        by = {a[0]: a for a in attrs}
        pos = column(raw, count, stride, by["POSITION"][3], by["POSITION"][2])
        uv = column(raw, count, stride, by["TEXCOORD"][3], by["TEXCOORD"][2])
        tris = np.concatenate(ibs)
        nor = decompress_normals(raw, count, stride, by["NORMAL"][3])
        face = np.cross(pos[tris[:, 1]] - pos[tris[:, 0]], pos[tris[:, 2]] - pos[tris[:, 0]])
        agree = (face * nor[tris[:, 0]]).sum(1) > 0
        print("   normals agree with winding on %.1f%% of triangles" % (agree.mean() * 100))
        with open(os.path.join(OUT, "old_mesh_%d.obj" % mesh), "w") as f:
            f.write("o old_mesh_%d\n" % mesh)
            for p in pos:
                f.write("v %.5f %.5f %.5f\n" % tuple(p))
            for t in uv:
                f.write("vt %.5f %.5f\n" % (t[0], 1 - t[1]))
            for n in nor:
                f.write("vn %.5f %.5f %.5f\n" % tuple(n))
            for t in tris:
                a, b, c = t + 1
                f.write("f %d/%d/%d %d/%d/%d %d/%d/%d\n" % (a, a, a, b, b, b, c, c, c))
        info["meshes"].append({"mesh": mesh, "verts": int(count), "tris": int(len(tris)),
                               "lo": pos.min(0).tolist(), "hi": pos.max(0).tolist(), "strings": strings[:14]})
        print("   bounds", pos.min(0).round(3), pos.max(0).round(3))
        mesh += 1
    json.dump(info, open(os.path.join(OUT, "old_model.json"), "w"), indent=1)
    save_textures()


main()
