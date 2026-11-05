import math,zlib
import numpy as np
import map_kit as K
PAINT='rt_tyre'
RESOURCE='materials/riverside/discarded-tyres-v1/rubber.vmat'
def configure(model):
 model.material_overrides[PAINT]=RESOURCE;model.tile_overrides[PAINT]=12
def tire(m,c,axis=(0,0,1),r=13.,w=8.,paint_name='rs_rubber'):
 assert abs(float(axis[2]))>.99, 'Loose tyres only'
 tyre(m,c[0],c[1],c[2]-w/2,r,w)
def _casing(model, e, n, z, radius=14.0, width=8.0):
    # Cross-section follows the outside casing up from the lower bead, then
    # returns along the inner liner. There is no face across either opening.
    profile = np.array(((.55, .12), (.60, .07), (.70, .04), (.83, .09),
        (.93, .18), (.972, .30), (.976, .42), (.976, .58), (.972, .70),
        (.93, .82), (.86, .89), (.84, .91), (.825, .905), (.80, .925),
        (.71, .96), (.675, .955), (.66, .965), (.64, .96), (.60, .93),
        (.55, .88), (.545, .84), (.55, .81), (.62, .80), (.72, .83),
        (.82, .79), (.90, .69), (.935, .57), (.935, .43), (.90, .31),
        (.82, .21), (.72, .17), (.62, .20), (.55, .19)), dtype=float)
    profile *= (radius, width)
    rng = np.random.default_rng(zlib.crc32(f"tyre:{e}:{n}".encode()))
    spin = rng.uniform(0, math.tau)
    # Small casing distortion and a shallow lean, partly sunk in the sediment.
    ellipse = np.array((1.0, .985))
    tilt = rng.uniform(-.018, .018, 2)

    def at(a, r, h):
        xy = np.array((math.cos(a), math.sin(a))) * ellipse * r
        return np.array((e + xy[0], n + xy[1], z + h + np.dot(xy, tilt)))

    sides, rows = 64, len(profile)
    angles = np.arange(sides) * math.tau / sides + spin
    points = np.array([at(a, r, h) for r, h in profile for a in angles])
    faces = []
    for j in range(rows):
        for k in range(sides):
            faces.append((j*sides+k, j*sides+(k+1)%sides,
                          ((j+1)%rows)*sides+(k+1)%sides, ((j+1)%rows)*sides+k))
    normals = np.zeros_like(points)
    for face in faces:
        a, b, c, d = points[list(face)]
        normal = np.cross(b-a, c-a) + np.cross(c-a, d-a)
        normals[list(face)] += normal
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    distances = np.concatenate(([0], np.cumsum(np.linalg.norm(np.diff(profile, axis=0), axis=1))))
    total = distances[-1] + np.linalg.norm(profile[-1]-profile[0])
    for index, face in enumerate(faces):
        j, k = divmod(index, sides)
        u0, u1 = k/sides * math.tau*radius/12, (k+1)/sides * math.tau*radius/12
        v0, v1 = distances[j]/12, (distances[j+1] if j+1 < rows else total)/12
        model.polygon(PAINT, points[list(face)], normals=normals[list(face)],
                      uv=((u0,v0), (u1,v0), (u1,v1), (u0,v1)))

    # Three staggered rows of low, chamfered tread blocks leave real grooves.
    # All inner faces sit inside the casing, so no closed bottom faces are added.
    blocks = 44
    for lane, (lo, hi) in enumerate(((.30, .425), (.46, .585), (.62, .73))):
        for block in range(blocks):
            centre = spin + (block + lane*.32)*math.tau/blocks
            half = math.pi/blocks*.84
            h0, h1 = width*lo, width*hi
            angular_chamfer, edge = .008, .10
            outline = np.array(((centre-half+angular_chamfer,h0), (centre+half-angular_chamfer,h0),
                (centre+half,h0+edge), (centre+half,h1-edge), (centre+half-angular_chamfer,h1),
                (centre-half+angular_chamfer,h1), (centre-half,h1-edge), (centre-half,h0+edge)))
            outline[:,0] += (outline[:,1]-(h0+h1)/2)*(.018 if lane%2 else -.018)
            middle = outline.mean(axis=0)
            inset = middle + (outline-middle)*(.91, .83)
            base = np.array([at(a, radius*.968, h) for a,h in outline])
            top_radius = radius - rng.uniform(.035, .10)
            top = np.array([at(a, top_radius, h) for a,h in inset])
            radial = np.column_stack((np.cos(inset[:,0]), np.sin(inset[:,0]), np.zeros(8)))
            model.polygon(PAINT, top, normals=radial,
                          uv=[(a*radius/12, h/12) for a,h in inset])
            for k in range(8):
                nxt = (k+1)%8
                model.polygon(PAINT, (base[k], base[nxt], top[nxt], top[k]),
                              uv=((0,0), (1,0), (1,.03), (0,.03)))
    configure(model)

def tyre(model,e,n,z,radius=14.,width=8.):
 _casing(model,e,n,z,radius,width)
 import riverdale_parts as P
 # Moulded sidewall lettering follows the curved rubber surface.
 for k in range(64):
  aa=[2*math.pi*i/64 for i in (k,k+1)]
  for r0,h0,r1,h1 in ((.70,.96,.71,.96),(.71,.96,.78,.936),(.78,.936,.80,.925),(.80,.925,.81,.916)):
   ps=[(e+math.cos(a)*r*radius,n+math.sin(a)*r*radius,z+h*width+.028) for a,r,h in ((aa[0],r0,h0),(aa[1],r0,h0),(aa[1],r1,h1),(aa[0],r1,h1))]
   uv=[(1-k/64,(r0-.70)/.11),(1-(k+1)/64,(r0-.70)/.11),(1-(k+1)/64,(r1-.70)/.11),(1-k/64,(r1-.70)/.11)]
   P.card(model,'rt_sidewall',ps,(0,0,1),uv=uv)
 model.material_overrides['rt_sidewall']='materials/riverside/discarded-tyres-v1/sidewall.vmat'
 model.tile_overrides['rt_sidewall']=12
