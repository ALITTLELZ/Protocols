import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/6bc986-part-4/6bc986-part-4.ot2.apiv2.py"

import math
from opentrons import types

metadata = {
    'protocolName': '3. Master Mix only-edit',
    'author': 'Steve Plonk <protocols@opentrons.com>',
    'apiLevel': '2.9'
}


def run(ctx):

    # get parameter values from json above
    [blowout_vertical_offset, clearance_aspirate, clearance_dispense,
     sample_count
     ] = get_values(  # noqa: F821
      'blowout_vertical_offset', 'clearance_aspirate', 'clearance_dispense',
      'sample_count')

    # constrain blowout_vertical_offset value to acceptable range
    if blowout_vertical_offset > 25 or blowout_vertical_offset < 0:
        raise Exception('''
        Vertical offset for blowout must be between 0 and 25 mm.''')

    num_cols = math.ceil(sample_count / 8)
    tip_max = 50

    # p50 multi, p20 multi and tips
    tips20 = [ctx.load_labware("opentrons_96_tiprack_20ul", '4')]
    tips300 = [ctx.load_labware("opentrons_96_tiprack_300ul", '1')]
    p20m = ctx.load_instrument(
        "p20_multi_gen2", 'right', tip_racks=tips20)
    p50m = ctx.load_instrument(
        "p50_multi", 'left', tip_racks=tips300)

    # thermo 96 well plate on slot 6
    dna_template = ctx.load_labware("thermo_96_wellplate_200ul", '6')
    p20m.transfer(0, dna_template.wells_by_name()[
     'A1'], dna_template.wells_by_name()['A1'], trash=False)

    # to satisfy linter
    p50m.transfer(0, dna_template.wells_by_name()[
     'A1'], dna_template.wells_by_name()['A1'], trash=False)

    # usa plate on slot 3
    usa_plate = ctx.load_labware("usa_96_wellplate_200ul", '3')

    # aspir8 reservoir in slot 2 with ghost movement to reservoir
    reservoir = ctx.load_labware("aspir8_1_reservoir_taped", '2')

    # to distribute and blow out with control over location within the well
    def create_chunks(list_name, n):
        for i in range(0, len(list_name), n):
            yield list_name[i:i+n]

    def repeat_dispense(dist_vol, source, dest, max_asp=tip_max, disposal=0):
        # chunk size math.floor((max_asp - disposal) / dist_vol) for multi disp
        for chunk in create_chunks(dest.columns()[
         :num_cols], 1):
            if disposal > 0:
                p20m.aspirate(disposal, source)
            p20m.aspirate(dist_vol*len(chunk), source)
            for column in chunk:
                p20m.dispense(dist_vol, column[0].bottom(clearance_dispense))
            # blowout changed to dispense of disposal volume to avoid bubbles
            p20m.dispense(disposal, source.move(types.Point(
             x=0, y=0, z=blowout_vertical_offset)))

    # 20 ul master mix to two columns, blow out to bottom of reservoir, repeat
    p20m.pick_up_tip()
    repeat_dispense(15, reservoir.wells_by_name()[
     'A1'].bottom(clearance_aspirate), usa_plate, disposal=5)
    p20m.drop_tip()

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
    filename = f"detailed_action_json/6bc986-part-4.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)