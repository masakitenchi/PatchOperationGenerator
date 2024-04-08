import lxml.etree as ET
import regex as re
from typing import Any
import json as JSON


xpath_regex = re.compile(
    r"Defs\/(?<defType>.*?Def)\[(?<condition>.*)\](?<field>.*)"
)

class PatchOperationEncoder(JSON.JSONEncoder):
	def default(self, o)-> dict[str, Any] | Any:
		if isinstance(o, PatchOperation):
			return {'class': o._class, 'defType': o.defType, 'targetNode': o.targetNode, 'value': o.value, 'condition': o.condition, 'xpath': o.xpath}
		# Let the base class default method raise the TypeError
		return super().default(o)


class PatchOperation():
	_class: str
	defType: str
	targetNode: str
	value: str | list[str]
	condition: str
	merged: bool = False

	def __init__(self, _class: str, xpath: str, value: str | list[str] = None, attribute: str = None) -> None:
		self._class = _class
		self.xpath = xpath
		self.value = value
		self.attribute = attribute
		match = xpath_regex.match(xpath)
		if match:
			self.defType = match['defType']
			self.targetNode = match['field']
			self.condition = match['condition']

	def to_ET(self) -> ET.Element:
		root = ET.Element("Operation")
		root.set("Class", self._class)
		xpath = ET.Element("xpath")
		xpath.text = self.xpath
		root.append(xpath)
		if self.value is not None:
			value = ET.Element("value")
			if isinstance(self.value, list):
				for v in self.value:
					try:
						value.append(ET.fromstring(v))
					except ET.XMLSyntaxError as e:
						print(f"Error: {e}, v: {v}")
			else:
				value.text = self.value
			root.append(value)
		return root
	
	def merge_xpath(self, other: "PatchOperation") -> None:
		self.xpath += f"|\n{other.xpath}"

	def merge_value(self, other: "PatchOperation") -> None:
		if isinstance(self.value, list):
			self.value += other.value
		else:
			self.value = [self.value, other.value]

def node_to_str(node: ET._Element) -> str:
	tag_with_attr = node.tag + " " + " ".join([f"{k}=\"{v}\"" for k, v in node.attrib.items()]) if node.attrib.__len__() > 0 else node.tag
	if node.__len__() > 0:
		return f"<{tag_with_attr}>{"".join([node_to_str(x) for x in list(node)])}</{node.tag}>"
	else:
		return f"<{tag_with_attr}>{node.text}</{node.tag}>"

addr = r"D:\SteamLibrary\steamapps\common\RimWorld\Mods\Core_SK\Patches\CombatExtended\Ammo\Shell\155mmHowitzer.xml"

def test() -> None:
	patches = []
	tree = ET.parse(addr)
	root = tree.getroot()
	for node in filter(lambda x: x is not ET.Comment, root):
		if node.find('value') is not None:
			if node.find('value').__len__() > 0:
				value = [ node_to_str(x) for x in list(node.find('value'))]
			else:
				value = [node.find('value').text]
		else: value = None
		patches.append(PatchOperation(node.get("Class"), node.find("xpath").text, value))
	merged = {}
	for patch in patches:
		if patch._class not in merged:
			merged[patch._class] = []
		merged[patch._class].append(patch)
	
	merge_remove(merged['PatchOperationRemove'])
	merge_add(merged['PatchOperationAdd'])

	#print(merged)
	
	tree = ET.ElementTree(ET.Element("Patch"))
	root = tree.getroot()
	for patch in filter(lambda x: not x.merged, patches):
		root.append(patch.to_ET())
	tree.write("output.xml", pretty_print=True, xml_declaration=True, encoding="utf-8", with_comments=True)

def merge_remove(patches: list[PatchOperation]) -> None:
	"""
	Defs/CombatExtended.AmmoSetDef[defName="AmmoSet_155mmHowitzerShell"]/ammoTypes/Ammo_155mmHowitzerShell_Smoke + 
	Defs/CombatExtended.AmmoSetDef[defName="AmmoSet_155mmHowitzerShell"]/ammoTypes/Ammo_155mmHowitzerShell_Incendiary = 

	Defs/CombatExtended.AmmoSetDef[defName="AmmoSet_155mmHowitzerShell"]/ammoTypes/Ammo_155mmHowitzerShell_Incendiary | 
	Defs/CombatExtended.AmmoSetDef[defName="AmmoSet_155mmHowitzerShell"]/ammoTypes/Ammo_155mmHowitzerShell_Smoke
	"""
	for i in range(0, len(patches) - 2):
		if patches[i].merged: continue
		for j in range(1, len(patches) - 1):
			if patches[j].merged or i == j: continue
			if patches[i].xpath.split('/')[0:-1] == patches[j].xpath.split('/')[0:-1]:
				#print(f"Merge {patches[i].xpath} with {patches[j].xpath}")
				patches[i].merge_xpath(patches[j])
				patches[j].merged = True
	
def merge_add(patches: list[PatchOperation]) -> None:
	"""
	xpath1 == xpath2 -> merge
	"""
	for i in range(0, len(patches) - 2):
		if patches[i].merged: continue
		for j in range(1, len(patches) - 1):
			if patches[j].merged or i == j: continue
			if patches[i].xpath == patches[j].xpath:
				print(f"Merge {patches[i].xpath} with {patches[j].xpath}")
				patches[i].merge_value(patches[j])
				patches[j].merged = True



if __name__ == '__main__':
	test()