"""Place the original Veridant lanterns beside circulation rather than in it.

Only named placements change; fixture geometry, height and lighting stay the
same. These offsets are shared by regeneration and the scoped installed-map fix.
All coordinates are east, north, height in inches.
"""
MOVES = {
    'Garden lantern 0': {
        'old': (-600., 260., 128.), 'new': (-686., 260., 128.),
        'model': 'veridant_dress', 'height': 96.,
        'reason': 'Move the post from the open south terrace route to the sea-side balustrade.',
    },
    'Garden lantern 1': {
        'old': (-320., 600., 128.), 'new': (-686., 680., 128.),
        'model': 'veridant_dress', 'height': 96.,
        'reason': 'Move out of the cross-terrace route, beyond the promenade-stair opening and beside the balustrade.',
    },
    'North terrace lantern 0': {
        'old': (-20., 300., 128.), 'new': (-164., 240., 128.),
        'model': 'veridant_buildings', 'height': 96.,
        'reason': 'Move to the south-west balustrade corner, clear of the reception stairwell and central terrace.',
    },
    'North terrace lantern 1': {
        'old': (130., 650., 128.), 'new': (-92., 724., 128.),
        'model': 'veridant_buildings', 'height': 96.,
        'reason': 'Free the bar approach and group the post beside the pine planter instead.',
    },
    'North terrace lantern 2': {
        'old': (300., 520., 128.), 'new': (240., 580., 128.),
        'model': 'veridant_buildings', 'height': 96.,
        'reason': 'Clear the grand-stair centreline and keep the post to the side of its upper landing.',
    },
    'East terrace lantern 2': {
        'old': (820., 500., 192.), 'new': (410., 566., 192.),
        'model': 'veridant_buildings', 'height': 96.,
        'reason': 'Move from the open terrace to the western glass-rail edge, below the stair approach.',
    },
    'East terrace lantern near': {
        'old': (930., -150., 192.), 'new': (798., -150., 192.),
        'model': 'veridant_buildings', 'height': 96.,
        'reason': 'Move the isolated post beside the western terrace railing, clearing the open floor.',
    },
    'Promenade lamp 7': {
        'old': (-1690., 1020., 0.), 'new': (-1690., 950., 0.),
        'model': 'veridant_dress', 'height': 140.,
        'reason': 'The old base was inside the north boundary wall at N=1000..1024; move it back onto paving.',
    },
}


def placed_base(name, base):
    move = MOVES.get(name)
    if move is None:
        return base
    current = tuple(float(p) for p in base)
    if current not in (move['old'], move['new']):
        raise ValueError(f'Review changed lantern layout: {name}: {current}')
    return move['new']
