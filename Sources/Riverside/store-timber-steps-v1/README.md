# Lucky Stop timber entrance steps - review candidate

Substantial close-range rebuild of the shop entrance's three plain wooden blocks. Six separate chamfered tread boards, four
sawtooth-cut stringers with diagonal lower edges, rear support beam/feet, galvanized angle brackets and cross-head screws.
Original 90-inch width, 30-inch run and tread tops 6.5/13/19.5 inches retained. Root engine 490,-235,0, yaw0. No new collision,
lights or gameplay components. All shared textures/materials unchanged: unlettered wood crops from approved Riverside crate
atlas, Lowtide galvanized steel and existing dark paint. No external images or image generation.

Audited existing approved/pending assets and active model chats. The approved concrete T2 steps are unsuitable for this wooden
shop porch; roof/window/bin work from other chats is excluded. Model models/props/riverside/store_timber_steps_v1/steps.vmdl.
build.py creates three LODs and a private background, matching exactly 36 original step triangles against the active store input.
prepare_review.py reuses the known native import and disposable-scene render workflow. review.py import compiles three resources;
verify.py checks imported/protected hashes, winding, degenerate triangles and no added physics; review.py context creates separate
before/after scenes under matching map light/exposure. compose.py arranges matching standing-height views.

LODs: 5,132 / 4,364 / 236 triangles, thresholds 20/45. Three reused materials, no new bitmap assets.

Work/receipts: output/riverside/store-timber-steps-v1/. Review only. Wait for user approval before integration. Preserve original
collision wedge, porch, store, other installed upgrades and all lights. Later installation must remove only the 36 original
triangles and save one native renderer, with a narrow generator hook. Never install the private whole-store background.

Final validation: three resources compile; all LODs have zero inverted or degenerate triangles. Separate native before/after
scenes preserve the active Riverdale editor tab and play state, report no error models, and use identical entrance cameras,
lighting and exposure. Comparison was inspected; all protected public store/scene hashes still match. A first longer capture
did not return a final receipt and was replaced by the verified single-view captures in context-capture.json.
