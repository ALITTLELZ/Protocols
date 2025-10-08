import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/5a3797-protocol-2/5a3797-protocol-2.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Protocol 2 - PCR setup',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.8'
}


def run(ctx):

    [m20_mount, samples, reservoir_height, pcr_plate_height,
        sample_plate_height] = get_values(  # noqa: F821
        "m20_mount", "samples", "reservoir_height",
        "pcr_plate_height", "sample_plate_height")

    reservoir_height = float(reservoir_height)
    pcr_plate_height = float(pcr_plate_height)
    sample_plate_height = float(sample_plate_height)
    samples = int(samples)
    columns = math.ceil(samples/8)

    # Load Labware
    tiprack1 = ctx.load_labware('opentrons_96_filtertiprack_20ul',
                                1, 'Tip Box 1')
    tiprack2 = ctx.load_labware('opentrons_96_filtertiprack_20ul',
                                2, 'Tip Box 2')
    mastermix = ctx.load_labware('96well_pcr_base_200ul_strip', 7)['A1']
    sample_plate = ctx.load_labware('kingfisher_96_deepwell_plate_2ml', 4)
    pcr_plate = ctx.load_labware(
                'thermofishermicroampfast96well0.1_96_wellplate_100ul', 5)

    # Load Pipette
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount,
                              tip_racks=[tiprack1, tiprack2])

    # Aliquot 15uL of Mastermix
    m20.pick_up_tip(tiprack1['A1'])
    for pcr_well in pcr_plate.rows()[0][:columns]:
        m20.transfer(15, mastermix.bottom(reservoir_height),
                     pcr_well.bottom(pcr_plate_height), new_tip='never')
    m20.drop_tip()

    # Aliquot 10 uL of Sample
    for source, dest, tip in zip(sample_plate.rows()[0][:columns],
                                 pcr_plate.rows()[0][:columns],
                                 tiprack2.rows()[0][:columns]):
        m20.pick_up_tip(tip)
        m20.transfer(10, source.bottom(sample_plate_height),
                     dest.bottom(pcr_plate_height), new_tip='never')
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
    filename = f"detailed_action_json/5a3797-protocol-2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)