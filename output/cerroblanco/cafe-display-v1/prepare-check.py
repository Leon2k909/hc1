from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'Sources/CerroBlanco/cafe-display-v1'
s=(R/'Sources/CerroBlanco/cafe-grinder-v1/verify.py').read_text().replace("PROP/'grinder.obj'","PROP/'display.obj'")
s=s.replace('all(-4<=p[0]<=4 and -0.001<=p[1]<=16.001 and -4.6<=p[2]<=3.8 for p in vs)','all(-682.3<=p[0]<=-627.7 and 41.99<=p[1]<=56.3 and 603.7<=p[2]<=627 for p in vs)')
s=s.replace('==128','==22').replace('==4880','==2112').replace('==67610','==72468').replace("'unrelated_faces_preserved':67610","'unrelated_faces_preserved':72468").replace(",'modelled_beans':24",'')
(o/'verify.py').write_text(s)
