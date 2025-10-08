import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0a25f2/capsule_filling.ot2.apiv2.py"

from opentrons.types import Point

metadata = {
    'protocolName': 'Capsule Filling 3x Custom 10x10 Racks',
    'author': 'Nick <ndiehl@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.5'
}


def run(ctx):
    num_samples, transfer_vol, p1000_mount = get_values(  # noqa: F821
        'num_samples', 'transfer_vol', 'p1000_mount')

    # labware
    capsule_assembly = ctx.load_labware(
        'custom_300_other_100x500ul_100x500ul_100x500ul', '1')
    tiprack = ctx.load_labware('opentrons_96_tiprack_1000ul', '9')

    # pipette
    p1000 = ctx.load_instrument(
        'p1000_single_gen2', p1000_mount, tip_racks=[tiprack])
    p1000.pick_up_tip()

    capsules_reordered = []
    for x, top in enumerate([True, False]):
        blocks_inds = range(2) if True else range(1)
        for i in blocks_inds:
            for col in capsule_assembly.columns()[x*10:(x+1)*10]:
                for well in col[i*10:(i+1)*10]:
                    capsules_reordered.append(well)

    # transfer from reservoir in trash spot
    source = ctx.loaded_labwares[12].wells()[0].top().move(
        Point(x=0, y=0, z=-20))

    # perform transfers
    for cap in capsules_reordered[:num_samples]:
        p1000.aspirate(100, source.move(Point(z=20)))
        p1000.aspirate(transfer_vol, source)
        p1000.dispense(transfer_vol, cap.top(-1))
        p1000.dispense(p1000.current_volume, cap.top())
    p1000.return_tip()

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
    filename = f"detailed_action_json/0a25f2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)