import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/03f9cd/03f9cd.ot2.apiv2.py"

import math
metadata = {
    'protocolName': 'Custom Emulsions via CSV File',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [csv_aq, csv_oil, p300_mount, p1000_mount] = get_values(  # noqa: F821
        "csv_aq", "csv_oil", "p300_mount", "p1000_mount")

    # labware
    aq_rack = ctx.load_labware('opentrons_6_tuberack_falcon_50ml_conical', 10)
    oil_rack = ctx.load_labware('opentrons_6_tuberack_falcon_50ml_conical',
                                11)
    dest_racks = [ctx.load_labware('vpscientific_48_wellplate_2000ul', slot)
                  for slot in [7, 8, 9]]
    tips300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
               for slot in [1]]
    tips1000 = [ctx.load_labware('opentrons_96_tiprack_1000ul', slot)
                for slot in [4]]

    # pipettes
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount,
                               tip_racks=tips300)
    p1000 = ctx.load_instrument('p1000_single_gen2', p1000_mount,
                                tip_racks=tips1000)

    # mapping
    aq_csv_rows = [[val.strip() for val in line.split(',')][1:]
                   for line in csv_aq.splitlines()
                   if line.split(',')[0].strip()][1:]
    oil_csv_rows = [[val.strip() for val in line.split(',')][1:]
                    for line in csv_oil.splitlines()
                    if line.split(',')[0].strip()][1:]
    aq_init_vols = aq_csv_rows[0]
    aq_vols = aq_csv_rows[1:]
    oil_init_vols = oil_csv_rows[0]
    oil_vols = oil_csv_rows[1:]
    aq_source_rows = [tube for row in aq_rack.rows() for tube in row]
    oil_source_rows = [tube for row in oil_rack.rows() for tube in row]
    dest_rack_wells = [well for rack in dest_racks
                       for row in rack.rows()
                       for well in row]

    # liquid height tracking
    radius = aq_rack.wells()[0].diameter/2

    def aspirate_liquid_height_track(vol, well, pip):
        nonlocal h
        dh = vol/(math.pi*radius**2)*2
        h -= dh
        if h < 40:
            h = 1
        pip.aspirate(vol, well.bottom(h))
        pip.touch_tip(v_offset=-3)
        ctx.delay(seconds=2)

    # protocol
    ctx.comment('\n--------------ADDING AQUEOUS TO PLATES---------------\n\n')
    dest_well_ctr = 0
    num_aq_cols = len(aq_vols[0])
    for col in range(num_aq_cols):
        init_vol = float(aq_init_vols[col])
        h_naught = 0.8*init_vol*1000/(math.pi*radius**2)
        h = h_naught
        for row in aq_vols:
            vol = float(row[col])*1000
            if vol == 0:
                dest_well_ctr += 1
                continue
            if vol < 300:
                if not p300.has_tip:
                    p300.pick_up_tip()
                pip = p300
            else:
                if not p1000.has_tip:
                    p1000.pick_up_tip()
                pip = p1000
            aspirate_liquid_height_track(vol, aq_source_rows[col], pip)
            pip.dispense(vol, dest_rack_wells[dest_well_ctr].top(z=-3))
            pip.blow_out()

            dest_well_ctr += 1

        if p300.has_tip:
            p300.drop_tip()
        if p1000.has_tip:
            p1000.drop_tip()
        dest_well_ctr = 0
        ctx.comment('\n')

    ctx.comment('\n--------------ADDING OIL TO PLATES---------------\n\n')
    dest_well_ctr = 0
    num_oil_cols = len(oil_vols[0])
    for col in range(num_oil_cols):
        init_vol = float(oil_init_vols[col])
        h_naught = 0.75*init_vol*1000/(math.pi*radius**2)
        h = h_naught
        for row in oil_vols:
            vol = float(row[col])*1000
            if vol == 0:
                dest_well_ctr += 1
                continue
            if vol < 300:
                if not p300.has_tip:
                    p300.pick_up_tip()
                pip = p300
            else:
                if not p1000.has_tip:
                    p1000.pick_up_tip()
                pip = p1000
            aspirate_liquid_height_track(vol, oil_source_rows[col], pip)
            pip.dispense(vol, dest_rack_wells[dest_well_ctr].top(z=-3))
            pip.blow_out()

            dest_well_ctr += 1

        if p300.has_tip:
            p300.drop_tip()
        if p1000.has_tip:
            p1000.drop_tip()
        dest_well_ctr = 0
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
    filename = f"detailed_action_json/03f9cd.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)