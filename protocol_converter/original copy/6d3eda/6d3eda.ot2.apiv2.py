import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/6d3eda/6d3eda.ot2.apiv2.py"

from opentrons import protocol_api

metadata = {"apiLevel": "2.5"}


def run(ctx):
    # Add tip tracking to this protocol
    count, volume, input_labware, output_labware = get_values(  # noqa: F821
            'sample_count', 'volume', 'input_labware', 'output_labware')
    sample_plates = [ctx.load_labware(input_labware, '2')]
    target_plates = [ctx.load_labware(output_labware, '5')]
    tip_racks = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '1')]
    if count > 24:
        sample_plates.append(ctx.load_labware(input_labware, '3'))
        target_plates.append(ctx.load_labware(output_labware, '6'))

    # Variable pipettes?
    p300s = ctx.load_instrument(
            'p300_single_gen2', "right", tip_racks=tip_racks)

    for i, sample_plate in enumerate(sample_plates):
        for well_num, well in enumerate(sample_plate.wells()[:count-(i*24)]):
            try:
                p300s.pick_up_tip()
            except protocol_api.labware.OutOfTipsError:
                ctx.pause("Replace the tips")
                p300s.reset_tipracks()
                p300s.pick_up_tip()
            p300s.transfer(volume, well, target_plates[i].wells()[well_num],
                           blow_out=True, new_tip='never')
            p300s.drop_tip()

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
    filename = f"detailed_action_json/6d3eda.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)