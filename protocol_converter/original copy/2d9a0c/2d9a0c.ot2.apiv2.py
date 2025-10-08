import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/2d9a0c/2d9a0c.ot2.apiv2.py"

from opentrons import protocol_api


metadata = {
    'protocolName': 'PCR Workflow With Thermocycler',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(protocol):

    [lid_temp, tube_rack, num_samples, num_tipracks,
        p300_mount, p20_mount] = get_values(  # noqa: F821
        "lid_temp", "tube_rack", "num_samples", "num_tipracks",
        "p300_mount", "p20_mount")

    num_samples = int(num_samples)
    if not 1 <= num_samples <= 96:
        raise Exception("Enter a sample number between 1-96")

    # load labware. Set lid temperature
    buff_tuberack = protocol.load_labware(tube_rack, '5')
    thermocyc = protocol.load_module('thermocycler')
    tc_plate = thermocyc.load_labware('thermo_non_skirted_96_plate_300ul')
    plate_B = protocol.load_labware('thermo_non_skirted_96_plate_300ul', '4')
    rack20 = [protocol.load_labware('opentrons_96_tiprack_20ul', slot)
              for slot in [str(tiprack)
              for tiprack in range(1, int(num_tipracks)+1)]]
    rack300 = protocol.load_labware('opentrons_96_tiprack_300ul', '6')
    if thermocyc.lid_position != 'open':
        thermocyc.lid_position == 'open'
    thermocyc.set_lid_temperature(lid_temp)

    # load instruments, tip replace function
    p20 = protocol.load_instrument('p20_single_gen2', p20_mount,
                                   tip_racks=rack20)
    p300 = protocol.load_instrument('p300_single_gen2', p300_mount,
                                    tip_racks=[rack300])

    def pick_up(pip):
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            protocol.pause("Replace all tip racks")
            pip.reset_tipracks()
            pip.pick_up_tip()

    # protocol
    profile = [
        {'temperature': 37, 'hold_time_minutes': 10},
        {'temperature': 55, 'hold_time_minutes': 10},
        {'temperature': 95, 'hold_time_minutes': 1},
        {'temperature': 55, 'hold_time_minutes': 15},
        {'temperature': 37, 'hold_time_minutes': 30},
        {'temperature': 50, 'hold_time_minutes': 10},
        {'temperature': 57, 'hold_time_minutes': 30},
        {'temperature': 37, 'hold_time_minutes': 15},
        {'temperature': 65, 'hold_time_minutes': 15},
        {'temperature': 42, 'hold_time_minutes': 5},
        {'temperature': 37, 'hold_time_minutes': 5},
        {'temperature': 37, 'hold_time_minutes': 30},
        {'temperature': 60, 'hold_time_minutes': 10},
        {'temperature': 45, 'hold_time_minutes': 30},
    ]

    # transfer 20ul buffer to plate
    if num_samples == 96:
        p300.pick_up_tip()
        chunks = [tc_plate.wells()[i:i+8]
                  for i in range(0, len(tc_plate.wells()[:num_samples]), 8)]
        for chunk in chunks:
            p300.distribute(20, buff_tuberack.wells_by_name()['A1'],
                            [well for well in chunk],
                            new_tip='never',
                            blow_out=True,
                            blowout_location='source well')
        p300.drop_tip()

    else:
        p300.pick_up_tip()
        for s, d in zip(plate_B.wells()[:num_samples], tc_plate.wells()):
            p300.transfer(20, s, d, new_tip='never')
        p300.drop_tip()

    # transfer 2ul sample to tc plate. Air gap for small volume
    for s, d in zip(plate_B.wells()[:num_samples], tc_plate.wells()):
        p20.transfer(2, s, d,
                     air_gap=5,
                     blow_out=True,
                     blowout_location='destination well')
    thermocyc.close_lid()

    # run 1st set of steps in profile
    thermocyc.execute_profile(steps=profile[0:2],
                              repetitions=1,
                              block_max_volume=22)
    thermocyc.set_block_temperature(55)

    # profile steps with adding buffer in between each step
    tube_wells = [well for row in buff_tuberack.rows() for well in row][1:]
    profile_step = [[2, 4], [4, 6], [6, 7], [7, 11], [11, 13], [13, 14]]
    block_vol = 22

    for index, (tube, step) in enumerate(zip(tube_wells, profile_step)):
        transfer_vol = 5 if index > 0 else 20
        block_vol += 5 if index > 0 else 20

        thermocyc.open_lid()
        for well in tc_plate.wells()[:num_samples]:
            pick_up(p20)
            p20.aspirate(transfer_vol, tube)
            p20.dispense(transfer_vol, well)
            p20.drop_tip()

        thermocyc.close_lid()
        thermocyc.execute_profile(steps=profile[step[0]: step[1]],
                                  repetitions=1,
                                  block_max_volume=block_vol)
        thermocyc.set_block_temperature(profile[step[1]-1]['temperature'])

    # final transfer of 100ul
    thermocyc.open_lid()
    transfer_vol = 100
    for well in tc_plate.wells()[:num_samples]:
        pick_up(p300)
        p300.aspirate(transfer_vol, buff_tuberack.wells_by_name()['B2'])
        p300.dispense(transfer_vol, well)
        p300.drop_tip()

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
    filename = f"detailed_action_json/2d9a0c.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)