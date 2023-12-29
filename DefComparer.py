import lxml.etree as ET
from PatchGenerator import PatchOperation

comp_list: int = 0
nesting_list: list[str] = []

def is_in(defName_NamePair: tuple[str, str], dictionary: dict[tuple[str, str], ET._Element]) -> bool:
	"""Check if the given defName_NamePair is in the dictionary"""
	if defName_NamePair in dictionary.keys():
		return True
	# defName is empty (Abstract Def) and Name Attribute is the same
	if defName_NamePair[0] == '' and defName_NamePair[1] in [x[1] for x in dictionary.keys()]:
		return True
	# defName is the same
	if defName_NamePair[0] != '' and defName_NamePair[0] in [x[0] for x in dictionary.keys()]:
		return True
	return False

def generate_xpath(elem: ET._Element) -> str:
	result: str = ""
	assertion: str = None
	elemiter = elem
	while elemiter is not None:
		if 'Def' in elemiter.tag:
			if 'Abstract' in elemiter.attrib and 'Name' in elemiter.attrib:
				assertion = f'@Name="{elemiter.attrib["Name"]}"'
			elif elemiter.find('./defName') is not None:
				assertion = f'defName="{elemiter.find("./defName").text}"'
		result = elemiter.tag + '/' + result
		elemiter = elemiter.getparent()
	if assertion is not None:
		assertion = '[' + assertion + ']'
	result = result.removesuffix('/')
	List = result.split('/')
	if assertion is not None:
		List[1] = List[1] + assertion
	result = '/'.join(List)
	return result

def _compare_attribute(left: ET._Element, right: ET._Element) -> bool | dict[str, str]:
	result = {}
	for key, value in right.attrib.items():
		if key not in left.attrib:
			result[key] = value + ' -> ' + 'None' 
		elif value != left.attrib[key]:
			result[key] = right.attrib[key] + ' -> ' + value
	if result != {}:
		return result
	return True

def _compare_list(left: ET._Element, right: ET._Element) -> (list[str], list[str]):
	"""Returns two lists, the first one need a PatchOperationAdd, while the second one need a PatchOperationRemove"""
	# Iterate throught left element's children and find if it exists in right element's children
	# _Element has a __iter__ method that returns an iterator of its children
	DLeft = [x.text for x in list(left) if isinstance(x, ET._Element)]
	DRight = [x.text for x in list(right) if isinstance(x, ET._Element)]
	addList = set(DLeft) - set(DRight)
	removeList = set(DRight) - set(DLeft)
	return (addList, removeList)

def _compare_text(left: ET._Element, right: ET._Element) -> bool:
	"""Only returns False when both are leaf node and the text is different"""
	if left.__len__() != 0 or right.__len__() != 0:
		return True
	return left.text == right.text

def _compare_recursive(left: ET._Element, right: ET._Element) -> list[ET._Element]:
	global comp_list
	"""Compare two elements recursively\n When encountering a difference other than attribute, it will return a list of PatchOperation"""
	Operations = []
	# Compare attributes
	attr_result = _compare_attribute(left, right)
	if isinstance(attr_result, dict):
		for attrName in attr_result.keys():
			attrValue = attr_result[attrName].split(' -> ')[1]
			xpath = generate_xpath(left)
			patchclass = 'PatchOperationAttributeSet'
			Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=attrValue, attribute=attrName))
			#log('\n' + right.tag + attr_result.__str__() + '\n\n')
	# Compare text
	if not _compare_text(left, right):
		# Add PatchOperationReplace
		patchclass = 'PatchOperationReplace'
		xpath = generate_xpath(left)
		if left.tag == 'li':
			item_node = ET.Element('li')
			item_node.text = left.text
			xpath += f'[text()="{right.text}"]'
			Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=item_node))
		else:
			Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=left.text))
	# Compare children only when their children's tag is not li and their <li> child don't have children
	if (left.find('./li') != None and right.find('./li') != None) and \
	all(x.__len__() == 0 for x in list(left.findall('./li'))) and \
	all(x.__len__() == 0 for x in list(right.findall('./li'))):
		comp_list += 1
		add_list, remove_list = _compare_list(left, right)
		for item in add_list:
			# Add PatchOperationAdd
			patchclass = 'PatchOperationAdd'
			xpath = generate_xpath(right)
			item_node = ET.Element('li')
			item_node.text = item
			Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=item_node))
		for item in remove_list:
			# Add PatchOperationRemove
			patchclass = 'PatchOperationRemove'
			# need to find the exact node. .../li[text()="item"]
			xpath = generate_xpath(right) + f'/li[text()="{item}"]'
			# PatchOpeartionRemove doesn't need value
			Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath))

	# They are List<T> type
	elif (left.find('./li') != None and right.find('./li') != None) and \
	any(x.__len__() != 0 for x in list(left.findall('./li'))) and \
	any(x.__len__() != 0 for x in list(right.findall('./li'))):
		print(f'Nesting <li> detected. {generate_xpath(left)}\n We do not support this yet. Replacing the whole node with the left one.')
		# Add PatchOperationReplace
		patchclass = 'PatchOperationReplace'
		xpath = generate_xpath(right)
		Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=left))

	# Normal case
	else:
		# recursively compare children
		left_children = {x.tag : x for x in list(left) if not isinstance(x, ET._Comment)}
		right_children = {x.tag : x for x in list(right) if not isinstance(x, ET._Comment)}

		for tag in set(left_children.keys()) & set(right_children.keys()):
			Operations = Operations + _compare_recursive(left_children[tag], right_children[tag])
		# not in right but in left
		for tag in set(left_children.keys()) - set(right_children.keys()):
			# Add PatchOperationAdd
			patchclass = 'PatchOperationAdd'
			xpath = generate_xpath(left_children[tag].getparent())
			Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=left_children[tag]))
		for tag in set(right_children.keys()) - set(left_children.keys()):
			# Add PatchOperationRemove
			#print(type(node))
			patchclass = 'PatchOperationRemove'
			xpath = generate_xpath(right_children[tag])
			Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath))
	return Operations


def compare_root(left : ET._ElementTree, right: ET._ElementTree) -> list[ET._Element]:
	"""Compare two root trees. Their root element must be <Defs>"""
	result: list[ET._Element] = []
	if left.getroot().tag != 'Defs' or right.getroot().tag != 'Defs':
		raise ValueError('Root element must be <Defs>')
	# Create two dicts to store all elements
	# key -> (Element.find('./defName'), Element.get('Name')), value -> Element
	left_dict: dict[tuple[str, str], ET._Element] = {}
	right_dict: dict[tuple[str, str], ET._Element] = {}

	for item in left.getroot():
		if isinstance(item, ET._Comment):
			continue
		key = (item.find('./defName').text if item.find('./defName') is not None else '', item.get('Name'))
		left_dict[key] = item
	for item in right.getroot():
		if isinstance(item, ET._Comment):
			continue
		key = (item.find('./defName').text if item.find('./defName') is not None else '', item.get('Name'))
		right_dict[key] = item
	
	# Compare two dicts
	for item in list(left_dict.keys()):
		# only defName, only Name or both
		if is_in(item, right_dict):
		# Compare two elements
			# defName and Name are identical
			if item in right_dict.keys():
				Operations = _compare_recursive(left_dict[item], right_dict[item])
			# only Name is identical and defName is None(Abstract Def)
			elif item[0] == '' and item[1] in [x[1] for x in right_dict.keys()]:
				Operations = _compare_recursive(left_dict[item], right_dict[('', item[1])])
			# only defName is identical, and Name is None
			else:
				if any(x for x in right_dict.keys() if x[0] == item[0] and x[1] == None):
					key = next(x for x in right_dict.keys() if x[0] == item[0] and x[1] == None)
					Operations = _compare_recursive(left_dict[item], right_dict[key])
			if Operations != []:
				result = result + Operations
	
	for item in list(left_dict.keys()):
		if not is_in(item, right_dict):
			# Add PatchOperationAdd
			patchclass = 'PatchOperationAdd'
			xpath = generate_xpath(left_dict[item].getparent())
			result.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=left_dict[item]))
	
	for item in list(right_dict.keys()):
		if not is_in(item, left_dict):
			# Add PatchOperationRemove
			patchclass = 'PatchOperationRemove'
			xpath = generate_xpath(right_dict[item])
			result.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath))
	print(comp_list)
	return result


if __name__ == "__main__":
	left = ET.parse('./test.xml')
	right = ET.parse('./test2.xml')
	result = compare_root(left, right)
	# print(result)
	PatchOperation.write_all_operations('./result.xml', result)
