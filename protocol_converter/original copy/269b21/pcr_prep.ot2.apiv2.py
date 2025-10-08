import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/269b21/pcr_prep.ot2.apiv2.py"

# metadata
metadata = {
    'protocolName': 'PCR Prep',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(ctx):

    [num_mm, num_samples, p20_mount] = get_values(  # noqa: F821
        'num_mm', 'num_samples', 'p20_mount')

    # labware
    plate384 = ctx.load_labware(
        'biorad_384_wellplate_50ul', '1', '384-well plate')
    stripblock = ctx.load_labware('genmate_96_aluminumblock_20ul', '2')
    tempdeck = ctx.load_module('tempdeck', '4')
    tubeblock = tempdeck.load_labware(
        'opentrons_24_aluminumblock_nest_1.5ml_snapcap')
    tempdeck.set_temperature(4)
    tiprack20 = [
        ctx.load_labware('opentrons_96_tiprack_20ul', slot, '20µl tiprack')
        for slot in ['5', '6']]

    # pipette
    p20 = ctx.load_instrument(
        'p20_single_gen2', p20_mount, tip_racks=tiprack20)

    # mm and sample setup
    mm = [well for row in tubeblock.rows() for well in row][:num_mm]
    samples = [well for row in stripblock.rows() for well in row][:num_samples]
    mm_dests = [
        [well
         for set in [row[i*3:i*3+3]
                     for row in plate384.rows()[r*2:r*2+2]]
         for well in set]
        for r in range(len(plate384.rows())//2)
        for i in range(len(plate384.columns())//3)][:num_mm]
    sample_dests = [
        row[i*6:i*6+6]
        for i in range(len(plate384.columns())//6)
        for row in plate384.rows()][:num_samples]

    # transfer mastermix 6-replicates
    for m, d_set in zip(mm, mm_dests):
        p20.pick_up_tip()
        for d in d_set:
            p20.transfer(10, m, d.bottom(2), new_tip='never')
            p20.blow_out(d.top(-2))
        p20.drop_tip()

    # transfer samples
    for samp, s_set in zip(samples, sample_dests):
        for s in s_set:
            p20.pick_up_tip()
            p20.transfer(5, samp, s.bottom(2), new_tip='never')
            p20.blow_out(s.top(-2))
            p20.drop_tip()

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
    filename = f"detailed_action_json/269b21.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)