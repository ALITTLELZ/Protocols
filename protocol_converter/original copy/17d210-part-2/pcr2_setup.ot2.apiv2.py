import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/17d210-part-2/pcr2_setup.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Verogen ForenSeq DNA Signature Prep Kit Part 2/5:  PCR2 Setup',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.10'
}


def run(ctx):

    [num_samples, m20_mount, m300_mount, index_vol,
     pcr2_buffer_vol, udi_start_col] = get_values(  # noqa: F821
        'num_samples', 'm20_mount', 'm300_mount', 'index_vol',
        'pcr2_buffer_vol', 'udi_start_col')
    # num_samples = 48
    # m20_mount = 'left'
    # m300_mount = 'right'
    # index_vol = 8.0
    # pcr2_buffer_vol = 27.0

    # load labware
    pcr2_buffer = ctx.load_labware('striptubes_96_wellplate_1000ul', '3',
                                   'PCR2 buffer tubes (strip column 1)').rows()[0][:1]
    pcr_plate = ctx.load_labware('eppendorfmetaladapter_96_wellplate_200ul',
                                 '9', 'PCR Plate')
    index_plate = ctx.load_labware('udiplate_96_wellplate_200ul', '6',
                                   'UDI plate')
    tips20m = [ctx.load_labware('opentrons_96_filtertiprack_20ul', '5')]
    tips300m = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '2')]

    # load pipette
    if m300_mount == m20_mount:
        raise Exception('Pipette mounts cannot match.')
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount, tip_racks=tips20m)
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount,
                               tip_racks=tips300m)

    m300.default_speed = 400
    m20.default_speed = 400

    num_cols = math.ceil(num_samples/8)
    indices = index_plate.rows()[0][udi_start_col-1:udi_start_col-1+num_cols]
    samples = pcr_plate.rows()[0][:num_cols]

    # transfer indices
    for source, dest in zip(indices, samples):
        m20.transfer(index_vol, source, dest)
        ctx.max_speeds['Z'] = 40

    # transfer buffer
    for i, dest in enumerate(samples):
        m300.transfer(pcr2_buffer_vol, pcr2_buffer[0], dest,
                      mix_after=(5, pcr2_buffer_vol))

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
    filename = f"detailed_action_json/17d210-part-2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)