"""Nested service-pipe bypasses around the south side-wall riser bundles.

The original perimeter lines crossed the risers at z=240/241.5. Stagger the
cross-wall legs as well, so the two bypass pipes cannot intersect each other.
"""
def perimeter_path(n_off, radius):
    e=1000-n_off;inner=e-60;z=236+radius
    start,end=(170,330) if n_off==10 else (150,350)
    return [(-e,0,z),(-e,start,z),(-inner,start,z),(-inner,end,z),(-e,end,z),
            (-e,2000-n_off,z),(e,2000-n_off,z),(e,end,z),(inner,end,z),
            (inner,start,z),(e,start,z),(e,0,z)]
