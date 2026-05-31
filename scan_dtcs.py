import xml.etree.ElementTree as ET
import argparse
from utils import load_messages, load_collections, collections
from data_types import Module
from connection import EcuConnection
from selection import select_ecu_element, set_prefilled_selects

def load_arguments():
    parser = argparse.ArgumentParser(description='Scan DTCs from a Hyundai ECU')
    parser.add_argument('-i', '--interactive-select', nargs='*', help='Prefill selections with indices', type=int, metavar='N')
    parser.add_argument('-k', '--kia', help='Use KIA vehicles', action='store_true')
    parser.add_argument('--interface', default='can0', help='CAN interface name (default: can0)')
    return parser.parse_args()

def resolve_dtc_descriptions(dtcs, module):
    dtc_table = collections.get('dtc', {})
    module_dtcs = {}
    
    for module_dtc in module.dtcs:
        module_dtcs[module_dtc.header] = module_dtc.index
    
    for dtc in dtcs:
        if dtc.description is not None:
            continue 
        if dtc.header in module_dtcs:
            dtc.index = module_dtcs[dtc.header]
        try:
            dtc.description = dtc_table[dtc.index]
        # Try suffixed variants
        except (KeyError):
            for key, desc in dtc_table.items():
                if key.startswith(dtc.header + '-'):
                    dtc.description = desc
                    break
    return dtcs

def main():
    args = load_arguments()
    if args.interactive_select:
       set_prefilled_selects(args.interactive_select)

    print('Loading definitions...')
    load_messages('decrypted_xef/add-ENG.xml')
    load_messages('decrypted_xef/keyvalue.xml')
    load_messages('decrypted_xef/keyvalueUnit.xml')
    load_collections('decrypted_xef/dtc-ENG.xml')

    ecu_element = select_ecu_element(args.kia)
    if ecu_element is None:
        print('[!] Failed to load ECU definition')
        return

    module = Module.from_xml(ecu_element)

    print(f'\nConnecting to {module.system_id}...')
    connection = EcuConnection(module, interface=args.interface)
    try:
        connection.connect()
        print('Reading DTCs...')
        dtcs = connection.read_dtcs()
        dtcs_with_descriptions = resolve_dtc_descriptions(dtcs, module)

        print(f'\n{len(dtcs)} DTC(s) found:')
        for dtc in dtcs_with_descriptions:
            print(f'  {dtc.header}: {dtc.description or "(unknown code)"}')

    finally:
        connection.disconnect()

if __name__ == '__main__':
    main()