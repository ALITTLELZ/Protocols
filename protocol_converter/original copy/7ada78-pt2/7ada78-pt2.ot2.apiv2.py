import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7ada78-pt2/7ada78-pt2.ot2.apiv2.py"

from opentrons import protocol_api

metadata = {
    'protocolName': 'RNA Normalization I & II',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx: protocol_api.ProtocolContext):

    [
     _num_col,
     _csv,
     _source_type,
     _p20_mount,
     _m20_mount
    ] = get_values(  # noqa: F821 (<--- DO NOT REMOVE!)
        "_num_col",
        "_csv",
        "_source_type",
        "_p20_mount",
        "_m20_mount")

    # VARIABLES

    # number of columsn in tc plate
    num_col = int(_num_col)

    # should be formatted as so:
    # SlotSource | Source | SourceVolH20 | SourceVolRNA | SlotDest | Dest
    csv = _csv
    source_type = _source_type
    slots = ['1'] if source_type == "kingfisher_96_wellplate_600ul" else ['1', '2', '4', '5']  # noqa: E501

    # change pipette mounts here to "left" or "right", respectively
    p20_mount = _p20_mount
    m20_mount = _m20_mount

    # MODULES
    thermocyc = ctx.load_module('thermocycler')

    # LABWARE
    tuberacks = [ctx.load_labware(
                 source_type,
                 slot, label='Sample Source')
                 for slot in slots]
    tc_plate = thermocyc.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')
    water_plate = ctx.load_labware('abgene_96_wellplate_330ul', '3',
                                   label='Abgene Plate')

    # TIPRACK
    tipracks = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
                for slot in ['6', '9']]

    # INSTRUMENTS
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount, tip_racks=tipracks)
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount, tip_racks=tipracks)

    def pick_up(pip):
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            ctx.pause("Replace tip racks on Slots 6 and 9")
            pip.reset_tipracks()
            pick_up()

    def pre_wet(vol, well):
        ctx.comment('PRE-WET')
        p20.aspirate(vol, well, rate=0.5)
        p20.dispense(vol, well, rate=0.5)
        ctx.comment('DONE PRE-WET')

    # MAPPING
    slot_source = 0
    source_well = 1
    transfer_vol_water = 2
    transfer_vol_rna = 3
    slot_dest = 4
    dest_well = 5

    all_rows = [[val.strip() for val in line.split(',')]
                for line in csv.splitlines()
                if line.split(',')[0].strip()][1:]

    print(tuberacks)

    # protocol
    ctx.comment('\n\nPRE-COOL THERMOCYC\n')
    if thermocyc.lid_position != 'open':
        thermocyc.open_lid()
    thermocyc.set_block_temperature(4)
    thermocyc.set_lid_temperature(105)

    ctx.comment('\n\nMOVING WATER TO PLATE\n')
    pick_up(p20)
    for water_well, the in zip(water_plate.wells(), all_rows):
        if the[transfer_vol_water].lower() == 'x':
            continue
        vol = int(the[transfer_vol_water])
        dest = ctx.loaded_labwares[int(the[slot_dest])].wells_by_name()[
                                    the[dest_well]]
        pre_wet(vol, water_well)
        p20.aspirate(vol, water_well)
        p20.dispense(vol, dest)
    p20.drop_tip()

    ctx.comment('\n\nMOVING RNA TO PLATE\n')
    for the in all_rows:
        if the[transfer_vol_rna].lower() == 'x':
            continue
        vol = int(the[transfer_vol_rna])
        source = ctx.loaded_labwares[int(the[slot_source])].wells_by_name()[
                                        the[source_well]]
        dest = ctx.loaded_labwares[int(the[slot_dest])].wells_by_name()[
                                    the[dest_well]]

        pick_up(p20)
        pre_wet(vol, source)
        p20.aspirate(vol, source)
        p20.dispense(vol, dest)
        p20.drop_tip()
        ctx.comment('\n')

    ctx.pause('''
                 RNA and water on Thermocycler Plate.

                 Replace the 96 well plate containing water on Slot 3 with
                 the exact same 96 well plate with cold mastermix in Column 1.

                 Select "Resume" on the Opentron App to continue.

              ''')

    ctx.comment('\n\nMOVING MASTERMIX TO PLATE\n')
    mmx_plate = water_plate
    mmx = mmx_plate.rows()[0][0]
    for col in tc_plate.rows()[0][:num_col]:
        pick_up(m20)
        m20.aspirate(4, mmx, rate=0.5)
        m20.dispense(4, col, rate=0.5)
        m20.mix(4, 12, col, rate=0.5)
        m20.drop_tip()

    ctx.comment('\n\nRUN THERMOCYCLER PROFILE\n')

    profile = [
                {'temperature': 25, 'hold_time_seconds': 10},
                {'temperature': 50, 'hold_time_seconds': 10},
                {'temperature': 85, 'hold_time_seconds': 5}
                ]

    thermocyc.close_lid()
    thermocyc.execute_profile(steps=profile,
                              repetitions=1,
                              block_max_volume=20)
    thermocyc.open_lid()

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
    filename = f"detailed_action_json/7ada78-pt2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)