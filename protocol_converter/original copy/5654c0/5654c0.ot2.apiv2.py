import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/5654c0/5654c0.ot2.apiv2.py"

metadata = {
    'protocolName': 'DNA Normalization from .csv',
    'author': 'Sakib <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.8'
}


def run(ctx):

    [dna_csv, p300_mount, p20_mount] = get_values(  # noqa: F821
        "dna_csv", "p300_mount", "p20_mount")

    # Load Labware
    tiprack_300ul = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
                     for slot in range(1, 3)]
    tiprack_20ul = [ctx.load_labware('opentrons_96_tiprack_20ul', slot)
                    for slot in range(3, 5)]

    plates = {
        'LC 96-well plate': ctx.load_labware(
            'thermofisher_96_skirted_pcr_200ul',
            5, label='LC 96-well plate'),
        'HC 96-well plate': ctx.load_labware(
            'thermofisher_96_skirted_pcr_200ul',
            6, label='HC 96-well plate'),
        'water': ctx.load_labware('agilent_1_reservoir_290ml', 7,
                                  label='water'),
        'LC Dil Plate': ctx.load_labware('thermofisher_96_skirted_pcr_200ul',
                                         8, label='LC Dil Plate'),
        'HC Dil Plate': ctx.load_labware('thermofisher_96_skirted_pcr_200ul',
                                         9, label='HC Dil Plate'),
        'Norm Plate': ctx.load_labware('thermofisher_96_skirted_pcr_200ul',
                                       10, label='Norm Plate')
    }

    # Load Pipettes
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount,
                               tip_racks=tiprack_300ul)
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount,
                              tip_racks=tiprack_20ul)

    # Transfer 90 uL of Water to LC Dil Plate and HC Dil Plate (1)
    p300.transfer(90, plates['water'].wells(), [plates['LC Dil Plate'].wells(),
                                                plates[
                                                    'HC Dil Plate'].wells()])

    # Parse DNA Norm CSV File
    data = [[val.strip() for val in line.split(',')] for line in
            dna_csv.splitlines()[1:] if line and line.split(',')[0]]
    lc_plates = []
    hc_plates = []
    water_data = []

    for row in data:
        if row[0].lower().strip() == 'water':
            water_data.append(row)
        elif row[0].lower().strip() == 'lc 96-well plate':
            lc_plates.append(row)
        elif row[0].lower().strip() == 'hc 96-well plate':
            hc_plates.append(row)

    # Transfer Water (2)
    for row in water_data:
        s_plate, d2_vol, d2_plate, d2_well = row[0], row[10], row[11], row[12]

        d2_vol = float(d2_vol)
        s_plate = plates[s_plate]
        d2_plate = plates[d2_plate]

        pip = p300 if d2_vol > 20 else p20
        pip.transfer(d2_vol, plates['water'].wells(),
                     d2_plate.wells_by_name()[d2_well])

    # Transfer DNA from LC Plates to LC Dil Plates (3)
    for row in lc_plates:
        s_plate, s_well = row[0], row[1]
        d1_vol, d1_plate, d1_well = row[5], row[6], row[7]
        d2_vol, d2_plate, d2_well = row[10], row[11], row[12]

        d1_vol = float(d1_vol)
        s_plate = plates[s_plate]
        d1_plate = plates[d1_plate]

        pip = p300 if d1_vol > 20 else p20
        pip.transfer(d1_vol, s_plate.wells_by_name()[s_well],
                     d1_plate.wells_by_name()[d1_well])

    # Transfer DNA from HC Plates to HC Dil Plates (4)
    for row in hc_plates:
        s_plate, s_well = row[0], row[1]
        d1_vol, d1_plate, d1_well = row[5], row[6], row[7]
        d2_vol, d2_plate, d2_well = row[10], row[11], row[12]

        d1_vol = float(d1_vol)
        s_plate = plates[s_plate]
        d1_plate = plates[d1_plate]

        pip = p300 if d1_vol > 20 else p20
        pip.transfer(d1_vol, s_plate.wells_by_name()[s_well],
                     d1_plate.wells_by_name()[d1_well])

    # Transfer DNA from LC Plate to Norm (5)
    for row in lc_plates:
        s_plate, s_well = row[0], row[1]
        d2_vol, d2_plate, d2_well = row[10], row[11], row[12]

        d2_vol = float(d2_vol)
        s_plate = plates[s_plate]
        d2_plate = plates[d2_plate]

        pip = p300 if d2_vol > 20 else p20
        pip.transfer(d2_vol, s_plate.wells_by_name()[s_well],
                     d2_plate.wells_by_name()[d2_well])

    # Transfer DNA from LC Dil to Norm (6)
    for row in lc_plates:
        d1_plate, d1_well = row[6], row[7]
        d2_vol, d2_plate, d2_well = row[10], row[11], row[12]

        d2_vol = float(d2_vol)
        d1_plate = plates[d1_plate]
        d2_plate = plates[d2_plate]

        pip = p300 if d2_vol > 20 else p20
        pip.transfer(d2_vol, d1_plate.wells_by_name()[d1_well],
                     d2_plate.wells_by_name()[d2_well])

    # Transfer DNA from HC Plate to Norm (7)
    for row in hc_plates:
        s_plate, s_well = row[0], row[1]
        d2_vol, d2_plate, d2_well = row[10], row[11], row[12]

        d2_vol = float(d2_vol)
        s_plate = plates[s_plate]
        d2_plate = plates[d2_plate]

        pip = p300 if d2_vol > 20 else p20
        pip.transfer(d2_vol, s_plate.wells_by_name()[s_well],
                     d2_plate.wells_by_name()[d2_well])

    # Transfer DNA from HC Dil to Norm (8)
    for row in hc_plates:
        d1_plate, d1_well = row[6], row[7]
        d2_vol, d2_plate, d2_well = row[10], row[11], row[12]

        d2_vol = float(d2_vol)
        d1_plate = plates[d1_plate]
        d2_plate = plates[d2_plate]

        pip = p300 if d2_vol > 20 else p20
        pip.transfer(d2_vol, d1_plate.wells_by_name()[d1_well],
                     d2_plate.wells_by_name()[d2_well])

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
    filename = f"detailed_action_json/5654c0.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)