"""Smooth hollow carved-stone bowl replacing the forecourt's faceted cap."""
from riverdale_parts import lathe
def build_into(m,c=(0,0)):
    profile=[(0,14),(9.5,14),(10,14.5),(10,17),(9.5,18),(8.2,20),(7.7,24),(7.7,40),(8.2,43),(10,45),(14,46),(20,47.5),(26,50),(30,53),(32.4,56),(33,57),(33,58),(32.6,58.5),(31.4,58.5),(31,58),(30.5,56.8),(28.5,54.5),(25,52.5),(20,50.8),(14,49.8),(7,49.3),(0,49.2)]
    lathe(m,c,profile,'vr_stone',128)
