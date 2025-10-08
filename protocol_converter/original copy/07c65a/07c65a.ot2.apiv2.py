import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/07c65a/07c65a.ot2.apiv2.py"

from opentrons import types

metadata = {
    'protocolName': 'Sample Dilution with CSV Input',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [csv_samp, p20_mount] = get_values(  # noqa: F821
        "csv_samp", "p20_mount")

    csv_lines = [[val.strip() for val in line.split(',')]
                 for line in csv_samp.splitlines()
                 if line.split(',')[0].strip()][1:]

    # labware
    temp_mod = ctx.load_module('temperature module gen2', 4)
    temp_mod.set_temperature(4)
    temp_rack = temp_mod.load_labware('opentrons_24_aluminumblock_nest_2ml_snapcap')  # noqa: E501
    dna_plate = ctx.load_labware('armadillo_96_wellplate_200ul_pcr_full_skirt', 6)  # noqa: E501

    tips20 = [ctx.load_labware('opentrons_96_tiprack_20ul', slot)
              for slot in [11]]

    # pipettes
    m20 = ctx.load_instrument('p20_multi_gen2', p20_mount, tip_racks=tips20)

    # PICK UP ONE TIP WITH P300 MULTI PIPETTE ######################
    num_chan = 1
    tips_ordered = [
        tip
        for row in tips20[0].rows()[
            len(tips20[0].rows())-num_chan::-1*num_chan]
        for tip in row]

    tip_count = 0

    def pick_up_one():

        current = 0.1
        if p20_mount == "right":
            ctx._hw_manager.hardware._attached_instruments[types.Mount.RIGHT].update_config_item('pick_up_current', current)  # noqa: E501
        elif p20_mount == "left":
            ctx._hw_manager.hardware._attached_instruments[types.Mount.LEFT].update_config_item('pick_up_current', current)  # noqa: E501

        nonlocal tip_count
        m20.pick_up_tip(tips_ordered[tip_count])
        tip_count += 1

    # mapping
    water = temp_rack.wells()[0]

    # protocol
    ctx.comment('\n---------------ADDING WATER TO PLATE----------------\n\n')
    for row in csv_lines:
        volume = float(row[1])
        well = dna_plate.wells_by_name()[row[0]]
        pick_up_one()
        m20.aspirate(volume, water)
        m20.dispense(volume, well)
        m20.mix(3, volume, well)
        m20.drop_tip()

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
    filename = f"detailed_action_json/07c65a.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)