import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/13c0b8/13c0b8.ot2.apiv2.py"

metadata = {
    'protocolName': 'Non-Sterile Cell Analysis',
    'author': 'Chaz <chaz@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.1'
}


def run(protocol):
    # load labware and pipettes
    tempdeck = protocol.load_module('tempdeck', '1')
    tempplate = tempdeck.load_labware('brandplates_96_wellplate_360ul')

    liqplate = protocol.load_labware(
        'brandplates_96_wellplate_360ul', '2', 'Plate with liquids')

    trough = protocol.load_labware('nest_12_reservoir_15ml', '3')

    tips20 = [protocol.load_labware(
        'opentrons_96_tiprack_20ul', s) for s in ['4', '5', '7']]
    tips300 = [protocol.load_labware(
        'opentrons_96_tiprack_300ul', s) for s in ['6', '9']]

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=tips20)

    p300 = protocol.load_instrument('p300_multi', 'right', tip_racks=tips300)

    facs = trough['A1']
    b6 = trough['A3']
    liq_waste = trough['A12']

    p20_count = 0

    def p20_pick_up():
        nonlocal p20_count

        if p20_count == 288:  # 96 * 3
            p20.home()
            protocol.pause('Please replace P20 Tips in 4, 5, and 7.')
            tips20.reset()
            p20_count = 0

        p20.pick_up_tip()
        p20_count += 1

    # Step 3
    a_10 = ['A'+str(i) for i in range(1, 11)]
    tubes10 = ['A'+str(i) for i in range(1, 7)] + [
        'B'+str(i) for i in range(1, 5)]

    p20_pick_up()
    # Step 3A
    for well in a_10:
        p20.transfer(20, facs, tempplate[well].top(), new_tip='never')
        p20.blow_out(tempplate[well].top())

    p20.drop_tip()
    # Steps 3B - 3U
    for src, dest in zip(tubes10, tempplate.wells()):
        p20_pick_up()
        p20.transfer(1, liqplate[src], dest, new_tip='never')
        p20.mix(4, 15, dest)
        p20.blow_out(dest.top())
        p20.drop_tip()

    # Step 4
    b_10 = ['B'+str(i) for i in range(1, 11)]

    p20_pick_up()
    # Step 4A
    for well in b_10:
        p20.transfer(20, facs, tempplate[well].top(), new_tip='never')
        p20.blow_out(tempplate[well].top())

    p20.drop_tip()
    # Step 4B -
    tubelist = [val for val in tubes10]
    tubelist.insert(0, tubelist.pop(-1))

    l_o_l = []
    for i in tubelist:
        x = [val for val in tubes10]
        x.remove(i)
        l_o_l.append(x)

    tubes_cd = ['C'+str(i) for i in range(1, 7)]+[
        'D'+str(i) for i in range(1, 5)]

    for tubes, cd, well in zip(l_o_l, tubes_cd, tempplate.wells()[10:]):
        for t in tubes:
            p20_pick_up()
            p20.transfer(1, liqplate[t], well, new_tip='never')
            p20.drop_tip()

        p20_pick_up()
        p20.transfer(1, liqplate[cd], well, new_tip='never')
        p20.mix(4, 15, well)
        p20.blow_out(well.top())
        p20.drop_tip()

    # Step 5
    col4wells = [well for well in tempplate.columns()[3]]
    for well in col4wells:
        p20_pick_up()
        p20.transfer(10, b6, well, new_tip='never')
        p20.mix(4, 20, well)
        p20.blow_out(well.top())
        p20.drop_tip()

    # Step 6
    tempdeck.set_temperature(4)
    protocol.comment('Incubating at 4C for 30 minutes.')
    protocol.delay(minutes=30)

    # Step 7
    col4multi = [tempplate['A'+str(i)] for i in range(1, 5)]
    for col in col4multi:
        p300.pick_up_tip()
        p300.transfer(200, facs, col, new_tip='never')
        p300.blow_out(col.top())
        p300.drop_tip()

    # Step 8
    protocol.pause('Please remove plate from temp deck and spin down plate.  When spun down, replace plate on temperature module and click RESUME.')

    # Step 9
    for col in col4multi:
        p300.pick_up_tip()
        p300.transfer(210, col, liq_waste, new_tip='never')
        p300.drop_tip()

    # Step 10
    for col in col4multi:
        p300.pick_up_tip()
        p300.transfer(100, facs, col, new_tip='never')
        p300.mix(4, 80, col)
        p300.blow_out(col.top())
        p300.drop_tip()

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
    filename = f"detailed_action_json/13c0b8.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)