import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7062c9/normalization.ot2.apiv2.py"

from opentrons.types import Mount

metadata = {
    'protocolName': 'Capping Assay: Steps 1-2',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.13'
    }


def run(ctx):
    [input_csv, p300_mount, p20_mount] = get_values(  # noqa: F821
        'input_csv', 'p300_mount', 'p20_mount')

    # labware
    sample_racks = [
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', slot,
            f'sample rack {i+1}')
        for i, slot in enumerate(['7', '4'])]
    final_plate = ctx.load_labware('neptune_96_aluminumblock_200ul',
                                   '5', 'normalized plate')
    tuberack = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '8',
        'buffer + probe tuberack')
    tipracks20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', '3')]
    tipracks200 = ctx.load_labware('opentrons_96_filtertiprack_200ul', '9')

    # pipettes
    p300 = ctx.load_instrument('p300_multi_gen2', p300_mount,
                               tip_racks=[tipracks200])
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount,
                              tip_racks=tipracks20)

    mount = Mount.LEFT if p300.mount == 'left' else Mount.RIGHT
    ctx._hw_manager.hardware._attached_instruments[
        mount].update_config_item(
            'pick_up_current', 0.1)

    # reagents
    water = tuberack.wells()[0]
    buffer = tuberack.wells()[1]
    protease = tuberack.wells()[2]

    def drop_all_tips():
        for pipette in ctx.loaded_instruments.values():
            if pipette.has_tip:
                pipette.drop_tip()

    tip_data = {
        'single': {
            'count': 0,
            'tips': [
                well for col in tipracks200.columns()
                for well in col[::-1]]
        },
        'multi': {
            'count': 0,
            'tips': [tipracks200.rows()[0][::-1]]
        }
    }

    def pickup_p300(mode='single'):
        p300.pick_up_tip(tip_data[mode]['tips'][tip_data[mode]['count']])
        tip_data[mode]['count'] += 1

    def slow_withdraw(pip, well, delay_seconds=2.0):
        pip.default_speed /= 16
        if delay_seconds > 0:
            ctx.delay(seconds=delay_seconds)
        pip.move_to(well.top())
        pip.default_speed *= 16

    # parse csv
    data = [
        [val for val in line.split(',')]
        for line in input_csv.splitlines()[1:]
        if line and line.split(',')[0].strip()]

    output_wells = final_plate.wells()[:16] + final_plate.wells()[95:79:-1]

    # prealocate water
    for i, line in enumerate(data):
        water_vol = float(line[2])
        pip = p20 if water_vol <= 20 else p300
        dest_well = output_wells[i]
        if not pip.has_tip:
            if pip == p20:
                pip.pick_up_tip()
            else:
                pickup_p300('single')
        pip.aspirate(water_vol, water.bottom(1))
        slow_withdraw(pip, water)
        pip.dispense(water_vol, dest_well.bottom(1))
        slow_withdraw(pip, dest_well)
    drop_all_tips()

    # prealocate buffer
    for i, line in enumerate(data):
        buffer_vol = float(line[3])
        pip = p20 if buffer_vol <= 20 else p300
        dest_well = output_wells[i]
        if not pip.has_tip:
            if pip == p20:
                pip.pick_up_tip()
            else:
                pickup_p300('single')
        pip.aspirate(buffer_vol, buffer.bottom(1))
        slow_withdraw(pip, buffer)
        pip.dispense(buffer_vol, dest_well.bottom(1))
        slow_withdraw(pip, dest_well)
    drop_all_tips()

    last_probe = None
    for i, line in enumerate(data):
        probe_vol = float(line[4])
        probe = tuberack.wells_by_name()[line[5].upper().strip()]
        pip = p20 if probe_vol <= 20 else p300
        dest_well = output_wells[i]
        if not probe == last_probe:
            if pip.has_tip:
                pip.drop_tip()
            if pip == p20:
                pip.pick_up_tip()
            else:
                pickup_p300('single')
        pip.aspirate(probe_vol, probe.bottom(1))
        slow_withdraw(pip, probe)
        pip.dispense(probe_vol, dest_well.bottom(1))
        slow_withdraw(pip, dest_well)
    drop_all_tips()

    # transfer sample and mix
    samples = [well for rack in sample_racks for well in rack.wells()]
    for i, line in enumerate(data):
        sample_vol = float(line[1])
        total_vol = float(line[6])
        pip = p20 if sample_vol <= 20 else p300
        sample_well, dest_well = [
            samples[i], output_wells[i]]
        if 0.8*total_vol < pip.max_volume:
            mix_vol = 0.8*total_vol
        else:
            mix_vol = 0.8*pip.max_volume
        if pip == p20:
            pip.pick_up_tip()
        else:
            pickup_p300('single')
        pip.aspirate(sample_vol, sample_well.bottom(1))
        slow_withdraw(pip, sample_well)
        pip.dispense(sample_vol, dest_well.bottom(1))
        pip.mix(3, mix_vol, dest_well.bottom(1))
        slow_withdraw(pip, dest_well)
        drop_all_tips()

    ctx.pause('Put sample plate in the thermal cycler for 30min')

    # transfer protease
    for i, line in enumerate(data):
        dest_well = output_wells[i]
        p20.pick_up_tip()
        p20.aspirate(5, protease.bottom(1))
        slow_withdraw(p20, protease)
        p20.dispense(5, dest_well.bottom(1))
        p20.mix(3, 20, dest_well.bottom(1))
        slow_withdraw(p20, dest_well)
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
    filename = f"detailed_action_json/7062c9.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)