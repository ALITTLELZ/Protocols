import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/00bbd7/00bbd7.ot2.apiv2.py"

"""PROTOCOL."""
metadata = {
    'protocolName': 'Covid-19 Saliva Sample Plating',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.10'
}


def run(ctx):
    """PROTOCOL."""
    [num_samp, delay_after_asp,
        asp_rate, disp_rate, p1000_mount] = get_values(  # noqa: F821
        "num_samp", "delay_after_asp", "disp_rate", "asp_rate", "p1000_mount")

    # load labware
    plate = ctx.load_labware('nest_96_wellplate_2ml_deep', '1')
    tiprack = [ctx.load_labware('opentrons_96_tiprack_1000ul', '2')]
    tuberacks = [ctx.load_labware('opentrons_15_tuberack_15000ul',
                 slot) for slot in ['4', '5', '6', '7', '8', '9', '10']]

    # load instrument
    p1000 = ctx.load_instrument('p1000_single_gen2', 'left', tip_racks=tiprack)

    # protocol
    tubes_by_row = [tube for rack in tuberacks
                    for row in rack.rows() for tube in row]
    wells_by_row = [well for row in plate.rows() for well in row]

    p1000.flow_rate.aspirate = asp_rate*p1000.flow_rate.aspirate
    p1000.flow_rate.dispense = disp_rate*p1000.flow_rate.dispense

    for sample, dest_well in zip(tubes_by_row, wells_by_row[:num_samp]):
        p1000.pick_up_tip()
        p1000.aspirate(200, sample)
        ctx.delay(seconds=delay_after_asp)
        p1000.dispense(200, dest_well)
        p1000.blow_out()
        p1000.drop_tip()

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
    filename = f"detailed_action_json/00bbd7.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)