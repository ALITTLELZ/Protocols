import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/33b12a/33b12a.ot2.apiv2.py"

metadata = {
    'apiLevel': '2.5',
    'protocolName': 'CerTest VIASURE SARS-CoV-2 Real Time PCR Detection kit',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Custom Protocol Request'
}


def run(ctx):

    rehydration_buffer = ctx.load_labware(
        'nest_1_reservoir_195ml', '3').wells()[0]
    pcr_plate = ctx.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt', '5')
    sample_plate = ctx.load_labware(
        'nest_96_wellplate_2ml_deep', '6')
    controls = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '8')
    pos_ctrl = controls.wells()[0]
    neg_ctrl = controls.wells()[1]

    tip_racks = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_20ul',
            x) for x in [
            '7',
            '4']]
    p20m = ctx.load_instrument('p20_multi_gen2', 'right', tip_racks=tip_racks)

    [p20m.transfer(15, rehydration_buffer, col, mix_after=(2, 10))
     for col in pcr_plate.rows()[0]]
    for i, col in enumerate(sample_plate.rows()[0][:-1]):
        p20m.transfer(5, col, pcr_plate.rows()[0][i], mix_after=(1, 5))

    p20m.pick_up_tip(tip_racks[1]['C12'])
    p20m.aspirate(5, sample_plate.rows()[0][-1])
    p20m.dispense(5, pcr_plate.rows()[0][-1])
    p20m.drop_tip()

    p20m.pick_up_tip(tip_racks[1]['B12'])
    p20m.aspirate(5, neg_ctrl)
    p20m.dispense(5, pcr_plate.wells_by_name()["G12"])
    p20m.drop_tip()

    p20m.pick_up_tip(tip_racks[1]['A12'])
    p20m.aspirate(5, pos_ctrl)
    p20m.dispense(5, pcr_plate.wells_by_name()["H12"])
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
    filename = f"detailed_action_json/33b12a.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)