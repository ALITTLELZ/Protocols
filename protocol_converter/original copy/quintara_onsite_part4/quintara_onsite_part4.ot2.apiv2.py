import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/quintara_onsite_part4/quintara_onsite_part4.ot2.apiv2.py"

metadata = {
    'protocolName': 'Water Filling 9 Plates',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [starting_tip_col,
        source_labware, p300_mount] = get_values(  # noqa: F821
        "starting_tip_col", "source_labware", "p300_mount")

    # labware
    source_plate = ctx.load_labware(source_labware, 11)
    dest_plates = [ctx.load_labware('doublepcr_96_wellplate_300ul', slot)
                   for slot in [7, 8, 9, 4, 5, 6, 1, 2, 3]]
    tips = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
            for slot in [10]]

    starting_tip = tips[0].rows()[0][starting_tip_col-1]

    ctx.pause(f"""
    Ensure that there is a {tips[0]}.
    Select "Resume" on the Opentrons app.
        """)

    # pipettes
    pip = ctx.load_instrument('p300_multi_gen2',
                              p300_mount,
                              tip_racks=tips)

    all_dest_columns = [
                        col
                        for plate in dest_plates
                        for col in plate.rows()[0]
                        ]

    # source mapping
    source = source_plate.wells()[0]

    all_chunks = [all_dest_columns[i:i+5]
                  for i in range(0, len(all_dest_columns), 5)]

    disp_vol = 20

    pip.pick_up_tip(starting_tip)

    for chunk in all_chunks:
        pip.aspirate(36*len(chunk)+disp_vol, source)
        for well in chunk:
            pip.dispense(36, well.bottom(z=1))
        pip.dispense(pip.current_volume, source)
        ctx.comment('\n')

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
    filename = f"detailed_action_json/quintara_onsite_part4.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)