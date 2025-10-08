import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/60d861-2/pcr_prep.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'CYP Induction, Part 2/3',
    'author': 'Nick <ndiehl@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.12'
}


def run(ctx):

    num_samples, m20_mount = get_values(  # noqa: F821
        'num_samples', 'm20_mount')

    tipracks20 = [
        ctx.load_labware('opentrons_96_tiprack_20ul', slot)
        for slot in ['1', '4', '7', '10']]
    source_plates = [
        ctx.load_labware('thermofishermicroamp_96_wellplate_200ul', slot,
                         f'source plate {i+1}')
        for i, slot in enumerate(['2', '3'])]
    dest_plates = [
        ctx.load_labware('thermofishermicroamp_96_wellplate_200ul', slot,
                         f'destination plate {i+1}')
        for i, slot in enumerate(['5', '6'])]
    rt_mix = ctx.load_labware('nest_1_reservoir_195ml', '8',
                              'RT mix').wells()[0]

    num_cols = math.ceil(num_samples/8)
    sources = [
        well for plate in source_plates for well in plate.rows()[0][:num_cols]]
    dests = [
        well for plate in dest_plates for well in plate.rows()[0][:num_cols]]

    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount,
                              tip_racks=tipracks20)

    m20.pick_up_tip()
    m20.aspirate(2, rt_mix)
    for d in dests:
        m20.aspirate(16, rt_mix)
        m20.dispense(16, d)
    m20.dispense(m20.current_volume, rt_mix.top())

    for s, d in zip(sources, dests):
        if not m20.has_tip:
            m20.pick_up_tip()
        m20.transfer(9, s, d, new_tip='never')
        m20.drop_tip()

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
    filename = f"detailed_action_json/60d861-2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)