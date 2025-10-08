import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/063611-part-2/063611-part-2.ot2.apiv2.py"

metadata = {
    'title': 'Custom Tiprack Reformatting',
    'author': 'Steve Plonk',
    'apiLevel': '2.10'
}


def run(ctx):

    [box_count] = get_values(  # noqa: F821
        "box_count")

    ctx.set_rail_lights(True)
    ctx.delay(seconds=10)

    """
    This script puts tips into a custom arrangement required
    for use of a multi-channel pipette with only four tips attached
    (on alternating nozzles).
    """
    # p300 multi, full tip boxes, empty tip boxes
    tips300 = [ctx.load_labware('opentrons_96_tiprack_300ul', str(
     slot), 'FULL TIPRACK') for slot in [7, 8, 9][:int(box_count / 2)]]
    p300m = ctx.load_instrument("p300_multi_gen2", 'right', tip_racks=tips300)

    empty300 = [ctx.load_labware('opentrons_96_tiprack_300ul', str(
     slot), 'EMPTY TIPRACK') for slot in [4, 5, 6][:int(box_count / 2)]]

    for full, empty in zip(tips300, empty300):
        for index, column in enumerate(full.columns()):
            p300m.pick_up_tip(column[4])
            p300m.drop_tip(empty.columns()[index][4])

    for box in tips300+empty300:
        for column in box.columns():
            if box in empty300:
                p300m.pick_up_tip(column[4])
                p300m.drop_tip(column[0])
            for s in range(1, 6, 2):
                p300m.pick_up_tip(column[s])
                p300m.drop_tip(column[s+1])

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
    filename = f"detailed_action_json/063611-part-2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)