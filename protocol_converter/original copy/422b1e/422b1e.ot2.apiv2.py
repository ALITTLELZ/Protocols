import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/422b1e/422b1e.ot2.apiv2.py"

metadata = {
    'protocolName': 'Titration Procedure',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.2'
}


def run(protocol):
    # load labware and pipettes
    p1000tips = protocol.load_labware('opentrons_96_tiprack_1000ul', '11')
    p1000 = protocol.load_instrument(
        'p1000_single_gen2', 'right', tip_racks=[p1000tips])

    dest_beaker = protocol.load_labware('custom_beaker', '4')
    waste_beaker = protocol.load_labware('custom_beaker', '8')
    tube_rack = protocol.load_labware(
        'opentrons_6_tuberack_falcon_50ml_conical', '9')
    tubes = [t for x in tube_rack.rows() for t in x]

    # create beaker height definitions
    # the number represents mm from defined bottom
    dest_ht = dest_beaker['A1'].bottom(1)
    waste_ht = waste_beaker['A1'].bottom(1)

    wait_time = 5  # this is how long the protocol will delay (min)

    # pick up tip
    p1000.pick_up_tip()  # this will always pick up tip from A1; can be changed

    for tube in tubes:
        for _ in range(2):
            p1000.aspirate(1000, tube)
            p1000.dispense(1000, dest_ht)
        protocol.comment('Delaying %s minutes' % wait_time)
        protocol.delay(minutes=wait_time)
        for _ in range(2):
            p1000.aspirate(1000, dest_ht)
            p1000.dispense(1000, waste_ht)

    p1000.drop_tip()

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
    filename = f"detailed_action_json/422b1e.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)