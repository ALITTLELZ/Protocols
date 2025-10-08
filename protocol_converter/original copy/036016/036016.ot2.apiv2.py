import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/036016/036016.ot2.apiv2.py"

metadata = {
    'protocolName': 'Thermocycler 4Plates 384PCR 12PrimesSets-32cDNAsQuad',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [p20_mount] = get_values(  # noqa: F821
        "p20_mount")

    # labware
    thermocyc = ctx.load_module('Thermocycler Module')

    tc_plate = thermocyc.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')
    plate = ctx.load_labware('corning_96_wellplate_360ul_flat', 9)

    plates_384 = [ctx.load_labware('appliedbiosystemsthermofisherlife4309849withbarcode_384_wellplate_30ul', slot, label='384 Plate')  # noqa: E501
                  for slot in [2, 3, 5, 6]]
    plates_384 = plates_384
    tips = [ctx.load_labware('opentrons_96_tiprack_20ul', slot)
            for slot in [1, 4]]

    # pipettes
    m20 = ctx.load_instrument('p20_multi_gen2', p20_mount, tip_racks=tips)

    def change_speed(percentage):
        m20.default_speed = 400*(percentage/100)

    if thermocyc.lid_position == "open":
        thermocyc.close_lid()
    thermocyc.set_block_temperature(4)
    thermocyc.set_lid_temperature(40)

    # protocol
    change_speed(50)
    m20.flow_rate.aspirate = 2
    m20.flow_rate.dispense = 2

    # ---------------------- SLOT 5 ----------------------

    slot_5_all_cols = [ctx.loaded_labwares[5].rows()[row][col]
                       for col in range(24) for row in range(2)]

    num_cols = 8
    m20.pick_up_tip()
    wells = slot_5_all_cols[:num_cols*2]
    for i in range(0, len(wells), 2):
        m20.aspirate(20, plate.rows()[0][0].bottom(0.5))
        ctx.delay(seconds=1)

        for j in range(2):
            m20.dispense(10, slot_5_all_cols[:num_cols*2][i+j].bottom(0.5))
            m20.move_to(slot_5_all_cols[:num_cols*2][i+j].bottom(1.5))
            ctx.delay(seconds=1)
        ctx.comment('\n')

    m20.drop_tip()
    ctx.comment('\n\n\n\n')

    m20.pick_up_tip()
    wells = slot_5_all_cols[num_cols*2:num_cols*4]
    for i in range(0, len(wells), 2):
        m20.aspirate(20, plate.rows()[0][1].bottom(0.5))
        ctx.delay(seconds=1)

        for j in range(2):
            m20.dispense(10,
                         wells[i+j].bottom(0.5))  # noqa: E501
            m20.move_to(wells[i+j].bottom(1.5))  # noqa: E501
            ctx.delay(seconds=1)
    m20.drop_tip()
    ctx.comment('\n\n\n')

    m20.pick_up_tip()
    wells = slot_5_all_cols[num_cols*4:num_cols*8]
    for i in range(0, len(wells), 2):
        m20.aspirate(20, plate.rows()[0][2].bottom(0.5))
        ctx.delay(seconds=1)

        for j in range(2):
            m20.dispense(10,
                         wells[i+j].bottom(0.5))
            m20.move_to(wells[i+j].bottom(1.5))
            ctx.delay(seconds=1)
    m20.drop_tip()
    ctx.comment('\n\n\n\n')

    # ---------------------- SLOT 6 ----------------------
    slot_6_all_cols = [ctx.loaded_labwares[6].rows()[row][col]
                       for col in range(24) for row in range(2)]

    m20.pick_up_tip()
    wells = slot_6_all_cols[:num_cols*2]
    for i in range(0, len(wells), 2):
        m20.aspirate(20, plate.rows()[0][3].bottom(0.5))
        ctx.delay(seconds=1)

        for j in range(2):
            m20.dispense(10,
                         wells[i+j].bottom(0.5))
            m20.move_to(wells[i+j].bottom(1.5))
            ctx.delay(seconds=1)
    m20.drop_tip()
    ctx.comment('\n\n\n\n')

    m20.pick_up_tip()
    wells = slot_6_all_cols[num_cols*2:num_cols*4]
    for i in range(0, len(wells), 2):
        m20.aspirate(20, plate.rows()[0][4].bottom(0.5))
        ctx.delay(seconds=1)
        for j in range(2):
            m20.dispense(10,
                         wells[i+j].bottom(0.5))  # noqa: E501
            m20.move_to(wells[i+j].bottom(1.5))  # noqa: E501
            ctx.delay(seconds=1)
    m20.drop_tip()
    ctx.comment('\n\n\n\n')

    m20.pick_up_tip()
    wells = slot_6_all_cols[num_cols*4:num_cols*8]
    for i in range(0, len(wells), 2):
        m20.aspirate(20, plate.rows()[0][5].bottom(0.5))
        ctx.delay(seconds=1)
        for j in range(2):
            m20.dispense(10,
                         wells[i+j].bottom(0.5))  # noqa: E501
            m20.move_to(wells[i+j].bottom(1.5))  # noqa: E501
            ctx.delay(seconds=1)
    m20.drop_tip()
    ctx.comment('\n\n\n\n')

    # ---------------------- SLOT 2 ----------------------
    slot_2_all_cols = [ctx.loaded_labwares[2].rows()[row][col]
                       for col in range(24) for row in range(2)]

    m20.pick_up_tip()
    wells = slot_2_all_cols[:num_cols*2]
    for i in range(0, len(wells), 2):
        m20.aspirate(20, plate.rows()[0][6].bottom(0.5))
        ctx.delay(seconds=1)
        for j in range(2):
            m20.dispense(10,
                         wells[i+j].bottom(0.5))  # noqa: E501
            m20.move_to(wells[i+j].bottom(1.5))  # noqa: E501
            ctx.delay(seconds=1)
    m20.drop_tip()
    ctx.comment('\n\n\n\n')

    m20.pick_up_tip()
    wells = slot_2_all_cols[num_cols*2:num_cols*4]
    for i in range(0, len(wells), 2):
        m20.aspirate(20, plate.rows()[0][7].bottom(0.5))
        ctx.delay(seconds=1)
        for j in range(2):
            m20.dispense(10,
                         wells[i+j].bottom(0.5))  # noqa: E501
            m20.move_to(wells[i+j].bottom(1.5))  # noqa: E501
            ctx.delay(seconds=1)
    m20.drop_tip()
    ctx.comment('\n\n\n\n')

    m20.pick_up_tip()
    wells = slot_2_all_cols[num_cols*4:num_cols*8]
    for i in range(0, len(wells), 2):
        m20.aspirate(20, plate.rows()[0][8].bottom(0.5))
        ctx.delay(seconds=1)
        for j in range(2):
            m20.dispense(10,
                         wells[i+j].bottom(0.5))  # noqa: E501
            m20.move_to(wells[i+j].bottom(1.5))  # noqa: E501
            ctx.delay(seconds=1)
    m20.drop_tip()
    ctx.comment('\n\n\n\n')

    # ---------------------- SLOT 3 ----------------------
    slot_3_all_cols = [ctx.loaded_labwares[3].rows()[row][col]
                       for col in range(24) for row in range(2)]

    m20.pick_up_tip()
    wells = slot_3_all_cols[:num_cols*2]
    for i in range(0, len(wells), 2):
        m20.aspirate(20, plate.rows()[0][9].bottom(0.5))
        ctx.delay(seconds=1)
        for j in range(2):
            m20.dispense(10,
                         wells[i+j].bottom(0.5))  # noqa: E501
            m20.move_to(wells[i+j].bottom(1.5))  # noqa: E501
            ctx.delay(seconds=1)
    m20.drop_tip()
    ctx.comment('\n\n\n\n')

    m20.pick_up_tip()
    wells = slot_3_all_cols[num_cols*2:num_cols*4]
    for i in range(0, len(wells), 2):
        m20.aspirate(20, plate.rows()[0][10].bottom(0.5))
        ctx.delay(seconds=1)
        for j in range(2):
            m20.dispense(10,
                         wells[i+j].bottom(0.5))  # noqa: E501
            m20.move_to(wells[i+j].bottom(1.5))  # noqa: E501
            ctx.delay(seconds=1)
    m20.drop_tip()
    ctx.comment('\n\n\n\n')

    m20.pick_up_tip()
    wells = slot_3_all_cols[num_cols*4:num_cols*8]
    for i in range(0, len(wells), 2):
        m20.aspirate(20, plate.rows()[0][11].bottom(0.5))
        ctx.delay(seconds=1)
        for j in range(2):
            m20.dispense(10,
                         wells[i+j].bottom(0.5))  # noqa: E501
            m20.move_to(wells[i+j].bottom(1.5))  # noqa: E501
            ctx.delay(seconds=1)
    m20.drop_tip()
    ctx.comment('\n\n\n\n')

    # ----------------------------------Thermocycler--------------------------
    m20.flow_rate.aspirate = 2
    m20.flow_rate.dispense = 0.2
    thermocyc.open_lid()

    ctx.comment('Dispensing From Thermocycler')
    dispense_columns = [
        [1, 2, 9, 10, 17, 18],
        [3, 4, 11, 12, 19, 20],
        [5, 6, 13, 14, 21, 22],
        [7, 8, 15, 16, 23, 24]
    ]
    plate_slots = [5, 6, 2, 3]

    for i, (disp_col_list, slot) in enumerate(zip(dispense_columns,
                                                  plate_slots)):
        dispense_wells = [ctx.loaded_labwares[slot].rows()[row][col-1]
                          for col in disp_col_list for row in range(2)]
        m20.pick_up_tip()
        m20.aspirate(13, tc_plate.rows()[0][i].bottom(0.5))
        ctx.delay(seconds=1)
        for well in dispense_wells:

            m20.dispense(1, well.bottom(0.5))
            m20.move_to(well.bottom(1.5))
            ctx.delay(seconds=1)
        m20.blow_out(ctx.loaded_labwares[12].wells()[0].top())
        m20.drop_tip()
        ctx.comment('\n\n\n\n')

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
    filename = f"detailed_action_json/036016.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)