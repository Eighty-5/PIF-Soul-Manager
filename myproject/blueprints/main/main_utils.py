

def find_first_missing_session_number(lst):
    try:
        return sorted(set(range(1, 4)) - set(lst))[0]
    except IndexError:
        return False