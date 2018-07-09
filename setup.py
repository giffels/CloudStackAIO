from setuptools import setup, find_packages
import os

repo_base_dir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(repo_base_dir, 'README.md'), 'r') as read_me:
    long_description = read_me.read()

setup(
    name='CloudStackAIO',
    version='0.0.4',
    description='Very thin Python CloudStack client using asyncio',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/giffels/CloudStackAIO',
    author='Manuel Giffels',
    author_email='giffels@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP :: Session',
        'Framework :: AsyncIO',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='asyncio cloudstack client',
    packages=find_packages(exclude=['tests']),
    install_requires=['aiohttp'],
    test_suite='tests',
    zip_safe=False,
    package_data={
        'sample': ['CloudStack.py'],
    },
    project_urls={
        'Bug Reports': 'https://github.com/giffels/CloudStackAIO/issues',
        'Source': 'https://github.com/giffels/CloudStackAIO',
    },
)
