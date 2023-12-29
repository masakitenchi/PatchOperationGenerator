from importlib.metadata import files
from io import TextIOWrapper
from turtle import right
from lxml import etree
import os
import argparse
import copy
from regex import R
from PatchGenerator import PatchOperation
from file import choose_dir, choose_files
from DefComparer import compare_root, comp_list

dirname = os.path.split(__file__)[0]
output: TextIOWrapper = None
leftPath: str
rightPath: str
rootL: etree.Element
rootR: etree.Element
Operations : list[PatchOperation] = []

def _log(message: str = None) -> None:
	"""result.verbose is defined only in this file. DO NOT USE IT IN OTHER FILES"""
	global output
	#print(*args, **kwargs)
	if not result.verbose: return
	if output is None:
		output = open(os.path.join(dirname, 'result.txt'), 'w', encoding='utf-8')
	output.write(message)

def recursive_search(path: str = None) -> set[tuple[str, str]]:
	"""Returns a list of all abspath of xml files in a given directory, including those in subdirectories"""
	result: set[tuple[str, str]] = set()
	for root, subdirs, files in os.walk(path):
		for file in files:
			if file.endswith('.xml'):
				result.add((root, file))
		for subdir in subdirs:
			result.union(recursive_search(os.path.join(root, subdir)))
	return result


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--file", nargs=2, action="store", metavar="Target files")
	parser.add_argument('--folder', '-f', action='store_true', help='Choose two folders to compare')
	parser.add_argument('--verbose', '-v', action='store_true', help='Create a result.txt in root directory, shows all the differences')
	parser.add_argument('--recursive', '-r', action='store_true', help='Look into subfolders as well')
	result = parser.parse_args()
	if result.recursive:
		# print('Recursive mode')
		if result.folder:
			dir1, dir2 = choose_dir()
			files1 = recursive_search(dir1)
			files2 = recursive_search(dir2)
			#print(files1)
			#print(dir1, '\n', dir2)
			finished_list = list(files1)
			for file in files1:
				if file[1] in [f[1] for f in files2]:
					Operations.clear()
					leftPath = os.path.normpath(os.path.join(file[0], file[1]))
					rightPath = os.path.normpath(os.path.join(file[0].replace(dir1, dir2), file[1]))
					UppererFolder = os.path.sep.join(leftPath.split(os.path.sep)[-3:-1])
					#print(f'UppererFolder {UppererFolder}')
					# Seems we need to remove the \\ prefix otherwise os.path.join will not work
					PatchPath = os.path.join(dirname, 'Patches', 'CombatExtended', UppererFolder.removeprefix('CombatExtended\\'), file[1])
					#print(PatchPath)
					if not os.path.exists(os.path.split(PatchPath)[0]):
						os.makedirs(os.path.split(PatchPath)[0])
					Left = etree.parse(leftPath)
					Right = etree.parse(rightPath)
					#print(f'Comparing {leftPath} and {rightPath}\n')
					#print(f'Writing to {PatchPath}\n')
					PatchOperation.write_all_operations(PatchPath, compare_root(Left, Right))
					print(f'Finished {file[1]}')
					finished_list.remove(file)

			# Copy HSK specific files
			if len(finished_list) > 0:
				print('Copying HSK specific files into ./MissingFiles')
			for file in finished_list:
				with open(os.path.join(file[0], file[1]), 'rb') as f:
					UppererFolder = os.path.sep.join(
						os.path.normpath
						(os.path.join(file[0], file[1]))

						.split(os.path.sep)
						[-3:-1])
					#print(f'UppererFolder {UppererFolder}')
					# Seems we need to remove the \\ prefix otherwise os.path.join will not work
					PatchPath = os.path.join(dirname, 'MissingFiles', 'CombatExtended', UppererFolder.removeprefix('CombatExtended\\'), file[1])
					if not os.path.exists(os.path.split(PatchPath)[0]):
						os.makedirs(os.path.split(PatchPath)[0])
					new = open(PatchPath, 'wb')
					new.write(f.read())
					new.close()

			# Comment out files not in HSK
			for file in files2:
			#print(file)
				if file[1] not in [f[1] for f in files1]:
					print(f'Removing {file[1]} from {file[0]} ...')
					os.rename(os.path.join(file[0], file[1]), os.path.join(file[0], file[1] + '.bak'))

		else:
			if result.file is None:
				result.file = choose_files()
			leftPath = result.file[0]
			rightPath = result.file[1]
			print(f"Left = {result.file[0]}")
			print(f"Right = {result.file[1]}")
			Left = etree.parse(result.file[0])
			Right = etree.parse(result.file[1])
			rootL = Left.getroot()

	elif result.folder:
		dir1, dir2 = choose_dir()
		#print(dir1, dir2)
		files1 = [f for f in os.listdir(dir1) if f.endswith('.xml')]
		files2 = [f for f in os.listdir(dir2) if f.endswith('.xml')]
		for file in files1:
			if file in files2:
				Operations.clear()
				leftPath = os.path.normpath(os.path.join(dir1, file))
				rightPath = os.path.normpath(os.path.join(dir2, file))
				UppererFolder = os.path.sep.join(leftPath.split(os.path.sep)[-3:-1])
				PatchPath = os.path.join(dirname, 'Patches', 'CombatExtended', UppererFolder, file)
				if not os.path.exists(os.path.split(PatchPath)[0]):
					os.makedirs(os.path.split(PatchPath)[0])
				Left = etree.parse(leftPath)
				Right = etree.parse(rightPath)
				PatchOperation.write_all_operations(PatchPath, compare_root(Left, Right))

		# Remove files not in HSK
		for file in files2:
			#print(file)
			if file not in files1:
				print(f'Removing {file[1]} from {file[0]} ...')
				os.rename(os.path.join(file[0], file[1]), os.path.join(file[0], file[1] + '.bak'))

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
		PatchOperation.write_all_operations('./Patch.xml', compare_root(Left, Right))
