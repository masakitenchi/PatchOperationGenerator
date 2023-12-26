from io import TextIOWrapper
from lxml import etree
import os
import argparse
import copy
from regex import R
from PatchGenerator import PatchOperation
from file import choose_dir, choose_files

dirname = os.path.split(__file__)[0]
output: TextIOWrapper = None
leftPath: str
rightPath: str
rootL: etree.Element
rootR: etree.Element
Operations : list[PatchOperation] = []


def log(message: str = None) -> None:
	global output
	#print(*args, **kwargs)
	if not result.verbose: return
	if output is None:
		output = open(os.path.join(dirname, 'result.txt'), 'w', encoding='utf-8')
	output.write(message)

def generate_xpath_newtemp(elem: etree.Element) -> str:
	result: str = ""
	assertion: str = None
	elemiter = elem
	while elemiter is not None:
		if elemiter.tag.__contains__('Def'):
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


def generate_xpath(elem: etree.Element, *,  defName: str = None, attrName: str = None, attrValue: str = None) -> str:
	return generate_xpath_newtemp(elem)
	result: str = ''
	elemiter = elem.iterancestors()
	for path in elemiter:
		result = path.tag + '/' + result
	result = result.removesuffix('/')
	print(result)
	List = result.split('/')
	print(List)
	if (len(List) > 1):
		if defName is not None:
			List[1] = List[1] + f'[defName="{defName}"]'
		elif attrName is not None and attrValue is not None:
			List[1] = List[1] + f'[@{attrName}="{attrValue}"]'
	print(List)
	result = '/'.join(List) + '/' + elem.tag
	return result

def CompareAttr(left: etree.Element, right: etree.Element) -> bool | dict[str, str]:
	result = {}
	for key, value in left.attrib.items():
		if key not in right.attrib:
			result[key] = value + ' -> None' 
		elif value != right.attrib[key]:
			result[key] = right.attrib[key] + ' -> ' + value
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
			for attrName in attrResult.keys():
				attrValue = attrResult[attrName].split(' -> ')[1]
				xpath = generate_xpath(left, attrName=attrName, attrValue=attrValue)
				patchclass = 'PatchOperationAttributeSet'
				Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=attrValue, attribute=attrName))
				log('\n' + right.tag + attrResult.__str__() + '\n\n')
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
					log('\n' + right.tag + attrresult.__str__() + '\n\n') """
				if DR[NodeName][0].text == Node.text:
					continue
				else:
					if defType is not None and defName is not None:
						xpath = generate_xpath(Node, defName=defName)
						patchclass = 'PatchOperationReplace'
						Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=Node.text))
						log(
							f'{rightPath} has different {Node.tag} in {defType}.{defName}. "{Node.text}" -> "{DR[NodeName][0].text}"\n'
						)
						log(f'\txpath: {xpath}\n')
					else:
						xpath = generate_xpath(Node, attrName=attrName, attrValue=attrValue)
						patchclass = 'PatchOperationReplace'
						Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=Node.text, attribute=attrName))
						log(
							f'{rightPath} has different {Node.tag} in {attrName} = {attrValue}. "{Node.text}" -> "{DR[NodeName][0].text}"\n'
						)
						log(f'\txpath: {xpath}\n')
			elif NodeName not in DR.keys():
				if defType is not None and defName is not None:
					xpath = generate_xpath(Node, defName=defName)
					# Add to the parent node
					#print(type(Node))
					xpath = xpath.removesuffix('/' + xpath.split('/').pop())
					patchclass = 'PatchOperationAdd'
					Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=Node))
					log(
						f"{rightPath} is missing {Node.tag}. name = {defType}.{defName}\n"
					)
					log(f'\txpath: {generate_xpath(Node, defName=defName)}\n')
				else:
					xpath = generate_xpath(Node, attrName=attrName, attrValue=attrValue)
					# Add to the parent node
					#print(type(Node))
					xpath = xpath.removesuffix('/' + xpath.split('/').pop())
					patchclass = 'PatchOperationAdd'
					Operations.append(PatchOperation.GeneratePatchOperation(patchclass=patchclass, xpath=xpath, value=Node, attribute=attrName))
					log(
						f"{rightPath} is missing {Node.tag} in {attrName} = {attrValue}\n"
					)
					log(f'\txpath: {generate_xpath(Node, attrName=attrName, attrValue=attrValue)}\n')
			elif Node.__len__() > 0:
				if defType is not None and defName is not None:
					CompareInt(Node, DR[NodeName][0], defType=defType, defName=defName)
				elif attrName is not None and attrValue is not None:
					CompareInt(Node, DR[NodeName][0], attrName=attrName, attrValue=attrValue)

def Compare(left: etree.Element, right: etree.Element, PatchPath: str | TextIOWrapper) -> None:
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
					log(
						f"{rightPath} is missing abstract node named {NameAttr}, type = {NodeName}\n"
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
					log(
						f"{rightPath} is missing the whole {defName.text}, type = {NodeName}\n"
					)
	PatchOperation.write_all_operations(PatchPath, Operations)
	return


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--file", nargs=2, action="store", metavar="Target files")
	parser.add_argument('--folder', '-f', action='store_true', help='Choose two folders to compare')
	parser.add_argument('--verbose', '-v', action='store_true', help='Create a result.txt in root directory, shows all the differences')
	result = parser.parse_args()
	#print(result)
	# if not result.file.count == 2:
	if result.folder:
		dir1, dir2 = choose_dir()
		files1 = [f for f in os.listdir(dir1) if f.endswith('.xml')]
		files2 = [f for f in os.listdir(dir2) if f.endswith('.xml')]
		for file in files1:
			if file in files2:
				Operations.clear()
				leftPath = os.path.normpath(os.path.join(dir1, file))
				rightPath = os.path.normpath(os.path.join(dir2, file))
				UppererFolder = os.path.sep.join(leftPath.split(os.path.sep)[-3:-1])
				PatchPath = os.path.join(dirname, 'Patches', UppererFolder, file)
				if not os.path.exists(os.path.split(PatchPath)[0]):
					os.makedirs(os.path.split(PatchPath)[0])
				with open(PatchPath, 'w', encoding='utf-8') as Patch:
					Left = etree.parse(leftPath)
					Right = etree.parse(rightPath)
					Compare(Left.getroot(), Right.getroot(), PatchPath)

	else:
		if result.file is None:
			result.file = choose_files()
		leftPath = result.file[0]
		rightPath = result.file[1]
		print(f"Left = {result.file[0]}")
		print(f"Right = {result.file[1]}")
		Left = etree.parse(result.file[0])
		Right = etree.parse(result.file[1])
		rootL = Left.getroot()  # Should be 'Defs'
		rootR = Right.getroot()  # Should be 'Defs'
		Compare(rootL, rootR)
