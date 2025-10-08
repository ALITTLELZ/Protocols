import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/69db93/69db93.ot2.apiv2.py"

import math
from opentrons.types import Point

metadata = {
    'protocolName': 'RNA Extraction With Magnetic Beads (no tip waste)',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(ctx):

    [num_samp, asp_height, asp_flow_rate, disp_flow_rate,
     length_from_side, disp_height, m300_mount] = get_values(  # noqa: F821
        "num_samp", "asp_height", "asp_flow_rate", "disp_flow_rate",
        "length_from_side", "disp_height", "m300_mount")

    if not 1 <= num_samp <= 96:
        raise Exception("Enter a sample number between 1-96")
    if not 1 <= length_from_side <= 4.15:
        raise Exception("Enter a distance from the well side between 1-4.15mm")

    # load labware
    mag_mod = ctx.load_module('magnetic module gen2', '1')
    x_plate = mag_mod.load_labware('nest_96_wellplate_2ml_deep')
    res = ctx.load_labware('nest_12_reservoir_15ml', '2')
    pcr_plate = ctx.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', '3')
    parked_tips_rack1 = ctx.load_labware('opentrons_96_filtertiprack_200ul',
                                         '4', label='Parked Tip Rack 1')
    parked_tips_rack2 = ctx.load_labware('opentrons_96_filtertiprack_200ul',
                                         '7', label='Parked Tip Rack 2')
    parked_tips_rack3 = ctx.load_labware('opentrons_96_filtertiprack_200ul',
                                         '10', label='Parked Tip Rack 3')
    tipracks = [ctx.load_labware('opentrons_96_filtertiprack_200ul', str(slot))
                for slot in [5, 6, 8, 9]]
    liquid_waste = ctx.load_labware('nest_1_reservoir_195ml', '11')

    # load instrument + pipette settings
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount,
                               tip_racks=tipracks)

    num_col = math.ceil(num_samp/8)
    airgap = 20

    def remove_supernat(use):
        for index, (col, park) in enumerate(zip(x_plate.rows()[0][:num_col],
                                            use.rows()[0])):
            m300.pick_up_tip(park)
            side = -1 if index % 2 == 0 else 1
            aspirate_loc = col.bottom(z=asp_height).move(
                    Point(x=(col.length/2-length_from_side)*side))
            transfer_vols = [150, 150, 100]
            for vol in transfer_vols:
                m300.move_to(col.center())
                m300.aspirate(vol, aspirate_loc)
                m300.air_gap(airgap)
                m300.dispense(vol+airgap,
                              liquid_waste.wells()[0].top(z=disp_height))
                m300.blow_out(location=liquid_waste.wells()[0].top(z=15))
            ctx.comment('\n')
            m300.drop_tip(park)

    def mix(vol, park_tips_in, use_new_tips=False, blowout='trash'):
        m300.flow_rate.aspirate = asp_flow_rate
        m300.flow_rate.dispense = disp_flow_rate
        for col, park in zip(x_plate.rows()[0][:num_col],
                             park_tips_in.rows()[0]):
            if use_new_tips:
                m300.pick_up_tip()
            else:
                m300.pick_up_tip(park)
            m300.mix(15, vol, col.bottom(z=0.5))
            if blowout == 'trash':
                m300.blow_out(ctx.loaded_labwares[12].wells()[0])
            else:
                m300.blow_out()
            m300.drop_tip(park)
        m300.flow_rate.aspirate = 94
        m300.flow_rate.dispense = 94

    # reagents
    bind_buffer = res.wells()[:6]
    wash_buffer = res.wells()[6:10]
    te = res.wells()[10:]

    # protocol
    ctx.comment('\n--------- MIXING MAGPLATE AND PARKING TIPS (1) ---------\n')
    mix(150, park_tips_in=parked_tips_rack1, use_new_tips=True)
    # tip rack on 5 now empty

    ctx.comment('\n------ REMOVING SUPERNATANT TO LIQUID WASTE (2-4)-------\n')
    mag_mod.engage()
    ctx.delay(minutes=1)
    remove_supernat(use=parked_tips_rack1)  # use parked tips from step 1
    mag_mod.disengage()
    # parked tips on 1 not used again

    ctx.comment('\n------------ ADD ETOH + BINDING BUFFER (6) -------------\n')
    m300.pick_up_tip()
    for col, well in zip(x_plate.rows()[0][:num_col], bind_buffer*2):
        transfer_vols = [150, 150, 100]
        for vol in transfer_vols:
            m300.aspirate(vol, well)
            m300.air_gap(airgap)
            m300.dispense(vol+airgap, col.top(-2))
            m300.blow_out()
        ctx.comment('\n\n')
    m300.return_tip()

    ctx.comment('\n-------- MIXING MAGPLATE AND PARKING TIPS (7) ----------\n')
    mix(150, park_tips_in=parked_tips_rack2, use_new_tips=True)

    ctx.comment('\n----- REMOVING SUPERNATANT TO LIQUID WASTE (8-11) ------\n')
    mag_mod.engage()
    ctx.delay(seconds=30)
    remove_supernat(use=parked_tips_rack2)  # use parked tip from step 7
    mag_mod.disengage()

    ctx.comment('\n----------- ADD ETOH + BINDING BUFFER (12) -------------\n')
    m300.pick_up_tip()
    for col, well in zip(x_plate.rows()[0][:num_col], wash_buffer*3):
        transfer_vols = [150, 150, 100]
        for vol in transfer_vols:
            m300.aspirate(vol, well)
            m300.air_gap(airgap)
            m300.dispense(vol+airgap, col.top(-2))
            m300.blow_out()
        ctx.comment('\n\n')
    m300.return_tip()

    ctx.comment('\n-------- MIXING MAGPLATE AND PARKING TIPS (13) ---------\n')
    mix(150, park_tips_in=parked_tips_rack2)  # use parked tips from step 10

    ctx.comment('\n---- REMOVING SUPERNATANT TO LIQUID WASTE (14-18) ------\n')
    mag_mod.engage()
    ctx.delay(seconds=30)
    remove_supernat(use=parked_tips_rack2)  # use parked tips from step 13
    ctx.delay(minutes=3)
    mag_mod.disengage()
    # parked tips on 7 not used again

    ctx.comment('\n------------ ADDING TE TO ALL WELLS (19) ---------------\n')
    m300.pick_up_tip()
    for col, well in zip(x_plate.rows()[0][:num_col], te*6):
        m300.aspirate(65, well)
        m300.air_gap(airgap)
        m300.dispense(65+airgap, col.top(-2))
        m300.blow_out()
        ctx.comment('\n\n')
    m300.return_tip()

    ctx.comment('\n-------- MIXING MAGPLATE AND PARKING TIPS (20) ---------\n')
    mix(50,
        park_tips_in=parked_tips_rack3,
        use_new_tips=True,
        blowout='dest')

    ctx.comment('\n--------- TRANSFER ELUATE TO PCR PLATE (21:) -----------\n')
    mag_mod.engage()
    ctx.delay(seconds=45)
    for index, (s, d) in enumerate(zip(x_plate.rows()[0][:num_col],
                                       pcr_plate.rows()[0])):
        # use parked tips from step 20
        m300.pick_up_tip(parked_tips_rack3.rows()[0][index])
        m300.aspirate(65, s)
        m300.air_gap(airgap)
        m300.dispense(65+airgap, d.bottom(z=0.5))
        m300.blow_out(location=d.bottom(z=0.5))
        m300.return_tip()
        ctx.comment('\n')
    mag_mod.disengage()

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
    filename = f"detailed_action_json/69db93.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)