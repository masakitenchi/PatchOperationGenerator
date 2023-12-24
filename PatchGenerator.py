from typing import Any
import lxml.etree as ET
import os

from numpy import isin

# A valid PatchOperation consists of a xpath, a value and a patchclass.
"""
<Operation Class="PatchOperationAdd">
	<xpath>...</xpath>
	<value>...</value>
</Operation>
"""

class PatchOperation:
	def __init__():
		patchclass: str = ""
		xpath: str = ""
		value: str = ""
		attribute: str = None

	def GeneratePatchOperation(*, patchclass: str, xpath: str, value: Any, attribute: str = None) -> ET.Element:
		node_name = xpath.split("/")[-1]
		operation = ET.Element("Operation", attrib={"Class": patchclass})
		operation.append(ET.fromstring(f"<xpath>{xpath}</xpath>"))
		print(f'class : {patchclass}, xpath : {xpath}, value : {value}, attribute : {attribute}')
		if isinstance(value, ET._Element):
			value_node = ET.Element("value")
			value_node.text = "\n\t\t\t"
			value_node.append(value)
			operation.append(value_node)
		else:
			if patchclass == "PatchOperationAttributeSet":
				print(f'value = {value}')
				if value != "None":
					operation.append(ET.fromstring(f"<attribute>{attribute}</attribute>"))
					operation.append(ET.fromstring(f"<value>{value}</value>"))
				else:
					operation.attrib["Class"] = "PatchOperationAttributeRemove"
					operation.append(ET.fromstring(f"<attribute>{attribute}</attribute>"))
			else:
				operation.append(ET.fromstring(f"<value><{node_name}>{value}</{node_name}></value>"))
		return operation

	def MergePatchOperation(patchoperations: list[ET.Element]) -> list[ET.Element]:
		#dict[(patchclass, xpath), value]
		operationdict: dict[tuple(str, str), str] = {}
		for item in patchoperations:
			patchclass = item.get("Class")
			xpath = item.find("xpath").text
			value = "".join(item.find("value").itertext())
			if (patchclass, xpath) in operationdict.keys():
				if patchclass == "PatchOperationAdd":
					operationdict[(patchclass, xpath)] = operationdict[(patchclass, xpath)] + '\n' + value
				elif patchclass == "PatchOperationReplace":
					operationdict[(patchclass, xpath)] = value
				elif patchclass == "PatchOperationRemove":
					operationdict[(patchclass, xpath)] = None
				elif patchclass == "PatchOperationAttributeSet":
					operationdict[(patchclass, xpath)] = value
		patchoperations = [PatchOperation.GeneratePatchOperation(patchclass=item[0], xpath=item[1], value=operationdict[item]) for item in operationdict]
		return patchoperations
	
	def write_all_operations(filepath: str, patchoperations: list[ET.Element]) -> None:
		# write all operations to a file
		root = ET.Element("Patch")
		for item in patchoperations:
			root.append(item)
		tree = ET.ElementTree(root)
		tree.write(filepath, pretty_print=True, xml_declaration=True, encoding="utf-8")