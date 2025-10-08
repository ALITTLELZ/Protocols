import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/3662e6/3662e6.ot2.apiv2.py"

metadata = {
    'protocolName': 'Custom Drug Dilution Assay',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(protocol):
    [mnt300, mnt10, nc] = get_values(  # noqa: F821
     'mnt300', 'mnt10', 'nc')

    # load labware
    tips10 = [protocol.load_labware('opentrons_96_filtertiprack_10ul', '5')]
    tips300 = [protocol.load_labware('opentrons_96_tiprack_300ul', '2')]

    m10 = protocol.load_instrument('p10_multi', mnt10, tip_racks=tips10)
    m300 = protocol.load_instrument('p300_multi', mnt300, tip_racks=tips300)
    m10.flow_rate.aspirate = 10
    m10.flow_rate.dispense = 10

    dd01, dd1, dd10, ds200 = [
        protocol.load_labware(
            'corning_96_wellplate_360ul_flat',
            s,
            n) for s, n in zip(range(1, 12, 3), [
                'Drug Dilution 0.1uM',
                'Drug Dilution 1uM',
                'Drug Dilution 10uM',
                'Drug Stock 200uM'])]

    cells, media = [
        protocol.load_labware(
            'axygen_1_reservoir_90ml',
            s,
            n) for s, n in zip([11, 8], ['Cells', 'Media+IL-2+OKT3+CD28'])]

    # Transfer 100µL Media to wells in plates
    allPlateWells = dd10.rows()[0][:nc]+dd1.rows()[0][:nc]+dd01.rows()[0][:nc]

    protocol.comment('Transferring 100µL of Media to all wells...')
    tipctr = 0

    for well in allPlateWells:
        if tipctr == 0:
            m300.pick_up_tip()
        m300.aspirate(20, media['A1'].top())
        m300.aspirate(60, media['A1'])
        m300.dispense(60, media['A1'])
        m300.aspirate(100, media['A1'])
        m300.air_gap(30)
        m300.dispense(150, well)
        m300.blow_out()
        tipctr += 1
        if tipctr == 4:
            m300.return_tip()
            m300.reset_tipracks()
            tipctr = 0
    if m300.has_tip:
        m300.return_tip()

    # Perform dilutions
    protocol.comment('Performing 10x dilutions...')
    plates = [p.rows()[0][:nc] for p in [ds200, dd10, dd1, dd01]]
    for s, p1, p2, p3 in zip(*plates):
        m10.pick_up_tip()

        m10.transfer(
            10, s, p1, new_tip='never',
            mix_before=(4, 10), mix_after=(4, 10))
        m10.blow_out()
        m10.transfer(
            10, p1, p2, new_tip='never',
            mix_before=(1, 7), mix_after=(4, 10))
        m10.blow_out()
        m10.transfer(
            10, p2, p3, new_tip='never',
            mix_before=(1, 7), mix_after=(4, 10))
        m10.blow_out()

        m10.transfer(
            10, p3, protocol.fixed_trash['A1'], new_tip='never',
            mix_before=(1, 7), blow_out=True)

        m10.drop_tip()

    # Transfer 100µL Cells to wells in plates
    protocol.comment('Transferring 100µL of cells to all wells...')
    tipctr = 0
    m300.flow_rate.dispense = 200

    for well in allPlateWells:
        if tipctr == 0:
            m300.pick_up_tip(tips300[0]['A2'])
        m300.mix(5, 300, cells['A1'])
        m300.blow_out(cells['A1'])
        m300.aspirate(20, cells['A1'].top())
        m300.aspirate(60, cells['A1'])
        m300.dispense(60, cells['A1'])
        m300.aspirate(100, cells['A1'])
        m300.air_gap(30)
        m300.dispense(150, well.top(-2))
        m300.blow_out()
        tipctr += 1
        if tipctr == 4:
            m300.drop_tip(tips300[0]['A2'])
            tipctr = 0
    if m300.has_tip:
        m300.drop_tip(tips300[0]['A2'])

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
    filename = f"detailed_action_json/3662e6.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)