
import xml.etree.ElementTree as ET
import glob, os

prefilled_interactive_selects = []

def set_prefilled_selects(selects: list[int]) -> None:
    global prefilled_interactive_selects
    prefilled_interactive_selects = selects

def interactive_select(table, prompt):
    if len(prefilled_interactive_selects) > 0:
        index = int(prefilled_interactive_selects.pop(0))
        print(f'Prefilled: {index}')
        return table[index]
    try:
        return table[int(input(prompt))]
    except (KeyError, IndexError, ValueError):
        print('Invalid choice! Try again')
        return interactive_select(table, prompt)


def load_vehicles(use_kia: bool):
    path = 'decrypted_xef/vehiclesdata_KME.xml' if use_kia else 'decrypted_xef/vehiclesdata_HME.xml'
    tree = ET.parse(path)
    return list(tree.getroot())

def select_ecu_element(use_kia: bool):
    """Walk user through vehicle/year/engine/system selection.
    Returns the ECU XML element for the chosen module."""

    print('loading vehicles..')

    vehicles = load_vehicles(use_kia)

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
        else:
            return ecu_element

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