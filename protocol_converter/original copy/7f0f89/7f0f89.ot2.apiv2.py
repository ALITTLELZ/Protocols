import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7f0f89/7f0f89.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Adding Developer Solution to 216 Well Cartridge Plate',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(ctx):

    [num_samp, height_above_cartridge, disp_vol, asp_rate, disp_rate,
     asp_delay_time, disp_delay_time, p300_mount] = get_values(  # noqa: F821
        "num_samp", "height_above_cartridge", "disp_vol", "asp_rate",
        "disp_rate", "asp_delay_time", "disp_delay_time", "p300_mount")

    if not 1 <= num_samp <= 216:
        raise Exception("Enter a sample number between 1 and 216 samples")
    if not 0.1 <= height_above_cartridge <= 10:
        raise Exception("Enter a height between 1 and 10mm")
    if not 1 <= disp_vol <= 85:
        raise Exception("Enter a dispense volume between 1 and 85µL")

    # load labware
    plate = ctx.load_labware('generic_216_wellplate_85ul_flat', '1')
    reservoir = ctx.load_labware('nest_1_reservoir_195ml', '9')
    tiprack = ctx.load_labware('opentrons_96_tiprack_300ul', '6')

    # load instruments
    p300 = ctx.load_instrument('p300_multi_gen2', p300_mount,
                               tip_racks=[tiprack])

    # protocol
    p300.flow_rate.dispense = asp_rate
    p300.flow_rate.dispense = disp_rate
    num_transfers = math.floor(num_samp/4)
    plate_map = [well for well in plate.wells()[::4]][:num_transfers]
    remainder = num_samp % 4 if num_samp > 4 else 0

    p300.pick_up_tip()
    for well in plate_map:
        p300.aspirate(disp_vol+20, reservoir.wells()[0])  # aspirate extra
        ctx.delay(seconds=asp_delay_time)
        p300.dispense(disp_vol, well.top(height_above_cartridge))
        ctx.delay(seconds=disp_delay_time)
        p300.dispense(20, reservoir.wells()[0])
        p300.blow_out(reservoir.wells()[0])
        ctx.comment('\n')
    p300.return_tip()

    if remainder != 0:
        p300.pick_up_tip(tiprack.wells()[-1])
        for well in plate.wells()[num_samp-remainder:num_samp]:
            p300.aspirate(disp_vol+20, reservoir.wells()[0])  # aspirate extra
            ctx.delay(seconds=asp_delay_time)
            p300.dispense(disp_vol, well.top(height_above_cartridge))
            ctx.delay(seconds=disp_delay_time)
            p300.dispense(20, reservoir.wells()[0])
            p300.blow_out(reservoir.wells()[0])
            ctx.comment('\n\n')
        p300.return_tip()

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
    filename = f"detailed_action_json/7f0f89.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)