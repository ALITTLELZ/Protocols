import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/onsite-ganda-1/pcr_prep1.ot2.apiv2.py"

"""OPENTRONS."""
import math
import threading
from time import sleep

metadata = {
    'protocolName': 'rhAmpSeq Library Prep Part 1 - PCR Prep 1',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'   # CHECK IF YOUR API LEVEL HERE IS UP TO DATE
                         # IN SECTION 5.2 OF THE APIV2 "VERSIONING"
}


class CancellationToken:
    """flash_setup."""

    def __init__(self):
        """init."""
        self.is_continued = False

    def set_true(self):
        """set_true."""
        self.is_continued = True

    def set_false(self):
        """set_false."""
        self.is_continued = False


def turn_on_blinking_notification(hardware, pause):
    """Turn on blinking."""
    while pause.is_continued:
        hardware.set_lights(rails=True)
        sleep(1)
        hardware.set_lights(rails=False)
        sleep(1)


def create_thread(ctx, cancel_token):
    """Create thread."""
    t1 = threading.Thread(target=turn_on_blinking_notification,
                          args=(ctx._hw_manager.hardware, cancel_token))
    t1.start()
    return t1


def run(ctx):
    """PROTOCOL."""
    [
     num_samples, m20_mount, flash
    ] = get_values(  # noqa: F821 (<--- DO NOT REMOVE!)
        "num_samples", "m20_mount", "flash")
    # num_samples, m20_mount = 8, 'right'

    # define all custom variables above here with descriptions:
    cancellationToken = CancellationToken()
    num_cols = math.ceil(num_samples/8)
    m20_speed_mod = 4
    # airgap_library = 5

    # load modules
    mag_module = ctx.load_module('magnetic module gen2', '1')

    # load labware
    sample_plate = mag_module.load_labware('nest_96_wellplate'
                                           '_100ul_pcr_full_skirt')
    reagent_plate = ctx.load_labware('nest_96_wellplate_100ul_pcr_full_skirt',
                                     '2')
    # load tipracks
    tiprack20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul',
                                  str(slot))
                 for slot in [3, 5, 6][:math.ceil(num_samples/32)]]

    # load instrument
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount, tip_racks=tiprack20)

    # pipette functions   # INCLUDE ANY BINDING TO CLASS

    # helper functions

    # reagents
    library_mix = reagent_plate.rows()[0][0]
    pcr_forward = reagent_plate.rows()[0][1]
    pcr_reverse = reagent_plate.rows()[0][2]
    # plate, tube rack maps
    sample_dest = sample_plate.rows()[0][:num_cols]
    # protocol

    # add library mix, 5 uL
    for dest in sample_dest:
        m20.flow_rate.aspirate /= m20_speed_mod
        m20.flow_rate.dispense /= m20_speed_mod
        m20.pick_up_tip()
        m20.aspirate(5, library_mix)
        m20.move_to(library_mix.top(-2))
        ctx.delay(seconds=2)
        # m20.touch_tip(v_offset=-2)
        # m20.move_to(library_mix.top(-2))
        # m20.aspirate(airgap_library, library_mix.top())
        # m20.dispense(airgap_library, dest.top())
        m20.dispense(5, dest)
        m20.mix(1, 5, dest)
        ctx.max_speeds['A'] = 100
        ctx.max_speeds['Z'] = 100
        m20.drop_tip()
        del ctx.max_speeds['A']
        del ctx.max_speeds['Z']
        m20.flow_rate.aspirate *= m20_speed_mod
        m20.flow_rate.dispense *= m20_speed_mod
    # add forward, reverse primers, 2 uL each
    for reagent_source in [pcr_forward, pcr_reverse]:
        for dest in sample_dest:
            m20.flow_rate.aspirate /= m20_speed_mod
            m20.flow_rate.dispense /= m20_speed_mod
            m20.pick_up_tip()
            m20.aspirate(2, reagent_source)
            m20.move_to(reagent_source.top(-2))
            ctx.delay(seconds=2)
            # m20.touch_tip(v_offset=-2)
            m20.move_to(reagent_source.top(-2))
            # m20.aspirate(airgap_library, reagent_source.top())
            # m20.dispense(airgap_library, dest.top())
            m20.dispense(5, dest)
            m20.mix(1, 5, dest)
            ctx.max_speeds['A'] = 100
            ctx.max_speeds['Z'] = 100
            m20.drop_tip()
            del ctx.max_speeds['A']
            del ctx.max_speeds['Z']
            m20.flow_rate.aspirate *= m20_speed_mod
            m20.flow_rate.dispense *= m20_speed_mod

    if flash:
        if not ctx._hw_manager.hardware.is_simulator:
            cancellationToken.set_true()
        thread = create_thread(ctx, cancellationToken)
    m20.home()
    ctx.pause('Protocol Complete.')
    ctx.home()  # home before continuing with protocol
    if flash:
        cancellationToken.set_false()  # stop light flashing after home
        thread.join()
    ctx.pause()

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
    filename = f"detailed_action_json/onsite-ganda-1.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)