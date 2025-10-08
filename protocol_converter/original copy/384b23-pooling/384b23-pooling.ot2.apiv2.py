import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/384b23-pooling/384b23-pooling.ot2.apiv2.py"

metadata = {
    'protocolName': 'Sample Pooling Down Column',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(ctx):

    [use_tuberack_A, tuberackA_tube, num_rows_A,
     use_tuberack_B, tuberackB_tube, num_rows_B,
     delay, asp_height, p300_mount] = get_values(  # noqa: F821
            "use_tuberack_A", "tuberackA_tube", "num_rows_A",
            "use_tuberack_B", "tuberackB_tube",
            "num_rows_B", "delay", "asp_height", "p300_mount")

    num_rows_A = int(num_rows_A)
    num_rows_B = int(num_rows_B)

    # load labware
    tuberack_A = ctx.load_labware(tuberackA_tube, '1',
                                  label='Tuberack A')
    tuberack_B = ctx.load_labware(tuberackB_tube, '2', label='Tuberack B')
    tiprack = ctx.load_labware('opentrons_96_filtertiprack_200ul', '4')

    # load instrument
    p300 = ctx.load_instrument('p300_single_gen2',
                               p300_mount, tip_racks=[tiprack])
    p300.well_bottom_clearance.aspirate = asp_height
    print(tuberack_B.wells())

    # protocol
    if use_tuberack_A:
        for i in range(0, num_rows_A):
            for j, well in enumerate(tuberack_A.rows()[i][:5]):
                p300.pick_up_tip()
                p300.aspirate(100, well)
                ctx.delay(seconds=delay)
                p300.dispense(100, tuberack_A.rows()[i][5])
                if j == 4:
                    p300.mix(15, 200, tuberack_A.rows()[i][5])
                p300.drop_tip()

    if use_tuberack_B:
        for i in range(0, num_rows_B):
            for j, well in enumerate(tuberack_B.rows()[i][:5]):
                p300.pick_up_tip()
                p300.aspirate(100, well)
                ctx.delay(seconds=delay)
                p300.dispense(100, tuberack_B.rows()[i][5])
                if j == 4:
                    p300.mix(15, 200, tuberack_B.rows()[i][5])
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
    filename = f"detailed_action_json/384b23-pooling.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)