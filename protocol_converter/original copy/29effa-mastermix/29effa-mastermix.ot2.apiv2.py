import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/29effa-mastermix/29effa-mastermix.ot2.apiv2.py"

metadata = {
    'protocolName': 'Lyra Direct Covid-19 Mastermix Distribution',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(protocol):
    [p20mnt, num_wells] = get_values(  # noqa: F821
     'p20mnt', 'num_wells')

    # load labware and pipette
    tempdeck = protocol.load_module('temperature module gen2', '3')
    plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul')
    tempdeck.set_temperature(3)

    tips = [protocol.load_labware('opentrons_96_filtertiprack_20ul', '2')]
    tuberack = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '6')
    p20 = protocol.load_instrument('p20_single_gen2', p20mnt, tip_racks=tips)

    # variables
    wells = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'A2', 'B2', 'C2',
             'D2', 'E2', 'F2', 'G2', 'H2', 'A3', 'B3', 'C3', 'D3', 'E3', 'F3',
             'G3', 'H3', 'A4', 'B4', 'C4', 'D4', 'E4', 'F4', 'G4', 'H4', 'A5',
             'B5', 'C5', 'D5', 'E5', 'F5', 'G5', 'H5', 'A6', 'B6', 'C6', 'D6',
             'E6', 'F6', 'G6', 'H6', 'A7', 'B7', 'C7', 'D7', 'E7', 'F7', 'G7',
             'H7', 'A8', 'B8', 'C8', 'D8', 'E8', 'F8', 'G8', 'H8', 'A9', 'B9',
             'C9', 'D9', 'E9', 'F9', 'G9', 'H9', 'A10', 'B10', 'C10', 'D10',
             'E10', 'F10', 'G10', 'H10', 'A11', 'B11', 'C11', 'D11', 'E11',
             'F11', 'G11', 'H11', 'A12', 'B12', 'C12', 'D12', 'E12', 'F12',
             'G12', 'H12'][:num_wells]

    mastermix = tuberack['D1']

    # transfer to wells
    p20.pick_up_tip()

    for well in wells:
        p20.aspirate(15, mastermix)
        p20.dispense(15, plate[well])
        p20.blow_out()

    p20.drop_tip()

    protocol.comment('Protocol Complete!')

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
    filename = f"detailed_action_json/29effa-mastermix.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)