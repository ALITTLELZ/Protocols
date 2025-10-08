import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/quintara_onsite_nanopore_pooling/quintara_onsite_nanopore.ot2.apiv2.py"

metadata = {
    'protocolName': 'Nanopore Pooling',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [num_plates, p300_mount] = get_values(  # noqa: F821
        "num_plates", "p300_mount")

    # labware
    dest_plates = [ctx.load_labware('combo_96_wellplate_300ul',
                                    slot, label='Dest Plate')
                   for slot in [
                                4, 5, 6, 7, 8, 9
                                ][:num_plates]]

    tips = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
            for slot in [10]]

    half_tip_rack = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
                     for slot in [11]]

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', p300_mount, tip_racks=tips)

    tip_count = 0

    def pick_up_half():
        nonlocal tip_count
        m300.pick_up_tip(tips_ordered[tip_count])
        tip_count += 1

    # mapping
    num_chan = 4
    tips_ordered = [
        tip
        for row in half_tip_rack[0].rows()[
            len(half_tip_rack[0].rows())-num_chan::-1*num_chan]
        for tip in row]

    for plate in dest_plates:
        m300.pick_up_tip()
        d_col = plate.wells()[0]
        for i, s_col in enumerate(plate.rows()[0][::-1][:11]):
            m300.aspirate(20, s_col)
            if i == 5:
                m300.dispense(m300.current_volume, d_col)
                m300.blow_out()
        m300.dispense(m300.current_volume, d_col)
        m300.blow_out()
        m300.drop_tip()
    ctx.comment('\n\n')
    for plate in dest_plates:
        pick_up_half()
        m300.aspirate(130, plate.wells()[4])
        m300.dispense(130, plate.wells()[0])
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
    filename = f"detailed_action_json/quintara_onsite_nanopore_pooling.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)