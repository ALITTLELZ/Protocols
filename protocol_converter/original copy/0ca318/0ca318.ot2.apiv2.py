import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0ca318/0ca318.ot2.apiv2.py"

import math
from opentrons import protocol_api

metadata = {
    'protocolName': 'PCR Prep and PCR',
    'author': 'Rami <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [num_samp, source_type, mmx_type, start_tip,
        p20_mount, m20_mount] = get_values(  # noqa: F821
        "num_samp", "source_type", "mmx_type",
        "start_tip", "p20_mount", "m20_mount")

    # num_samp = 96
    # source_type = "tuberack"
    # p20_mount = "left"
    # m20_mount = "right"

    # load modules
    tc_mod = ctx.load_module('Thermocycler Module')
    tc_mod.open_lid()
    tc_mod.set_lid_temperature(105)
    pcr_plate = tc_mod.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')  # noqa: E501

    temp_mod = ctx.load_module('temperature module gen2', 3)
    temp_mod.set_temperature(4)

    # load labware
    if source_type == "tuberack":
        samples_racks = [ctx.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap',   # noqa: E501
                         slot) for slot in [4, 5, 1, 2]]
        sample_tubes = [tube for rack in samples_racks
                        for row in rack.rows() for tube in row][:num_samp]

    if mmx_type == "mmx_wellplate":
        mmx_plate = temp_mod.load_labware('opentrons_96_aluminumblock_nest_wellplate_100ul')  # noqa: E501
    else:
        mmx_plate = temp_mod.load_labware('opentrons_24_aluminumblock_nest_1.5ml_snapcap')  # noqa: E501

    tips = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
            for slot in [6, 9]]

    # load pipettes
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount,
                              tip_racks=tips)
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount,
                              tip_racks=tips)
    all_tips = [tip for rack in tips for tip in rack.wells()]
    start_tip -= 1
    m20.starting_tip = all_tips[start_tip]
    p20.starting_tip = all_tips[start_tip]

    def pick_up(pip):
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            ctx.pause(f"Replace empty tip rack for {pip}")
            pip.reset_tipracks()
            pip.pick_up_tip()

    # mapping
    num_full_cols = math.floor(num_samp/8)
    dispense_wells = [well for column in pcr_plate.columns()[1:11]
                      for well in column[1:7]][:num_samp]

    remainder = False if num_samp % 8 == 0 else True

    num_mmx_cols = math.ceil(num_samp/24)
    if mmx_type == "mmx_wellplate":
        mmx = mmx_plate.rows()[0][:num_mmx_cols]*24
    else:
        mmx = mmx_plate.rows()[0][:num_mmx_cols]*96

    unfilled_mmx_col = mmx_plate.rows()[0][5]

    if mmx_type == 'mmx_wellplate':
        ctx.comment('\n\nTRANSFERRING MASTERMIX TO PLATE\n')
        m20.pick_up_tip()

        for i, (s_col, d_col) in enumerate(zip(
                                                mmx,
                                                pcr_plate.rows()[0][:num_full_cols])):  # noqa: E501
            if i % 4 == 0 and i > 0:
                if m20.has_tip:
                    m20.drop_tip()
                m20.pick_up_tip()

            m20.aspirate(10, s_col, rate=0.5)
            m20.dispense(10, d_col, rate=0.5)  # noqa: E501
            m20.aspirate(12.5, s_col, rate=0.5)
            m20.dispense(12.5, d_col, rate=0.5)  # noqa: E501
            m20.blow_out(d_col.top())
            m20.touch_tip()
            ctx.comment('\n')

        if m20.has_tip:
            m20.drop_tip()

        if remainder:
            ctx.comment('\n\nTRANSFERRING MASTERMIX TO UNFILLED COLUMN\n')
            remaining_wells = num_samp % 8
            unfilled_col = pcr_plate.columns()[num_full_cols][:remaining_wells]
            p20.pick_up_tip()

            for well in unfilled_col:
                p20.aspirate(10, unfilled_mmx_col, rate=0.5)
                p20.dispense(10, well, rate=0.5)  # noqa: E501
                p20.aspirate(12.5, unfilled_mmx_col, rate=0.5)
                p20.dispense(12.5, well, rate=0.5)  # noqa: E501
                p20.blow_out(well.top())
                p20.touch_tip()
            p20.drop_tip()

    elif mmx_type == "mmx_tuberack":

        ctx.comment('\n\nTRANSFERRING MASTERMIX TO PLATE\n')
        p20.pick_up_tip()

        for i, (s, d) in enumerate(zip(mmx, dispense_wells)):

            if i % 4 == 0 and i > 0:
                if p20.has_tip:
                    p20.drop_tip()
                p20.pick_up_tip()

            p20.aspirate(10, s, rate=0.5)
            p20.dispense(10, d, rate=0.5)  # noqa: E501
            p20.aspirate(12.5, s, rate=0.5)
            p20.dispense(12.5, d, rate=0.5)  # noqa: E501
            p20.move_to(d.top())
            ctx.delay(seconds=1)
            p20.blow_out(d.top())
            p20.touch_tip(v_offset=-5)
            ctx.comment('\n')
        p20.drop_tip()

    if source_type == "tuberack":
        ctx.comment('\n\nTRANSFERRING SAMPLE TO PCR PLATE\n')
        for tube, dest in zip(sample_tubes, dispense_wells):
            p20.pick_up_tip()
            p20.aspirate(2.5, tube, rate=0.5)
            p20.dispense(2.5, dest)
            p20.mix(6, 20, dest, rate=0.5)
            p20.blow_out(dest.top())
            p20.touch_tip()
            p20.drop_tip()

    ctx.comment('\n\n-----------Running PCR------------\n')

    profile1 = [

                {'temperature': 95, 'hold_time_seconds': 180},

    ]

    profile2 = [

                {'temperature': 95, 'hold_time_seconds': 30},
                {'temperature': 55, 'hold_time_seconds': 30},
                {'temperature': 72, 'hold_time_seconds': 30}

    ]

    profile3 = [

                {'temperature': 72, 'hold_time_seconds': 300}

    ]

    tc_mod.close_lid()
    tc_mod.execute_profile(steps=profile1, repetitions=1, block_max_volume=25)
    tc_mod.execute_profile(steps=profile2, repetitions=25, block_max_volume=25)
    tc_mod.execute_profile(steps=profile3, repetitions=1, block_max_volume=25)
    tc_mod.set_block_temperature(4)
    tc_mod.set_lid_temperature(25)
    tc_mod.open_lid()

    ctx.comment('''Centrifuge the PCR plate at 1,000 × g at 20°C for 1 minute
                to collect condensation, carefully remove seal.

                Place pcr plate in slot 4 of robot 2.

                Also ensure that beads are vortexed and placed in column 1
                of the reagent plate. For part 2 of the protocol.''')

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
    filename = f"detailed_action_json/0ca318.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)