"""Super Claudio — level data.

Tile key (1 char = 1 tile = 2 screen cols):
  ' '  air
  '='  solid ground (indestructible)
  '#'  brick (breakable when super/fire)
  '?'  question block (has item inside)
  'X'  used/empty block
  'c'  coin
  'g'  Glitchy (goomba-type, walk into walls reverse)
  't'  Tokenoopa (koopa-type, stomped into shell)
  'h'  Hallucigator (flying enemy)
  '|'  pipe side (solid)
  'P'  pipe top (solid, enter-able someday)
  '^'  flagpole tip
  'F'  flagpole base
"""

# Each level: list of strings (all same length recommended)
# Rows: 0=top sky ... 9=bedrock
# Player starts near left, on the ground row

LEVELS = [
    {
        'world': (1, 1),
        'name':  'Startup Fields',
        'time':  280,
        'music': 'bright',
        'data': [
            #0         1         2         3         4         5         6         7         8         9        10
            #0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012
            "                                                                                                  ^ ",
            "                                                                                                  F ",
            "                 c c c                   c c c                                                    | ",
            "            ?         ?        ?##?              ?                               ?                | ",
            "                                                                                                  | ",
            "                           ====                         ====      ====                            | ",
            "                  g                  g     t                               t               g     | ",
            "========================        ===========         ====      ====      ===================      ==",
            "========================================================================================================",
            "========================================================================================================",
        ],
        'player_start': (3, 5),  # (tile_x, tile_y) — above ground
        'question_contents': {   # (tile_x, tile_y) → 'coin'|'mushroom'|'flower'
            (12, 3): 'coin',
            (18, 3): 'coin',
            (28, 3): 'coin',
            (29, 3): 'coin',
            (38, 3): 'coin',
            (59, 3): 'mushroom',
            (79, 3): 'coin',
        },
    },
    {
        'world': (1, 2),
        'name':  'Token Caverns',
        'time':  220,
        'music': 'cave',
        'data': [
            "########################################################################################################",
            "#                                                                                                     ^#",
            "#  c  c  c                c c c                    c c c                                             |#",
            "#           ?    ?  ?          ?###?                        ?                             ?          |#",
            "#                                              ======                                                |#",
            "#          ===                                                    ====     ====                       |#",
            "#                  g         g    t                                              t          g    t   |#",
            "#===================      =========         ======      ====       =============================   ===#",
            "########################################################################################################",
            "########################################################################################################",
        ],
        'player_start': (2, 5),
        'question_contents': {
            (12, 3): 'coin', (17, 3): 'coin', (19, 3): 'mushroom',
            (26, 3): 'coin', (27, 3): 'coin', (28, 3): 'coin',
            (41, 3): 'coin', (42, 3): 'coin', (43, 3): 'coin',
            (53, 3): 'coin',
            (79, 3): 'flower',
        },
    },
    {
        'world': (1, 3),
        'name':  'Neural Peaks',
        'time':  200,
        'music': 'boss',
        'data': [
            "                                                                                                      ^ ",
            "                                                                                                      F ",
            "         c c c        c c             c c c                  c  c  c                                  | ",
            "    ?    ?     ?    ?      ?    ?##?        ?   ?   ?                            ?        ?           | ",
            "                                                                                                      | ",
            "   ====              ====             ====                 ====      ====    ====                     | ",
            "              g  t          g  t            g  h  t  g                          t  h  g  t           | ",
            "====      ========      ========       ==========     ====      ====      ======================   ===",
            "=========================================================================================================",
            "=========================================================================================================",
        ],
        'player_start': (3, 5),
        'question_contents': {
            (5, 3): 'coin',  (9, 3): 'mushroom', (11, 3): 'coin',
            (14, 3): 'coin', (20, 3): 'coin',    (23, 3): 'coin',
            (27, 3): 'coin', (28, 3): 'coin',
            (32, 3): 'coin', (34, 3): 'coin',    (36, 3): 'coin',
            (38, 3): 'flower',
            (65, 3): 'flower',
            (73, 3): 'coin', (78, 3): 'coin',
        },
    },
]
TILE_SOLID   = set('=#?X|PF^')
TILE_BREAKABLE = {'#'}   # breakable by super/fire Claudio

TILE_DISPLAY = {
    ' ': ('  ', 0, False),   # air / sky
    '=': ('▓▓', 5, True),    # solid ground — heavy block texture
    '#': ('▦▦', 5, True),    # brick — cross-hatch brick look
    '?': ('[?', 4, True),    # question block — gold shimmer (overridden in draw)
    'X': ('▒▒', 5, False),   # used/spent block — faded
    'c': ('◆·', 4, True),    # coin — spinning diamond (overridden in draw)
    '|': ('▐▌', 3, False),   # pipe wall — half-block bars
    'P': ('╒╕', 3, True),    # pipe top opening
    '^': ('★ ', 4, True),    # flagpole tip — star
    'F': ('│ ', 3, False),   # flagpole pole — single vertical bar
    'g': ('  ', 2, False),   # glitchy (drawn separately)
    't': ('  ', 4, False),   # tokenoopa (drawn separately)
    'h': ('  ', 6, False),   # hallucigator (drawn separately)
}
