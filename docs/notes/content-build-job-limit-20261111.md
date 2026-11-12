# s&box 26.11.10 content build breaks after a few thousand compiles (2026-11-11)

## Symptom
After the s&box update of 2026-11-10 23:52 (editor version 26.11.10, Steam build 26576630), opening hc1 took forever
or never finished. The editor's new startup content build (`EditorContentBuild`, records in `.sbox/build/records`)
must finish before the editor opens. In hc1 it never did, so nothing was recorded and every launch started over.

Log signs (`logs/sbox-dev*.log`):
- thousands of `FixupResourceName: Illegal full path passed in ("c:/sbox-projects/hc1/forked-shooter-main/assets/...")`
- `Error opening shader "shaders/complex.shader" from mod "citizen"` (also `"content"`, `"xxx"`, or a library's mod)
- OBJ/FBX loads from `...\sbox\addons\citizen\assets\<a project path>`
- no `Content verarp.razedtest: N compiles ...` summary line, ever; `.sbox/build/records` stays empty

## Cause
An engine bug: after roughly 3,000-5,500 build jobs in one process, the native resource compiler stops mapping
project paths to the project's mod and every later compile fails. It's per process, not per project: a fresh test
project with 4,500 generated materials hit it at material 932 in the editor (after 4,500 describe jobs) and at
about 3,000 compiles in one `contentworker`. hc1 has ~8,500 sources, so the startup build's describe pass alone runs
past the limit and nothing ever publishes. Not caused by hc1 content: sounds, libraries, cloud packages, project code,
shaders, the org name and old compiled models were each ruled out in a test project.

Facepunch's PR 12342 (hotload `PackageAssemblyResolver`) is unrelated. Staging was not tried; nothing in
`engine/Sandbox.ContentBuild` changed upstream after 2026-11-09.

## Workaround: `Tools/contentbuild`
Builds a project's content with the engine's own `Sandbox.ContentBuild.dll` and `contentworker.exe`, a chunk of
folders at a time (800 sources by default) with fresh workers per chunk, so no worker reaches the limit. It writes
the same records the editor's startup build reads, so the editor then opens with almost nothing to compile.

```
dotnet build -c Release Tools/contentbuild
Tools/contentbuild/bin/Release/net10.0/contentbuild.exe C:\sbox-projects\hc1\forked-shooter-main
```

- Close the editor first (it holds `.sbox/build/lock`; the runner gives up after 15 s).
- `--only <folder under Assets>` builds one folder; `--max-sources N` changes the chunk size.
- Failure logs go to `.sbox/build/contentbuild-logs/chunk-NNNN.log`.
- Workers get no project assemblies, so project-only resource types (e.g. `.gnsmth`) are left to the editor.
- Proven on the test project: 4,500/4,500 built, then the editor's startup build recompiled none of them.
- hc1, 2026-11-11: 13 chunks in ~15 min (about 8,300 adopted, 139 compiled, 34 failed), 7,911 records. The editor
  then opened in ~2 min: `Content verarp.razedtest: 3 compiles, 23 failed, 962 adopted`, `Bootstrap Init Done`,
  no wrong-mod errors.
- The remaining failures are old broken sources, not this bug: the SWB attachment `.vmdl`s point at `.smd` files the
  engine can't load (their old `_c` still loads), plus a few camo/material sources. Logs in `contentbuild-logs/`.

Run it again whenever a big batch of assets changes, or after the next engine update, until Facepunch fixes it.
