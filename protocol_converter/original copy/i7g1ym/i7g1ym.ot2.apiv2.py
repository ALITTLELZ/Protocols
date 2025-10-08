import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/i7g1ym/i7g1ym.ot2.apiv2.py"

from opentrons import protocol_api

metadata = {
    'protocolName': 'Utility: Rearrange pipette tips for 24-well spacing',
    'author': 'Tim Fallon <tfallon@ucsd.edu>',
    'description': 'Rearranges pipette tips from their standard spacing in a  full box, to two empty tip box putting the pipette tips in every \
other row. This allows the P300/P20-multipipette to be used for  pipetting from 24 well plates.',
    'apiLevel': '2.13'
}


def run(protocol: protocol_api.ProtocolContext):

    tiprack_map = {
        'p10_single': {
            'standard': 'opentrons_96_tiprack_10ul',
            'filter': 'opentrons_96_filtertiprack_20ul'
        },
        'p50_single': {
            'standard': 'opentrons_96_tiprack_300ul',
            'filter': 'opentrons_96_filtertiprack_200ul'
        },
        'p300_single': {
            'standard': 'opentrons_96_tiprack_300ul',
            'filter': 'opentrons_96_filtertiprack_200ul'
        },
        'p1000_single': {
            'standard': 'opentrons_96_tiprack_1000ul',
            'filter': 'opentrons_96_filtertiprack_1000ul'
        },
        'p20_single_gen2': {
            'standard': 'opentrons_96_tiprack_20ul',
            'filter': 'opentrons_96_filtertiprack_20ul'
        },
        'p300_single_gen2': {
            'standard': 'opentrons_96_tiprack_300ul',
            'filter': 'opentrons_96_filtertiprack_200ul'
        },
        'p1000_single_gen2': {
            'standard': 'opentrons_96_tiprack_1000ul',
            'filter': 'opentrons_96_filtertiprack_1000ul'
        },
        'p300_multi_gen2': {
            'standard': 'opentrons_96_tiprack_300ul',
            'filter': 'opentrons_96_tiprack_300ul'
        }
    }

    pipette_type = 'p300_multi_gen2'
    pipette_mount = 'right'
    tip_type = 'filter'

    full_tiprack_slots = [10]
    empty_tiprack_slots = [4, 5]
    target_rows = ["A", "C", "E", "G"]
    target_cols = list(range(1, 13))
    full_tipracks = [
        protocol.load_labware(tiprack_map[pipette_type][tip_type], s)
        for s in full_tiprack_slots]
    empty_tipracks = [
        protocol.load_labware(tiprack_map[pipette_type][tip_type], s)
        for s in empty_tiprack_slots]

    pipette = protocol.load_instrument(
         pipette_type, pipette_mount, full_tipracks)

    col_index = -1
    row_index = 0
    empty_tiprack_index = 0
    for tr in full_tipracks:

        reversed_wells = list(tr.wells())
        reversed_wells.reverse()  # updates in place
        for w in reversed_wells:
            col_index += 1
            if row_index == len(target_rows)-1 and col_index == len(
                    target_cols):
                empty_tiprack_index += 1
                row_index = 0
                col_index = 0
            if col_index == len(target_cols):
                row_index += 1
                col_index = 0

            target_well = str(target_rows[row_index])+str(
                target_cols[col_index])  # I.e. like 'A1' or 'B1'
            source_location = w
            pipette.pick_up_tip(source_location)
            destination_location = empty_tipracks[empty_tiprack_index].wells(
                target_well)[0]
            pipette.drop_tip(destination_location)

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
    filename = f"detailed_action_json/i7g1ym.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)