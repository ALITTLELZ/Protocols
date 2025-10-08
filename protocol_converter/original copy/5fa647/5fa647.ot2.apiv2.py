import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/5fa647/5fa647.ot2.apiv2.py"

metadata = {
    'protocolName': 'SuperScript III: qRT-PCR Prep with CSV File',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(ctx):

    [csv_samp, num_samp, p20_mount, p300_mount] = get_values(  # noqa: F821
        "csv_samp", "num_samp", "p20_mount", "p300_mount")

    # load labware
    thermocyc = ctx.load_module('thermocycler')
    tc_plate = thermocyc.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')
    sample_tubes = ctx.load_labware(
                        'opentrons_24_aluminumblock_1500ul', '1')
    reagent_tubes = ctx.load_labware(
                        'opentrons_24_aluminumblock_1500ul', '2')
    tiprack20 = ctx.load_labware('opentrons_96_filtertiprack_20ul', '3')
    tiprack200 = ctx.load_labware('opentrons_96_filtertiprack_200ul', '4')

    # load instruments
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount,
                              tip_racks=[tiprack20])
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount,
                               tip_racks=[tiprack200])

    # load reagents
    rxn_mix = reagent_tubes.wells_by_name()['A1']
    enzyme_mix = reagent_tubes.wells_by_name()['A2']
    mix_tube = reagent_tubes.wells_by_name()['A3']
    rnase = reagent_tubes.wells_by_name()['A4']
    water = reagent_tubes.wells_by_name()['A5']
    rxn_mix_vol = 10*num_samp+10  # extra 10ul to ensure full distribution
    enzyme_mix_vol = 2*num_samp+10  # extra 10ul to ensure full distribution

    if thermocyc.lid_position != 'open':
        thermocyc.lid_position == 'open'
    thermocyc.set_lid_temperature(25)

    data = [[val.strip() for val in line.split(',')]
            for line in csv_samp.splitlines()
            if line.split(',')[0].strip()][1:]

    # make mix, mix, then distribute
    ctx.comment('\nMixing 2x RT Reaction Mix and Enzyme Mix\n')
    p300.transfer(rxn_mix_vol, rxn_mix, mix_tube)
    p300.transfer(enzyme_mix_vol, enzyme_mix, mix_tube)
    p300.pick_up_tip()
    p300.mix(10, rxn_mix_vol+enzyme_mix_vol
             if rxn_mix_vol+enzyme_mix_vol < 200 else 200, mix_tube)
    p300.drop_tip()
    ctx.comment('\nTransferring mix to plate\n')
    p20.pick_up_tip()
    for well in tc_plate.wells()[32:32+num_samp]:  # put rxn in middle of plate
        p20.aspirate(12, mix_tube)
        p20.dispense(12, well)
    p20.drop_tip()

    ctx.comment('\nAdding RNA to plate\n')
    # add rna sample from csv_samp
    for vol, s, d, in zip(data,
                          sample_tubes.wells(),
                          tc_plate.wells()[32:32+num_samp]):
        p20.pick_up_tip()
        p20.aspirate(int(vol[1]), s)
        p20.dispense(int(vol[1]), d)
        p20.mix(5, 20, d)
        p20.drop_tip()

        profile = [
            {'temperature': 25, 'hold_time_minutes': 10},
            {'temperature': 50, 'hold_time_minutes': 30},
            {'temperature': 85, 'hold_time_minutes': 5},
            {'temperature': 37, 'hold_time_minutes': 20},
        ]

    all_volumes = [int(line[1]) for line in data]
    thermocyc.close_lid()
    thermocyc.execute_profile(steps=profile[0:3],
                              repetitions=1,
                              block_max_volume=max(all_volumes))
    thermocyc.open_lid()
    ctx.pause('''Please remove sample plate from thermocycler and chill on ice.
                 Once chilled, put sample plate back in the thermocycler for
                 additon of RNase H and water.''')

    p20.distribute(1,
                   rnase,
                   [well.top(z=1)
                    for well in tc_plate.wells()][32:32+num_samp],
                   new_tip='always',
                   blow_out=True,
                   blowout_location='source well')

    thermocyc.execute_profile(steps=profile[3:],
                              repetitions=1,
                              block_max_volume=max(all_volumes)+1)

    for well in tc_plate.wells()[32:32+num_samp]:
        p300.pick_up_tip()
        p300.aspirate(60, water)
        p300.dispense(60, well)
        p300.drop_tip()

    ctx.comment('Protocol complete - remove sample plate and store on ice.')

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
    filename = f"detailed_action_json/5fa647.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)