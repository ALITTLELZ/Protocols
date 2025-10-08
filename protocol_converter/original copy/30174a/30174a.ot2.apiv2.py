import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/30174a/30174a.ot2.apiv2.py"


metadata = {
    'protocolName': 'DNA dilution using .csv file',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.5'
}

# csv_input = open("example.csv", "r").read()


def run(ctx):

    csv_input = get_values(  # noqa: F821
            'csv_input')

    plate1 = ctx.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt',
        '6',
        label="Plate 1")
    plate2 = ctx.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt',
        '9',
        label="Plate 2")
    te = ctx.load_labware('nest_1_reservoir_195ml', '8').wells()[0]

    p300s_tips = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '7')]
    p20s_tips = [ctx.load_labware('opentrons_96_filtertiprack_20ul', '5')]

    p300s = ctx.load_instrument(
        'p300_single_gen2',
        'right',
        tip_racks=p300s_tips)
    p20s = ctx.load_instrument('p20_single_gen2', 'left', tip_racks=p20s_tips)

    data = [
        [val.strip().upper() for val in line.split(',')]
        for line in csv_input
        if line and line.split(',')[0].strip()][1:]

    dna_transfer = []
    te_transfer = []
    wells = []

    for w, d, t in data:
        dna_transfer.append(float(d))
        te_transfer.append(float(t))
        wells.append(w)

    p300s.pick_up_tip()
    for i, vol in enumerate(te_transfer):
        p300s.transfer(
            vol, te, plate2.wells_by_name()[
                wells[i]], new_tip='never')
    p300s.drop_tip()

    for i, vol in enumerate(dna_transfer):
        p20s.transfer(
            vol, plate1.wells_by_name()[
                wells[i]], plate2.wells_by_name()[
                wells[i]], mix=(
                3, 2))

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
    filename = f"detailed_action_json/30174a.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)