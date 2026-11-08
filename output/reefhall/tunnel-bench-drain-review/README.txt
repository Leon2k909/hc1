Reef Hall Tunnel Bench 1 drain clearance review, 2026-11-06.
Moved world X +32 inches, from -1500,560,-40 to -1468,560,-40. Rotation and height unchanged.
Object: 7a12407d-7562-5a77-9404-0f812510eac3.
Room ModelCollider now uses models/maps/reefhall/reefhall_tunnel_bench_drain_clearance.vmdl, a copy with only its three bench collision boxes translated X +32.
Original room model retained. New variant compiled successfully. Scene saved through native editor; saved position and collision model verified.
Tools/reefhall_map.py changes only the e<0 tunnel bench plan north coordinate from -1500 to -1468.
Before and after are native direct window captures at camera -1350,700,25; angles 7,-125,0; FOV80.
Revert by restoring bench position -1500,560,-40, room ModelCollider models/maps/reefhall/reefhall_tunnel.vmdl and generator placement -1500.
Pending user visual review.
