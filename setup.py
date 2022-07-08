from setuptools import setup, find_packages
import re

def get_version():
    with open("lw_doc_extractor/_version.py") as fh:
        verLine = fh.read()
        m = re.match("\s*__version__ *= *[\"']([\d.]+)[\"']", verLine)
        if m:
            return m.group(1)
        else:
            raise RuntimeError("Unable to determine version of the project")

def get_long_description():
    with open("README.md", "r") as fh:
        return fh.read()


setup(
    name='lw-doc-extractor',
    version=get_version(),
    
#     # project description parameters. These should be filled in accordingly
#     author="placeholderauthor",
#     author_email="placeholderauthoremail",
#     description="placeholderdescription",
#     long_description=get_long_description(),
#     long_description_content_type="text/markdown",
#     python_requires='~=3.6',
#     classifiers=[
#         "Programming Language :: Python :: 3",
#         "License :: OSI Approved :: MIT License",
#         "Operating System :: OS Independent",
#     ]
    
    # packages for distribution are found & included automatically
    packages=find_packages(),
    # for defining other resource files if they need to be included in the installation
    package_data={
        '' : ['*.md']
    },
    
    # Set this is using a MANIFEST.in 
    # include_package_data=True,
    
    # libraries from PyPI that this project depends on
    install_requires=[
        # example library
        "k3logging==0.1",
        "python-docx"
    ],
    entry_points={
        'console_scripts': [
            # a list of strings of format:
            # <command> = <package>:<function>
            'lw-doc-extractor-cli = lw_doc_extractor.main.cli:main'
            # , ...
        ]
    }
)