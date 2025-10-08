import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/68ce98/68ce98.ot2.apiv2.py"

metadata = {
    'protocolName': 'Custom Sample Transfer',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.8'
}


def run(ctx):

    [asp_speed, disp_speed, asp_height,
        disp_height] = get_values(  # noqa: F821
        "asp_speed", "disp_speed", "asp_height", "disp_height")

    asp_speed = float(asp_speed)
    disp_speed = float(disp_speed)
    asp_height = float(asp_height)
    disp_height = float(disp_height)

    # Load Labware
    plate1 = ctx.load_labware('waters_96_wellplate_2ml', 1, 'Plate 1')
    plate2 = ctx.load_labware('waters_96_wellplate_2ml', 2, 'Plate 2')
    tiprack = ctx.load_labware('opentrons_96_tiprack_300ul', 4)

    # Load Pipette
    m300 = ctx.load_instrument('p300_multi_gen2', 'left', tip_racks=[tiprack])

    # Get sample columns
    plate1_wells = plate1.rows()[0]
    plate2_wells = plate2.rows()[0]

    # Flow Rates
    m300.flow_rate.aspirate = asp_speed
    m300.flow_rate.dispense = disp_speed

    # Pre-Wet Tip with 300 uL
    # Transfer 750 uL to Plate 2
    for p1_well, p2_well in zip(plate1_wells, plate2_wells):
        m300.pick_up_tip()
        for _ in range(3):
            m300.aspirate(300, p1_well.bottom(z=asp_height))
            m300.move_to(p1_well.top())
            m300.dispense(300, p1_well.bottom(z=disp_height))
        m300.transfer(750, p1_well.bottom(z=asp_height),
                      p2_well.bottom(z=disp_height), air_gap=30,
                      touch_tip=True,
                      blow_out=True, blowout_location='destination well',
                      new_tip='never')
        m300.drop_tip()

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
    filename = f"detailed_action_json/68ce98.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)