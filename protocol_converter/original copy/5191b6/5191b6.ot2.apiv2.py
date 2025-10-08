import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/5191b6/5191b6.ot2.apiv2.py"

metadata = {
    'protocolName': 'High-Throughput Synthesis',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.8'
}


def run(protocol):

    [p1000_tips, p300_tips, p1000_mount, p300_mount,
     vial_map, htp_csv, asp_height, disp_height, p1000_tiprack_slot,
     p300_tiprack_slot] = get_values(  # noqa: F821
        "p1000_tips", "p300_tips", "p1000_mount", "p300_mount",
        "vial_map", "htp_csv", "asp_height", "disp_height",
        "p1000_tiprack_slot", "p300_tiprack_slot")

    # Load Tip Racks
    p1000_tiprack = protocol.load_labware(p1000_tips, p1000_tiprack_slot)
    p300_tiprack = protocol.load_labware(p300_tips, p300_tiprack_slot)

    # Load Pipettes
    p1000 = protocol.load_instrument('p1000_single_gen2',
                                     p1000_mount, tip_racks=[p1000_tiprack])
    p300 = protocol.load_instrument('p300_single_gen2',
                                    p300_mount, tip_racks=[p300_tiprack])

    # Load Reaction Vessel Labware
    vial_info = [[val.strip() for val in line.split(',')]
                 for line in vial_map.splitlines()
                 if line.split(',')[0].strip()][1:]

    for line in vial_info:
        s_lw, s_slot = line[1:3]
        for slot, lw in zip([s_slot], [s_lw]):
            if int(slot) not in protocol.loaded_labwares:
                protocol.load_labware(lw.lower(), slot)

    # Get all sample reaction vials
    sample_tubes = []
    for line in vial_info:
        lw, slot, well = line[1:4]
        sample_tubes.append(protocol.loaded_labwares[
                            int(slot)].wells_by_name()[well])

    # Load Reservoir Labware
    htp_labware = [[val.strip().lower() for val in line.split(',')]
                   for line in htp_csv.splitlines()
                   if line.split(',')[0].strip()][1:4]

    # Get reservoir positions
    reservoirs = []
    for lw, slot, well in zip(htp_labware[0][1:], htp_labware[1][1:],
                              htp_labware[2][1:]):
        if lw:
            if int(slot) not in protocol.loaded_labwares:
                protocol.load_labware(lw.lower(), slot)
            reservoirs.append(protocol.loaded_labwares[
                            int(slot)].wells_by_name()[well.upper()])

    # Parse High-Throughput CSV
    htp_info = [[val.strip().lower() for val in line.split(',')]
                for line in htp_csv.splitlines()
                if line.split(',')[0].strip()][5:]

    # Get all dispense volumes in each row
    dispense_vols = [i[1:-1] for i in htp_info]

    # Group dispense volumes per column
    # Each list contains volumes per reservoir
    dispense_vols_serialized = [[vol[i] for vol in
                                dispense_vols] for i in range(len(
                                    dispense_vols[0]))]

    # Creates data structure with correct reservoir,
    # wells, and corresponding volumes
    raw_samples_data = {i: {well: vol for well, vol in
                        enumerate(volumes) if vol != ''}
                        for i, volumes in enumerate(dispense_vols_serialized)}

    # Remove columns with empty values
    samples_data = {i: v for i, v in raw_samples_data.items() if v}

    for res_well, res in enumerate(samples_data):
        for i, vol in enumerate(samples_data[res]):
            well, volume = i, int(samples_data[res][i])
            pip = p300 if volume < 300 else p1000
            if not pip.has_tip:
                pip.pick_up_tip()
            pip.well_bottom_clearance.aspirate = float(asp_height)
            pip.well_bottom_clearance.dispense = float(disp_height)
            pip.transfer(volume, reservoirs[res_well],
                         sample_tubes[well], new_tip='never')
        for pipette in [p300, p1000]:
            if pipette.has_tip:
                pipette.drop_tip()

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
    filename = f"detailed_action_json/5191b6.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)