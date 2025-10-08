import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/059126/059126.ot2.apiv2.py"

"""OPENTRONS."""
from opentrons import protocol_api
from opentrons.types import Point

metadata = {
    'protocolName': 'Reagent Addition',
    'author': 'Nick Diehl <ndiehl@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx: protocol_api.ProtocolContext):
    """PROTOCOL."""
    [
     num_384_cols,
     starting_tip_col_20,
     starting_tip_col_300,
     m20_mount,
     file_input
    ] = get_values(  # noqa: F821
        "num_384_cols",
        "starting_tip_col_20",
        "starting_tip_col_300",
        "m20_mount",
        "file_input")

    # define all custom variables above here with descriptions:
    if m20_mount == 'right':
        m300_mount = 'left'
    else:
        m300_mount = 'right'

    # load labware
    plate_96 = ctx.load_labware('greiner_96_wellplate_340ul', '4')
    plate_384 = ctx.load_labware('greiner_384_wellplate_50ul', '2')
    vials = ctx.load_labware('cytiva_24_wellplate_2000ul', '7')
    tiprack_300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
                   for slot in ['8']]
    tiprack_20 = [ctx.load_labware('opentrons_96_tiprack_20ul', slot)
                  for slot in ['9']]

    # load pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount,
                               tip_racks=tiprack_300)
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount,
                              tip_racks=tiprack_20)

    # parse .csv data
    data = [
        [val.strip() for val in line.split(',')]
        for line in file_input.splitlines()[1:]]

    m20.starting_tip = tiprack_20[0].columns()[starting_tip_col_20-1][0]

    tips_single_300 = [
        tip
        for rack in tiprack_300
        for col in rack.columns()[::-1]
        for tip in col[::-1]]
    starting_tip_300 = tiprack_300[0].columns()[starting_tip_col_300-1][-1]
    tips_single_300 = tips_single_300[tips_single_300.index(starting_tip_300):]

    counter_300 = 0

    def pick_up_300(mode='single'):
        nonlocal counter_300
        if mode == 'single':
            m300.pick_up_tip(tips_single_300[counter_300])
            counter_300 += 1
        else:
            m300.pick_up_tip()

    def wick(pip, well, side=1):
        pip.move_to(well.bottom().move(Point(x=side*well.diameter/2*0.8, z=3)))

    def slow_withdraw(well, pip=m300):
        ctx.max_speeds['A'] = 25
        ctx.max_speeds['Z'] = 25
        pip.move_to(well.top())
        del ctx.max_speeds['A']
        del ctx.max_speeds['Z']

    # transfer vial to 96-well plate
    for i, line in enumerate(data):
        source_vial = vials.wells_by_name()[line[0]]
        vol96 = float(line[1])
        pick_up_300('single')
        dest_col = plate_96.columns()[i]
        for well in dest_col:
            m300.aspirate(vol96, source_vial)
            slow_withdraw(source_vial, m300)
            m300.dispense(vol96, well.bottom(1.5))
            slow_withdraw(well, m300)
        m300.drop_tip()

    # transfer 96-well plate to 384-well plate
    dests_384 = [
        well for col in plate_384.columns()[:num_384_cols]
        for well in col[:2]]

    for i, line in enumerate(data):
        source_column = plate_96.rows()[0][i]
        vol384 = float(line[2])
        m20.pick_up_tip()
        for d in dests_384:
            m20.aspirate(vol384, source_column)
            slow_withdraw(source_column, m20)
            m20.dispense(vol384, d.bottom(0.5))
            wick(pip=m20, well=d)
        m20.drop_tip()

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
    filename = f"detailed_action_json/059126.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)