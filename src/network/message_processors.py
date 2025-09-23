import traceback
import logging
import time
import uuid
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


async def process_message_ml(message: Any, sender: Sender):
    """Process message from the queue.

    Args:
        message (Any): message to process
        sender (Sender): sender to send the results
    """
    # Инициализация логгера и метрик
    process_id = str(uuid.uuid4())[:8]
    logger = logging.getLogger(f"process_ml[{process_id}]")
    start_time = time.time()
    
    task_id = message.get('task_id', 'unknown') if isinstance(message, dict) else 'unknown'
    logger.info(f"Starting ML processing for task: {task_id}")
    logger.info(f"Message size: {len(str(message))} characters")
    
    available_zones: list[AvailableZone] = []
    occupied_zones: list[OccupiedZone] = []
    road_zones: list[SpecialRoadZone] = []
    cargos: list[CargoType] = []

    logger.info(f"Printing received message...")
    print('Message received')
    print()
    print(message)

    try:
        # input data validation
        logger.info(f"Starting input data validation...")
        validation_start = time.time()
        ModelInput(**message)
        validation_time = time.time() - validation_start
        logger.info(f"Input validation completed in {validation_time:.3f}s")

        # Processing available zones
        logger.info(f"Processing available zones...")
        zones_start = time.time()
        available_zones_count = len(message['available_zones'])
        logger.info(f"Found {available_zones_count} available zones to process")
        
        for i, zone in enumerate(message['available_zones']):
            logger.debug(f"Processing available zone {i+1}/{available_zones_count}")
            available_zones.append(AvailableZone(zone['boundary'],
                                                 zone['height'],
                                                 zone['orientation']))
        
        zones_time = time.time() - zones_start
        logger.info(f"Available zones processed in {zones_time:.3f}s")

        # Processing road zones
        logger.info(f"Processing road zones...")
        road_zones_start = time.time()
        road_zones_count = len(message['road_zones'])
        logger.info(f"Found {road_zones_count} road zones to process")
        
        for i, zone in enumerate(message['road_zones']):
            logger.debug(f"Processing road zone {i+1}/{road_zones_count}")
            road_zones.append(SpecialRoadZone(zone['line'],
                                              zone['width']))
        
        road_zones_time = time.time() - road_zones_start
        logger.info(f"Road zones processed in {road_zones_time:.3f}s")

        # Processing restricted zones
        logger.info(f"Processing restricted zones...")
        restricted_zones_start = time.time()
        restricted_zones_count = len(message['restricted_zones'])
        logger.info(f"Found {restricted_zones_count} restricted zones to process")
        
        for i, zone in enumerate(message['restricted_zones']):
            logger.debug(f"Processing restricted zone {i+1}/{restricted_zones_count}")
            occupied_zones.append(OccupiedZone(zone['boundary'],
                                               zone['clearance']))
        
        restricted_zones_time = time.time() - restricted_zones_start
        logger.info(f"Restricted zones processed in {restricted_zones_time:.3f}s")

        # Processing cargos
        logger.info(f"Processing cargos...")
        cargos_start = time.time()
        cargos_count = len(message['cargos'])
        total_cargo_quantity = sum(cargo['quantity'] for cargo in message['cargos'])
        logger.info(f"Found {cargos_count} cargo types with total quantity: {total_cargo_quantity}")
        
        for i, rack_section in enumerate(message['cargos']):
            logger.debug(f"Processing cargo {i+1}/{cargos_count}: ID={rack_section['id']}, "
                        f"quantity={rack_section['quantity']}")
            cargos.append(CargoType(
                cargo_type_id=rack_section['id'],
                weight=rack_section['weight'],
                length=rack_section['length'],
                width=rack_section['width'],
                height=rack_section['height'],
                quantity=rack_section['quantity']
            ))
        
        cargos_time = time.time() - cargos_start
        logger.info(f"Cargos processed in {cargos_time:.3f}s")

        # Processing reference data
        logger.info(f"Setting up reference book...")
        ref_start = time.time()
        roads_width = message['roads_width']
        roads_height = message['roads_height']
        file_id = message['file_id']
        logger.info(f"File ID: {file_id}, roads_width: {roads_width}, roads_height: {roads_height}")

        reference_book = ReferenceBook()

        if roads_width is not None:
            reference_book.roads_width = roads_width
            logger.debug(f"Set roads_width to {roads_width}")
        if roads_height is not None:
            reference_book.roads_height = roads_height
            logger.debug(f"Set roads_height to {roads_height}")
        
        ref_time = time.time() - ref_start
        logger.info(f"Reference book setup completed in {ref_time:.3f}s")

        # Getting DXF document from S3
        logger.info(f"Fetching DXF document from S3...")
        s3_start = time.time()
        doc = get_dxf_doc_from_s3(file_id)
        s3_time = time.time() - s3_start
        logger.info(f"DXF document fetched from S3 in {s3_time:.3f}s")

        # Scanning for occupied zones
        logger.info(f"Starting occupied zones scan...")
        scan_start = time.time()
        initial_occupied_count = len(occupied_zones)
        logger.info(f"Initial occupied zones count: {initial_occupied_count}")
        
        occupied_zones += scan_for_occupied_zones(
            doc=doc,
            available_zones=available_zones,
            occupied_zone_clearance=reference_book.forbidden_zone_clearance,
            roads_width=roads_width
        )
        
        scan_time = time.time() - scan_start
        final_occupied_count = len(occupied_zones)
        new_occupied_zones = final_occupied_count - initial_occupied_count
        logger.info(f"Occupied zones scan completed in {scan_time:.3f}s")
        logger.info(f"Found {new_occupied_zones} additional occupied zones (total: {final_occupied_count})")

        # Packing cargos into pallets
        logger.info(f"Starting cargo packing...")
        cargo_pack_start = time.time()
        logger.info(f"Packing {len(cargos)} cargo types into pallets...")
        
        pallets = CargoPacker.pack_cargos(
            cargos=cargos
        )
        
        cargo_pack_time = time.time() - cargo_pack_start
        pallets_count = len(pallets) if pallets else 0
        logger.info(f"Cargo packing completed in {cargo_pack_time:.3f}s")
        logger.info(f"Generated {pallets_count} pallets from {len(cargos)} cargo types")

        # Packing pallets into solution
        logger.info(f"Starting pallet packing...")
        pallet_pack_start = time.time()
        logger.info(f"Packing {pallets_count} pallets into available zones...")
        logger.info(f"Available zones: {len(available_zones)}, Occupied zones: {len(occupied_zones)}, "
                   f"Road zones: {len(road_zones)}")
        
        solution = PalletPacker.pack_pallets(
            pallets=pallets,
            available_zones=available_zones,
            occupied_zones=occupied_zones,
            special_road_zones=road_zones,
            reference_book=reference_book
        )
        
        pallet_pack_time = time.time() - pallet_pack_start
        logger.info(f"Pallet packing completed in {pallet_pack_time:.3f}s")

        # Checking for debugger and visualization
        logger.info(f"Checking debugger status...")
        debug_check_start = time.time()
        is_debug = check_if_debugger_is_active()
        debug_check_time = time.time() - debug_check_start
        logger.info(f"Debugger check completed in {debug_check_time:.3f}s, active: {is_debug}")
        
        if is_debug:
            logger.info(f"Starting solution visualization...")
            viz_start = time.time()
            visualize_solution(solution)
            viz_time = time.time() - viz_start
            logger.info(f"Solution visualization completed in {viz_time:.3f}s")

        # Generating output
        logger.info(f"Generating output response...")
        output_start = time.time()
        
        response = generate_output(
            solution=solution,
            reference_book=reference_book,
            task_id=message['task_id'],
            warnings_and_errors='',
            success_predict=True
        )
        
        output_time = time.time() - output_start
        logger.info(f"Output generation completed in {output_time:.3f}s")

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"Exception occurred after {error_time:.3f}s during ML processing: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.exception("Full exception traceback:")
        
        print(traceback.format_exc())
        
        logger.info(f"Generating error response...")
        error_response_start = time.time()
        output_message = {
            'task_id': message['task_id'],
            'racks': {},
            'warnings_and_errors': traceback.format_exc(),
            'success_predict': False
        }
        
        logger.info(f"Sending error response...")
        await sender.send(output_message)
        
        error_response_time = time.time() - error_response_start
        total_error_time = time.time() - start_time
        logger.info(f"Error response sent in {error_response_time:.3f}s")
        logger.info(f"Total error processing time: {total_error_time:.3f}s")
        return

    # Sending successful response
    logger.info(f"Sending successful response...")
    response_send_start = time.time()
    
    response_data = response.model_dump(mode='json')
    response_size = len(str(response_data))
    logger.info(f"Response data size: {response_size} characters")
    
    await sender.send(response_data)
    
    response_send_time = time.time() - response_send_start
    total_processing_time = time.time() - start_time
    
    logger.info(f"Response sent successfully in {response_send_time:.3f}s")
    logger.info(f"Total ML processing time: {total_processing_time:.3f}s")
    
    logger.info(f"Printing results...")
    print('Results sent')
    print()
    print(response.model_dump())
    
    # Final statistics
    logger.info(f"=" * 50)
    logger.info(f"ML Processing Summary for task: {task_id}")
    logger.info(f"Total time: {total_processing_time:.3f}s")
    logger.info(f"Processed {len(cargos)} cargo types -> {pallets_count} pallets")
    logger.info(f"Used {len(available_zones)} available zones, {len(occupied_zones)} occupied zones")
    logger.info(f"Success: True")
    logger.info(f"=" * 50)


def process_message_print(message: Any, sender: Sender):
    """Process message from the queue.

    Args:
        message (Any): message to process
        sender (Sender): sender to send the results
    """
    # Инициализация логгера
    process_id = str(uuid.uuid4())[:8]
    logger = logging.getLogger(f"process_print[{process_id}]")
    start_time = time.time()
    
    task_id = message.get('task_id', 'unknown') if isinstance(message, dict) else 'unknown'
    logger.info(f"Starting Print processing for task: {task_id}")
    logger.info(f"Message type: {type(message)}")
    logger.info(f"Message size: {len(str(message))} characters")
    
    logger.info(f"Printing message to console...")
    print_start = time.time()
    
    print('Got Message')
    print(message)
    
    print_time = time.time() - print_start
    total_time = time.time() - start_time
    
    logger.info(f"Message printed to console in {print_time:.3f}s")
    logger.info(f"Total print processing time: {total_time:.3f}s")
    
    logger.info(f"=" * 50)
    logger.info(f"Print Processing Summary for task: {task_id}")
    logger.info(f"Total time: {total_time:.3f}s")
    logger.info(f"Message successfully printed to console")
    logger.info(f"=" * 50)