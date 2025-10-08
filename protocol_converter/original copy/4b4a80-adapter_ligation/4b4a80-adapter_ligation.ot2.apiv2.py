import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/4b4a80-adapter_ligation/4b4a80-adapter_ligation.ot2.apiv2.py"

metadata = {
    'protocolName': '''NEBNext Ultra II FS DNA Library Prep Kit for Illumina
    E6177S/L (for 1-24 DNA samples): Step 3: Adapter Ligation''',
    'author': 'Steve Plonk <protocols@opentrons.com>',
    'apiLevel': '2.9'
}


def run(ctx):

    # bring in constant values from json string above
    [pcr_labware, sample_count, fragmented_sample_volume,
     ligation_mastermix_volume, ligation_mastermix_well,
     ligation_enhancer_volume, ligation_enhancer_well, ligation_adapter_volume,
     ligation_adapter_well, user_enzyme_volume, user_enzyme_well,
     empty_vial_well] = get_values(  # noqa: F821
      'pcr_labware', 'sample_count', 'fragmented_sample_volume',
      'ligation_mastermix_volume', 'ligation_mastermix_well',
      'ligation_enhancer_volume', 'ligation_enhancer_well',
      'ligation_adapter_volume', 'ligation_adapter_well', 'user_enzyme_volume',
      'user_enzyme_well', 'empty_vial_well')

    ctx.set_rail_lights(True)
    ctx.delay(seconds=10)

    if sample_count < 1 or sample_count > 24:
        raise Exception('Invalid number of samples (must be 1-24).')

    # turn off rail lights to bring the pause to the user's attention
    ctx.set_rail_lights(False)
    ctx.pause(f"""Please pre-cool the
    temperature module to 4 degrees via settings in the Opentrons app prior to
    running this protocol. Please add ligation master mix to well
    {ligation_mastermix_well}, ligation enhancer to well
    {ligation_enhancer_well}, ligation adapter to well {ligation_adapter_well},
    user enzyme to well {user_enzyme_well} and an empty vial to well
    {empty_vial_well} of the 4 degree temperature module on the OT-2 deck.""")
    ctx.set_rail_lights(True)

    # setup p20 single channel, p300 single channel, tips
    tips20 = [ctx.load_labware("opentrons_96_filtertiprack_20ul", '6')]
    tips300 = [ctx.load_labware("opentrons_96_tiprack_300ul", '3')]
    p20 = ctx.load_instrument(
        "p20_single_gen2", 'left', tip_racks=tips20)
    p300 = ctx.load_instrument(
        "p300_single_gen2", 'right', tip_racks=tips300)

    # temp mod at 4 degrees for mastermix, enhancer, adapter and user enzyme
    temp = ctx.load_module('Temperature Module', '2')
    temp_reagents = temp.load_labware(
        'opentrons_24_aluminumblock_nest_0.5ml_screwcap',
        'Opentrons 24-Well Aluminum Block')
    temp.set_temperature(4)

    # setup thermocycler for adapter ligation and user enzyme step
    tc = ctx.load_module('thermocycler')
    tc.open_lid()
    tc_plate = tc.load_labware(pcr_labware)

    # fragmented sample locations (first three columns of thermocycler plate)
    fragmented_sample = tc_plate.wells()[:sample_count]

    # reagent setup: combine mastermix, enhancer and adapter
    # adjusted settings, air gaps and blow outs for pipetting of viscous liquid
    p300.flow_rate.aspirate = 40
    p300.flow_rate.dispense = 40
    p300.flow_rate.blow_out = 300

    mixture_volume = ligation_mastermix_volume
    + ligation_enhancer_volume + ligation_adapter_volume

    ligation_mastermix, ligation_enhancer, ligation_adapter, user_enzyme,  mixture = [temp_reagents.wells_by_name()[well] for well in [
         ligation_mastermix_well, ligation_enhancer_well,
         ligation_adapter_well, user_enzyme_well, empty_vial_well]]

    p300.pick_up_tip()
    p300.mix(10, 250, ligation_mastermix.bottom(1))
    p300.blow_out(ligation_mastermix.top())
    p300.drop_tip()
    p300.transfer(
     [(sample_count + 1)*ligation_mastermix_volume,
      (sample_count + 1)*ligation_enhancer_volume],
     [ligation_mastermix, ligation_enhancer],
     mixture, air_gap=20, blow_out=True, new_tip='always')
    p300.transfer(
     (sample_count + 1)*ligation_adapter_volume,
     ligation_adapter, mixture, mix_after=(10, 250))

    # set aspirate, dispense, and blow_out rate back to default values
    p300.flow_rate.aspirate = 92.86
    p300.flow_rate.dispense = 92.96
    p300.flow_rate.blow_out = 92.86

    # add mixture (mastermix + enhancer + adapter) to fragmented samples
    p300.transfer(
     mixture_volume, mixture, fragmented_sample,
     mix_after=(3, (mixture_volume + fragmented_sample_volume) / 2),
     new_tip="always")

    # define adapter ligation protocol profile
    adapter_ligation_profile = [{'temperature': 20, 'hold_time_minutes': 15}]

    # run adapter ligation protocol
    tc.close_lid()
    tc.execute_profile(
     steps=adapter_ligation_profile,
     repetitions=1, block_max_volume=fragmented_sample_volume + mixture_volume)
    tc.open_lid()

    # ensure that the thermocycler lid is fully open to avoid risk of collision
    ctx.set_rail_lights(False)
    ctx.pause(
     """Important. Please ensure that the thermocycler lid is fully open to
     avoid collision with the pipette""")
    ctx.set_rail_lights(True)

    # add user enzyme
    p20.transfer(
     user_enzyme_volume, user_enzyme, fragmented_sample, mix_after=(6, 15),
     new_tip='always')

    # define user enzyme profile
    user_enzyme_profile = [{'temperature': 37, 'hold_time_minutes': 15}]

    # run user enzyme protocol
    tc.close_lid()
    tc.set_lid_temperature(47)
    tc.execute_profile(
     steps=user_enzyme_profile, repetitions=1,
     block_max_volume=fragmented_sample_volume + mixture_volume)
    tc.set_block_temperature(4)
    tc.set_lid_temperature(22)
    tc.open_lid()

    ctx.comment("Adapter ligation step is complete")
    ctx.set_rail_lights(False)

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
    filename = f"detailed_action_json/4b4a80-adapter_ligation.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)