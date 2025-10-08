import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7e4c3e-2/7e4c3e-2.ot2.apiv2.py"

import math
metadata = {'apiLevel': '2.0'}


def run(ctx):

    num_samples, tip_start = [96, "A1"]

    num_samples, tip_start = get_values(  # noqa: F821
            'num_samples', 'tip_start')
    column_count = math.ceil(num_samples / 8)

    p20m_racks = [
        ctx.load_labware(
            "opentrons_96_filtertiprack_20ul",
            x) for x in [
            "2",
            "3"]]
    p20m = ctx.load_instrument(
        'p20_multi_gen2',
        'right',
        tip_racks=p20m_racks)

    biorad_96_well = ctx.load_labware(
        "opentrons_96_aluminumblock_biorad_wellplate_200ul", "4")
    b_cols = biorad_96_well.rows()[0][:column_count]
    pcr_strip = ctx.load_labware(
        "opentrons_96_aluminumblock_generic_pcr_strip_200ul", "5")

    p20m.starting_tip = p20m_racks[0].well(tip_start)
    for cols, target_well in zip([b_cols[:6], b_cols[6:]], [
                                pcr_strip.wells_by_name()[x] for x in ["A1", "A2"]]):  # noqa: E501
        for col in cols:
            p20m.transfer(20, col, target_well)

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
    filename = f"detailed_action_json/7e4c3e-2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)