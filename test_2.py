

TMP_NUM = '000'


class Pokemon():
    def __init__(self, id, number, name):
        self.id = id
        self.number = number
        self.name = name

    def __repr__(self) -> str:
        return f"id={self.id}, number={self.number}, name={self.name}"



def main() -> None:
    mon_1 = Pokemon(1, '1', 'Bulbasaur')
    mon_2 = Pokemon(2, '2', 'Ivysaur')
    mon_3 = Pokemon(3, '3', 'Venusaur')
    mon_4 = Pokemon(4, '4', 'Charmander')
    mon_5 = Pokemon(5, '5', 'Charmeleon')
    mon_6 = Pokemon(6, '6', 'Charizard')
    mon_7 = Pokemon(7, '7', 'Caterpie')
    mon_8 = Pokemon(8, '8', 'Weedle')

    numbers_to_update = [{'new':'6', 'old':'5', 'obj':mon_5},
                         {'new':'4', 'old':'6', 'obj':mon_6},
                         {'new':'8', 'old':'7', 'obj':mon_7},
                         {'new':'5', 'old':'4', 'obj':mon_4},
                         {'new':'7', 'old':'8', 'obj':mon_8},
                         {'new':'9', 'old':'1', 'obj':mon_1}]
    
    number_sequence = get_number_change_seq(numbers_to_update)
    print(number_sequence)

def get_number_change_seq(numbers_to_update):
    updater_dict = {blueprint['old']:blueprint['new'] for blueprint in numbers_to_update}
    update_sequence = []
    print(updater_dict)
    while len(updater_dict) > 0:
        old = list(updater_dict)[0]
        updater_dict, update_sequence = recur_num(starter_number=old, 
                    check_number=old,
                    updater_dict=updater_dict,
                    update_sequence=update_sequence)
        if TMP_NUM in updater_dict:
            update_sequence.append({TMP_NUM:updater_dict[TMP_NUM]})
            updater_dict.pop(TMP_NUM)

    return update_sequence


def recur_num(starter_number, check_number, updater_dict, update_sequence):
    if updater_dict[check_number] == starter_number:
        update_sequence.append({check_number:TMP_NUM})
        updater_dict[TMP_NUM] = starter_number
        updater_dict[check_number] = TMP_NUM
        updater_dict.pop(check_number)
        return updater_dict, update_sequence
    elif updater_dict[check_number] in updater_dict:
        updater_dict, update_sequence = recur_num(starter_number, updater_dict[check_number], updater_dict, update_sequence)
    update_sequence.append({check_number:updater_dict[check_number]})
    updater_dict.pop(check_number)
    
    return updater_dict, update_sequence


if __name__ == '__main__':
    main()