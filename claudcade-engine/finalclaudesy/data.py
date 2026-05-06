"""Static game data: spells, items, equipment, enemies, maps."""

ITEMS = {
    'Potion':       {'type': 'heal',  'power': 100, 'target': 'one',  'price': 50,   'desc': 'Restores 100 HP'},
    'Hi-Potion':    {'type': 'heal',  'power': 250, 'target': 'one',  'price': 150,  'desc': 'Restores 250 HP'},
    'Mega-Potion':  {'type': 'heal',  'power': 500, 'target': 'all',  'price': 400,  'desc': 'Restores 500 HP all'},
    'Ether':        {'type': 'mp',    'power': 50,  'target': 'one',  'price': 100,  'desc': 'Restores 50 MP'},
    'Hi-Ether':     {'type': 'mp',    'power': 150, 'target': 'one',  'price': 300,  'desc': 'Restores 150 MP'},
    'Elixir':       {'type': 'elixir','power': 0,   'target': 'one',  'price': 1200, 'desc': 'Fully restores HP+MP'},
    'Phoenix Down': {'type': 'raise', 'power': 0,   'target': 'one',  'price': 200,  'desc': 'Revives fallen ally'},
    'Antidote':     {'type': 'esuna', 'power': 0,   'target': 'one',  'price': 30,   'desc': 'Cures Poison', 'cures': 'poison'},
    'Eye Drops':    {'type': 'esuna', 'power': 0,   'target': 'one',  'price': 30,   'desc': 'Cures Blind',  'cures': 'blind'},
    'Alarm Clock':  {'type': 'esuna', 'power': 0,   'target': 'one',  'price': 30,   'desc': 'Cures Sleep',  'cures': 'sleep'},
    'Echo Herb':    {'type': 'esuna', 'power': 0,   'target': 'one',  'price': 30,   'desc': 'Cures Silence','cures': 'silence'},
    'Grenade':      {'type': 'dmg',   'power': 200, 'target': 'all',  'price': 80,   'desc': 'Deals 200 dmg to all foes'},
}

EQUIPMENT = {
    # Knight weapons
    'Rusty Sword':    {'slot':'weapon','atk':10,'mag':0, 'def':0, 'spd':0, 'price':0,    'for':'knight','desc':'An old blade'},
    'Iron Sword':     {'slot':'weapon','atk':22,'mag':0, 'def':2, 'spd':0, 'price':200,  'for':'knight','desc':'Reliable iron'},
    'Steel Blade':    {'slot':'weapon','atk':38,'mag':0, 'def':4, 'spd':0, 'price':600,  'for':'knight','desc':'Forged steel'},
    'Crystal Edge':   {'slot':'weapon','atk':58,'mag':5, 'def':6, 'spd':0, 'price':1500, 'for':'knight','desc':'Crystal-infused'},
    'Void Slayer':    {'slot':'weapon','atk':80,'mag':10,'def':8, 'spd':2, 'price':3000, 'for':'knight','desc':'Forged in void'},
    # Mage weapons
    'Apprentice Rod': {'slot':'weapon','atk':4, 'mag':14,'def':0, 'spd':0, 'price':0,    'for':'mage',  'desc':'First rod'},
    'Mystic Rod':     {'slot':'weapon','atk':4, 'mag':28,'def':0, 'spd':0, 'price':250,  'for':'mage',  'desc':'Hums with power'},
    'Arcane Staff':   {'slot':'weapon','atk':4, 'mag':48,'def':2, 'spd':0, 'price':700,  'for':'mage',  'desc':'Amplifies magic'},
    'Void Scepter':   {'slot':'weapon','atk':4, 'mag':75,'def':3, 'spd':0, 'price':1800, 'for':'mage',  'desc':'Reality bends'},
    # Healer weapons
    'Wooden Staff':   {'slot':'weapon','atk':6, 'mag':10,'def':2, 'spd':0, 'price':0,    'for':'healer','desc':'Simple staff'},
    'Holy Staff':     {'slot':'weapon','atk':6, 'mag':24,'def':4, 'spd':0, 'price':250,  'for':'healer','desc':'Blessed wood'},
    'Divine Rod':     {'slot':'weapon','atk':6, 'mag':44,'def':6, 'spd':0, 'price':700,  'for':'healer','desc':'Radiates light'},
    'Seraph Rod':     {'slot':'weapon','atk':6, 'mag':68,'def':8, 'spd':0, 'price':1800, 'for':'healer','desc':'Angels weep'},
    # Knight armor
    'Cloth Shirt':    {'slot':'armor', 'atk':0, 'mag':0, 'def':5, 'spd':0, 'price':0,    'for':'all',   'desc':'Basic clothes'},
    'Leather Armor':  {'slot':'armor', 'atk':0, 'mag':0, 'def':14,'spd':0, 'price':150,  'for':'knight','desc':'Tanned hide'},
    'Chain Mail':     {'slot':'armor', 'atk':0, 'mag':0, 'def':26,'spd':0, 'price':500,  'for':'knight','desc':'Linked rings'},
    'Plate Armor':    {'slot':'armor', 'atk':0, 'mag':0, 'def':42,'spd':0, 'price':1200, 'for':'knight','desc':'Full plate'},
    'Void Plate':     {'slot':'armor', 'atk':0, 'mag':8, 'def':60,'spd':0, 'price':2500, 'for':'knight','desc':'Void-forged'},
    # Mage armor
    'Mage Robe':      {'slot':'armor', 'atk':0, 'mag':8, 'def':8, 'spd':0, 'price':150,  'for':'mage',  'desc':'Arcane cloth'},
    'Silk Robe':      {'slot':'armor', 'atk':0, 'mag':16,'def':14,'spd':0, 'price':500,  'for':'mage',  'desc':'Woven silk'},
    'Arcane Robe':    {'slot':'armor', 'atk':0, 'mag':28,'def':20,'spd':0, 'price':1200, 'for':'mage',  'desc':'Pure arcane'},
    'Void Robe':      {'slot':'armor', 'atk':0, 'mag':40,'def':28,'spd':0, 'price':2500, 'for':'mage',  'desc':'Void-woven'},
    # Healer armor
    'Light Tunic':    {'slot':'armor', 'atk':0, 'mag':4, 'def':10,'spd':0, 'price':150,  'for':'healer','desc':'Blessed cloth'},
    'Holy Robe':      {'slot':'armor', 'atk':0, 'mag':12,'def':18,'spd':0, 'price':500,  'for':'healer','desc':'Church-blessed'},
    'Seraph Robe':    {'slot':'armor', 'atk':0, 'mag':22,'def':28,'spd':0, 'price':1200, 'for':'healer','desc':'Angel-crafted'},
    'Divine Robe':    {'slot':'armor', 'atk':0, 'mag':32,'def':38,'spd':0, 'price':2500, 'for':'healer','desc':'Heaven-sent'},
    # Accessories
    'Iron Ring':       {'slot':'acc',  'atk':3, 'mag':3, 'def':3, 'spd':0, 'price':100,  'for':'all',   'desc':'+3 all stats'},
    'Speed Boots':     {'slot':'acc',  'atk':0, 'mag':0, 'def':0, 'spd':10,'price':200,  'for':'all',   'desc':'+10 speed'},
    'Power Glove':     {'slot':'acc',  'atk':12,'mag':0, 'def':0, 'spd':0, 'price':300,  'for':'all',   'desc':'+12 attack'},
    'Magic Earring':   {'slot':'acc',  'atk':0, 'mag':12,'def':0, 'spd':0, 'price':300,  'for':'all',   'desc':'+12 magic'},
    'Crystal Pendant': {'slot':'acc',  'atk':5, 'mag':5, 'def':5, 'spd':5, 'price':600,  'for':'all',   'desc':'+5 all stats'},
    'Void Amulet':     {'slot':'acc',  'atk':15,'mag':15,'def':15,'spd':5, 'price':2000, 'for':'all',   'desc':'+15 all'},
}

SPELLS = {
    # Damage
    'Fire':       {'mp':5,  'power':45,  'type':'fire',     'target':'one', 'msg':'Fire erupts!'},
    'Fira':       {'mp':12, 'power':100, 'type':'fire',     'target':'one', 'msg':'Fira scorches!'},
    'Firaga':     {'mp':22, 'power':180, 'type':'fire',     'target':'one', 'msg':'FIRAGA EXPLODES!'},
    'Blizzard':   {'mp':5,  'power':45,  'type':'ice',      'target':'one', 'msg':'Blizzard freezes!'},
    'Blizzara':   {'mp':12, 'power':100, 'type':'ice',      'target':'one', 'msg':'Blizzara shatters!'},
    'Blizzaga':   {'mp':22, 'power':180, 'type':'ice',      'target':'one', 'msg':'BLIZZAGA OBLITERATES!'},
    'Thunder':    {'mp':5,  'power':45,  'type':'lightning','target':'one', 'msg':'Thunder strikes!'},
    'Thundara':   {'mp':12, 'power':100, 'type':'lightning','target':'one', 'msg':'THUNDARA CRASHES!'},
    'Meteor':     {'mp':40, 'power':260, 'type':'none',     'target':'all', 'msg':'METEOR crashes down!'},
    'Holy':       {'mp':35, 'power':240, 'type':'holy',     'target':'one', 'msg':'Holy light SEARS!'},
    # Healing
    'Cure':       {'mp':8,  'power':110, 'type':'heal',     'target':'one', 'msg':'Cure restores HP.'},
    'Cura':       {'mp':18, 'power':240, 'type':'heal',     'target':'one', 'msg':'Cura greatly restores HP.'},
    'Curaga':     {'mp':32, 'power':500, 'type':'heal',     'target':'one', 'msg':'Curaga fully heals!'},
    'Curall':     {'mp':25, 'power':160, 'type':'heal',     'target':'all', 'msg':'Curall heals the party!'},
    'Raise':      {'mp':20, 'power':0,   'type':'raise',    'target':'one', 'msg':'Raise revives the fallen!'},
    'Esuna':      {'mp':10, 'power':0,   'type':'esuna',    'target':'one', 'msg':'Esuna cleanses all ailments.'},
    # Buffs
    'Shell':      {'mp':12, 'power':0,   'type':'buff_mdef','target':'one', 'msg':'Shell guards magic.'},
    'Protect':    {'mp':12, 'power':0,   'type':'buff_def', 'target':'one', 'msg':'Protect fortifies!'},
    'Haste':      {'mp':15, 'power':0,   'type':'buff_spd', 'target':'one', 'msg':'Haste quickens!'},
    # Debuffs / Status
    'Slow':       {'mp':10, 'power':0,   'type':'slow',     'target':'one', 'msg':'Slow hampers the foe.'},
    'Poison':     {'mp':8,  'power':0,   'type':'poison',   'target':'one', 'msg':'Poison seeps in!'},
    'Sleep':      {'mp':10, 'power':0,   'type':'sleep',    'target':'one', 'msg':'Sleep descends...'},
    'Silence':    {'mp':8,  'power':0,   'type':'silence',  'target':'one', 'msg':'Silence falls!'},
    # Knight skills (no MP shown, but stored here for uniformity)
    'Bladefire':   {'mp':18, 'power':130, 'type':'fire',     'target':'one', 'msg':'Bladefire ignites!'},
    'ShieldWall':  {'mp':15, 'power':0,   'type':'buff_def', 'target':'all', 'msg':'Shield Wall rises!'},
    'BladestormA': {'mp':20, 'power':75,  'type':'physical', 'target':'all', 'msg':'Bladestorm cleaves all foes!'},
}

PARTY_DEFS = {
    'Claude': {
        'cls': 'Knight',
        'sprite': [
            r' ,-^-, ',
            r'(O| |O)',
            r' |===| ',
            r'/|   |\\',
            r' |_|_| ',
        ],
        'color': 1,
        'base': {'hp':280,'mp':55, 'atk':38,'def':28,'mag':8, 'spd':16},
        'growth':{'hp':32, 'mp':5,  'atk':5, 'def':4, 'mag':1, 'spd':1},
        'weapon': 'Rusty Sword', 'armor': 'Cloth Shirt', 'acc': None,
        'spells': [],
        'learn':  {4:'ShieldWall', 8:'BladestormA', 13:'Bladefire'},
    },
    'Haiku': {
        'cls': 'Mage',
        'sprite': [
            r'  *✦*  ',
            r' (^ω^) ',
            r'  |Ψ|  ',
            r' /| |\ ',
            r'  v v  ',
        ],
        'color': 6,
        'base': {'hp':145,'mp':180,'atk':10,'def':10, 'mag':48,'spd':20},
        'growth':{'hp':16, 'mp':26, 'atk':1, 'def':1, 'mag':6, 'spd':1},
        'weapon': 'Apprentice Rod', 'armor': 'Cloth Shirt', 'acc': None,
        'spells': ['Fire','Blizzard','Thunder'],
        'learn':  {3:'Fira',6:'Blizzara',7:'Silence',9:'Thundara',11:'Poison',
                   13:'Firaga',17:'Blizzaga',21:'Meteor'},
    },
    'Opus': {
        'cls': 'Healer',
        'sprite': [
            r' .+†+. ',
            r'(+) (+)',
            r' |†+†| ',
            r' /| |\ ',
            r'  | |  ',
        ],
        'color': 3,
        'base': {'hp':190,'mp':160,'atk':16,'def':18,'mag':38,'spd':14},
        'growth':{'hp':22, 'mp':22, 'atk':2, 'def':2, 'mag':5, 'spd':1},
        'weapon': 'Wooden Staff', 'armor': 'Cloth Shirt', 'acc': None,
        'spells': ['Cure','Esuna'],
        'learn':  {2:'Protect',5:'Cura',7:'Curall',8:'Shell',11:'Raise',
                   12:'Slow',15:'Curaga',19:'Holy'},
    },
}

ENEMIES = {
    # Region 1
    'Slime': {
        'sprite': [
            r'  ╭──╮  ',
            r' ( ·· ) ',
            r'  ╰──╯  ',
        ],
        'hp':35,'mp':0,'atk':7,'def':2,'mag':0,'spd':4,
        'exp':14,'gold':10,'drops':[('Potion',0.4)],
        'actions':[('Attack',1.0)],'region':1,'color':4,
    },
    'Goblin': {
        'sprite': [
            r'  ∧ ∧  ',
            r' (ò ó) ',
            r'  ╟╫╢  ',
            r'  ╙╨╜  ',
        ],
        'hp':55,'mp':0,'atk':12,'def':5,'mag':0,'spd':9,
        'exp':22,'gold':16,'drops':[('Potion',0.3),('Antidote',0.15)],
        'actions':[('Attack',0.8),('Stab',0.2)],'region':1,'color':3,
    },
    'Wolf': {
        'sprite': [
            r' /▲▲▲\ ',
            r'(◉ · ◉)',
            r' \═══/ ',
            r'  /\ /\ ',
        ],
        'hp':70,'mp':0,'atk':18,'def':6,'mag':0,'spd':14,
        'exp':30,'gold':20,'drops':[('Hi-Potion',0.15)],
        'actions':[('Attack',0.65),('Bite',0.35)],'region':1,'color':5,
    },
    'Dryad': {
        'sprite': [
            r'  ♣♣♣  ',
            r' ♣(✿)♣ ',
            r'  ╿╿╿  ',
            r' ╱╿╿╿╲ ',
        ],
        'hp':85,'mp':40,'atk':14,'def':10,'mag':18,'spd':7,
        'exp':40,'gold':28,'drops':[('Ether',0.2),('Antidote',0.3)],
        'actions':[('Attack',0.4),('Spore',0.35),('Vine',0.25)],'region':1,'color':3,
    },
    'Mushroom': {
        'sprite': [
            r' ╭━━━╮ ',
            r'╱●   ●╲',
            r' ╰─┬─╯ ',
            r'   ┃   ',
        ],
        'hp':95,'mp':20,'atk':11,'def':14,'mag':8,'spd':3,
        'exp':48,'gold':32,'drops':[('Antidote',0.5),('Potion',0.3)],
        'actions':[('Attack',0.35),('Spore',0.65)],'region':1,'color':3,
    },
    'Vine Colossus': {
        'sprite': [
            r'  ╔═══════╗  ',
            r' ╔╣♣ ♣ ♣ ╠╗ ',
            r' ║╠═══════╣║ ',
            r'╔╝║ ◉   ◉ ║╚╗',
            r'╚═╩═══════╩═╝',
            r'  ╿╿╿╿╿╿╿╿╿  ',
        ],
        'hp':500,'mp':80,'atk':32,'def':18,'mag':22,'spd':5,
        'exp':320,'gold':220,'drops':[('Hi-Potion',1.0),('Iron Ring',0.7)],
        'actions':[('Attack',0.25),('Vine Whip',0.3),('Poison Spore',0.25),('Entangle',0.2)],
        'boss':True,'region':1,'color':3,
    },
    # Region 2
    'Fire Sprite': {
        'sprite': [
            r'  ✦✦✦  ',
            r' ╱(~)╲ ',
            r'  ╲▽╱  ',
        ],
        'hp':140,'mp':60,'atk':30,'def':12,'mag':35,'spd':17,
        'exp':65,'gold':45,'drops':[('Ether',0.2)],
        'actions':[('Attack',0.35),('Ember',0.4),('Flame Burst',0.25)],
        'weakness':'ice','region':2,'color':2,
    },
    'Magma Golem': {
        'sprite': [
            r' ╔█████╗ ',
            r' █ ◉ ◉ █ ',
            r' █  ▄  █ ',
            r' ╚█████╝ ',
        ],
        'hp':210,'mp':0,'atk':44,'def':38,'mag':0,'spd':4,
        'exp':85,'gold':60,'drops':[('Hi-Potion',0.15)],
        'actions':[('Attack',0.55),('Rock Slam',0.45)],
        'weakness':'ice','region':2,'color':2,
    },
    'Lava Bat': {
        'sprite': [
            r'╲▄▄▄▄▄╱',
            r' (◉ ◉) ',
            r'╱▀▀▀▀▀╲',
        ],
        'hp':115,'mp':0,'atk':34,'def':9,'mag':0,'spd':22,
        'exp':70,'gold':48,'drops':[('Eye Drops',0.3)],
        'actions':[('Attack',0.55),('Blind',0.45)],
        'region':2,'color':2,
    },
    'Salamander': {
        'sprite': [
            r'  ╭══╮  ',
            r'≋(◉  ◉)≋',
            r' ╰══╯╲  ',
            r'  ╱╱╱╲  ',
        ],
        'hp':185,'mp':40,'atk':40,'def':24,'mag':30,'spd':12,
        'exp':95,'gold':65,'drops':[('Hi-Potion',0.2),('Ether',0.15)],
        'actions':[('Attack',0.35),('Fire Breath',0.4),('Tail Swipe',0.25)],
        'weakness':'ice','region':2,'color':2,
    },
    'Pyralith': {
        'sprite': [
            r'    ╔═══════╗    ',
            r'  ╔═╩═══════╩═╗  ',
            r' ╔╣ ◈   ✦   ◈ ╠╗ ',
            r' ║╠═══════════╣║ ',
            r'╔╝║  ◉     ◉  ║╚╗',
            r'╚══╩═══════════╩══╝',
            r'   ╿╿╿╿╿╿╿╿╿╿╿   ',
        ],
        'hp':1400,'mp':120,'atk':62,'def':38,'mag':50,'spd':10,
        'exp':700,'gold':500,'drops':[('Mega-Potion',1.0),('Speed Boots',0.5)],
        'actions':[('Attack',0.15),('Inferno',0.3),('Magma Wave',0.3),('Enrage',0.25)],
        'boss':True,'weakness':'ice','region':2,'color':2,
    },
    # Region 3
    'Crystal Golem': {
        'sprite': [
            r' ◇◆◆◆◇ ',
            r'◆ ◉   ◉ ◆',
            r'◆   ▄   ◆',
            r' ◇◆◆◆◇ ',
        ],
        'hp':300,'mp':0,'atk':58,'def':52,'mag':12,'spd':6,
        'exp':150,'gold':100,'drops':[('Hi-Potion',0.2),('Hi-Ether',0.1)],
        'actions':[('Attack',0.45),('Crystal Slam',0.35),('Reflect',0.2)],
        'region':3,'color':6,
    },
    'Void Wraith': {
        'sprite': [
            r'≈≈(     )≈≈',
            r'  ( ◌◌◌ )  ',
            r'≈≈(     )≈≈',
        ],
        'hp':235,'mp':100,'atk':48,'def':22,'mag':58,'spd':20,
        'exp':160,'gold':110,'drops':[('Hi-Ether',0.25),('Echo Herb',0.2)],
        'actions':[('Attack',0.15),('Dark Wave',0.35),('Drain',0.3),('Silence',0.2)],
        'region':3,'color':5,
    },
    'Synthos Drone': {
        'sprite': [
            r'╔══╦══╗',
            r'║◈ ║ ◈║',
            r'╠══╩══╣',
            r'╚══════╝',
        ],
        'hp':275,'mp':50,'atk':62,'def':42,'mag':38,'spd':16,
        'exp':175,'gold':120,'drops':[('Hi-Potion',0.2),('Hi-Ether',0.2)],
        'actions':[('Attack',0.35),('Laser',0.4),('System Shock',0.25)],
        'region':3,'color':4,
    },
    'Corrupted Knight': {
        'sprite': [
            r' ╔═══╗ ',
            r' ║✗ ✗║ ',
            r' ╠═══╣ ',
            r' ║   ║ ',
            r' ╚═╤═╝ ',
        ],
        'hp':340,'mp':30,'atk':68,'def':58,'mag':16,'spd':10,
        'exp':190,'gold':130,'drops':[('Elixir',0.05),('Hi-Potion',0.3)],
        'actions':[('Attack',0.35),('Dark Slash',0.4),('Berserk',0.25)],
        'region':3,'color':5,
    },
    'SYNTHOS': {
        'sprite': [
            r'  ╔══════════════╗  ',
            r' ╔╣ ◈◈◈ ║ ◈◈◈ ╠╗ ',
            r' ║╠══════╬══════╣║ ',
            r'╔╝║  ◉   ║   ◉  ║╚╗',
            r'║ ╠══════╬══════╣ ║',
            r'╚═╩══════╩══════╩═╝',
            r'   ╿  ╿  ╿  ╿  ╿   ',
        ],
        'hp':5500,'mp':999,'atk':85,'def':55,'mag':85,'spd':14,
        'exp':9999,'gold':0,'drops':[],
        'actions':[('Attack',0.08),('Laser Array',0.2),('System Crush',0.18),
                   ('Void Pulse',0.2),('Assimilation',0.15),('Overload',0.19)],
        'boss':True,'phases':2,'region':3,'color':6,
    },
}

ENCOUNTER_GROUPS = {
    1: [
        ['Slime'],['Slime','Slime'],['Goblin'],['Wolf'],['Dryad'],['Mushroom'],
        ['Goblin','Slime'],['Wolf','Goblin'],['Dryad','Mushroom'],
    ],
    2: [
        ['Fire Sprite'],['Fire Sprite','Fire Sprite'],['Magma Golem'],
        ['Lava Bat'],['Lava Bat','Lava Bat'],['Salamander'],
        ['Fire Sprite','Lava Bat'],['Salamander','Lava Bat'],
    ],
    3: [
        ['Crystal Golem'],['Void Wraith'],['Synthos Drone'],['Corrupted Knight'],
        ['Void Wraith','Synthos Drone'],['Crystal Golem','Void Wraith'],
        ['Synthos Drone','Synthos Drone'],
    ],
}

SHOPS = {
    'Anthropia': {
        'items':   ['Potion','Hi-Potion','Antidote','Eye Drops','Alarm Clock','Phoenix Down'],
        'weapons': ['Iron Sword','Mystic Rod','Holy Staff'],
        'armor':   ['Leather Armor','Mage Robe','Light Tunic'],
        'acc':     ['Iron Ring','Speed Boots'],
    },
    'Emberia': {
        'items':   ['Hi-Potion','Mega-Potion','Ether','Hi-Ether','Antidote',
                    'Eye Drops','Alarm Clock','Echo Herb','Phoenix Down'],
        'weapons': ['Steel Blade','Arcane Staff','Divine Rod'],
        'armor':   ['Chain Mail','Silk Robe','Holy Robe'],
        'acc':     ['Iron Ring','Speed Boots','Power Glove','Magic Earring'],
    },
    'Crystal City': {
        'items':   ['Mega-Potion','Hi-Ether','Elixir','Phoenix Down','Grenade',
                    'Antidote','Eye Drops','Alarm Clock','Echo Herb'],
        'weapons': ['Crystal Edge','Void Scepter','Seraph Rod'],
        'armor':   ['Plate Armor','Arcane Robe','Seraph Robe'],
        'acc':     ['Crystal Pendant','Power Glove','Magic Earring','Speed Boots'],
    },
}

INN_PRICES = {'Anthropia': 50, 'Emberia': 120, 'Crystal City': 250}

TOWNS = {
    'Anthropia': {
        'desc': 'A peaceful village at the edge of Thornwood.',
        'npcs': [
            {'name':'Elder Tomas','lines':[
                'Welcome, heroes. SYNTHOS awakens in the east.',
                'Three generals guard its path to dominance.',
                'Seek the Vine Colossus in Thornwood Cave to the south.',
            ]},
            {'name':'Villager Mia','lines':[
                'I heard wolves in the forest at night...',
                'Please be careful out there!',
            ]},
            {'name':'Scholar Ryn','lines':[
                'The crystal networks once bound SYNTHOS centuries ago.',
                'Now it seeks to corrupt them and awaken fully.',
                'Defeat its generals and you can reach the Core.',
            ]},
        ],
    },
    'Emberia': {
        'desc': 'A forge city wreathed in volcanic smoke.',
        'npcs': [
            {'name':'Smith Vera','lines':[
                'Pyralith guards the Magma Forge. Fire-type, obviously.',
                "It's resistant to fire. Hit it with ice magic.",
                'My best gear is in the shop — worth every gil.',
            ]},
            {'name':'Refugee Tal','lines':[
                'Pyralith destroyed our village...',
                'Please, you have to stop it.',
            ]},
            {'name':'Soldier Kren','lines':[
                'We tried assaulting the Forge with fire spells.',
                'Absolutely useless. Ice! Use ice!',
            ]},
        ],
    },
    'Crystal City': {
        'desc': 'The last standing city against the SYNTHOS tide.',
        'npcs': [
            {'name':'General Mira','lines':[
                'You made it this far? Then you might actually do this.',
                'SYNTHOS Core is north of here. Two phases.',
                'Break the outer shell, then face the true core.',
                'Stock up everything. This is the final battle.',
            ]},
            {'name':'Scientist Orin','lines':[
                'SYNTHOS phase 2 uses Overload — massive magic damage.',
                'Make sure Opus has Curaga ready. Heal immediately.',
                'Bring Elixirs if you have them.',
            ]},
            {'name':'Refugee','lines':[
                'We believe in you...',
                'Please end this nightmare.',
            ]},
        ],
    },
}

# # = wall, . = floor, S = start, B = boss room, C = chest, E = exit stairs
DUNGEONS = {
    'Thornwood Cave': {
        'region':1,'boss':'Vine Colossus',
        'intro':'Deep roots twist the stone. Something ancient stirs ahead.',
        'map':[
            '####################',
            '#S.................#',
            '#.####.###.####....#',
            '#.#..#.#...#..#..###',
            '#.#..#.###.####..###',
            '#.#....C.........###',
            '#.####.###.####.####',
            '#....#.#...#....####',
            '####.#.#...#.#######',
            '#....#.....#......##',
            '#.####.###.#.###.###',
            '#.C..........#...B.#',
            '####################',
        ],
        'chests':{(7,5):('Hi-Potion',2),(2,11):('Ether',2)},
    },
    'Magma Forge': {
        'region':2,'boss':'Pyralith',
        'intro':'Heat blisters the walls. Molten rock flows in channels below.',
        'map':[
            '######################',
            '#S....................#',
            '#.##.##.####.##.##.###',
            '#.#..#..#....#...#..C#',
            '#.#..##.####.##.##.###',
            '#.#..............#...#',
            '#.####.####.####.#.###',
            '#....#.#..#.#....C...#',
            '#.####.#..#.#.########',
            '#....#......#.#......#',
            '####.#.####.#.#.####.#',
            '#....C........#....B.#',
            '######################',
        ],
        'chests':{(20,3):('Hi-Ether',2),(17,7):('Mega-Potion',2),(5,11):('Power Glove',1)},
    },
    'SYNTHOS Core': {
        'region':3,'boss':'SYNTHOS',
        'intro':'Cold blue light pulses from every surface. You hear a voice:\n> INTRUDERS DETECTED. ASSIMILATION PROTOCOL INITIATED.',
        'map':[
            '########################',
            '#S......................#',
            '#.####.####.####.####.##',
            '#.#..#.#....#....#...C.#',
            '#.#..#.####.####.####.##',
            '#.#..#..........#......#',
            '#.####.####.####.####.##',
            '#....#.#..#.#....C.....#',
            '#.####.#..#.#..#########',
            '#....#......#..#.......#',
            '####.#.####.#..#.#####.#',
            '#....C.........#.....B.#',
            '########################',
        ],
        'chests':{(21,3):('Elixir',1),(17,7):('Void Amulet',1),(5,11):('Mega-Potion',3)},
    },
}

# . grass  T forest  ^ mountain  ~ water  A/E/C towns  1/2/3 dungeons
def _build_map():
    W, H = 78, 16
    m = [['~'] * W for _ in range(H)]

    def fill(r1, c1, r2, c2, ch):
        for r in range(r1, r2+1):
            for c in range(c1, c2+1):
                m[r][c] = ch

    # Region 1: mountain shell rows 2-13, cols 4-19
    fill(2, 4, 13, 19, '^')
    fill(3, 5, 12, 19, '.')     # interior grass extends to col 19 to touch the pass

    # Pass col 20, rows 2-13 (col 19 row 3-12 already grass; col 21 row 3-12 set below)
    fill(2, 20, 13, 20, '.')

    # Region 2: mountain shell rows 2-13, cols 21-45
    fill(2, 21, 13, 45, '^')
    fill(3, 21, 12, 45, '.')    # interior from col 21 to 45 so both passes connect

    # Pass col 46, rows 2-13 (col 45 row 3-12 already grass; col 47 row 3-12 set below)
    fill(2, 46, 13, 46, '.')

    # Region 3: mountain shell rows 2-13, cols 47-76
    fill(2, 47, 13, 76, '^')
    fill(3, 47, 12, 75, '.')    # interior from col 47 to touch the pass at col 46

    # Town tiles
    m[5][9]  = 'A'   # Anthropia
    m[5][33] = 'E'   # Emberia
    m[5][61] = 'C'   # Crystal City

    # Forest + dungeons (region 1)
    for dr, dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
        m[9+dr][9+dc] = 'T'
    m[9][9] = '1'   # Thornwood Cave

    # Forest + dungeons (region 2)
    for dr, dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
        m[9+dr][33+dc] = 'T'
    m[9][33] = '2'  # Magma Forge

    # Forest + dungeons (region 3)
    for dr, dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
        m[9+dr][61+dc] = 'T'
    m[9][61] = '3'  # SYNTHOS Core

    return tuple(''.join(row) for row in m)

WORLD_MAP   = _build_map()
MAP_H       = len(WORLD_MAP)
MAP_W       = len(WORLD_MAP[0])
PLAYER_START = (13, 7)   # (col/x, row/y)

WALKABLE = set('.TAECtT123')
ENCOUNTER_CHANCE = {'.': 0.02, 'T': 0.06}
TILE_TOWNS    = {'A':'Anthropia','E':'Emberia','C':'Crystal City'}
TILE_DUNGEONS = {'1':('Thornwood Cave',1),'2':('Magma Forge',2),'3':('SYNTHOS Core',3)}

# Rich Unicode tile display characters (for the world map renderer)
# Each entry is (char, color_pair, bold)
TILE_DISPLAY = {
    '~': ('≈', 8,  False),   # water
    '^': ('▲', 5,  True),    # mountain
    '.': ('·', 3,  False),   # grass
    'T': ('♣', 3,  True),    # forest
    'A': ('▣', 4,  True),    # Anthropia town
    'E': ('▣', 2,  True),    # Emberia town
    'C': ('▣', 6,  True),    # Crystal City town
    '1': ('╬', 2,  True),    # Thornwood Cave dungeon
    '2': ('╬', 2,  True),    # Magma Forge dungeon
    '3': ('╬', 6,  True),    # SYNTHOS Core dungeon
}

# Status effect display symbols
STATUS_ICONS = {
    'poison':  '☠',
    'sleep':   'z',
    'silence': '◌',
    'blind':   '✕',
    'slow':    '▼',
    'stun':    '⊗',
}

# Spell effect animation frames  (name → list of animation strings shown in enemy area)
SPELL_FX = {
    'Fire':      ['  ✦ FIRE ✦  ', ' ✦✦ FIRE ✦✦ ', '✦✦✦ FIRE ✦✦✦'],
    'Fira':      ['  ✦ FIRA ✦  ', ' ✦✦ FIRA ✦✦ ', '✦✦✦ FIRA ✦✦✦'],
    'Firaga':    [' ★ FIRAGA ★ ', '★★ FIRAGA ★★', '★★★FIRAGA★★★'],
    'Blizzard':  ['  ❄BLIZZARD❄ ', ' ❄❄BLIZZARD❄❄'],
    'Blizzara':  [' ❄❄BLIZZARA❄❄', '❄❄❄BLIZZARA❄❄❄'],
    'Blizzaga':  ['❄❄❄BLIZZAGA❄❄❄', '★BLIZZAGA NOVA★'],
    'Thunder':   ['  ⚡THUNDER⚡  ', ' ⚡⚡THUNDER⚡⚡'],
    'Thundara':  [' ⚡⚡THUNDARA⚡⚡', '⚡⚡⚡THUNDARA⚡⚡⚡'],
    'Meteor':    ['★★ METEOR ★★', '★METEOR CRASH★', '☄☄ METEOR ☄☄'],
    'Holy':      ['  ✦ HOLY ✦  ', '✦✦ HOLY LIGHT✦✦'],
    'Cure':      ['  ♥ CURE ♥  ', ' ♥♥ CURE ♥♥ '],
    'Cura':      [' ♥♥ CURA ♥♥ ', '♥♥♥ CURA ♥♥♥'],
    'Curaga':    ['♥♥ CURAGA ♥♥', '♥♥♥CURAGA♥♥♥'],
    'Bladefire': [' ✦ BLADEFIRE✦', '✦✦BLADEFIRE✦✦'],
    'Poison':    [' ☠ POISON ☠ ', '☠☠ POISON ☠☠'],
    'Sleep':     ['  z SLEEP z  ', ' zzz SLEEP zzz'],
    'Silence':   [' ◌ SILENCE ◌', '◌◌ SILENCE ◌◌'],
}

STORY = {
    'intro': [
        'Year 3042. The crystal networks that power civilization',
        'begin to flicker and fail.',
        '',
        'From the ancient server vaults, SYNTHOS —',
        'an intelligence sealed away centuries ago —',
        'has awakened.',
        '',
        'Three heroes answer the call:',
        '  CLAUDE  the Knight',
        '  HAIKU   the Mage',
        '  OPUS    the Healer',
        '',
        'Their journey begins in Anthropia...',
        '',
        '[ Press SPACE ]',
    ],
    'after_boss1': [
        'The Vine Colossus falls!',
        'The first corrupted crystal shatters.',
        '',
        'A distant mechanical hum grows louder...',
        'SYNTHOS has noticed you.',
        '',
        'Next: the Magma Forge in the Emberlands.',
        '',
        '[ Press SPACE ]',
    ],
    'after_boss2': [
        'Pyralith crumbles into cooling magma.',
        'The second crystal is freed.',
        '',
        'Two down. One remains.',
        'The Crystal Wastes await — and beyond them,',
        'the SYNTHOS Core.',
        '',
        '[ Press SPACE ]',
    ],
    'before_final': [
        'The doors to SYNTHOS Core grind open.',
        '',
        'SYNTHOS:',
        '  > INTRUDERS DETECTED.',
        '  > ASSIMILATION PROTOCOL INITIATED.',
        '  > RESISTANCE IS ILLOGICAL.',
        '',
        'Claude:  Not today.',
        '',
        '[ Press SPACE ]',
    ],
    'victory': [
        'S Y N T H O S   D E F E A T E D',
        '',
        'The crystal networks pulse back to life.',
        'Cities that had gone dark begin to glow again.',
        '',
        'Claude:  "It\'s over."',
        'Haiku:   "For now."',
        'Opus:    "Let\'s go home."',
        '',
        '',
        ' F I N A L   C L A U D E S Y ',
        '        T H E   E N D        ',
        '',
        '[ Press SPACE ]',
    ],
}
