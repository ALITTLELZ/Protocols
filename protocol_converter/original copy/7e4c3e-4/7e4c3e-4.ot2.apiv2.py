import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7e4c3e-4/7e4c3e-4.ot2.apiv2.py"

metadata = {'apiLevel': '2.0'}


def run(ctx):

    a1_init_vol, a3_init_vol, a4_init_vol, b3_init_vol, tip_start = get_values(  # noqa: F821, E501
            'a1_init_vol', 'a3_init_vol', 'a4_init_vol', 'b3_init_vol', 'tip_start')  # noqa: E501

    p1000s_rack = ctx.load_labware("opentrons_96_filtertiprack_1000ul", "1")
    p1000s = ctx.load_instrument(
        'p1000_single_gen2',
        'left',
        tip_racks=[p1000s_rack])
    p1000s.starting_tip = p1000s_rack.well(tip_start)

    tube_rack = ctx.load_labware(
        "opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical", "4")
    tube_a1 = tube_rack.wells_by_name()["A1"]
    tube_a3 = tube_rack.wells_by_name()["A3"]
    tube_a4 = tube_rack.wells_by_name()["A4"]
    tube_b3 = tube_rack.wells_by_name()["B3"]

    deepwell_a1 = ctx.load_labware("nest_96_wellplate_2ml_deep", "6")
    deepwell_a3 = ctx.load_labware("nest_96_wellplate_2ml_deep", "2")
    deepwell_a4 = ctx.load_labware("nest_96_wellplate_2ml_deep", "5")
    deepwell_b3 = ctx.load_labware("nest_96_wellplate_2ml_deep", "3")

    def height_offset(vol_used, tube_type="50ml", init_vol=50):
        if tube_type == "50ml":
            liquid_top = init_vol * 2
            # 1mm per 2ml
            if vol_used == 0:
                return liquid_top
            offset = vol_used / 500
            if offset > liquid_top:
                ctx.comment("WARNING: Not enough liquid in 50ml tube")
                return 1
            return liquid_top - offset
        if tube_type == "15ml":
            liquid_top = init_vol * 7.5
            # 1mm per 2ml
            if vol_used == 0:
                return liquid_top
            offset = vol_used / 133
            if offset > liquid_top:
                ctx.comment("WARNING: Not enough liquid in 15ml tube")
                return 1
            return liquid_top - offset

    for init_vol, tube, tube_type, deepwell, vol in zip(
        [
            a1_init_vol, a3_init_vol, a4_init_vol, b3_init_vol], [
            tube_a1, tube_a3, tube_a4, tube_b3], [
                "15ml", "50ml", "50ml", "50ml"], [
                    deepwell_a1, deepwell_a3, deepwell_a4, deepwell_b3], [
                        50, 245, 200, 200]):
        vol_used = 0
        p1000s.pick_up_tip()
        for well in deepwell.wells():
            p1000s.transfer(
                vol,
                tube.bottom(
                    height_offset(
                        vol_used,
                        tube_type=tube_type,
                        init_vol=init_vol)),
                well,
                new_tip='never')
        p1000s.drop_tip()

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
    filename = f"detailed_action_json/7e4c3e-4.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)