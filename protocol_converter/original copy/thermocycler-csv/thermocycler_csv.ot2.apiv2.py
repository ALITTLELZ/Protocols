import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/thermocycler-csv/thermocycler_csv.ot2.apiv2.py"

metadata = {
    'protocolName': 'Thermocycler Example Protocol',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.0'
    }


def run(protocol):
    [well_vol, lid_temp, input_csv, final_temp, open_lid,
        deactivate_mod] = get_values(  # noqa: F821
            'well_vol', 'lid_temp', 'input_csv', 'final_temp', 'open_lid',
            'deactivate_mod')

    # ex_prof = """cycle,repetitions,"steps (temperature, time in minutes)",,
    # 1,1,"96, 30",,
    # 2,30,"96, 15","60, 30","74, 30"
    # 3,1,"74, 30",,"""
    #
    # [well_vol, lid_temp, input_csv, final_temp, open_lid, deactivate_mod] = [
    #     20, 105, ex_prof, 4, True, True]

    # load thermocycler
    tc_mod = protocol.load_module('thermocycler')

    """
    Add liquid transfers here, if interested (make sure TC lid is open)
    Example (Transfer 50ul of Sample from plate to Thermocycler):

    tips = [protocol.load_labware('opentrons_96_tiprack_300ul', '2')]
    pipette = protocol.load_instrument('p300_single', 'right', tip_racks=tips)
    tc_plate = tc_mod.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')
    sample_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '1')

    tc_wells = tc_plate.wells()
    sample_wells = sample_plate.wells()

    if tc_mod.lid_position != 'open':
        tc_mod.open_lid()

    for t, s in zip(tc_wells, sample_wells):
        pipette.transfer(50, s, t)
    """

    # parse profile input
    profiles_parsed = [
        line.split(',')
        for line in input_csv.splitlines()[1:] if line
        and line.split(',')[0].strip()
    ]

    profiles = [
        {'cycles': int(prof[1]), 'temps': [set for set in prof[2:] if set]}
        for prof in profiles_parsed if len(prof) > 1
    ]
    for p in profiles:
        print(p)

    # Close lid
    if tc_mod.lid_position != 'closed':
        tc_mod.close_lid()

    # lid temperature set
    tc_mod.set_lid_temperature(lid_temp)

    # run profile
    for profile in profiles:
        set = [
            {
                'temperature': float(temp.split(';')[0]),
                'hold_time_minutes': float(temp.split(';')[1])
            }
            for temp in profile['temps']
        ]
        tc_mod.execute_profile(
            steps=set, repetitions=profile['cycles'],
            block_max_volume=well_vol)

    # reach final temperature
    tc_mod.deactivate_lid()
    tc_mod.set_block_temperature(final_temp)

    if open_lid:
        tc_mod.open_lid()

    if deactivate_mod:
        tc_mod.deactivate_block()

    from opentrons.protocol_api.labware import Well, Labware
    import re
    import json
    all_vars = locals()

    # Wells that have been processed 
    processed_wells = set()
    liquid_locations = {}

    for var_name, var_value in all_vars.items():
        if isinstance(var_value, list) and len(var_value) > 0 and isinstance(var_value[0], Well):
            for i, well in enumerate(var_value):
                processed_wells.add(well)   
                display_name = well.display_name
                well_position = display_name.split(" of ")[0] if " of " in display_name else "unknown"
                slot_match = re.search(r" on (\d+)$", display_name)
                slot_number = slot_match.group(1) if slot_match else "unknown"
                name_with_index = f"{var_name}[{i}]"
                liquid_locations[name_with_index] = {
                    "well": well_position,
                    "slot": slot_number
                }

    for var_name, var_value in all_vars.items():
        if isinstance(var_value, Well):
            if var_value in processed_wells:
                continue
            
            display_name = var_value.display_name
            well_position = display_name.split(" of ")[0] if " of " in display_name else "unknown"
            slot_match = re.search(r" on (\d+)$", display_name)
            slot_number = slot_match.group(1) if slot_match else "unknown"
            liquid_locations[var_name] = {
                "well": well_position,
                "slot": slot_number
            }
    filename = f"detailed_action_json/thermocycler-csv.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)