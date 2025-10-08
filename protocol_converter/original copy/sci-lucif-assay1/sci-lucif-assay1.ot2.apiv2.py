import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/sci-lucif-assay1/sci-lucif-assay1.ot2.apiv2.py"

# flake8: noqa

metadata = {
    'protocolName': 'Luciferase Reporter Assay for NF-kB Activation - Protocol 1: Cell Culture Preparation',
    'author': 'Boren Lin, Opentrons',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}

TOTAL_COl = 12

def run(ctx):


    [p300_mount] = get_values(  # noqa: F821
        "p300_mount")

    # labware
    working_plate = ctx.load_labware('corning_96_wellplate_360ul_flat', 6,
                                     'working plate')
    cell_stock = ctx.load_labware('nest_12_reservoir_15ml', 3, 'cell stock')
    tiprack = ctx.load_labware('opentrons_96_tiprack_300ul', 8)
    p300 = ctx.load_instrument('p300_multi_gen2', p300_mount, tip_racks=[tiprack])

    cells_source = cell_stock.wells()[0]
    cells_final = working_plate.rows()[0][:TOTAL_COl]

    # protocol
    ctx.comment('\n\n\n~~~~~~~~TRANSFER CELLS~~~~~~~~\n')
    p300.pick_up_tip()
    p300.mix(5, 200, cells_source.bottom(z=5), rate = 3)
    p300.mix(5, 200, cells_source.bottom(z=2), rate = 3)

    for i in range(TOTAL_COl):
        p300.mix(3, 200, cells_source.bottom(z=1), rate = 3)
        p300.aspirate(100, cells_source.bottom(z=0.5), rate = 0.5)
        p300.air_gap(15)
        final = cells_final[i]
        p300.dispense(115, final.top(z=-2), rate = 0.75)
        p300.blow_out()
        p300.touch_tip()

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
    filename = f"detailed_action_json/sci-lucif-assay1.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)