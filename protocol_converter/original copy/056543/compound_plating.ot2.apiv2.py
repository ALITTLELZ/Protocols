import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/056543/compound_plating.ot2.apiv2.py"

from opentrons.types import Point


metadata = {
    'protocolName': 'Compound Plating',
    'author': 'Nick Diehl <ndiehl@opentrons.com>',
    'apiLevel': '2.13'
}


def run(ctx):

    [mount_p20, file_input] = get_values(  # noqa: F821
        'mount_p20', 'file_input')

    #  labware
    plates96 = [
        ctx.load_labware('biorad_96_wellplate_200ul_pcr', str(slot))
        for slot in range(1, 8)]
    ctx.load_labware('corning_384_wellplate_112ul_flat', '8')
    ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '9')
    tipracks20 = [
        ctx.load_labware('opentrons_96_tiprack_20ul', slot)
        for slot in ['10', '11']]

    # pipettes
    p20 = ctx.load_instrument('p20_single_gen2', mount_p20,
                              tip_racks=tipracks20)

    # load data
    data = [
        [val.strip() for val in line.split(',') if val]
        for line in file_input.splitlines()[1:]]
    all_destinations = [well for plate in plates96 for well in plate.wells()]

    def wick(well, pip=p20, side=1):
        pip.move_to(well.bottom().move(Point(x=side*well.diameter/2*0.8, z=3)))

    def slow_withdraw(well, pip=p20):
        ctx.max_speeds['A'] = 25
        ctx.max_speeds['Z'] = 25
        pip.move_to(well.top())
        del ctx.max_speeds['A']
        del ctx.max_speeds['Z']

    def slow_descent(well, h=0.5, pip=p20):
        pip.move_to(well.top())
        ctx.max_speeds['A'] = 25
        ctx.max_speeds['Z'] = 25
        pip.move_to(well.bottom(h))
        del ctx.max_speeds['A']
        del ctx.max_speeds['Z']

    def check_dests(dest):
        nonlocal all_destinations
        if dest in all_destinations:
            all_destinations.remove(dest)
            return False
        else:
            return True

    def create_chunks(info_list):
        max_vol = p20.tip_racks[0].wells()[0].max_volume
        chunks = []
        running_chunk = []
        for dict in info_list:
            if sum(
                    [dict['volume'] for dict in running_chunk])  + dict['volume'] > max_vol:
                chunks.append(running_chunk)
                running_chunk = [dict]
            else:
                running_chunk.append(dict)
        # append final running chunk if not empty
        if len(running_chunk) > 0:
            chunks.append(running_chunk)
        return chunks

    transfer_data = [{}]

    for line in data:
        _, s_slot, s_well, _, d_slot, d_well, vol = line[:7]
        source = ctx.loaded_labwares[int(s_slot)].wells_by_name()[s_well]
        dest = ctx.loaded_labwares[int(d_slot)].wells_by_name()[d_well]
        vol = float(vol)
        refill = check_dests(dest)
        if refill:
            transfer_data.append({})
            all_destinations = [
                well for plate in plates96 for well in plate.wells()]

        if source not in transfer_data[-1]:
            transfer_data[-1][source] = []
        transfer_data[-1][source].append(
            {'destination': dest, 'volume': vol})

    for i, refill in enumerate(transfer_data):
        for source, transfer_info in refill.items():
            # create chunks
            chunks = create_chunks(transfer_info)
            p20.pick_up_tip()
            for chunk in chunks:
                p20.aspirate(sum([dict['volume'] for dict in chunk]), source)
                slow_withdraw(source)
                for dest in [dict['destination'] for dict in chunk]:
                    slow_descent(dest, 0.5)
                    p20.dispense(vol, dest.bottom(0.5))
                    wick(dest)
                    slow_withdraw(dest)
            p20.drop_tip()

        if i < len(transfer_data) - 1:
            ctx.pause('\n\n\n\nReplace 96-well plates and tip racks. Insert  two new tip racks in positions 10 and 11, remove all 96-well plates from \
positions 1-7, and insert five new 96-well plates in positions 1-5.\n\n\n\n')
            p20.reset_tipracks()

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
    filename = f"detailed_action_json/056543.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)