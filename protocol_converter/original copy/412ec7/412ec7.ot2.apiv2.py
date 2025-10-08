import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/412ec7/412ec7.ot2.apiv2.py"

"""ESKILS PROTOCOL."""
metadata = {
    'protocolName': 'Serial Dilution for Eskil',
    'author': 'John C. Lynch',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'   # CHECK IF YOUR API LEVEL HERE IS UP TO DATE
    }


def run(ctx):
    """LINTER."""
    [plate_type,
     temp_mod_on,
     dilution_factor,
     num_of_dilutions,
     total_mixing_volume,
     blank_on,
     tip_use_strategy
     ] = get_values(  # noqa: F821 (<--- DO NOT REMOVE!)
        'plate_type',
        'temp_mod_on',
        'dilution_factor',
        'num_of_dilutions',
        'total_mixing_volume',
        'blank_on',
        'tip_use_strategy')

    # Check for bad setup here
    if not 1 <= num_of_dilutions <= 11:
        raise Exception('Enter a number of dilutions between 1 and 11')
    if temp_mod_on == 1 and 'aluminum' not in plate_type:
        raise Exception('Please select compatible plate and temperature module setting')
    if temp_mod_on == 0 and 'aluminum' in plate_type:
        raise Exception(
                        'Please select compatible plate and temperature module setting')
    if num_of_dilutions == 11 and blank_on == 1:
        raise Exception(
                        'No room for blank with 11 dilutions'
        )

    # define all custom variables above here with descriptions:
    transfer_volume = total_mixing_volume/dilution_factor
    diluent_volume = total_mixing_volume - transfer_volume

    # load modules
    if temp_mod_on == 1:
        temp_mod = ctx.load_module('tempdeck', '4')

    # load labware
    trough = ctx.load_labware('nest_12_reservoir_15ml', '1')
    if temp_mod_on == 1:
        dilute_plate = temp_mod.load_labware(plate_type)
    elif temp_mod_on == 0:
        dilute_plate = ctx.load_labware(plate_type, '4')

    # load tipracks
    tiprack = [
        ctx.load_labware('opentrons_96_tiprack_300ul', slot)
        for slot in ['2', '3']
        ]
    # load instrument
    pipette = ctx.load_instrument(
        'p300_multi_gen2', mount='left', tip_racks=tiprack)
    # pipette functions   # INCLUDE ANY BINDING TO CLASS

    # helper functions

    # reagents

    # protocol
    # step 2
    # Distribute diluent across the plate to the the number of samples
    pipette.transfer(
        diluent_volume,
        trough.wells()[0],
        dilute_plate.rows()[0][1:num_of_dilutions],
        air_gap=10,
        new_tip=tip_use_strategy
    )

    # step 3, 4
    # Dilution of samples across the 96-well flat bottom plate
    if tip_use_strategy == 'never':
        pipette.pick_up_tip()
    for s, d in zip(
            dilute_plate.rows()[0][:num_of_dilutions-1],
            dilute_plate.rows()[0][1:num_of_dilutions]
    ):
        pipette.transfer(
            transfer_volume,
            s,
            d,
            air_gap=10,
            mix_after=(5, total_mixing_volume-5),
            new_tip=tip_use_strategy
        )
    if tip_use_strategy == 'never':
        pipette.drop_tip()

    if blank_on == 1:
        pipette.transfer(
            diluent_volume,
            trough.wells()[0],
            dilute_plate.rows()[0][-1],
            air_gap=10,
            new_tip=tip_use_strategy
        )

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
    filename = f"detailed_action_json/412ec7.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)