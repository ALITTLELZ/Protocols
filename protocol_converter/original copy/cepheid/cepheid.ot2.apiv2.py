import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/cepheid/cepheid.ot2.apiv2.py"

metadata = {
    'protocolName': 'Pooling Samples and Distribution to Cepheid',
    'author': 'Dipro <dipro@basisdx.org>; Chaz <chaz@opentrons.com>',
    'source': 'Covid-19 Diagnostics',
    'apiLevel': '2.6'
}


def run(protocol):
    [numSamps, mnt] = get_values(  # noqa: F821
     'numSamps', 'mnt')

    # load labware and pipettes
    tips1000 = protocol.load_labware('opentrons_96_filtertiprack_1000ul', '8')

    p1000 = protocol.load_instrument(
        'p1000_single_gen2', mnt, tip_racks=[tips1000])

    samp_tuberack_1 = protocol.load_labware('basisdx_15_tuberack_12000ul', '4')
    samp_tuberack_2 = protocol.load_labware('basisdx_15_tuberack_12000ul', '6')

    pool_rack = protocol.load_labware('basisdx_15_tuberack_12000ul', '5')

    cepheid_1 = protocol.load_labware('cepheid', '1')
    cepheid_2 = protocol.load_labware('cepheid', '2')
    cepheid_3 = protocol.load_labware('cepheid', '3')

    # load samples & visby dilution buffer

    samp_1 = samp_tuberack_1['A1']
    samp_2 = samp_tuberack_1['A2']
    samp_3 = samp_tuberack_1['A3']
    samp_4 = samp_tuberack_1['A4']
    samp_5 = samp_tuberack_1['A5']
    samp_6 = samp_tuberack_1['B1']
    samp_7 = samp_tuberack_1['B2']
    samp_8 = samp_tuberack_1['B3']
    samp_9 = samp_tuberack_1['B4']
    samp_10 = samp_tuberack_1['B5']

    samp_11 = samp_tuberack_1['C1']
    samp_12 = samp_tuberack_1['C2']
    samp_13 = samp_tuberack_1['C3']
    samp_14 = samp_tuberack_1['C4']
    samp_15 = samp_tuberack_1['C5']

    samp_16 = samp_tuberack_2['A1']
    samp_17 = samp_tuberack_2['A2']
    samp_18 = samp_tuberack_2['A3']
    samp_19 = samp_tuberack_2['A4']
    samp_20 = samp_tuberack_2['A5']
    samp_21 = samp_tuberack_2['B1']
    samp_22 = samp_tuberack_2['B2']
    samp_23 = samp_tuberack_2['B3']
    samp_24 = samp_tuberack_2['B4']
    samp_25 = samp_tuberack_2['B5']
    samp_26 = samp_tuberack_2['C1']
    samp_27 = samp_tuberack_2['C2']
    samp_28 = samp_tuberack_2['C3']
    samp_29 = samp_tuberack_2['C4']
    samp_30 = samp_tuberack_2['C5']

    pool_1 = pool_rack['A1']
    pool_2 = pool_rack['A5']
    pool_3 = pool_rack['C1']

    cepheid_well_1 = cepheid_1['A1']
    cepheid_well_2 = cepheid_2['A1']
    cepheid_well_3 = cepheid_3['A1']

    # setting pipette speeds
    p1000.flow_rate.aspirate = 300
    p1000.flow_rate.dispense = 300

    # Pool samples
    protocol.comment('Pooling Samples Now')
    pool_vol = 62
    mygap = 50

    # maybe define the number of samples here
    my_list_of_samples_1 = [samp_1, samp_2, samp_3, samp_4, samp_5,
                            samp_6, samp_7, samp_8, samp_9, samp_10]
    my_list_of_samples_2 = [samp_11, samp_12, samp_13, samp_14, samp_15,
                            samp_16, samp_17, samp_18, samp_19, samp_20]
    my_list_of_samples_3 = [samp_21, samp_22, samp_23, samp_24, samp_25,
                            samp_26, samp_27, samp_28, samp_29, samp_30]

    def pool_party(my_list_of_samples, pool, cepheid_well):
        for sample in my_list_of_samples:
            p1000.pick_up_tip()
            p1000.aspirate(pool_vol, sample.bottom(10))
            p1000.air_gap(mygap)

            # dispense into pool
            p1000.dispense(pool_vol+5+mygap, pool.top(-30))
            if sample != my_list_of_samples[-1]:
                p1000.air_gap(mygap)
                p1000.drop_tip(home_after=False)

            else:
                # Mix the Pool
                protocol.comment('Mixing Pooled Samples')
                p1000.mix(2, 500, pool.bottom(38))

                # Dispensing to Cepheid
                protocol.comment('Adding Pool to Cepheid')
                ali_vol = 300
                p1000.aspirate(ali_vol, pool.bottom(38))
                p1000.aspirate(1, pool.top(-1))
                p1000.air_gap(mygap)
                p1000.dispense(ali_vol+20+mygap, cepheid_well.bottom(10))
                p1000.air_gap(mygap)
                p1000.drop_tip()

    pool_party(my_list_of_samples_1, pool_1, cepheid_well_1)
    if numSamps > 10:
        pool_party(my_list_of_samples_2, pool_2, cepheid_well_2)
    if numSamps > 20:
        pool_party(my_list_of_samples_3, pool_3, cepheid_well_3)

    # Finish
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
    filename = f"detailed_action_json/cepheid.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)