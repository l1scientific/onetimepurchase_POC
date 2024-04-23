# ddb_helper.py
# this is my helper function for dealing with dynamoDB


import datetime
import dateutil.parser

def init_attr(  ):
    attr = {}
    attr['ended_session_count'] = 0
    attr['launch_count'] = 1
    
    attr['listen_state'] = 'ENDED'
    attr['listen_time'] = 0
    attr['previous_listen_id'] = 'None'
    attr['current_listen_id'] = 'None'
    attr['current_listen_title'] = 'None'
    attr['current_listen_segment'] = 1
    attr['is_currently_listening'] = False

    return attr

#x = init_attr( )

############################################################################
# for test purposes load teh cbc doc
def load_CBC_test_data( cbcnum, max_seg_size=2500 ):
    fname = 'testdata/CBCtest' + str(cbcnum) + '.txt'
    data_dict = {}
    curr_field = ''
    curr_text = ''
    text_array = []
    with open( fname,'r') as xfile:
        while 1:
            x = xfile.readline()
            if x =='':
                break
            # remove bad chars
                        
            if '=== ' in x and x.find( '=== ' )==0:
                x = x.replace('\n','' )
                # store new field name as xfield
                xfield = x.split(' ')[1]
                
                data_dict[xfield] = ''
                
                    
                data_dict[curr_field]=curr_text
                curr_field = xfield
                curr_text = ''               
                    
                    
                    
            else:
                curr_text += x
                if xfield == 'body':
                    y = x.strip().rstrip()
                    if not len(y)==0:
                        text_array.append( x )
        data_dict[ curr_field ] = curr_text
    # convert date to datetime object
    if 'date' in data_dict:
        s = data_dict['date']
        c0 = s.find(':')
        c1 = s.find('|')
        s = s[c0+1:c1]
        
        
        dval = dateutil.parser.parse( s )        
        data_dict['date' ] = dval
                
        
        
    # now check if we need to segment the body
    # and use text_array to do it
    #data_dict['text_array'] = text_array
    # split data into segments
    seg_num = 1
    data_dict['body'] = {'1':text_array[0]}
    for ii in range( 1, len(text_array) ):
        x = text_array[ii]
        clen = len(data_dict['body'][ str(seg_num) ])
        xlen = len( x )
        if xlen + clen > max_seg_size:
            seg_num += 1
            data_dict['body'][ str(seg_num) ] = x
        else:
            data_dict['body'][ str(seg_num) ] +=  x
    # adjust empty author field
    if 'author' in data_dict:
        a = data_dict['author']
        a = a.strip().rstrip()
        data_dict['author'] = a
    return data_dict












############################################################################
# parse the article dictionary returned by my server
# segment the body and return a useful dict
def parse_article_obj( data_dict, max_seg_size=2500 ):
    
    
    text_array = data_dict[ 'body' ].split( '\n' )
    
   # convert date to datetime object
    if 'date' in data_dict:
        s = data_dict['date']
        c0 = s.find(':')
        c1 = s.find('|')
        s = s[c0+1:c1]
        
        
        dval = dateutil.parser.parse( s )        
        data_dict[ 'date' ] = dval
                
        
        
    # now check if we need to segment the body
    # and use text_array to do it
    #data_dict['text_array'] = text_array
    # split data into segments
    seg_num = 1
    data_dict['body'] = {'1':text_array[0]}
    for ii in range( 1, len(text_array) ):
        x = text_array[ii]
        clen = len(data_dict['body'][ str(seg_num) ])
        xlen = len( x )
        if xlen + clen > max_seg_size:
            seg_num += 1
            data_dict['body'][ str(seg_num) ] = x
        else:
            data_dict['body'][ str(seg_num) ] +=  x
    # adjust empty author field
    if 'author' in data_dict:
        a = data_dict['author']
        a = a.strip().rstrip()
        data_dict['author'] = a
    return data_dict




############################################################################
# parse the test folder
def parse_test_data( ):

    import os, shutil
    source_dir = 'testdata/raw/'
    save_dir = 'testdata/'
    
    z = os.listdir( source_dir )
    n = 1
    for d in z:
        f0 = source_dir + d
        f1 = save_dir + 'CBCtest' + str(n) + '.txt'
        n += 1
        shutil.copyfile(f0, f1)
        


############################################################################
r"""
parse_test_data()
import os
z = os.listdir( 'testdata/')
max_p_size = 0
for f in z:
    if not '.txt' in f:
        continue
    t = f.split('CBCtest')
    t = t[1].split('.')[0]
    X = load_CBC_test_data( int(t) )
    print('number of segments', len(X['body'] ) )
    aa = input()
        
print('the max p size is', max_p_size )
"""











    








    
