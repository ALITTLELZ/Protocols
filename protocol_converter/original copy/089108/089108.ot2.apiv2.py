import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/089108/089108.ot2.apiv2.py"

# flake8: noqa

from opentrons import protocol_api

metadata = {
    'protocolName': '96-well Plasmid ezFilter Miniprep Kit',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [num_plates, num_samp_p1,
        num_samp_p2,
        include_buffer_a1,
        include_buffer_a2,
        include_buffer_n3,
        include_moving_fresh_plate,
        include_isoprop,
        include_wash_buffer,
        include_elution,
            m300_mount] = get_values(  # noqa: F821
        "num_plates", "num_samp_p1",
            "num_samp_p2",
            "include_buffer_a1",
            "include_buffer_a2",
            "include_buffer_n3",
            "include_moving_fresh_plate",
            "include_isoprop",
            "include_wash_buffer",
            "include_elution",
            "m300_mount")

    num_plates = int(num_plates)
    num_samp_p1 = int(num_samp_p1)
    num_samp_p2 = int(num_samp_p2)

    # labware
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', 11)
    plates = [ctx.load_labware('usascientific_96_wellplate_2.4ml_deep', slot)
              for slot in [2, 5]][:num_plates]
    second_plates = [ctx.load_labware('jackyshiyihigh_96_wellplate_1200ul',
                                      slot)
                     for slot in [3, 6]][:num_plates]
    elution_plates = [ctx.load_labware('jackyshiyielution_96_wellplate_1200ul',
                                       slot)
                      for slot in [1, 4]][:num_plates]

    tips = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
            for slot in [7, 8, 9, 10]]

    def pick_up():
        try:
            m300.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            ctx.pause("Replace all tip racks")
            m300.reset_tipracks()
            m300.pick_up_tip()

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount, tip_racks=tips)

    # mapping
    buffer = reservoir.wells()[0]
    num_col_p1 = num_samp_p1 // 8
    num_col_p2 = num_samp_p2 // 8
    sample_cols = [cols
                   for plate, sample_number in zip(
                                                plates,
                                                [num_col_p1, num_col_p2]
                                                )
                   for cols in plate.rows()[0][:sample_number]]

    sample_cols_plate2 = [cols
                          for plate, sample_number in zip(
                                                second_plates,
                                                [num_col_p1, num_col_p2]
                                                )
                          for cols in plate.rows()[0][:sample_number]]

    elution_cols = [cols
                    for plate, sample_number in zip(
                                                elution_plates,
                                                [num_col_p1, num_col_p2]
                                                )
                    for cols in plate.rows()[0][:sample_number]]
    airgap = 25

    # protocol
    if include_buffer_a1:
        ctx.comment('\n--------------ADDING BUFFER A1 TO PLATES--------------\n\n')
        pick_up()
        for col in sample_cols:
            m300.aspirate(200, buffer.bottom(z=6))
            m300.dispense(200, col)
            m300.blow_out()
        m300.drop_tip()

        if num_plates == 1:
            first_string = "slot 2"
            second_string = "Return plate to slot 2."

        else:
            first_string = "slots 2 and 5."
            second_string = "Return plates to slots 2 and 5."

        ctx.pause(f"""Remove USA Scientific 96 Deep Well Plate from {first_string}.
                             Add plastic seal. Mix with multi-tube vortexer.\n
                             {second_string}\n
                             Remove trough in slot 11 (195ml 1well) with Buffer A1.
                             Exchange with a new trough with Buffer A2 in Slot 1.\n
                             Select "Resume" on the Opentrons app.""")

    if include_buffer_a2:
        ctx.comment('\n-------------ADDING BUFFER A2 TO PLATES---------------\n\n')

        for col in sample_cols:
            pick_up()
            m300.aspirate(200, buffer)
            m300.dispense(200, col)
            m300.mix(3, 200, col)
            m300.blow_out()
            m300.drop_tip()

        ctx.pause("""
                    Remove trough in slot 11 (195ml 1well) with Buffer A2.
                    Exchange with a new trough with Buffer N3 in Slot 11.
                    Select "Resume" on the Opentrons app.""")

    if include_buffer_n3:
        ctx.comment('\n-------------ADDING BUFFER N3 TO PLATES---------------\n\n')

        for col in sample_cols:
            pick_up()
            m300.aspirate(280, buffer)
            m300.dispense(280, col)
            m300.mix(3, 300, col)
            m300.blow_out()
            m300.drop_tip()

    if include_moving_fresh_plate:
        ctx.comment('\n-------------MOVING TO FRESH PLATE---------------\n\n')

        for s_col, d_col in zip(sample_cols, sample_cols_plate2):
            pick_up()
            m300.transfer(680, s_col, d_col,
                          new_tip='never',
                          blow_out=True,
                          blowout_location='destination well')
            m300.blow_out()
            m300.drop_tip()

        if num_plates == 1:
            first_string = "slot 3"
            second_string = "slot 2"

        else:
            first_string = "slots 3 and 6"
            second_string = "slots 2 and 5"

        ctx.pause(f"""
                    Remove the labware in {first_string} for processing.\n
                    Remove deep well plate in {second_string}\n
                    Place a processed deep well plate into {second_string}\n
                    Replace Slot 11, 1 well reservoir with 100% isopropanol
                    (low surface tension)\n
                    Place deepwell plate + top to {first_string}\n
                    Select "Resume" on the Opentrons app""")

    if include_isoprop:
        ctx.comment('\n--------ADDING ISOPROPANOL AND TRANSFERRING----------\n\n')


        for s_col, d_col in zip(sample_cols, sample_cols_plate2):
            pick_up()
            for _ in range(2):
                m300.aspirate(250, buffer)
                m300.air_gap(airgap)
                m300.dispense(250+airgap, s_col.top(z=-2))
                m300.touch_tip()
                m300.blow_out()
            m300.mix(3, 300, s_col)
            for _ in range(5):
                m300.aspirate(250, s_col)
                m300.dispense(250, d_col)
            m300.blow_out()
            m300.drop_tip()
            ctx.comment('\n\n')

        ctx.pause(f"""
                    Remove and process plate in {first_string} and replace
                    in {first_string}\n
                    Exchange trough in slot 11 with 1 well reservoir
                    with wash buffer\n
                    Select "Resume" on the Opentrons app.""")

    if include_wash_buffer:

        ctx.comment('\n------------ADDING WASH BUFFER TO PLATES------------\n\n')
        pick_up()
        for col in sample_cols_plate2:
            for _ in range(3):
                m300.aspirate(250, buffer)
                m300.air_gap(airgap)
                m300.dispense(250+airgap, col.top(z=-2))
                m300.blow_out()
            m300.blow_out()
        m300.drop_tip()

        if num_plates == 1:
            first_string = "slot 3"
            second_string = "slot 1"

        else:
            first_string = "slots 3 and 6"
            second_string = "slots 1 and 4"

        ctx.pause(f"""
                    Remove and process plate in {first_string}\n
                    Ensure elution plate combo is in {second_string}\n
                    Exchange trough in slot 11 with 1 well reservoir
                    with elution buffer\n
                    Select "Resume" on the Opentrons app.""")

    if include_elution:
        ctx.comment('\n----------ADDING ELUTION BUFFER TO PLATES-----------\n\n')

        for col in elution_cols:
            pick_up()
            m300.aspirate(35, buffer)
            m300.dispense(35, col)
            m300.blow_out()
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
    filename = f"detailed_action_json/089108.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)