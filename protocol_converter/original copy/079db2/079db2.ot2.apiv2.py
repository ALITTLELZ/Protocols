import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/079db2/079db2.ot2.apiv2.py"

metadata = {
    'protocolName': 'Reformatting with Custom Tube Rack',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [num_samp, volume, p300_mount] = get_values(  # noqa: F821
        "num_samp", "volume", "p300_mount")

    if not 1 <= num_samp <= 86:
        raise Exception("Enter a sample number between 1-86")

    # labware

    tuberacks = [ctx.load_labware('custom_24_tuberack', slot)
                 for slot in [1, 2, 3, 4]]
    plate = ctx.load_labware('nest_96_wellplate_2ml_deep', 6)
    tips = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
            for slot in [8]]

    # pipettes
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount, tip_racks=tips)

    # mapping
    source_wells = [tube for rack in tuberacks
                    for row in rack.rows() for tube in row][:num_samp]
    dest_wells = [well for row in plate.rows() for well in row][10:]

    # protocol
    ctx.comment('\n---------------ADDING SAMPLE TO PLATE----------------\n\n')
    for s, d in zip(source_wells, dest_wells):
        p300.pick_up_tip()
        p300.aspirate(volume, s)
        p300.dispense(volume, d)
        p300.drop_tip()
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
    filename = f"detailed_action_json/079db2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)