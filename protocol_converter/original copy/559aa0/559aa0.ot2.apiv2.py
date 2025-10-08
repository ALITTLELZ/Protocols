import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/559aa0/559aa0.ot2.apiv2.py"

metadata = {
    'protocolName': 'PCR/qPCR prep: distribute primers to 384 well plates',
    'author': 'Steve Plonk <protocols@opentrons.com>',
    'apiLevel': '2.9'
}


def run(ctx):

    # bring in constant values from json string above
    [samp_col_counts, plate_count, labware_384_well_plate, n1_col, n2_col,
     rp_col, ntc_col, primer_volume, disposal_vol, include_ntc, include_multi
     ] = get_values(  # noqa: F821
      'samp_col_counts', 'plate_count', 'labware_384_well_plate', 'n1_col',
      'n2_col', 'rp_col', 'ntc_col', 'primer_volume', 'disposal_vol',
      'include_ntc', 'include_multi')

    ctx.set_rail_lights(True)

    # a samp_col_count value between 1-12 specified for each 384-well plate
    if len(samp_col_counts.split(',')) != plate_count:
        raise Exception('''A count of patient sample columns (between 1 and 12,
        for downstream steps) must be specified for each 384-well plate.''')

    for num in samp_col_counts.split(','):
        if (int(num) < 1) or (int(num) > 12):
            raise Exception('''Invalid number of sample columns specified (
                               expected value between 1 and 12).''')

    # patient sample column count (in downstream steps) for each 384-well plate
    col_counts = samp_col_counts.split(',')

    # p20 multi channel, tips
    tips20 = [
     ctx.load_labware(
      "opentrons_96_filtertiprack_20ul", slot) for slot in [9]]

    p20m = ctx.load_instrument(
        "p20_multi_gen2", 'right', tip_racks=tips20)

    # source and destination plates
    one_ml_plate = ctx.load_labware("nunc_96_wellplate_1000ul", '8')

    available_slots = [
     str(slot) for slot in [*range(1, 12)] if ctx.deck[slot] is None]
    plates = [ctx.load_labware(
     labware_384_well_plate, slot) for slot in available_slots[:plate_count]]

    # optional single or multi dispenses
    if include_multi:
        multi = 2
    else:
        multi = 1

    # define pipetting steps
    def primer_transfer():
        p20m.pick_up_tip()
        for i, plate in enumerate(plates):
            col_count = int(col_counts[i])*2
            vol_in_tip = 0
            for index, column in enumerate(plate.columns()[:col_count]):
                if index % 2 == mod:
                    if vol_in_tip < primer_volume:
                        p20m.blow_out(
                         one_ml_plate.columns_by_name()[str(col)][0].bottom())
                        vol_in_tip = 0
                        p20m.aspirate(
                         (multi*primer_volume) + disposal_vol,
                         one_ml_plate.columns_by_name()[str(col)][0])
                        vol_in_tip += ((multi*primer_volume) + disposal_vol)
                    p20m.dispense(primer_volume, column[well])
                    vol_in_tip -= primer_volume
        p20m.drop_tip()

    # distribute primers (optionally skipping no-template control primer)
    if include_ntc:
        for mod, col, well in zip(
         [0, 0, 1, 1], [n1_col, rp_col, n2_col, ntc_col], [0, 1, 0, 1]):
            primer_transfer()
    else:
        for mod, col, well in zip(
         [0, 0, 1], [n1_col, rp_col, n2_col], [0, 1, 0]):
            primer_transfer()

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
    filename = f"detailed_action_json/559aa0.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)