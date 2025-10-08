import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/00c517-pt2/00c517-pt2.ot2.apiv2.py"

from opentrons import protocol_api
import math

metadata = {
    'protocolName': 'VIB UGENT - Part 2',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [input_csv, init_samp_vol, init_vol_sds,
        start_tip_p20, start_tip_p300,
        p20_mount, p300_mount] = get_values(  # noqa: F821
        "input_csv", "init_samp_vol", "init_vol_sds",
            "start_tip_p20", "start_tip_p300",
            "p20_mount", "p300_mount")

    all_rows = [[val.strip() for val in line.split(',')]
                for line in input_csv.splitlines()
                if line.split(',')[0].strip()][1:]

    start_tip_p20 -= 1
    start_tip_p300 -= 1

    # labware
    sample_plate = ctx.load_labware('agilent_96_wellplate_500ul', 2)
    dest_plate = ctx.load_labware('agilent_96_wellplate_1400ul', 3)
    bsa_tuberack = ctx.load_labware('opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical', 4)  # noqa:E501

    tips300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
               for slot in [9]]
    tips20 = [ctx.load_labware('opentrons_96_tiprack_20ul', slot)
              for slot in [6]]

    # liquid height tracking
    v_naught_sds = init_vol_sds*1000

    radius_sds = bsa_tuberack.rows()[0][3].diameter/2

    h_naught_sds = 0.85*v_naught_sds/(math.pi*radius_sds**2)

    h_sds = h_naught_sds

    def adjust_height(vol):
        nonlocal h_sds

        radius = radius_sds

        dh = (vol/(math.pi*radius**2))*1.33

        h_sds -= dh

        if h_sds < 12:
            h_sds = 1

    def pick_up(pip):
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            ctx.pause("Replace empty tip rack")
            pip.reset_tipracks()
            pick_up()

    # pipettes
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount, tip_racks=tips20)
    p300 = ctx.load_instrument('p300_single_gen2',
                               p300_mount, tip_racks=tips300)

    p20.starting_tip = tips20[0].wells()[start_tip_p20]
    p300.starting_tip = tips300[0].wells()[start_tip_p300]

    # mapping
    sds = bsa_tuberack.rows()[0][3]  # A3

    # add sds
    for row in all_rows:
        sds_vol = float(row[3])
        well = row[1]
        dest_well = dest_plate.wells_by_name()[well]

        if sds_vol > 0:

            if sds_vol <= 20:
                pip = p20
                if not p20.has_tip:
                    pip.pick_up_tip()
            else:
                pip = p300
                if not p300.has_tip:
                    pip.pick_up_tip()

            pip.aspirate(sds_vol, sds)
            pip.dispense(sds_vol, dest_well)
            adjust_height(sds_vol)

    if p20.has_tip:
        p20.drop_tip()
    if p300.has_tip:
        p300.drop_tip()

    # add sample
    for row in all_rows:
        samp_vol = float(row[4])
        well = row[1]
        source_well = sample_plate.wells_by_name()[well]
        dest_well = dest_plate.wells_by_name()[well]

        if samp_vol > 0:

            if samp_vol <= 20:
                pip = p20
                if not p20.has_tip:
                    if p300.has_tip:
                        p300.drop_tip()
                    pip.pick_up_tip()
            else:
                pip = p300
                if not p300.has_tip:
                    if p20.has_tip:
                        p20.drop_tip()
                    pip.pick_up_tip()

            if pip == p20:
                pip.mix(10, 20, source_well)
            elif pip == p300:
                pip.mix(5,
                        0.8*init_samp_vol if 0.8*init_samp_vol < 300 else 300,
                        source_well)

            pip.aspirate(samp_vol, source_well)
            pip.dispense(samp_vol, dest_well)
            adjust_height(samp_vol)

        if p20.has_tip:
            p20.drop_tip()
        if p300.has_tip:
            p300.drop_tip()

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
    filename = f"detailed_action_json/00c517-pt2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)