import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/quintara_onsite_part2/quintara_onsite_part2.ot2.apiv2.py"

metadata = {
    'protocolName': 'Two 96 Deepwell to PCR Plate (Vertical)',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [num_sets, dest_start_col, p20_mount] = get_values(  # noqa: F821
        "num_sets", "dest_start_col", "p20_mount")

    dest_start_col -= 1

    if num_sets > 8-dest_start_col:
        raise Exception("""You do not have enough destination columns
                           for the number of sets specified""")

    # labware
    source_plate = ctx.load_labware('quintara_192_deepwell_plate', 1)
    dest_plate = ctx.load_labware('quintara_192_pcr_plate', 2)
    tips = [ctx.load_labware('opentrons_96_tiprack_20ul', slot)
            for slot in [10, 11, 9]]
    half_tip_rack = [ctx.load_labware('opentrons_96_tiprack_20ul', slot)
                     for slot in [6]]

    # pipettes
    m20 = ctx.load_instrument('p20_multi_gen2', p20_mount, tip_racks=tips)

    num_chan = 4
    tips_ordered = [
        tip
        for row in half_tip_rack[0].rows()[
            len(half_tip_rack[0].rows())-num_chan::-1*num_chan]
        for tip in row]

    tip_count = 0

    def pick_up_half():
        nonlocal tip_count
        m20.pick_up_tip(tips_ordered[tip_count])
        tip_count += 1

    # mapping
    all_source_columns_full_tip = [col for i in [0, 12]
                                   for col in source_plate.rows()[i]]

    all_source_columns_half_tip = [col for i in [8, 20]
                                   for col in source_plate.rows()[i]]

    chunk_s_col_full = [all_source_columns_full_tip[i:i+4]
                        for i in range(0,
                        len(all_source_columns_full_tip), 4)]

    chunk_s_col_half = [all_source_columns_half_tip[i:i+4]
                        for i in range(0,
                        len(all_source_columns_half_tip), 4)]

    # protocol
    ctx.comment('\n-----------Filling Destination Plate-------------\n\n')
    for i, (chunk, half_chunk) in enumerate(
                                            zip(
                                                chunk_s_col_full[:num_sets],
                                                chunk_s_col_half
                                                )):
        for j, well in enumerate(chunk):
            if j == 0 or j == 3:
                vol = 20
            if j == 1 or j == 2:
                vol = 2

            m20.pick_up_tip()
            m20.aspirate(vol, well)
            m20.dispense(vol, dest_plate.rows()[12][dest_start_col+i])
            m20.return_tip()
        ctx.comment('\n')

        for j, well in enumerate(half_chunk):
            if j == 0 or j == 3:
                vol = 20
            if j == 1 or j == 2:
                vol = 2

            pick_up_half()
            m20.aspirate(vol, well)
            if vol == 20:
                m20.dispense(vol, dest_plate.rows()[20][dest_start_col+i])
            else:
                m20.dispense(vol,
                             dest_plate.rows()[20][
                                dest_start_col+i].bottom(z=0.4))
            m20.return_tip()
        ctx.comment('\n\n\n\n')

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
    filename = f"detailed_action_json/quintara_onsite_part2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)