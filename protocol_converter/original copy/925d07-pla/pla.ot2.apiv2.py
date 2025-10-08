import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/925d07-pla/pla.ot2.apiv2.py"

metadata = {
    'protocolName': 'Plasmid Luciferase Assay',
    'author': 'Nick Diehl <ndiehl@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}

V141_PLASMID_DISPENSE_HEIGHT = 0.5  # mm above bottom
LIPOFECTAMINE_2000_DISPENSE_HEIGHT = 0.5  # mm above bottom


def run(ctx):

    # labware
    plate384 = ctx.load_labware('corning_384_wellplate_112ul_flat', '1')
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', '4')
    plate96 = ctx.load_labware('corning_96_wellplate_360ul_flat', '5')
    tipracks20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['7', '8', '9']]

    # pipette
    m20 = ctx.load_instrument('p20_multi_gen2', 'right', tip_racks=tipracks20)

    # reagent
    v141_plasmid = reservoir.rows()[0][0]
    lipofectamine_2000 = reservoir.rows()[0][1]
    sirna = plate96.rows()[0]

    quadruplicate_sets = [
        [well for col in plate384.columns()[i*2:(i+1)*2] for well in col[:2]]
        for i in range(12)]

    ctx.comment('\n\n\n\n\nV141 PLASMID TRANSFERS\n\n\n\n\n')

    m20.pick_up_tip()
    for set in quadruplicate_sets:
        m20.aspirate(19, v141_plasmid.bottom(4))
        m20.touch_tip(v141_plasmid, v_offset=18.9-v141_plasmid.depth)
        m20.air_gap(1)
        m20.dispense(1, set[0].top(-1))
        for well in set:
            m20.dispense(4, well.bottom(V141_PLASMID_DISPENSE_HEIGHT))
            # m20.touch_tip(well, v_offset=6.4-well.depth)
        m20.dispense(m20.current_volume, v141_plasmid.bottom(4))
    m20.drop_tip()

    ctx.comment('\n\n\n\n\nSiRNA TRANSFERS\n\n\n\n\n')

    for source, set in zip(sirna, quadruplicate_sets):
        m20.pick_up_tip()
        m20.aspirate(19, source.bottom(1))
        m20.air_gap(1)
        m20.dispense(1, set[0].top(-1))
        for well in set:
            m20.dispense(4, well.bottom(1))
            # m20.touch_tip(well, v_offset=10.43-well.depth)
        m20.drop_tip()

    ctx.comment('\n\n\n\n\nLIPOFECTAMINE 2000 TRANSFERS\n\n\n\n\n')

    for set in quadruplicate_sets:
        m20.pick_up_tip()
        m20.aspirate(19, lipofectamine_2000.bottom(4))
        m20.touch_tip(lipofectamine_2000,
                      v_offset=18.9-lipofectamine_2000.depth)
        m20.air_gap(1)
        m20.dispense(1, set[0].top(-1))
        for well in set:
            m20.dispense(4, well.bottom(LIPOFECTAMINE_2000_DISPENSE_HEIGHT))
            # m20.touch_tip(well, v_offset=10.43-well.depth)
        m20.aspirate(5, set[-1].top())  # air gap on way to trash
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
    filename = f"detailed_action_json/925d07-pla.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)