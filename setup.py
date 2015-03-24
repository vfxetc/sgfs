from setuptools import setup, find_packages

setup(
    name='sgfs',
    version='0.1.0b',
    description='Translation layer between Shotgun entities and a file structure.',
    url='http://github.com/westernx/sgfs',
    
    packages=find_packages(exclude=['build*', 'tests*']),
    include_package_data=True,
    
    author='Mike Boers',
    author_email='sgfs@mikeboers.com',
    license='BSD-3',
    
    entry_points={
        'console_scripts': [

            # Low-level structure.
            'sgfs-tag = sgfs.commands.tag:main',
            'sgfs-create-structure = sgfs.commands.create_structure:main',

            # Relinking or updating tags.
            'sgfs-relink = sgfs.commands.relink:main',
            'sgfs-rebuild-cache = sgfs.commands.relink:main_rebuild',
            'sgfs-update = sgfs.commands.update:main',

            # Opening commands.
            'sgfs-open = sgfs.commands.open:run_open',
            'sgfs-shotgun = sgfs.commands.open:run_shotgun',
            'sgfs-path = sgfs.commands.open:run_path',

            'sgfs-rv = sgfs.commands.rv:run',

        ],
    },
    
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    
)