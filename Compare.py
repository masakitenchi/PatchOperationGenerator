from lxml import etree
import os
import argparse
from PatchGenerator import PatchOperation
from file import choose_dir, choose_files

dirname = os.path.split(__file__)[0]
output = open(os.path.join(dirname, "result.txt"), "w", encoding="utf-8")
leftName: str
rightName: str
rootL: etree.Element
rootR: etree.Element
Operations : list[PatchOperation] = []

def generate_xpath(elem: etree.Element, *,  nodeName: str = None, attrName: str = None, attrValue: str = None) -> str:
	result: str = ''
	elemiter = elem.iterancestors()
	for path in elemiter:
		result = path.tag + '/' + result
	result = result.removesuffix('/')
	#print(result.split('/').__str__())
	List = result.split('/')
	index = len(List)
	if(elem.tag.__contains__('Def')):
		if nodeName is not None:
			List.append(f'[defName="{nodeName}"]')
		elif attrName is not None and attrValue is not None:
			List.append(f'[@{attrName}="{attrValue}"]')
	elif nodeName is not None:
		List[1] = List[1] + f'[defName="{nodeName}"]'
	elif attrName is not None and attrValue is not None:
		List[1] = List[1] + f'[@{attrName}="{attrValue}"]'
	result = '/'.join(List) + '/' + elem.tag
	return result

def CompareAttr(left: etree.Element, right: etree.Element) -> bool | dict[str, str]:
	result = {}
	for key, value in left.attrib.items():
		if key not in right.attrib:
			result[key] = 'None ->' + value
		elif value != right.attrib[key]:
			result[key] = value + ' -> ' + right.attrib[key]
	if result != {}:
		return result
	return True


def CreateDict(elem: etree.Element) -> dict[str, list[etree.Element]]:
	SubNodeList = set([x.tag for x in elem.findall("./*")])
	if len(SubNodeList) == 0:
		return {}
	SubNodeDict = {}
	for NodeName in SubNodeList:
		SubNodeDict[NodeName] = elem.findall(f"./{NodeName}")
	return SubNodeDict


def CompareInt(
	left: etree.Element, right: etree.Element, *, defType: str = None, defName: str = None, attrName: str = None, attrValue: str = None
) -> None:
	# if the element has attribute then run CompareAttr
	if left.attrib != {} and right.attrib != {}:
		attrResult = CompareAttr(left, right)
		if isinstance(attrResult, dict):
			xpath = generate_xpath(left, attrName=attrName, attrValue=attrValue)
			patchclass = 'PatchOperationAttributeSet'
			Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=attrResult, attribute=attrName))
			output.write('\n' + right.tag + attrResult.__str__() + '\n\n')
	DL = CreateDict(left)
	DR = CreateDict(right)
	for NodeName in DL.keys():
		for Node in DL[NodeName]:
			tag = Node.tag
			if NodeName in DR.keys() and Node.__len__() == 0:
				""" attrresult = CompareAttr(Node, DR[NodeName][0])
				if isinstance(attrresult, dict):
					xpath = generate_xpath(Node, attrName=attrName, attrValue=attrValue)
					patchclass = 'PatchOperationAttributeSet'
					Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=attrresult, attribute=attrName))
					output.write('\n' + right.tag + attrresult.__str__() + '\n\n') """
				if DR[NodeName][0].text == Node.text:
					continue
				else:
					if defType is not None and defName is not None:
						xpath = generate_xpath(Node, nodeName=defName)
						patchclass = 'PatchOperationReplace'
						Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=Node.text))
						output.write(
							f'{rightName} has different {Node.tag} in {defType}.{defName}. "{Node.text}" -> "{DR[NodeName][0].text}"\n'
						)
						output.write(f'\txpath: {xpath}\n')
					else:
						xpath = generate_xpath(Node, attrName=attrName, attrValue=attrValue)
						patchclass = 'PatchOperationReplace'
						Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=Node.text, attribute=attrName))
						output.write(
							f'{rightName} has different {Node.tag} in {attrName} = {attrValue}. "{Node.text}" -> "{DR[NodeName][0].text}"\n'
						)
						output.write(f'\txpath: {xpath}\n')
			elif NodeName not in DR.keys():
				if defType is not None and defName is not None:
					xpath = generate_xpath(Node, nodeName=defName)
					# Add to the parent node
					#print(type(Node))
					xpath = xpath.removesuffix('/' + xpath.split('/').pop())
					patchclass = 'PatchOperationAdd'
					Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=Node))
					output.write(
						f"{rightName} is missing {Node.tag}. name = {defType}.{defName}\n"
					)
					output.write(f'\txpath: {generate_xpath(Node, nodeName=defName)}\n')
				else:
					xpath = generate_xpath(Node, attrName=attrName, attrValue=attrValue)
					# Add to the parent node
					#print(type(Node))
					xpath = xpath.removesuffix('/' + xpath.split('/').pop())
					patchclass = 'PatchOperationAdd'
					Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=Node, attribute=attrName))
					output.write(
						f"{rightName} is missing {Node.tag} in {attrName} = {attrValue}\n"
					)
					output.write(f'\txpath: {generate_xpath(Node, attrName=attrName, attrValue=attrValue)}\n')
			elif Node.__len__() > 0:
				if defType is not None and defName is not None:
					CompareInt(Node, DR[NodeName][0], defType=defType, defName=defName)
				elif attrName is not None and attrValue is not None:
					CompareInt(Node, DR[NodeName][0], attrName=attrName, attrValue=attrValue)

def Compare(left: etree.Element, right: etree.Element) -> None:
	SubNodeDictL = CreateDict(left)
	SubNodeDictR = CreateDict(right)
	# print(SubNodeDictL)
	for NodeName in SubNodeDictL.keys():
		# print(NodeName)
		for Node in SubNodeDictL[NodeName]:
			if Node.tag == "RecipeDef":
				continue
			# print(Node)
			if (
				Node.get("Abstract", default="False").lower() == "true"
				and Node.get("Name") != None
			):  # Abstract Node
				NameAttr = Node.get("Name")
				#print(f"Name = {NameAttr}")
				if (x for x in SubNodeDictR[NodeName] if x.get("Name") == NameAttr) is not None:
					elem = next(
						x for x in SubNodeDictR[NodeName] if x.get("Name") == NameAttr
					)
					CompareInt(Node, elem, attrName='Name', attrValue=NameAttr)
				else:
					output.write(
						f"{rightName} is missing abstract node named {NameAttr}, type = {NodeName}\n"
					)
			else:  # Non-Abstract Node
				defName = Node.find("./defName")
				#print(f"defName = {defName.text}")
				if any(
					x
					for x in SubNodeDictR[NodeName]
					if x.find("./defName") != None
					and x.find("./defName").text == defName.text
				):
					elem = next(
						x
						for x in SubNodeDictR[NodeName]
						if x.find("./defName") != None
						and x.find("./defName").text == defName.text
					)
					CompareInt(Node, elem, defType=NodeName, defName=defName.text)
				else:
					output.write(
						f"{rightName} is missing the whole {defName.text}, type = {NodeName}\n"
					)
	PatchOperation.write_all_operations(os.path.join(dirname, "result.xml"), Operations)
	return


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--file", nargs=2, action="store", metavar="Target files")
	parser.add_argument('--folder', '-f', action='store_true')
	result = parser.parse_args()
	#print(result)
	# if not result.file.count == 2:
	if result.folder:
		dir1, dir2 = choose_dir()
		files1 = set(f for f in os.listdir(dir1) if f.endswith('.xml'))
		files2 = set(f for f in os.listdir(dir2) if f.endswith('.xml'))
		for file in files1:
			if file in files2:
				leftName = os.path.join(dir1, file)
				rightName = os.path.join(dir2, file)
				Left = etree.parse(leftName)
				Right = etree.parse(rightName)
				Compare(Left.getroot(), Right.getroot())
		pass
	else:
		result.file = choose_files()
		leftName = result.file[0]
		rightName = result.file[1]
		print(f"Left = {result.file[0]}")
		print(f"Right = {result.file[1]}")
		Left = etree.parse(result.file[0])
		Right = etree.parse(result.file[1])
		rootL = Left.getroot()  # Should be 'Defs'
		rootR = Right.getroot()  # Should be 'Defs'
		Compare(rootL, rootR)
