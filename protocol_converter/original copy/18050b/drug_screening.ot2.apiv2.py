import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/18050b/drug_screening.ot2.apiv2.py"

import math

# metadata
metadata = {
    'protocolName': 'Drug Screening',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(ctx):
    [p10_multi_mount, mother_plate_type, num_daughter_plates, start_col,
        end_col, transfer_volume, dispense_plan] = get_values(  # noqa: F821
            'p10_multi_mount', 'mother_plate_type', 'num_daughter_plates',
            'start_col', 'end_col', 'transfer_volume', 'dispense_plan')

    # checks
    if num_daughter_plates > 6 or num_daughter_plates < 1:
        raise Exception('Invalid number of daughter plates (must be 1-6)')
    if start_col < 1 or end_col > 24 or start_col >= end_col:
        raise Exception('Invaid columns (start and end must be 1-24), and  end must be after start.')

    # labware
    tipracks10 = [
        ctx.load_labware('opentrons_96_tiprack_10ul', slot, '10ul tiprack')
        for slot in ['1', '2', '3', '10']
    ]
    daughters = [
        ctx.load_labware(
            'corning_384_wellplate_112ul_flat',
            slot,
            'copy (daughter) plate ' + str(i+1)
        )
        for i, slot in enumerate(range(4, 4+num_daughter_plates))
        ]
    mother = ctx.load_labware(
        mother_plate_type, '11', 'Prestwick (mother plate)')

    # pipette
    p10 = ctx.load_instrument(
        'p10_multi', p10_multi_mount, tip_racks=tipracks10)
    p10.flow_rate.aspirate = 2
    p10.flow_rate.dispense = 5

    # sample setup
    sources = [
        well for col in mother.columns()[int(start_col)-1:int(end_col)]
        for well in col[:2]
    ]
    dest_sets = [
        [daughter.columns()[col][row] for daughter in daughters]
        for col in range(int(start_col)-1, int(end_col))
        for row in range(2)
    ]

    def split_dests(dest_list, num_elements):
        num_splits = math.ceil(len(dest_list)/num_elements)
        return [
            dest_list[i*num_elements:i*num_elements+num_elements]
            if i + num_elements <= len(dest_list) else dest_list[i:]
            for i in range(num_splits)
        ]

    # transfers
    for s, d_set in zip(sources, dest_sets):
        p10.pick_up_tip()
        if dispense_plan == 'single':
            for d in d_set:
                p10.transfer(
                    transfer_volume,
                    s.top(7-s.geometry._depth),
                    d.top(2-d.geometry._depth),
                    new_tip='never'
                )
                p10.touch_tip(d, v_offset=7-d.geometry._depth)
        else:
            num_trans_per_asp = int(9//transfer_volume)
            disp_sets = split_dests(d_set, num_trans_per_asp)
            for set in disp_sets:
                asp_vol = len(set)*transfer_volume + 1
                p10.aspirate(asp_vol, s.top(7-s.geometry._depth))
                for well in set:
                    p10.dispense(
                        transfer_volume, well.top(2-well.geometry._depth))
                    p10.touch_tip(well, v_offset=7-well.geometry._depth)
                p10.blow_out(s.top(7-s.geometry._depth))
        p10.drop_tip()

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
    filename = f"detailed_action_json/18050b.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)