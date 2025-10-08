import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7663a6/7663a6.ot2.apiv2.py"

metadata = {
    'protocolName': 'PCR Prep with Frozen Aluminum Block',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(ctx):

    [num_col, source_start_col, dest_start_col, sample_vol, mmx_vol,
     source_asp_height_plate, source_asp_height_plate_mmx,
     source_asp_flow_rate_plate, delay,
     source_asp_flow_rate_mmx, dispense_height, dest_flow_rate_sample,
     dest_flow_rate_mmx, mix_vol, mix_reps, touch_tip, blow_out,
     p20_mount, m20_mount] = get_values(  # noqa: F821
        "num_col", "source_start_col", "dest_start_col", "sample_vol",
        "mmx_vol", "source_asp_height_plate",
        "source_asp_height_plate_mmx", "source_asp_flow_rate_plate", "delay",
        "source_asp_flow_rate_mmx", "dispense_height", "dest_flow_rate_sample",
        "dest_flow_rate_mmx", "mix_vol", "mix_reps",
        "touch_tip", "blow_out", "p20_mount", "m20_mount")

    if not 0 <= num_col <= 12:
        raise Exception("Enter a column number between 1 and 12")
    if not 0 <= source_start_col <= 12:
        raise Exception("Enter a column number between 1 and 12")
    if not 0 <= dest_start_col <= 12:
        raise Exception("Enter a column number between 1 and 12")
    source_start_col -= 1
    dest_start_col -= 1

    # load labware
    sample_plate = ctx.load_labware(
                'nest_96_wellplate_100ul_pcr_full_skirt', '1')
    dest_plate = ctx.load_labware(
                'nest_96_wellplate_100ul_pcr_full_skirt', '2')
    mastermix = ctx.load_labware(
                'opentrons_24_aluminumblock_nest_1.5ml_snapcap', '3')
    tiprack_single = ctx.load_labware('opentrons_96_filtertiprack_20ul', '4')
    tiprack_multi = ctx.load_labware('opentrons_96_filtertiprack_20ul', '5')

    # load pipette
    p20 = ctx.load_instrument('p20_single_gen2',
                              p20_mount, tip_racks=[tiprack_single])
    m20 = ctx.load_instrument('p20_multi_gen2',
                              m20_mount, tip_racks=[tiprack_multi])

    # load reagents
    mmx = mastermix.wells()[0]

    # PROTOCOL
    p20.flow_rate.aspirate = source_asp_flow_rate_mmx
    p20.flow_rate.dispense = dest_flow_rate_mmx
    m20.flow_rate.aspirate = source_asp_flow_rate_plate
    m20.flow_rate.dispense = dest_flow_rate_sample
    num_samp = num_col*8
    airgap = 3

    # transfer mastermix to plate
    p20.pick_up_tip()
    for i, dest in enumerate(
                            dest_plate.wells()[dest_start_col*8:
                                               dest_start_col*8+num_samp]):
        if not p20.has_tip:
            p20.pick_up_tip()
        p20.aspirate(mmx_vol, mmx.bottom(source_asp_height_plate_mmx))
        ctx.delay(seconds=delay)
        if touch_tip:
            p20.touch_tip()
        p20.dispense(mmx_vol, dest.bottom(dispense_height))
        if blow_out:
            p20.blow_out()
        if (i+1) % 8 == 0:
            p20.drop_tip()
            ctx.comment('\n')

    # transfer sample to plate
    for s_col, d_col in zip(sample_plate.rows()[0][source_start_col:
                            source_start_col+num_col],
                            dest_plate.rows()[0][dest_start_col:
                            dest_start_col+num_col]):
        m20.pick_up_tip()
        m20.aspirate(sample_vol, s_col.bottom(source_asp_height_plate))
        m20.air_gap(airgap)
        if touch_tip:
            m20.touch_tip()
        m20.dispense(sample_vol+airgap, d_col.bottom(dispense_height))
        m20.mix(mix_reps, mix_vol, d_col)
        if blow_out:
            m20.blow_out()
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
    filename = f"detailed_action_json/7663a6.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)