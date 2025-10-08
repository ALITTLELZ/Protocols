import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/illumina-nextera-XT-library-prep-part1/nexteraXT_dna_library_prep_part1.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Illumina Nextera XT NGS Prep 1: Tagment Genomic DNA &  Amplify Libraries',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.2'
    }


def run(protocol_context):
    [p20_mount, m20_mount, number_of_samples] = get_values(  # noqa: F821
        'p20_mount', 'm20_mount', 'number_of_samples')

    # labware setup
    gDNA_plate = protocol_context.load_labware(
        'biorad_96_wellplate_200ul_pcr', '1', 'gDNA plate')
    out_plate = protocol_context.load_labware(
        'biorad_96_wellplate_200ul_pcr', '2', 'output plate')
    index_plate = protocol_context.load_labware(
        'biorad_96_wellplate_200ul_pcr', '4', 'index plate')
    tuberack = protocol_context.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '5',
        'reagent rack')
    tiprack_single = [
        protocol_context.load_labware('opentrons_96_tiprack_20ul', slot)
        for slot in ['3', '6', '7', '8']]
    tiprack_multi = [
        protocol_context.load_labware('opentrons_96_tiprack_20ul', slot)
        for slot in ['9', '10']]

    # reagent setup
    num_cols = math.ceil(number_of_samples/8)

    atm = tuberack.wells()[0]  # Amplicon Tagment Mix
    td = tuberack.wells()[1]  # Tagment DNA Buffer
    nt = tuberack.wells()[2]  # Neutralize Tagment Buffer
    npm = tuberack.wells()[3]  # Nextera PCR Master Mix
    indexes = index_plate.rows()[0][:num_cols]

    # pipette setup
    p20 = protocol_context.load_instrument(
        'p20_single_gen2', p20_mount, tip_racks=tiprack_single)
    m20 = protocol_context.load_instrument(
        'p20_multi_gen2', m20_mount, tip_racks=tiprack_multi)

    # define sample locations
    samples_multi = gDNA_plate.rows()[0][:num_cols]
    output_single = out_plate.wells()[:number_of_samples]
    output_multi = out_plate.rows()[0][:num_cols]

    """
    Tagment genomic DNA
    """
    # Add Tagment DNA Buffer to each well
    p20.transfer(10, td, output_single, blow_out=True)

    # Add normalized gDNA to each well
    m20.transfer(5, samples_multi, output_multi, new_tip='always')

    # Add ATM to each well
    p20.transfer(5, atm, output_single, mix_after=(5, 10), new_tip='always')

    protocol_context.pause("Centrifuge at 280 × g at 20°C for 1 minute. Place  on the preprogrammed thermal cycler and run the tagmentation program. When \
the sample reaches 10°C, immediately proceed to the next step because the  transposome is still active. Place the plate back to slot 2.")

    # Add Neutralize Tagment Buffer to each well
    p20.transfer(5, nt, output_single, mix_after=(5, 10), new_tip='always')

    protocol_context.pause("Centrifuge at 280 × g at 20°C for 1 minute. Place  the plate back on slot 2.")

    # Incubate at RT for 5 minutes
    protocol_context.delay(minutes=5)

    """
    Amplify Libraries
    """
    # Add each index
    m20.transfer(
        10, indexes, output_multi, mix_after=(5, 10), new_tip='always')

    # Add Nextera PCR Master Mix to each well
    p20.transfer(15, npm, output_single, mix_after=(2, 10))

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
    filename = f"detailed_action_json/illumina-nextera-XT-library-prep-part1.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)