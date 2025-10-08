import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/3b0db0/3b0db0.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Temperature Controlled PCR Prep With Tube Strips',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(ctx):

    [num_samp, asp_delay, mix_reps, asp_height, asp_height_m20,
     asp_rate, disp_rate, asp_rate_m20, disp_rate_m20,
     p20_mount, m20_mount] = get_values(  # noqa: F821
        "num_samp", "asp_delay", "mix_reps", "asp_height", "asp_height_m20",
         "asp_rate", "disp_rate", "asp_rate_m20", "disp_rate_m20",
        "p20_mount", "m20_mount")

    if not 1 <= num_samp <= 96:
        raise Exception("Enter a sample number between 1-96")

    num_col_floor = math.floor(num_samp/8)
    remain = num_samp % 8

    # load labware
    temp_mod = ctx.load_module('temperature module gen2', '3')
    sample_plate = temp_mod.load_labware('biorad_96_wellplate_200ul_pcr')
    tip_rack = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
                for slot in ['1', '2']]
    saliva = [ctx.load_labware(
            'tuberack_15_tuberack_5000ul', slot)
            for slot in ['5', '6', '7', '8', '9', '10', '11']]
    reagent_plate = ctx.load_labware('pcrstripplate_96_wellplate_200ul', '4')

    # load instrument
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount, tip_racks=tip_rack)
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount, tip_racks=tip_rack)

    m20.well_bottom_clearance.aspirate = asp_height_m20
    p20.flow_rate.aspirate = asp_rate*p20.flow_rate.aspirate
    p20.flow_rate.dispense = disp_rate*p20.flow_rate.dispense
    m20.flow_rate.aspirate = asp_rate_m20*m20.flow_rate.aspirate
    m20.flow_rate.dispense = disp_rate_m20*m20.flow_rate.dispense

    # reagents, setup
    temp_mod.set_temperature(4)
    mastermix = reagent_plate.rows()[0][:4]
    tubes = [tube for tuberack in saliva for tube in tuberack.wells()]

    m20.pick_up_tip()
    col_ctr = 0
    for i, col in enumerate(sample_plate.rows()[0][:num_col_floor]):
        if i % 3 == 0 and i != 0:
            col_ctr += 1
        m20.aspirate(15, mastermix[col_ctr])
        m20.dispense(15, col)
    m20.drop_tip()

    p20.pick_up_tip()
    for mix, well in zip(reagent_plate.wells()[:remain],
                         sample_plate.wells()
                         [num_col_floor*8:num_col_floor*8+remain]):
        p20.aspirate(15, mix)
        p20.dispense(15, well)
    p20.drop_tip()

    # add saliva
    airgap = 5
    for s, d in zip(tubes[:num_samp], sample_plate.wells()):
        p20.pick_up_tip()
        p20.aspirate(5, s.bottom(z=asp_height))
        p20.air_gap(airgap)
        ctx.delay(seconds=asp_delay)
        p20.dispense(5+airgap, d)
        ctx.delay(seconds=asp_delay)
        p20.mix(mix_reps, 15, d)
        ctx.delay(seconds=asp_delay)
        p20.blow_out()
        p20.touch_tip()
        p20.drop_tip()

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
    filename = f"detailed_action_json/3b0db0.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)