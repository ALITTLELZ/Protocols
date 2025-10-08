import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0ef96f/cherrypick.ot2.apiv2.py"

# metadata
metadata = {
    'protocolName': 'Cherrypicking from .csv',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(ctx):

    [input_file, p20_mount, p300_mount] = get_values(  # noqa: F821
        'input_file', 'p20_mount', 'p300_mount')
    # [input_file, p20_mount, p300_mount] = [
    #     'Lable,Pos,nM,FC,Rxn,Vol,h2O,Tube\nP_F3,A1,28.9,0.8,100,10,30, #     T1\nP_B3,A2,28.32,0.8,100,10,,T1\nP_FIP,A3,53.8,1.6,100,20,,\
    #     T1\nP_BIP,A4,82,1.6,100,20,,T1\nP_LF,A5,32.5,0.4,100,5,,T1',
    #     'right', 'left']

    # load labware
    plate = ctx.load_labware(
        'usascientific_96_wellplate_2.4ml_deep', '1', 'deepwell plate')
    tuberack24 = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
        '4',
        '4x6 rack with 2ml Eppendorf tubes'
    )
    tipracks20 = [
        ctx.load_labware('opentrons_96_tiprack_20ul', slot, '20ul tiprack')
        for slot in ['2', '3']
    ]
    tipracks300 = [
        ctx.load_labware('opentrons_96_tiprack_300ul', slot, '300ul tiprack')
        for slot in ['5', '6']
    ]

    # load pipettes
    p20 = ctx.load_instrument(
        'p20_single_gen2', p20_mount, tip_racks=tipracks20)
    p300 = ctx.load_instrument(
        'p300_single_gen2', p300_mount, tip_racks=tipracks300)

    # reagent setup
    h2o = tuberack24.columns()[4][-1]
    r1 = tuberack24.columns()[5]

    tube_list = [
        well for set in [
            col if i < 4 else col[:3]
            for i, col in enumerate(tuberack24.columns()[:5])]
        for well in set
    ]

    # parse
    labels, wells, nms, final_vols, h2o_vols, tubes = [
        [line.split(',')[ind].strip() for line in input_file.splitlines()[1:]]
        for ind in [0, 1, 2, 5, 6, 7]
    ]

    """ Phase 1 """
    r1_ind = 0
    r1_vol_count = 0
    for nm, well in zip(nms, wells):
        vol = float(nm)*5
        if r1_vol_count + vol > 2000:
            r1_ind += 1
            r1_vol_count = 0
        r1_vol_count += vol
        dest = plate.wells_by_name()[well]
        p300.pick_up_tip()
        p300.transfer(vol, r1[r1_ind], dest, air_gap=20, new_tip='never')
        mix_vol = vol if vol < 250 else 250
        p300.mix(3, mix_vol, dest)
        p300.blow_out(dest.top(-2))
        p300.drop_tip()

    """ Phase 2 """
    for h2o_vol, well in zip(h2o_vols, wells):
        if h2o_vol:
            vol = float(h2o_vol)
        pip = p20 if vol <= 20 else p300
        if not pip.hw_pipette['has_tip']:
            pip.pick_up_tip()
        pip.transfer(vol, h2o, dest.top(), new_tip='never')

    """ Phase 3 """
    existing_tubes = {}
    for final_vol, well, tube in zip(final_vols, wells, tubes):
        vol = float(final_vol)
        source = plate.wells_by_name()[well]
        dest = tube_list[int(tube.split('T')[-1])-1]
        p20.pick_up_tip()
        p20.transfer(vol, source, dest, new_tip='never')
        if tube in existing_tubes:
            existing_tubes[tube] += vol
            mix = True
        else:
            existing_tubes[tube] = vol
            mix = False
        if mix:
            if existing_tubes[tube] >= 20:
                mix_vol = 15
            else:
                mix_vol = vol
            p20.mix(3, mix_vol, dest)
        p20.blow_out(dest.top(-2))
        p20.drop_tip()

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
    filename = f"detailed_action_json/0ef96f.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)