import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/kapa-qubit/kapa-qubit.ot2.apiv2.py"

metadata = {
    'protocolName': 'Kapa Qubit',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [num_col, m20_mount, m300_mount] = get_values(  # noqa: F821
        "num_col", "m20_mount", "m300_mount")

    # num_col = 3
    # m300_mount = 'left'
    # m20_mount = 'right'

    # labware
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', 3)
    dest_plate = ctx.load_labware('agilent_96_wellplate_270ul', 2)
    source_plate = ctx.load_labware('agilent_96_wellplate_270ul', 1)
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
               for slot in [7]]
    tips20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
              for slot in [9]]

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount,
                               tip_racks=tips200)
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount, tip_racks=tips20)

    # mapping
    buffer = reservoir['A1']
    standard1 = source_plate['A11']
    standard2 = source_plate['A12']
    sample_cols_source = source_plate.rows()[0][:num_col]
    sample_cols_dest = dest_plate.rows()[0][2:2+num_col]

    # transfer buffer to column 1 2 and sample columns
    m300.pick_up_tip()
    for col in dest_plate.rows()[0][:2]:
        m300.aspirate(190, buffer)
        m300.dispense(190, col)
    ctx.comment('\n\n')

    for col in sample_cols_dest:
        m300.aspirate(198, buffer)
        m300.dispense(198, col)
    m300.drop_tip()
    ctx.comment('\n\n')

    # transfer standards
    for standard, col in zip([standard1, standard2], dest_plate.rows()[0][:2]):
        m20.pick_up_tip()
        m20.aspirate(10, standard)
        m20.dispense(10, col)
        m20.mix(5, 20, col)
        m20.blow_out()
        m20.drop_tip()

    ctx.comment('\n\n')
    for s, d in zip(sample_cols_source, sample_cols_dest):
        m20.pick_up_tip()
        m20.aspirate(2, s)
        m20.dispense(2, d)
        m20.mix(5, 20, d)
        m20.blow_out()
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
    filename = f"detailed_action_json/kapa-qubit.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)