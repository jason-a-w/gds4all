import xml.etree.ElementTree as ET
import sys, glob, os, textwrap, argparse
from data_types import Module
from utils import _get, get_from_collection, get_message, load_collections, load_messages
# used for debugging. set sys.argv to, say, 26, 3, 1. 
# a 2006 2.0 tiburon will be selected: vehicle 26, year 3, variant 1
prefilled_interactive_selects = []

TERMINAL_WIDTH = os.get_terminal_size().columns

def _print (*args, indent: int = 0, **kwargs):
	return print(' '*indent, *args, **kwargs)
	
def interactive_select (table, prompt):
	if (len(prefilled_interactive_selects) > 0):
		index = int(prefilled_interactive_selects.pop(0))
		print('Prefilled: {}'.format(index))
		return table[index]

	try:
		return table[int(input(prompt))]
	except (KeyError, IndexError, ValueError):
		print('Invalid choice! Try again')
		return interactive_select(table, prompt)

def load_arguments ():
	parser = argparse.ArgumentParser(description='GDS4ALL - Parser for Hyundai GDS definitions')
	parser.add_argument('-i', '--interactive-select', nargs='*', help='Prefill selections with indices', type=int, metavar='N')
	parser.add_argument('-k', '--kia', help='Use KIA vehicles', action='store_true')
	args = parser.parse_args()
	return args

def load_vehicles ():
	if args.kia:
		tree = ET.parse('decrypted_xef/vehiclesdata_KME.xml')
	else:
		tree = ET.parse('decrypted_xef/vehiclesdata_HME.xml')
	root = tree.getroot()
	vehicles = []

	for child in root:
		vehicles.append(child)

	return vehicles


def load_ecu (ecu_code: str):
	print('Loading ECU code: {}'.format(ecu_code))
	patterns = {'Exact Match': 'decrypted_xef/{}.xml', 
			   'Largest DGN Suffix File': 'decrypted_xef/{}[DGN]0.xml', 
			   'Wildcard': 'decrypted_xef/{}*.xml'}
	for name, pattern in patterns.items():
		files = glob.glob(pattern.format(ecu_code))
		if len(files) == 0:
			continue
		elif len(files) == 1:
			file = files[0]
		else:
			file = max(files, key=lambda file: os.stat(file).st_size)
		try:
			tree = ET.parse(file)
		except ET.ParseError:
			print('File {} was found but failed to parse'.format(file))
			continue
		root = tree.getroot()
		if len(root) == 0:
			print('File {} was found but apparently contains no root'.format(file))
		else:
			print('Loaded ECU using pattern: {}'.format(name))
			return root
	return None

def handle_step (bus, step):
	print('Step #{}'.format(step.attrib['stepno']))
	print(get_message(step.attrib['stepdesc'], attribute='stepdesc'))

	message = step.findall('message')[0]
	if (message.attrib['messageindex'] != '0'):
		print(get_message(message.attrib['messageindex'], attribute='messageindex'))

	keystrings = step.findall('keystring')

	print('\n')
	if (keystrings[0].attrib['type'] != '0'):
		for key, keystring in enumerate(keystrings):
			print('[{}] {}'.format(key, keystring.attrib['filename']))
		keystring = interactive_select(keystrings, '=========\nSelect: ')

		if 'jumpstep' in keystring.attrib:
			return int(keystring.attrib['jumpstep'])

	for request in message.findall('request'):
		for response in request:
			print('    Expected response format: {}\n'.format(response.attrib['responsevalue']))
			print('    We\'re looking for some data with size {}, starting at offset {}'.format(response.attrib['datasize'], response.attrib['startposition']))

			for comcode in response.findall('comcode'):
				operation_name = 'equals to' if comcode.attrib['compare'] == '1' else 'does not equal' 
				print('    - If this data {} {}, then we jump to step {}'.format(operation_name, comcode.attrib['code'], comcode.attrib['jumpstep']))

	return False

def print_module(module, ecu_element):
	print('=== Communication ===')
	_print('{}'.format(module.communication_setup), indent=4)

	print('\n=== This ECU supports the following functions: ===')
	for function_declaration in module.communication_setup.supported_functions:
			_print('- {} ({})'.format(function_declaration.description, function_declaration.index), indent=4)

	_print('\n=== Current data function ===')
	for data_node in [v for k, v in sorted(module.current_data.items())]:
		_print('- {}: ({})'.format(data_node.name, data_node.index), indent=4)
		_print('Payload: {}'.format(data_node.request_payload), indent=8)
		_print('Response format: {}'.format(data_node.response_prefix), indent=8)
		
		if data_node.unit:
			_print('Unit: {}'.format(data_node.unit), indent=8)
		_print('Position: {} Size: {}'.format(data_node.position, data_node.size), indent=8)
		_print('Precision: {}'.format(data_node.decimal_points), indent=8)
		_print('Conversion: {}'.format(data_node.conversion), indent=8)
		print()
	
	print('=== Actuation test function ===')
	for test_node in module.actuation_tests:
		_print(str(test_node), indent=8)

	print('\n=== DTCS: ===')
	for dtc in module.dtcs:
		wrapped = textwrap.wrap(str(dtc), width=TERMINAL_WIDTH - 20)
		for line in wrapped:
			_print(line, indent=8)
	
	# TODO: addfunctions not yet modeled in Module - using raw XML for now
	print('\n=== "addfunction" functions: ===')
	addfunction_functions = ecu_element.findall('addfunction')
	for key, node in enumerate(addfunction_functions):
		_print('[{}] {}'.format(key, get_message(node.get('fuctionindex'), attribute='index')), indent=8)
		_print('{}'.format(get_message(node.get('fuctiondesc'), attribute='fuctiondesc')), indent=12)
		_print('Steps:', indent=12)
		for step in sorted(node.findall('step'), key=lambda s: int(_get(s, 'stepno'))):
			_print('#{} {}'.format(_get(step, 'stepno'), get_message(_get(step, 'stepdesc'), attribute='stepdesc')), indent=16)
			message = step.findall('message')[0]
			if (message.get('messageindex') != '0'):
				message_text = get_message(message.get('messageindex'), attribute='messageindex')
				message_lines = message_text.split('\\n')
				for i, line in enumerate(message_lines):
					try:
						if line == '' and message_lines[i+1] == '':
							continue
					except IndexError:
						pass

					line = line.strip().replace('\n', '')

					for line in textwrap.wrap(line, width=(TERMINAL_WIDTH-20)):
						_print('{}'.format(line), indent=20)

def main(args):
	print('loading messages..')
	load_messages('decrypted_xef/add-ENG.xml')
	load_messages('decrypted_xef/keyvalue.xml')
	load_messages('decrypted_xef/keyvalueUnit.xml') 

	print('loading collections..')
	load_collections('decrypted_xef/dtc-ENG.xml')

	if not os.path.isdir('Lut'):
		print('[!] Lookup table files not found, enum values won\'t be extracted.')
		print('You can find them in the Lut directory in main GDS dir')

	print('loading vehicles..')

	vehicles = load_vehicles()

	for key, vehicle in enumerate(vehicles):
		print('[{}] - {}'.format(key, vehicle.get('modeldesc')))

	vehicle = interactive_select(vehicles, 'Select vehicle: ')
	print('selected vehicle: {}'.format(vehicle.get('modeldesc')))

	# manufacturer, lang, vehicle type, model vin
	vehicle_years = vehicle[0][0][0][0][0]
	
	for key, vehicle_year in enumerate(vehicle_years):
		print('[{}] - {}'.format(key, vehicle_year.get('modelyr')))

	vehicle_variants = interactive_select(vehicle_years, 'Select year: ')

	for key, variant in enumerate(vehicle_variants):
		print('[{}] - {}'.format(key, variant.get('enginedesc')))

	vehicle_systems = interactive_select(vehicle_variants, 'Select engine type: ')

	for key, system in enumerate(vehicle_systems):
		print('\n[{}] - {}'.format(key, system.get('sysitemdesc')))
		print('    {}'.format('/'.join([subsystem.get('syssubitemdesc') for subsystem in system])))

	vehicle_system = interactive_select(vehicle_systems, 'Select system: ')
	
	if (len(vehicle_system) > 1):
		for key, subsystem in enumerate(vehicle_system):
			print('[{}] {}'.format(key, subsystem.get('syssubitemdesc')))
		vehicle_system = interactive_select(vehicle_system, 'Select subsystem: ')
	else:
		vehicle_system = vehicle_system[0]

	print('\n\n\nSelected system: {}'.format(vehicle_system.get('syssubitemdesc')))
	if len(vehicle_system) > 1:
		print('There is more than one ECU assigned to this subsystem: {}'.format(', '.join([ecu.get('ecucode') for ecu in vehicle_system])))

	for ecu_node in vehicle_system:
		ecu_code = ecu_node.attrib['ecucode']
		ecu_element = load_ecu(ecu_code)

		if ecu_element is None:
			print('[!] Failed to load ECU definition: {}'.format(ecu_code))
			continue

		module = Module.from_xml(ecu_element)
		
		
		for dtc in module.dtcs:
			dtc.description = (
				get_from_collection(dtc.index, 'dtc')
				or get_from_collection(dtc.header, 'dtc')
				or 'No description found'
			)
		for sf in module.communication_setup.supported_functions:
			sf.description = get_message(sf.index, attribute='index')
		
	
		print_module(module, ecu_element)

		_stephandlingmethods = '''continue # ACHTUNG!
		selected_function = interactive_select(addfunction_functions, 'Select function: ')

		print('\n\n\n==========')
		print(get_message(selected_function.attrib['fuctiondesc'], attribute='fuctiondesc'))

		function_steps = sorted(selected_function.findall('step'), key=lambda s: int(s.attrib['stepno']))
		next_step_no = handle_step(bus, function_steps[0])
		while next_step_no:
			try:
				next_step = function_steps[next_step_no-1]
				next_step_no = handle_step(bus, next_step)
				if (next_step_no == 0):
					break
			except (IndexError, KeyError):
				break'''

	if (len(vehicle_system) > 1):
		print('[!] Be advised: more than 1 ECU definition was processed and displayed')

if __name__ == '__main__':
	args = load_arguments()
	if args.interactive_select:
		prefilled_interactive_selects = args.interactive_select
	main(args)
