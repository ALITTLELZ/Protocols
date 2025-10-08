import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/sci-phytip-neutralization/neutralization.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Phytip Protein A, ProPlus, ProPlus LX Columns -  Neutralization',
    'author': 'Opentrons <protocols@opentrons.com>',
    'apiLevel': '2.11'
}


# for Elution buffer 80 uL, add Neutralization buffer 20 uL;
# for Elution buffer 100 uL, add Neutralization buffer 25 uL


def run(ctx):

    num_samples, vol_neutralization_buffer = get_values(  # noqa: F821
        'num_samples', 'vol_neutralization_buffer')

    num_cols = math.ceil(num_samples/8)

    tiprack = ctx.load_labware(
        'opentrons_96_tiprack_300ul', '6', '300ul opentrons tiprack')

    elution_plate = ctx.load_labware(
        'thermoscientific_96_wellplate_v_450', '11', 'elute plate')
    tuberack = ctx.load_labware(
        'opentrons_15_tuberack_nest_15ml_conical', '10', 'elution buffer')

    neutral_buffer = tuberack.rows()[0][4]

    s300 = ctx.load_instrument(
        'p300_single_gen2', 'right', tip_racks=[tiprack])

    # neutralization)
    s300.pick_up_tip()
    for col in range(num_cols):
        s300.blow_out(neutral_buffer)
        s300.aspirate(vol_neutralization_buffer*9, neutral_buffer, rate=0.5)
        for i in range(8):
            well = elution_plate.rows()[i][col]
            s300.dispense(vol_neutralization_buffer, well.top(1), rate=0.5)
            s300.touch_tip()
    s300.drop_tip()

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
    filename = f"detailed_action_json/sci-phytip-neutralization.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)