import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0966ae/culture.ot2.apiv2.py"

metadata = {
    'protocolName': '384-Well Plate Prep',
    'author': 'Nick Diehl <ndiehl@opentrons.com>',
    'apiLevel': '2.14'
}


def run(ctx):

    [num_plates, protocol_selection, mount_p300] = get_values(  # noqa: F821
        'num_plates', 'protocol_selection', 'mount_p300')

    tiprack300 = [ctx.load_labware('opentrons_96_tiprack_300ul', '1')]
    tuberack = ctx.load_labware(
        'opentrons_15_tuberack_falcon_15ml_conical', '2')
    plates384 = [
        ctx.load_labware('ananda_384_wellplate_100ul', slot,
                         f'plate {i+1}')
        for i, slot in enumerate(range(3, 3+num_plates))]

    p300 = ctx.load_instrument('p300_single_gen2',
                               mount_p300,
                               tip_racks=tiprack300)

    # reagents
    coating_solution = tuberack.wells()[0]
    water = tuberack.wells()[1]
    waste = ctx.loaded_labwares[12].wells()[0]
    vol_coating_solution = 100.0
    vol_water1 = 100.0
    vol_water2 = 100.0

    coating_solution_liq = ctx.define_liquid(
        name='coating solution',
        description='',
        display_color='B925FF'
    )
    water_liq = ctx.define_liquid(
        name='water',
        description='',
        display_color='50D5FF'
    )

    coating_solution.load_liquid(coating_solution_liq, volume=10000)
    water.load_liquid(water_liq, volume=10000)

    def slow_withdraw(well, delay_seconds=2.0, pip=p300):
        pip.default_speed /= 16
        if delay_seconds > 0:
            ctx.delay(seconds=delay_seconds)
        pip.move_to(well.top())
        pip.default_speed *= 16

    def custom_transfer(vol,
                        source,
                        destination,
                        vol_pre_airgap=10,
                        h_asp=1.0,
                        h_disp=1.0,
                        blow_out=False,
                        pip=p300):
        if vol_pre_airgap > 0:
            pip.aspirate(vol_pre_airgap, source.top())
        p300.aspirate(vol, source.bottom(h_asp))
        slow_withdraw(source)
        p300.dispense(p300.current_volume, destination.bottom(h_disp))
        if blow_out:
            pip.blow_out(destination.bottom(h_disp))
        slow_withdraw(destination)

    # DAY 1
    if protocol_selection == 1:
        dests1 = [
            well for plate in plates384
            for row in [
                plate.rows_by_name()[row_name] for row_name in 'CEFHIKLN']
            for well in row[3::3]]
        p300.pick_up_tip()
        for d in dests1:
            custom_transfer(vol_coating_solution, coating_solution, d, h_asp=5)
        p300.drop_tip()
    # DAY 2
    elif protocol_selection == 2:
        sources2 = [
            well for plate in plates384
            for row in [
                plate.rows_by_name()[row_name] for row_name in 'CEFHIKLN']
            for well in row[1:-1:2]]
        p300.pick_up_tip()
        for s in sources2:
            custom_transfer(vol_coating_solution, s, waste, h_asp=0.2,
                            h_disp=30, vol_pre_airgap=20, blow_out=True)
        p300.drop_tip()

    elif protocol_selection == 3:
        dests3 = [
            well for plate in plates384
            for row in [plate.rows_by_name()[row_name] for row_name in 'CFIL']
            for well in row[3::3]]
        p300.pick_up_tip()
        for d in dests3:
            custom_transfer(vol_water1, water, d, h_asp=5)
        p300.drop_tip()

        ctx.delay(minutes=10)

        dests4 = [
            well for plate in plates384
            for row in [plate.rows_by_name()[row_name] for row_name in 'EHKN']
            for well in row[3::3]]
        p300.pick_up_tip()
        for d in dests4:
            custom_transfer(vol_water1, water, d, h_asp=5)
        p300.drop_tip()

        ctx.delay(minutes=10)

    else:
        # sources5 = [
        #     well for plate in plates384
        #     for row in [
        #         plate.rows_by_name()[row_name] for row_name in 'CEFHIKLN']
        #     for well in row[1:-1:2]]
        # p300.pick_up_tip()
        # for s in sources5:
        #     custom_transfer(vol_water1, s, waste, h_asp=0.2,
        #                     h_disp=30, vol_pre_airgap=20, blow_out=True)
        # p300.drop_tip()

        dests6 = [
            well for plate in plates384
            for row in [plate.rows_by_name()[row_name] for row_name in 'CFIL']
            for well in row[1:-3:3]]
        p300.pick_up_tip()
        for d in dests6:
            custom_transfer(vol_water2, water, d, h_asp=5)
        p300.drop_tip()

        ctx.delay(minutes=10)

        dests7 = [
            well for plate in plates384
            for row in [plate.rows_by_name()[row_name] for row_name in 'EHKN']
            for well in row[1:-3:3]]
        p300.pick_up_tip()
        for d in dests7:
            custom_transfer(vol_water2, water, d, h_asp=5)
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
    filename = f"detailed_action_json/0966ae.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)

        # sources8 = sources5
        # p300.pick_up_tip()
        # for s in sources8:
        #     custom_transfer(vol_water2, s, waste, h_asp=0.2,
        #                     h_disp=30, vol_pre_airgap=20, blow_out=True)
        # p300.drop_tip()

        # dests9 = dests3
        # p300.pick_up_tip()
        # for d in dests9:
        #     custom_transfer(vol_water1, water, d, h_asp=5)
        # p300.drop_tip()

        # ctx.delay(minutes=10)

        # dests10 = dests4
        # p300.pick_up_tip()
        # for d in dests10:
        #     custom_transfer(vol_water1, water, d, h_asp=5)
        # p300.drop_tip()

        # ctx.delay(minutes=10)

        # sources11 = sources8
        # p300.pick_up_tip()
        # for s in sources11:
        #     custom_transfer(vol_water2+20, s, waste, h_asp=0.2,
        #                     h_disp=30, vol_pre_airgap=20, blow_out=True)
        # p300.drop_tip()