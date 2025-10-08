import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/3a49b6/3a49b6.ot2.apiv2.py"

metadata = {
    'protocolName': 'Normalization',
    'author': 'Steve <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(ctx):

    ctx.set_rail_lights(True)

    # uploaded csv
    [p20_side, clearance_water, mix_count, flow_rate_factor,
     uploaded_csv] = get_values(  # noqa: F821
        "p20_side", "clearance_water", "mix_count", "flow_rate_factor",
        "uploaded_csv")

    # data from csv
    header_line, *data_lines = uploaded_csv.splitlines()
    data = [
     dict(zip([item for item in header_line.split(",") if any(item)],
          [item for item in line.split(',')])) for line in data_lines]

    # tips and p20 single
    tips20 = [
     ctx.load_labware(
      "opentrons_96_filtertiprack_20ul", str(slot)) for slot in [8, 5]]
    p20s = ctx.load_instrument(
        "p20_single_gen2", p20_side, tip_racks=tips20)

    # helper function
    def flow_rate_settings():
        if 0.5 <= flow_rate_factor <= 3:
            speed = flow_rate_factor*7.34
            p20s.flow_rate.aspirate = speed
            p20s.flow_rate.dispense = speed

    flow_rate_settings()

    # labware
    [tube_rack, dest_plate] = [
     ctx.load_labware(labware, slot) for labware, slot in zip(
        ["opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical",
         "nest_96_wellplate_100ul_pcr_full_skirt"],
        [str(num) for num in [11, 6, 9]])]

    # water in well A1 of tube rack in slot 11
    water = tube_rack.wells_by_name()['A1']

    # temperature module with pcr plate containing RNA in slot 3
    temp_mod = ctx.load_module('temperature module gen2', '3')
    rna = temp_mod.load_labware("nest_96_wellplate_100ul_pcr_full_skirt")
    temp_mod.set_temperature(4)

    # water to destination plate
    # if Vol RNA < 1 ul, set data['Vol RNA']='1'
    # if Vol H2O < 1 ul, set data['Vol H2O']='0'
    p20s.pick_up_tip()
    for item in data:
        if float(item['Vol RNA']) < 1:
            item['Vol RNA'] = '1'
        if float(item['Vol H2O']) < 1:
            item['Vol H2O'] = '0'
        p20s.transfer(
         round(float(item['Vol H2O']), 2), water.bottom(clearance_water),
         dest_plate.wells_by_name()[item['Well']],
         new_tip='never')
    p20s.drop_tip()

    # rna to destination plate
    for item in data:
        p20s.transfer(
         round(float(item['Vol RNA']), 2),
         rna.wells_by_name()[item['Well']],
         dest_plate.wells_by_name()[item['Well']],
         mix_after=(mix_count, 10), new_tip='always')

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
    filename = f"detailed_action_json/3a49b6.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)