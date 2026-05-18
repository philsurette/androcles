# Sample Production with Embedded Staging

[[layout id=main-stage units=ft]]
stage type=proscenium width=36 depth=24 audience=south
grid standard=9

level deck z=0
level bridge polygon=(-10,18, 10,18, 10,22, -10,22) z=8
stair stair_l from=(-12,14,0) to=(-10,18,8) steps=10

anchor door_l kind=exit at=(-18,20,0)
anchor door_r kind=exit at=(18,20,0)
anchor vom_dr kind=entrance at=(18,3,0)
anchor trap_c kind=trap at=(0,12,0) size=(4,4)

set table kind=furniture at=C size=(5,3) fixed=true
set throne kind=furniture at=UC size=(4,4) fixed=true

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

[[blocking beat=b3 scene=1.2 line=HAM-121]]
HAM @ DL face=CLA
CLA @ UC
HAM move DL -> C dur=2.5 curve=arc
HAM face CLA
cue LX.12 at=HAM.arrive(C)
[[/blocking]]

CLAUDIUS
A brother's murder—

[[blocking beat=b4 scene=1.2 line=CLA-122]]
HAM gesture point target=CLA hand=R
HAM move C -> table dur=1.5
HAM pickup sword from=table
CLA stand dur=1.0
cue Q.17 at=CLA.stand
[[/blocking]]
