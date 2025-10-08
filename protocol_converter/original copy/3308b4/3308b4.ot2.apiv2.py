import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/3308b4/3308b4.ot2.apiv2.py"

"""PROTOCOL."""
metadata = {
    'protocolName': 'PCR/qPCR Prep',
    'author': 'Opentrons',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'   # CHECK IF YOUR API LEVEL HERE IS UP TO DATE
                         # IN SECTION 5.2 OF THE APIV2 "VERSIONING"
}


def run(ctx):

    [mount_m300
     ] = get_values(  # noqa: F821 (<--- DO NOT REMOVE!)
        "mount_m300")

    # define all custom variables above here with descriptions:

    # number of samples

    # "True" for park tips, "False" for discard tips

    # load labware
    spr_well = ctx.load_labware('nest_1_reservoir_195ml', '4')
    vhb_well = ctx.load_labware('nest_1_reservoir_195ml', '5')
    water_well = ctx.load_labware('nest_1_reservoir_195ml', '6')
    spr_plate = ctx.load_labware('nest_96_wellplate_2ml_deep', '7')
    vhb_plate = ctx.load_labware('nest_96_wellplate_2ml_deep', '8')
    water_plate = ctx.load_labware('nest_96_wellplate_2ml_deep', '9')

    # load tipracks
    tiprack = [
        ctx.load_labware('opentrons_96_tiprack_300ul', '1')
        ]

    # load instrument
    m300 = ctx.load_instrument(
        'p300_multi_gen2', mount=mount_m300, tip_racks=tiprack)

    # reagents
    spr = spr_well.wells()[0]
    vhb = vhb_well.wells()[0]
    water = water_well.wells()[0]

    # lists
    volume_list = [350, 350, 50]
    source_list = [spr, vhb, water]
    dest_list = [spr_plate.rows()[0], vhb_plate.rows()[0],
                 water_plate.rows()[0]]

    # protocol
    for volume, source, dests in zip(volume_list, source_list, dest_list):
        m300.pick_up_tip()
        m300.transfer(volume,
                      source,
                      dests,
                      new_tip='never'
                      )
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
    filename = f"detailed_action_json/3308b4.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)