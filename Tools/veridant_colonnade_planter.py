"""Limestone planter fitted clear of glazing and the adjacent pier."""
from riverdale_parts import box,bevel_box,v,card,UP
def build_into(m,c=(0,0),z0=0):
    e0,e1=c[0]-29,c[0]+13;n0,n1=c[1]-31,c[1]+16
    for a,b,d,e in [(e0,e1,n0,n0+2),(e0,e1,n1-2,n1),(e0,e0+2,n0+2,n1-2),(e1-2,e1,n0+2,n1-2)]:
        box(m,a,b,d,e,z0,z0+23,'vr_stone')
    axes=(v(1,0,0),v(0,1,0),v(0,0,1))
    for a,b,d,e in [(e0-1,e1+1,n0-1,n0+2),(e0-1,e1+1,n1-2,n1+1),(e0-1,e0+2,n0+2,n1-2),(e1-2,e1+1,n0+2,n1-2)]:
        bevel_box(m,((a+b)/2,(d+e)/2,z0+23.5),axes,(b-a,e-d,1),'vr_stone_dark',bevel=.12)
    card(m,'vr_soil',[v(e0+2,n0+2,z0+22),v(e1-2,n0+2,z0+22),v(e1-2,n1-2,z0+22),v(e0+2,n1-2,z0+22)],UP)
