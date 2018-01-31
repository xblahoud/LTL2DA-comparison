def ltl_to_ba(tgba=False):
    spot_n = 'Spot'
    spot_o = '' if tgba else ' -B'
    ltl3ba_n = 'LTL3BA'
    ltl3ba_o = ' -H2' if tgba else ' -H3' 
    ba_suff = '/TGBA' if tgba else '/NBA'
    tools = {
        '{}{}'.format(spot_n,ba_suff) :  \
            'ltl2tgba{} -f %f'.format(spot_o),
        '{}{}'.format(ltl3ba_n,ba_suff) :  \
            'ltl3ba -M0{} -f %s'.format(ltl3ba_o),
        '{}d{}'.format(ltl3ba_n,ba_suff) :  \
            'ltl3ba -M1{} -f %s'.format(ltl3ba_o),
    }
    if tgba:
        tools['LTL3TELA/DTELA'] = 'ltl3tela -f %f'
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

def get_tools(fragment='full'):
    rab4 = 'Rab4/bin/'
    sacc = ' | autfilt -S > %O'
    rabinizers = {
        "R3//DTGRA": 'java -jar Rab3/rabinizer3.1.jar -silent -format=hoa -out=std %[eiRWM]f > %O',
        "R3//DSRA" : 'java -jar Rab3/rabinizer3.1.jar -silent -format=hoa -out=std -auto=sr %[eiRWM]f > %O',
        "R4//DTGRA": rab4 + 'ltl2dgra %f > %O',
        "R4//DSRA" : rab4 + 'ltl2dra %f' + sacc
    }
    ltl3dra = {
        "LTL3DRA//DTGRA" : 'ltl3dra -f %s > %O',
        "LTL3DRA//DSRA" : 'ltl3dra -H3 -f %s > %O'
    }
    ltl2tgba = {
        "ltl2tgba//DPA"      : 'ltl2tgba -DG -f %f > %O',
    }
    parity = {
        "ltl2dpa/ldba/DTPA"      : rab4 + 'ltl2dpa --mode=ldba %f > %O',
        "ltl2dpa/Rab/DTPA"       : rab4 + 'ltl2dpa --mode=rabinizer %f > %O',
    }
    
    # name, command, generalized, dstar_interface, acc
    determinization_tools = [
        ('Spot','autfilt -DG', False, False, 'DTPA'),
        ('Spot','autfilt -DG', True, False, 'DTPA'),
        ('ltl2dstar','ltl2dstar -H', False, True, 'DSRA'),
        ('ltl2dstar(NBA)','ltl2dstar -B -H - -', False, False, 'DSRA')
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

full_tools = get_tools()
ltl3dra_tools = get_tools('ltl-gux')
direct = ['LTL3DRA','R3','R4']
safra = ['ltl2dstar','ltl2dstar(NBA)','Spot','ltl2tgba']
ltl2dpa = ['ltl2dpa']
tool_order = direct + safra + ltl2dpa
