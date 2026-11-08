"""Companion olive-grove print with the existing gallery frame dimensions."""
import veridant_gallery_art as A
def build_into(m,c=(0,0),z0=0):
    A.build_into(m,c,z0)
    m.material_overrides['vr_gallery_art']='materials/veridant/gallery-art-olive-v1/olive.vmat'
