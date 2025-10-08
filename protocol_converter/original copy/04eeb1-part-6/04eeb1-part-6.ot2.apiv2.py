import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/04eeb1-part-6/04eeb1-part-6.ot2.apiv2.py"

from opentrons import protocol_api, types

metadata = {
    'protocolName': 'Illumina COVIDSeq Test: Amplify Tagmented Amplicons',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.10'
}


def run(ctx):

    [m300_mount, plate_1_cols, temperature, mm_col] = get_values(  # noqa: F821
        "m300_mount", "plate_1_cols", "temperature", "mm_col")

    # Labware
    tips200ul = ctx.load_labware('opentrons_96_filtertiprack_200ul', 4)
    temp_mod = ctx.load_module('temperature module gen2', 1)
    reservoir = temp_mod.load_labware('nest_12_reservoir_15ml',
                                      "Master Mix Reservoir")
    mag_mod = ctx.load_module('magnetic module gen2', 3)
    plate_1 = mag_mod.load_labware('biorad_96_wellplate_200ul_pcr')

    # Pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount,
                               tip_racks=[tips200ul])

    # Helper Functions
    def includeCols(includedCols, plateCols):
        included_cols = []
        if includedCols != "":
            included_cols = [int(i)-1 for i in includedCols.split(",")]
            dests = [col for i, col in enumerate(plateCols) if i
                     in included_cols]
            return dests

    def remove_supernatant(vol, src, dest, side):
        m300.flow_rate.aspirate = 20
        m300.aspirate(10, src.top())
        while vol > 200:
            m300.aspirate(
                200, src.bottom().move(types.Point(x=side, y=0, z=0.5)))
            m300.dispense(200, dest)
            m300.aspirate(10, dest)
            vol -= 200
        m300.aspirate(vol, src.bottom().move(types.Point(x=side, y=0, z=0.5)))
        m300.dispense(vol, dest)
        m300.dispense(10, dest)
        m300.flow_rate.aspirate = 50

    def pick_up(pip):
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pip.home()
            ctx.pause("Please replace the tips and click Resume.")
            pip.reset_tipracks()
            pip.pick_up_tip()

    # Wells
    plate_1_wells = includeCols(plate_1_cols, plate_1.rows()[0])
    mm = reservoir[mm_col]
    trash = ctx.loaded_labwares[12]['A1']

    # Protocol Steps

    temp_mod.set_temperature(temperature)
    # Engage Mag Mod
    mag_mod.engage()

    # Remove Supernatant
    for col in plate_1_wells:
        pick_up(m300)
        remove_supernatant(120, col, trash, -1)
        m300.drop_tip()

    # Transfer AMP Master Mix
    for col in plate_1_wells:
        pick_up(m300)
        m300.transfer(40, mm, col, new_tip='never')
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
    filename = f"detailed_action_json/04eeb1-part-6.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)