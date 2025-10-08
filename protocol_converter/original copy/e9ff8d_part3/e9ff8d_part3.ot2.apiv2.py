import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/e9ff8d_part3/e9ff8d_part3.ot2.apiv2.py"

# flake8: noqa

metadata = {
    'protocolName': '4.1 Sample Index PCR',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [num_samp, tip_rack,
        start_index_tip, p300_mount, m300_mount] = get_values(  # noqa: F821
        "num_samp", "tip_rack", "start_index_tip", "p300_mount", "m300_mount")

    start_index_tip = str(start_index_tip)

    start_index_dict = {1: "A", 2: "B", 3: "C", 4: "D",
                        5: "E", 6: "F", 7: "G", 8: "H"}
    keys = [k for k, v in start_index_dict.items() if v == start_index_tip[0]]
    index_check = int(keys[0]) + num_samp - 1

    print(index_check)

    if index_check > 8:
        raise Exception(f"""Index start well entered "{start_index_tip}" does
                            not allow enough tips for {num_samp} samples""")


    if not 1 <= num_samp <= 8:
        raise Exception("Enter a sample number between 1-8")

    # labware
    mag_mod = ctx.load_module('magnetic module', 10)
    print(mag_mod)

    temp_mod_reag = ctx.load_module('temperature module', 6)
    temp_mod = ctx.load_module('temperature module gen2', 9)

    strip_tube_plate = temp_mod_reag.load_labware('eppendorf_96_aluminumblock_200ul',
                                             "SAMPLE PLATE")


    # ADD MAGNETIC MODULE
    reag_rack = temp_mod.load_labware('opentrons_24_aluminumblock_nest_2ml_snapcap',
                                      "REAGENT RACK")

    index_plate = ctx.load_labware('index_96_wellplate_200ul', 5,
                                   "INDEX PLATE")

    tipracks = [ctx.load_labware(tip_rack, slot)
                for slot in [7]]

    # pipettes
    p300 = ctx.load_instrument('p300_single_gen2',
                               p300_mount,
                               tip_racks=tipracks)
    m300 = ctx.load_instrument('p300_multi_gen2',
                               m300_mount,
                               tip_racks=tipracks)

    num_channels_per_pickup = num_samp
    tips_ordered = [
        tip for rack in tipracks
        for row in rack.rows()[
            len(rack.rows())-num_channels_per_pickup::-1*num_channels_per_pickup]  # noqa: E501
        for tip in row]

    tip_count = 0

    def pick_up(pip):
        nonlocal tip_count
        pip.pick_up_tip(tips_ordered[tip_count])
        tip_count += 1

    # mapping
    temp_mod.set_temperature(4)
    temp_mod_reag.set_temperature(4)
    samples = strip_tube_plate.columns()[0][0]
    new_sample_loc = strip_tube_plate.columns()[0][0]
    index_mix = reag_rack.rows()[0][0]
    index_well = index_plate.wells_by_name()[start_index_tip]

    ctx.comment('\n\n~~~~~~~~~~~~~~~~ADDING INDEX MIX~~~~~~~~~~~~~~~~\n')
    for sample in strip_tube_plate.columns()[0][:num_samp]:
        pick_up(p300)
        p300.aspirate(60, index_mix)
        p300.dispense(60, sample)
        p300.blow_out()
        p300.drop_tip()

    ctx.comment('\n\n~~~~~~~~~~~~~~~~PIERCING FOIL~~~~~~~~~~~~~~~~\n')
    pick_up(m300)
    m300.move_to(index_well.top(z=-7))
    m300.touch_tip(v_offset=-7, radius=0.65)
    m300.drop_tip()

    ctx.comment('\n\n~~~~~~~~~~~~~~~~ADDING INDEX~~~~~~~~~~~~~~~~\n')
    pick_up(m300)
    m300.aspirate(20, index_well)
    m300.dispense(20, new_sample_loc)
    m300.mix(5, 90, new_sample_loc)
    m300.blow_out()
    m300.drop_tip()

    ctx.comment("""
    Adding index complete. Centrifuge and thermal cycle according to 4.1.e
    and 4.1.f of the SOP.
    """)

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
    filename = f"detailed_action_json/e9ff8d_part3.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)