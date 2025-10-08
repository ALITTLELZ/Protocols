import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/43d313-part-8/43d313-part-8.ot2.apiv2.py"

import math
from opentrons.protocol_api.labware import OutOfTipsError

metadata = {
    'protocolName': '''ArcBio RNA Workflow Continuous:
    Post-PCR Instrument: Library-QC''',
    'author': 'Steve Plonk <protocols@opentrons.com>',
    'apiLevel': '2.11'
}


def run(ctx):

    # get parameter values from json above
    [count_samples, clearance_reservoir, height_engage, time_engage, offset_x,
     time_dry] = get_values(  # noqa: F821
      'count_samples', 'clearance_reservoir', 'height_engage', 'time_engage',
      'offset_x', 'time_dry')

    ctx.set_rail_lights(True)

    if not 1 <= count_samples <= 96:
        raise Exception('Invalid sample count (must be 1-96).')

    num_cols = math.ceil(count_samples / 8)

    # helper functions

    # notify user to replenish tips
    def pick_up_or_refill(pip, vol=200):
        nonlocal tipCtr
        try:
            if vol == 200:
                pip.pick_up_tip()
            else:
                if tipCtr < len(tips300.rows()[0]):
                    pip.pick_up_tip(tips300.rows()[0][tipCtr])
                    tipCtr += 1
                else:
                    tipCtr = 0
                    ctx.pause(
                     """Please Refill the 300 uL Tip Box
                     and Empty the Tip Waste""")
                    pip.pick_up_tip(tips300.rows()[0][tipCtr])
                    tipCtr += 1
        except OutOfTipsError:
            ctx.pause(
             """Please Refill the {} Tip Boxes
             and Empty the Tip Waste""".format(pip))
            pip.reset_tipracks()
            pip.pick_up_tip()

    # set liquid volume
    def liq_volume(wells, vol):
        for well in wells:
            well.liq_vol = vol

    # return liquid height in a well
    def liq_height(well):
        if well.diameter is not None:
            radius = well.diameter / 2
            cse = math.pi*(radius**2)
        elif well.length is not None:
            cse = well.length*well.width
        else:
            cse = None
        if cse:
            return well.liq_vol / cse
        else:
            raise Exception("""Labware definition must
                supply well radius or well length and width.""")

    # tips, p20 multi, p300 multi
    tips20 = [ctx.load_labware(
     "opentrons_96_filtertiprack_20ul", str(slot)) for slot in [10, 11]]
    p20m = ctx.load_instrument(
        "p20_multi_gen2", 'left', tip_racks=tips20)
    tips200 = [
     ctx.load_labware(
      "opentrons_96_filtertiprack_200ul", str(slot)) for slot in [7, 8]]
    tips300 = ctx.load_labware("opentrons_96_tiprack_300ul", 9)
    tipCtr = 0
    p300m = ctx.load_instrument(
        "p300_multi_gen2", 'right', tip_racks=tips200)

    # Tapestation reagent in 8-tube strip
    reagents = ctx.load_labware(
     'opentrons_96_aluminumblock_generic_pcr_strip_200ul',
     '2', 'Tapestation Reagent')

    [tapestation_reagent] = [reagents.columns()[index] for index in [0]]

    # Qubit flextubes
    flextubeblocks = [ctx.load_labware(
     "opentrons_96_aluminumblock_generic_pcr_strip_200ul", str(
      slot)) for slot in [5, 6]]

    # skip even numbered columns to make room for tube lids
    qubit_flextubes = []
    for block in flextubeblocks:
        new = [block.columns()[index] for index in [*range(0, 12, 2)]]
        qubit_flextubes.extend(new)

    # reservoir for Qubit solution
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', '4', 'Reservoir')

    qubit_solution = reservoir.wells()[0]

    # libraries in PCR plate on temperature module at room temp
    temp = ctx.load_module('temperature module gen2', '3')
    libraries = temp.load_labware(
     'eppendorftwin.tec96_96_aluminumblock_200ul',
     "Libraries at Room Temperature")

    # magnetic module with Agilent Tapestation plate
    mag = ctx.load_module('magnetic module gen2', '1')
    mag.disengage()
    mag_plate = mag.load_labware(
     'agilent_96_wellplate_200ul', 'Agilent Tapestation Plate')

    ctx.comment("STEP - Tapestation Reagent")
    p20m.distribute(
     2, tapestation_reagent[0].bottom(1),
     [column[0].bottom(1) for column in mag_plate.columns()[:num_cols]],
     disposal_volume=2)

    ctx.pause("Place Qubit 8-tube Flex Strips on aluminum block and resume")

    ctx.comment("STEP - Libraries to Qubit Strip Tubes and Tapestation Plate")

    for index, column in enumerate(libraries.columns()[:num_cols]):
        p20m.distribute(
         2, column[0].bottom(1),
         [qubit_flextubes[index][0].bottom(1),
          mag_plate.columns()[index][0].bottom(1)],
         mix_after=(5, 3), disposal_volume=0, new_tip='always')

    ctx.comment("STEP - Qubit solution to Qubit Flex Strip Tubes")

    p300m.transfer(
     198, qubit_solution.bottom(clearance_reservoir),
     [column[0].bottom(1) for column in qubit_flextubes],
     mix_after=(10, 160), new_tip='always')

    ctx.pause(
     '''Library QC protocol complete''')

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
    filename = f"detailed_action_json/43d313-part-8.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)