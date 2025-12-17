import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0a9b58/0a9b58.ot2.apiv2.py"

metadata = {
    'protocolName': 'Pooling and Normalization via CSV',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [protocol, csv_samp, p20_mount, p300_mount] = get_values(  # noqa: F821
        "protocol", "csv_samp", "p20_mount", "p300_mount")

    if "normalization" in csv_samp.lower() and protocol == "pooling":
        raise Exception("""
                           There appears to be the word "normalization"
                           in your csv, although you have selected "pooling"
                           as the protocol. Please input the correct csv for
                           the "pooling" protocol.
                           """)
    if "pool" in csv_samp.lower() and protocol == "normalization":
        raise Exception("""
                           There appears to be the word "pool" in your csv,
                           although you have selected "normalization"
                           as the protocol. Please input the correct csv for
                           the "pooling" protocol.
                           """)

    csv_lines = [[val.strip() for val in line.split(',')]
                 for line in csv_samp.splitlines()
                 if line.split(',')[0].strip()][2:]

    # labware

    if protocol == "normalization":
        water = ctx.load_labware('agilent_1_reservoir_290ml', 1).wells()[0]
        source_plate = ctx.load_labware('biorad_96_wellplate_200ul_pcr', 2)
        dest_plate = ctx.load_labware('biorad_96_wellplate_200ul_pcr', 3)
        tips = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
                for slot in [4, 5]]
        tips3 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
                 for slot in [6]]

    if protocol == "pooling":
        source_plate = ctx.load_labware('biorad_96_wellplate_200ul_pcr', 2)
        dest_plate = ctx.load_labware('biorad_96_wellplate_200ul_pcr', 3)
        tips = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
                for slot in [4]]

    # pipettes
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount, tip_racks=tips)
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount, tip_racks=tips3)

    # protocol
    if protocol == "normalization":

        # transfer water
        ctx.comment('\n ------------- TRANSFERRING WATER ------------ \n\n')
        for line in csv_lines:
            water_vol = float(line[1])
            dest_well = dest_plate.wells_by_name()[line[3]]

            if water_vol <= 0.0:
                continue

            else:
                pip = p300 if water_vol > 20 else p20
                if not pip.has_tip:
                    pip.pick_up_tip()
                pip.transfer(water_vol, water, dest_well, new_tip='never')

        if p20.has_tip:
            p20.drop_tip()
        if p300.has_tip:
            p300.drop_tip()

        # dna
        ctx.comment('\n ------------- TRANSFERRING DNA ------------ \n\n')
        for line in csv_lines:

            dna_vol = float(line[2])
            source_well = source_plate.wells_by_name()[line[0]]
            dest_well = dest_plate.wells_by_name()[line[3]]

            if dna_vol <= 0.0:
                continue

            if dna_vol < 1.0:
                raise Exception("DNA volume found which is less than 1.0ul")

            else:
                pip = p300 if water_vol > 20 else p20
                pip.pick_up_tip()
                pip.transfer(dna_vol, source_well,
                             dest_well, new_tip='never')
                pip.drop_tip()

    if protocol == "pooling":

        # dna
        ctx.comment('\n ------------- POOLING DNA ------------ \n\n')
        for line in csv_lines:

            dna_vol = float(line[3])
            source_well = source_plate.wells_by_name()[line[0]]
            dest_well = dest_plate.wells_by_name()[line[4]]

            if dna_vol <= 0.0:
                continue

            if dna_vol <= 1.0:
                raise Exception("DNA volume found which is less than 1.0ul")

            else:
                p20.pick_up_tip()
                p20.transfer(dna_vol, source_well,
                             dest_well, new_tip='never')
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
    filename = f"detailed_action_json/0a9b58.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)