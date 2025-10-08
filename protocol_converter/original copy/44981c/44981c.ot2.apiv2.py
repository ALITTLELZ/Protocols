import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/44981c/44981c.ot2.apiv2.py"

from opentrons import protocol_api

metadata = {
    'protocolName': 'CSV Cherrypicking APIv2',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.8'
}


def run(protocol):
    [transfer_csv, src_labware, dest_labware,
     pipettes, tiptype] = get_values(  # noqa: F821
     'transfer_csv', 'src_labware', 'dest_labware', 'pipettes', 'tiptype')

    # convert CSV/multi-line string to list
    transfer_info = [
        line.split(',')
        for line in transfer_csv.splitlines() if line
    ][1:]
    source_plate_slots = []
    source_wells = []
    target_plate_slots = []
    target_wells = []
    volumes = []
    mix_vols = []
    mix_cycles = []

    # parse for transfer information
    for line in transfer_info:
        source_plate_slots.append(line[0].strip())
        source_wells.append(line[1].strip())
        volumes.append(float(line[2].strip()))
        target_plate_slots.append(line[3].strip())
        target_wells.append(line[4].strip())
        mix_vols.append(float(line[5].strip()))
        mix_cycles.append(int(line[6].strip()))

    # create dictionary based on slots found and labware
    src_slots = list(set(source_plate_slots))
    sources = {}
    for s in src_slots:
        sources[s] = protocol.load_labware(src_labware, s)
    dest_slots = list(set(target_plate_slots))
    targets = {}
    for s in dest_slots:
        targets[s] = protocol.load_labware(dest_labware, s)

    # create tip racks and pipettes based on variables
    sp_name, bp_name, sp_tip, bp_tip = pipettes.split(' ')
    if sp_tip == bp_tip:
        sp_tips = [
            protocol.load_labware(
                tiptype+sp_tip, str(s)) for s in range(7, 12)]
        bp_tips = sp_tips
    else:
        sp_tips = [
            protocol.load_labware(tiptype+sp_tip, str(s)) for s in [7, 8, 9]]
        bp_tips = [
            protocol.load_labware(tiptype+bp_tip, str(s)) for s in [10, 11]]

    small_pip = protocol.load_instrument(sp_name, 'right', tip_racks=sp_tips)
    big_pip = protocol.load_instrument(bp_name, 'left', tip_racks=bp_tips)

    def pick_up(pip):
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            protocol.pause("Replace the tips")
            pip.reset_tipracks()
            pip.pick_up_tip()

    # perform transfers
    for s_slot, s_well, t_slot, t_well, vol, mix_vol, mix_n in zip(
            source_plate_slots,
            source_wells,
            target_plate_slots,
            target_wells,
            volumes,
            mix_vols,
            mix_cycles):

        if vol > 0:
            pip = small_pip if vol <= small_pip.max_volume else big_pip

            pick_up(pip)

            pip.transfer(
                vol,
                sources[s_slot][s_well],
                targets[t_slot][t_well],
                blow_out=True,
                new_tip='never'
            )
            if mix_vol > pip.max_volume:
                mix_vol = pip.max_volume
            pip.mix(mix_n, mix_vol)
            pip.blow_out()
            pip.drop_tip()

    protocol.comment('Protocol complete!')

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
    filename = f"detailed_action_json/44981c.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)