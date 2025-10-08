import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/925d07-q/pcr_prep.ot2.apiv2.py"

import math

metadata = {
    'title': 'QIAcuity Plate Transfer',
    'author': 'Nick Diehl <ndiehl@opentrons.com>',
    'apiLevel': '2.11'
}


def run(ctx):

    num_samples, transfer_volume, m20_mount = get_values(  # noqa: F821
        'num_samples', 'transfer_volume', 'm20_mount')

    source_plate = ctx.load_labware('nest_96_wellplate_100ul_pcr_full_skirt',
                                    '1', 'source plate (NEST)')
    dest_plate = ctx.load_labware('qiacuity_96_wellplate_200ul', '2',
                                  'destination plate (QIAcuity)')
    tipracks20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', '4')]

    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount,
                              tip_racks=tipracks20)

    num_cols = math.ceil(num_samples/8)

    m20.flow_rate.aspirate = 5
    m20.flow_rate.dispense = 5

    for s, d in zip(source_plate.rows()[0][:num_cols],
                    dest_plate.rows()[0][:num_cols]):
        m20.transfer(transfer_volume, s.bottom(0.5), d.bottom(3))

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
    filename = f"detailed_action_json/925d07-q.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)