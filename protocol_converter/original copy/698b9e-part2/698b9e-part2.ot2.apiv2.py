import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/698b9e-part2/698b9e-part2.ot2.apiv2.py"

metadata = {
    'protocolName': 'PCR Prep with 1.5 mL Tubes Part 2 - Adding Sample',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(ctx):

    [num_samp, p20_mount,
        p300_mount, aspirate_delay_time] = get_values(  # noqa: F821
        "num_samp", "p20_mount", "p300_mount", "aspirate_delay_time")

    # load labware
    saliva = ctx.load_labware('opentrons_15_tuberack_falcon_15ml_conical', '1')
    buffer = ctx.load_labware('nunc_96_wellplate_450ul', '2')
    mastermix_plate = ctx.load_labware('microamp_96_wellplate_100ul', '4')
    tiprack20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', '5')]
    tiprack300 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '6')]

    # load instruments
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount,
                               tip_racks=tiprack300)
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount,
                              tip_racks=tiprack20)

    # step 1 - add saliva samples to buffer plates
    ctx.comment('\n\nAdding Saliva to Buffer\n\n')
    airgap = 10
    tube_counter = num_samp
    well_ctr = 0
    while tube_counter > 0:
        for i, saliva_tube in enumerate(saliva.wells()[:tube_counter]):
            p300.pick_up_tip()
            p300.aspirate(80, saliva_tube)
            ctx.delay(seconds=aspirate_delay_time)
            p300.air_gap(airgap)
            p300.touch_tip()
            p300.dispense(80+airgap, buffer.wells()[i+well_ctr])
            p300.mix(6, 150, buffer.wells()[i+well_ctr])
            p300.blow_out()
            p300.drop_tip()
            ctx.comment('\n')
        tube_counter -= 15
        well_ctr += 15
        if tube_counter > 0:
            ctx.pause('''Replace sample tubes in tube rack -
                         if needed, empty trash.''')

    # step 2 - add diluted saliva to mastermix plates
    ctx.comment('\n\nAdding Diluted Saliva to Mastermix Plates\n\n')
    airgap = 5
    for s, d in zip(buffer.wells()[:num_samp],
                    mastermix_plate.wells()):
        p20.pick_up_tip()
        p20.aspirate(2.4, s)
        ctx.delay(seconds=aspirate_delay_time)
        p20.air_gap(airgap)
        p20.touch_tip()
        p20.dispense(2.4+airgap, d)
        p20.mix(6, 9, d)
        p20.blow_out()
        p20.drop_tip()
        ctx.comment('\n')

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
    filename = f"detailed_action_json/698b9e-part2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)