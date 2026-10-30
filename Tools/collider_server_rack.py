"""Human-scale, ventilated east stair server rack. Plan axes; inches."""
import math
import numpy as np
import map_kit as K
import boxyard_map as B
import collider_detail_geometry as D

POSITION = (430., -60.)
SIZE = (28., 44., 84.)
UP = np.array((0., 0., 1.))


def build(model, e=POSITION[0], n=POSITION[1], collision=True):
    """42U enclosure with removable panels and recessed, varied rack equipment."""
    def plate(x0,x1,y0,y1,z0,z1,paint='co_case',bevel=.12):
        D.plate(model,(e+x0,n+y0,z0),(e+x1,n+y1,z1),paint,bevel)

    if collision:
        model.box((e-14,n-22,0),(e+14,n+22,84),None,'metal')
    # Separate plinth, levelling feet, corner frame and folded cap.
    plate(-13.6,13.6,-21.6,21.6,1.4,4.5,'co_steel',.35)
    plate(-14,14,-22,22,82.7,84,'co_case',.32)
    plate(-12.9,12.9,-20.9,20.9,82.45,82.7,'co_rubber',.08)
    for x in (-12.4,12.4):
        for y in (-20.4,20.4):
            B.lathe(model,(e+x,n+y,0),UP,[(.95,0),(.95,.4),(.48,.65),(.48,1.4)],
                'co_rubber',sides=12,cap='co_rubber')
            plate(x-.7,x+.7,y-.7,y+.7,4.4,82.8,'co_case',.14)
    # Thin side skins split at a removable-panel seam; genuine vent openings.
    for side in (-1,1):
        x0,x1=sorted((side*13.8,side*13.35))
        plate(x0,x1,-19.5,19.5,7,35.5,'co_case',.10)
        plate(x0,x1,-19.5,19.5,49,81.5,'co_case',.10)
        for y0,y1 in ((-19.5,-13),(13,19.5)):
            plate(x0,x1,y0,y1,35.5,49,'co_case',.09)
        # Recessed louvres leave open air gaps instead of painted vent stripes.
        for z in np.arange(36.,49.,1.15):
            plate(x0-.025,x1+.025,-13,13,z,z+.30,'co_trim',.045)
        for z in (11,78):
            for y in (-16,16):
                D.bolt(model,(e+side*13.85,n+y,z),(side,0,0),.19,.07)
        # Small quarter-turn panel latch.
        plate(side*13.85-.09,side*13.85+.09,-1.1,1.1,53,55,'co_trim',.07)
    # Closed rear with inset replaceable fan cartridges.
    plate(-12.8,12.8,20.8,21.5,5,82,'co_steel',.18)
    for z in (23,47,70):
        D.plate(model,(e-5.9,n+21.45,z-5.9),(e+5.9,n+21.75,z+5.9),'co_case',.3)
        B.lathe(model,(e,n+21.8,z),(0,1,0),[(4.6,0),(4.9,.12),(4.9,.22),(4.6,.22),(4.6,0)],'co_trim',sides=24)
        for k in range(7):
            a=k*math.tau/7
            D.beam(model,(e,n+21.8,z),(e+math.cos(a)*4.4,n+21.8,z+math.sin(a)*4.4),(.6,.15),'co_steel',.035)
        B.lathe(model,(e,n+21.85,z),(0,1,0),[(1.1,0),(1.1,.18)],'co_trim',sides=16,cap='co_trim')
    # Door return, gasket and 19-inch equipment mounting uprights.
    for x0,x1 in ((-13.4,-11.3),(11.3,13.4)):
        plate(x0,x1,-22,-20.6,5,82.6,'co_case',.16)
    for z0,z1 in ((4.5,6.5),(80.8,82.7)):
        plate(-11.4,11.4,-22,-20.6,z0,z1,'co_case',.14)
    for x in (-10.8,10.8):
        plate(x-.32,x+.32,-20.3,-19.8,6.7,80.7,'co_trim',.07)
        # Three square cage-nut positions per rack unit.
        for z in np.arange(7.3,80,1.75):
            for dz in (0,.52,1.05):
                B.card(model,'co_rubber',[(e+x-.10,n-20.31,z+dz-.13),(e+x+.10,n-20.31,z+dz-.13),
                    (e+x+.10,n-20.31,z+dz+.13),(e+x-.10,n-20.31,z+dz+.13)],(0,-1,0))
    # Equipment sits behind the jambs. Different U sizes avoid identical repeats.
    units=((7,7),(14.5,3.5),(18.5,3.5),(22.5,7),(30,14),
           (44.5,3.5),(48.5,3.5),(52.5,7),(60,7),(68,7),(76,3.5))
    for index,(bottom,height) in enumerate(units):
        top=bottom+height-.25
        paint='co_trim' if index in (1,5,6) else 'co_case'
        plate(-9.7,9.7,-19.4,15,bottom,top,'co_steel',.12)
        # Dark inner cavity, then real slats in front of it.
        plate(-9.7,9.7,-19.75,-19.4,bottom+.18,top-.18,paint,.10)
        if height<10:
            for xx in np.arange(-6.4,5.8,.64):
                # A repeated opening separated by a small folded metal rib.
                plate(xx,xx+.11,-20.05,-19.8,bottom+.65,top-.65,'co_silver' if paint=='co_trim' else 'co_trim',.035)
            for x in (-8.5,8.5):
                plate(x-.2,x+.2,-20.2,-19.8,bottom+.7,top-.7,'co_silver',.07)
            # Two tiny status lamps, not the large repeated blue rectangles.
            plate(6.4,6.52,-20.12,-20.06,bottom+.68,bottom+.80,'co_beam',.015)
            if index in (0,3,7):
                plate(6.8,6.91,-20.12,-20.06,bottom+.68,bottom+.80,'co_amber',.015)
        else:
            # Removable blanking panel with a stamped label holder.
            plate(-4.5,4.5,-19.96,-19.77,bottom+height*.5-1,bottom+height*.5+1,'co_steel',.06)
            plate(-3,3,-20.01,-19.97,bottom+height*.5-.35,bottom+height*.5+.35,'co_silver',.02)
        for x in (-10.25,10.25):
            for z in (bottom+.5,top-.5):
                D.bolt(model,(e+x,n-20.45,z),(0,-1,0),.18,.09)
    # Flush access latch and three hinges belong to the enclosure, not each unit.
    plate(11.55,12.65,-22.27,-22.02,38,45,'co_steel',.16)
    D.beam(model,(e+12.1,n-22.35,39),(e+12.1,n-22.35,44),(.32,.30),'co_silver',.08)
    for z in (15,43,73):
        B.lathe(model,(e-12.9,n-22.1,z-1.4),UP,[(.25,0),(.25,2.8)],'co_trim',sides=12,cap='co_trim')

