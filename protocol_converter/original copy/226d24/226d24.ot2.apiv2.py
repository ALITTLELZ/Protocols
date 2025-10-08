import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/226d24/226d24.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'PCR Set-Up',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(protocol):
    [p300mnt, p20mnt, num_samples] = get_values(  # noqa: F821
     'p300mnt', 'p20mnt', 'num_samples')

    # load labware and pipette
    res = protocol.load_labware('nest_12_reservoir_15ml', '5')

    pcr_plate = protocol.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt', '4')

    samp_plate = protocol.load_labware(
        'thermofisherdwplate_96_wellplate_2000ul', '1')

    primer_plate = protocol.load_labware('plateone_96_wellplate_1000ul', '7')

    tips20 = [
        protocol.load_labware(
            'opentrons_96_filtertiprack_20ul', s) for s in ['3', '6']]
    tips300 = [protocol.load_labware('opentrons_96_filtertiprack_200ul', '2')]

    m20 = protocol.load_instrument('p20_multi_gen2', p20mnt, tip_racks=tips20)
    m300 = protocol.load_instrument(
        'p300_multi_gen2', p300mnt, tip_racks=tips300)

    # variable declarations
    num_cols = math.ceil(num_samples/8)
    samps = samp_plate.rows()[0][:num_cols]
    pcr_wells = pcr_plate.rows()[0][:num_cols]
    primers = primer_plate.rows()[0][:num_cols]

    reaction_vols = [i*9*num_cols for i in [26, 20, 1]]

    reaction_m = res.wells()[:3]

    rm = res['A4']

    # create reactionmix
    protocol.comment('Combining water, mastermix, and reverse primers...')
    for vol, loc in zip(reaction_vols, reaction_m):
        m300.pick_up_tip()
        m300.transfer(vol, loc, rm.top(-3), new_tip='never')
        m300.blow_out()
        m300.drop_tip()

    # distribute reactionmix
    protocol.comment('Distributing reaction mix...')
    m300.pick_up_tip()
    m300.mix(12, 180, rm)
    m300.blow_out()

    for well in pcr_wells:
        m300.aspirate(47, rm)
        m300.dispense(47, well)

    m300.drop_tip()

    # add forward primers
    protocol.comment('Adding forward primers...')
    for primer, well in zip(primers, pcr_wells):
        m20.pick_up_tip()
        m20.mix(3, 5, primer)
        m20.aspirate(1, primer)
        m20.dispense(1, well)
        m20.blow_out()
        m20.drop_tip()

    # add samples
    protocol.comment('Adding samples...')
    for s, well in zip(samps, pcr_wells):
        m20.pick_up_tip()
        m20.mix(3, 5, s)
        m20.aspirate(1, s)
        m20.dispense(1, well)
        m20.mix(5, 18, well)
        m20.blow_out()
        m20.drop_tip()

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
    filename = f"detailed_action_json/226d24.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)