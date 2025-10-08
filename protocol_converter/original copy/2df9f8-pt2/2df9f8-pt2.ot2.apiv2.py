import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/2df9f8-pt2/2df9f8-pt2.ot2.apiv2.py"

"""Protocol."""
import math
metadata = {
    'protocolName': 'Plate Filling Heat Inactivated Covid Samples for PCR - Part 2',  # noqa: E501
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):
    """Protocol."""
    [num_samp, m20_mount] = get_values(  # noqa: F821
        'num_samp', 'm20_mount')

    if not 1 <= num_samp <= 96:
        raise Exception("Enter a number of samples between 1-96")

    if not num_samp % 8 == 0:
        raise Exception("Enter a number of samples which is divisible by 8")

    num_col = math.ceil(num_samp/8)

    # load labware
    source_plate = ctx.load_labware('nest_96_wellplate_2ml_deep', '1')
    final_plate = ctx.load_labware('nest_96_wellplate_2ml_deep', '2')
    tiprack = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
               for slot in ['3']]

    # load instrument
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount, tip_racks=tiprack)

    # protocol
    # distribute to inter plate
    airgap = 2
    for s, d in zip(source_plate.rows()[0], final_plate.rows()[0][:num_col]):
        m20.pick_up_tip()
        m20.aspirate(6, s)
        m20.touch_tip()
        m20.air_gap(airgap)
        m20.dispense(airgap, d.top())
        m20.dispense(6, d)
        m20.blow_out()
        m20.drop_tip()

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
    filename = f"detailed_action_json/2df9f8-pt2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)