import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/5c50d9/5c50d9.ot2.apiv2.py"

"""Protocol."""
from opentrons import protocol_api

metadata = {
    'protocolName': 'Semi-Automated PCR Prep',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.10'
}


def run(ctx):
    """Protocol."""
    [num_samp, p20_rate, p300_rate,
        p20_mount, p300_mount] = get_values(  # noqa: F821
        "num_samp", "p20_rate", "p300_rate", "p20_mount", "p300_mount")

    # load labware
    final_plate = ctx.load_labware('corning_384_wellplate_112ul_flat', '1')
    thermocyc_plate = ctx.load_labware('corning_384_wellplate_112ul_flat', '2')
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', '3')
    tuberacks = [ctx.load_labware('opentrons_15_tuberack_falcon_15ml_conical',
                 slot) for slot in ['4', '5', '6', '7', '8', '9']]
    tiprack20 = ctx.load_labware('opentrons_96_filtertiprack_20ul', '10')
    tiprack300 = ctx.load_labware('opentrons_96_filtertiprack_200ul', '11')

    # load pipettes
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount,
                              tip_racks=[tiprack20])
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount,
                               tip_racks=[tiprack300])

    p20.flow_rate.dispense = p20_rate*p20.flow_rate.dispense
    p300.flow_rate.dispense = p300_rate*p300.flow_rate.dispense

    def pickup(pip):
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pip.home()
            ctx.pause("Replace the tips")
            pip.reset_tipracks()
            pip.pick_up_tip()

    # protocol
    lysis_buffer = reservoir.wells()[0]

    # distribute lysis buffer to all wells
    pickup(p300)
    for well in thermocyc_plate.wells()[:num_samp]:
        p300.distribute(50, lysis_buffer, well, new_tip='never')
    p300.drop_tip()

    # distribute sample to all well
    tubes = [tube for rack in tuberacks for tube in rack.wells()]
    airgap = 5
    tube_ctr = 0
    for well in thermocyc_plate.wells()[:num_samp]:
        pickup(p300)
        p300.aspirate(50, tubes[tube_ctr])
        ctx.delay(seconds=1)
        p300.air_gap(airgap)
        p300.dispense(50, well)
        p300.drop_tip()
        tube_ctr += 1
        ctx.comment('\n')
        if tube_ctr == 90:
            tube_ctr = 0
            ctx.pause('''
                        All samples on deck are transferred-
                        Place remaining tubes in tuberacks starting from
                        Slot 4, placing tubes down by column.
                        ''')

    ctx.pause('''Sample and lysis transfer complete. Spin down, and thermocycle
                 the 384 well plate, and then place the plate back on the deck
                 for final transfer. ''')

    # final transfer to 384 plate
    for source, dest in zip(thermocyc_plate.wells(),
                            final_plate.wells()[:num_samp]):
        pickup(p20)
        p20.aspirate(4, source)
        p20.air_gap(airgap)
        p20.dispense(4, dest)
        p20.blow_out()
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
    filename = f"detailed_action_json/5c50d9.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)