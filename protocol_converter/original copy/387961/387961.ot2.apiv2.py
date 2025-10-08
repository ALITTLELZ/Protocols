import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/387961/387961.ot2.apiv2.py"

metadata = {
    'protocolName': 'Plate Filling with Custom 384-Well Plate',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(protocol):

    # labware
    plate384 = protocol.load_labware('flipped_384_plate', '3')
    srcplate = protocol.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt', '5')
    tips = protocol.load_labware('opentrons_96_tiprack_20ul', '1')

    pip = protocol.load_instrument('p20_multi_gen2', 'right', tip_racks=[tips])

    mm_loc = {
        'A1': ['B'+str(i) for i in range(1, 5)],
        'A2': ['A'+str(i) for i in range(1, 5)],
        'A3': ['B'+str(i) for i in range(5, 9)],
        'A4': ['A'+str(i) for i in range(5, 9)],
        'A5': ['A'+str(i) for i in range(9, 13)],
        'A6': ['B'+str(i) for i in range(9, 13)],
        'A7': ['A'+str(i) for i in range(13, 17)],
        'A8': ['B'+str(i) for i in range(13, 17)]
        }

    for i in range(1, 9):
        pip.pick_up_tip()
        tip_vol = 0
        for well in mm_loc['A'+str(i)]:
            if tip_vol == 0:
                pip.aspirate(20, srcplate['A'+str(i)])
                tip_vol = 20
            pip.dispense(10, plate384[well])
            tip_vol -= 10
        pip.drop_tip()

    tip_vol = 0
    pip.pick_up_tip()
    for well in plate384.rows()[10]:
        if tip_vol == 0:
            pip.aspirate(20, srcplate['A11'])
            tip_vol = 20
        pip.dispense(10, well)
        tip_vol -= 10

    for well in plate384.rows()[11]:
        if tip_vol == 0:
            pip.aspirate(20, srcplate['A12'])
            tip_vol = 20
        pip.dispense(10, well)
        tip_vol -= 10

    pip.drop_tip()

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
    filename = f"detailed_action_json/387961.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)