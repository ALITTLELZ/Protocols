import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0944e4/ngs_cleanup.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'NGS Library Cleanup with Ampure XP Beads',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.8'
}


def run(ctx):

    [p20_multi_mount, p300_multi_mount, number_of_samples, volume_of_beads,
     bead_incubation_time_in_minutes, bead_settling_time_on_magnet_in_minutes,
     drying_time_in_minutes, volume_EB_in_ul,
     volume_final_elution_in_ul] = get_values(  # noqa: F821
        'p20_multi_mount', 'p300_multi_mount', 'number_of_samples',
        'volume_of_beads', 'bead_incubation_time_in_minutes',
        'bead_settling_time_on_magnet_in_minutes', 'drying_time_in_minutes',
        'volume_EB_in_ul', 'volume_final_elution_in_ul')

    # check
    if number_of_samples > 96 or number_of_samples < 1:
        raise Exception('Invalid number of samples.')
    if p20_multi_mount == p300_multi_mount:
        raise Exception('Pipette mounts cannot match.')

    # load labware
    magdeck = ctx.load_module('magnetic module gen2', '1')
    mag_plate = magdeck.load_labware('twintec_pcr_plate', 'magnetic plate')
    elution_plate = ctx.load_labware('twintec_pcr_plate', '2', 'elution plate')
    tips20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', '3')]
    tips300 = [
        ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
        for slot in ['4', '5', '6', '8', '9', '10', '11']
    ]
    res12 = ctx.load_labware(
        'usascientific_12_reservoir_22ml', '7', 'reagent reservoir')

    # reagents
    beads = res12.wells()[0]
    etoh = res12.wells()[1]
    eb_buff = res12.wells()[2]
    waste = [chan.top(-10) for chan in res12.wells()[10:]]

    tips300_count = 0
    tips300_max = len(tips300)*12

    def pick_up():
        nonlocal tips300_count
        if tips300_count == tips300_max:
            raise Exception('Replace 200µl filter tipracks before resuming.')
            tips300_count = 0
            m300.reset()
        tips300_count += 1
        m300.pick_up_tip()

    # location for safe tip drop

    def drop(pip):
        pip.move_to(res12.wells()[7].top(10))
        pip.drop_tip()

    # pipettes
    m20 = ctx.load_instrument(
        'p20_multi_gen2', mount=p20_multi_mount, tip_racks=tips20)
    m300 = ctx.load_instrument(
        'p300_multi_gen2', mount=p300_multi_mount, tip_racks=tips300)
    m300.flow_rate.aspirate = 100
    m300.flow_rate.dispense = 200
    m20.flow_rate.aspirate = 3
    m20.flow_rate.dispense = 6

    # sample setup
    num_cols = math.ceil(number_of_samples/8)
    mag_samples = mag_plate.rows()[0][:num_cols]
    elution_samples = elution_plate.rows()[0][:num_cols]

    # mix beads
    ctx.max_speeds['A'] = 50
    ctx.max_speeds['Z'] = 50
    # transfer beads and mix samples
    for m in mag_samples:
        pick_up()
        m300.mix(5, volume_of_beads, beads)
        m300.blow_out(beads.top())
        m300.transfer(volume_of_beads, beads, m, new_tip='never')
        m300.blow_out()
        m300.mix(10, volume_of_beads, m)
        m300.blow_out(m.top())
        drop(m300)
    ctx.max_speeds['A'] = 125
    ctx.max_speeds['Z'] = 125

    # incubation
    ctx.delay(minutes=bead_incubation_time_in_minutes, msg='Incubating off  magnet for ' + str(bead_incubation_time_in_minutes) + ' minutes.')
    magdeck.engage(height=18)
    ctx.delay(minutes=bead_settling_time_on_magnet_in_minutes, msg='Incubating  on magnet for ' + str(bead_settling_time_on_magnet_in_minutes) + ' minutes.')

    # remove supernatant
    for m in mag_samples:
        pick_up()
        m300.transfer(
            175, m.bottom(0.5), waste[1], new_tip='never')
        m300.blow_out(waste[1])
        drop(m300)

    # 2x EtOH washes
    for _ in range(2):
        # transfer EtOH
        for m in mag_samples:
            pick_up()
            m300.transfer(180, etoh, m, new_tip='never', air_gap=20)
            m300.blow_out(m)
            drop(m300)

        ctx.delay(minutes=1, msg='Incubating for 1 minute.')

        # remove supernatant
        for m in mag_samples:
            pick_up()
            m300.transfer(
                180, m.bottom(0.5), waste[0], new_tip='never')
            m300.blow_out(waste[0])
            drop(m300)

    # remove residual supernatant
    for m in mag_samples:
        m20.pick_up_tip()
        m20.transfer(
            10, m.bottom(0.5), waste[1], new_tip='never')
        m20.blow_out()
        drop(m20)

    ctx.delay(
        minutes=drying_time_in_minutes, msg='Drying for  ' + str(drying_time_in_minutes) + ' minutes.')
    magdeck.disengage()

    # transfer EB buffer
    for m in mag_samples:
        pick_up()
        m300.aspirate(30, eb_buff.top(5))
        m300.aspirate(volume_EB_in_ul, eb_buff)
        m300.dispense(30+volume_EB_in_ul, m)
        m300.blow_out()
        drop(m300)

    ctx.pause('Remove PCR plate, seal and shake at 1800 RPM for 2 minutes.  Return PCR plate to magnetic module and incubate for 3 minutes before \
resuming.')

    magdeck.engage(height=18)
    ctx.delay(minutes=3, msg='Incubating on magnet for 3 minutes.')

    # transfer supernatant to new PCR plate
    for m, e in zip(mag_samples, elution_samples):
        pick_up()
        m300.aspirate(30, m.top(5))
        m300.aspirate(volume_final_elution_in_ul, m)
        m300.dispense(volume_final_elution_in_ul, e)
        m300.dispense(30, e.bottom(7))
        m300.blow_out(e.top(-2))
        drop(m300)

    magdeck.disengage()

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
    filename = f"detailed_action_json/0944e4.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)