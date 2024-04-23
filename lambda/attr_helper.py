# attr_helper.py
# helper for initializing attributes
import datetime
    
    





######################################################################
# helper to initialize persistent attributes
def init_p_attr(  ):
    attr = {}

    attr['sub_period_end'] = ""

    # track launches and closes
    attr['ended_session_count'] = 0
    attr['launch_count'] = 1
    
    attr['ad_weights'] = []
    attr['ad_frequency'] = None

    attr['help_count'] = 1
    
    attr['current_speed']  = 'medium'
    attr['listen_state'] = 'ENDED'
    attr['listen_time'] = 0

    attr['num_of_ads'] = 0
    attr['ad_playing'] = False
        
    # store current publisher/publication/article
    # data in a dict
    # fid: flask db id
    # name: name of publisher
    # desc: description
    # npubs: number of publications
    # aid: index of item on alexa listing (may differ from fid)
    attr['current_publisher'] = {'fid':'NULL',
                                 'name':'NULL',
                                 'desc':'NULL',
                                 'num_publications':'NULL',
                                 'publication_name_list':[],
                                 'publication_id_list':[],
                                 'publication_region_list':[],
                                 'last_listen':'null',
                                 'publisher_ads':{}
                                 }
                                 
    
    
    attr['current_publication'] = {'fid':'NULL',
                                 'title':'NULL',
                                 'desc':'NULL',
                                 'date':'NULL',
                                 'neditions':'NULL',
                                 'publisher_name':'NULL',
                                   'xkey_required':False,
                                   'xkey_val':'NULL',
                                    'presented_edition_list_length':0,
                                   'is_selected':False,
                                   'publication_ads':{}}
    
                                 
    attr['current_edition'] = {'fid':'NULL',
                                 'title':'NULL',
                                 'desc':'NULL',
                                 'date':'NULL',
                                 'narticles':'NULL',
                                 'publisher_name':'NULL',
                                   'xkey_required':False,
                                   'xkey_val':'NULL' }


    attr['current_listen'] = {'fid':'NULL',
                                 'title':'NULL',
                                 'body':'NULL',
                                 'author':'NULL',
                                 'date_published':'NULL',
                              'segment':1 }
       
    
    attr['current_region'] = {}
    
    attr['favourites_list'] = []

    attr['xkeys'] = {}
    attr['is_currently_listening'] = False
    attr['has_active_doc'] = False
    attr['document_type'] = 'NEWS'
    # set the external user ID to default value, but only if it doesn't exist
    # since I don't want to reset it
    
    attr['current_publications_desc_list'] = []
    attr['current_publications_name_list'] = []
    attr['current_publications_id_list'] = []
    attr['current_publications_edition_count_list'] = []

    return attr

#########################################################################
def update_p_attr( p_attr, data_dict ):
    p_attr['current_listen']['body'] = {}
    for b in data_dict['body']:
        p_attr['current_listen']['body'][b] = data_dict['body'][b]

    p_attr['current_listen']['title'] = data_dict['title']

    p_attr['current_listen']['segment'] = 1
               
    return p_attr





###########################################################################
def clear_current_pubs( p_attr ):
    p_attr['current_publications_desc_list'] = []
    p_attr['current_publications_name_list'] = []
    p_attr['current_publications_id_list'] = []
    p_attr['current_publications_edition_count_list'] = []

    return p_attr





########################################################################
def init_xuserID(  p_attr ):
    if not 'xuserID' in p_attr:
        p_attr['xuserID' ] = '-1'

    return p_attr


###########################################################################################
# initialize the sessional attribute ##############################
def init_s_attr( ):
    attr = {}

    # SUBSCRIPTION ATTRIBUTES
    attr['list_of_isps'] = []
    attr['purchased_isps'] = []

    #
    attr[ 'publisher_id_map' ] = {}
    attr[ 'publication_id_map' ] = {}
    attr[ 'edition_id_map' ] = {}
    attr[ 'art_id_map' ] = {}
    attr['enter_xkey'] = False

    attr['current_menu'] = 'null'
    attr['booknews_val'] = 'news'

    attr[ 'reset_pub_list' ] = False

    attr[ 'resuming_from_yesno' ] = False

    attr[ 'x_entity' ] = []
    attr['x_slotname' ] = ''

    attr['error_code'] = 0

    attr['in_help'] = False

    attr['first_time_mainmenu'] = True

    attr['should_play_ad'] = False
    attr['ad_finish_time'] = 0.0



    return attr





