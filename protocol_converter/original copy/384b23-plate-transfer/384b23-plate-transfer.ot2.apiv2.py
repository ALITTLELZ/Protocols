import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/384b23-plate-transfer/384b23-plate-transfer.ot2.apiv2.py"

metadata = {
    'protocolName': 'Sample Transfer to 96 Well-Plate',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(ctx):

    [num_samp, vol_dispensed, delay,
        asp_height, p300_mount, p1000_mount] = get_values(  # noqa: F821
             "num_samp", "vol_dispensed", "delay",
             "asp_height", "p300_mount", "p1000_mount")

    if not 1 <= num_samp <= 96:
        raise Exception("Enter a sample number between 1-96")

    # load labware
    tuberack_96 = [ctx.load_labware('6x4_0.6inch_t6', slot, label='Tuberack')
                   for slot in ['1', '4', '7', '10']]
    plate = ctx.load_labware('microamp_96_wellplate_100ul', '2')
    tiprack1000 = ctx.load_labware('opentrons_96_tiprack_1000ul', '5')
    tiprack200 = ctx.load_labware('opentrons_96_filtertiprack_200ul', '3')

    # load instrument
    p1000 = ctx.load_instrument('p1000_single_gen2',
                                p1000_mount, tip_racks=[tiprack1000])
    p300 = ctx.load_instrument('p300_single_gen2',
                               p300_mount, tip_racks=[tiprack200])
    p1000.well_bottom_clearance.aspirate = asp_height
    p300.well_bottom_clearance.aspirate = asp_height

    tubes = [tube for tuberack in tuberack_96 for tube in tuberack.wells()]
    if vol_dispensed < 100:
        pip = p300
    else:
        pip = p1000

    # protocol
    for samp, dest in zip(tubes, plate.wells()):
        pip.pick_up_tip()
        pip.aspirate(200, samp)
        ctx.delay(seconds=delay)
        pip.dispense(200, dest)
        pip.drop_tip()

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
    filename = f"detailed_action_json/384b23-plate-transfer.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)