import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7e4c3e-6/7e4c3e-6.ot2.apiv2.py"

import math
metadata = {'apiLevel': '2.5'}


def run(ctx):

    num_samples, tip_start_20, tip_start_1000 = get_values(  # noqa: F821
            'num_samples', 'tip_start_20', 'tip_start_1000')
    column_count = math.ceil(num_samples / 8)

    p20m_racks = [
        ctx.load_labware(
            "opentrons_96_filtertiprack_20ul",
            x) for x in [
            "2",
            "3"]]
    p20m = ctx.load_instrument(
        'p20_multi_gen2',
        'right',
        tip_racks=p20m_racks)
    p20m.starting_tip = p20m_racks[0].well(tip_start_20)
    p1000s_rack = ctx.load_labware("opentrons_96_filtertiprack_1000ul", "1")
    p1000s = ctx.load_instrument(
        'p1000_single_gen2',
        'left',
        tip_racks=[p1000s_rack])
    p1000s.starting_tip = p1000s_rack.well(tip_start_1000)

    applied_biosystems_plate = ctx.load_labware(
            "appliedbiosystemsmicroampoptical384wellreactionplatewithbarcode_384_wellplate_30ul",  # noqa: E501
            "6")
    tube_rack = ctx.load_labware(
        "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", "4")
    pcr_strip = ctx.load_labware(
        "opentrons_96_aluminumblock_generic_pcr_strip_200ul", "5")

    master_mix_1 = tube_rack.wells_by_name()["A1"]
    master_mix_2 = tube_rack.wells_by_name()["B1"]

    p1000s.transfer(200, master_mix_1, pcr_strip.columns()[0], new_tip="once")
    p1000s.transfer(100.8, master_mix_2, pcr_strip.columns()[1])

    for source_well, target_loc in zip([pcr_strip.wells_by_name()["A1"], pcr_strip.wells_by_name()[  # noqa: E501
            "B1"]], [[1, 2, 4, 5, 7, 8, 10, 11, 13, 14, 16, 17][:math.ceil(column_count / 2) * 2], [3, 6, 9, 12, 15, 18][:math.ceil(column_count / 2)]]):  # noqa: E501
        p20m.pick_up_tip()
        for letter in ["A", "B"]:
            for num in target_loc:
                p20m.aspirate(8, source_well)
                p20m.dispense(
                    8, applied_biosystems_plate.wells_by_name()[
                        "{}{}".format(
                            letter, num)])
        p20m.drop_tip()

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
    filename = f"detailed_action_json/7e4c3e-6.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)