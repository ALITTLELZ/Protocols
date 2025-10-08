import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/onsite_atila_saliva384_pt2/onsite_atila_saliva384_pt2.ot2.apiv2.py"

from opentrons import protocol_api
import math

metadata = {
    'protocolName': 'iAMP COVID-19 Detection Kit - Pt. 2',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx: protocol_api.ProtocolContext):

    [
     num_samp_plate1,
     num_samp_plate2,
     num_samp_plate3,
     num_samp_plate4,
     m20_mount,
     p20_mount] = get_values(  # noqa: F821
         "num_samp_plate1",
         "num_samp_plate2",
         "num_samp_plate3",
         "num_samp_plate4",
         "m20_mount",
         "p20_mount")

    if not 0 <= num_samp_plate1 <= 96:
        raise Exception("Enter a sample number 0-96")
    if not 0 <= num_samp_plate2 <= 96:
        raise Exception("Enter a sample number 0-96")
    if not 0 <= num_samp_plate3 <= 96:
        raise Exception("Enter a sample number 0-96")
    if not 0 <= num_samp_plate4 <= 94:
        raise Exception("Enter a sample number 0-94")

    # LABWARE
    pcr_plate = ctx.load_labware(
                  "biorad_384_wellplate_50ul", '3',
                  label='the 384 PCR PLATE')
    sample_plates = [ctx.load_labware(
                      "biorad_96_aluminumblock_120ul",
                      slot, label="the SAMPLE PLATE")
                     for slot in ['4', '5', '1', '2']]
    reagent_plate = ctx.load_labware('nest_96_wellplate_2ml_deep', '9')

    # TIPRACKS
    tiprack20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot,
                                  label='20uL TIPRACK')
                 for slot in ['6', '10', '11', '7', '8']]

    # INSTRUMENTS
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount,
                              tip_racks=tiprack20)

    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount,
                              tip_racks=tiprack20)

    # protocol
    samples_per_plate = [
                         num_samp_plate1,
                         num_samp_plate2,
                         num_samp_plate3,
                         num_samp_plate4
                         ]
    num_full_plate_cols = [math.floor(plate_samp_num/8)
                           for plate_samp_num in samples_per_plate]
    spill_over_per_plate = [num_samp_plate % 8
                            for num_samp_plate in samples_per_plate]

    quadrant_1 = pcr_plate.rows()[0][::2]
    quadrant_2 = pcr_plate.rows()[1][::2]
    quadrant_3 = pcr_plate.rows()[0][1::2]
    quadrant_4 = pcr_plate.rows()[1][1::2]
    quadrants = [quadrant_1, quadrant_2, quadrant_3, quadrant_4]

    quadrant_by_col_1 = [well for col in pcr_plate.columns()[::2] for well in col[::2]]  # noqa: E501
    quadrant_by_col_2 = [well for col in pcr_plate.columns()[::2] for well in col[1::2]]  # noqa: E501
    quadrant_by_col_3 = [well for col in pcr_plate.columns()[1::2] for well in col[::2]]  # noqa: E501
    quadrant_by_col_4 = [well for col in pcr_plate.columns()[1::2] for well in col[1::2]]  # noqa: E501
    quadrants_by_col = [quadrant_by_col_1, quadrant_by_col_2, quadrant_by_col_3, quadrant_by_col_4]  # noqa: E501

    airgap = 2
    ctx.comment('\n\n~~~~~~~~MOVING SRM TO PLATE FULL COLS~~~~~~~~~\n')
    srm = reagent_plate.rows()[0][0]
    m20.pick_up_tip()
    for i, (quadrant, full_col) in enumerate(zip(quadrants, num_full_plate_cols)):  # noqa: E501
        if num_samp_plate4 == 94 and i == 3:
            full_col = 16
        for col in quadrant[:full_col]:
            m20.aspirate(13, srm)
            m20.air_gap(airgap)
            m20.dispense(13+airgap, col)
            m20.blow_out()
            m20.touch_tip(radius=0.75)

        ctx.comment('\n')
    m20.drop_tip()

    if sum(spill_over_per_plate) > 0 and num_samp_plate4 != 94:
        ctx.comment('\n\n~~~~~~~~MOVING SRM TO UNFILLED COLUMNS~~~~~~~~~\n')
        p20.pick_up_tip()
        for i, (quadrant,
                quadrant_by_col,
                full_col,
                num_spill_wells) in enumerate(zip(
                                     quadrants,
                                     quadrants_by_col,
                                     num_full_plate_cols,
                                     spill_over_per_plate)):
            wells_to_dispense = quadrant_by_col[full_col*8:full_col*8+num_spill_wells]  # noqa: E501

            for source_well, dest in zip(reagent_plate.columns()[0],
                                         wells_to_dispense):
                p20.aspirate(13, source_well)
                p20.air_gap(airgap)
                p20.dispense(13+airgap, dest)
                p20.blow_out()
                p20.touch_tip(radius=0.75)
            ctx.comment('\n')
        p20.drop_tip()

    if num_samp_plate3 != 96:
        ctx.comment('\n\n~~~~~~~~MOVING SRM TO CONTROL WELL O24~~~~~~~~~\n')
        p20.pick_up_tip()
        p20.aspirate(13, srm)
        p20.air_gap(airgap)
        p20.dispense(13+airgap, pcr_plate.wells_by_name()["O24"])
        p20.blow_out()
        p20.touch_tip(radius=0.75)
        if num_samp_plate4 != 94:
            p20.drop_tip()

    if num_samp_plate4 != 94:
        ctx.comment('\n\n~~~~~~~~MOVING SRM TO CONTROL WELL P24~~~~~~~~~\n')
        if not p20.has_tip:
            p20.pick_up_tip()
        p20.aspirate(13, srm)
        p20.air_gap(airgap)
        p20.dispense(13+airgap, pcr_plate.wells_by_name()["P24"])
        p20.blow_out()
        p20.touch_tip(radius=0.75)
    if p20.has_tip:
        p20.drop_tip()

    ctx.comment('\n\n~~~~~~~~MOVING SAMPLES TO PLATE FULL COLS~~~~~~~~~\n')
    for i, (quadrant, full_col) in enumerate(zip(quadrants, num_full_plate_cols)):  # noqa: E501
        source_cols = sample_plates[i].rows()[0][:full_col]
        if num_samp_plate3 == 96 and i == 2:
            end_col = 11
        elif num_samp_plate4 == 94 and i == 3:
            end_col = 11
        else:
            end_col = full_col

        for source, col in zip(source_cols, quadrant[:end_col]):

            m20.pick_up_tip()
            m20.aspirate(2, source)
            m20.dispense(2, col)
            m20.mix(1, 12, col)
            m20.blow_out()
            m20.drop_tip()
        ctx.comment('\n')
        ctx.comment('\n')

    if sum(spill_over_per_plate) > 0:
        ctx.comment('\n\n~~~~~~~~MOVING SAMPLE TO UNFILLED COLUMNS~~~~~~~~~\n')
        for i, (quadrant,
                quadrant_by_col,
                full_col,
                num_spill_wells) in enumerate(zip(
                                     quadrants,
                                     quadrants_by_col,
                                     num_full_plate_cols,
                                     spill_over_per_plate)):
            if num_samp_plate3 == 96 and i == 2:
                num_spill_wells = 7
                full_col = 11

            if num_samp_plate4 == 94 and i == 3:
                num_spill_wells = 7
                full_col = 11
            wells_to_dispense = quadrant_by_col[full_col*8:full_col*8+num_spill_wells]  # noqa: E501

            if full_col == 12:
                full_col = 11

            for source_well, dest in zip(sample_plates[i].columns()[full_col][:num_spill_wells],  # noqa: E501
                                         wells_to_dispense):
                p20.pick_up_tip()
                p20.aspirate(2, source_well)
                p20.dispense(2, dest)
                p20.mix(1, 12, dest)
                p20.drop_tip()
            ctx.comment('\n')

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
    filename = f"detailed_action_json/onsite_atila_saliva384_pt2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)