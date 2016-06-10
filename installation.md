
# Installing the Rp-Bp and Rp-chi pipelines

This document describes detailed installation instructions for the Rp-Bp and Rp-chi pipelines. These steps have been primarily tested on Ubuntu.

<a id="toc"></a>

* [Prerequisites](#prerequisites)
* [Simple installation](#simple-installation)
* [Virtual environment installation](#virtual-environment-installation)

<a id="prerequisites"></a>

## Prerequisites

The pipelines make use of a number of standard bioinformatics tools. All of these must be installed and available on the `$PATH` for the pipeline to work correctly. All of the pipeline scripts checks that the required programs are available before executing. If any required programs cannot be found, the script prints an error message about the missing program and does not continue. The versions used during development and testing are specified below. For most of the tools, any recent version should be sufficient. If problems arise, though, please use the version indicated below

* [bedtools](http://bedtools.readthedocs.io/en/latest/), version 2.25.0. Importantly, [bedtools intersect](http://bedtools.readthedocs.io/en/latest/content/tools/intersect.html) must accept the `-F` option
* [bowtie2](http://bowtie-bio.sourceforge.net/bowtie2/index.shtml), version 2.2.6
* [cufflinks](http://cole-trapnell-lab.github.io/cufflinks/), version 2.2.1. Only the `gffread` program is required for Rp-Bp.
* [flexbar](https://github.com/seqan/flexbar), version 2.5
* [SAMtools](http://www.htslib.org/), version 1.2
* [STAR](https://github.com/alexdobin/STAR), version 2.4.1d

[Back to top](#toc)

<a id='simple-installation'></a>

## Simple installation


We recommend installing the application in a virtual environment as described [below](#virtual-environment-installation). If this is not desired for some reason, the following instructions can be used to install the package without sudo access in a user's home directory.

The commands below are presumably executed in a directory like `$HOME/install`. They install the python executables into `$HOME/local/bin` (or wherever the `prefix` option is located).
So that directory must be in the `$PATH`.
This can be accomplished by adding a line like `export PATH=$HOME/local/bin:$PATH` in the file `.bashrc` on Ubuntu.


```python
### Lines to add to .bashrc

# for the OpenBLAS library
export LD_LIBRARY_PATH=$HOME/local/lib:$LD_LIBRARY_PATH
    
# for the installation process
export PATH=$HOME/local/bin:$PATH

### Downloading and installing the required software

# Download, extract and install Python 3. 
wget https://www.python.org/ftp/python/3.5.1/Python-3.5.1.tgz && tar -xvf Python-3.5.1.tgz && cd Python-3.5.1 && ./configure --prefix=$HOME/local --with-ensurepip=upgrade && make && make install && cd ..

# Upgrade pip. 
pip3 install --upgrade pip

# Clone the git repository. 
git clone git@github.com:dieterich-lab/rp-bp.git
    
# Change into the rp-bp directory and build the package. 
cd rp-bp && make
```

The build process includes compiling several libraries for optimized numerical calculations. Due to the optimized nature of these libraries, the initial installation can take up to an hour.

[Back to top](#toc)

<a id='virtual-environment-installation'></a>

## Virtual environment installation


These instructions explain how to install the software and most dependencies from scratch without required root access.
It only requires standard development libraries and tools, like gcc and the gzip development headers.
The python build scripts will also output a line like "The necessary bits to build these optional modules were not found" if any optional libraries, developoment headers, etc., are not found.

The commands below are presumably executed in a directory like `$HOME/install`.
They install the python executables into `$HOME/local/bin` (or wherever the `prefix` option is located).
So that directory must be in the `$PATH`.
This can be accomplished by adding a line like `export PATH=$HOME/local/bin:$PATH` in the file `.bashrc` on Ubuntu.


```python
### Lines to add to .bashrc

# for the virtual environment
# See http://www.simononsoftware.com/virtualenv-tutorial-part-2/ for more details.
export WORKON_HOME=$HOME/.virtualenvs
source $HOME/local/bin/virtualenvwrapper_lazy.sh 

# for the OpenBLAS library
export LD_LIBRARY_PATH=$HOME/local/lib:$LD_LIBRARY_PATH
    
# for the installation process
export PATH=$HOME/local/bin:$PATH

### Downloading and installing the required software

# Download, extract and install Python 2. This is necessary for creating the virtual environment
wget https://www.python.org/ftp/python/2.7.11/Python-2.7.11.tgz && tar -xvf Python-2.7.11.tgz && cd Python-2.7.11 && ./configure --prefix=$HOME/local --with-ensurepip=upgrade && make && make install && cd ..
    
# Download, extract and install Python 3. This is necessary for the pipelines
wget https://www.python.org/ftp/python/3.5.1/Python-3.5.1.tgz && tar -xvf Python-3.5.1.tgz && cd Python-3.5.1 && ./configure --prefix=$HOME/local --with-ensurepip=upgrade && make && make install && cd ..

# Upgrade both versions of pip. 
pip2 install --upgrade pip && pip3 install --upgrade pip

# Install the virtual environment wrapper for Python 2. 
pip2 install --upgrade virtualenvwrapper

# Create a virtual environment using Python 3. 
mkvirtualenv rpbp -p $HOME/local/bin/python3

# Clone the git repository.
git clone git@github.com:dieterich-lab/rp-bp.git

# Change into the rp-bp directory and build the package. 
cd rp-bp && make
```

The build process includes compiling several libraries for optimized numerical calculations. Due to the optimized nature of these libraries, the initial installation can take up to an hour.

To use the programs in the future, use the `workon` command to ensure the virtual environment is active.


```python
# activate virtual environment
workon rpbp
```

[Back to top](#toc)