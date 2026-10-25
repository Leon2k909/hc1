"""Check authored wall closure and both caps, without engine movement claims."""
import argparse
from collections import deque
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def vector(value):
    return tuple(float(x) for x in value.split(','))


def bounds(obj, component):
    assert vector(obj.get('Rotation', '0,0,0,1')) == (0, 0, 0, 1)
    assert vector(obj.get('Scale', '1,1,1')) == (1, 1, 1)
    position = vector(obj['Position'])
    center = vector(component.get('Center', '0,0,0'))
    size = vector(component['Scale'])
    assert all(x > 0 for x in size)
    return ([position[i] + center[i] - size[i] / 2 for i in range(3)],
            [position[i] + center[i] + size[i] / 2 for i in range(3)])


def audit(scene, radius=0, height=64):
    boundary = next(x for x in scene['GameObjects'] if x.get('Name') == 'Closed Player Boundary')
    assert vector(boundary['Position']) == (0, 0, 0)
    assert vector(boundary['Rotation']) == (0, 0, 0, 1)
    assert vector(boundary['Scale']) == (1, 1, 1)
    walls, ceilings, floors = [], [], []
    for obj in boundary['Children']:
        assert obj['Enabled'] and 'playerclip' in obj['Tags'].split(',')
        for collider in obj['Components']:
            if collider['__type'] != 'Sandbox.BoxCollider':
                continue
            assert collider['__enabled'] and not collider['IsTrigger'] and collider['Static']
            low, high = bounds(obj, collider)
            item = dict(name=obj['Name'], id=obj['__guid'], low=low, high=high)
            if high[2] - low[2] > min(high[i] - low[i] for i in (0, 1)):
                walls.append(item)
            elif high[2] <= 0:
                floors.append(item)
            else:
                ceilings.append(item)
    assert walls and ceilings and floors, 'Missing walls, ceiling or lower caps'
    common_z = [max(x['low'][2] for x in walls), min(x['high'][2] for x in walls)]
    assert common_z[1] - common_z[0] > height
    expanded = [([w['low'][i] - radius for i in (0, 1)],
                 [w['high'][i] + radius for i in (0, 1)]) for w in walls]
    axes = []
    for axis in (0, 1):
        cuts = {edge[axis] for box in expanded for edge in box}
        # Split at cap edges too, so overlapping caps are checked as a union.
        cuts.update(edge[axis] for cap in floors+ceilings for edge in (cap['low'],cap['high']))
        axes.append(sorted(cuts | {min(cuts) - 64, max(cuts) + 64}))
    xs, ys = axes
    nx, ny = len(xs) - 1, len(ys) - 1
    centers = {(i, j): ((xs[i] + xs[i+1]) / 2, (ys[j] + ys[j+1]) / 2)
               for i in range(nx) for j in range(ny)}
    solid = {cell for cell, p in centers.items()
             if any(all(lo[k] < p[k] < hi[k] for k in (0, 1)) for lo, hi in expanded)}
    origin = next(cell for cell in centers if xs[cell[0]] <= 0 < xs[cell[0]+1]
                  and ys[cell[1]] <= 0 < ys[cell[1]+1])
    assert origin not in solid
    reached, queue = {origin}, deque([origin])
    while queue:
        i, j = queue.popleft()
        for cell in ((i-1, j), (i+1, j), (i, j-1), (i, j+1)):
            if cell in centers and cell not in solid and cell not in reached:
                reached.add(cell)
                queue.append(cell)
    escaped = [cell for cell in reached if cell[0] in (0, nx-1) or cell[1] in (0, ny-1)]
    uncovered = [cell for cell in reached if not any(
        all(cap['low'][k] <= (xs if k == 0 else ys)[cell[k]]
            and cap['high'][k] >= (xs if k == 0 else ys)[cell[k]+1] for k in (0, 1))
        and common_z[0] <= cap['low'][2] < common_z[1] for cap in ceilings)]
    uncovered_floor = [cell for cell in reached if not any(
        all(cap['low'][k] <= (xs if k == 0 else ys)[cell[k]]
            and cap['high'][k] >= (xs if k == 0 else ys)[cell[k]+1] for k in (0, 1))
        and cap['low'][2] < common_z[0] < cap['high'][2] < common_z[1] for cap in floors)]
    assert not escaped, f'Horizontal opening connects to exterior: {escaped}'
    assert not uncovered, f'Interior cells without an overlapping ceiling: {uncovered}'
    assert not uncovered_floor, f'Interior cells without an overlapping lower cap: {uncovered_floor}'
    area = next(x for x in scene['GameObjects'] if x.get('Name') == 'Military AO')
    zone = next(c for c in area['Components'] if c['__type'] == 'Zone')
    play_area = next(c for c in area['Components'] if c['__type'] == 'Facepunch.PlayArea')
    trigger = next(c for c in area['Components'] if c['__type'] == 'Sandbox.BoxCollider')
    assert play_area['Zone']['component_id'] == zone['__guid'] and trigger['IsTrigger']
    ao_low, ao_high = bounds(area, trigger)
    spawns = []
    for group_name in ('Team Spawns', 'Free For All Spawns'):
        group = next(x for x in scene['GameObjects'] if x.get('Name') == group_name)
        assert vector(group['Position']) == (0, 0, 0)
        assert vector(group['Rotation']) == (0, 0, 0, 1)
        assert vector(group['Scale']) == (1, 1, 1)
        for spawn in group['Children']:
            if not any(c['__type'] == 'TeamSpawnPoint' for c in spawn.get('Components', [])):
                continue
            p = vector(spawn['Position'])
            cell = next((cell for cell in reached
                         if xs[cell[0]] <= p[0] < xs[cell[0]+1]
                         and ys[cell[1]] <= p[1] < ys[cell[1]+1]), None)
            inside_ao = all(ao_low[k] + radius <= p[k] <= ao_high[k] - radius for k in (0, 1))
            inside_ao = inside_ao and ao_low[2] <= p[2] and p[2] + height <= ao_high[2]
            under_ceiling = any(all(cap['low'][k] <= p[k] <= cap['high'][k] for k in (0, 1))
                                and p[2] + height <= cap['low'][2] for cap in ceilings)
            above_floor = any(all(cap['low'][k] <= p[k] <= cap['high'][k] for k in (0, 1))
                              and p[2] >= cap['high'][2] for cap in floors)
            assert cell is not None and inside_ao and under_ceiling and above_floor, f'Spawn outside enclosed area: {spawn["Name"]}'
            spawns.append(dict(name=spawn['Name'], position=p, cell=cell, insideAo=inside_ao,
                               underCeiling=under_ceiling,aboveFloor=above_floor))
    assert spawns, 'No saved spawns inspected'
    return dict(radius=radius, controllerHeight=height, walls=walls, ceilings=ceilings,floors=floors,
                commonWallHeightRange=common_z, partitionCells=nx*ny,
                interiorCells=len(reached), exteriorConnections=escaped,
                uncoveredCeilingCells=uncovered,uncoveredFloorCells=uncovered_floor,savedSpawns=spawns,
                scope='Exact axis-aligned source partition: horizontal wall closure and overlapping upper/lower cap coverage. '
                      'Does not verify native collider import/filtering, controller motion, '
                      'unstuck behavior, network authority or exhaustive gameplay escapes.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scene', type=Path, default=ROOT/'Assets/scenes/maps/forestbase/forestbase.scene')
    parser.add_argument('--output', type=Path, default=ROOT/'output/forestbase/boundary-source-audit.json')
    args = parser.parse_args()
    source = json.loads(args.scene.read_text(encoding='utf-8-sig'))
    report = dict(source=str(args.scene), audits=[audit(source, r) for r in (0, 16)])
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps([dict(radius=x['radius'], walls=len(x['walls']), ceilings=len(x['ceilings']),floors=len(x['floors']),
                           savedSpawns=len(x['savedSpawns']),
                           interiorCells=x['interiorCells'], exteriorConnections=x['exteriorConnections'],
                           uncoveredCeilingCells=x['uncoveredCeilingCells'],uncoveredFloorCells=x['uncoveredFloorCells']) for x in report['audits']]))
