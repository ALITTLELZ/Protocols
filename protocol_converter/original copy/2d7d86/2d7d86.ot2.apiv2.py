import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/2d7d86/2d7d86.ot2.apiv2.py"

metadata = {
    'protocolName': 'UTI Batch qPCR Setup',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [tip_start, m20_mount] = get_values(  # noqa: F821
        "tip_start", "m20_mount")

    if not 1 <= tip_start <= 12:
        raise Exception("Enter a column number between 1-12")

    # load labware
    source_plate = ctx.load_labware('thermofisherscientificdeepwell_96_wellplate_2000ul', 4)  # noqa: E501
    dest_plate = ctx.load_labware('thermofisher_384_wellplate_50ul', 5)
    tips = ctx.load_labware('opentrons_96_tiprack_20ul', 6)

    # load instrument
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount, tip_racks=[tips])

    tip_cols = [col for col in tips.rows()[0]][tip_start-1:]

    tip_pickups_by_col = [8, 8]

    for i, pickup in enumerate(tip_pickups_by_col):
        if pickup > 0:
            m20.pick_up_tip(tip_cols[i])
            for dest in dest_plate.rows()[i]:
                m20.aspirate(10, source_plate.rows()[0][i])
                m20.dispense(10, dest)
            m20.drop_tip()
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
    filename = f"detailed_action_json/2d7d86.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)