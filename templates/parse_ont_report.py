#! /usr/bin/env python3

# a program to parse the output of ont report and extract the relevant information

import ast
import csv
import sys
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def search_list(lst, key):
    for item in lst:
        if key in item:
            return item
    return None


def parse_barcodes(barcode_str):
    try:
        value = barcode_str.split('=')[1].strip()

    except AttributeError as e:
        logging.debug(f"Barcode string not found: {e}")
        logging.warning("No barcoding kits were used in this run. Check the report for more details")
        return None

    try:
        # Safely evaluate the string to a Python object
        barcodes = ast.literal_eval(value)
        return barcodes

    except (ValueError, SyntaxError) as e:
        logging.error(f"Error parsing barcodes: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        logging.error("Usage: parse_ont_report.py <ont_report.json>")
        sys.exit(1)

    ont_report_file = sys.argv[1]
    logging.info(f"Reading ONT report from: {ont_report_file}")

    try:
        with open(ont_report_file, 'r') as f:
            ont_report = json.load(f)
    except FileNotFoundError:
        logging.error(f"File not found: {ont_report_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON format in {ont_report_file}: {e}")
        sys.exit(1)

    # Extract relevant information from the ont report
    protocol_run_info = ont_report.get('protocol_run_info', {})
    args = protocol_run_info.get('args', [])

    # check if barcoding_kits is in the args list and parse it
    barcoding_kits = parse_barcodes(search_list(args, 'barcoding_kits'))

    if not barcoding_kits:
        raise RuntimeError("No barcoding kits were used in this run. Check the report for more details")

    user_info = protocol_run_info.get('user_info', {})
    protocol_group_id = user_info.get('protocol_group_id', 'Unknown')
    user_specified_flow_cell_id = user_info.get('user_specified_flow_cell_id', 'Unknown')

    # Log the extracted information
    logging.info(f"Protocol Group ID: {protocol_group_id}")
    logging.info(f"User Specified Flow Cell ID: {user_specified_flow_cell_id}")
    logging.info(f"Barcoding Kits Used: {', '.join(barcoding_kits) if barcoding_kits else 'None'}")
    logging.info("============================================================")
    logging.info("Use this as a starting point for samplesheet:\n")

    writer = csv.writer(sys.stdout, delimiter=',', lineterminator='\n')
    writer.writerow(["experiment_id", "kit", "flow_cell_id", "barcode", "alias"])
    writer.writerow([
        protocol_group_id,
        ', '.join(barcoding_kits) if barcoding_kits else 'None',
        user_specified_flow_cell_id,
        None,
        None
    ])