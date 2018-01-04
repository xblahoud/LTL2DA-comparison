# -*- coding: utf-8 -*-
import subprocess
import sys
import os.path
import spot
from IPython.display import SVG
from datetime import datetime
import pandas as pd
from experiments_lib import hoa_to_spot, dot_to_svg, pretty_print

def bogus_to_lcr(form):
    """Converts a formula as it is printed in ``_bogus.ltl`` file
    (uses ``--relabel=abc``) to use ``pnn`` AP names.
    """
    args = ['-r0','--relabel=pnn','-f',form]
    return subprocess.check_output(["ltlfilt"] + args, universal_newlines=True).strip()

class LtlcrossRunner(object):
    """A class for running Spot's `ltlcross` and storing and manipulating
    its results. For LTL3HOA it can also draw very weak alternating automata
    (VWAA).

    Parameters
    ----------
    tools : a dict (String -> String)
        The records in the dict of the form ``name : ltlcross_cmd``
    >>> tools = {"LTL3HOA"    : "ltl3hoa -d -x -i -p 2 -f %f > %O",
    >>>          "SPOT":   : "ltl2tgba"
    >>>         }

    formula_files : a list of strings
        paths to files with formulas to be fed to `ltlcross`
    res_filename : String
        filename to store the ltlcross`s results
    cols : list of Strings, default ``['states','edges','transitions']``
        names of ltlcross's statistics columns to be recorded
    """
    def __init__(self, tools,
                 formula_files=['formulae/classic.ltl'],
                 res_filename='na_comp.csv',
                 cols=['states', 'edges', 'transitions'],
                 log_file=None,
                ):
        self.tools = tools
        self.mins = []
        self.f_files = formula_files
        self.cols = cols
        self.automata = None
        self.values = None
        self.form = None
        if res_filename == '' or res_filename is None:
            self.res_file = '_'.join(tools.keys()) + '.csv'
        else:
            self.res_file = res_filename
        if log_file is None:
            self.log_file = self.res_file[:-3] + 'log'
        else:
            self.log_file = log_file

    def create_args(self, automata=True, check=False, timeout='300',
                     log_file=None, res_file=None,
                     save_bogus=True, tool_subset=None):
        """Creates args that are passed to run_ltlcross
        """
        if log_file is None:
            log_file = self.log_file
        if res_file is None:
            res_file = self.res_file
        if tool_subset is None:
            tool_subset=self.tools.keys()

        ### Prepare ltlcross command ###
        tools_strs = ["{"+name+"}" + cmd for (name, cmd) in self.tools.items() if name in tool_subset]
        args = tools_strs +  ' '.join(['-F '+F for F in self.f_files]).split()
        if timeout:
            args.append('--timeout='+timeout)
        if automata:
            args.append('--automata')
        if save_bogus:
            args.append('--save-bogus={}_bogus.ltl'.format(res_file[:-4]))
        if not check:
            args.append('--no-checks')
        args.append('--products=0')
        args.append('--csv='+res_file)
        return args

    def ltlcross_cmd(self, args=None, automata=True,
                     check=False, timeout='300',
                     log_file=None, res_file=None,
                     save_bogus=True, tool_subset=None):
        """Returns ltlcross command for the parameters.
        """
        if log_file is None:
            log_file = self.log_file
        if res_file is None:
            res_file = self.res_file
        if tool_subset is None:
            tool_subset=self.tools.keys()
        if args is None:
            args = self.create_args(automata, check, timeout,
                                    log_file, res_file,
                                    save_bogus, tool_subset)
        return ' '.join(['ltlcross'] + args)

    def run_ltlcross(self, args=None, automata=True,
                     check=False, timeout='300',
                     log_file=None, res_file=None,
                     save_bogus=True, tool_subset=None):
        """Removes any older version of ``self.res_file`` and runs `ltlcross`
        on all tools.

        Parameters
        ----------
        args : a list of ltlcross arguments that can be used for subprocess
        tool_subset : a list of names from self.tools
        """
        if log_file is None:
            log_file = self.log_file
        if res_file is None:
            res_file = self.res_file
        if tool_subset is None:
            tool_subset=self.tools.keys()
        if args is None:
            args = self.create_args(automata, check, timeout,
                                    log_file, res_file,
                                    save_bogus, tool_subset)

        # Delete ltlcross result and lof files
        subprocess.call(["rm", "-f", res_file, log_file])

        ## Run ltlcross ##
        log = open(log_file,'w')
        cmd = self.ltlcross_cmd(args)
        print(cmd, file=log)
        print(datetime.now().strftime('[%d.%m.%Y %T]'), file=log)
        print('=====================', file=log,flush=True)
        self.returncode = subprocess.call(["ltlcross"] + args, stderr=subprocess.STDOUT, stdout=log)
        log.writelines([str(self.returncode)+'\n'])
        log.close()

    def parse_results(self, res_file=None):
        """Parses the ``self.res_file`` and sets the values, automata, and
        form. If there are no results yet, it runs ltlcross before.
        """
        if res_file is None:
            res_file = self.res_file
        if not os.path.isfile(res_file):
            raise FileNotFoundError(res_file)
        res = pd.read_csv(res_file)
        # Removes unnecessary parenthesis from formulas
        res.formula = res['formula'].map(pretty_print)

        form = pd.DataFrame(res.formula.drop_duplicates())
        form['form_id'] = range(len(form))
        form.index = form.form_id
        #form['interesting'] = form['formula'].map(is_interesting)

        res = form.merge(res)
        # Shape the table
        table = res.set_index(['form_id', 'formula', 'tool'])
        table = table.unstack(2)
        table.axes[1].set_names(['column','tool'],inplace=True)

        # Create separate tables for automata
        automata = table[['automaton']]

        # Removes formula column from the index
        automata.index = automata.index.levels[0]

        # Removes `automata` from column names -- flatten the index
        automata.columns = automata.columns.levels[1]
        form = form.set_index(['form_id', 'formula'])

        # stores the followed columns only
        values = table[self.cols]
        self.form = form
        self.values = values.sort_index(axis=1,level=['column','tool'])
        # self.compute_best("Minimum")
        self.automata = automata

    def compute_best(self, tools=None, colname="Minimum"):
        """Computes minimum values over tools in ``tools`` for all
        formulas and stores them in column ``colname``.
        
        Parameters
        ----------
        tools : list of Strings
            column names that are used to compute the min over
        colname : String
            name of column used to store the computed values
        """
        if tools is None:
            tools = list(self.tools.keys())
        self.mins.append(colname)
        for col in self.cols:
            self.values[col, colname] = self.values[col][tools].min(axis=1)
        self.values.sort_index(axis=1, level=0, inplace=True)

    def aut_for_id(self, form_id, tool):
        """For given formula id and tool it returns the corresponding
        non-deterministic automaton as a Spot's object.

        Parameters
        ----------
        form_id : int
            id of formula to use
        tool : String
            name of the tool to use to produce the automaton
        """
        if self.automata is None:
            raise AssertionError("No results parsed yet")
        if tool not in self.tools.keys():
            raise ValueError(tool)
        return hoa_to_spot(self.automata.loc[form_id, tool])

    def cummulative(self, col="states"):
        """Returns table with cummulative numbers of given ``col``.

        Parameters
        ---------
        col : String
            One of the followed columns (``states`` default)
        """
        return self.values[col].dropna().sum()

    def smaller_than(self, tool1, tool2, reverse=False,
                     restrict=True,
                     col='states', restrict_cols=True):
        """Returns a dataframe with results where ``col`` for ``tool1``
        has strictly smaller value than ``col`` for ``tool2``.

        Parameters
        ----------
        tool1 : String
            name of tool for comparison (the better one)
            must be among tools
        tool2 : String
            name of tool for comparison (the worse one)
            must be among tools
        reverse : Boolean, default ``False``
            if ``True``, it switches ``tool1`` and ``tool2``
        restrict : Boolean, default ``True``
            if ``True``, the returned DataFrame contains only the compared
            tools
        col : String, default ``'states'``
            name of column use for comparison.
        restrict_cols : Boolean, default ``True``
            if ``True``, show only the compared column
        """
        if tool1 not in list(self.tools.keys())+self.mins:
            raise ValueError(tool1)
        if tool2 not in list(self.tools.keys())+self.mins:
            raise ValueError(tool2)
        if col not in self.cols:
            raise ValueError(col)
        if reverse:
            tool1, tool2 = tool2, tool1
        v = self.values
        res = v[v[col][tool1] < v[col][tool2]]
        if restrict:
            res = res.loc(axis=1)[:, [tool1, tool2]]
        if restrict_cols:
            res = res[col]
        return res

    def vwaa_for_id(self, form_id, tool, unreachable=False):
        """For given formula id and tool it returns the corresponding
        non-deterministic automaton as a Spot's object

        Parameters
        ----------
        form_id : int
            id of formula to use
        tool : String
            Name of the tool (and options) to use to produce the automaton.
            It uses the ``tools`` dict to gather the correct options.
        unreachable : Bool
            Prints also unreachable states if ``True``. Default ``False``
        """
        if self.automata is None:
            raise AssertionError("No results parsed yet")
        if tool not in self.tools.keys():
            raise ValueError(tool)
        cmd = create_ltl3hoa_cmd(self.tools[tool])
        cmd += ' -p1 -o dot'
        if unreachable:
            cmd += ' -z0'
        f = self.form_of_id(form_id, False)
        ltl3hoa = subprocess.Popen(cmd.split() + ["-f", f],
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = ltl3hoa.communicate()
        if stderr:
            print("Calling the translator produced the message:\n" +
                  stderr.decode('utf-8'), file=sys.stderr)
        ret = ltl3hoa.wait()
        if ret:
            raise subprocess.CalledProcessError(ret, 'translator')
        dot = stdout.decode('utf-8')
        return SVG(dot_to_svg(dot))

    def form_of_id(self, form_id, spot_obj=True):
        """For given form_id returns the formula

        Parameters
        ----------
        form_id : int
            id of formula to return
        spot_obj : Bool
            If ``True``, returns Spot formula object (uses Latex to
            print the formula in Jupyter notebooks)
        """
        f = self.values.index[form_id][1]
        if spot_obj:
            return spot.formula(f)
        return f
