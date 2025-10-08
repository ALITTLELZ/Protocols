import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0e696e/cherrypicking.ot2.apiv2.py"

metadata = {
    'protocolName': 'Cherrypicking',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.10'
}


def run(ctx):

    [transfer_csv, pipette_type, pipette_mount, tip_type,
     primer_lw, sample_vol, primer_vol, tip_reuse] = get_values(  # noqa: F821
        "transfer_csv", "pipette_type", "pipette_mount", "tip_type",
        "primer_lw", "sample_vol", "primer_vol", "tip_reuse")

    # load pipette
    pip = ctx.load_instrument(pipette_type, pipette_mount)

    primer = ctx.load_labware(primer_lw, '9',
                              'primer (position A1)').wells()[0]
    if pipette_type != 'p20_single_gen2':
        p20_mount = 'left' if pipette_mount == 'right' else 'right'
        mod = 'filter' if tip_type == 'filter' else ''
        tiprack_p20 = [
            ctx.load_labware(f'opentrons_96_{mod}tiprack_20ul', '10')]
        p20 = ctx.load_instrument('p20_single_gen2', p20_mount,
                                  tip_racks=tiprack_p20)
    final_plate = ctx.load_labware(
        'custom_96_wellplate_200ul', '11', 'final PCR plate')

    range = str(pip.max_volume)
    tiprack_map = {
        '10': {
            'standard': 'opentrons_96_tiprack_10ul',
            'filter': 'opentrons_96_filtertiprack_20ul'
        },
        '20': {
            'standard': 'opentrons_96_tiprack_20ul',
            'filter': 'opentrons_96_filtertiprack_20ul'
        },
        '50': {
            'standard': 'opentrons_96_tiprack_300ul',
            'filter': 'opentrons_96_filtertiprack_200ul'
        },
        '300': {
            'standard': 'opentrons_96_tiprack_300ul',
            'filter': 'opentrons_96_filtertiprack_200ul'
        },
        '1000': {
            'standard': 'opentrons_96_tiprack_1000ul',
            'filter': 'opentrons_96_filtertiprack_1000ul'
        }
    }

    # load labware
    transfer_info = [[val.strip().lower() for val in line.split(',')]
                     for line in transfer_csv.splitlines()
                     if line.split(',')[0].strip()][1:]
    for line in transfer_info:
        s_lw, s_slot = line[:2]
        if not int(s_slot) in ctx.loaded_labwares:
            ctx.load_labware(s_lw.lower(), s_slot)

    # load tipracks in remaining slots
    tiprack_type = tiprack_map[range][tip_type]
    tipracks = []
    for slot in [1, 2, 3, 4, 5, 6, 7, 8]:
        if slot not in ctx.loaded_labwares:
            tipracks.append(ctx.load_labware(tiprack_type, str(slot)))
    pip.tip_racks = tipracks

    tip_count = 0
    pickups_per_rack = 96 if pip.type == 'single' else 12
    tip_max = len(tipracks*pickups_per_rack)

    def pick_up():
        nonlocal tip_count
        if tip_count == tip_max:
            ctx.pause('Please refill tipracks before resuming.')
            pip.reset_tipracks()
            tip_count = 0
        pip.pick_up_tip()
        tip_count += 1

    def parse_well(well):
        letter = well[0]
        number = well[1:]
        return letter.upper() + str(int(number))

    if tip_reuse == 'never':
        pick_up()
    for line in transfer_info:
        _, s_slot, s_well, h, d_well = line[:5]
        source = ctx.loaded_labwares[
            int(s_slot)].wells_by_name()[parse_well(s_well)].bottom(float(h))
        dest = final_plate.wells_by_name()[parse_well(d_well)]
        if tip_reuse == 'always':
            pick_up()
        pip.transfer(float(sample_vol), source, dest, new_tip='never')
        if tip_reuse == 'always':
            pip.drop_tip()
    if pip.hw_pipette['has_tip']:
        pip.drop_tip()

    # transfer primer to sample wells
    primer_pip = p20 if pipette_type != 'p20_single_gen2' else pip
    for line in transfer_info:
        _, s_slot, s_well, h, d_well = line[:5]
        if pip.type == 'multi':
            col = d_well[1:]
            destinations = [
                well for well in final_plate.columns_by_name()[col]]
        else:
            destinations = [final_plate.wells_by_name()[parse_well(d_well)]]
        for d in destinations:
            primer_pip.transfer(primer_vol, primer.bottom(2), dest)

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
    filename = f"detailed_action_json/0e696e.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)