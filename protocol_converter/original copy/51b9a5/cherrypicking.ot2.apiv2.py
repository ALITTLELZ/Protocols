import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/51b9a5/cherrypicking.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Agar Plating',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.10'
}


def run(ctx):

    [num_plates, num_samples, transfer_vol, source_plate, pipette_type,
     pipette_mount, tip_type, puncture_agar,
     puncture_depth, mix_sources] = get_values(  # noqa: F821
        'num_plates', 'num_samples', 'transfer_vol', 'source_plate',
        'pipette_type', 'pipette_mount', 'tip_type', 'puncture_agar',
        'puncture_depth', 'mix_sources')

    tiprack20 = ctx.load_labware(tip_type, '1', '20µl tiprack')
    source_plate = ctx.load_labware(source_plate, '2', 'source plate')
    agar_plates = [
        ctx.load_labware('nunc_rectangular_agar_plate', slot,
                         'agar plate ' + str(i+1))
        for i, slot in enumerate(
            ['3', '4', '5', '6', '7', '8', '9', '10', '11'])]

    p20 = ctx.load_instrument(pipette_type, pipette_mount,
                              tip_racks=[tiprack20])
    if p20.type == 'single':
        sources = source_plate.wells()[:num_samples]
        dest_sets = [
            [plate.wells()[i] for plate in agar_plates]
            for i in range(num_samples)]
    else:
        num_cols = math.ceil(num_samples/8)
        sources = source_plate.rows()[0][:num_cols]
        dest_sets = [
            [plate.rows()[0][i] for plate in agar_plates]
            for i in range(num_cols)]

    for source, dest_set in zip(sources, dest_sets):
        p20.pick_up_tip()
        for i, d in enumerate(dest_set):
            if i == 0 and mix_sources:
                p20.mix(5, 10, source)
            p20.aspirate(transfer_vol, source)
            if puncture_agar:
                p20.move_to(d.bottom(-1*puncture_depth))
            p20.dispense(transfer_vol, d.bottom())
        p20.drop_tip()

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
    filename = f"detailed_action_json/51b9a5.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)