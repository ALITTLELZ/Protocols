import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/3633ca/3633ca.ot2.apiv2.py"

metadata = {
    'protocolName': 'Ethanol Transfer',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.5'
}


def run(protocol):
    [p300mnt, p20mnt] = get_values(  # noqa: F821
        'p300mnt', 'p20mnt')

    # load labware and pipettes
    tips20 = [protocol.load_labware('opentrons_96_tiprack_20ul', '3')]
    p20 = protocol.load_instrument('p20_multi_gen2', p20mnt, tip_racks=tips20)
    p300 = protocol.load_instrument('p300_multi_gen2', p300mnt)

    magdeck = protocol.load_module('magdeck', '4')
    magplate = magdeck.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')
    magrows = magplate.rows()[0]

    res = protocol.load_labware('usascientific_12_reservoir_22ml', '1')
    tips1 = protocol.load_labware('opentrons_96_tiprack_300ul', '7').rows()[0]
    tips2 = protocol.load_labware('opentrons_96_tiprack_300ul', '10').rows()[0]

    p300.flow_rate.aspirate = 100
    p300.flow_rate.dispense = 150
    p20.flow_rate.dispense = 50

    magdeck.engage()

    # Ethanol addition and removal
    def ethanol_wash(src1, src2, tips, waste):
        src = [res.wells()[src1] for _ in range(6)]
        src += [res.wells()[src2] for _ in range(6)]
        for tip, s, well in zip(tips, src, magrows):
            p300.pick_up_tip(tip)
            p300.aspirate(150, s)
            p300.dispense(150, well)
            p300.return_tip()

        protocol.comment('Incubating for 30 seconds')
        protocol.delay(seconds=30)

        p300.flow_rate.aspirate = 50
        for tip, well in zip(tips, magrows):
            p300.pick_up_tip(tip)
            p300.aspirate(150, well)
            p300.dispense(150, res.wells()[waste].top())
            p300.drop_tip()
        p300.flow_rate.aspirate = 100

    ethanol_wash(0, 1, tips1, 9)

    ethanol_wash(2, 3, tips2, 10)

    for well in magrows:
        p20.pick_up_tip()
        p20.aspirate(15, well.bottom(0.2))
        p20.dispense(15, res.wells()[11].top())
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
    filename = f"detailed_action_json/3633ca.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)