import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'kitchensnitch_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Jan Fontanilla',
    maintainer_email='janfontanilla12@gmail.com',
    description='Launch files and config for KitchenSnitch',
    license='MIT',
)
