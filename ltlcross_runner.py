# -*- coding: utf-8 -*-
import subprocess
import sys
import os.path
import re
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

def parse_check_log(log_f):
    log = open(log_f,'r')
    bugs = {}
    bogus_forms = {}

    formula = re.compile('.*ltl:(\d+): (.*)$')
    empty_line = re.compile('^\s$')
    problem = re.compile('error: .* nonempty')

    for line in log:
        m_form = formula.match(line)
        if m_form:
            form = m_form
            f_bugs = []
        m_empty = empty_line.match(line)
        if m_empty:
            if len(f_bugs) > 0:
                form_id = int(form.group(1))-1
                bugs[form_id] = f_bugs
                bogus_forms[form_id] = form.group(2)
        m_prob = problem.match(line)
        if m_prob:
            f_bugs.append(m_prob.group(0))
    log.close()
    tools = parse_log_tools(log_f)
    return bugs, bogus_forms, tools

def parse_log_tools(log_f):
    log = open(log_f,'r')
    tools = {}
    tool = re.compile('.*\[(P\d+)\]: (.*)$')
    empty_line = re.compile('^\s$')
    for line in log:
        m_tool = tool.match(line)
        m_empty = empty_line.match(line)
        if m_empty:
            break
        if m_tool:
            tid = m_tool.group(1)
            tcmd = m_tool.group(2)
            tools[tid] = tcmd
    log.close()
    return tools

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
                     save_bogus=True, tool_subset=None,
                     forms = True, escape_tools=False):
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
        if escape_tools:
            tools_strs = ["'{}'".format(t_str) for t_str in tools_strs]
        args = tools_strs
        if forms:
            args +=  ' '.join(['-F '+F for F in self.f_files]).split()
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
                     save_bogus=True, tool_subset=None,
                     forms=True, lcr='ltlcross'):
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
                                    save_bogus, tool_subset, forms,
                                    escape_tools=True)
        return ' '.join([lcr] + args)

    def run_ltlcross(self, args=None, automata=True,
                     check=False, timeout='300',
                     log_file=None, res_file=None,
                     save_bogus=True, tool_subset=None,
                     lcr='ltlcross'):
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
        cmd = self.ltlcross_cmd(args,lcr=lcr)
        print(cmd, file=log)
        print(datetime.now().strftime('[%d.%m.%Y %T]'), file=log)
        print('=====================', file=log,flush=True)
        self.returncode = subprocess.call([lcr] + args, stderr=subprocess.STDOUT, stdout=log)
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
        # Add incorrect columns to track flawed automata
        if not 'incorrect' in res.columns:
            res['incorrect'] = False
        # Removes unnecessary parenthesis from formulas
        res.formula = res['formula'].map(pretty_print)

        form = pd.DataFrame(res.formula.drop_duplicates())
        form['form_id'] = range(len(form))
        form.index = form.form_id

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

        # Store incorrect and exit_status information separately
        self.incorrect = table[['incorrect']]
        self.incorrect.columns = self.incorrect.columns.droplevel()
        self.exit_status = table[['exit_status']]
        self.exit_status.columns = self.exit_status.columns.droplevel()

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

    def smaller_than(self, t1, t2, reverse=False,
                     restrict=True,
                     col='states', restrict_cols=True):
        """Returns a dataframe with results where ``col`` for ``tool1``
        has strictly smaller value than ``col`` for ``tool2``.

        Parameters
        ----------
        t1 : String
            name of tool for comparison (the better one)
            must be among tools
        t2 : String
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
        return self.better_than(t1,t2,reverse=reverse,
                    props=[col],include_fails=False,
                    restrict_cols=restrict_cols,
                    restrict_tools=restrict)

    def better_than(self, t1, t2, props=['states','acc'],
                    reverse=False, include_fails=True,
                    restrict_cols=True,restrict_tools=True
                    ):
        """Compares ``t1`` against ``t2`` lexicographicaly
        on cols from ``props`` and returns DataFrame with
        results where ``t1`` is better than ``t2``.

        Parameters
        ----------
        t1 : String
            name of tool for comparison (the better one)
            must be among tools
        t2 : String
            name of tool for comparison (the worse one)
            must be among tools
        props : list of Strings, default (['states','acc'])
            list of columns on which we want the comparison (in order)
        reverse : Boolean, default ``False``
            if ``True``, it switches ``t1`` and ``t2``
        include_fails : Boolean, default ``True``
            if ``True``, include formulae where t2 fails and t1 does not
            fail
        restrict_cols : Boolean, default ``True``
            if ``True``, the returned DataFrame contains only the compared
            property columns
        restrict_tools : Boolean, default ``True``
            if ``True``, the returned DataFrame contains only the compared
            tools
        """
        if t1 not in list(self.tools.keys())+self.mins:
            raise ValueError(t1)
        if t2 not in list(self.tools.keys())+self.mins:
            raise ValueError(t2)
        if reverse:
            t1, t2 = t2, t1
        v = self.values
        t1_ok = self.exit_status[t1] == 'ok'
        if include_fails:
            t2_ok = self.exit_status[t2] == 'ok'
            # non-fail beats fail
            c = v[t1_ok & ~t2_ok]
            # We work on non-failures only from now on
            eq = t1_ok & t2_ok
        else:
            c = pd.DataFrame()
            eq = t1_ok
        for prop in props:
            # For each prop we add t1 < t2
            better = v[prop][t1] < v[prop][t2]
            # but only from those which were equivalent so far
            equiv_and_better = v.loc[better & eq]
            c = c.append(equiv_and_better)
            # And now choose those equivalent also on prop to eq
            eq = eq & (v[prop][t1] == v[prop][t2])

        # format the output
        idx = pd.IndexSlice
        tools = [t1,t2] if restrict_tools else slice(None)
        props = props if restrict_cols else slice(None)
        return c.loc[:,idx[props,tools]]

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

    def id_of_form(self, f, convert=False):
        """Returns id of a given formula. If ``convert`` is ``True``
        it also calls ``bogus_to_lcr`` first.
        """
        if convert:
            f = bogus_to_lcr(f)
        ni = self.values.index.droplevel(0)
        return ni.get_loc(f)

    def mark_incorrect(self, form_id, tool,output_file=None,input_file=None):
        """Marks automaton given by the formula id and tool as flawed
        and writes it into the .csv file
        """
        if tool not in self.tools.keys():
            raise ValueError(tool)
        # Put changes into the .csv file
        if output_file is None:
            output_file = self.res_file
        if input_file is None:
            input_file = self.res_file
        csv = pd.read_csv(input_file)
        if not 'incorrect' in csv.columns:
            csv['incorrect'] = False
        cond = (csv['formula'].map(pretty_print) ==
                pretty_print(self.form_of_id(form_id,False))) &\
                (csv.tool == tool)
        csv.loc[cond,'incorrect'] = True
        csv.to_csv(output_file,index=False)

        # Mark the information into self.incorrect
        self.incorrect.loc[self.index(form_id)][tool] = True

    def na_incorrect(self):
        """Marks values for flawed automata as N/A. This causes
        that the touched formulae will be removed from cummulative
        etc. if computed again. To reverse this information you
        have to parse the results again.

        It also sets ``exit_status`` to ``incorrect``
        """
        self.values = self.values[~self.incorrect]
        self.exit_status[self.incorrect] = 'incorrect'

    def index(self, form_id):
        return (form_id,self.form_of_id(form_id,False))

    def get_error_count(self,err_type='timeout'):
        """Returns a Series with total number of er_type errors for
        each tool.

        Parameters
        ----------
        err_type : String one of `timeout`, `parse error`,
                                 `incorrect`, `crash`, or
                                 'no output'
                  Type of error we seek
        """
        if err_type not in ['timeout', 'parse error',
                            'incorrect', 'crash',
                            'no output']:
            raise ValueError(err_type)

        if err_type == 'crash':
            c1 = self.exit_status == 'exit code'
            c2 = self.exit_status == 'signal'
            return (c1 | c2).sum()
        return (self.exit_status == err_type).sum()

    def cross_compare(self,tools=None,props=['states','acc'],
                      include_fails=True):
        if tools is None:
            tools = self.tools.keys()
        c = pd.DataFrame(index=tools, columns=tools).fillna(0)
        for tool in tools:
            c[tool] = pd.DataFrame(c[tool]).apply(lambda x:
                      len(self.better_than(x.name,tool,props,
                               include_fails=include_fails)), 1)
        return c
