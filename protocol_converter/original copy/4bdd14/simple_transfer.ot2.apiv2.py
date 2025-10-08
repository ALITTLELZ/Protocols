import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/4bdd14/simple_transfer.ot2.apiv2.py"

metadata = {
    'protocolName': 'Simple Plate Transfer - 4 Sources',
    'author': 'Nick <ndiehl@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.8'
}


def run(ctx):
    [m300_mount, num_plates] = get_values(  # noqa: F821
     'm300_mount', 'num_plates')

    # load labware
    tips300 = [ctx.load_labware('opentrons_96_tiprack_300ul', '1')]
    source_plate = ctx.load_labware('nest_96_wellplate_2ml_deep', '2',
                                    'source plate')
    dest_plates = [
        ctx.load_labware('greinermicrolon_96_wellplate_340ul', str(slot),
                         f'plate {i+1}')
        for i, slot in enumerate(range(3, 3+num_plates))]

    # load pipettes
    m300 = ctx.load_instrument('p300_multi', m300_mount, tip_racks=tips300)

    col_ind_sets = [[i, i+4, i+8] for i in range(4)]
    for i, ind_set in enumerate(col_ind_sets):
        m300.pick_up_tip()
        for c in ind_set:
            m300.distribute(50, source_plate.rows()[0][i],
                            [plate.columns()[c] for plate in dest_plates],
                            disposal_vol=0, new_tip='never')
        m300.drop_tip()

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
    filename = f"detailed_action_json/4bdd14.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)