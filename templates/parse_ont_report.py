#! /usr/bin/env python3

# a program to parse the output of ont report and extract the relevant information

import ast
import csv
import sys
import json


def search_list(lst, key):
    for item in lst:
        if key in item:
            return item
    return None


def parse_barcodes(barcode_str):
    value = barcode_str.split('=')[1].strip()

    try:
        # Safely evaluate the string to a Python object
        barcodes = ast.literal_eval(value)
        return barcodes

    except (ValueError, SyntaxError) as e:
        print(f"Error parsing barcodes: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: parse_ont_report.py <ont_report.json>")
        sys.exit(1)

    ont_report_file = sys.argv[1]

    with open(ont_report_file, 'r') as f:
        ont_report = json.load(f)

    # Extract relevant information from the ont report
    protocol_run_info = ont_report.get('protocol_run_info', {})
    args = protocol_run_info.get('args', [])
    barcoding_kits = parse_barcodes(search_list(args, 'barcoding_kits'))
    user_info = protocol_run_info.get('user_info', {})
    protocol_group_id = user_info.get('protocol_group_id', 'Unknown')
    user_specified_flow_cell_id = user_info.get('user_specified_flow_cell_id', 'Unknown')

    # Print the extracted information
    print(f"Barcoding Kits Used: {', '.join(barcoding_kits) if barcoding_kits else 'None'}")
    print(f"Protocol Group ID: {protocol_group_id}")
    print(f"User Specified Flow Cell ID: {user_specified_flow_cell_id}")
    print("\n============================================================")
    print("Add this to sample sheet:\n")

    writer = csv.writer(sys.stdout, delimiter=',', lineterminator='\n')
    writer.writerow(["experiment_id", "kit", "flow_cell_id", "barcode", "alias"])
    writer.writerow([
        protocol_group_id,
        ', '.join(barcoding_kits) if barcoding_kits else 'None',
        user_specified_flow_cell_id,
        None,
        None
    ])