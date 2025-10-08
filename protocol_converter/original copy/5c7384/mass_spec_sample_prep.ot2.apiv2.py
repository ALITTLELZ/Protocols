import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/5c7384/mass_spec_sample_prep.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Mass Spec Sample Prep',
    'author': 'Nick <ndiehl@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(ctx):

    [num_samples, p20_type, p300_type, p20_mount, p300_mount, plate_def,
     module_type] = get_values(  # noqa: F821
        'num_samples', 'p20_type', 'p300_type', 'p20_mount', 'p300_mount',
        'plate_def', 'module_type')

    waste = ctx.load_labware('nest_1_reservoir_195ml', '1',
                             'waste container (load empty)').wells()[0].top()
    tips20 = [
        ctx.load_labware('opentrons_96_tiprack_20ul', slot)
        for slot in ['6']]
    tips300 = [
        ctx.load_labware('opentrons_96_tiprack_300ul', slot)
        for slot in ['9']]
    magdeck = ctx.load_module('magnetic module gen2', '4')
    mag_plate = magdeck.load_labware(plate_def)
    reagent_plate = ctx.load_labware(plate_def, '5', 'reagent plate')
    etoh_plate = ctx.load_labware(plate_def, '2', 'ethanol plate')
    acetonitrile_plate = ctx.load_labware(
        plate_def, '3', 'acetonitrile plate')
    if module_type == 'thermocycler':
        temp_module = ctx.load_module('thermocycler')
        heat_func = temp_module.set_block_temperature
    else:
        tips20.insert(-1, ctx.load_labware('opentrons_96_tiprack_20ul', '8'))
        tips300.insert(
            -1, ctx.load_labware('opentrons_96_tiprack_300ul', '11'))
        temp_module = ctx.load_module('temperature module gen2', '7')
        heat_func = temp_module.set_temperature

    sample_plate = temp_module.load_labware(plate_def, 'sample plate')
    num_cols = math.ceil(num_samples/8)
    samples_s = sample_plate.wells()[:num_samples]
    samples_m = sample_plate.rows()[0][:num_cols]
    mag_samples_s = mag_plate.wells()[:num_samples]
    mag_samples_m = mag_plate.rows()[0][:num_cols]

    p20 = ctx.load_instrument(p20_type, p20_mount, tip_racks=tips20)
    p300 = ctx.load_instrument(p300_type, p300_mount,
                               tip_racks=tips300)

    if p20.channels == 1:
        dtt = reagent_plate.columns()[0]
        caa = reagent_plate.columns()[1]
        mag_bead_stock = reagent_plate.columns()[2]
        acetonitrile = acetonitrile_plate.wells()[:num_samples]
    else:
        dtt = reagent_plate.rows()[0][0]
        caa = reagent_plate.rows()[0][1]
        mag_bead_stock = reagent_plate.rows()[0][2]
        acetonitrile = acetonitrile_plate.rows()[0][:num_cols]

    if p300.channels == 1:
        etoh = etoh_plate.wells()[:num_samples]
        abc = reagent_plate.columns()[3:5]
        trypsin = reagent_plate.columns()[5]
    else:
        etoh = etoh_plate.rows()[0][:num_cols]
        abc = reagent_plate.rows()[0][3:5]
        trypsin = reagent_plate.rows()[0][5]

    heat_func(60)

    tip_log = {}
    if p20.channels == 1:
        tip_list20 = [tip for rack in tips20 for tip in rack.wells()]
    else:
        tip_list20 = [tip for rack in tips20 for tip in rack.rows()[0]]
    if p300.channels == 1:
        tip_list300 = [tip for rack in tips300 for tip in rack.wells()]
    else:
        tip_list300 = [tip for rack in tips300 for tip in rack.rows()[0]]

    tip_log['tips'] = {
        p20: tip_list20,
        p300: tip_list300}
    tip_log['max'] = {
        p20: len(tip_log['tips'][p20]),
        p300: len(tip_log['tips'][p300])}
    tip_log['count'] = {p20: 0, p300: 0}

    def _pick_up(pip, loc=None):
        if tip_log['count'][pip] == tip_log['max'][pip] and not loc:
            ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before  resuming.')
            pip.reset_tipracks()
            tip_log['count'][pip] = 0
        if loc:
            pip.pick_up_tip(loc)
        else:
            pip.pick_up_tip(tip_log['tips'][pip][tip_log['count'][pip]])
            tip_log['count'][pip] += 1

    """ Reduction and Alkylation """
    samples = samples_s if p20.channels == 1 else samples_m
    for i, s in enumerate(samples):
        _pick_up(p20)
        p20.transfer(5, dtt, s, mix_after=(2, 5), new_tip='never')
        p20.drop_tip()

    ctx.delay(minutes=30, msg='Incubating 30 minutes at 60C for reduction.')

    for i, s in enumerate(samples):
        _pick_up(p20)
        p20.transfer(5, caa, s, mix_after=(2, 5), new_tip='never')
        p20.drop_tip()

    heat_func(25)
    ctx.delay(minutes=30, msg='Incubating 30 minutes at RT (25C) for  alkylation.')

    """ Protein Binding """
    for i, s in enumerate(samples):
        _pick_up(p20)
        p20.transfer(5, mag_bead_stock, s, mix_after=(2, 5),
                     new_tip='never')
        p20.drop_tip()

    for i, (s, a) in enumerate(zip(samples, acetonitrile)):
        _pick_up(p20)
        p20.transfer(15, a, s, mix_after=(2, 20),
                     new_tip='never')
        p20.return_tip()

    ctx.pause('Please move plate from thermocycler to magnetic module. Resume  when the plate has been moved.')

    magdeck.engage()
    ctx.delay(minutes=5, msg='Incubating on magnet for 5 minutes.')

    mag_samples = mag_samples_s if p20.channels == 1 else mag_samples_m
    for i, m in enumerate(mag_samples):
        _pick_up(p20, tips20[0].wells()[i])
        p20.transfer(43, m.bottom(1), waste, new_tip='never')
        p20.drop_tip()

    """ Ethanol Wash """
    mag_samples = mag_samples_s if p300.channels == 1 else mag_samples_m
    for wash in range(2):
        magdeck.disengage()
        for i, (m, e) in enumerate(zip(mag_samples, etoh)):
            _pick_up(p300)
            p300.transfer(200, e, m, mix_after=(10, 50), new_tip='never')
            p300.return_tip()

        magdeck.engage()
        ctx.delay(minutes=5, msg='Incubating on magnet for 5 minutes.')

        for i, m in enumerate(mag_samples):
            _pick_up(p300)
            p300.transfer(230, m.bottom(1), waste, new_tip='never')
            p300.return_tip()

        ctx.pause('Please replace the ethanol plate (slot 6) with a fresh  plate of ethanol before resuming.')

    """ Acetonitrile Wash """
    magdeck.disengage()
    for i, (m, a) in enumerate(zip(mag_samples, acetonitrile)):
        _pick_up(p300, tips300[0].wells()[i])
        p300.transfer(171.5, a, m, mix_after=(10, 50), new_tip='never')
        p300.return_tip()

    magdeck.engage()
    ctx.delay(minutes=5, msg='Incubating on magnet for 5 minutes')

    for i, m in enumerate(mag_samples):
        _pick_up(p300, tips300[0].wells()[i])
        p300.transfer(230, m.bottom(1), waste, new_tip='never')
        p300.drop_tip()

    ctx.pause('Place plate in thermocycler')

    """ On-Bead Digestion """
    if p300.channels == 1:
        samples = samples_s
        for i, s in enumerate(samples):
            _pick_up(p300)
            p300.transfer(35, abc[i//48][(i % 48) % 8], s, new_tip='never')
            p300.drop_tip()
    else:
        samples = samples_m
        for i, s in enumerate(samples):
            _pick_up(p300)
            p300.transfer(35, abc[i//6], s, new_tip='never')
            p300.drop_tip()

    if p20.channels == 1:
        samples = samples_s
        for i, s in enumerate(samples):
            _pick_up(p20)
            p20.transfer(5, trypsin[i % 8], s, mix_after=(2, 5),
                         new_tip='never')
            p20.drop_tip()
    else:
        samples = samples_m
        for i, s in enumerate(samples):
            _pick_up(p20)
            p20.transfer(5, trypsin, s, mix_after=(2, 5), new_tip='never')
            p20.drop_tip()

    heat_func(37)
    ctx.comment('Protocol complete. Please shake the plate from the magnetic  module to resuspend the beads, and replace on the thermocycler now set at \
37C.')

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
    filename = f"detailed_action_json/5c7384.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)