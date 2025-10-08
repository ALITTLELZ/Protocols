import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/58d57d/58d57d.ot2.apiv2.py"

metadata = {
    'protocolName': 'Promega ADP-Glo Kinase Assay',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(ctx):

    [samples, liquid_A_vol, liquid_B_vol, liquid_C_vol,
        liquid_D_vol] = get_values(  # noqa: F821
        "samples", "liquid_A_vol", "liquid_B_vol",
        "liquid_C_vol", "liquid_D_vol")

    # Load Labware
    plate = ctx.load_labware("greiner_384_wellplate_130ul", 1)
    tiprack = ctx.load_labware("opentrons_96_tiprack_20ul", 2)
    tuberack = ctx.load_labware(
                "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", 4)

    # Load Pipette
    p20 = ctx.load_instrument("p20_single_gen2", "left", tip_racks=[tiprack])

    # Get wells by row
    sample_wells = [well for wells in plate.rows() for well in wells][:samples]

    # Reagents
    liquid_A = tuberack['A1']
    liquid_B = tuberack['B1']
    liquid_C = tuberack['C1']
    liquid_D = tuberack['D1']

    p20.transfer(liquid_A_vol, liquid_A, sample_wells, touch_tip=True)
    ctx.pause("Centrifuge Plate to Mix Liquid A")

    p20.transfer(liquid_B_vol, liquid_B, sample_wells, touch_tip=True)
    ctx.pause("Centrifuge Plate and Incubate for 60 minutes")

    p20.transfer(liquid_C_vol, liquid_C, sample_wells, touch_tip=True)
    ctx.pause("Incubate for 40 minutes")

    p20.transfer(liquid_D_vol, liquid_D, sample_wells, touch_tip=True)
    ctx.pause("Incubate for 30 minutes")

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
    filename = f"detailed_action_json/58d57d.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)