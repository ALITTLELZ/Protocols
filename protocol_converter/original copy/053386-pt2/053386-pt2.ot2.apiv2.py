import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/053386-pt2/053386-pt2.ot2.apiv2.py"

metadata = {
    'protocolName': 'Human Islets - Sample Barcoding Oligos',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [m300_mount] = get_values(  # noqa: F821
        "m300_mount")

    # labware
    samp_plate = ctx.load_labware(
                                       'opentrons_96_aluminumblock_generic_pcr_strip_200ul',  # noqa: E501
                                       1,
                                       label='sample plate')

    barcode_plate = ctx.load_labware(
                                       'opentrons_96_aluminumblock_generic_pcr_strip_200ul',  # noqa: E501
                                       3,
                                       label='barcode plate')

    reservoir = ctx.load_labware('nest_12_reservoir_15ml', 2)

    tips = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
            for slot in [4, 5, 6, 7, 8]]

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount, tip_racks=tips)

    # mapping
    trash = ctx.loaded_labwares[12].wells()[0].top()

    wash_buff = reservoir.wells()[0]
    smart_seq_3 = reservoir.wells()[1]
    pool_res_well = reservoir.wells()[-1]

    samp_cols = samp_plate.rows()[0]
    barcode_cols = barcode_plate.rows()[0]

    def remove_super(vol):
        for col in samp_cols:
            m300.pick_up_tip()
            m300.aspirate(vol, col)
            m300.dispense(vol, trash)
            m300.drop_tip()

    # protocol
    ctx.comment('\n---------------ADD BARCODE----------------\n\n')
    for s, d in zip(barcode_cols, samp_cols):
        m300.pick_up_tip()
        m300.aspirate(20, s)
        m300.dispense(20, d)
        m300.mix(10, 50, d)
        m300.drop_tip()

    for _ in range(3):

        ctx.comment('\n---------------ADD WASH BUFFER----------------\n\n')
        m300.pick_up_tip()
        for col in samp_cols:
            m300.aspirate(150, wash_buff)
            m300.dispense(150, col.top())
        m300.drop_tip()

        ctx.pause("Spin at 800g for 6 min")

        ctx.comment('\n---------------REMOVE SUPER----------------\n\n')
        remove_super(150)

    ctx.comment('\n---------------ADD SMART SEQ3----------------\n\n')

    for _ in range(3):
        m300.pick_up_tip()
        m300.aspirate(150, smart_seq_3)
        m300.dispense(150, samp_plate.rows()[0][0])
        m300.mix(5, 150, samp_plate.rows()[0][0])
        m300.aspirate(200, samp_plate.rows()[0][0])
        m300.dispense(50, pool_res_well)
        m300.dispense(150, samp_plate.rows()[0][1])
        for col in range(1, 11):
            m300.mix(5, 150, samp_plate.rows()[0][col])
            m300.aspirate(200, samp_plate.rows()[0][col])
            m300.dispense(50, pool_res_well)
            m300.dispense(150, samp_plate.rows()[0][col+1])
        m300.mix(5, 150, samp_plate.rows()[0][-1])
        m300.aspirate(150, samp_plate.rows()[0][-1])  # move entire col 12
        m300.dispense(150, pool_res_well)
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
    filename = f"detailed_action_json/053386-pt2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)