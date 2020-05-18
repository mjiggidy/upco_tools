import setuptools

with open("README.md", "r") as fh:
	long_description = fh.read()

setuptools.setup(
	name="upco_tools_mjiggidy", # Replace with your own username
	version="0.0.1",
	author="Michael J. Jordan",
	author_email="michael@glowingpixel.com",
	description="Various tools for film and television post production",
	long_description=long_description,
	long_description_content_type="text/markdown",
	url="https://github.com/mjiggidy/upco_tools",
	packages=setuptools.find_packages(),
	classifiers=[
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: GNU General Public License v3 (GPLv3) ",
		"Operating System :: OS Independent",
	],
	python_requires='>=3.6',
)