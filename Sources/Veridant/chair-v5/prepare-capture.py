"""Prepare matched engine captures without touching the active map or camera."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/veridant/chair-v5'
stage=(OUT/'publish-stage.txt').read_text().strip()
manifest=json.loads((OUT/stage/'manifest.json').read_text())
(OUT/'capture-manifest.json').write_text(json.dumps({'placements':manifest['placements']},indent=2),encoding='utf-8')
(OUT/'capture-request.json').write_text(json.dumps({'phase':'before'}),encoding='utf-8')
script=(ROOT/'Sources/Veridant/chair-v4/capture.cs.txt').read_text()
script=script.replace('output/veridant/chair-v4','output/veridant/chair-v5')
script=script.replace('Stage="stage-v4"',f'Stage="{stage}"')
script=script.replace('material.GetTexture(name)?.MarkUsed(1024);',
    'material.GetTexture(name)?.MarkUsed(material.ResourcePath?.Contains("chair-v5")==true?2048:1024);')
script=script.replace('Forward:30f, Side:26f, Height:36f, Target:17f','Forward:32f, Side:30f, Height:39f, Target:20f')
script=script.replace('Forward:24f, Side:-30f, Height:33f, Target:18f','Forward:27f, Side:-34f, Height:37f, Target:20f')
script=script.replace('Forward:0f, Side:39f, Height:30f, Target:17f','Forward:0f, Side:45f, Height:33f, Target:20f')
script=script.replace('Forward:-31f, Side:23f, Height:34f, Target:18f','Forward:-35f, Side:27f, Height:38f, Target:20f')
script=script.replace('Forward:38f, Side:36f, Height:39f, Target:17f','Forward:42f, Side:40f, Height:43f, Target:20f')
(ROOT/'Sources/Veridant/chair-v5/capture.cs.txt').write_text(script,encoding='utf-8')
