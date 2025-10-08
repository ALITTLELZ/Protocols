import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/dynabeads_plate_prep_1/dynabeads_IP_96well.ot2.apiv2.py"

"""PROTOCOL."""
metadata = {
    'protocolName': 'Dynabeads for IP Reagent-In-Plate Plate Prep 1',
    'author': '',
    'source': '',
    'apiLevel': '2.11'
            }


def run(ctx):
    """PROTOCOL."""

    [num_samples] = get_values(  # noqa: F821
        'num_samples')

    total_cols = int(num_samples//8)
    r1 = int(num_samples % 8)
    if r1 != 0:
        total_cols = total_cols + 1

    # load labware
    reagent_plate = ctx.load_labware('nest_96_wellplate_2ml_deep', '4',
                                     'reagents')
    reagent_tube = ctx.load_labware('opentrons_15_tuberack_nest_15ml_conical',
                                    '5', 'reagents - stock')
    tiprack = ctx.load_labware('opentrons_96_tiprack_300ul', '7')

    # load pipette
    pip_single = ctx.load_instrument('p300_single_gen2', 'right',
                                     tip_racks=[tiprack])

    # liquids
    beads = reagent_plate.columns()[0]
    ab = reagent_plate.columns()[1]
    beads_stock = reagent_tube.rows()[0][0]
    ab_stock = reagent_tube.rows()[0][1]

    # protocol

    ctx.comment('\n\n\n~~~~~~~~MIXING AND TRANSFER BEADS ~~~~~~~~\n')
    pip_single.pick_up_tip()
    for i in range(total_cols):
        h = 5 + i * 3
        pip_single.mix(5, 250, beads_stock.bottom(z=h), rate=5)
    for i in range(8):
        pip_single.transfer(total_cols*50,
                            beads_stock,
                            beads[i],
                            blow_out=True,
                            blowout_location='destination well',
                            new_tip='never',
                            mix_before=(5, 100),
                            )
    pip_single.drop_tip()
    ctx.comment('\n\n\n~~~~~~~~TRANSFER AB ~~~~~~~~\n')
    pip_single.pick_up_tip()
    for i in range(8):
        pip_single.transfer(total_cols*50,
                            ab_stock,
                            ab[i],
                            blow_out=True,
                            blowout_location='destination well',
                            new_tip='never',
                            )
    pip_single.drop_tip()

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
    filename = f"detailed_action_json/dynabeads_plate_prep_1.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)