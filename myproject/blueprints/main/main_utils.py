

def find_first_missing_session_number(lst):
    try:
        return sorted(set(range(1, 4)) - set(lst))[0]
    except IndexError:
        return False
    
def get_column_widths(player_count):
    column_widths = {}
    column_widths['player_column'] = int(12 / player_count)
    if column_widths['player_column'] < 6:
        column_widths['box_column'] = 12
    else:
        column_widths['box_column'] = 6
    return column_widths