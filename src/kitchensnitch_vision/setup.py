from setuptools import find_packages, setup

package_name = 'kitchensnitch_vision'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Jan Fontanilla',
    maintainer_email='janfontanilla12@gmail.com',
    description='Pitcher tag tracking and sink state detection for KitchenSnitch',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'pitcher_tracker = kitchensnitch_vision.pitcher_tracker:main',
            'sink_checker = kitchensnitch_vision.sink_checker:main',
        ],
    },
)
