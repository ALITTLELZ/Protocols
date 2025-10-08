import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/quintara_onsite_nanopore/quintara_onsite_nanopore.ot2.apiv2.py"

metadata = {
    'protocolName': 'Nanopore Aliquoting',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [num_plates, p20_mount] = get_values(  # noqa: F821
        "num_plates", "p20_mount")

    # labware
    source_plate = ctx.load_labware('barcode_96_wellplate_200ul', 9,
                                    label='Source Plate')
    dest_plates = [ctx.load_labware('combo_96_wellplate_300ul',
                                    slot, label='Dest Plate')
                   for slot in [
                                1, 2, 3, 4, 5, 6, 7
                                ][:num_plates]]

    water_res = ctx.load_labware('nest_12_reservoir_15ml', 8)
    tips = [ctx.load_labware('opentrons_96_tiprack_20ul', slot)
            for slot in [10]]

    # pipettes
    m20 = ctx.load_instrument('p20_multi_gen2', p20_mount, tip_racks=tips)

    # mapping
    dest_cols = [plate.rows()[0][i]
                 for i in range(12) for plate in dest_plates]

    water = water_res.wells()[0]

    # protocol
    ctx.comment('\n--------------ADDING BARCODE TO PLATES--------------\n\n')
    d_col_ctr = 0
    for s in source_plate.rows()[0]:
        m20.pick_up_tip()
        m20.aspirate(8.5, water)
        m20.dispense(8.5, s)
        m20.mix(3, 14, s)
        for _ in range(num_plates):
            m20.aspirate(2, s, rate=0.5)
            m20.dispense(2, dest_cols[d_col_ctr], rate=0.5)
            # m20.blow_out() ????????????????????
            d_col_ctr += 1
        m20.drop_tip()
        ctx.comment('\n\n')

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
    filename = f"detailed_action_json/quintara_onsite_nanopore.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)