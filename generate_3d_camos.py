import os
import json

camos_dir = 'Assets/gunsmith/Camos'

def process():
    files = [f for f in os.listdir(camos_dir) if f.endswith('.gnsmth') and not f.endswith('_seamless.gnsmth') and not f.endswith('_animated.gnsmth') and not f.endswith('_glowing.gnsmth')]
    
    count = 0
    for filename in files:
        filepath = os.path.join(camos_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"Error parsing {filename}: {e}")
                continue
                
        if data.get('Category') == 'Camoflague' and data.get('CamoTexture'):
            if 'CamoMaterial' in data:
                continue
                
            basename = filename.replace('.gnsmth', '')
            
            if "04834e09-0d45-4dd2-87bb-c498ef2dc4fea" in basename:
                continue

            texture_path = data.get('CamoTexture')
            
            vmat_content = f""""Layer0"
{{
	"shader"		"shaders/hc1_animated_camo.shader"
	"TextureColor"		"{texture_path}"
	"g_vTexCoordScrollSpeed"		"[0.000 0.000]"
}}
"""
            vmat_filename = f"{basename}_seamless.vmat"
            vmat_filepath = os.path.join(camos_dir, vmat_filename)
            with open(vmat_filepath, 'w', encoding='utf-8') as f:
                f.write(vmat_content)
                
            new_data = data.copy()
            new_data['Name'] = f"{data.get('Name', basename)} (3D)"
            new_data['Category'] = "Camoflague3D"
            new_data['CamoMaterial'] = f"gunsmith/Camos/{vmat_filename}"
            
            new_gnsmth_filename = f"{basename}_seamless.gnsmth"
            new_gnsmth_filepath = os.path.join(camos_dir, new_gnsmth_filename)
            with open(new_gnsmth_filepath, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, indent=4)
                
            count += 1
            
    print(f"Generated {count} 3D camos!")

if __name__ == '__main__':
    process()
