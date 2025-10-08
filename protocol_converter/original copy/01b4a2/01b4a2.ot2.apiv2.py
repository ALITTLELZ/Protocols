import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/01b4a2/01b4a2.ot2.apiv2.py"

import math
metadata = {
    'protocolName': 'Sample Prep with DMSO and CSV Input',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [num_plates, csv_samp, init_vol,
        p300_mount, p1000_mount] = get_values(  # noqa: F821
        "num_plates", "csv_samp", "init_vol",
            "p300_mount", "p1000_mount")

    # labware
    final_plates = [ctx.load_labware('micronicm9641.4_96_wellplate_1400ul',
                    slot)
                    for slot in [6, 3]][:num_plates]
    reag_rack = ctx.load_labware('opentrons_6_tuberack_50000ul', 8)
    middle_rack = ctx.load_labware(
                    'bricklabwaretype2rackshort_24_wellplate_2000ul', 9)
    tips300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
               for slot in [5]]
    tips1000 = [ctx.load_labware('opentrons_96_tiprack_1000ul', slot)
                for slot in [7]]

    # pipettes
    p300 = ctx.load_instrument('p300_single_gen2',
                               p300_mount, tip_racks=tips300)
    p1000 = ctx.load_instrument('p1000_single_gen2',
                                p1000_mount, tip_racks=tips1000)

    # liquid height tracking
    v_naught_dil = init_vol*1000
    radius = reag_rack.wells()[0].diameter/2
    h_naught_dil = 0.6*v_naught_dil/(math.pi*radius**2)
    h = h_naught_dil

    def adjust_height(vol):
        nonlocal h
        dh = vol/(math.pi*radius**2)
        h -= dh
        if h < 12:
            h = 1

    # mapping
    csv_rows = [[val.strip() for val in line.split(',')]
                for line in csv_samp.splitlines()
                if line.split(',')[0].strip()][1:]

    buff = reag_rack.wells()[0]

    # protocol
    for row in csv_rows:
        transfer_vol = float(row[2])
        dest_well = middle_rack.wells_by_name()[row[1]]
        p1000.pick_up_tip()
        p1000.transfer(transfer_vol, buff.bottom(h),
                       dest_well, new_tip='never', touch_tip=True)
        p1000.mix(15, transfer_vol/2 if transfer_vol/2 < 1000 else 1000, dest_well)  # noqa:E501
        p1000.touch_tip()
        p1000.blow_out()
        p1000.drop_tip()
        adjust_height(transfer_vol)

    ctx.pause("Check vials then select `Resume` in the Opentrons app")

    all_cols = [col for plate in final_plates for col in plate.columns()]

    for row, dest_col in zip(csv_rows, all_cols):
        source_well = middle_rack.wells_by_name()[row[1]]
        p300.pick_up_tip()
        p300.aspirate(270, source_well)
        p300.touch_tip()
        for well in dest_col:
            p300.dispense(30, well)
        p300.dispense(30, source_well)
        p300.blow_out()
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
    filename = f"detailed_action_json/01b4a2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)