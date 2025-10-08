import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/6bc986-part-2/6bc986-part-2.ot2.apiv2.py"

import math
from opentrons import types

metadata = {
    'protocolName': 'Apostle Prot. K',
    'author': 'Steve Plonk <protocols@opentrons.com>',
    'apiLevel': '2.9'
}


def run(ctx):

    # get parameter values from json above
    [clearance_aspirate, clearance_dispense, sample_count
     ] = get_values(  # noqa: F821
      'clearance_aspirate', 'clearance_dispense', 'sample_count')

    num_cols = math.ceil(sample_count / 8)
    tip_max = 50

    # p50 multi and tips
    tips300 = [ctx.load_labware("opentrons_96_tiprack_300ul", '4')]
    p50m = ctx.load_instrument(
        "p50_multi", 'left', tip_racks=tips300)

    # 96 deep well plate on slot 8
    deep_well_plate = ctx.load_labware("nest_96_wellplate_2ml_deep", '8')

    # aspir8 reservoir in slot 2
    reservoir = ctx.load_labware("aspir8_1_reservoir_taped", '2')

    # to distribute and blow out with control over location within the well
    def create_chunks(list_name, n):
        for i in range(0, len(list_name), n):
            yield list_name[i:i+n]

    def repeat_dispense(dist_vol, source, dest, max_asp=tip_max, disposal=0):
        for chunk in create_chunks(dest.columns()[
         :num_cols], math.floor((max_asp - disposal) / dist_vol)):
            if disposal > 0:
                p50m.aspirate(disposal, source)
            p50m.aspirate(dist_vol*len(chunk), source)
            for column in chunk:
                p50m.move_to(column[0].bottom(clearance_dispense))
                p50m.move_to(column[0].bottom(
                 clearance_dispense).move(types.Point(x=-1, y=0, z=1)))
                p50m.dispense(dist_vol)
            p50m.blow_out(source.move(types.Point(x=0, y=0, z=0)))

    # distribute 4 ul Prot. K to v-bottom deep wells
    p50m.pick_up_tip()
    repeat_dispense(4, reservoir.wells_by_name()['A1'].bottom(
     clearance_aspirate), deep_well_plate, disposal=5)
    p50m.drop_tip()

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
    filename = f"detailed_action_json/6bc986-part-2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)