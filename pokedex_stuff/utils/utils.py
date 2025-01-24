TMP_NUM = '000'


def number_change_all(numbers_to_update) -> None:
    
    updater_dict = {blueprint['old']:blueprint['new'] for blueprint in numbers_to_update}
    popper_dict = {key:'' for key in updater_dict.keys()}
    while len(popper_dict) > 0:
        for old_number, new_number in updater_dict.items():
            if new_number in updater_dict:
                updater_dict = recursive_number_change(starter_number=old_number, 
                                                       saved_number=False, 
                                                       updater_dict=updater_dict,
                                                       popper_dict=popper_dict)
                break
            else:
                number_change_db_updates(pokemon)
                popper_dict.pop(old_number)


def recursive_number_change(starter_number, saved_number, updater_dict, popper_dict):
    if saved_number == starter_number:
        updater_dict[TMP_NUM] = updater_dict[starter_number].copy()
        updater_dict[TMP_NUM]['old'] = TMP_NUM
        updater_dict[saved_number]['new'] = TMP_NUM
        popper_dict[TMP_NUM] = ''
        number_change_db_updates(updater_dict[saved_number])
        popper_dict.pop(starter_number)
        return popper_dict, updater_dict
    if saved_number == False:
        saved_number = starter_number
    if updater_dict[saved_number]['new'] in updater_dict:
        updater_dict = recursive_number_change(starter_number, updater_dict[saved_number]['new'], updater_dict, popper_dict)
        if saved_number == starter_number:
            number_change_db_updates(updater_dict[TMP_NUM])
            popper_dict.pop(TMP_NUM)
        else:
            print(saved_number)
            print(updater_dict[saved_number])
            number_change_db_updates(updater_dict[saved_number])
            popper_dict.pop(saved_number)
    else:
        number_change_db_updates(updater_dict[saved_number])
        popper_dict.pop(saved_number)

    # print("NUMBERS TO UPDATE")
    # print(numbers_to_update)
    # print("UPDATER DICT")
    # print(updater_dict)
    return popper_dict, updater_dict
    
    
def number_change_db_updates(blueprint) -> None:
    # ADD FAMILY CHANGE AS WELL
    blueprint['obj'].number = blueprint['new']
    for fusion in blueprint['obj'].fusions_head:
        print(fusion)
    for fusion in blueprint['obj'].fusions_body:
        print(fusion)
    fusions_numbers_to_update = blueprint['obj'].fusions_head + blueprint['obj'].fusions_body
    for fusion in fusions_numbers_to_update:
        fusion.number = f"{fusion.head.number}.{fusion.body.number}"
    for fusion in blueprint['obj'].fusions_head:
        print(fusion)
    for fusion in blueprint['obj'].fusions_body:
        print(fusion)
    print(f"{blueprint['old']} -> {blueprint['new']}")
    # print("Base")
    # print(blueprint['obj'])
    # fusions = blueprint['obj'].fusions_head + blueprint['obj'].fusions_body
    # print("Fusions")
    # for fusion in fusions:
    #     print(fusion)