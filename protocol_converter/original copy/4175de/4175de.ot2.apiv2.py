import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/4175de/4175de.ot2.apiv2.py"

metadata = {
    'protocolName': 'Cherrypicking PCR/qPCR prep',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(protocol):
    [transfer_csv, total_samples, p20_mount, pcr_labware,
        mastermix_vol] = get_values(  # noqa: F821
        "transfer_csv", "total_samples", "p20_mount", "pcr_labware",
        "mastermix_vol")

    # Load Tip Racks
    tipracks = [protocol.load_labware('opentrons_96_filtertiprack_20ul', slot)
                for slot in ['1', '4', '7']]

    # Load Module
    temp_mod = protocol.load_module('temperature module gen2', 3)
    pcr_plate = temp_mod.load_labware(pcr_labware)
    mastermix = protocol.load_labware(
        'opentrons_24_tuberack_generic_2ml_screwcap', 2)['A6']

    # Load labware via CSV
    transfer_info = [[val.strip().lower() for val in line.split(',')]
                     for line in transfer_csv.splitlines()
                     if line.split(',')[0].strip()][1:]
    for line in transfer_info:
        s_lw, s_slot, d_lw, d_slot = line[:2] + line[4:6]
        for slot, lw in zip([s_slot, d_slot], [s_lw, d_lw]):
            if not int(slot) in protocol.loaded_labwares:
                protocol.load_labware(lw.lower(), slot)

    def parse_well(well):
        letter = well[0]
        number = well[1:]
        return letter.upper() + str(int(number))

    # Load Pipette
    p20 = protocol.load_instrument('p20_single_gen2', p20_mount,
                                   tip_racks=tipracks)

    # Activate temperature module and set temperature to 4 Celsius
    # Pauses protocol until desired temperature is reached
    protocol.comment("Setting temperature to 4C on the Temperature Module")
    temp_mod.set_temperature(4)

    # Transfer Master Mix to Variable # of wells on PCR Plate sequentially
    protocol.comment("Transferring master mix...")
    mastermix_wells = [well for row in pcr_plate.rows()
                       for well in row][:int(total_samples)]

    p20.pick_up_tip()
    for well in mastermix_wells:
        p20.transfer(float(mastermix_vol), mastermix, well,
                     new_tip='never')
    p20.drop_tip()

    # Transfer DNA from source wells to PCR Plate
    protocol.comment("Transferring DNA samples from source to destination")
    for line in transfer_info:
        _, s_slot, s_well, h, _, d_slot, d_well, vol = line[:8]
        source = protocol.loaded_labwares[int(s_slot)].wells_by_name()[
            parse_well(s_well)].bottom(float(h))
        dest = protocol.loaded_labwares[int(d_slot)].wells_by_name()[
            parse_well(d_well)]
        p20.transfer(float(vol), source, dest, new_tip='always')

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
    filename = f"detailed_action_json/4175de.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)