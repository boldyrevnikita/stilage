import traceback
from typing import Any

from src.cargo_packer import CargoPacker
from src.network.network import Sender
from src.network.output_generation import generate_output
from src.network.utils import get_dxf_doc_from_s3
from src.occupied_zone_scan import scan_for_occupied_zones
from src.pallet import CargoType
from src.pallet_packer.pallet_packer import PalletPacker
from src.reference_book import ReferenceBook
from src.zone import AvailableZone, OccupiedZone, SpecialRoadZone
from src.utils import check_if_debugger_is_active
from src.visualize import visualize_solution
from src.network.input_schema import ModelInput


def process_message_ml(message: Any, sender: Sender):
    """Process message from the queue.

    Args:
        message (Any): message to process
        sender (Sender): sender to send the results
    """
    available_zones: list[AvailableZone] = []
    occupied_zones: list[OccupiedZone] = []
    road_zones: list[SpecialRoadZone] = []
    cargos: list[CargoType] = []

    print('Message received')
    print()
    print(message)

    try:
        # input data validation
        ModelInput(**message)

        for zone in message['available_zones']:
            available_zones.append(AvailableZone(zone['boundary'],
                                                 zone['height'],
                                                 zone['orientation']))

        for zone in message['road_zones']:
            road_zones.append(SpecialRoadZone(zone['line'],
                                              zone['width']))

        for zone in message['restricted_zones']:
            occupied_zones.append(OccupiedZone(zone['boundary'],
                                               zone['clearance']))

        for rack_section in message['cargos']:
            cargos.append(CargoType(
                cargo_type_id=rack_section['id'],
                weight=rack_section['weight'],
                length=rack_section['length'],
                width=rack_section['width'],
                height=rack_section['height'],
                quantity=rack_section['quantity']
            ))

        roads_width = message['roads_width']
        roads_height = message['roads_height']
        file_id = message['file_id']

        reference_book = ReferenceBook()

        if roads_width is not None:
            reference_book.roads_width = roads_width
        if roads_height is not None:
            reference_book.roads_height = roads_height

        doc = get_dxf_doc_from_s3(file_id)

        occupied_zones += scan_for_occupied_zones(
            doc=doc,
            available_zones=available_zones,
            occupied_zone_clearance=reference_book.forbidden_zone_clearance,
            roads_width=roads_width
        )

        pallets = CargoPacker.pack_cargos(
            cargos=cargos
        )
        solution = PalletPacker.pack_pallets(
            pallets=pallets,
            available_zones=available_zones,
            occupied_zones=occupied_zones,
            special_road_zones=road_zones,
            reference_book=reference_book
        )

        if check_if_debugger_is_active():
            visualize_solution(solution)

        response = generate_output(
            solution=solution,
            reference_book=reference_book,
            task_id=message['task_id'],
            warnings_and_errors='',
            success_predict=True
        )

    except Exception:
        print(traceback.format_exc())
        output_message = {
            'task_id': message['task_id'],
            'racks': {},
            'warnings_and_errors':  traceback.format_exc(),
            'success_predict': False
        }
        sender.send(output_message)
        return

    sender.send(response.model_dump(mode='json'))
    print('Results sent')
    print()
    print(response.model_dump())


def process_message_print(message: Any, sender: Sender):
    """Process message from the queue.

    Args:
        message (Any): message to process
        sender (Sender): sender to send the results
    """
    print('Got Message')
    print(message)
