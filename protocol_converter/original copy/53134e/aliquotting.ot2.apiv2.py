import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/53134e/aliquotting.ot2.apiv2.py"

metadata = {
    'protocolName': 'Media Aliquotting',
    'author': 'Nick <ndiehl@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.3'
}


def run(ctx):
    [num_samples, transfer_vol, p1000_mount] = get_values(  # noqa: F821
        'num_samples', 'transfer_vol', 'p1000_mount')

    # labware
    source = ctx.load_labware('nest_1_reservoir_195ml', '1',
                              'liquid reservoir').wells()[0]
    tuberack = ctx.load_labware('custom_24_tuberack_2000ul', '2',
                                'custom tuberack')
    tiprack = [
        ctx.load_labware('opentrons_96_tiprack_1000ul', '4', '1000µl tiprack')]

    # pipette
    p1000 = ctx.load_instrument('p1000_single_gen2', p1000_mount,
                                tip_racks=tiprack)

    # perform transfers
    for d in tuberack.wells()[:num_samples]:
        for _ in range(2):
            p1000.pick_up_tip()
            p1000.transfer(
                transfer_vol, source, d, air_gap=50, new_tip='never')
            p1000.air_gap(50)
            p1000.drop_tip()

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
    filename = f"detailed_action_json/53134e.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)