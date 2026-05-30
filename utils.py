import xml.etree.ElementTree as ET

messages = {}
collections = {}

def _get (xml, param: str, default = None, cast_to = None, cast_args: tuple = None) -> str | None:
	value = xml.get(param, default)
	
	if value == '':
		return default

	if cast_to:
		try:
			value = cast_to(value, *cast_args)
		except (TypeError, ValueError) as e:
			value = None
	
	return value

def get_lookup_table (identifier: int) -> list|None:
	lut_filenames = [f'Lut/{identifier}.lut', f'Lut/{identifier}.LUT'] # consistency [cool]
	values = []

	for lut_filename in lut_filenames:
		try:
			with open(lut_filename, 'r') as f:
				for value in f.readlines():
					values.append(value.lstrip().rstrip())
			return values
		except FileNotFoundError:
			pass
	return None

def get_message (key: int, attribute: str = None):
	try:
		return messages[attribute][key]
	except KeyError:
		return ''

def get_from_collection (key: str, collection_name: str = 'currentdata'):
	try:
		return collections[collection_name][key]
	except KeyError:
		return ''
	

def load_messages (dataset: str):
	tree = ET.parse(dataset).getroot()
	for keyvalue in tree:
		if keyvalue.attrib['attr'] not in messages:
			messages[keyvalue.attrib['attr']] = {}
		messages[keyvalue.attrib['attr']][keyvalue.attrib['key']] = keyvalue.attrib['desc']

def load_collections (dataset: str):
	tree = ET.parse(dataset).getroot()

	for collection in tree:
		collections[collection.tag] = {}
		for keyvalue in collection:
			collections[collection.tag][keyvalue.attrib['key']] = keyvalue.attrib['desc']
