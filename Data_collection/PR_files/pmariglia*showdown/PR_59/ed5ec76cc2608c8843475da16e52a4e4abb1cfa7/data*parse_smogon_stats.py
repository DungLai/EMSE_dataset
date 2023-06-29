import ntpath
import re
from datetime import datetime
from dateutil import relativedelta

import requests

import constants
from showdown.engine.helpers import normalize_name

OTHER_STRING = "other"
MOVES_STRING = "moves"
ITEM_STRING = "items"
SPREADS_STRING = "spreads"
ABILITY_STRING = "abilities"

PERCENTAGES_REGEX = '(\d+\.\d+%)'


def get_smogon_stats_file_name(game_mode, month_delta=1):
    """
    Gets the smogon stats url based on the game mode
    Uses the previous-month's statistics
    """

    # blitz comes and goes - use the non-blitz version
    if game_mode.endswith('blitz'):
        game_mode = game_mode[:-5]

    # always use the `-0` file - the higher ladder is for noobs
    smogon_url = "https://www.smogon.com/stats/{}-{}/chaos/{}-0.json"

    previous_month = datetime.now() - relativedelta.relativedelta(months=month_delta)
    year = previous_month.year
    month = "{:02d}".format(previous_month.month)

    return smogon_url.format(year, month, game_mode)


def get_pokemon_information(smogon_stats_url):
    r = requests.get(smogon_stats_url)
    if r.status_code == 404:
        r = requests.get(get_smogon_stats_file_name(ntpath.basename(smogon_stats_url.replace('-0.txt', '')), month_delta=2))
    infos = r.json()['data']
    final_infos = {}
    for x in infos.keys():
        spreads = []
        items = []
        moves = []
        abilities = []
        final_infos[normalize_name(x)] = {}
        for t in infos[x]['Spreads']:
            if float("{:.16f}".format(float(infos[x]['Spreads'][t]))) != 0:
                spreads.append((normalize_name(t.split(':')[0]), normalize_name(t.split(':')[1].replace('/', ',')), float("{:.16f}".format(float(100*(infos[x]['Spreads'][t]/infos[x]['Raw count']))))))
        for j in infos[x]['Items']:
            if infos[x]['Items'][j] != 0:
                items.append((j, 100*(infos[x]['Items'][j]/infos[x]['Raw count'])))
        for k in infos[x]['Moves']:
            if infos[x]['Moves'][k] != 0:
                moves.append((k, 100*(infos[x]['Moves'][k]/infos[x]['Raw count'])))
        for l in infos[x]['Abilities']:
            if infos[x]['Abilities'][l] != 0:
                abilities.append((l, 100*(infos[x]['Abilities'][l]/infos[x]['Raw count'])))
        final_infos[normalize_name(x)][SPREADS_STRING] = spreads
        final_infos[normalize_name(x)][ITEM_STRING] = items
        final_infos[normalize_name(x)][MOVES_STRING] = moves
        final_infos[normalize_name(x)][ABILITY_STRING] = abilities
    return final_infos
