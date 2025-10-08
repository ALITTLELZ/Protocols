import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/Opentrons_Logo/Opentrons_Logo.ot2.apiv2.py"

from opentrons import protocol_api
import math

metadata = {
    'protocolName': 'Opentrons Logo',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.10'
    }


def run(ctx: protocol_api.ProtocolContext):
    [_pip_model, _pip_mount, _dp_type, _dye_type] = get_values(  # noqa: F821
        '_pip_model', '_pip_mount', '_dp_type', '_dye_type')

    # customizable parameters
    pip_model = _pip_model
    pip_mount = _pip_mount
    dp_type = _dp_type
    dye_type = _dye_type

    # create pipette and tiprack
    tip_size = pip_model.split('_')[0][1:]
    tip_size = '300' if tip_size == '50' else tip_size
    tip_name = 'opentrons_96_tiprack_'+tip_size+'ul'
    tips = [ctx.load_labware(tip_name, '1', 'Opentrons Tips')]

    pipette = ctx.load_instrument(
        pip_model, pip_mount, tip_racks=tips)

    # create plates and pattern list
    output = ctx.load_labware(dp_type, '3', 'Destination Plate')

    dye_container = ctx.load_labware(dye_type, '2', 'Dye Source')

    # Well Location set-up
    dye1_wells = ['A5', 'A6', 'A8', 'A9', 'B4', 'B10', 'C3', 'C11', 'D3',
                  'D11', 'E3', 'E11', 'F3', 'F11', 'G4', 'G10',
                  'H5', 'H6', 'H7', 'H8', 'H9']

    dye1_dest = [output[x] for x in dye1_wells]

    dye2_wells = ['C7', 'D6', 'D7', 'D8', 'E5', 'E6', 'E7', 'E8',
                  'E9', 'F5', 'F6', 'F7', 'F8', 'F9', 'G6', 'G7', 'G8']

    dye2_dest = [output[x] for x in dye2_wells]

    if 'reservoir' in dye_type:
        dye1 = [dye_container.wells()[0]] * 2
        dye2 = [dye_container.wells()[1]] * 2
    else:
        dye1 = dye_container.wells()[:2]
        dye2 = dye_container.wells()[2:4]

    dye_vol = 100 if tip_size == '1000' else 50

    # distribution function
    def logo_distribute(srcs, dests):
        """
        This is a function that will perform the pick_up_tip(), transfers(),
        and drop_tip() needed to create the Opentrons logo
        :param srcs: source wells (should be a list)
        :param dests: destination wells (should be a list)
        """
        halfDests = math.ceil(len(dests)/2)
        pipette.pick_up_tip()
        for src, dest in zip(srcs, [dests[:halfDests], dests[halfDests:]]):
            for d in dest:
                pipette.transfer(dye_vol, src, d, new_tip='never')
        pipette.drop_tip()

    logo_distribute(dye1, dye1_dest)
    logo_distribute(dye2, dye2_dest)

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
    filename = f"detailed_action_json/Opentrons_Logo.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)