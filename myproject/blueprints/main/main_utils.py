from ...extensions import db
from ...models import User, Player, Pokedex, Pokemon, Save, Artist, RouteList, SoulLink, Route
from ...utils import func_timer

def missing_numbers(lst, option):
    try:
        missing_lst = sorted(set(range(1, 4)) - set(lst))
        if option == 'first':
            return missing_lst[0]
        elif option == 'all':
            return missing_lst
        else:
            raise Exception("missing_numbers requires an option of 'first' or 'all'")
    except IndexError:
        return None
    
def get_column_widths(player_count):
    column_widths = {}
    column_widths['player_column'] = int(12 / player_count)
    if column_widths['player_column'] < 6:
        column_widths['box_column'] = 12
    else:
        column_widths['box_column'] = 6
    return column_widths

