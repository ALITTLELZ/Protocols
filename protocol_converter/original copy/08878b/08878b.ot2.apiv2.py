import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/08878b/08878b.ot2.apiv2.py"

metadata = {
    'protocolName': 'Transfer with Temperature Module',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(protocol):
    [p300_mnt, p1k_mnt, inc_time] = get_values(  # noqa: F821
        'p300_mnt', 'p1k_mnt', 'inc_time')

    # load labware
    tempdeck = protocol.load_module('tempdeck', '4')
    sample_plate = tempdeck.load_labware('biorad_96_wellplate_200ul_pcr')

    tips300 = [
        protocol.load_labware(
            'opentrons_96_tiprack_300ul', str(s), '300ul Tips')
        for s in [8, 11]]

    tips1k = [protocol.load_labware(
        'opentrons_96_tiprack_1000ul', '9', '1000ul Tips')
        ]

    tr1550 = protocol.load_labware(
        'opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical',
        '5',
        '15-50mL Tube Rack'
        )

    tr2 = protocol.load_labware(
        'opentrons_24_tuberack_generic_2ml_screwcap', '6', '2mL Tube Rack')

    R1 = tr1550['A1']
    R2 = tr1550['A2']
    R3 = tr1550['B1']
    R4 = tr1550['A3']
    aceacid = tr1550['B2']

    p300 = protocol.load_instrument(
        'p300_single_gen2',
        p300_mnt,
        tip_racks=tips300
        )

    p1k = protocol.load_instrument(
        'p1000_single',
        p1k_mnt,
        tip_racks=tips1k
        )

    small_vol = [25, 50, 75, 150]
    big_vol = [475, 450, 425, 350]

    def tr2_setup(init_well):
        p300.pick_up_tip()
        p300.aspirate(300, tr2.wells()[init_well-4])

        for i, vol in enumerate(small_vol):
            well = init_well+(4*i)
            p300.dispense(vol, tr2.wells()[well])

        p300.drop_tip()

        for i, vol in enumerate(big_vol):
            well = init_well+(4*i)
            p1k.pick_up_tip()
            p1k.transfer(vol, R4, tr2.wells()[well], new_tip='never')
            p1k.mix(5, 450, tr2.wells()[well])
            p1k.blow_out(tr2.wells()[well].top())
            p1k.drop_tip()

    tr2_setup(4)
    tr2_setup(5)

    def setup_temp(src, dest_no):
        dest1 = 'A'+str(dest_no)
        dest2 = 'B'+str(dest_no)
        p300.pick_up_tip()
        p300.aspirate(105, src)
        p300.dispense(50, sample_plate[dest1])
        p300.dispense(50, sample_plate[dest2])
        p300.drop_tip()

    tr2_wells = [R4]
    for ltr in ['A', 'B']:
        for n in range(2, 6):
            tr2_wells.append(tr2[ltr+str(n)])

    for i, src in enumerate(tr2_wells):
        setup_temp(src, i+1)

    dest_wells = []
    for i in range(1, 10):
        dest_wells.append(sample_plate['A'+str(i)])
        dest_wells.append(sample_plate['B'+str(i)])

    def final_transfer(src, vol):
        for dest in dest_wells:
            p300.pick_up_tip()
            p300.transfer(vol, src, dest, new_tip='never')
            p300.mix(5, vol+30)
            p300.blow_out(dest.top())
            p300.drop_tip()
        protocol.delay(minutes=inc_time)

    ft_srcs = [R1, R2, R3, aceacid, aceacid]
    ft_vols = [100, 25, 50, 25, 25]

    tempdeck.set_temperature(37)

    for src, vol in zip(ft_srcs, ft_vols):
        final_transfer(src, vol)

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
    filename = f"detailed_action_json/08878b.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)