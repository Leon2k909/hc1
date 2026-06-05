import json
import uuid

def convert_scene_to_prefab():
    with open('Assets/scenes/gunsmith.scene', 'r', encoding='utf-8') as f:
        scene_data = json.load(f)
        
    game_objects = scene_data.get('GameObjects', [])
    
    # Filter out Scene Information
    filtered_objects = [go for go in game_objects if go.get('Name') != 'Scene Information']
    
    # Create the root object for the prefab
    root_object = {
        "__guid": str(uuid.uuid4()),
        "__version": 2,
        "Flags": 0,
        "Name": "GunsmithStudio",
        "Position": "0,0,-10000",
        "Rotation": "0,0,0,1",
        "Scale": "1,1,1",
        "Tags": "",
        "Enabled": True,
        "NetworkMode": 1,
        "NetworkFlags": 0,
        "NetworkOrphaned": 0,
        "NetworkTransmit": False,
        "OwnerTransfer": 0,
        "Components": [],
        "Children": filtered_objects
    }
    
    prefab_data = {
        "RootObject": root_object,
        "ResourceVersion": 2,
        "__version": 2
    }
    
    with open('Assets/prefabs/gunsmith_studio.prefab', 'w', encoding='utf-8') as f:
        json.dump(prefab_data, f, indent=2)

if __name__ == '__main__':
    convert_scene_to_prefab()
