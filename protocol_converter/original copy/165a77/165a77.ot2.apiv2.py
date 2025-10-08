import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/165a77/165a77.ot2.apiv2.py"

from opentrons import types

metadata = {
    'protocolName': 'PCR/qPCR prep: distribute samples to 384 well plates',
    'author': 'Steve Plonk <protocols@opentrons.com>',
    'apiLevel': '2.9'
}


def run(ctx):

    # bring in constant values from json string above
    [plate_count, samp_col_counts, labware_384_well_plate,
     labware_patient_samples, patient_sample_vol, disposal_vol,
     patient_sample_count, include_ntc
     ] = get_values(  # noqa: F821
      'plate_count', 'samp_col_counts', 'labware_384_well_plate',
      'labware_patient_samples', 'patient_sample_vol', 'disposal_vol',
      'patient_sample_count', 'include_ntc')

    ctx.set_rail_lights(True)

    # a samp_col_count value between 1-12 specified for each 384-well plate
    if len(samp_col_counts.split(',')) != plate_count:
        raise Exception('''A count of patient sample columns (between 1 and 12)
        must be specified for each 384-well plate.''')

    for num in samp_col_counts.split(','):
        if (int(num) < 1) or (int(num) > 12):
            raise Exception('''Invalid number of sample columns specified
            (must be 1-12).''')

    # patient sample column count for each 384-well plate
    col_counts = samp_col_counts.split(',')

    # tips
    tips20 = [
     ctx.load_labware("opentrons_96_filtertiprack_20ul", slot) for slot in [
      str(slot) for slot in [1, 4, 7]][:plate_count]]

    # p20 multi channel
    p20m = ctx.load_instrument(
        "p20_multi_gen2", "right", tip_racks=tips20)

    # source and destination plates
    patient_samples = [
     ctx.load_labware(labware_patient_samples, slot) for slot in [
      str(slot) for slot in [2, 5, 8]][:plate_count]]
    plates_384 = [
     ctx.load_labware(labware_384_well_plate, slot) for slot in [
      str(slot) for slot in [3, 6, 9]][:plate_count]]

    # patient sample column count for each 384-well plate
    col_counts = samp_col_counts.split(',')

    # to optionally skip no-template control
    if include_ntc:
        well_index = 2
    else:
        well_index = 1

    # distribute sample in "384 plate map.png" arrangement
    for i, plate in enumerate(patient_samples):
        # to yield next 384 column
        next_col = (
         column for column in plates_384[i].columns()[:2*int(col_counts[i])])
        for column in patient_samples[i].columns()[:int(col_counts[i])]:
            dest = [
              well.center().move(types.Point(
               well.diameter*0.08, -well.diameter*0.08, 1)) for well in next(
               next_col)[:2]] + [well.center().move(types.Point(
                well.diameter*0.08, -well.diameter*0.08, 1)) for well in next(
                next_col)[:well_index]]
            p20m.distribute(
             patient_sample_vol, [column[0], column[0]], dest,
             disposal_volume=disposal_vol)

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
    filename = f"detailed_action_json/165a77.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)