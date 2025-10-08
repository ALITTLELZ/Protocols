import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7fc7b1/cherrypick_pcr_prep.ot2.apiv2.py"

metadata = {
    'protocolName': 'PCR Preparation Cherrypicking',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.5'
}


def run(ctx):

    [mm_lw, mm_slot, mm_transfer_vol, mm_source_vol, mastermix_start_col,
     dna_vol, transfer_scheme, transfer_csv,
     p20_mount] = get_values(  # noqa: F821
        'mm_lw', 'mm_slot', 'mm_transfer_vol', 'mm_source_vol',
        'mastermix_start_col', 'dna_vol', 'transfer_scheme', 'transfer_csv',
        'p20_mount')

    # load labware
    mm = ctx.load_labware(mm_lw, mm_slot, 'mastermix container').rows()[0][
        mastermix_start_col-1:]

    transfer_info = [[val.strip().lower() for val in line.split(',')]
                     for line in transfer_csv.splitlines()
                     if line.split(',')[0].strip()][1:]

    def parse_well(well):
        return well[0].upper() + str(int(well[1:]))

    # parse csv file
    lw_map = {
        '96': 'greinerbioone_96_wellplate_200ul',
        '384': 'sarstedt_384_wellplate_40ul'
    }
    transfer_dict = {}
    for line in transfer_info:
        s_slot, s_well, d_lw, d_slot, d_well = line[:5]
        if int(s_slot) not in ctx.loaded_labwares:
            ctx.load_labware(lw_map['96'], s_slot)
        if int(d_slot) not in ctx.loaded_labwares:
            ctx.load_labware(lw_map[d_lw], d_slot)
        source = ctx.loaded_labwares[int(s_slot)].wells_by_name()[
            parse_well(s_well)]
        dest = ctx.loaded_labwares[int(d_slot)].wells_by_name()[
            parse_well(d_well)]
        if source not in transfer_dict:
            transfer_dict[source] = [dest]
        else:
            transfer_dict[source].append(dest)

    # load tipracks in remaining slots
    tipracks = []
    for slot in range(1, 13):
        if slot not in ctx.loaded_labwares:
            tipracks.append(
                ctx.load_labware('opentrons_96_tiprack_20ul', str(slot)))

    # load pipette
    m20 = ctx.load_instrument('p20_multi_gen2', p20_mount, tip_racks=tipracks)

    tip_count = 0
    tip_max = len(tipracks*96)

    def pick_up():
        nonlocal tip_count
        if tip_count == tip_max:
            ctx.pause('Please refill tipracks before resuming.')
            m20.reset_tipracks()
            tip_count = 0
        m20.pick_up_tip()
        tip_count += 1

    # transfer mastermix
    all_dests = [d for dest_set in transfer_dict.values() for d in dest_set]
    pick_up()
    dests_per_col = mm_source_vol//mm_transfer_vol
    for i, d in enumerate(all_dests):
        m20.aspirate(2, mm[i//dests_per_col].top())
        m20.aspirate(mm_transfer_vol, mm[i//dests_per_col])
        m20.dispense(2+mm_transfer_vol, d)
    m20.drop_tip()

    # transfer sample
    for source, dests in transfer_dict.items():
        pick_up()
        if transfer_scheme == 'single':
            for d in dests:
                m20.aspirate(2, source.top())
                m20.aspirate(dna_vol, source)
                m20.dispense(2+dna_vol, d.bottom(1))
        else:
            m20.distribute(dna_vol, source, [d.bottom(1) for d in dests],
                           air_gap=2, new_tip='never')
        m20.drop_tip()

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
    filename = f"detailed_action_json/7fc7b1.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)