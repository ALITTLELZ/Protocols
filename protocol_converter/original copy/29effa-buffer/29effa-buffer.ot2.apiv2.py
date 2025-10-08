import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/29effa-buffer/29effa-buffer.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Lyra Direct Covid-19 Buffer Distribution',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(protocol):
    [p300mnt, num_wells] = get_values(  # noqa: F821
     'p300mnt', 'num_wells')

    # load labware and pipette
    tips = [protocol.load_labware('opentrons_96_tiprack_300ul', '1')]
    m300 = protocol.load_instrument('p300_multi_gen2', p300mnt, tip_racks=tips)

    plate = protocol.load_labware('eppendorf_96_wellplate_1000ul', '4')
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', '7')

    # variables
    buffers = [well for well in reservoir.wells()[:4] for _ in range(3)]
    num_cols = math.ceil(num_wells/8)
    wells = plate.rows()[0][:num_cols]

    # transfers
    m300.pick_up_tip()

    for buffer, well in zip(buffers, wells):
        for _ in range(2):
            m300.aspirate(200, buffer)
            m300.dispense(200, well)
        m300.blow_out(well.bottom(1))

    m300.drop_tip()

    protocol.comment('Protocol Complete!')

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
    filename = f"detailed_action_json/29effa-buffer.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)