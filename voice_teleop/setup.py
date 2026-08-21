from setuptools import find_packages, setup

package_name = 'voice_teleop'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='divyanshu',
    maintainer_email='you@example.com',
    description='Voice-controlled teleop for tortoisebot via OpenAI Whisper + GPT intent matching',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'voice_teleop_node = voice_teleop.voice_teleop_node:main',
        ],
    },
)
