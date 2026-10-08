"""Railhead masonry: shared texture coordinates, clean joins and unwrapped arches."""
import math
from collections import defaultdict

import numpy as np
import map_kit as K

PAINTS = ('rw_dressed_red', 'rw_dressed', 'rw_sandstone')


def align_uvs(model):
    """Keep courses aligned across mesh boundaries, including the mirrored wings.

    map_kit normally gives each model a random texture offset. That is useful for
    separate buildings, but a station wall split into several models needs one
    continuous masonry pattern. Curved reveals keep their authored unwrap.
    """
    for paint in PAINTS:
        tile = model.tile_overrides.get(paint)
        if tile is None:
            continue
        for index, (points, normal) in enumerate(model.polygons.get(paint, ())):
            key = (paint, index)
            if key not in model.polygon_uvs:
                model.polygon_uvs[key] = [K.face_uv(K.to_world(p), K.to_world(normal), paint, tile=tile)
                                          for p in points]


def _subtract(lo, hi, other_lo, other_hi):
    a, b = np.maximum(lo, other_lo), np.minimum(hi, other_hi)
    if np.any(b - a < 1e-5):
        return [(lo, hi)]
    pieces = [(lo, (a[0], hi[1])), ((b[0], lo[1]), hi),
              ((a[0], lo[1]), (b[0], a[1])), ((a[0], b[1]), (b[0], hi[1]))]
    return [(np.asarray(p), np.asarray(q)) for p, q in pieces if np.all(np.asarray(q) - p > 1e-5)]


def clean_joins(models):
    """Remove coplanar render faces at sill, tower and wall joins; retain collision.

    Cut-stone trim takes precedence over the wall behind it. Only axis-aligned
    rectangular masonry faces are clipped; arches and other authored geometry
    are kept. No tiny depth offsets or stacked wall surfaces are required.
    """
    planes = defaultdict(list)
    replacements = {}
    for paint in PAINTS:
        for name, model in models.items():
            for index, (points, normal) in enumerate(model.polygons.get(paint, ())):
                p = np.asarray(points)
                axis = int(np.argmax(abs(normal)))
                other = [a for a in range(3) if a != axis]
                if len(p) != 4 or abs(normal[axis]) < .9999:
                    continue
                if np.ptp(p[:, axis]) > 1e-5:
                    continue
                if any(len(set(np.round(p[:, a], 5))) != 2 for a in other):
                    continue
                key = (axis, round(float(p[0, axis]), 5), int(np.sign(normal[axis])))
                lo, hi = p[:, other].min(0), p[:, other].max(0)
                pieces = [(lo, hi)]
                for used_lo, used_hi in planes[key]:
                    pieces = [part for a, b in pieces for part in _subtract(a, b, used_lo, used_hi)]
                    if not pieces:
                        break
                planes[key].extend(pieces)
                if len(pieces) == 1 and np.array_equal(pieces[0][0], lo) and np.array_equal(pieces[0][1], hi):
                    continue
                faces = []
                for a, b in pieces:
                    q = p.copy()
                    for j, ax in enumerate(other):
                        q[:, ax] = np.where(abs(p[:, ax] - lo[j]) < 1e-5, a[j], b[j])
                    uv = model.polygon_uvs.get((paint, index))
                    if uv is not None:
                        # Preserve a caller's explicit mapping when a rectangle is shortened.
                        frame = np.column_stack((p[:, other], np.ones(4)))
                        coefficients = np.linalg.lstsq(frame, np.asarray(uv), rcond=None)[0]
                        uv = (np.column_stack((q[:, other], np.ones(4))) @ coefficients).tolist()
                    faces.append((list(q), normal, uv))
                replacements[name, paint, index] = faces

    for name, model in models.items():
        for paint in PAINTS:
            original = model.polygons.get(paint, ())
            new, uvs, normals = [], {}, {}
            for index, (points, normal) in enumerate(original):
                parts = replacements.get((name, paint, index))
                if parts is None:
                    parts = [(points, normal, model.polygon_uvs.get((paint, index)))]
                for points, normal, uv in parts:
                    target = (paint, len(new))
                    if uv is not None:
                        uvs[target] = uv
                    smooth = model.polygon_normals.get((paint, index))
                    if smooth is not None and (name, paint, index) not in replacements:
                        normals[target] = smooth
                    new.append((points, normal))
            if not original:
                continue
            model.polygons[paint] = new
            model.polygon_uvs = {key: value for key, value in model.polygon_uvs.items() if key[0] != paint} | uvs
            model.polygon_normals = {key: value for key, value in model.polygon_normals.items() if key[0] != paint} | normals
    return models


class Wall(K.Wall):
    def build(self, model, outside, inside, reveal, end=None, surface='default', sill_paint=None):
        start = len(model.polygons[reveal])
        super().build(model, outside, inside, reveal, end=end, surface=surface, sill_paint=sill_paint)
        # Continue the arch's unwrap down its jambs. Projecting each curved facet
        # independently otherwise changes texture phase and smears mortar seams.
        run_axis, depth_axis = (0, 1) if self.axis == 'e' else (1, 0)
        for opening in self.openings:
            if not opening.arched:
                continue
            for index in range(start, len(model.polygons[reveal])):
                points, _ = model.polygons[reveal][index]
                p = np.asarray(points)
                left = np.all(abs(p[:, run_axis] - opening.r0) < 1e-5)
                right = np.all(abs(p[:, run_axis] - opening.r1) < 1e-5)
                if not (left or right) or p[:, 2].min() > opening.spring:
                    continue
                model.polygon_uvs[reveal, index] = [
                    ((point[depth_axis] - self.across[0]) / 96.,
                     (point[2] if left else 2 * opening.spring + math.pi * opening.radius - point[2]) / 96.)
                    for point in points]

    def _arch_head(self, model, opening, outside, inside, reveal, out_face, surface, steps=48):
        """A smooth visual opening, with stone mapped continuously along its curve."""
        start = len(model.polygons[reveal])
        hull_start = len(model.hulls)
        super()._arch_head(model, opening, outside, inside, reveal, out_face, surface, steps=steps)
        # Keep the existing gameplay hulls rather than multiplying collision faces.
        collision = K.Model()
        super()._arch_head(collision, opening, outside, inside, reveal, out_face, surface, steps=12)
        model.hulls[hull_start:] = collision.hulls
        centre = (opening.r0 + opening.r1) * .5
        d0, d1 = self.across
        for index in range(start, len(model.polygons[reveal])):
            points, normal = model.polygons[reveal][index]
            uv, smooth = [], []
            for point in points:
                r, depth, z = (point[0], point[1], point[2]) if self.axis == 'e' else (point[1], point[0], point[2])
                theta = math.atan2(z - opening.spring, r - centre)
                uv.append(((depth - d0) / 96., (opening.spring + opening.radius * (math.pi - theta)) / 96.))
                inward = np.array((centre - r, 0, opening.spring - z) if self.axis == 'e'
                                   else (0, centre - r, opening.spring - z), float)
                smooth.append(K.normalise(inward))
            model.polygon_uvs[reveal, index] = uv
            model.polygon_normals[reveal, index] = smooth
