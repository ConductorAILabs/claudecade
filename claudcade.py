#!/usr/bin/env python3
"""Claudcade — The Claude Terminal Arcade Launcher"""
import curses
import os
import random
import subprocess
import sys
import time

from claudcade_engine import at_safe, setup_colors

# ── TITLE ART (CLAUDECADE in block font) ───────────────────────────────────────
TITLE = [
    " ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗ ██████╗ █████╗ ██████╗ ███████╗",
    "██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝",
    "██║     ██║     ███████║██║   ██║██║  ██║█████╗  ██║     ███████║██║  ██║█████╗  ",
    "██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝  ██║     ██╔══██║██║  ██║██╔══╝  ",
    "╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗╚██████╗██║  ██║██████╔╝███████╗",
    " ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═════╝ ╚══════╝",
]

# Game block-font titles (for right panel display)
GAME_TITLES = {
    'ctype': [
        " ██████╗       ████████╗██╗   ██╗██████╗ ███████╗",
        "██╔════╝       ╚══██╔══╝╚██╗ ██╔╝██╔══██╗██╔════╝",
        "██║     ██████╗   ██║    ╚████╔╝ ██████╔╝█████╗  ",
        "██║     ╚═════╝   ██║     ╚██╔╝  ██╔═══╝ ██╔══╝  ",
        "╚██████╗          ██║      ██║   ██║     ███████╗",
        " ╚═════╝          ╚═╝      ╚═╝   ╚═╝     ╚══════╝",
    ],
    'claudtra': [
        " ██████╗██╗      █████╗ ██╗   ██╗██████╗ ████████╗██████╗  █████╗ ",
        "██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗",
        "██║     ██║     ███████║██║   ██║██║  ██║   ██║   ██████╔╝███████║",
        "██║     ██║     ██╔══██║██║   ██║██║  ██║   ██║   ██╔══██╗██╔══██║",
        "╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝   ██║   ██║  ██║██║  ██║",
        " ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝",
    ],
    'fight': [
        " ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗    ███████╗██╗ ██████╗ ██╗  ██╗████████╗███████╗██████╗ ",
        "██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝    ██╔════╝██║██╔════╝ ██║  ██║╚══██╔══╝██╔════╝██╔══██╗",
        "██║     ██║     ███████║██║   ██║██║  ██║█████╗      █████╗  ██║██║  ███╗███████║   ██║   █████╗  ██████╔╝",
        "██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝      ██╔══╝  ██║██║   ██║██╔══██║   ██║   ██╔══╝  ██╔══██╗",
        "╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗    ██║     ██║╚██████╔╝██║  ██║   ██║   ███████╗██║  ██║",
        " ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝    ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝",
    ],
    'finalclaudesy': [
        "███████╗██╗███╗   ██╗ █████╗ ██╗          ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗███████╗██╗   ██╗",
        "██╔════╝██║████╗  ██║██╔══██╗██║         ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝██╔════╝╚██╗ ██╔╝",
        "█████╗  ██║██╔██╗ ██║███████║██║         ██║     ██║     ███████║██║   ██║██║  ██║█████╗  ███████╗ ╚████╔╝ ",
        "██╔══╝  ██║██║╚██╗██║██╔══██║██║         ██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝  ╚════██║  ╚██╔╝  ",
        "██║     ██║██║ ╚████║██║  ██║███████╗    ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗███████║   ██║   ",
        "╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝     ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚══════╝   ╚═╝   ",
    ],
    'superclaudio': [
        "███████╗██╗   ██╗██████╗ ███████╗██████╗      ██████╗██╗      █████╗ ██╗   ██╗██████╗ ██╗ ██████╗ ",
        "██╔════╝██║   ██║██╔══██╗██╔════╝██╔══██╗    ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██║██╔═══██╗",
        "███████╗██║   ██║██████╔╝█████╗  ██████╔╝    ██║     ██║     ███████║██║   ██║██║  ██║██║██║   ██║",
        "╚════██║██║   ██║██╔═══╝ ██╔══╝  ██╔══██╗    ██║     ██║     ██╔══██║██║   ██║██║  ██║██║██║   ██║",
        "███████║╚██████╔╝██║     ███████╗██║  ██║    ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝██║╚██████╔╝",
        "╚══════╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝     ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝ ",
    ],
    'claudturismo': [
        " ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗    ████████╗██╗   ██╗██████╗ ██╗███████╗███╗   ███╗ ██████╗ ",
        "██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝    ╚══██╔══╝██║   ██║██╔══██╗██║██╔════╝████╗ ████║██╔═══██╗",
        "██║     ██║     ███████║██║   ██║██║  ██║█████╗         ██║   ██║   ██║██████╔╝██║███████╗██╔████╔██║██║   ██║",
        "██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝         ██║   ██║   ██║██╔══██╗██║╚════██║██║╚██╔╝██║██║   ██║",
        "╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗       ██║   ╚██████╔╝██║  ██║██║███████║██║ ╚═╝ ██║╚██████╔╝",
        " ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝       ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝ ",
    ],
    'claudemon': [
        " ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗███╗   ███╗ ██████╗ ███╗   ██╗",
        "██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝████╗ ████║██╔═══██╗████╗  ██║",
        "██║     ██║     ███████║██║   ██║██║  ██║█████╗  ██╔████╔██║██║   ██║██╔██╗ ██║",
        "██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝  ██║╚██╔╝██║██║   ██║██║╚██╗██║",
        "╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝██║ ╚████║",
        " ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝",
    ],
}

# ── GAME CATALOGUE ─────────────────────────────────────────────────────────────
# Each game has 'frames' (list of frame-art for animation) instead of static 'art'.
# Animation cycles every ~6 ticks via frames[(tick // 6) % len(frames)].

GAMES = [
    {
        'name':     'C-TYPE',
        'subtitle': 'SPACE SHOOTER',
        'script':   'ctype.py',
        'genre':    'SHMUP',
        'color':    1,
        'title_key': 'ctype',
        'desc': [
            'Dodge waves · Charge beam · Get power-ups',
            'Boss every 6th wave · Parallax starfield',
            '5 enemy types · Escalating difficulty',
            'Score system with local leaderboard',
        ],
        'controls': [
            'WASD / Arrows  Move',
            'J / SPACE      Fire',
            'Hold J         Charge beam',
            'ESC            Pause / Quit',
        ],
        # Animation: ship firing bullets right, enemies drift in from the right,
        # occasional impact mid-cycle. 8 frames @ 10 FPS = ~0.8s per loop.
        'frames': [
            ["  ▲ ·         ◆",
             "═►       ·     ",
             "  ▼          ◆ "],
            ["  ▲  ·       ◆ ",
             "═►·       ·    ",
             "  ▼         ◆  "],
            ["  ▲   ·     ◆  ",
             "═►   ·     ·   ",
             "  ▼        ◆   "],
            ["  ▲    ·   ◆   ",
             "═►·     ·    ✦ ",
             "  ▼       ◆    "],
            ["  ▲     ·  ✧   ",
             "═►   ·      ·  ",
             "  ▼       ·    "],
            ["  ▲      ·  ·  ",
             "═►·     ·      ",
             "  ▼            "],
            ["  ▲       ·   ◆",
             "═►   ·       · ",
             "  ▼          ◆ "],
            ["  ▲ ·      ·  ◆",
             "═►·    ·       ",
             "  ▼         ◆  "],
        ],
    },
    {
        'name':     'CLAUDTRA',
        'subtitle': 'RUN & GUN',
        'script':   'claudtra.py',
        'genre':    'ACTION',
        'color':    3,
        'title_key': 'claudtra',
        'desc': [
            'Side-scrolling action platformer',
            'Grunt and heavy enemies · Multi-life system',
            'Jump, crouch, shoot through waves',
            'Score system with local leaderboard',
        ],
        'controls': [
            'A / D          Move left / right',
            'SPACE          Jump',
            'J              Shoot',
            'S              Crouch · ESC  Pause',
        ],
        # Animation: runner with shot flying right, enemy approaching, leg cycle.
        'frames': [
            ["  ╭─╮          ",
             "  │·│═►        ",
             "  ╰┬╯       ·  ",
             "  ╱╲      ·  ◆ "],
            ["  ╭─╮    ·     ",
             "  │·│  ═►      ",
             "  ╰┬╯      ·   ",
             "  ╲╱   ·    ◆  "],
            ["  ╭─╮     ·    ",
             "  │·│   ═►     ",
             "  ╰┬╯     ·    ",
             "  ╱╲     ◆     "],
            ["  ╭─╮      ·   ",
             "  │·│    ═►    ",
             "  ╰┬╯    · ✦   ",
             "  ╲╱      ✧    "],
            ["  ╭─╮   ·      ",
             "  │·│     ═►   ",
             "  ╰┬╯           ",
             "  ╱╲           "],
            ["  ╭─╮    ·     ",
             "  │·│      ═►  ",
             "  ╰┬╯       ·  ",
             "  ╲╱        ·  "],
            ["  ╭─╮     ·    ",
             "  │·│═►     ·  ",
             "  ╰┬╯        · ",
             "  ╱╲      ·  ◆ "],
            ["  ╭─╮          ",
             "  │·│═►        ",
             "  ╰┬╯     ·    ",
             "  ╲╱    ·    ◆ "],
        ],
    },
    {
        'name':     'CLAUDE FIGHTER',
        'subtitle': '1V1 FIGHTING',
        'script':   'fight.py',
        'genre':    'FIGHTING',
        'color':    2,
        'title_key': 'fight',
        'desc': [
            '5 unique fighters with distinct styles',
            'Punch, kick, block, jump mechanics',
            'Best of 3 rounds vs AI opponent',
            'Score system with local leaderboard',
        ],
        'controls': [
            'A / D          Move',
            'SPACE          Jump',
            'J              Punch',
            'K  Kick · L  Block · S  Crouch',
        ],
        # Animation: two fighters trading punches; left jabs F1-F3, right counters F4-F6.
        'frames': [
            ["  ◯       ◯   ",
             " ╱│╲     ╱│╲  ",
             "  ╱╲     ╱╲   "],
            ["  ◯       ◯   ",
             " ╱│═►    ╱│╲  ",
             "  ╱╲     ╱╲   "],
            ["  ◯       ◯   ",
             " ╱│═══►  ╱│╲  ",
             "  ╱╲     ╱╲   "],
            ["  ◯    ✦  ◯   ",
             " ╱│═════ ✧│╲  ",
             "  ╱╲     ╱╲   "],
            ["  ◯       ◯   ",
             " ╱│╲   ◀═│╲   ",
             "  ╱╲     ╱╲   "],
            ["  ◯       ◯   ",
             " ╱│╲ ◀═══│╲   ",
             "  ╱╲     ╱╲   "],
            ["  ◯  ✦    ◯   ",
             "╲╱│ ◀═════│╲  ",
             "  ╱╲     ╱╲   "],
            ["  ◯       ◯   ",
             " ╱│╲     ╱│╲  ",
             "  ╱╲     ╱╲   "],
        ],
    },
    {
        'name':     'SUPER CLAUDIO',
        'subtitle': 'PLATFORMER',
        'script':   None,
        'genre':    'PLATFORM',
        'color':    4,
        'title_key': 'superclaudio',
        'coming_soon': True,
        'desc': [
            'Save the princess. Jump, stomp, collect.',
            '4 worlds · Power-ups · Hidden levels',
            'Classic platforming action',
            'COMING SOON · In development',
        ],
        'controls': [
            'A / D          Move',
            'W / SPACE      Jump',
            'J              Fire / Run',
            'ESC            Pause',
        ],
        # Animation: hero runs, jumps for coin, grabs it, lands. 8 frames.
        'frames': [
            ["    ★         ",
             "   ◯    ◆  ◆  ",
             "  ╱│╲         ",
             "  ╱ ╲ ▓▓▓▓▓▓▓ "],
            ["    ★         ",
             "   ◯    ◆  ◆  ",
             "  ╱│╲         ",
             "   ╲╱ ▓▓▓▓▓▓▓ "],
            ["   ◯ ★         ",
             "  ╱│╲   ◆  ◆  ",
             "    ▼         ",
             "      ▓▓▓▓▓▓▓ "],
            ["   ◯  ★        ",
             "  ╱│╲ ✦    ◆  ",
             "                 ",
             "      ▓▓▓▓▓▓▓ "],
            ["   ◯           ",
             "  ╱│╲ ✧    ◆  ",
             "    ▼         ",
             "      ▓▓▓▓▓▓▓ "],
            ["    ★         ",
             "   ◯       ◆  ",
             "  ╱│╲         ",
             "  ╱ ╲ ▓▓▓▓▓▓▓ "],
            ["    ★ ◆       ",
             "   ◯       ◆  ",
             "  ╱│╲         ",
             "   ╲╱ ▓▓▓▓▓▓▓ "],
            ["    ★ ◆       ",
             "   ◯    ◆     ",
             "  ╱│╲         ",
             "  ╱ ╲ ▓▓▓▓▓▓▓ "],
        ],
    },
    {
        'name':     'CLAUDTURISMO',
        'subtitle': 'RACING',
        'script':   None,
        'genre':    'RACING',
        'color':    1,
        'title_key': 'claudturismo',
        'coming_soon': True,
        'desc': [
            'Pseudo-3D racing · 3 laps, real curves',
            '8 tracks · 5 cars · Time attack mode',
            'Drift physics · Boost system',
            'COMING SOON · In development',
        ],
        'controls': [
            'W / UP         Accelerate',
            'S / DOWN       Brake',
            'A / D          Steer',
            'SPACE          Boost',
        ],
        # Animation: car holds steady, road dashes scroll right -> sense of speed.
        'frames': [
            ["   ╱─────╲   ",
             "  ╱  ◉═◉  ╲  ",
             "  ▔▔▔▔▔▔▔▔▔  ",
             "  ║ │ │ │ ║  "],
            ["   ╱─────╲   ",
             "  ╱  ◉═◉  ╲  ",
             "  ▔▔▔▔▔▔▔▔▔  ",
             "   ║ │ │ │ ║ "],
            ["   ╱─────╲   ",
             "  ╱  ◉═◉  ╲  ",
             "  ▔▔▔▔▔▔▔▔▔  ",
             "║   ║ │ │ │ ║"],
            ["   ╱─────╲   ",
             "  ╱  ◉═◉  ╲  ",
             "  ▔▔▔▔▔▔▔▔▔  ",
             "│║   ║ │ │ │ "],
            ["   ╱─────╲   ",
             "  ╱  ◉═◉  ╲  ",
             "  ▔▔▔▔▔▔▔▔▔  ",
             "│ ║   ║ │ │ │"],
            ["   ╱─────╲   ",
             "  ╱  ◉═◉  ╲  ",
             "  ▔▔▔▔▔▔▔▔▔  ",
             " │ ║   ║ │ │ "],
            ["   ╱─────╲   ",
             "  ╱  ◉═◉  ╲  ",
             "  ▔▔▔▔▔▔▔▔▔  ",
             "  │ ║   ║ │ │"],
            ["   ╱─────╲   ",
             "  ╱  ◉═◉  ╲  ",
             "  ▔▔▔▔▔▔▔▔▔  ",
             " ║ │ ║   ║ │ "],
        ],
    },
    {
        'name':     'CLAUDEMON',
        'subtitle': 'CREATURE RPG',
        'script':   None,
        'genre':    'CRTR-RPG',
        'color':    3,
        'title_key': 'claudemon',
        'coming_soon': True,
        'desc': [
            'Catch all 20 creatures · Turn-based battles',
            'Type matchups · Evolution · Trading',
            '6 gym leaders · Elite Four · Champion',
            'COMING SOON · In development',
        ],
        'controls': [
            'WASD / Arrows  Move',
            'SPACE          Confirm',
            'M              Menu',
            'B              Bag / Items',
        ],
        # Animation: creature wiggles side to side, blinks, sparkles drift around.
        'frames': [
            ["   ╭───╮     ",
             "   │◉ ◉│  ✦  ",
             "   ╰─◡─╯     ",
             "    ╱╲       "],
            ["    ╭───╮    ",
             "    │◉ ◉│ ✧  ",
             "    ╰─◡─╯    ",
             "     ╱╲      "],
            ["    ╭───╮ ✧  ",
             "    │● ●│    ",
             "    ╰─◠─╯    ",
             "     ╱╲      "],
            ["   ╭───╮ ✦   ",
             " ✧ │◉ ◉│     ",
             "   ╰─◡─╯     ",
             "    ╱╲       "],
            ["   ╭───╮     ",
             " ✦ │★ ★│     ",
             "   ╰─◡─╯     ",
             "    ╱╲       "],
            ["    ╭───╮    ",
             "  ✧ │◉ ◉│ ✦  ",
             "    ╰─◠─╯    ",
             "     ╱╲      "],
            ["   ╭───╮     ",
             "   │● ●│  ✧  ",
             "   ╰─◡─╯     ",
             "    ╱╲       "],
            ["    ╭───╮    ",
             " ✦  │◉ ◉│    ",
             "    ╰─◡─╯    ",
             "     ╱╲      "],
        ],
    },
    {
        'name':     'FINAL CLAUDESY',
        'subtitle': 'EPIC JRPG',
        'script':   'finalclaudesy.py',
        'genre':    'RPG',
        'color':    6,
        'title_key': 'finalclaudesy',
        'desc': [
            '3 heroes · 3 regions · 20+ spells',
            'Turn-based combat · Equipment system',
            'Towns, dungeons, NPCs, full story',
            '~3 hours of content · Multiple endings',
        ],
        'controls': [
            'WASD / Arrows  Move or select',
            'SPACE / Enter  Confirm action',
            'M              Open party menu',
            'Q / ESC        Cancel / Back',
        ],
        # Animation: hero strikes, slash flies right, enemy hit, recovery.
        'frames': [
            ["    ◯        ",
             "   ╱│╲═►     ",
             "    │     ◆  ",
             "   ╱ ╲       "],
            ["    ◯        ",
             "   ╱│ ═►     ",
             "    │     ◆  ",
             "   ╱ ╲       "],
            ["    ◯        ",
             "   ╱│  ═►    ",
             "    │     ◆  ",
             "   ╱ ╲       "],
            ["    ◯        ",
             "   ╱│   ═►   ",
             "    │     ✦  ",
             "   ╱ ╲       "],
            ["    ◯        ",
             "   ╱│    ✧   ",
             "    │   ◀═   ",
             "   ╱ ╲       "],
            ["    ◯        ",
             "   ╱│  ◀═    ",
             "    │ ✧      ",
             "   ╱ ╲       "],
            ["    ◯        ",
             "   ╱│◀═      ",
             "    │  ◆     ",
             "   ╱ ╲       "],
            ["    ◯        ",
             "   ╱│╲       ",
             "    │     ◆  ",
             "   ╱ ╲       "],
        ],
    },
]

# ── LIVE PREVIEW DEMOS ─────────────────────────────────────────────────────────
# Per-game simulators that step state each UI frame and render the result into
# the right-panel preview box. Each demo subclasses _Demo and returns
# DEMO_H rows of DEMO_W cells. Only the currently-highlighted game's demo is
# stepped/rendered — switching selection pauses the previous and resumes the
# new one from wherever it left off.

DEMO_H = 4
DEMO_W = 18


class _Demo:
    # Step state every Nth UI tick (UI runs at 60 FPS — step_every=3 -> 20 sim FPS).
    step_every = 3

    def __init__(self) -> None:
        self.t = 0
        self.ui_t = 0
        self.rng = random.Random()

    def _blank(self) -> list[list[str]]:
        return [[' '] * DEMO_W for _ in range(DEMO_H)]

    def _put(self, c: list[list[str]], r: int, col: int, s: str) -> None:
        if not (0 <= r < DEMO_H):
            return
        for i, ch in enumerate(s):
            cc = col + i
            if 0 <= cc < DEMO_W:
                c[r][cc] = ch

    def render(self) -> list[str]:
        if self.ui_t % self.step_every == 0:
            self.t += 1
            self.step()
        self.ui_t += 1
        canvas = self._blank()
        self.draw(canvas)
        return [''.join(row) for row in canvas]

    def step(self) -> None: pass
    def draw(self, c: list[list[str]]) -> None: pass


class _CtypeDemo(_Demo):
    def __init__(self) -> None:
        super().__init__()
        # Seed in-flight bullets + an approaching enemy so the panel is busy
        # immediately on first reveal rather than building up over a second.
        self.bullets: list[list[int]] = [[7, 1], [11, 1]]
        self.enemies: list[list[int]] = [[DEMO_W - 1, 1]]
        self.hits: list[list[int]] = []

    def step(self) -> None:
        for b in self.bullets: b[0] += 1
        self.bullets = [b for b in self.bullets if b[0] < DEMO_W]
        if self.t % 4 == 0:
            self.bullets.append([5, 1])
        if self.t % 2 == 0:
            for e in self.enemies: e[0] -= 1
            self.enemies = [e for e in self.enemies if e[0] > 4]
        if self.t % 10 == 0 and len(self.enemies) < 3:
            self.enemies.append([DEMO_W - 1, self.rng.randrange(0, 3)])
        for b in self.bullets[:]:
            for e in self.enemies[:]:
                if b[1] == e[1] and abs(b[0] - e[0]) <= 1:
                    self.hits.append([e[0], e[1], 0])
                    if b in self.bullets: self.bullets.remove(b)
                    if e in self.enemies: self.enemies.remove(e)
                    break
        for h in self.hits: h[2] += 1
        self.hits = [h for h in self.hits if h[2] < 3]

    def draw(self, c: list[list[str]]) -> None:
        self._put(c, 0, 2, '▲')
        self._put(c, 1, 0, '═►')
        self._put(c, 2, 2, '▼')
        for b in self.bullets: self._put(c, b[1], b[0], '·')
        for e in self.enemies: self._put(c, e[1], e[0], '◆')
        for h in self.hits:    self._put(c, h[1], h[0], '✦' if h[2] < 2 else '✧')


class _ClaudtraDemo(_Demo):
    def __init__(self) -> None:
        super().__init__()
        self.shot_x = 8       # shot already in flight
        self.enemy_x = 13
        self.leg = 0

    def step(self) -> None:
        if self.t % 2 == 0: self.leg ^= 1
        if self.shot_x < 0:
            if self.t % 7 == 0: self.shot_x = 5
        else:
            self.shot_x += 1
            if self.shot_x >= self.enemy_x - 1:
                self.enemy_x = DEMO_W - 1
                self.shot_x = -1
            elif self.shot_x >= DEMO_W:
                self.shot_x = -1
        if self.t % 4 == 0 and self.enemy_x > 9:
            self.enemy_x -= 1

    def draw(self, c: list[list[str]]) -> None:
        self._put(c, 0, 2, '╭─╮')
        self._put(c, 1, 2, '│·│')
        self._put(c, 2, 2, '╰┬╯')
        self._put(c, 3, 2, '╱╲' if self.leg == 0 else '╲╱')
        if self.shot_x >= 0:
            self._put(c, 1, self.shot_x, '═►')
            if self.shot_x >= self.enemy_x - 2:
                self._put(c, 1, self.enemy_x, '✦'); return
        self._put(c, 1, self.enemy_x, '◆')


class _FightDemo(_Demo):
    step_every = 4

    def __init__(self) -> None:
        super().__init__()
        self.atk = 0          # 0 = left attacks, 1 = right attacks
        self.phase = 2        # start mid-extend so action is visible immediately
        self.phase_t = 0

    def step(self) -> None:
        self.phase_t += 1
        if self.phase_t >= 3:
            self.phase_t = 0
            self.phase += 1
            if self.phase > 4:
                self.phase = 0
                self.atk ^= 1

    def draw(self, c: list[list[str]]) -> None:
        self._put(c, 0, 2,  '◯')
        self._put(c, 0, 13, '◯')
        self._put(c, 2, 2,  '╱╲')
        self._put(c, 2, 13, '╱╲')
        body_l, body_r = ' ╱│╲', ' ╱│╲'
        if self.atk == 0:
            if self.phase == 2:   body_l = ' ╱│═►'
            elif self.phase == 3:
                body_l = ' ╱│════►'; body_r = '  ╲╱│'
                self._put(c, 1, 12, '✦')
            elif self.phase == 4: body_r = '  ╲╱│'
        else:
            if self.phase == 2:   body_r = '◀═│╲'
            elif self.phase == 3:
                body_r = '◀════│╲'; body_l = '│╲╱'
                self._put(c, 1, 5,  '✦')
            elif self.phase == 4: body_l = '│╲╱'
        self._put(c, 1, 1,  body_l)
        self._put(c, 1, 12, body_r)


class _SuperClaudioDemo(_Demo):
    def __init__(self) -> None:
        super().__init__()
        self.jump_t = -1
        self.coin_x = 12          # coin already approaching
        self.collected = False
        self.spawn_cool = 0

    def step(self) -> None:
        if self.coin_x >= 0:
            if self.t % 2 == 0: self.coin_x -= 1
            if self.coin_x < 0:
                self.collected = False
                self.spawn_cool = 8
        elif self.spawn_cool > 0:
            self.spawn_cool -= 1
            if self.spawn_cool == 0:
                self.coin_x = DEMO_W - 1
        if self.coin_x == 8 and self.jump_t < 0:
            self.jump_t = 0
        if self.jump_t >= 0:
            self.jump_t += 1
            if self.jump_t >= 6: self.jump_t = -1
        if self.jump_t in (2, 3) and self.coin_x in range(4, 7):
            self.collected = True
            self.coin_x = -1

    def draw(self, c: list[list[str]]) -> None:
        self._put(c, 3, 0, '▓' * DEMO_W)
        if self.jump_t >= 0:
            self._put(c, 0, 3, '◯')
            self._put(c, 1, 2, '╱│╲')
            self._put(c, 2, 3, '▼')
        else:
            self._put(c, 0, 3, '★')
            self._put(c, 1, 3, '◯')
            self._put(c, 2, 2, '╱│╲')
        if self.coin_x >= 0:
            row = 0 if self.t % 2 == 0 else 1
            self._put(c, row, self.coin_x, '◆')
        elif self.collected:
            self._put(c, 1, 5, '✦')


class _ClaudturismoDemo(_Demo):
    step_every = 2

    def __init__(self) -> None:
        super().__init__()
        self.dash = 0

    def step(self) -> None:
        self.dash = (self.dash + 1) % 4

    def draw(self, c: list[list[str]]) -> None:
        for r in range(DEMO_H):
            self._put(c, r, 1, '║')
            self._put(c, r, DEMO_W - 2, '║')
        mid = DEMO_W // 2
        for i in range(DEMO_H):
            if (i + self.dash) % 2 == 0:
                self._put(c, i, mid, '│')
        self._put(c, 0, 6, '╭───╮')
        self._put(c, 1, 6, '│◉═◉│')
        self._put(c, 2, 6, '╰───╯')


class _ClaudemonDemo(_Demo):
    step_every = 4

    def __init__(self) -> None:
        super().__init__()
        self.wig = 0
        self.blink = 0
        self.sparkles: list[list[int]] = [[2, 0, 0], [14, 1, 1], [3, 2, 2]]

    def step(self) -> None:
        self.wig = (self.wig + 1) % 4
        if self.t % 6 == 0: self.blink = 2
        if self.blink > 0:  self.blink -= 1
        if self.t % 3 == 0 and len(self.sparkles) < 3:
            self.sparkles.append([
                self.rng.randrange(0, DEMO_W),
                self.rng.randrange(0, DEMO_H - 1),
                0,
            ])
        for s in self.sparkles: s[2] += 1
        self.sparkles = [s for s in self.sparkles if s[2] < 4]

    def draw(self, c: list[list[str]]) -> None:
        dx = 1 if self.wig in (1, 2) else 0
        base = 5 + dx
        for s in self.sparkles:
            self._put(c, s[1], s[0], '✦' if s[2] < 2 else '✧')
        self._put(c, 0, base, '╭───╮')
        eyes = '│─ ─│' if self.blink > 0 else '│◉ ◉│'
        self._put(c, 1, base, eyes)
        mouth = '╰─◠─╯' if self.wig in (0, 2) else '╰─◡─╯'
        self._put(c, 2, base, mouth)
        self._put(c, 3, base + 2, '╱╲')


class _FinalClaudesyDemo(_Demo):
    step_every = 4

    def __init__(self) -> None:
        super().__init__()
        self.phase = 2          # start with slash already launching
        self.slash_x = 7
        self.enemy_x = 14

    def step(self) -> None:
        self.phase += 1
        if self.phase == 2:
            self.slash_x = 5
        elif self.phase in (3, 4, 5):
            self.slash_x += 2
        elif self.phase == 6:
            self.slash_x = -1
        elif self.phase >= 9:
            self.phase = 0

    def draw(self, c: list[list[str]]) -> None:
        self._put(c, 0, 3, '◯')
        if self.phase in (1, 2):
            self._put(c, 1, 2, '╱│╲')
        else:
            self._put(c, 1, 2, '╱│ ')
        self._put(c, 2, 3, '│')
        self._put(c, 3, 2, '╱ ╲')
        if 0 <= self.slash_x < DEMO_W:
            self._put(c, 1, self.slash_x, '═►')
        if self.phase < 6:
            self._put(c, 1, self.enemy_x, '◆')
        elif self.phase == 6:
            self._put(c, 1, self.enemy_x, '✦')
        elif self.phase == 7:
            self._put(c, 1, self.enemy_x, '✧')
        else:
            self._put(c, 1, self.enemy_x, '◆')


DEMOS: dict[str, _Demo] = {
    'ctype':         _CtypeDemo(),
    'claudtra':      _ClaudtraDemo(),
    'fight':         _FightDemo(),
    'superclaudio':  _SuperClaudioDemo(),
    'claudturismo':  _ClaudturismoDemo(),
    'claudemon':     _ClaudemonDemo(),
    'finalclaudesy': _FinalClaudesyDemo(),
}


# ── DRAWING HELPERS ────────────────────────────────────────────────────────────
_p = at_safe

# ── MAIN SCREEN ────────────────────────────────────────────────────────────────
# Background-star positions are deterministic per (H,W); cached so we don't
# re-roll random + reseed the global RNG every frame (was 60+ syscalls/sec).
_STAR_CACHE: dict[tuple[int, int], list[tuple[int, int, str]]] = {}

def _bg_stars(H: int, W: int) -> list[tuple[int, int, str]]:
    key = (H, W)
    if key not in _STAR_CACHE:
        rng = random.Random(999)
        glyphs = ['·', '·', '·', '+', '*']
        _STAR_CACHE[key] = [
            (rng.randint(1, max(1, H-2)),
             rng.randint(1, max(1, W-2)),
             rng.choice(glyphs))
            for _ in range(40)
        ]
    return _STAR_CACHE[key]

def draw_main(scr, H, W, tick, cursor):
    P = curses.color_pair
    scr.erase()

    # ── Animated background stars ──────────────────────────────────────────
    dim = P(5)|curses.A_DIM
    for r, c, ch in _bg_stars(H, W):
        if (tick // 8 + r * 3 + c) % 11 == 0:
            _p(scr, H, W, r, c, ch, dim)

    # ── Outer border ────────────────────────────────────────────────────────
    _p(scr, H, W, 0,   0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        _p(scr, H, W, r, 0,   '║', P(5))
        _p(scr, H, W, r, W-1, '║', P(5))

    # ── Header block (shaded depth) ─────────────────────────────────────────
    shade_full = '▓▒░' + '░'*(W-8) + '░▒▓'
    _p(scr, H, W, 1, 1, shade_full[:W-2], P(5)|curses.A_DIM)

    # Title art — gradient from blue → cyan → magenta → pink (top to bottom)
    # Standard 8-color palette: BLUE(8), CYAN(1), MAGENTA(6) approximate the gradient
    title_colors = [
        P(8)|curses.A_BOLD,  # bright blue
        P(8)|curses.A_BOLD,  # bright blue
        P(1)|curses.A_BOLD,  # cyan (transition)
        P(6),                # magenta (transition)
        P(6)|curses.A_BOLD,  # bright pink/magenta
        P(6)|curses.A_BOLD,  # bright pink/magenta
    ]
    for i, line in enumerate(TITLE):
        tx = max(1, (W - len(line)) // 2)
        _p(scr, H, W, 2+i, tx, line, title_colors[i % len(title_colors)])

    # Compute layout based on actual title height
    TITLE_END = 2 + len(TITLE)  # title rows: 2..TITLE_END-1
    sub = '◈   T H E   C L A U D E   T E R M I N A L   A R C A D E   ◈'
    _p(scr, H, W, TITLE_END, max(1, (W-len(sub))//2), sub, P(6)|curses.A_BOLD)

    _p(scr, H, W, TITLE_END+1, 1, shade_full[:W-2], P(5)|curses.A_DIM)

    # ── Section divider ─────────────────────────────────────────────────────
    DIV = TITLE_END + 2
    _p(scr, H, W, DIV, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)

    # ── Vertical panel split ─────────────────────────────────────────────────
    LIST_W  = 30
    SPLIT   = LIST_W + 1
    DET_X   = SPLIT + 1
    DET_W   = W - DET_X - 1
    PANEL_Y = DIV + 1

    for r in range(PANEL_Y, H-3):
        _p(scr, H, W, r, SPLIT, '║', P(5))
    _p(scr, H, W, DIV,  SPLIT, '╦', P(5)|curses.A_BOLD)
    _p(scr, H, W, H-3,  SPLIT, '╩', P(5)|curses.A_BOLD)

    # ── Game list (left panel) ───────────────────────────────────────────────
    _p(scr, H, W, PANEL_Y,   2, 'GAMES',  P(5)|curses.A_BOLD)
    _p(scr, H, W, PANEL_Y,  22, 'GENRE',  P(5)|curses.A_DIM)
    _p(scr, H, W, PANEL_Y+1, 2, '─'*(LIST_W-2), P(5)|curses.A_DIM)

    # One row per game so all 7 fit comfortably in a standard 24-row terminal.
    # Every game uses its assigned color — coming-soon games are still in
    # color, just marked with a star prefix in the genre column.
    for i, g in enumerate(GAMES):
        gy = PANEL_Y + 2 + i
        if gy >= H-4: break
        sel = (i == cursor)
        cs  = g.get('coming_soon')
        prefix = '▶ ' if sel else '  '
        gcp = g['color']
        name_a  = (P(gcp)|curses.A_BOLD|curses.A_REVERSE) if sel else (P(gcp)|curses.A_BOLD)
        genre_a = P(7) if sel else (P(5)|curses.A_DIM)
        _p(scr, H, W, gy,   2, prefix + g['name'][:17], name_a)
        # Coming-soon games get a small ✦ marker in the genre column to flag them.
        genre_text = f'[{g["genre"]:7}]'
        if cs:
            _p(scr, H, W, gy, 19, '✦', P(gcp)|curses.A_BOLD)
        _p(scr, H, W, gy,  21, genre_text, genre_a)

    # ── Game detail (right panel) ────────────────────────────────────────────
    g   = GAMES[cursor]
    gcp = g['color']

    # Block-font game title — centered horizontally in the detail panel.
    # Starts 2 rows below PANEL_Y so it has visual breathing room from the
    # main CLAUDECADE title above the divider (was crammed back-to-back).
    title_key = g.get('title_key', g['name'].lower().replace(' ', ''))
    TITLE_Y = PANEL_Y + 2
    if title_key in GAME_TITLES:
        ART_Y = TITLE_Y
        title_lines = GAME_TITLES[title_key]
        for i, line in enumerate(title_lines):
            if ART_Y + i < H - 4:
                trimmed = line[:DET_W-2] if len(line) > DET_W-2 else line
                tx = DET_X + max(1, (DET_W - len(trimmed)) // 2)
                _p(scr, H, W, ART_Y+i, tx, trimmed, P(gcp)|curses.A_BOLD)
        ART_Y += len(title_lines)
    else:
        ART_Y = TITLE_Y
        gt   = f'★  {g["name"]}  —  {g["subtitle"]}  ★'
        _p(scr, H, W, ART_Y, DET_X+1, gt[:DET_W-2], P(gcp)|curses.A_BOLD)
        ART_Y += 1

    # Single-line subtitle + thin divider under the block-font title.
    sub = f'·  {g["subtitle"]}  ·'
    _p(scr, H, W, ART_Y,   DET_X + max(1, (DET_W - len(sub)) // 2), sub, P(gcp)|curses.A_DIM)
    _p(scr, H, W, ART_Y+1, DET_X+1, '─'*(DET_W-2), P(5)|curses.A_DIM)

    # Game preview — live demo (one simulation step per UI frame). Centered
    # horizontally within the detail panel. Falls back to static `frames` if
    # no demo class is registered for this title_key.
    ART_Y = ART_Y + 3
    demo = DEMOS.get(title_key)
    if demo is not None:
        art = demo.render()
    else:
        frames = g.get('frames') or [g.get('art', [])]
        art    = frames[(tick // 6) % len(frames)] if frames else []
    cs     = g.get('coming_soon')
    if art:
        aw    = max(len(l) for l in art) + 2
        ah    = len(art) + 2
        # Center the box horizontally in the detail panel.
        box_x = DET_X + max(2, (DET_W - (aw + 2)) // 2)
        ART_X = box_x + 2
        if ART_Y + ah < H - 6:
            _p(scr, H, W, ART_Y,      box_x, '┌'+'─'*aw+'┐', P(5)|curses.A_DIM)
            _p(scr, H, W, ART_Y+ah-1, box_x, '└'+'─'*aw+'┘', P(5)|curses.A_DIM)
            for r in range(1, ah-1):
                _p(scr, H, W, ART_Y+r, box_x,        '│', P(5)|curses.A_DIM)
                _p(scr, H, W, ART_Y+r, box_x+aw+1,   '│', P(5)|curses.A_DIM)
            sprite_attr = (P(5)|curses.A_DIM) if cs else (P(gcp)|curses.A_BOLD)
            for i, line in enumerate(art):
                _p(scr, H, W, ART_Y+1+i, ART_X, line, sprite_attr)
            if cs:
                badge = ' ✦ LOCKED ✦ '
                bx = box_x + 1 + (aw - len(badge)) // 2
                by = ART_Y + ah // 2
                _p(scr, H, W, by, bx, badge, P(5)|curses.A_BOLD|curses.A_REVERSE)
            # CRITICAL: advance ART_Y past the box so the description below
            # doesn't overdraw it (was the cause of "demos not showing up").
            ART_Y += ah + 1

    # Description
    DESC_X = DET_X + 2
    _p(scr, H, W, ART_Y,   DESC_X, 'ABOUT', P(gcp)|curses.A_BOLD)
    _p(scr, H, W, ART_Y,   DESC_X+8, '─'*max(0, DET_W-10), P(5)|curses.A_DIM)
    for i, line in enumerate(g['desc']):
        if ART_Y+1+i < H-5:
            _p(scr, H, W, ART_Y+1+i, DESC_X, f'• {line}', P(5))

    # Controls
    CTRL_Y = ART_Y + len(g['desc']) + 2
    if CTRL_Y < H - 5:
        _p(scr, H, W, CTRL_Y, DET_X+2, 'CONTROLS', P(5)|curses.A_BOLD)
        _p(scr, H, W, CTRL_Y, DET_X+12, '─'*max(0, DET_W-12), P(5)|curses.A_DIM)
        for i, ctrl in enumerate(g['controls']):
            ky, rest = ctrl.split(None, 1) if ' ' in ctrl else (ctrl, '')
            cy = CTRL_Y + 1 + i
            if cy >= H-4: break
            _p(scr, H, W, cy, DET_X+4, ky, P(gcp)|curses.A_BOLD)
            pad = 14 - len(ky)
            _p(scr, H, W, cy, DET_X+4+len(ky)+max(1,pad), rest, P(5))

    # Launch prompt (blinking) — different message for coming-soon games
    if (tick // 15) % 2 == 0:
        if g.get('coming_soon'):
            lp = f'★ COMING SOON ★  {g["name"]}'
            attr = P(5)|curses.A_BOLD|curses.A_REVERSE
        else:
            lp = f'[ ENTER ]  Launch  {g["name"]}'
            attr = P(gcp)|curses.A_BOLD|curses.A_REVERSE
        lx = DET_X + (DET_W - len(lp)) // 2
        _p(scr, H, W, H-4, lx, lp, attr)

    # ── Footer ──────────────────────────────────────────────────────────────
    _p(scr, H, W, H-3, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    foot = f'  ↑↓  Select     ENTER  Launch     Q  Quit              {len(GAMES)} GAMES  ·  Claudcade v1.0'
    _p(scr, H, W, H-2, 2, foot, P(5))

    scr.refresh()

# ── ARCADE MAIN ────────────────────────────────────────────────────────────────
_launch_script = None

def arcade_main(scr):
    global _launch_script
    curses.cbreak(); curses.noecho(); scr.keypad(True)
    scr.nodelay(True); curses.curs_set(0)
    setup_colors()
    try: curses.mousemask(0)  # disable mouse for the launcher
    except curses.error: pass

    cursor = 0
    nxt    = time.perf_counter()
    tick   = 0

    while True:
        now = time.perf_counter()
        if now < nxt: time.sleep(max(0, nxt-now-0.001)); continue
        nxt += 1/60; tick += 1

        H, W = scr.getmaxyx()
        keys = set()
        while True:
            k = scr.getch()
            if k == -1: break
            keys.add(k)

        UP   = curses.KEY_UP   in keys or ord('w') in keys
        DOWN = curses.KEY_DOWN in keys or ord('s') in keys
        OK   = any(k in keys for k in (ord('\n'), 10, 13, ord(' ')))
        QUIT = ord('q') in keys or ord('Q') in keys or 27 in keys

        if UP:   cursor = (cursor-1) % len(GAMES)
        if DOWN: cursor = (cursor+1) % len(GAMES)
        if QUIT: _launch_script = None; break
        if OK:
            if GAMES[cursor].get('coming_soon'):
                # Don't launch; just buzz visually next loop
                continue
            _launch_script = GAMES[cursor]['script']
            break

        draw_main(scr, H, W, tick, cursor)

def run():
    global _launch_script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    while True:
        try:
            curses.wrapper(arcade_main)
        except curses.error:
            print('\n  ERROR: Curses terminal support failed')
            print('  This usually means you\'re not in a proper interactive terminal.\n')
            print('  To play Claudcade, run it in a tmux session:')
            print('    $ tmux')
            print('    $ python3 claudcade.py\n')
            break
        except KeyboardInterrupt:
            print('\n  Thanks for playing — Claudcade\n')
            break

        if _launch_script is None:
            print('\n  Thanks for playing — Claudcade\n')
            break
        # Rename the tmux window to the launching game so it's obvious which
        # game is running when switching between tmux windows. Restored to
        # CLAUDCADE on return. Best-effort: no-op outside tmux.
        game_name = next((g['name'] for g in GAMES
                          if g.get('script') == _launch_script), _launch_script)
        if os.environ.get('TMUX'):
            subprocess.run(['tmux', 'rename-window', game_name],
                           check=False, capture_output=True)
        script = os.path.join(script_dir, _launch_script)
        subprocess.run([sys.executable, script], cwd=script_dir)
        if os.environ.get('TMUX'):
            subprocess.run(['tmux', 'rename-window', 'CLAUDCADE'],
                           check=False, capture_output=True)

if __name__ == '__main__':
    run()
