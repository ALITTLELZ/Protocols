import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/08e3eb/08e3eb.ot2.apiv2.py"

metadata = {
    'protocolName': 'Custom Plate Filling',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.5'
}


def run(protocol):
    [start_tip, run_number] = get_values(  # noqa: F821
        'start_tip', 'run_number')

    # load labware and pipettes
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', '10')

    m50 = protocol.load_instrument('p50_multi', 'left')

    reservoir = protocol.load_labware('agilent_48_reservoir_5000ul', '11')

    plates = [
        protocol.load_labware(
            'microamp_96well_200ul',
            str(slot)) for slot in range(1, 10)]

    dest1 = [plate[x] for plate in plates for x in ['A1', 'A5', 'A9']]
    dest2 = [plate[x] for plate in plates for x in ['A2', 'A6', 'A10']]
    dest3 = [plate[x] for plate in plates for x in ['A3', 'A7', 'A11']]
    dest4 = [plate[x] for plate in plates for x in ['A4', 'A8', 'A12']]

    start_tip = int(start_tip)

    destinations = [dest1, dest2, dest3, dest4]
    sources = [reservoir[x] for x in ['A1', 'A2', 'A3', 'A4']]
    tips = [tips300['A'+str(t)] for t in range(start_tip, start_tip+4)]

    for x in range(run_number):
        for tip, src, dest in zip(tips, sources, destinations):
            m50.pick_up_tip(tip)
            m50vol = 0
            for d in dest:
                if m50vol < 10:
                    m50.dispense(m50vol, src)
                    m50.aspirate(50, src)
                    m50vol = 50
                m50.dispense(6, d)
                m50vol -= 6
            m50.dispense(m50vol, src)
            m50.blow_out()
            m50.return_tip() if x == run_number-1 else m50.drop_tip()
        m50.home()
        for i in range(6):
            protocol.set_rail_lights(not protocol.rail_lights_on)
            protocol.delay(seconds=1)
        if x == run_number-1:
            protocol.comment('Protocol complete!')
        else:
            pause_msg = 'Plates filled. Please replace plates and click RESUME'
            protocol.pause(pause_msg)

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
    filename = f"detailed_action_json/08e3eb.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)