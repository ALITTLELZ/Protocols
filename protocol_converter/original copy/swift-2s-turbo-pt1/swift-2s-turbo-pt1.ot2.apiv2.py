import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/swift-2s-turbo-pt1/swift-2s-turbo-pt1.ot2.apiv2.py"

import os
import csv

metadata = {
    'protocolName': 'Swift 2S Turbo DNA Library Kit Protocol: Part 1/3 -  Enzymatic Prep & Ligation',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.10'
}


def run(protocol):
    [pip_tip, samps] = get_values(  # noqa: F821
     'pip_tip', 'samps')

    pip_type, tip_name = pip_tip.split()

    # Labware Setup
    small_tips = protocol.load_labware(tip_name, '5')

    small_pip = protocol.load_instrument(
        pip_type, 'left')

    tempdeck = protocol.load_module('Temperature Module', '3')

    cool_reagents = tempdeck.load_labware(
        'opentrons_24_aluminumblock_generic_2ml_screwcap',
        'Opentrons 24-Well Aluminum Block')

    reaction_plate = protocol.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul', '1')

    # Tip tracking between runs
    if not protocol.is_simulating():
        file_path = '/data/csv/tiptracking.csv'
        file_dir = os.path.dirname(file_path)
        # check for file directory
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        # check for file; if not there, create initial tip count tracking
        if not os.path.isfile(file_path):
            with open(file_path, 'w') as outfile:
                outfile.write("0, 0\n")

    tip_count_list = []
    if protocol.is_simulating():
        tip_count_list = [0, 0]
    else:
        with open(file_path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            tip_count_list = next(csv_reader)

    spip_count = int(tip_count_list[0])
    bpip_count = int(tip_count_list[1])

    # Reagent Setup
    enzymatic_prep_mm = cool_reagents.wells_by_name()['A1']
    ligation_mm = cool_reagents.wells_by_name()['A2']

    # Destination of input DNA samples and samples on the magnetic module
    enzymatic_prep_samples = reaction_plate.columns()[0]
    samps = int(samps)
    if samps > 8:
        enzymatic_prep_samples += reaction_plate.columns()[1]
        if samps > 16:
            enzymatic_prep_samples += reaction_plate.columns()[2]

    # Actively cool the samples and enzymes
    tempdeck.set_temperature(4)

    # Make sure to vortex mastermix right before the run
    # Custom transfer function for accounting for various volumes

    def small_pick_up():
        nonlocal spip_count

        if spip_count == 96:
            small_pip.home()
            protocol.pause('Out of tips. Please replace tips in slot 5 and  click RESUME.')
            small_tips.reset()

        small_pip.pick_up_tip(small_tips.wells()[spip_count])

        spip_count += 1

    def vol_trans(vol, src, dest):
        if pip_type[1:3] == '50':
            if not small_pip.hw_pipette['has_tip']:
                small_pick_up()
            small_pip.transfer(vol, src, dest, new_tip='never')
        else:
            if tip_name[-4:-2] == '20':
                if vol < 20:
                    small_pick_up()
                    small_pip.transfer(vol, src, dest, new_tip='never')
                else:
                    while vol >= 15:
                        if not small_pip.hw_pipette['has_tip']:
                            small_pick_up()
                        small_pip.transfer(15, src, dest, new_tip='never')
                        vol -= 15
                        if vol >= 15:
                            small_pip.drop_tip()
            else:
                while vol > 8:
                    if not small_pip.hw_pipette['has_tip']:
                        small_pick_up()
                    small_pip.transfer(8, src, dest, new_tip='never')
                    small_pip.drop_tip()
                    vol -= 8
                small_pick_up()
                small_pip.transfer(vol, src, dest, new_tip='never')

    # if using the P20, change the aspirate/dispense/blow out rates
    if pip_type == 'p20_single_gen2':
        small_pip.flow_rate.aspirate = 25
        small_pip.flow_rate.dispense = 50
        small_pip.flow_rate.blow_out = 1000

    # Dispense Enzymatic Prep Master Mix to the samples
    for well in enzymatic_prep_samples:
        vol_trans(14, enzymatic_prep_mm.bottom(0.2), well.top(-12))
        small_pip.blow_out()
        small_pip.mix(2, small_pip.max_volume/2, well.top(-13.5))
        small_pip.move_to(well.top(-12))
        protocol.delay(seconds=0.5)
        small_pip.blow_out()
        small_pip.drop_tip()

    # Run Enzymatic Prep Profile
    protocol.pause('Enzymatic prep complete. Please place sample plate in  thermocycler and run program according to Swift 2S Turbo manual. When \
    complete, return samples to OT-2 deck for ligation prep and click RESUME.')

    # Transfer Ligation Master Mix to the samples

    small_pick_up()
    small_pip.mix(10, small_pip.max_volume/2, ligation_mm)
    small_pip.blow_out(ligation_mm.top())

    for well in enzymatic_prep_samples:
        vol_trans(30, ligation_mm, well.top(-7))
        small_pip.blow_out()
        small_pip.mix(2, small_pip.max_volume/2, well.top(-13.5))
        small_pip.blow_out(well.top(-7))
        small_pip.drop_tip()

    protocol.comment("Add samples to the thermocycler for ligation.  Temp deck will remain on at 4C")

    # write updated tipcount to CSV
    new_tip_count = str(spip_count)+", "+str(bpip_count)+"\n"
    if not protocol.is_simulating():
        with open(file_path, 'w') as outfile:
            outfile.write(new_tip_count)

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
    filename = f"detailed_action_json/swift-2s-turbo-pt1.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)