import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/2aee74-96-2/olink.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Olink Target 96 Part 2/3: Extension',
    'author': 'Nick <ndiehl@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    num_samples, plate_type, m300_mount = get_values(  # noqa: F821
        'num_samples', 'plate_type', 'm300_mount')

    if not 1 <= num_samples <= 96:
        raise Exception('Invalid number of samples (1-96)')

    ext_mix = ctx.load_labware(
        'nest_12_reservoir_15ml', '5',
        'reservoir for extension mix (channel 1)').wells()[0]
    inc_plate = ctx.load_labware(plate_type, '2', 'incubation plate')
    tipracks300 = [ctx.load_labware('opentrons_96_tiprack_300ul', '6')]

    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount,
                               tip_racks=tipracks300)

    num_cols = math.ceil(num_samples/8)

    ctx.comment('Bring the Incubation Plate to room temperature, spin at 400 x  g for 1 min. Preheat the PCR machine.')
    ctx.comment('Vortex the Extension mix and pour into a multi-channel  pipette reservoir.')

    m300.pick_up_tip()
    m300.aspirate(20, ext_mix)
    for col in inc_plate.rows()[0][:num_cols]:
        m300.aspirate(96, ext_mix)
        m300.dispense(96, col.top(-1))
    m300.drop_tip()

    ctx.comment('Seal the plate with an adhesive plastic film, vortex  thoroughly ensuring that all wells are mixed, and spin down.')
    ctx.comment('Place the Incubation Plate in the thermal cycler, and start  the PEA program (50°C 20 min, 95°C 5 min (95°C 30s, 54°C 1 min, 60°C 1 min) \
x17, 10°C hold).')

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
    filename = f"detailed_action_json/2aee74-96-2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)