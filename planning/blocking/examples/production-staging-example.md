# Sample Production with Embedded Staging

[[layout id=main-stage units=ft]]
stage type=proscenium width=36 depth=24 audience=south
grid standard=9

actor HM name=Hamlet
actor CD name=Claudius

setup act1
level deck z=0
level bridge at=UC size=(18,4) z=8

anchor door_l kind=exit at=(-18,20,0)
anchor door_r kind=exit at=(18,20,0)
anchor vom_dr kind=entrance at=(18,3,0)
anchor deck_l at=CL
anchor bridge_l at=(-10,20,8)
anchor trap_c kind=trap at=(0,12,0) size=(4,4)
stair stair_l from=deck_l to=bridge_l

piece table kind=table at=C size=(5,3) fixed=true
piece throne kind=chair at=UC size=(4,4) fixed=true

prop letter preset=table
prop sword preset=throne
[[/layout]]

[[cues]]
LX.12 type=lighting label="Special on Hamlet" focus=C fade=1.5
LX.13 type=lighting label="Widen to throne" focus=[C,UC] fade=2.0
SND.04 type=sound label="Distant bell"
Q.17 type=group cues=[LX.13,SND.04] label="Revelation cue"
[[/cues]]

## Act 1, Scene 2

HAMLET
Now might I do it pat—

[[blocking beat=b3 scene=1.2 set=act1 line=HM-121]]
HM @ DL face=CD
CD @ UC
HM move DL -> C dur=2.5 curve=arc
HM face CD
cue LX.12 at=HM.arrive(C)
[[/blocking]]

CLAUDIUS
A brother's murder—

[[blocking beat=b4 scene=1.2 set=act1 line=CD-122]]
HM gesture point target=CD hand=R
HM move C -> table dur=1.5
HM pickup sword from=table
CD stand dur=1.0
cue Q.17 at=CD.stand
[[/blocking]]
