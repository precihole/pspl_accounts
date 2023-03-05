from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in pspl_accounts/__init__.py
from pspl_accounts import __version__ as version

setup(
	name="pspl_accounts",
	version=version,
	description="accounts",
	author="PSPL",
	author_email="rehan@preciholesports.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
