def ltl_to_ba(tgba=False):
    spot_n = 'Spot'
    spot_o = '' if tgba else ' -B'
    ltl3ba_n = 'LTL3BA'
    ltl3ba_o = ' -H2' if tgba else ' -H3' 
    ba_suff = '/TGB' if tgba else '/SB'
    tools = {
        '{}{}'.format(spot_n,ba_suff) :  \
            'ltl2tgba{} -f %f'.format(spot_o),
        '{}{}'.format(ltl3ba_n,ba_suff) :  \
            'ltl3ba -M0{} -f %s'.format(ltl3ba_o),
        '{}d{}'.format(ltl3ba_n,ba_suff) :  \
            'ltl3ba -M1{} -f %s'.format(ltl3ba_o),
    }
    if tgba:
        tools['LTL3TELA/TEL'] = 'ltl3tela -f %f'
    return tools

def det_pair(det_tool, ltl_to_ba, dstar=False):
    '''produces a dictionary that combines tool for
    determinization with tools for LTL->BA translation
    
    Parameters
    ----------
    `det_tool`  : a pair of `name` and `command`
    `ltl_to_ba` : a `dict` of name->command
    `dstar`     : `Bool` that indicates whether to use ltl2dstar interface
    '''
    if not dstar:
        tools = {
            '{}/{}.{}'.format(det_tool[0],name,det_tool[2]) :
                '{} | {} > %O'.format(cmd,det_tool[1]) for
                    name, cmd in ltl_to_ba.items()
        }
    else:
        tools = {
            '{}/{}.{}'.format(det_tool[0],name,det_tool[2]) :
                '{} -t "{} > %%H" %L %O'.format(det_tool[1],cmd.replace('%s','%%s').replace('%f','%%s')) for
                    name, cmd in ltl_to_ba.items()
    }
    return tools

def get_tools(fragment='ltl-gux'):
    rab4 = 'Rab4/bin/'
    sacc = ' | autfilt --sbacc > %O'
    rabinizers = {
        "R3//TGR": 'java -jar Rab3/rabinizer3.1.jar -silent -format=hoa -out=std %[eiRWM]f > %O',
        "R3//SR" : 'java -jar Rab3/rabinizer3.1.jar -silent -format=hoa -out=std -auto=sr %[eiRWM]f > %O',
        "R4//TGR": rab4 + 'ltl2dgra %f > %O',
        "R4//SR" : rab4 + 'ltl2dra %f' + sacc
    }
    ltl3dra = {
        "LTL3DRA//TGR" : 'ltl3dra -f %s > %O',
        "LTL3DRA//SR" : 'ltl3dra -H3 -f %s > %O'
    }
    ltl2tgba = {
        "ltl2tgba//TP"      : 'ltl2tgba -DG -f %f > %O',
    }
    parity = {
        "ltl2dpa/ldba/TP"      : rab4 + 'ltl2dpa --mode=ldba %f > %O',
        "ltl2dpa/Rab/TP"       : rab4 + 'ltl2dpa --mode=rabinizer %f > %O',
    }
    
    # name, command, generalized, dstar_interface, acc
    determinization_tools = [
        ('Spot','autfilt -DG', False, False, 'TP'),
        ('Spot','autfilt -DG', True, False, 'TP'),
        ('ltl2dstar','ltl2dstar -H', False, True, 'SR'),
        ('ltl2dstar(NBA)','ltl2dstar -B -H - -', False, False, 'SR')
    ]
    
    tools = {}
    tools.update(rabinizers)
    tools.update(ltl2tgba)
    tools.update(parity)
    
    for tool in determinization_tools:
        tools.update(det_pair((tool[0],tool[1],tool[4]),ltl_to_ba(tool[2]),tool[3]))
    
    if fragment == 'ltl-gux' or fragment == 'ltlgux':
        tools.update(ltl3dra)
    return tools

def mint(s):
    return("\\mintinline{bash}{"+s+"}")

def latex(tools, decompose=True):
    for name, cmd in sorted(tools.items()):
        if decompose:
            name = ' & '.join(name.split('/'))
        print("    & {}\n    & {}\\\\".format(name,mint(cmd)))

full_tools = get_tools('full')
ltl3dra_tools = get_tools('ltl-gux')
direct = ['LTL3DRA','R3','R4']
safra = ['ltl2dstar','ltl2dstar(NBA)','Spot','ltl2tgba']
ltl2dpa = ['ltl2dpa']
mt_ord = direct + safra + ltl2dpa
it_ord = ['LTL3BA', 'LTL3BAd', 'LTL3TELA', 'Spot',
          '', 'ldba', 'Rab']
acc_ord = ['TGR','SR',
           'TGB.TP','SB.TP','TEL.TP',
           'SB.SR',
           'TP']

def sort_tools(fragment='ltl-gux'):
    tool_order = []
    for mt in mt_ord:
        for it in it_ord:
            for acc in acc_ord:
                for t in get_tools(fragment).keys():
                    if t == '{}/{}/{}'.format(mt,it,acc):
                        tool_order.append(t)
    return tool_order

tool_order = sort_tools('ltl-gux')

def fix_tool(tool,fill_lines=True,fill='\\hfill'):
    tool = tool.replace('//','/---/')
    tool = tool.replace('R3','Rabinizer 3').replace('R4','Rabinizer 4')
    tool = tool.replace('TEL.TP','TEL.TEL')
    if tool.startswith('Spot/'):
        tool = 'Spot (autf.)/' + tool[5:]
    tool = tool.replace('ltl2tgba','Spot')
    if fill_lines:
        split = tool.split('/')
        widths = [6.1,4.6,3.8]
        flush = ['\\raggedright','\\centering','\\raggedleft']
        if len(split) == 3:
            tmp = ['\\parbox[b]{{{}em}}{{{} {}{}}}'.format(widths[i],
                    flush[i],split[i],fill) for i in range(len(split))]
            tool = ''.join(tmp)
    return tool

if __name__ == '__main__':
    from evaluation_utils import to_tuples

    def mint(s):
        return("\\mintinline{bash}{"+s+"}")

    order = sort_tools()
    tools = get_tools()
    print('''\\begin{{tabular}}{{lll}}
\\toprule
type & {} & ltlcross command \\\\'''.format(
    fix_tool('name/interm./acc')
    ))
    for way, w_tools in \
        zip(['direct', 'Safra', 'other'],
            [direct, safra, ltl2dpa]):
        #get count for multirow
        c = 0
        for t in order:
            main = to_tuples([t])[0][0]
            if main in w_tools:
                c += 1
                if main == 'R3':
                    c += 1
        print('\\midrule')
        print('\\multirow{{{}}}{{*}}{{{}}}'.format(c,way))
        # print tools
        for t in order:
            main = to_tuples([t])[0][0]
            if main in w_tools:
                if main != 'R3':
                    print('  & {}\n  & {}\\\\\n%'.\
                      format(fix_tool(t),mint(tools[t])))
                else:
                    cmd = tools[t]
                    first, second = cmd.split('-f')
                    second = '-f' + second
                    first += '\\ '
                    print('''  & {}\n  & {}\\\\
 & & {}\\\\
 %'''.format(fix_tool(t),mint(first),mint(second)))
    print('\\bottomrule\n\\end{tabular}\n')