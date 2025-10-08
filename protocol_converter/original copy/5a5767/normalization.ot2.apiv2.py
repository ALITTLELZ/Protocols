import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/5a5767/normalization.ot2.apiv2.py"

import math

metadata = {
    'protocolName': '384-well Plate One-to-One Transfer',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.2'
    }


def run(ctx):
    [p50_mount, dest_plate_type, num_samples,
     transfer_vol] = get_values(  # noqa: F821
        'p50_mount', 'dest_plate_type', 'num_samples', 'transfer_vol')

    # labware
    dest_plate = ctx.load_labware(dest_plate_type, '1', 'destination plate')
    source_plate = ctx.load_labware('greinerbioone_384_wellplate_100ul', '6',
                                    'source plate')
    tipracks300 = [
        ctx.load_labware('opentrons_96_tiprack_300ul', slot)
        for slot in ['7', '8', '10', '11']]

    # pipette
    m50 = ctx.load_instrument('p50_multi', p50_mount, tip_racks=tipracks300)

    # setup sources and destinations
    num_cols = math.ceil(num_samples/8)
    sources, dests = [
        [well for row in plate.rows()[:2] for well in row][:num_cols]
        for plate in [source_plate, dest_plate]]

    m50.transfer(transfer_vol, sources, dests, new_tip='always')

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
    filename = f"detailed_action_json/5a5767.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)