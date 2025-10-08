import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/08fd01/08fd01.ot2.apiv2.py"

# flake8: noqa

metadata = {
    'protocolName': 'PCR Prep and Pooling with 384 Plates',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [p20_mount] = get_values(  # noqa: F821
        "p20_mount")

    # labware
    pcr_plates = [ctx.load_labware(
            'custom_384_wellplate_50ul', slot)
            for slot in [1, 4, 8, 10]]
    pool_plate = ctx.load_labware(
                'custom_384_wellplate_50ul', 7)

    reservoir = ctx.load_labware('nest_12_reservoir_15ml', 6)

    tipracks = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
                for slot in [2, 5, 9, 11]]

    water_tiprack = ctx.load_labware('opentrons_96_filtertiprack_20ul', 3)

    # instruments
    p20 = ctx.load_instrument('p20_multi_gen2', p20_mount, tip_racks=tipracks)

    # protocol
    pcr_row_nums = [0, 0, 1, 1]*3
    pcr_col_nums = []

    for i in range(0, 24, 2):
        for _ in range(2):
            pcr_col_nums.append(i)
            pcr_col_nums.append(i+1)

    plate_1_pool_wells = pool_plate.rows()[0][:24:2]
    p1_pool_match = []
    plate_2_pool_wells = pool_plate.rows()[0][1:24:2]
    p2_pool_match = []
    plate_3_pool_wells = pool_plate.rows()[1][:24:2]
    p3_pool_match = []
    plate_4_pool_wells = pool_plate.rows()[1][1:24:2]
    p4_pool_match = []

    for ele in plate_1_pool_wells:
        p1_pool_match.extend([ele, ele, ele, ele])

    for ele in plate_2_pool_wells:
        p2_pool_match.extend([ele, ele, ele, ele])

    for ele in plate_3_pool_wells:
        p3_pool_match.extend([ele, ele, ele, ele])

    for ele in plate_4_pool_wells:
        p4_pool_match.extend([ele, ele, ele, ele])

    pool_schemes = [p1_pool_match, p2_pool_match, p3_pool_match, p4_pool_match]

    ctx.comment('\nADDING WATER\n\n')
    p20.pick_up_tip(water_tiprack.wells()[0])
    for i in range(2):
        for col in pool_plate.rows()[i]:
            p20.aspirate(12, reservoir.wells()[0])
            p20.dispense(12, col)
            p20.blow_out()
        ctx.comment('\n')
    p20.drop_tip()

    ctx.comment('\nADDING SAMPLE\n\n')
    for plate, pool_scheme in zip(pcr_plates, pool_schemes):

        for i, (pcr_row_start, pcr_col_start, pool) in enumerate(zip(pcr_row_nums*4, pcr_col_nums, pool_scheme)):

            if i % 4 == 0:
                if p20.has_tip:
                    p20.return_tip()
                p20.pick_up_tip()

            source_well = plate.rows()[pcr_row_start][pcr_col_start]
            p20.aspirate(3, source_well)
            p20.dispense(3, pool)
            p20.blow_out()

        ctx.comment('\n')

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
    filename = f"detailed_action_json/08fd01.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)