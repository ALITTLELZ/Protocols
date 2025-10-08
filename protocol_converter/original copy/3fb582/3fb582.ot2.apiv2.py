import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/3fb582/3fb582.ot2.apiv2.py"

metadata = {
    'protocolName': 'PCR setup using a CSV file',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.2'
}

# c = """Reagent,Source Slot,Source Well,Target Slot,Target Well,Volume
# Water,2,A1,9,A1,10
# Primer 1,2,A2,9,A1,5
# PCR Mix,2,A3,9,A1,10
# DNA 1,2,A4,9,A1,1
# """


def run(ctx):

    c = get_values(  # noqa: F821
            'csv_input')[0]

    csv_data = [r.split(',') for r in c.strip().splitlines() if r][1:]
    steps = {"Water": [], "PCR": [], "Primer": [], "DNA": []}
    for line in csv_data:
        for k, v in steps.items():
            if k in line[0]:
                steps[k].append(line)

    tube_racks = [
        ctx.load_labware(
            "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap",
            x) for x in [
            "2",
            "5",
            "8",
            "11"]]
    tube_rack_slot = {
        str(i): tube_rack for i,
        tube_rack in zip(range(2, 12, 3), tube_racks)}

    p20s = ctx.load_instrument(
        "p20_single_gen2",
        "right",
        tip_racks=[
            ctx.load_labware(
                "opentrons_96_filtertiprack_20ul",
                x) for x in [
                "1",
                "4",
                "7",
                "10",
                "3"]])

    destination_plate_96 = ctx.load_labware(
        "nest_96_wellplate_100ul_pcr_full_skirt", "6")
    destination_plate_384 = ctx.load_labware(
        "corning_384_wellplate_112ul_flat", "9")
    destination_slot = {"6": destination_plate_96, "9": destination_plate_384}

    p20s.pick_up_tip()
    for r, ss, source_well, ts, target_well, volume in steps["Water"]:
        p20s.transfer(
            float(volume),
            tube_rack_slot[ss].wells_by_name()[source_well],
            destination_slot[ts].wells_by_name()[target_well],
            new_tip='never')
    p20s.drop_tip()

    p20s.pick_up_tip()
    for r, ss, source_well, ts, target_well, volume in steps["PCR"]:
        p20s.transfer(
            float(volume),
            tube_rack_slot[ss].wells_by_name()[source_well],
            destination_slot[ts].wells_by_name()[target_well].top(),
            new_tip='never')
    p20s.drop_tip()

    for step in [steps["Primer"], steps["DNA"]]:
        for r, ss, source_well, ts, target_well, volume in step:
            p20s.transfer(
                float(volume),
                tube_rack_slot[ss].wells_by_name()[source_well],
                destination_slot[ts].wells_by_name()[target_well],
                new_tip='always')

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
    filename = f"detailed_action_json/3fb582.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)