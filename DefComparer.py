import lxml.etree
from PatchGenerator import PatchOperation
from Compare import _log, generate_xpath_newtemp



def _compare_attribute(left: lxml.etree._Element, right: lxml.etree._Element) -> bool | dict[str, str]:
	result = {}
	for key, value in left.attrib.items():
		if key not in right.attrib:
			result[key] = value + ' -> ' + 'None' 
		elif value != right.attrib[key]:
			result[key] = right.attrib[key] + ' -> ' + value
	if result != {}:
		return result
	return True

def _compare_list(left: lxml.etree._Element, right: lxml.etree._Element) -> (list[str], list[str]):
	"""Returns two lists, the first one need a PatchOperationAdd, while the second one need a PatchOperationRemove"""
	# Iterate throught left element's children and find if it exists in right element's children
	# _Element has a __iter__ method that returns an iterator of its children
	DLeft = [x.text for x in list(left) if isinstance(x, lxml.etree._Element)]
	DRight = [x.text for x in list(right) if isinstance(x, lxml.etree._Element)]
	addList = set(DLeft) - set(DRight)
	removeList = set(DRight) - set(DLeft)
	return (addList, removeList)

def _compare_text(left: lxml.etree._Element, right: lxml.etree._Element) -> bool:
	"""Only returns False when both are leaf node and the text is different"""
	if left.__len__() != 0 or right.__len__() != 0:
		return True
	return left.text == right.text

def _compare_recursive(left: lxml.etree._Element, right: lxml.etree._Element) -> list[PatchOperation]:
	"""Compare two elements recursively\n When encountering a difference other than attribute, it will return a list of PatchOperation"""
	Operations = []
	# Compare attributes
	attr_result = _compare_attribute(left, right)
	if isinstance(attr_result, dict):
		for attrName in attr_result.keys():
			attrValue = attr_result[attrName].split(' -> ')[1]
			xpath = generate_xpath_newtemp(left)
			patchclass = 'PatchOperationAttributeSet'
			Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=attrValue, attribute=attrName))
			#log('\n' + right.tag + attr_result.__str__() + '\n\n')
	# Compare text
	if not _compare_text(left, right):
		# Add PatchOperationReplace
		patchclass = 'PatchOperationReplace'
		xpath = generate_xpath_newtemp(left.getparent())
	# Compare children only when their children's tag is not li
	if left.find('./li') != None or right.find('./li') != None:
		add_list, remove_list = _compare_list(left, right)
		for item in add_list:
			# Add PatchOperationAdd
			patchclass = 'PatchOperationAdd'
			xpath = generate_xpath_newtemp(right)
			Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=item))
		for item in remove_list:
			# Add PatchOperationRemove
			patchclass = 'PatchOperationRemove'
			# need to find the exact node. .../li[text()="item"]
			xpath = generate_xpath_newtemp(right) + f'[text()="{item}"]'
			# PatchOpeartionRemove doesn't need value
			Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath))
	else:
		# recursively compare children
		left_children = {x.tag : x for x in list(left) if not isinstance(x, lxml.etree._Comment)}
		right_children = {x.tag : x for x in list(right) if not isinstance(x, lxml.etree._Comment)}

		# & won't work even if the two sets have the "same" elements
		for tag in left_children.keys() & right_children.keys():
			Operations = Operations + _compare_recursive(left_children[tag], right_children[tag])
		# not in right but in left
		for tag in left_children.keys() - right_children.keys():
			# Add PatchOperationAdd
			patchclass = 'PatchOperationAdd'
			xpath = generate_xpath_newtemp(left_children[tag].getparent())
			Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=left_children[tag]))
		for tag in right_children.keys() - left_children.keys():
			# Add PatchOperationRemove
			#print(type(node))
			patchclass = 'PatchOperationRemove'
			xpath = generate_xpath_newtemp(right_children[tag])
			Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath))
	return Operations


def compare_root(left : lxml.etree._ElementTree, right: lxml.etree._ElementTree) -> list[PatchOperation]:
	"""Compare two root trees. Their root element must be <Defs>"""
	result: list[PatchOperation] = []
	if left.getroot().tag != 'Defs' or right.getroot().tag != 'Defs':
		raise ValueError('Root element must be <Defs>')
	# Create two dicts to store all elements
	# key -> (Element.find('./defName'), Element.get('Name')), value -> Element
	left_dict: dict[tuple[str, str], lxml.etree._Element] = {}
	right_dict: dict[tuple[str, str], lxml.etree._Element] = {}

	for item in left.getroot():
		if isinstance(item, lxml.etree._Comment) or item.tag == 'RecipeDef':
			continue
		key = (item.find('./defName').text if item.find('./defName') is not None else '', item.get('Name'))
		left_dict[key] = item
	for item in right.getroot():
		if isinstance(item, lxml.etree._Comment) or item.tag == 'RecipeDef':
			continue
		key = (item.find('./defName').text if item.find('./defName') is not None else '', item.get('Name'))
		right_dict[key] = item

	# Compare two dicts
	for item in left_dict.keys() & right_dict.keys():
		# Compare two elements
		Operations = _compare_recursive(left_dict[item], right_dict[item])
		if Operations != []:
			result = result + Operations
	return result


if __name__ == "__main__":
	left = lxml.etree.parse('./test.xml')
	right = lxml.etree.parse('./test2.xml')
	result = compare_root(left, right)
	# print(result)
	PatchOperation.write_all_operations('./result.xml', result)
