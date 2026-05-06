"""Claudémon game data — creatures, moves, maps, items."""

# Effectiveness: CHART[atk_type][def_type] = multiplier
CHART = {
    'Neural': {'Logic': 2.0, 'Spark': 0.5, 'Neural': 0.5},
    'Logic':  {'Data': 2.0, 'Neural': 0.5, 'Logic': 0.5},
    'Data':   {'Spark': 2.0, 'Logic': 0.5, 'Data': 0.5},
    'Spark':  {'Neural': 2.0, 'Flow': 2.0, 'Data': 0.5, 'Spark': 0.5},
    'Flow':   {'Spark': 0.5, 'Flow': 0.5},
    'Void':   {'Normal': 0.0, 'Void': 0.5},
    'Normal': {},
}

def effectiveness(atk_type: str, def_type: str) -> float:
    return CHART.get(atk_type, {}).get(def_type, 1.0)

MOVES = {
    # Normal
    'Tackle':      {'type':'Normal','power':40,'pp':35,'acc':95,'cat':'physical','desc':'A basic tackle.'},
    'Growl':       {'type':'Normal','power':0, 'pp':40,'acc':100,'cat':'status','stat':('def',-1),'desc':'Lowers foe defense.'},
    'Quick Hit':   {'type':'Normal','power':40,'pp':30,'acc':100,'cat':'physical','priority':1,'desc':'Always goes first.'},
    # Neural
    'Prompt':      {'type':'Neural','power':45,'pp':25,'acc':100,'cat':'special','desc':'A neural prompt burst.'},
    'Deep Think':  {'type':'Neural','power':70,'pp':15,'acc':90, 'cat':'special','desc':'Focused neural strike.'},
    'Overfit':     {'type':'Neural','power':90,'pp':10,'acc':85, 'cat':'special','desc':'Powerful but risky.'},
    'Insight':     {'type':'Neural','power':0, 'pp':20,'acc':100,'cat':'status','stat':('spatk',1),'desc':'Raises Sp.Atk.'},
    # Data
    'Data Pulse':  {'type':'Data','power':50,'pp':25,'acc':100,'cat':'special','desc':'Sends a data burst.'},
    'Byte Slam':   {'type':'Data','power':65,'pp':20,'acc':95, 'cat':'physical','desc':'Slams with raw data.'},
    'Corrupt':     {'type':'Data','power':80,'pp':10,'acc':90, 'cat':'special','desc':'Corrupts target data.'},
    'Compile':     {'type':'Data','power':0, 'pp':20,'acc':100,'cat':'status','stat':('atk',1),'desc':'Raises Attack.'},
    'Defrag':      {'type':'Data','power':0, 'pp':20,'acc':100,'cat':'status','stat':('def',1),'desc':'Raises Defense.'},
    # Logic
    'Reason':      {'type':'Logic','power':45,'pp':25,'acc':100,'cat':'special','desc':'A logical strike.'},
    'Deduce':      {'type':'Logic','power':65,'pp':20,'acc':95, 'cat':'special','desc':'Deduced weak point.'},
    'Paradox':     {'type':'Logic','power':80,'pp':10,'acc':85, 'cat':'special','desc':'Creates a paradox.'},
    'Analyze':     {'type':'Logic','power':0, 'pp':20,'acc':100,'cat':'status','stat':('def',-1),'target':'foe','desc':'Lowers foe defense.'},
    # Spark
    'Zap':         {'type':'Spark','power':40,'pp':30,'acc':100,'cat':'special','desc':'A spark of electricity.'},
    'Lightning':   {'type':'Spark','power':65,'pp':15,'acc':95, 'cat':'special','desc':'A lightning strike.'},
    'Overcharge':  {'type':'Spark','power':90,'pp':10,'acc':80, 'cat':'special','desc':'Massive spark overload.'},
    # Flow
    'Stream':      {'type':'Flow','power':40,'pp':25,'acc':100,'cat':'special','desc':'A flowing stream.'},
    'Current':     {'type':'Flow','power':65,'pp':15,'acc':95, 'cat':'special','desc':'A powerful current.'},
    # Void
    'Null':        {'type':'Void','power':55,'pp':20,'acc':95, 'cat':'special','desc':'Void energy strike.'},
    'Erase':       {'type':'Void','power':85,'pp':10,'acc':85, 'cat':'special','desc':'Erases the target.'},
    'Void Pulse':  {'type':'Void','power':100,'pp':5,'acc':80,'cat':'special','desc':'Ultimate void attack.'},
}

# art: list of strings for battle display (5-6 lines, ~12 chars wide)
# learnset: {level: move_name}
# base_exp: EXP given to winner when defeated at lv5

CLAUDEMON = {
    'Promptling': {
        'type1':'Neural','type2':None,
        'hp':45,'atk':35,'def':30,'spatk':55,'spdef':45,'spd':50,
        'catch_rate':45,
        'base_exp':65,
        'evolves_at':16,'evolves_into':'Prompter',
        'art':[
            "   ·◉·   ",
            "  (^‿^)  ",
            "  /|█|\\  ",
            "  / | \\  ",
            "    ═    ",
        ],
        'learnset':{1:'Tackle',1:'Growl',5:'Prompt',9:'Insight',13:'Deep Think',18:'Overfit'},
        'desc':'Sparks neural prompts from its glowing antenna.',
        'starter':True,
    },
    'Prompter': {
        'type1':'Neural','type2':None,
        'hp':70,'atk':55,'def':50,'spatk':80,'spdef':65,'spd':70,
        'catch_rate':45,'base_exp':145,'evolves_at':32,'evolves_into':'Prompticus',
        'art':[
            "  ◈·◉·◈  ",
            " (^‿‿^)  ",
            " /|█C█|\\ ",
            " / |─| \\ ",
            "   ═══   ",
        ],
        'learnset':{1:'Prompt',16:'Deep Think',22:'Insight',28:'Overfit'},
        'desc':'A seasoned prompter with twin antennas.',
    },
    'Prompticus': {
        'type1':'Neural','type2':'Logic',
        'hp':95,'atk':75,'def':70,'spatk':110,'spdef':90,'spd':95,
        'catch_rate':45,'base_exp':240,'evolves_at':None,'evolves_into':None,
        'art':[
            "◈══◉══◈ ",
            "(^◉‿◉^) ",
            "/█C█C█\\ ",
            "│ ═══ │ ",
            "╘═════╛ ",
        ],
        'learnset':{1:'Prompt',32:'Overfit',36:'Paradox',40:'Void Pulse'},
        'desc':'Master of prompts. Its thoughts are reality.',
    },

    'Dataling': {
        'type1':'Data','type2':None,
        'hp':50,'atk':55,'def':45,'spatk':40,'spdef':40,'spd':40,
        'catch_rate':45,'base_exp':65,'evolves_at':16,'evolves_into':'Databyte',
        'art':[
            "  ┌───┐  ",
            "  │◦ ◦│  ",
            "  ├───┤  ",
            "  │0 1│  ",
            "  └───┘  ",
        ],
        'learnset':{1:'Tackle',1:'Growl',5:'Data Pulse',9:'Compile',13:'Byte Slam',18:'Defrag'},
        'desc':'Stores data in its crystalline body. Very sturdy.',
        'starter':True,
    },
    'Databyte': {
        'type1':'Data','type2':None,
        'hp':75,'atk':80,'def':65,'spatk':60,'spdef':60,'spd':55,
        'catch_rate':45,'base_exp':145,'evolves_at':32,'evolves_into':'Dataforce',
        'art':[
            " ╔═════╗ ",
            " ║◦ DB◦║ ",
            " ╠══╦══╣ ",
            " ║01║10║ ",
            " ╚══╩══╝ ",
        ],
        'learnset':{1:'Data Pulse',16:'Byte Slam',22:'Defrag',28:'Corrupt'},
        'desc':'Its body now holds terabytes of compressed power.',
    },
    'Dataforce': {
        'type1':'Data','type2':'Logic',
        'hp':100,'atk':110,'def':90,'spatk':80,'spdef':80,'spd':65,
        'catch_rate':45,'base_exp':240,'evolves_at':None,'evolves_into':None,
        'art':[
            "╔═══════╗",
            "║◉ DB  ◉║",
            "╠═══╦═══╣",
            "║010║101║",
            "╚═══╩═══╝",
        ],
        'learnset':{1:'Byte Slam',32:'Corrupt',36:'Analyze',40:'Void Pulse'},
        'desc':'A fortress of data. Nearly impenetrable defense.',
    },

    'Logixlet': {
        'type1':'Logic','type2':None,
        'hp':40,'atk':40,'def':35,'spatk':50,'spdef':55,'spd':60,
        'catch_rate':45,'base_exp':65,'evolves_at':16,'evolves_into':'Logicon',
        'art':[
            "  ┌───┐  ",
            "  │◎ ◎│  ",
            "  └─∧─┘  ",
            "   /│\\   ",
            "  /_│_\\  ",
        ],
        'learnset':{1:'Tackle',1:'Growl',5:'Reason',9:'Analyze',13:'Deduce',18:'Insight'},
        'desc':'Thinks in pure logic. Its movements follow strict rules.',
        'starter':True,
    },
    'Logicon': {
        'type1':'Logic','type2':None,
        'hp':65,'atk':60,'def':55,'spatk':75,'spdef':80,'spd':80,
        'catch_rate':45,'base_exp':145,'evolves_at':32,'evolves_into':'Logixend',
        'art':[
            " ┌──────┐ ",
            " │◎  ◎ │ ",
            " │  L  │ ",
            " └──∧──┘ ",
            "  /│ │\\  ",
        ],
        'learnset':{1:'Reason',16:'Deduce',22:'Analyze',28:'Paradox'},
        'desc':'Logic made manifest. Calculates every move in advance.',
    },
    'Logixend': {
        'type1':'Logic','type2':'Neural',
        'hp':90,'atk':85,'def':80,'spatk':105,'spdef':110,'spd':100,
        'catch_rate':45,'base_exp':240,'evolves_at':None,'evolves_into':None,
        'art':[
            "╔════════╗",
            "║◎  L  ◎║",
            "║   ∞   ║",
            "╚═══∧═══╝",
            "   /│ │\\  ",
        ],
        'learnset':{1:'Deduce',32:'Paradox',36:'Overfit',40:'Void Pulse'},
        'desc':'The ultimate reasoning machine. Its logic is absolute.',
    },

    'Bitling': {
        'type1':'Spark','type2':None,
        'hp':35,'atk':40,'def':30,'spatk':35,'spdef':30,'spd':55,
        'catch_rate':200,'base_exp':40,'evolves_at':18,'evolves_into':'Byteon',
        'art':[
            " ⚡[0|1]⚡ ",
            "  ╔═══╗  ",
            "  ║ · ║  ",
            "  ╚═══╝  ",
        ],
        'learnset':{1:'Tackle',4:'Zap',8:'Quick Hit',12:'Lightning'},
        'desc':'Constantly flickers between 0 and 1.',
    },
    'Byteon': {
        'type1':'Spark','type2':'Data',
        'hp':60,'atk':65,'def':50,'spatk':60,'spdef':50,'spd':80,
        'catch_rate':100,'base_exp':120,'evolves_at':None,'evolves_into':None,
        'art':[
            "⚡[01|10]⚡",
            " ╔══════╗ ",
            " ║  ⚡  ║ ",
            " ║ 0110 ║ ",
            " ╚══════╝ ",
        ],
        'learnset':{1:'Zap',18:'Lightning',24:'Overcharge',30:'Data Pulse'},
        'desc':'A fully evolved Bitling crackling with stored voltage.',
    },

    'Pixlet': {
        'type1':'Data','type2':None,
        'hp':38,'atk':32,'def':38,'spatk':42,'spdef':42,'spd':42,
        'catch_rate':180,'base_exp':42,'evolves_at':20,'evolves_into':'Pixmon',
        'art':[
            " ░░░░░░  ",
            " ░◉ ◉░  ",
            " ░ ▾ ░  ",
            " ░░░░░  ",
        ],
        'learnset':{1:'Tackle',5:'Data Pulse',10:'Defrag'},
        'desc':'Its body is made of pure pixel data.',
    },
    'Pixmon': {
        'type1':'Data','type2':'Spark',
        'hp':65,'atk':55,'def':60,'spatk':70,'spdef':65,'spd':60,
        'catch_rate':90,'base_exp':125,'evolves_at':None,'evolves_into':None,
        'art':[
            "░░░░░░░░",
            "░◉⚡⚡◉░",
            "░░ ▾ ░░",
            "░░░░░░░░",
        ],
        'learnset':{1:'Data Pulse',20:'Byte Slam',26:'Corrupt'},
        'desc':'Its pixels glow with stored electrical charge.',
    },

    'Loopmon': {
        'type1':'Logic','type2':None,
        'hp':42,'atk':38,'def':42,'spatk':48,'spdef':45,'spd':45,
        'catch_rate':160,'base_exp':50,'evolves_at':22,'evolves_into':'Loopcore',
        'art':[
            "  ↻   ↺  ",
            " ╭─────╮ ",
            " │  ∞  │ ",
            " ╰─────╯ ",
            "  ↺   ↻  ",
        ],
        'learnset':{1:'Tackle',6:'Reason',12:'Deduce'},
        'desc':'Thinks in infinite loops. Hard to reason with.',
    },
    'Loopcore': {
        'type1':'Logic','type2':'Data',
        'hp':70,'atk':60,'def':65,'spatk':75,'spdef':70,'spd':65,
        'catch_rate':80,'base_exp':135,'evolves_at':None,'evolves_into':None,
        'art':[
            " ↻═════↺ ",
            "╔═══════╗",
            "║  ∞∞∞  ║",
            "╚═══════╝",
            " ↺═════↻ ",
        ],
        'learnset':{1:'Reason',22:'Deduce',28:'Paradox',34:'Analyze'},
        'desc':'Its loops process logic faster than light.',
    },

    'Flowlet': {
        'type1':'Flow','type2':None,
        'hp':40,'atk':35,'def':38,'spatk':48,'spdef':50,'spd':48,
        'catch_rate':170,'base_exp':45,'evolves_at':20,'evolves_into':'Flowmon',
        'art':[
            " ≋≋≋≋≋≋  ",
            "≋(· ·)≋  ",
            " ≋≋∿≋≋   ",
            "  ≋≋≋    ",
        ],
        'learnset':{1:'Tackle',5:'Stream',10:'Current'},
        'desc':'Flows around obstacles. Never stops moving.',
    },
    'Flowmon': {
        'type1':'Flow','type2':'Neural',
        'hp':70,'atk':60,'def':60,'spatk':75,'spdef':75,'spd':70,
        'catch_rate':85,'base_exp':130,'evolves_at':None,'evolves_into':None,
        'art':[
            "≋≋≋≋≋≋≋≋ ",
            "≋(◉ ◉)≋  ",
            "≋≋ ∿∿ ≋≋ ",
            " ≋≋≋≋≋≋  ",
        ],
        'learnset':{1:'Stream',20:'Current',26:'Insight'},
        'desc':'Its adaptive flow can mimic any attack style.',
    },

    'Voidlet': {
        'type1':'Void','type2':None,
        'hp':38,'atk':45,'def':35,'spatk':55,'spdef':40,'spd':50,
        'catch_rate':120,'base_exp':60,'evolves_at':28,'evolves_into':'Voidmon',
        'art':[
            " ▓▓▓▓▓▓  ",
            " ▓○   ▓  ",
            " ▓  ○ ▓  ",
            " ▓▓▓▓▓▓  ",
        ],
        'learnset':{1:'Tackle',8:'Null',15:'Erase'},
        'desc':'Exists in the space between data. Unsettling.',
    },
    'Voidmon': {
        'type1':'Void','type2':None,
        'hp':70,'atk':80,'def':60,'spatk':95,'spdef':70,'spd':75,
        'catch_rate':60,'base_exp':165,'evolves_at':None,'evolves_into':None,
        'art':[
            "▓▓▓▓▓▓▓▓ ",
            "▓○     ▓ ",
            "▓  ▪▪  ▓ ",
            "▓     ○▓ ",
            "▓▓▓▓▓▓▓▓ ",
        ],
        'learnset':{1:'Null',28:'Erase',35:'Void Pulse'},
        'desc':'A void given form. Its gaze deletes what it sees.',
    },

    'Compilex': {
        'type1':'Data','type2':'Logic',
        'hp':60,'atk':55,'def':70,'spatk':65,'spdef':70,'spd':40,
        'catch_rate':80,'base_exp':120,'evolves_at':None,'evolves_into':None,
        'art':[
            " ╔╗╔╗╔╗  ",
            " ╠╣╠╣╠╣  ",
            " ╠╩╩╩╩╣  ",
            " ║ CPX ║  ",
            " ╚═════╝  ",
        ],
        'learnset':{1:'Data Pulse',1:'Reason',12:'Compile',20:'Defrag',28:'Corrupt'},
        'desc':'A compiler given life. Translates pain into power.',
    },

    'Quantix': {
        'type1':'Spark','type2':'Logic',
        'hp':55,'atk':65,'def':55,'spatk':80,'spdef':65,'spd':85,
        'catch_rate':50,'base_exp':150,'evolves_at':None,'evolves_into':None,
        'art':[
            "  ⚡◈⚡   ",
            " /◈ ◈\\  ",
            "⚡  Q  ⚡ ",
            " \\◈ ◈/  ",
            "  ⚡◈⚡   ",
        ],
        'learnset':{1:'Zap',1:'Reason',15:'Lightning',22:'Paradox',30:'Overcharge'},
        'desc':'Exists in superposition. Its attacks are unpredictable.',
    },

    'Claudor': {
        'type1':'Neural','type2':'Logic',
        'hp':95,'atk':80,'def':75,'spatk':115,'spdef':95,'spd':90,
        'catch_rate':15,'base_exp':300,'evolves_at':None,'evolves_into':None,
        'art':[
            "★/═══════\\★",
            " │◎  C  ◎│ ",
            " │ ☆★★☆ │ ",
            " │  ═══  │ ",
            "★\\═══════/★",
        ],
        'learnset':{1:'Prompt',1:'Reason',1:'Data Pulse',20:'Deep Think',30:'Paradox',40:'Void Pulse'},
        'desc':'The legendary Claudor. Said to know all prompts.',
        'legendary':True,
    },
}

ITEMS = {
    'Claudéball': {'type':'ball','catch_mult':1.0,'price':200,'desc':'Standard catch ball.'},
    'GreatBall':  {'type':'ball','catch_mult':1.5,'price':600,'desc':'Higher catch rate.'},
    'UltraBall':  {'type':'ball','catch_mult':2.0,'price':1200,'desc':'Very high catch rate.'},
    'Potion':     {'type':'heal','power':20,'price':300,'desc':'Restores 20 HP.'},
    'Hi-Potion':  {'type':'heal','power':50,'price':700,'desc':'Restores 50 HP.'},
    'Max Potion': {'type':'heal','power':999,'price':2500,'desc':'Fully restores HP.'},
    'Revive':     {'type':'revive','power':0,'price':1500,'desc':'Revives a fainted Claudémon.'},
}

SHOPS = {
    'startup': ['Claudéball','Potion'],
    'route1':  ['Claudéball','GreatBall','Potion','Hi-Potion'],
    'forest':  ['GreatBall','UltraBall','Hi-Potion','Max Potion','Revive'],
}

ENCOUNTERS = {
    'route1':  [('Bitling',2,8),('Pixlet',3,8),('Loopmon',5,10)],
    'forest':  [('Flowlet',8,14),('Voidlet',10,16),('Compilex',12,18)],
    'peaks':   [('Loopcore',18,24),('Byteon',18,24),('Quantix',20,26),('Voidmon',22,28)],
    'core':    [('Claudor',40,40)],
}

# . path  # wall/tree  G grass  ~ water  T town  N NPC marker  P player start
WORLD_MAPS = {
    'startup': {
        'name': 'Startup Town',
        'encounter_table': None,
        'connections': {'right': ('route1', 2, 9)},
        'map': [
            "▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲",
            "▲··················▲···▲",
            "▲·T······T·····T···▲···▲",
            "▲··················▲···▲",
            "▲·T······T·········▲···▲",
            "▲·············≈≈≈≈≈····▲",
            "▲·····N········≈≈≈·····▲",
            "▲··················════▲",
            "▲·····P············════ ",
            "▲··················════▲",
            "▲······················▲",
            "▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲",
        ],
        'npcs': {
            (5, 6): {'name': 'Prof. Claude', 'role': 'professor'},
        },
        'exits': {(23, 8): 'route1'},
    },
    'route1': {
        'name': 'Route 1',
        'encounter_table': 'route1',
        'connections': {'left': ('startup', 1, 8), 'right': ('forest', 2, 9)},
        'map': [
            "▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲",
            " ···GGGG···············▲",
            " ···GGGG··▲▲···········▲",
            " ···GGGG··▲▲···GGGG····▲",
            " ·········▲▲···GGGG····▲",
            " ·········▲▲···GGGG····▲",
            " ·········▲▲···········▲",
            " ···GGGG···············▲",
            " ···GGGG···············  ",
            " ···GGGG···············▲",
            " ······················▲",
            "▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲",
        ],
        'npcs': {},
        'exits': {(0, 8): 'startup', (23, 8): 'forest'},
    },
    'forest': {
        'name': 'Neural Forest',
        'encounter_table': 'forest',
        'connections': {'left': ('route1', 23, 8), 'right': ('peaks', 2, 9)},
        'map': [
            "▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲",
            " GGGG··········GGGG····▲",
            " GGGG··▲▲·▲▲···GGGG····▲",
            " ·····▲▲···▲▲··········▲",
            " ·····▲▲···▲▲··GGGG····▲",
            " ·····▲▲···▲▲··GGGG····▲",
            " ·····▲▲···▲▲··········▲",
            " GGGG·▲▲···▲▲··········▲",
            " GGGG··········GGGG····  ",
            " GGGG··········GGGG····▲",
            " ······················▲",
            "▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲",
        ],
        'npcs': {},
        'exits': {(0, 8): 'route1', (23, 8): 'peaks'},
    },
    'peaks': {
        'name': 'Binary Peaks',
        'encounter_table': 'peaks',
        'connections': {'left': ('forest', 23, 8)},
        'map': [
            "▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲",
            " ·······▲▲▲············▲",
            " ·GGGGG·▲▲▲············▲",
            " ·GGGGG·▲▲▲············▲",
            " ·GGGGG················▲",
            " ··········▲▲▲·········▲",
            " ··········▲▲▲·········▲",
            " ··········▲▲▲·········▲",
            " ··············GGGGG···  ",
            " ··············GGGGG···▲",
            " ······················▲",
            "▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲",
        ],
        'npcs': {},
        'exits': {(0, 8): 'forest'},
    },
}

PLAYER_START = ('startup', 5, 8)
