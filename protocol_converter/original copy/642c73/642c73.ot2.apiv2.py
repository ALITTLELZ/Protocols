import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/642c73/642c73.ot2.apiv2.py"

metadata = {
    'protocolName': 'PCR Prep - Plate Filling',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(protocol):
    [numSamps] = get_values(  # noqa: F821
     'numSamps')

    # load labware and pipette
    tips = [protocol.load_labware('opentrons_96_filtertiprack_20ul', '6')]
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=tips)

    destPlate = protocol.load_labware('biorad_96_wellplate_200ul_pcr', '2')
    destWells = [
        well for row in destPlate.rows() for well in row][:numSamps+1]

    tuberacks = [
        protocol.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
            s) for s in [1, 4, 7, 10, 3]
            ]
    mm = tuberacks[-1].wells()[0]
    water = tuberacks[-1].wells()[-1]

    samples = []
    for rack in tuberacks[:4]:
        for row in rack.rows():
            for well in row:
                samples.append(well)

    # Transfer Master Mix
    protocol.comment('Transferring 20uL of Master Mix to all wells...\n')

    p20.pick_up_tip()

    for well in destWells:
        p20.aspirate(20, mm)
        p20.dispense(20, well)

    # Transfer water to last well
    protocol.comment('Transferring Water (control) to last well...\n')

    p20.aspirate(5, water)
    p20.dispense(5, destWells[-1])
    p20.mix(2, 20)

    p20.drop_tip()

    # Transfer samples
    protocol.comment('Transferring 5uL of Sample to corresponding wells...\n')
    for src, dest in zip(samples[:numSamps], destWells):
        p20.pick_up_tip()
        p20.aspirate(5, src)
        p20.dispense(5, dest)
        p20.mix(2, 20)
        p20.drop_tip()

    protocol.comment('\nProtocol complete!')

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
    filename = f"detailed_action_json/642c73.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)