import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/075bee/075bee.ot2.apiv2.py"

import math
metadata = {
    'protocolName': 'Material Synthesis Prep with CSV Input',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [init_vols_csv, source_csv_slot3,
     source_csv_slot7, source_csv_slot8,
     source_csv_slot9, p300_mount] = get_values(  # noqa: F821
        "init_vols_csv", "source_csv_slot3", "source_csv_slot7",
         "source_csv_slot8", "source_csv_slot9", "p300_mount")

    # labware
    source_rack_50 = ctx.load_labware(
                    'opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical', 5)

    source_rack_15 = ctx.load_labware(
                    'opentrons_15_tuberack_falcon_15ml_conical', 2)
    dest_racks = [ctx.load_labware('twdtradewinds_24_tuberack_4000ul', slot)
                  for slot in [3, 7, 8, 9]]
    tips = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
            for slot in [1, 4]]

    # pipettes
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount, tip_racks=tips)

    # protocol

    radius_15_tubes = source_rack_15.wells()[0].diameter/2
    radius_50_tubes = source_rack_50.rows()[0][3].diameter/2

    ctx.max_speeds['Z'] = 125
    ctx.max_speeds['A'] = 125

    csv_rows_init_vols = [[val.strip() for val in line.split(',')]
                          for line in init_vols_csv.splitlines()
                          if line.split(',')[0].strip()][1:]

    init_vols_all_tubes = [int(row[2]) for row in csv_rows_init_vols]
    init_height_all_tubes = []
    for i, vol in enumerate(init_vols_all_tubes):
        radius = radius_15_tubes if i < 15 else radius_50_tubes
        init_height_all_tubes.append(1000*vol*0.6/(math.pi*radius**2))

    all_csvs = [source_csv_slot3, source_csv_slot7,
                source_csv_slot8, source_csv_slot9]

    for csv, dest_rack in zip(all_csvs, dest_racks):
        dest_rack_wells = [well for row in dest_rack.rows() for well in row]
        csv_rows = [[val.strip() for val in line.split(',')][3:]
                    for line in csv.splitlines()
                    if line.split(',')[0].strip()][1:]

        for source_tube_vols, col_num in zip(csv_rows_init_vols, range(18)):
            source_tube = ctx.loaded_labwares[int(source_tube_vols[0])].wells_by_name()[source_tube_vols[1]]  # noqa: E501
            radius = source_tube.diameter/2

            # liquid height tracking
            if not p300.has_tip:
                p300.pick_up_tip()
            pick_up_tip_ctr = 0

            for row, dest_well in zip(csv_rows, dest_rack_wells):
                vol = float(row[col_num])*1000

                if vol > 0:
                    if vol <= 300:
                        h = init_height_all_tubes[col_num]
                        dh = vol/(math.pi*radius**2)
                        p300.aspirate(vol, source_tube.bottom(h if h > 15 else 1))  # noqa: E501
                        ctx.delay(seconds=1)
                        ctx.max_speeds['Z'] /= 10
                        ctx.max_speeds['A'] /= 10
                        p300.move_to(source_tube.top())
                        ctx.max_speeds['Z'] *= 10
                        ctx.max_speeds['A'] *= 10
                        ctx.delay(seconds=5)
                        p300.touch_tip(v_offset=-1)
                        p300.dispense(vol, dest_well.top(z=-3))

                        init_height_all_tubes[col_num] -= dh
                        pick_up_tip_ctr += 1
                    else:
                        num_divisions = math.ceil(vol/300)
                        vol_divided = vol / num_divisions
                        for _ in range(num_divisions):
                            h = init_height_all_tubes[col_num]
                            dh = vol/(math.pi*radius**2)
                            p300.aspirate(vol_divided, source_tube.bottom(h if h > 15 else 1))  # noqa: E501
                            ctx.delay(seconds=1)
                            ctx.max_speeds['Z'] /= 10
                            ctx.max_speeds['A'] /= 10
                            p300.move_to(source_tube.top())
                            ctx.max_speeds['Z'] *= 10
                            ctx.max_speeds['A'] *= 10
                            ctx.delay(seconds=5)
                            p300.touch_tip(v_offset=-1)
                            p300.dispense(vol_divided, dest_well)
                            init_height_all_tubes[col_num] -= dh
                            pick_up_tip_ctr += 1

            if pick_up_tip_ctr > 0:
                p300.drop_tip()
        for tube in dest_rack_wells:
            p300.pick_up_tip()
            p300.mix(3, 200, tube)
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
    filename = f"detailed_action_json/075bee.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)