Install
=======

MemX requires Python 3.10 or higher.

Download the current version
----------------------------
Clone this git repository and the required submodule ABC (https://people.eecs.berkeley.edu/~alanmi/abc/). For ABC, make sure to clone the submodule from here: https://github.com/sventhijssen/abc.
Clone the submodules using the following command::

    $ git clone https://github.com/sventhijssen/memx.git
    $ git submodule update --init --recursive

Download required Python packages
---------------------------------
MemX relies on a wide variety of Python packages, including NetworkX. To install these dependencies, use the following command::

	$ pip install -r requirements.txt

Download required software
--------------------------
Additionally, MemX relies on CPLEX to solve ILP (integer linear programming) problems. Please install CPLEX from the website and set the path to the executable in utils.config.
The CPLEX website can be found here: https://www.ibm.com/products/ilog-cplex-optimization-studio
