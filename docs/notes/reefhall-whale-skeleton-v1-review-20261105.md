## Reef Hall suspended whale skeleton — review (2026-11-05)

- Authored museum-inspired skeleton at plan(-2300,0), z475, nominal length640. Curved ribs, vertebral processes,
  compact neck, separate skull/jaws and flipper bones, tapering tail. Stylized game sculpture, not scientific reconstruction.
- Reuses original `rh_bone` material and all60 original steel suspension faces. No new textures, external mesh
  assets, lights or collision. Remove4,520 original bone triangles, add47,920 and preserve38,738 other lobby faces
  exactly. Full physics/scene/hull hashes unchanged; approved planters and other surrounding improvements retained.
- Candidate only. Public map/generator unchanged pending acceptance. On acceptance, narrow-splice bone faces and
  replace only the bone-generation part of `reefhall_map.whale`; preserve the exact original cable recipe.
- Source, checks, reference provenance, matched actual native before/after and atrium placement captures:
  `Sources/ReefHall/whale-skeleton-v1/`, local `review/`. Three models compile/load. Isolated capture scenes are
  destroyed without scene/play control. No map rebuild, envmap bake or FPS benchmark.
