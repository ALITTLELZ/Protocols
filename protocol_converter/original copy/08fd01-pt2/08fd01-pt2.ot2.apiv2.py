import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/08fd01-pt2/08fd01-pt2.ot2.apiv2.py"

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
    pcr_plate = ctx.load_labware(
                'custom_384_wellplate_50ul', 8)
    pool_plate = ctx.load_labware(
                'custom_384_wellplate_50ul', 9)
    index_plate = ctx.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', 7)

    reservoir = ctx.load_labware('nest_12_reservoir_15ml', 5)

    tipracks = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
                for slot in [2, 4, 6, 10, 11]]

    mmx_tiprack = ctx.load_labware('opentrons_96_filtertiprack_20ul', 3)

    # instruments
    p20 = ctx.load_instrument('p20_multi_gen2', p20_mount, tip_racks=tipracks)

    # protocol
    ctx.comment('\nADDING MASTERMIX\n\n')
    p20.pick_up_tip(mmx_tiprack.wells()[0])
    for i in range(2):
        for col in pool_plate.rows()[i]:
            p20.aspirate(16, reservoir.wells()[0])
            p20.dispense(16, col)
            p20.blow_out()
        ctx.comment('\n')
    p20.drop_tip()

    ctx.comment('\nADDING INDEX\n\n')
    index_row_order = [0, 0, 1, 1]
    index_col_order = [0, 1, 0, 1]

    col_ctr = 0

    for col_96_plate in range(12):
        p20.pick_up_tip()
        p20.aspirate(8, index_plate.rows()[0][col_96_plate])
        for index_row, index_col in zip(index_row_order, index_col_order):
            p20.dispense(2,
                         pcr_plate.rows()[index_row][index_col+col_ctr],
                         rate=0.5)
        col_ctr += 2
        p20.return_tip()

    ctx.comment('\nADDING SAMPLE\n\n')

    for i in range(2):
        for s_col, d_col in zip(pool_plate.rows()[i], pcr_plate.rows()[i]):
            p20.pick_up_tip()
            p20.aspirate(2, s_col)
            p20.dispense(2, d_col)
            p20.blow_out()
            p20.return_tip()
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
    filename = f"detailed_action_json/08fd01-pt2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)