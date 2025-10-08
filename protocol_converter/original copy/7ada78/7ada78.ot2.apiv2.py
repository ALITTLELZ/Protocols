import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7ada78/7ada78.ot2.apiv2.py"

from opentrons import protocol_api

metadata = {
    'protocolName': 'RNA Quantitation',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx: protocol_api.ProtocolContext):

    [
     _csv,
     _source_type,
     _p20_mount,
     _m20_mount
    ] = get_values(  # noqa: F821 (<--- DO NOT REMOVE!)
        "_csv",
        "_source_type",
        "_p20_mount",
        "_m20_mount")

    # VARIABLES
    csv = _csv
    source_type = _source_type
    p20_mount = _p20_mount
    m20_mount = _m20_mount

    # MODULES
    thermocyc = ctx.load_module('thermocycler')

    # LABWARE
    slots = ['1'] if source_type == "kingfisher_96_wellplate_600ul" else ['1', '2', '4', '5']  # noqa: E501
    tuberacks = [ctx.load_labware(
                 source_type,
                 slot, label='Sample Tuberack')
                 for slot in slots]
    tc_plate = thermocyc.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')
    dest_plate = ctx.load_labware('optiplate_96_wellplate_400ul',
                                  '3', label='Optiplate')

    # TIPRACKS
    tipracks = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
                for slot in ['6', '9']]

    # INSTRUMENTS
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount, tip_racks=tipracks)
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount, tip_racks=tipracks)

    pip = m20 if source_type == "kingfisher_96_wellplate_600ul" else p20
    print(pip.type)

    def pre_wet(vol, well):
        ctx.comment('PRE-WET')
        pip.aspirate(vol, well, rate=0.5)
        pip.dispense(vol, well, rate=0.5)
        ctx.comment('DONE PRE-WET')

    # MAPPING
    slot_source = 0
    source_well = 1
    transfer_vol = 3
    slot_dest = 4
    dest_well = 5

    all_rows = [[val.strip() for val in line.split(',')]
                for line in csv.splitlines()
                if line.split(',')[0].strip()][1:]

    print(tuberacks, tc_plate, dest_plate)
    if thermocyc.lid_position != 'open':
        thermocyc.open_lid()

    # protocol

    ctx.comment('\n\nMOVING SAMPLES TO PLATE\n')

    for the in all_rows:
        if the[transfer_vol].lower() == 'x':
            continue
        vol = int(the[transfer_vol])
        source = ctx.loaded_labwares[int(the[slot_source])].wells_by_name()[
                                        the[source_well]]
        dest = ctx.loaded_labwares[int(the[slot_dest])].wells_by_name()[
                                        the[dest_well]]
        pip.pick_up_tip()
        pre_wet(vol, source)
        pip.aspirate(vol, source)
        pip.dispense(vol, dest)
        pip.drop_tip()

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
    filename = f"detailed_action_json/7ada78.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)