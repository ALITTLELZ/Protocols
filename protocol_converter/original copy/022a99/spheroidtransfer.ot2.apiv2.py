import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/022a99/spheroidtransfer.ot2.apiv2.py"

import math
from opentrons.types import Point

metadata = {
    'apiLevel': '2.14',
    'protocolName': 'Spheroid Transfer',
    'author': 'Nick Diehl <ndiehl@opentrons.com>',
}

NUM_SPHEROIDS = 384
VOL_SPHEROID = 20
FLOW_RATE_ASP = 15.0
FLOW_RATE_DISP = 7.5


def run(ctx):

    source_plate = ctx.load_labware(
        'corning_384_wellplate_90ul', '4', 'spheroid source plate')
    dest_plate = ctx.load_labware(
        'akura_384_wellplate_50ul', '1', 'destination plate')
    tipracks20 = [
        ctx.load_labware('opentrons_96_tiprack_20ul', slot)
        for slot in ['2']]

    m20 = ctx.load_instrument('p20_multi_gen2', 'left', tip_racks=tipracks20)
    m20.flow_rate.aspirate = FLOW_RATE_ASP
    m20.flow_rate.dispense = FLOW_RATE_DISP

    def slow_withdraw(pip, well, delay_seconds=1.0):
        pip.default_speed /= 16
        if delay_seconds > 0:
            ctx.delay(seconds=delay_seconds)
        pip.move_to(well.top())
        pip.default_speed *= 16

    num_transfers = math.ceil(NUM_SPHEROIDS/8)

    sources = [
        well
        for col in source_plate.columns()
        for well in col[:2]][:num_transfers]
    dests = [
        well
        for col in dest_plate.columns()
        for well in col[:2]][:num_transfers]

    # perform transfers
    m20.pick_up_tip()
    for i, (s, d) in enumerate(zip(sources, dests)):
        if i == 32:
            m20.drop_tip()
            m20.pick_up_tip()
        m20.aspirate(VOL_SPHEROID, s.bottom(0.2))
        slow_withdraw(m20, s)
        m20.move_to(d.top())
        m20.dispense(VOL_SPHEROID, d.bottom().move(Point(y=-0.9, z=3)))
        slow_withdraw(m20, d)
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
    filename = f"detailed_action_json/022a99.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)