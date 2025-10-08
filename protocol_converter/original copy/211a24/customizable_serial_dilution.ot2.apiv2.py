import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/211a24/customizable_serial_dilution.ot2.apiv2.py"

metadata = {
    'protocolName': 'Customizable Serial Dilution',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.9'
    }


def run(ctx):
    [pipette_mount, diluent_csv, sample_csv, serial_csv,
     load_csv] = get_values(  # noqa: F821
     'pipette_mount', 'diluent_csv', 'sample_csv', 'serial_csv', 'load_csv')

    # labware
    dilution_plates = [
        ctx.load_labware(
            'nest_96_wellplate_100ul_pcr_full_skirt', slot,
            'dilution plate ' + str(i+1))
        for i, slot in enumerate(['1', '3', '4', '6'])]
    sample_plate = ctx.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt', '2')
    gyros_plate = ctx.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt', '5', 'GyrosPCRPlate')
    diluent = ctx.load_labware(
        'nest_1_reservoir_195ml', '8', 'diluent')
    tiprack = [
        ctx.load_labware('opentrons_96_tiprack_300ul', slot)
        for slot in ['7', '9', '10', '11']]

    p300 = ctx.load_instrument('p300_single_gen2', 'left', tip_racks=tiprack)

    labware_map = {
        'SamplePlate1': sample_plate,
        'GyrosDiluent': diluent,
        'GyrosPCRPlate': gyros_plate,
        'PCRPlate[001]': dilution_plates[0],
        'PCRPlate[002]': dilution_plates[1],
        'PCRPlate[003]': dilution_plates[2],
        'PCRPlate[004]': dilution_plates[3],
    }
    action_map = {
        'A': p300.aspirate,
        'D': p300.dispense,
        'W': p300.drop_tip
    }

    def csv_action(input_csv, mix=False):
        info = [
            line for line in input_csv.splitlines() if line]
        for line in info:
            vals = line.split(';')
            action = vals[0]
            if action == 'W':
                action_map[action]()
            else:
                labware = labware_map[vals[1]]
                well = labware.wells_by_name()[vals[4]]
                volume = float(vals[6])
                if not p300.has_tip:
                    p300.pick_up_tip()
                action_map[action](volume, well)
                if action == 'D' and mix:
                    p300.mix(10, 100, well)

    # diluent addition
    csv_action(diluent_csv)

    # samples
    csv_action(sample_csv)

    # serial dilution
    csv_action(serial_csv, mix=True)

    # load plate
    csv_action(load_csv)

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
    filename = f"detailed_action_json/211a24.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)