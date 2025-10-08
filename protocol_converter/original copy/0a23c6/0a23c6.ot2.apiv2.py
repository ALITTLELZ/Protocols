import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0a23c6/0a23c6.ot2.apiv2.py"

import math

metadata = {
    'apiLevel': '2.5',
    'protocolName': '',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Custom Protocol Request'
}


def run(ctx):
    sample_count = get_values(  # noqa: F821
            'sample_count')[0]
    col_count = math.ceil(sample_count / 8)

    tempdeck = ctx.load_module('temperature module gen2', '9')
    temp_plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul')
    tp_cols = temp_plate.rows()[0][:col_count]

    pcr_strip = ctx.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul', '6')
    pcr_strip2 = ctx.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul', '8')
    mastermix = ctx.load_labware(
        'opentrons_24_aluminumblock_nest_1.5ml_snapcap', '7')

    prime_direct = mastermix.wells_by_name()["A1"]
    n1 = mastermix.wells_by_name()["A2"]
    n2 = mastermix.wells_by_name()["A3"]
    rp = mastermix.wells_by_name()["A4"]

    p300s = ctx.load_instrument(
        'p300_single_gen2', 'left', tip_racks=[
            ctx.load_labware(
                'opentrons_96_filtertiprack_200ul', '3')])
    p20m = ctx.load_instrument(
        'p20_multi_gen2',
        'right',
        tip_racks=[
            ctx.load_labware(
                'opentrons_96_filtertiprack_20ul',
                x) for x in [
                '1',
                '2',
                '4']])

    tempdeck.set_temperature(4)

    p300s.transfer(130, prime_direct, pcr_strip.columns()[0], new_tip='once')
    for mm, col in zip([n1, n2, rp], pcr_strip.columns()[1:4]):
        p300s.transfer(20, mm, col, new_tip='once')

    for col in tp_cols:
        p20m.transfer(5, col, pcr_strip.wells_by_name()["A1"])

    for target, sample_col_num in zip(pcr_strip.rows()[0][1:4], [
                                      [a + b for a in [0, 3, 6, 9]]
                                      for b in [1, 2, 3]]):
        for num in sample_col_num:
            if num <= col_count:
                p20m.transfer(1.5, tp_cols[num - 1], target)

    for target, sample_col_num in zip(pcr_strip2.rows()[0][0:4], [
                                      [a + b for a in [1, 2, 3]]
                                      for b in [0, 3, 6, 9]]):
        for num in sample_col_num:
            if num <= col_count:
                p20m.transfer(8.5, tp_cols[num - 1], target)

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
    filename = f"detailed_action_json/0a23c6.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)