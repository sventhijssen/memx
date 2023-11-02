.. _tutorial:

Tutorial
========

Command-line interface
----------------------

In this tutorial, we will walk through the command-line interface (CLI).
The CLI is an easy-to-use interface for interaction with the MemX framework.
It was inspired after the ABC (https://github.com/berkeley-abc/abc) framework developed by Dr. Brayton and Dr. Mishchenko at UC Berkeley [abc]_.

.. [abc] Brayton, R., & Mishchenko, A. (2010). ABC: An academic industrial-strength verification tool. In Computer Aided Verification: 22nd International Conference, CAV 2010, Edinburgh, UK, July 15-19, 2010. Proceedings 22 (pp. 24-40). Springer Berlin Heidelberg.

Introduction
""""""""""""

The command-line interface was developed to make interation easy-to-use. Many synthesis and verification flows have the same common components, which can be easily invoked using commands.

Here, commands are separated by the token :code:`|`. Each command can have a list of required and optional arguments. Optional arguments are indicated by the flag :code:`-FLAG_NAME`. For example:

.. code-block:: python

   Program.execute("read ex.v | sbdd | compact -vh")

Log file
""""""""

In the complex hierarchy of commands, one may be interested in some of the more interesting intermediate results.
These are saved automatically to a log file when the :code:`log` command has been used at the beginning of the program.
The log file is in JSON file format for easy parsing afterwards.

.. code-block:: python

   Program.execute("log ex.json | read ex.v | sbdd | compact -vh")


Reading files
"""""""""""""

I/O is provided for several file formats, including but not limited to Verilog, PLA, BLIF, BDD, TOPO, XBAR etc.

.. code-block:: python

   Program.execute("read FILE_NAME")

Constructing decision diagrams
""""""""""""""""""""""""""""""

Once an input file has been read, such as in Verilog, PLA, or BLIF, this can be converted into a decision diagram, such as binary decision diagrams (BDDs).

.. code-block:: python

   Program.execute("read FILE_NAME | bdd")
   Program.execute("write FILE_NAME | robdd")
   Program.execute("write FILE_NAME | sbdd")

Synthesis frameworks
""""""""""""""""""""

One can apply several synthesis frameworks after pre-processing, such as COMPACT or PATH.
Please refer to the respective commands for an exhaustive list of required and optional arguments.

.. code-block:: python

   Program.execute("read ex.v | sbdd | compact")
   Program.execute("read ex.bdd | path")

Writing files
"""""""""""""

Finally, one can write the resulting Boolean function(s) to file using the :code:`write` command.

**Caution** for the :code:`write` command. This file name is an optional argument. When more than one Boolean function lives in the namespace, then this will override the same file.
In this case, do not provide a file name, and a file name is generated automatically for each individual Boolean function.

.. code-block:: python

   Program.execute("read ex.bdd | compact | draw write.dot")

Drawing files
"""""""""""""

As part of the I/O, some Boolean functions can be represented graphically. For example, BDDs and XBARs.

Use the :code:`draw` command to write a file in DOT file format. Next, the DOT file can be converted into PNG and SVG using Graphviz (https://graphviz.org/).

.. code-block:: python

   Program.execute("read ex.bdd | compact | draw ex.dot")
