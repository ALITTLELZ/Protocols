import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/07ad5f/07ad5f.ot2.apiv2.py"

import math
from opentrons import protocol_api

metadata = {
    'protocolName': 'DNeasy Plant DNA Purification',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.15'
}


def run(ctx):

    [num_samp_plate1, num_samp_plate2,
        m300_mount] = get_values(  # noqa: F821
        "num_samp_plate1", "num_samp_plate2", "m300_mount")

    # num_samp_plate1 = 48
    # num_samp_plate2 = 96

    num_col_plate1 = math.ceil(num_samp_plate1/8)
    num_col_plate2 = math.ceil(num_samp_plate2/8)
    # m300_mount = 'left'

    # labware
    reservoir_12 = ctx.load_labware('nest_12_reservoir_15ml', 11)
    reservoir_1_well = [ctx.load_labware('nest_1_reservoir_195ml', slot)
                        for slot in [3, 6, 9]]
    deep_plates = [ctx.load_labware('nest_96_wellplate_2ml_deep', slot)
                   for slot in [1, 4, 2, 5]]
    tips = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
            for slot in [7, 8, 10]]

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount, tip_racks=tips)

    def pick_up():
        try:
            m300.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            ctx.pause(f"Replace empty tip rack for {m300}")
            m300.reset_tipracks()
            m300.pick_up_tip()

    # mapping
    lysis = reservoir_1_well[0]['A1']
    aw1 = reservoir_1_well[1]['A1']
    aw2 = reservoir_1_well[2]['A1']

    p3 = reservoir_12.wells()[:2]*1000
    ae_buffer = reservoir_12.wells()[2:4]*1000

    all_sample_cols = [
                       col for plate, num_cols in zip(
                                                        deep_plates[:2],
                                                        [num_col_plate1,
                                                         num_col_plate2]
                                                         )
                       for col in plate.rows()[0][:num_cols]
                       ]
    all_sample_cols_right_side = [
                       col for plate, num_cols in zip(
                                                        deep_plates[2:],
                                                        [num_col_plate1,
                                                         num_col_plate2]
                                                         )
                       for col in plate.rows()[0][:num_cols]
                       ]

    # protocol
    ctx.comment('\n---------------ADDING BUFFER TO PLATES----------------\n\n')
    pick_up()
    for col in all_sample_cols:
        for _ in range(2):
            m300.aspirate(200, lysis)
            m300.dispense(200, col.top())
    m300.drop_tip()

    ctx.pause('Please take deepwell plate off deck and grind and centrifuge')

    ctx.comment('\n---------------ADDING P3----------------\n\n')
    pick_up()
    for source, col in zip(p3, all_sample_cols):
        m300.aspirate(130, source)
        m300.dispense(130, col.top())
    m300.drop_tip()

    ctx.pause("""Take samples and incubate for 10 minutes at -20C.
                 After, put sample plates back on slots 1 and 4.""")

    ctx.comment('\n---------------TRANSFERRING SAMPLE----------------\n\n')
    for source_plate, dest_plate, num_col in zip(deep_plates[:2],
                                                 deep_plates[2:],
                                                 [num_col_plate1,
                                                 num_col_plate2]):
        for s, d in zip(source_plate.rows()[0][:num_col],
                        dest_plate.rows()[0]):
            pick_up()
            for _ in range(2):
                m300.aspirate(200, s, rate=0.2)
                m300.dispense(200, d)
            m300.drop_tip()

    ctx.pause('Replace sample plates with fresh plates on slots 1 & 4.')

    ctx.comment('\n-------------ADDING A1 BUFFER TO PLATES-------------\n\n')
    pick_up()
    for col in all_sample_cols_right_side:
        for _ in range(3):
            m300.aspirate(200, aw1)
            m300.dispense(200, col.top())
    m300.drop_tip()

    ctx.comment('\n---------------TRANSFERRING SAMPLE----------------\n\n')
    for source_plate, dest_plate, num_col in zip(deep_plates[2:],
                                                 deep_plates[:2],
                                                 [num_col_plate1,
                                                 num_col_plate2]):
        for s, d in zip(source_plate.rows()[0][:num_col],
                        dest_plate.rows()[0]):
            pick_up()
            for _ in range(5):
                m300.aspirate(200, s, rate=0.2)
                m300.dispense(200, d)
            m300.drop_tip()

    ctx.pause('Centrifuge and filter samples')

    ctx.comment('\n---------------ADDING AW2 BUFFER TO PLATES------------\n\n')
    pick_up()
    for col in all_sample_cols:
        for _ in range(4):
            m300.aspirate(200, aw2)
            m300.dispense(200, col.top())
    m300.drop_tip()

    ctx.comment('\n---------------ADDING AE BUFFER----------------\n\n')
    pick_up()
    for source, col in zip(ae_buffer, all_sample_cols):
        m300.aspirate(100, source)
        m300.dispense(100, col.top())
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
    filename = f"detailed_action_json/07ad5f.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)