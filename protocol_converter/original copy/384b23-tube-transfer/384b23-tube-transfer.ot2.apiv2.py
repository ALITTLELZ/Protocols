import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/384b23-tube-transfer/384b23-tube-transfer.ot2.apiv2.py"

metadata = {
    'protocolName': 'Custom Tube to Tube transfer',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(ctx):

    [num_samp, delay, asp_height_recipient,
     disp_height_dest, p1000_mount] = get_values(  # noqa: F821
            "num_samp", "delay", "asp_height_recipient",
            "disp_height_dest", "p1000_mount")

    if not 1 <= num_samp <= 24:
        raise Exception("Enter a sample number between 1-24")

    # load labware
    source_tube_rack = ctx.load_labware("6x4_0.6inch_t6", '1',
                                        label='Source Tube Rack')
    dest_tube_rack = ctx.load_labware("6x5_half_inch_t1_t3", '2',
                                      label='Dest Tube Rack')
    tiprack1000 = ctx.load_labware('opentrons_96_tiprack_1000ul', '3')

    # load instrument
    p1000 = ctx.load_instrument('p1000_single_gen2',
                                p1000_mount, tip_racks=[tiprack1000])

    dest_tubes = [tube for row in dest_tube_rack.rows() for tube in row[:4]]

    for s, d in zip(source_tube_rack.wells()[:num_samp], dest_tubes):
        p1000.pick_up_tip()
        p1000.aspirate(500, s.bottom(asp_height_recipient))
        ctx.delay(seconds=delay)
        p1000.dispense(500, d.bottom(disp_height_dest))
        p1000.drop_tip()
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
    filename = f"detailed_action_json/384b23-tube-transfer.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)