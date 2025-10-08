import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/19fc32/19fc32.ot2.apiv2.py"

metadata = {
    'protocolName': 'Library Prep Clean Up',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.1'
}


def run(protocol):
    [p50mnt] = get_values(  # noqa: F821
        'p50mnt')

    # labware and pipette set-up
    tips = [protocol.load_labware(
        'opentrons_96_tiprack_300ul', str(s)) for s in range(5, 11)]
    p50 = protocol.load_instrument('p50_multi', p50mnt, tip_racks=tips)

    trough = protocol.load_labware('nest_12_reservoir_15ml', '1', 'Reservoir')
    beads = trough['A1']
    etoh1 = trough['A2']
    etoh2 = trough['A3']
    etoh3 = trough['A4']
    etoh4 = trough['A5']
    rsb = trough['A6']
    waste1 = trough['A9']
    waste2 = trough['A10']
    waste3 = trough['A11']
    waste4 = trough['A12']

    magdeck = protocol.load_module('magdeck', '4')
    magplate = magdeck.load_labware(
        'biorad_96_wellplate_200ul_pcr', 'Mag Plate')

    plate96 = protocol.load_labware(
        'biorad_96_wellplate_200ul_pcr', '2', '96-well plate')
    plate384 = protocol.load_labware(
        'corning_384_wellplate_112ul_flat', '3', '384-well plate')

    mag_samps = magplate.rows()[0]
    p96_samps = plate96.rows()[0]
    p384_samps = plate384.rows()[0]

    # Transfer 15ul beads from trough
    for mag in mag_samps:
        p50.pick_up_tip()
        p50.mix(5, 30, beads)
        p50.transfer(15, beads, mag, new_tip='never')
        p50.mix(10, 40, mag)
        p50.blow_out(mag.top())
        p50.drop_tip()

    # wait 5 minutes, then use magdeck for 2 minutes
    protocol.delay(minutes=5)
    magdeck.engage()
    protocol.delay(minutes=2)

    # remove supernatant
    for mag in mag_samps:
        p50.pick_up_tip()
        p50.transfer(40, mag, waste1, new_tip='never')
        p50.drop_tip()

    # wash with 200ul EToH two times
    def etoh_wash(e1, e2, w1, w2):
        p50.pick_up_tip()
        for m in mag_samps[:6]:
            p50.transfer(200, e1, m.top(), air_gap=10, new_tip='never')
        for m in mag_samps[6:]:
            p50.transfer(200, e2, m.top(), air_gap=10, new_tip='never')
        protocol.delay(seconds=30)
        p50.flow_rate.aspirate = 12
        for m in mag_samps[:6]:
            if not p50.hw_pipette['has_tip']:
                p50.pick_up_tip()
            p50.transfer(200, m, w1, air_gap=10, new_tip='never')
            p50.drop_tip()
        for m in mag_samps[6:]:
            p50.pick_up_tip()
            p50.transfer(200, m, w2, air_gap=10, new_tip='never')
            p50.drop_tip()
        p50.flow_rate.aspirate = 25

    etoh_wash(etoh1, etoh2, waste1, waste2)
    etoh_wash(etoh3, etoh4, waste3, waste4)

    # air dry for 15 minutes, then remove from magnetic stand
    protocol.delay(minutes=15)
    magdeck.disengage()

    # add 25ul rsb to each well
    for mag in mag_samps:
        p50.pick_up_tip()
        p50.transfer(25, rsb, mag, new_tip='never')
        p50.mix(10, 25, mag)
        p50.blow_out(mag.top())
        p50.drop_tip()

    # incubate for 2 minutes, then engage magdeck for 2 minutes
    protocol.delay(minutes=2)
    magdeck.engage()
    protocol.delay(minutes=2)

    # transfer 4ul supernatant to 384 well plate and 20ul to 96 well plate
    p50.flow_rate.aspirate = 12
    for mag, p96, p384 in zip(mag_samps, p96_samps, p384_samps):
        p50.pick_up_tip()
        p50.aspirate(24, mag)
        p50.dispense(20, p96)
        p50.dispense(4, p384)
        p50.blow_out(p384.top())
        p50.drop_tip()

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
    filename = f"detailed_action_json/19fc32.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)