import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/02b308/pcr_prep.ot2.apiv2.py"

from opentrons.types import Point

metadata = {
    'protocolName': 'PCR Prep',
    'author': 'Opentrons <protocols@opentrons.com>',
    'apiLevel': '2.13'
}


def run(ctx):

    [mount_m20, num_plates, num_primers] = get_values(  # noqa: F821
        'mount_m20', 'num_plates', 'num_primers')

    ctx.max_speeds['X'] = 200
    ctx.max_speeds['Y'] = 200

    primers_plate = ctx.load_labware('eppendort_96_deepwell_1000ul', '8',
                                     'primers plate')
    dna_plate = ctx.load_labware('eppendort_96_deepwell_1000ul', '9',
                                 'mastermix/cDNA plate')
    qpcr_plates = [
        ctx.load_labware('appliedbiosystems_384_wellplate_40ul', slot,
                         f'qPCR plate {i+1}')
        for i, slot in enumerate(range(7, 7-num_plates, -1))]
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot,
                         '200µl filtertiprack')
        for slot in ['10', '11']]

    # load P300M pipette
    m20 = ctx.load_instrument(
        'p20_multi_gen2', mount_m20, tip_racks=tips20)

    # locations
    primers = primers_plate.rows()[0][:num_primers]
    dna_sources = dna_plate.rows()[0][:num_plates*2]
    vol_primer = 2.0
    vol_dna = 8.0

    def wick(well, pip=m20, side=1):
        ctx.max_speeds['A'] = 25
        ctx.max_speeds['Z'] = 25
        pip.move_to(well.bottom().move(Point(x=side*well.diameter/2*0.8, z=3)))
        pip.move_to(well.top().move(Point(x=side*well.diameter/2*0.8)))
        del ctx.max_speeds['A']
        del ctx.max_speeds['Z']

    def slow_withdraw(well, pip=m20, delay=2.0):
        ctx.max_speeds['A'] = 25
        ctx.max_speeds['Z'] = 25
        if delay:
            ctx.delay(seconds=delay)
        pip.move_to(well.top())
        del ctx.max_speeds['A']
        del ctx.max_speeds['Z']

    # transfer primers
    for i, primer in enumerate(primers):
        m20.pick_up_tip()
        for plate in qpcr_plates:
            row = plate.rows()[i % 2]
            shift = (i // 2) * 3
            dests = row[shift:shift+3] +  row[shift+12:shift+12+3]
            for d in dests:
                m20.aspirate(vol_primer, primer.bottom(1))
                slow_withdraw(primer)
                m20.dispense(vol_primer, d.bottom(0.5))
                wick(d)
        m20.drop_tip()

    # transfer cDNA + mm
    m20.flow_rate.dispense *= 2
    m20.flow_rate.blow_out *= 2
    vol_pre_air_gap = 20 - vol_dna
    for i, s in enumerate(dna_sources):
        plate = qpcr_plates[i//2]
        half = i % 2
        columns = plate.columns()[half*12:(half+1)*12]
        all_dests = [well for col in columns for well in col[:2]]
        m20.pick_up_tip()
        for d in all_dests:
            m20.aspirate(vol_pre_air_gap, s.top())
            m20.aspirate(vol_dna, s.bottom(1))
            m20.dispense(m20.current_volume, d.top(-1))
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
    filename = f"detailed_action_json/02b308.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)