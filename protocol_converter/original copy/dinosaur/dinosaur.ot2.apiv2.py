import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/dinosaur/dinosaur.ot2.apiv2.py"

metadata = {
    'protocolName': 'Dinosaur',
    'author': 'Opentrons <protocols@opentrons.com>',
    'description': 'Draw a picture of a dinosaur',
    'apiLevel': '2.9'
}


def run(ctx):

    [p300_mount, tip_type, plate_type] = get_values(  # noqa: F821
        "p300_mount", "tip_type", "plate_type")

    # Load Labware
    tiprack = ctx.load_labware(tip_type, 6)
    plate = ctx.load_labware(plate_type, 3)
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', 8)

    # Load Pipette
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount,
                               tip_racks=[tiprack])

    # Solutions
    green = reservoir['A1']
    blue = reservoir['A2']

    # Wells to dispense green
    green_wells = [well for well in plate.wells(
        'E1', 'D2', 'E2', 'D3', 'E3', 'F3', 'G3', 'H3',
        'C4', 'D4', 'E4', 'F4', 'G4', 'H4', 'C5', 'D5',
        'E5', 'F5', 'G5', 'C6', 'D6', 'E6', 'F6', 'G6',
        'C7', 'D7', 'E7', 'F7', 'G7', 'D8', 'E8', 'F8',
        'G8', 'H8', 'E9', 'F9', 'G9', 'H9', 'F10', 'G11',
        'H12')]

    # Wells to dispense blue
    blue_wells = [well for well in plate.wells(
                  'C3', 'B4', 'A5', 'B5', 'B6', 'A7', 'B7',
                  'C8', 'C9', 'D9', 'E10', 'E11', 'F11', 'G12')]

    # Distribute green solution to wells
    p300.distribute(50, green, green_wells, disposal_vol=0, blow_out=True)
    # Distribute blue solution to wells
    p300.distribute(50, blue, blue_wells, disposal_vol=0, blow_out=True)

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
    filename = f"detailed_action_json/dinosaur.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)