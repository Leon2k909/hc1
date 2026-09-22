"""Install rear-grip/magazine resources without rewriting existing attachment choices."""
import json,uuid,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def guid(key):return str(uuid.uuid5(uuid.NAMESPACE_URL,'razed/rear-mag/'+key))
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
def walk(go):
    yield go
    for child in go.get('Children',[]):yield from walk(child)
for weapon in ['m4a1','scarh']:
    for key,title,category,description,capacity,reload in [
        ('rubber_grip','Rubberized Grip',14,'Contoured rubber overmold',0,1),
        ('taped_grip','Taped Grip',14,'Olive cloth wrap',0,1),
        ('short_mag','20 Round Compact',15,'20 rounds · 10% faster reload',20,.90),
        ('extended_mag','40 Round Extended',15,'40 rounds · 15% slower reload',40,1.15)]:
        name=weapon+'_'+key;folder=ROOT/'Assets/gunsmith'/weapon/'rear_mag'
        bone=('magazine' if category==15 else 'weapon_root') if weapon=='m4a1' else ('Mag' if category==15 else 'Base')
        mount={'__type':'Facepunch.Gunsmith.GunsmithBoneAttachment','__guid':guid(name+'/mount'),'BoneName':bone,
            'HiddenBodygroup':'magazine' if category==15 else '',
            'ModelVariants':{'weapons/swb/scarh/w_scarh.vmdl':f'attachments/rear_mag/{name}_world/{name}_world.vmdl'} if weapon=='scarh' else {}}
        write(folder/(key+'.prefab'),{'RootObject':{'__guid':guid(name+'/root'),'Name':title,'Flags':0,'Enabled':True,'NetworkMode':1,
            'Position':'0,0,0','Rotation':'0,0,0,1','Scale':'1,1,1','Components':[
            {'__type':'Sandbox.ModelRenderer','__guid':guid(name+'/renderer'),'Model':f'attachments/rear_mag/{name}/{name}.vmdl','Tint':'1,1,1,1'},mount]},'ResourceVersion':2,'__version':2})
        write(folder/(key+'.gnsmth'),{'Name':title,'Category':category,'Description':description,'MagazineCapacity':capacity,'ReloadTimeMultiplier':reload,
            'MainPrefab':{'_type':'gameobject','prefab':f'gunsmith/{weapon}/rear_mag/{key}.prefab'},
            'EligibleEquipment':[f'weapons/{weapon}/{weapon}.equip'],'RequiredLevel':0,'ModifyBodygroups':False,'__references':[],'__version':0})
    for variant in ['vm','wm']:
        p=ROOT/f'Assets/Weapons/{weapon}/{variant}_{weapon}.prefab';data=json.loads(p.read_text(encoding='utf-8-sig'));root=data['RootObject']
        for category,position in [(14,'-3,0,3' if weapon=='m4a1' else '5,-3,-7'),(15,'2,0,2' if weapon=='m4a1' else '10,-3,-7')]:
            categoryname='RearGrip' if category==14 else 'Magazine'
            if any(c.get('__type')=='Facepunch.Gunsmith.GunsmithAttachmentPoint' and c.get('Category') in [category,categoryname] for go in walk(root) for c in go.get('Components',[])):continue
            root.setdefault('Children',[]).append({'__guid':guid(f'{weapon}/{variant}/{category}/point'),'Flags':0,'Name':categoryname+' Attachment Point','Position':position,'Rotation':'0,0,0,1','Scale':'1,1,1','Enabled':True,
                'Components':[{'__type':'Facepunch.Gunsmith.GunsmithAttachmentPoint','__guid':guid(f'{weapon}/{variant}/{category}/component'),'Category':category}]})
        write(p,data)

# Split the SCAR's authored magazine into a selectable bodygroup, retaining its existing skin weights.
def end_of(text,start):
    opener=text[start];closer={'{':'}','[':']'}[opener];level=0;quoted=False;escape=False
    for i in range(start,len(text)):
        ch=text[i]
        if escape:escape=False;continue
        if ch=='\\' and quoted:escape=True;continue
        if ch=='"':quoted=not quoted;continue
        if quoted:continue
        if ch==opener:level+=1
        if ch==closer:
            level-=1
            if level==0:return i+1
    raise ValueError('Unbalanced ModelDoc')
def node(text,classname,name=None):
    for match in re.finditer(r'_class\s*=\s*"'+classname+'"',text):
        start=text.rfind('{',0,match.start());end=end_of(text,start);block=text[start:end]
        if name is None or re.search(r'name\s*=\s*"'+name+'"',block):return start,end,block
    raise ValueError('Missing '+classname+'/'+str(name))
for variant in ['v_scarh','v_scarh_gunsmith','w_scarh']:
    p=ROOT/f'Assets/Weapons/swb/scarh/{variant}.vmdl';text=p.read_text()
    if re.search(r'name\s*=\s*"magazine"',text):continue
    a,b,original=node(text,'RenderMeshFile','scar')
    f=original.index('import_filter');fs=original.index('{',f);fe=end_of(original,fs)
    mag=original[:fs]+'{ exclude_by_default = true exception_list = [ "mag", ] }'+original[fe:]
    mag=re.sub(r'name\s*=\s*"scar"','name = "magazine"',mag,count=1)
    pos=original.index('[',original.index('exception_list',fs));pe=end_of(original,pos)
    edited=original[:pe-1]+' "mag", '+original[pe-1:]
    text=text[:a]+edited+',\n'+mag+text[b:]
    a,b,group=node(text,'BodyGroupList');cs=group.index('[',group.index('children'));ce=end_of(group,cs)
    addition='''
            { _class = "BodyGroup" name = "magazine" children = [
                { _class = "BodyGroupChoice" name = "standard_magazine" meshes = [ "magazine", ] },
                { _class = "BodyGroupChoice" name = "" meshes = [ "", ] },
            ] hidden_in_tools = false },
'''
    group=group[:ce-1]+addition+group[ce-1:];text=text[:a]+group+text[b:];p.write_text(text,encoding='utf-8')
    # The extra empty choice reserves bit 5; the auto-generated Body moves to bit 6.
for variant in ['vm','wm']:
    p=ROOT/f'Assets/Weapons/SCARH/{variant}_scarh.prefab';data=json.loads(p.read_text())
    for c in data['RootObject']['Components']:
        if c.get('__type')=='Sandbox.SkinnedModelRenderer':c['BodyGroups']=81
    write(p,data)
print('Installed two grips and two magazines per rifle, plus animated SCAR magazine bodygroup')
