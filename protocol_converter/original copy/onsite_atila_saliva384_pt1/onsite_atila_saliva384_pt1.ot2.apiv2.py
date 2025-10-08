import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/onsite_atila_saliva384_pt1/onsite_atila_saliva384_pt1.ot2.apiv2.py"

from opentrons import protocol_api

metadata = {
    'protocolName': 'iAMP COVID-19 Detection Kit - Pt. 2',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx: protocol_api.ProtocolContext):

    [num_samp, reaction_plate,
        p20_mount] = get_values(  # noqa: F821
        "num_samp", "reaction_plate", "p20_mount")

    if not 1 <= num_samp <= 96:
        raise Exception("Enter a sample number 1-96")

    # LABWARE
    pcr_plate = ctx.load_labware(
                  reaction_plate, '9',
                  label='the PCR PLATE')
    sample_racks = [ctx.load_labware(
                      'opentrons_15_tuberack_5000ul',
                      slot, label="the SAMPLE RACK")
                    for slot in ['1', '2', '3', '4', '5', '6', '7']]

    # TIPRACKS
    tiprack20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', '10',
                                  label='20uL TIPRACK')]

    # INSTRUMENTS
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount,
                              tip_racks=tiprack20)

    # MAPPING
    all_sample_tubes = [tube
                        for rack in sample_racks
                        for tube in rack.wells()][:num_samp]

    # protocol

    ctx.comment('\n\n~~~~~~~~MOVING SAMPLES TO PLATE~~~~~~~~~\n')
    for sample, well in zip(all_sample_tubes, pcr_plate.wells()):
        p20.pick_up_tip()
        p20.aspirate(10, sample)
        p20.dispense(10, well)
        p20.blow_out()
        p20.touch_tip()
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
    filename = f"detailed_action_json/onsite_atila_saliva384_pt1.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)