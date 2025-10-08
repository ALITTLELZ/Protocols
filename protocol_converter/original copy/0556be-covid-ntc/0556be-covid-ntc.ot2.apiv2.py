import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0556be-covid-ntc/0556be-covid-ntc.ot2.apiv2.py"

metadata = {
    'protocolName': 'COVID NTC Protocol - NFW',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.8'
}


def run(ctx):

    [p1000_mount, component_1_volume, asp_height] = get_values(  # noqa: F821
        "p1000_mount", "component_1_volume", "asp_height")

    asp_height = float(asp_height)

    # Load Labware
    tuberack = ctx.load_labware(
        'opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical', 10)['A1']
    dest_tubes = ctx.load_labware(
        'opentrons_24_aluminumblock_generic_2ml_screwcap', 11)
    tiprack_1000ul = ctx.load_labware('opentrons_96_filtertiprack_1000ul', 1)

    # Load Instruments
    p1000 = ctx.load_instrument('p1000_single_gen2', 'right',
                                tip_racks=[tiprack_1000ul])

    # Transfer Component 1 to Destination Tubes
    p1000.transfer(float(component_1_volume), tuberack.bottom(asp_height),
                   dest_tubes.wells())

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
    filename = f"detailed_action_json/0556be-covid-ntc.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)