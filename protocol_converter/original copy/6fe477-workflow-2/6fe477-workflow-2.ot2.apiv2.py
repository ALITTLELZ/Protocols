import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/6fe477-workflow-2/6fe477-workflow-2.ot2.apiv2.py"

metadata = {
    'protocolName': 'Nucleic Acid Purification - Workflow 2',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.8'
}


def run(protocol):

    [total_samples, pool_size, p300_mount,
     p1000_mount] = get_values(  # noqa: F821
     "total_samples", "pool_size", "p300_mount", "p1000_mount")

    pool_size = int(pool_size)
    total_samples = int(total_samples)

    # Load Tip Racks
    tiprack_200ul_filter = protocol.load_labware(
        'opentrons_96_filtertiprack_200ul', 5)
    tiprack_1000ul = protocol.load_labware('opentrons_96_tiprack_1000ul', 6)

    # Load Pipettes
    p300 = protocol.load_instrument('p300_single_gen2', p300_mount,
                                    tip_racks=[tiprack_200ul_filter])
    p1000 = protocol.load_instrument('p1000_single_gen2', p1000_mount,
                                     tip_racks=[tiprack_1000ul])

    # 1.5mL Tube Rack
    sample_tube_rack = protocol.load_labware('vwr_24_tuberack_1.5ml', 2)

    # Lysis Buffer Reservoir
    buffer_reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3)['A1']

    # Load 7 Tube Racks with Samples in 30 mL Tubes
    tube_racks = []
    for slot in range(1, 12):
        if slot not in protocol.loaded_labwares:
            tube_racks.append(protocol.load_labware('caplugs_6_tuberack_30ml',
                                                    slot))

    all_wells = [well for tube in tube_racks for well
                 in tube.wells()][:total_samples]
    sample_wells = [all_wells[i:i + pool_size] for i in range(0,
                    len(all_wells), pool_size)]
    dest_wells = sample_tube_rack.wells()[0:len(sample_wells)]

    # Transfer 40 uL samples into DWP
    protocol.comment(f'Adding 40 uL samples with a pool size of {pool_size}')
    p300.flow_rate.aspirate = 30
    for s, d in zip(sample_wells, dest_wells):
        p300.transfer(40, s, d, new_tip='always')

    # Transfer 560 uL of Lysis Buffer into samples in tube rack
    protocol.comment('Adding 560 uL of Lysis buffer into 1.5mL tubes on the  tube rack')
    p1000.transfer(560, buffer_reservoir, dest_wells, new_tip='always')

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
    filename = f"detailed_action_json/6fe477-workflow-2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)