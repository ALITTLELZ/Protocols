import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/298069/sample_aliquotting.ot2.apiv2.py"

import math

# metadata
metadata = {
    'protocolName': 'Sample Aliquoting',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(ctx):

    # parameters
    [p1000_mount] = get_values(  # noqa: F821
        'p1000_mount')

    # labware
    rack15 = ctx.load_labware(
        'opentrons_15_tuberack_falcon_15ml_conical', '1', '15ml tuberack')
    rack2 = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '2',
        '2ml tuberack')
    tiprack1000 = ctx.load_labware(
        'opentrons_96_tiprack_1000ul', '4', '1000ul tiprack')

    # pipettes
    p1000 = ctx.load_instrument(
        'p1000_single_gen2', p1000_mount, tip_racks=[tiprack1000])

    # setup
    srcs = {
        rack15.columns()[0][0]: 60,
        rack15.columns()[0][1]: 60
    }
    dest_sets = [
        [well for row in rack2.rows()[i*2:i*2+2] for well in row]
        for i in range(2)
    ]

    def h_track(src, dv):
        dh = (dv/(math.pi*(src.diameter/2)**2))*1.05
        h = srcs[src]
        srcs[src] = h - dh if h - dh >= 10 else 10
        return src.bottom(srcs[src])

    # perform transfers
    for s, dest_set in zip(srcs, dest_sets):
        p1000.pick_up_tip()
        for i in range(4):
            p1000.distribute(
                300,
                h_track(s, 900),
                [d.top() for d in dest_set[i*3:i*3+3]],
                disposal_vol=0,
                new_tip='never'
            )
            if i < 3:
                p1000.blow_out(s.top())
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
    filename = f"detailed_action_json/298069.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)