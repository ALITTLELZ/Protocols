import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0dda91/0dda91.ot2.apiv2.py"

import math

metadata = {
    'protocolName': '16S Library pooling',
    'author': 'Parrish Payne <parrish.payne@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}

# Step 1: Use a single channel pipettor and a new tip each time, transfer
# 2-35 uL from the 96 well PCR plate to a single 2 mL snap tube
# Step 2: Repeat across the entire plate according to the .csv file


def run(ctx):

    [input_csv, p20_mount] = get_values(  # noqa: F821
        'input_csv', 'p20_mount')

    p20_mount = 'right'

    # labware
    tips = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
            for slot in [1, 4]]

    pcr_plate = ctx.load_labware(
        'biorad_96_wellplate_200ul_pcr', 2)

    tube_rack = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 3)

    mag_mod = ctx.load_module('magnetic module gen2', 6)   # not used
    mag_mod.disengage()

    # pipettes
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount, tips)

    # parse
    all_rows = [
        [val.strip().upper() for val in line.split(',')]
        for line in input_csv.splitlines()[1:]
        if line and line.split(',')[0]][1:]

    all_samples = [
        well
        for well in pcr_plate.wells()
        ]

    for row, source in zip(all_rows, all_samples):

        volume = float(row[2])
        dest = (row[3])

        if volume > 20:
            num_transfers = math.ceil(volume/p20.max_volume)
            transfer_vol = volume/num_transfers
            for _ in range(num_transfers):

                p20.pick_up_tip()
                p20.aspirate(transfer_vol, source)
                p20.dispense(transfer_vol, tube_rack.wells_by_name()[dest])
                p20.drop_tip()
        else:
            p20.pick_up_tip()
            p20.aspirate(volume, source)
            p20.dispense(volume, tube_rack.wells_by_name()[dest])
            p20.drop_tip()

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
    filename = f"detailed_action_json/0dda91.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)