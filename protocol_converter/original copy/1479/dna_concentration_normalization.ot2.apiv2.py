import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/1479/dna_concentration_normalization.ot2.apiv2.py"

metadata = {
    'protocolName': 'DNA Concentration Normalization',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.4'
    }


def run(ctx):
    [volume_csv, max_reaction_volume] = get_values(  # noqa: F821
        'volume_csv', 'max_reaction_volume')

    p10_tip_count = 0
    p50_tip_count = 0

    def update_p10_tip_count(num):
        nonlocal p10_tip_count
        p10_tip_count += num
        if p10_tip_count > 96:
            ctx.pause('The P10 tips have run out. Replenish tip rack before  resuming protocol.')
            p10.reset_tip_tracking()
            p10_tip_count = 0

    def update_p50_tip_count(num):
        nonlocal p50_tip_count
        p50_tip_count += num
        if p50_tip_count > 96:
            ctx.pause('The P50 tips have run out. Replenish tip rack before  resuming protocol.')
            p50.reset_tip_tracking()
            p50_tip_count = 0

    def csv_to_list(csv_string):
        sources, dests, dna_vol, diluent_vol = [], [], [], []
        info_list = [cell for line in csv_string.splitlines() if line
                     for cell in [line.split(',')]]
        labware_dict = {}
        for line in info_list[1:]:
            source_slot = line[0].split(' ')[-1]
            if source_slot not in labware_dict:
                labware_dict[source_slot] = ctx.load_labware(
                    'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
                    source_slot)
            source_well = line[1]
            dest_well = line[2]
            vol_dna = float(line[3])
            vol_dil = float(line[4])
            sources.append(
                labware_dict[source_slot].wells_by_name()[source_well])
            dests.append(pcr_plate.wells_by_name()[dest_well])
            dna_vol.append(vol_dna)
            diluent_vol.append(vol_dil)

        return sources, dests, dna_vol, diluent_vol

    # labware setup
    tuberack = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '2')
    pcr_plate = ctx.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul', '1',
        'PCR strips')

    tipracks_10 = ctx.load_labware('opentrons_96_tiprack_10ul', '7')
    tiprack_300 = ctx.load_labware('opentrons_96_tiprack_300ul', '9')

    # instruments setup
    p10 = ctx.load_instrument(
        'p10_single', mount='left', tip_racks=[tipracks_10])
    p50 = ctx.load_instrument(
        'p50_single', mount='right', tip_racks=[tiprack_300])

    # reagent setup
    buffer = tuberack.wells()[0]

    sources, dests, dna_vols, diluent_vols = csv_to_list(volume_csv)

    # distribute buffer
    for vol, dest in zip(diluent_vols, dests):
        if vol >= 5:
            pipette = p50
        elif vol > 0 and vol < 5:
            pipette = p10
        else:
            continue
        if not pipette.hw_pipette['has_tip']:
            pipette.pick_up_tip()
            pipette.aspirate(vol, buffer)
        if vol > pipette.current_volume:
            pipette.aspirate(
                pipette.max_volume - pipette.current_volume, buffer)
        pipette.dispense(vol, dest)
    if p50.hw_pipette['has_tip']:
        p50.drop_tip()
        update_p50_tip_count(1)
    if p10.hw_pipette['has_tip']:
        p10.drop_tip()
        update_p10_tip_count(1)

    # transfer and mix samples
    for source, vol, dest in zip(sources, dna_vols, dests):
        if vol > 10:
            pipette = p50
            update_p50_tip_count(1)
        else:
            pipette = p10
            update_p10_tip_count(1)
        pipette.pick_up_tip()
        pipette.transfer(vol, source, dest, new_tip='never')
        pipette.mix(3, max_reaction_volume / 2, dest)
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
    filename = f"detailed_action_json/1479.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)