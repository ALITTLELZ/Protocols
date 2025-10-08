import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/459a55/mass_spec_prep.ot2.apiv2.py"

# metadata
metadata = {
    'protocolName': 'Mass Spec Sample Prep',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(ctx):

    [p300_mount, p20_mount, num_samples] = get_values(  # noqa: F821
        'p300_mount', 'p20_mount', 'num_samples')

    # check
    if num_samples > 22 or num_samples < 1:
        raise Exception('Invalid number of samples (must be 1-22)')
    if p300_mount == p20_mount:
        raise Exception('Pipette mounts cannot match.')

    # labware
    tempdeck = ctx.load_module('tempdeck', '1')
    plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul')
    tubeblock = ctx.load_labware(
        'opentrons_24_aluminumblock_nest_1.5ml_snapcap', '2', 'sample tubes')
    tiprack300 = [
        ctx.load_labware('opentrons_96_tiprack_300ul', '5', '300ul tiprack')]
    tiprack20 = [
        ctx.load_labware('opentrons_96_tiprack_20ul', '6', '20ul tiprack')]

    # pipettes
    p300 = ctx.load_instrument(
        'p300_single_gen2', p300_mount, tip_racks=tiprack300)
    p20 = ctx.load_instrument(
        'p20_single_gen2', p20_mount, tip_racks=tiprack20)

    # samples and reagent setup
    starting_tubes = [
        tube for tube in
        [well for col in tubeblock.columns()[:2] for well in col[:3]] + [
         well for col in tubeblock.columns()[2:]
         for well in col]][:num_samples]
    samples = [
        plate.wells_by_name()[tube.display_name.split(' ')[0]]
        for tube in starting_tubes][:num_samples]
    denaturing_sol = tubeblock.wells_by_name()['D1']
    dtt = tubeblock.wells_by_name()['D2']

    # transfer from tubes to plate
    for tube, well in zip(starting_tubes, samples):
        p300.pick_up_tip()
        p300.transfer(50, tube, well, air_gap=10, new_tip='never')
        p300.blow_out(well.top(-1))
        p300.drop_tip()

    # transfer denaturing solution
    for well in samples:
        p300.pick_up_tip()
        p300.transfer(
            50, denaturing_sol, well, mix_after=(5, 50), new_tip='never')
        p300.blow_out(well.top(-1))
        p300.drop_tip()

    # transfer DTT
    for well in samples:
        p20.pick_up_tip()
        p20.transfer(10, dtt, well, new_tip='never')
        p20.blow_out(well.top(-1))
        p20.drop_tip()

    tempdeck.set_temperature(50)
    ctx.delay(minutes=60)
    tempdeck.set_temperature(4)
    ctx.comment('Protocol finished. Remove plate from 4˚C temperature module  when ready.')

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
    filename = f"detailed_action_json/459a55.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)