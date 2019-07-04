import glob
import os
from pathlib import Path

from setuptools import setup, find_packages

home = str(Path.home())

setup(
    name='devops tools',
    packages=find_packages(),
    package_data={
        'data': ['docker/**/*']
    },
    data_files=[
        (os.path.join(home, 'devops_tools', 'examples'), glob.glob("example/*"))
    ],
    version='0.1',
    description='It\'s a DevOps tool, highly configurable job chains.',
    author='Zhang Yanwei',
    author_email='verdigris@163.com',
    keywords=['devops', 'job chains'],
    install_requires=[
        'docker >= 3.2.1',
        'paramiko >= 2.4.1',
        'PyYAML >= 3.12',
        'requests'
    ],
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
        "Topic :: Utilities"
    ]
)
