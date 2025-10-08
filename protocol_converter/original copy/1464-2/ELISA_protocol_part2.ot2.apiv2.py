import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/1464-2/ELISA_protocol_part2.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Antibody Addition',
    'author': 'Alise <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.14'
}


def run(ctx):
    [number_of_standards, concentration_csv] = get_values(  # noqa: F821
     'number_of_standards', 'concentration_csv')

    # labware setup
    tuberack_4 = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '4')
    deep_plates = [ctx.load_labware('nest_96_wellplate_2ml_deep', slot)
                   for slot in ['5', '6']]
    trough = ctx.load_labware('nest_12_reservoir_15ml', '8')
    plate = ctx.load_labware(
        'corning_96_wellplate_360ul_flat', '9')

    tipracks_300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
                    for slot in ['3']]
    tiprack_m300 = ctx.load_labware('opentrons_96_tiprack_300ul', '7')

    # instruments setup
    m300 = ctx.load_instrument(
        'p300_multi_gen2',
        mount='left',
        tip_racks=[tiprack_m300])
    p300 = ctx.load_instrument(
        'p300_single',
        mount='right',
        tip_racks=tipracks_300)

    # reagent setup
    tubes = [well for row in tuberack_4.rows() for well in row]
    water = tubes[0]
    diluent = tubes[1]
    standards = tubes[2:2 + number_of_standards]
    samples = tubes[2 + number_of_standards:]
    antibody = trough.wells('A1')

    # define elution pool
    dil_dests = [row for deep_plate in deep_plates
                 for row in deep_plate.rows()]
    conc_lists = [[int(cell) for cell in line.split(',') if cell]
                  for line in concentration_csv.splitlines() if line]
    concs = [5, 10, 25, 50, 100, 500, 1000, 5000, 10000, 25000, 50000, 100000]

    samples = [
        row[concs.index(conc)]
        for concentrations, row in zip(conc_lists, dil_dests)
        for conc in concentrations
        ]

    dests = [
        [plate.columns()[index][num], plate.columns()[index+1][num]]
        for index in range(0, 12, 2) for num in range(8)
        ]

    """
    Adding Enzyme Conjugate Reagent
    """
    num_cols = math.ceil((2 + number_of_standards + len(samples)) / 8) * 2
    m300.distribute(100, antibody,
                    plate.columns()[:num_cols],
                    blow_out=antibody)

    """
    Adding Water
    """
    p300.distribute(50, water, dests[0])
    dests.pop(0)

    """
    Adding Dilution Buffer
    """
    p300.distribute(50, diluent, dests[0])
    dests.pop(0)

    """
    Adding HCP Standards
    """
    ctx.comment('hcp')
    for standard in standards:
        p300.distribute(50, standard, dests[0])
        dests.pop(0)

    """
    Adding Samples
    """
    for sample, chunk in zip(samples, dests):
        p300.pick_up_tip()
        p300.aspirate(130, sample)
        for well in chunk:
            p300.dispense(50, well)
        p300.drop_tip()

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
    filename = f"detailed_action_json/1464-2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
        # dests.pop(0)