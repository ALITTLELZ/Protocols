import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/10bf60-station-C/generic_station_C.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Covid-19 qPCR Setup Protocol',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.10'
}


def run(ctx):

    [num_samples, mm_vol, sample_vol, m20_mount,
     p20_mount] = get_values(  # noqa: F821
        'num_samples', 'mm_vol', 'sample_vol', 'm20_mount', 'p20_mount')

    # labware and modules
    elution_plate = ctx.load_labware(
        'appliedbiosystemsmicroamp_96_aluminumblock_200ul', '1',
        'eluates from RNA extraction')
    final_plate = ctx.load_labware(
        'appliedbiosystemsmicroamp_96_aluminumblock_200ul', '4',
        'final PCR plate')
    tempdeck = ctx.load_module('temperature module gen2', '7')
    tipracks20 = [
        ctx.load_labware('opentrons_96_tiprack_20ul', slot)
        for slot in ['2', '5']]
    mm = tempdeck.load_labware(
        'opentrons_24_aluminumblock_nest_2ml_snapcap',
        'mastermix (tube A1)').wells()[0]

    # pipettes
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount,
                              tip_racks=[tipracks20[0]])
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount,
                              tip_racks=[tipracks20[1]])

    # mastermix distribution
    p20.pick_up_tip()
    for i, well in enumerate(final_plate.wells()[:num_samples]):
        # avoid overflow
        if num_samples - i > 72 and mm_vol > 15:
            source = mm.bottom(mm.depth*0.6)
        else:
            source = mm.bottom(2)
        p20.transfer(mm_vol, source, well.bottom(2), new_tip='never')
    p20.drop_tip()

    # sample transfer
    for s, d in zip(
            elution_plate.rows()[0][:math.ceil(num_samples/8)],
            final_plate.rows()[0][:math.ceil(num_samples/8)]):
        air_gap = 2 if sample_vol <= 18 else 0
        m20.pick_up_tip()
        m20.transfer(sample_vol, s, d, air_gap=air_gap, mix_after=(3, 10),
                     new_tip='never')
        m20.air_gap(5)
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
    filename = f"detailed_action_json/10bf60-station-C.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)