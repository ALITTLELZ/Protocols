import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0f7910/0f7910.ot2.apiv2.py"

from opentrons import protocol_api


metadata = {
    'protocolName': 'Plate Filling with CSV Import',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [csv_samp,
     source_format,
     dest_format,
     starting_tip,
     p300_mount,
     p20_mount] = get_values(  # noqa: F821
        "csv_samp",
        "source_format",
        "dest_format",
        "starting_tip",
        "p300_mount",
        "p20_mount")

    # mapping
    csv_lines = [[val.strip() for val in line.split(',')]
                 for line in csv_samp.splitlines()
                 if line.split(',')[0].strip()][1:]

    unique_list = []
    for row in csv_lines:
        source_plate_slot = int(row[1])
        if source_plate_slot not in unique_list:
            unique_list.append(source_plate_slot)

    starting_tip -= starting_tip

    # labware
    source_plates = [ctx.load_labware(
                     'corning_96_wellplate_360ul_flat'
                     if source_format == "96"
                     else "corning_384_wellplate_112ul_flat", slot)
                     for slot in unique_list]
    source_plates = source_plates

    dest_plate = ctx.load_labware(
                     'corning_96_wellplate_360ul_flat'
                     if dest_format == "96"
                     else "corning_384_wellplate_112ul_flat", 2
                     if dest_format == "384"
                     else 1)
    transfer_vol = float(csv_lines[0][5])

    if transfer_vol > 20:
        tips300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
                   for slot in [10]]
    else:
        tips20 = [ctx.load_labware('opentrons_96_tiprack_20ul', slot)
                  for slot in [11]]

    # pipettes
    if transfer_vol > 20:
        p300 = ctx.load_instrument('p300_single_gen2', p300_mount,
                                   tip_racks=tips300)

    else:
        p20 = ctx.load_instrument('p20_single_gen2', p20_mount,
                                  tip_racks=tips20)

    def pick_up(pip):
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            ctx.pause("Replace empty tip racks.")
            pip.reset_tipracks()
            pick_up(pip)

    # protocol

    pip = p20 if transfer_vol <= 20 else p300
    pip.flow_rate.aspirate = 1
    pip.flow_rate.dispense = 2

    if transfer_vol > 20:
        pip.starting_tip = tips300[0].wells()[starting_tip]
    else:
        pip.starting_tip = tips20[0].wells()[starting_tip]

    for row in csv_lines:
        source_plate_slot = int(row[1])
        source_well_name = row[2]
        dest_well_name = row[4]

        source = ctx.loaded_labwares[source_plate_slot].wells_by_name()[source_well_name]  # noqa: E501
        dest = dest_plate.wells_by_name()[dest_well_name]

        pick_up(pip)
        pip.mix(1, transfer_vol, source.bottom(z=0.2))
        pip.aspirate(transfer_vol, source.bottom(z=0.2))
        pip.dispense(transfer_vol, dest)
        pip.move_to(dest.top(z=-3))
        ctx.delay(seconds=1)
        pip.blow_out()
        pip.drop_tip()
        ctx.comment('\n\n')

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
    filename = f"detailed_action_json/0f7910.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)