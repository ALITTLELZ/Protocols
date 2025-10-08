import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/5829d7/5829d7.ot2.apiv2.py"

metadata = {
    'protocolName': 'Tube to Plate Viral Media Transfer',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.10'
}


def run(ctx):

    [num_samp, tube_asp_height, well_disp_height, flow_rate_asp,
        flow_rate_disp,
     p1000_mount] = get_values(  # noqa: F821
        "num_samp", "tube_asp_height", "well_disp_height", "flow_rate_asp",
        "flow_rate_disp", "p1000_mount")

    # load labware
    wellplate = ctx.load_labware('qiagen_96_wellplate_2250ul', '3')
    tiprack = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', '6')]
    tuberacks = [ctx.load_labware(
                 'nest_32_tuberack_8x15ml_8x15ml_8x15ml_8x15ml', slot)
                 for slot in ['1', '4', '7']]

    # load instruments
    p1000 = ctx.load_instrument('p1000_single_gen2', p1000_mount,
                                tip_racks=tiprack)
    p1000.flow_rate.aspirate = flow_rate_asp
    p1000.flow_rate.dispense = flow_rate_disp

    # PROTOCOL
    tubes = [tube for tuberack in tuberacks for row in tuberack.rows()
             for tube in row][:num_samp]
    wells = [well for row in wellplate.rows() for well in row]

    for tube, well in zip(tubes, wells):
        p1000.pick_up_tip()
        p1000.aspirate(200, tube.bottom(z=tube_asp_height))
        ctx.delay(seconds=1.5)
        p1000.dispense(200, well.bottom(z=well_disp_height))
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
    filename = f"detailed_action_json/5829d7.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)