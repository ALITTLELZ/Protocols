import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/quintara_onsite_part1_384/quintara_onsite_part1_384.ot2.apiv2.py"

metadata = {
    'protocolName': '384 Plate to 96 Plate',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [p20_mount] = get_values(  # noqa: F821
        "p20_mount")

    # labware
    source_plate = ctx.load_labware('appliedbiosystem_384_wellplate_40ul', 1)
    dest_plate = ctx.load_labware('quintara_96_wellplate_300ul', 2)
    tips = [ctx.load_labware('opentrons_96_tiprack_20ul', slot)
            for slot in [10, 11, 7, 8]]

    # pipettes
    m20 = ctx.load_instrument('p20_multi_gen2', p20_mount, tip_racks=tips)

    # mapping
    all_source_wells = [
                        col
                        for i, j in zip([0, 0, 1, 1], [0, 1, 0, 1])
                        for col in source_plate.rows()[i][j::2]
                        ]

    chunked_source_cols = [all_source_wells[i:i+4]
                           for i in range(0, len(all_source_wells), 4)]

    for chunk, dest_col in zip(
                                  chunked_source_cols,
                                  dest_plate.rows()[0]
                                          ):

        for j, well in enumerate(chunk):
            if j == 0 or j == 3:
                vol = 20
            if j == 1 or j == 2:
                vol = 2
            m20.pick_up_tip()
            m20.aspirate(vol, well)
            m20.dispense(vol, dest_col)
            m20.return_tip()
        ctx.comment('\n\n')

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
    filename = f"detailed_action_json/quintara_onsite_part1_384.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)