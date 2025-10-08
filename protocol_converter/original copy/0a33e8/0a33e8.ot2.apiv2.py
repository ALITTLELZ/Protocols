import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0a33e8/0a33e8.ot2.apiv2.py"

import math


metadata = {
    'protocolName': 'PCR Prep Deep Well to 384',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [num_samp, m20_mount] = get_values(  # noqa: F821
        "num_samp", "m20_mount")

    if not 1 <= num_samp <= 382:
        raise Exception("Enter a sample number 1-382")

    # load labware
    deepwell_plates = [ctx.load_labware(
                       'kingfisher_96_wellplate_2000ul',
                       slot) for slot in [4, 1, 5, 2]]

    final_plate = ctx.load_labware('thermofisher_384_wellplate_50ul', 3)
    tipracks = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
                for slot in [10, 7, 11, 8]]

    # load instrument
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount, tip_racks=tipracks)

    # mapping
    num_col = math.ceil(num_samp/8)
    samples = [col for plate in deepwell_plates for col in plate.rows()[0]]
    row_order = [0, 1, 0, 1]
    col_order = [0, 0, 1, 1]
    final_map = [col for row_start, col_start in zip(row_order, col_order)
                 for col in final_plate.rows()[row_start][col_start::2]]

    for source, dest in zip(samples[:num_col], final_map):
        m20.pick_up_tip()
        m20.aspirate(5, source, rate=0.5)
        m20.dispense(5, dest, rate=0.5)
        m20.blow_out()
        m20.drop_tip()
        ctx.comment('\n')

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
    filename = f"detailed_action_json/0a33e8.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)