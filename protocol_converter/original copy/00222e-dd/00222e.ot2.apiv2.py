import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/00222e-dd/00222e.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Drug Dosing',
    'author': 'Nick Diehl <ndiehl@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [num_cell_lines, tip_start_col,
     num_rep_plates] = get_values(  # noqa: F821
        'num_cell_lines', 'tip_start_col', 'num_rep_plates')

    # labware
    rep_plates = [
        ctx.load_labware(
            'thermofisher_96_wellplate_300ul', slot, f'rep {slot}')
        for slot in range(1, 1+num_rep_plates)]
    source_plate = ctx.load_labware('thermoscientificnunc_96_wellplate_2000ul',
                                    '4', 'DRUG + YOYO-MEDIA')
    tipracks300 = [ctx.load_labware('opentrons_96_tiprack_300ul', '10')]

    # pipette
    m300 = ctx.load_instrument(
        'p300_multi_gen2', 'right', tip_racks=tipracks300)
    m300.starting_tip = tipracks300[0].columns()[tip_start_col-1][0]

    # variables
    vol_dose = 100.0
    vol_air_gap = 0
    cell_lines = [
        source_plate.rows()[0][i*2] for i in range(num_cell_lines)]
    rep_destination_sets = [
            [plate.rows()[0][1+i*3:1+(i+1)*3] for plate in rep_plates]
            for i in range(num_cell_lines)]
    rep_destination_sets_flat = []
    for rep_set in rep_destination_sets:
        flat_set = []
        for inner_set in rep_set:
            for well in inner_set:
                flat_set.append(well)
        rep_destination_sets_flat.append(flat_set)

    def slow_withdraw(pip, well):
        ctx.max_speeds['A'] = 25
        ctx.max_speeds['Z'] = 25
        pip.move_to(well.top())
        del ctx.max_speeds['A']
        del ctx.max_speeds['Z']

    # perform transfers
    num_dests_per_asp = int(
        m300.tip_racks[0].wells()[0].max_volume/(vol_dose+vol_air_gap))
    for source, dest_set in zip(cell_lines, rep_destination_sets_flat):
        num_asp = math.ceil(len(dest_set)/num_dests_per_asp)
        dest_sets_per_asp = [
            dest_set[i*num_dests_per_asp:(i+1)*num_dests_per_asp]
            if i < num_asp - 1
            else dest_set[i*num_dests_per_asp:]
            for i in range(num_asp)]
        m300.pick_up_tip()
        for d_set in dest_sets_per_asp:
            m300.mix(3, 300, source.bottom(1))  # premix
            for _ in range(len(d_set)):
                if vol_air_gap:
                    m300.aspirate(vol_air_gap, source.top())
                m300.aspirate(vol_dose, source.bottom(1))
            for i, d in enumerate(d_set):
                m300.dispense(vol_dose+vol_air_gap, d.bottom(7.6))
                if i == len(d_set) - 1:
                    m300.blow_out(d.bottom(7.6))
        m300.drop_tip()

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
    filename = f"detailed_action_json/00222e-dd.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)