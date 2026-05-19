// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# 1-0 ACT I

## 1.2-0 SCENE 1.2

1.2-1 @description: A room in the castle.
/*: stage type=proscenium
/*: grid standard=9
/*: actor HM name=Hamlet
/*: actor CD name=Claudius
/*: actor OP name=Ophelia
/*: setup act1
/*: level balcony at=UC size=(18,4) z=8
/*: anchor door_l = UL
/*: anchor door_r = UR
/*: anchor deck_l at=CL
/*: anchor balcony_l at=(-8,20,8)
/*: stair stair_l from=deck_l to=balcony_l
/*: piece table kind=table at=C size=(5,3)
/*: setup act2
/*: anchor door_l = CL
/*: anchor door_r = CR
/*: piece throne kind=chair at=UC size=(4,4)
/*: piece bench kind=bench at=DR size=(5,2)
/*: scene 1.2 set=act1
/HM: @ DL face=CD
/CD: @ UC
/OP: offstage via=door_l
/*: sword @ table

1.2-2 HM: I will watch from below.

## 1.3-0 SCENE 1.3

1.3-1 @description: The balcony is revealed.
/*: scene 1.3 set=act1
/HM: @ balcony_l face=CD
/CD: @ DC
/OP: @ deck_l face=HM
/*: sword @ table
/*: flower @ balcony_l

/HM: move balcony_l -> UC face=OP
/OP: move deck_l -> C face=HM

1.3-2 HM: I will speak with her.
/CD: move DC -> DR
/*: sword remove
/*: flower remove

1.3-3 CD: I will go.

## 2.1-0 SCENE 2.1

2.1-1 @description: Another room in the castle.
/*: scene 2.1 set=act2
/CD: @ throne
/HM: @ DL face=CD
/OP: offstage via=door_l
