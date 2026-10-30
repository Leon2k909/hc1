"""Validate and summarize the final native Depot benchmark evidence."""
import hashlib
import json
from pathlib import Path
import statistics

ROOT=Path.cwd()
OUTPUT=ROOT/'output/depot-performance-20261027'
SOURCE=ROOT/'Sources/Depot/performance-v1'

def load(name):
    return json.loads((OUTPUT/(name+'.json')).read_text(encoding='utf-8'))

def main():
    results=load('stable-results')
    rows=[]
    for view in ['pump','stair','upper']:
        before=next(r for r in results if r['name']==view and r['variant']=='before')
        after=next(r for r in results if r['name']==view and r['variant']=='after')
        prefix='stable-'+view+'-'
        revision_before=load(prefix+'before-source-revision')
        revision_after=load(prefix+'after-source-revision')
        assert revision_before==revision_after, 'Source changed between paired runs: '+view
        assert before['valid'] and after['valid'], 'An invalid sample remains: '+view
        assert before['start']['GameAssembly']==after['start']['GameAssembly'], 'Assembly changed between paired runs'
        assert before['start']['CameraPosition']==after['start']['CameraPosition']
        assert before['start']['CameraAngles']==after['start']['CameraAngles']
        assert before['start']['FieldOfView']==after['start']['FieldOfView']
        assert before['start']['Bots']==after['start']['Bots']==9
        a,b=before['FrameMs']['Average'],after['FrameMs']['Average']
        details={variant:load(prefix+variant+'-details')['results'] for variant in ['before','after']}
        assert all(d[3]['Resolution']=='1920x1080' for d in details.values())
        assert all(d[1]['Cap']['FpsMaxInactive']==0 for d in details.values())
        assert all(d[1]['CapWait']['AvgMs']==0 for d in details.values())
        rows.append({
            'view':view,'frames_per_run':900,'mean_frame_ms_before':a,'mean_frame_ms_after':b,
            'average_fps_before':round(1000/a,2),'average_fps_after':round(1000/b,2),
            'frame_time_change_percent':round(100*(b/a-1),2),
            'p99_frame_ms_before':before['FrameMs']['P99'],'p99_frame_ms_after':after['FrameMs']['P99'],
            'hitches_over_33ms_before':before['FrameMs']['Over33Ms'],'hitches_over_33ms_after':after['FrameMs']['Over33Ms'],
            'snapshot_gpu_ms':{k:d[0]['Gpu'] for k,d in details.items()},
            'snapshot_main_thread_ms':{k:d[0]['MainThread'] for k,d in details.items()},
            'state_before':before['state'],'state_after':after['state'],
            'first_sample_utc':before['start']['Utc'],'last_sample_utc':after['end']['Utc']
        })
    original=load('Depot.before.scene')
    saved=json.loads((ROOT/'Assets/scenes/maps/Depot/Depot.scene').read_text(encoding='utf-8'))
    stripped=json.loads(json.dumps(saved))
    additions=[]
    for obj in stripped['GameObjects']:
        for comp in obj.get('Components',[])[:]:
            if comp['__type']=='Facepunch.DepotMapCleanup':
                additions.append(comp)
                obj['Components'].remove(comp)
    assert len(additions)==1 and stripped==original, 'An unrelated scene field changed'
    checks=load('final-preservation-checks')
    assert checks['CleanupCount']==69 and checks['FunctionalPickupPreserved']
    assert checks['ArchitectureSpawnsAndLightingPreserved'] and checks['FloorTracesPreserved']
    assert checks['ActiveMapErrorModels']==0
    compilation=load('final-compile-status')
    assert not compilation['IsBuilding'] and all(c['Errors']==0 for c in compilation['Compilers'])
    mean_before=statistics.mean(r['mean_frame_ms_before'] for r in rows)
    mean_after=statistics.mean(r['mean_frame_ms_after'] for r in rows)
    report={
        'date':'2026-10-27','project':'C:/sbox-projects/hc1/forked-shooter-main','map':'facepunch.depot',
        'scope':'Local editor TDM; three fixed player views, one invulnerable stationary player, nine active bots, score completion disabled only during testing.',
        'hardware':{'cpu':'Intel Core i7-11700K','gpu':'NVIDIA GeForce RTX 5070'},
        'settings':{'resolution':[1920,1080],'anti_aliasing':'Multisample4x','upscaling':'Off','background_fps_cap_during_measurement':0},
        'engine':'26.10.13c','game_assembly':results[0]['start']['GameAssembly'],
        'measured_frames':5400,'all_pairs_have_matching_source_revisions':True,
        'rows':rows,'aggregate':{'mean_frame_ms_before':mean_before,'mean_frame_ms_after':mean_after,
            'fps_from_mean_frame_time_before':round(1000/mean_before,2),'fps_from_mean_frame_time_after':round(1000/mean_after,2),
            'frame_time_change_percent':round(100*(mean_after/mean_before-1),2)},
        'change':{'component':'Code/World/DepotMapCleanup.cs','legacy_objects_disabled':69,
            'renderers_in_disabled_objects':183,'colliders_in_disabled_objects':69,'visible_error_models_before':16,'visible_error_models_after':0,
            'per_frame_cleanup_work_added':False,'all_original_scene_fields_and_identities_preserved':True},
        'preservation_checks':checks,'native_compile_errors':0,
        'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'Code/World/DepotMapCleanup.cs',ROOT/'Assets/scenes/maps/Depot/Depot.scene']},
        'limits':[
            'Editor measurements include editor overhead and other desktop applications; these are not standalone or remote-client results.',
            'One 900-frame before/after pair per view; active bot combat is stochastic, so small FPS differences are not a statistically established gain.',
            'GPU and main-thread category numbers are subsequent native two-second snapshots, separate from the 900-frame frame-time samples.',
            'Earlier class-picker, map-transition, shader-compilation, hotload and incomplete runs are excluded from these results.',
            'Depot remains excluded from IsMatchReadyMap; this pass does not certify its spawn layout or all game modes.'
        ]
    }
    for path in [SOURCE/'results.json',OUTPUT/'results.json']:
        path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'aggregate':report['aggregate'],'views':[{k:r[k] for k in ['view','average_fps_before','average_fps_after','p99_frame_ms_before','p99_frame_ms_after']} for r in rows]},indent=2))

if __name__=='__main__':
    main()
