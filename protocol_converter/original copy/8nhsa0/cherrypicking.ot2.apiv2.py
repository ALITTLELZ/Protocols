import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/8nhsa0/cherrypicking.ot2.apiv2.py"

metadata = {
    'protocolName': 'Cherrypicking',
    'author': 'Nick <ndiehl@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.3'
}


def run(ctx):

    p50_mount, input_csv, air_gap = get_values(  # noqa: F821
        'p50_mount', 'input_csv', 'air_gap')

    # parse csv
    data = [
        [val.strip() for val in line.split(',')]
        for line in input_csv.splitlines()[1:]]
    occupied_slots = [int(line[ind]) for line in data for ind in [0, 2]]
    for slot in occupied_slots:
        if slot not in ctx.loaded_labwares:
            ctx.load_labware('biorad_96_wellplate_200ul_pcr', str(slot))

    tipracks = []
    for slot in range(1, 12):
        if slot not in ctx.loaded_labwares:
            tipracks.append(
                ctx.load_labware('opentrons_96_tiprack_300ul', str(slot),
                                 '300ul tiprack'))

    p50 = ctx.load_instrument('p50_single', p50_mount, tip_racks=tipracks)

    tip_max = len(tipracks)*96
    tip_count = 0

    def pick_up():
        nonlocal tip_count
        if tip_count == tip_max:
            ctx.pause('Refill tipracks before resuming.')
            p50.reset_tipracks()
            tip_count = 0
        tip_count += 1
        p50.pick_up_tip()

    for line in data:
        s_slot, s_well, d_slot, d_well, vol = line[:5]
        source = ctx.loaded_labwares[int(s_slot)].wells_by_name()[s_well]
        dest = ctx.loaded_labwares[int(d_slot)].wells_by_name()[d_well]
        pick_up()
        p50.transfer(float(vol), source, dest, air_gap=air_gap,
                     new_tip='never')
        p50.air_gap(5)
        p50.drop_tip()

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
    filename = f"detailed_action_json/8nhsa0.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)