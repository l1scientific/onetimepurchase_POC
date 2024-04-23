# intenthelper.py
# this script fills in the logic for each intent.
# functions should return speech text, reprompts, and the
# persistent and session attributes.

import datetime
import time
import random

import parsing_helper as ph
import fetch_helper as fh
import attr_helper
import re
from ask_sdk_model.er.dynamic import (
    UpdateBehavior,
    EntityListItem,
    Entity,
    EntityValueAndSynonyms,
)

import utils

# Test sync comment 3




######################################################################
# launch_helper
# handle logic for invocation
def launch_helper(p_attr, s_attr):
    stext = ""  # speech text
    rtext = ""  # reprompt text

    random.seed() #https://docs.python.org/3/library/random.html by python docs, if the parameter 'a' is ommitted then system time is used

    # initialize persistent attributes
    if not p_attr:
        p_attr = attr_helper.init_p_attr()

    # initialize sessional attributes
    s_attr = s_attr_updater(s_attr)

    s_attr["is_publication_selected"] = False
    s_attr["is_edition_selected"] = False
    s_attr["yesno_question"] = "NULL"
    s_attr["resuming_from_yesno"] = False
    s_attr["is_currently_listening"] = False
    
    # check xuserID
    p_attr = attr_helper.init_xuserID(p_attr)

    # contact the server to create our ID
    print("xxx calling fetch_init xxx")
    s1, r1, p_attr, s_attr, error_code = fh.fetch_init(p_attr, s_attr)
    print("ooo done fetch init call ooo")

    if error_code == 1:
        s_attr["error_code"] = 1
        return s1, r1, p_attr, s_attr

    print("---- I am here ----")
    # populate location entity
    l_entity = []
    ii = 1
    for xloc in p_attr["xlocations"]:
        s = EntityValueAndSynonyms(value=xloc, synonyms=[])
        p = Entity(id=str(ii), name=s)
        l_entity.append(p)
        ii += 1

    # modify response if it is the first listen
    s_attr["l_entity"] = l_entity
    s_attr["current_menu"] = "launch"

    if p_attr["launch_count"] == 1:
        stext = (
            "Welcome to the CBC subscription prototype. "  ##s_attr['help_response']['welcome-message'][0]
        )
        rtext = stext
        # rtext = ' To proceed, request a publication by name, or ask for a list of publications or a list of regions. '
        s_attr["last_speak"] = stext

    elif (
        not "last_listen" in p_attr["current_publisher"]
        or p_attr["current_publisher"]["last_listen"] == "null"
        or not p_attr["current_publisher"]["last_listen"]
        in p_attr["current_publisher"]["publication_name_list"]
    ):
        stext = "Welcome back to the CBC subscription prototype. "  # s_attr['help_response']['welcome-message'][1]
        rtext = stext
        s_attr["last_speak"] = stext

    else:
        stext = "Welcome back to the CBC subscription prototype. "  ##s_attr['help_response']['welcome-message'][2]
        # stext += 'Would you like to continue reading the '  + ph.cleanse_spec_chars(p_attr['current_publisher']['last_listen']) + '?'
        rtext = stext
        s_attr["last_speak"] = stext
        s_attr["yesno_question"] = "resume-last-listen"

 

    # reset persistent attributes
    p_attr["current_edition"]["genre_selected"] = "all_genres"
    p_attr["current_region"]["name"] = "NULL"

    # lock in the lone publication
    sdummy, rdummy, p_attr, s_attr = select_publication_helper(p_attr, s_attr)
    # stext += sdummy
    # rtext += rdummy

    if (len(s_attr['purchased_isps']) != 0) and (p_attr['sub_period_end'] == ""):
        stext += "It looks like you are in test mode, and recently reset your attributes after a previous purchase. Before you can proceed, please say cancel your subscription. "
        return stext, rtext, p_attr, s_attr

    if (len(s_attr['purchased_isps']) == 0) and ((p_attr['sub_period_end'] == "") or (datetime.datetime.strptime(p_attr['sub_period_end'], '%Y-%m-%d') < datetime.datetime.now())):
        stext += "You currently have the free version of the CBC Narrator. You will periodically hear ads before and between CBC articles. If you would like to remove all ads from playing, say 'buy a subscription' to hear your options. "  

    elif ((len(s_attr['purchased_isps']) == 0) and (datetime.datetime.strptime(p_attr['sub_period_end'], '%Y-%m-%d') > datetime.datetime.now())) or (len(s_attr['purchased_isps']) != 0):
        
        today = datetime.datetime.now()
        sub_end = datetime.datetime.strptime(p_attr['sub_period_end'], '%Y-%m-%d')
        days_remaining_to_sub_end = (sub_end - today).days

        print(sub_end)
        print(today)

        if (days_remaining_to_sub_end < 0):

            if s_attr['purchased_isps'][0].reference_name == 'monthly':

                sub_day = sub_end.day
                next_date = ph.next_monthly_occurrence(sub_day)
                p_attr['sub_period_end'] = next_date.strftime('%Y-%m-%d')

            elif s_attr['purchased_isps'][0].reference_name == 'yearly':

                sub_day = sub_end.day
                sub_month = sub_end.month
                next_date = ph.next_yearly_occurrence(sub_month, sub_day)
                p_attr['sub_period_end'] = next_date.strftime('%Y-%m-%d')

            days_remaining_to_sub_end = (next_date - today).days

        stext += f"You currently have {days_remaining_to_sub_end} days remaining in your current subscription period. "   
    
    stext += "Feel free to ask for help at any time. "    

    #elif :
    #    stext += "It looks like you are in test mode, and recently reset your attributes after a previous purchase. Before you can proceed, please say cancel your subscription. "
    #    return stext, rtext, p_attr, s_attr
    

    # load and list the genres
    s_attr["x_slotname"] = "GENRE_SLOT"
    stemp, rtemp, p_attr, s_attr = listgenres_helper(p_attr, s_attr)
    stext += stemp
    rtext += rtemp

    s_attr["last_reprompt"] = rtext

    p_attr["launch_count"] += 1

    print(f"PUB ADS: {p_attr['current_publisher']['publisher_ads']}")
    return stext, rtext, p_attr, s_attr





##################### help menu helper #####################
def help_helper(p_attr, s_attr):
    stext = ""
    rtext = ""
    if (s_attr["in_help"] == False) and (s_attr["current_menu"] == "reading-article"):
        s_attr["old_yesno_question"] = s_attr["yesno_question"]
        s_attr["yesno_question"] = "resume-current-article"

    if s_attr["in_help"] == False:
        s_attr["help_start"] = time.time()
        s_attr["in_help"] = True
        s_attr["old_last_speak"] = s_attr["last_speak"]
        s_attr["old_last_reprompt"] = s_attr["last_reprompt"]

    # build help message depending on the current menu
    if p_attr["help_count"] == 1:
        stext += s_attr["help_response"]["help-welcome"][0]

    p_attr["help_count"] += 1

    if s_attr["current_menu"] == "launch":
        stext += s_attr["help_response"]["launch"][0]

    # elif s_attr['current_menu'] == 'list-publications':
    #     stext += 'You are currently in the ' +(p_attr['current_publisher']['name']) + ' publication menu. '
    #     stext += s_attr['help_response']['list-publications'][0]

    # elif s_attr['current_menu'] == 'list-regions':
    #     stext += 'You are currently in the ' + (p_attr['current_publisher']['name']) + ' region menu. '
    #     stext += s_attr['help_response']['list-regions'][0]

    # elif s_attr['current_menu'] == 'list-publicationsbyregion':
    #     stext += 'You are currently in the ' + (p_attr['current_publisher']['name']) + ', '
    #     stext += p_attr['current_region']['name'] + ' publication menu. '
    #     stext += s_attr['help_response']['list-publicationsbyregion'][0]

    elif s_attr["current_menu"] == "list-editions":
        stext += (
            "You are currently in the "
            + (p_attr["current_publication"]["title"])
            + " edition menu. "
        )
        stext += s_attr["help_response"]["list-editions"][0]

    elif s_attr["current_menu"] == "list-articletitles":
        stext += (
            "You are currently in the " + (p_attr["current_publication"]["title"]) + " "
        )
        stext += str(p_attr["current_edition"]["title"]) + " article menu. "
        stext += s_attr["help_response"]["list-articletitles"][0]

    elif s_attr["current_menu"] == "list-articlesbygenre":
        stext += (
            "You are currently in the " + (p_attr["current_publication"]["title"]) + " "
        )
        stext += str(p_attr["current_edition"]["title"]) + " "
        stext += p_attr["current_edition"]["genre_selected"] + " article menu. "
        stext += s_attr["help_response"]["list-articlesbygenre"][0]

    elif s_attr["current_menu"] == "list-genres":
        stext += (
            "You are currently in the " + (p_attr["current_publication"]["title"]) + " "
        )
        stext += str(p_attr["current_edition"]["title"]) + " genre menu. "
        stext += s_attr["help_response"]["list-genres"][0]

    elif s_attr["current_menu"] == "reading-article":
        stext += (
            "You are currently listening to "
            + p_attr["current_listen"]["cleansed_title"]
            + ". "
        )
        stext += s_attr["help_response"]["reading-article"][0]

    elif not s_attr["current_menu"] in s_attr["help_response"]:
        stext += (
            "I am not sure which menu you are currently in. "
            "Try saying main menu to return to the launch menu and restart your search. "
        )

    # add the correct prompt depending on users current state
    if s_attr["currently_paused"] == True:
        aURL = "https://bppxmedia.s3.us-west-2.amazonaws.com/Walter_pause.mp3"

        stext += "I will now continue to pause.  Interrupt me and say resume "
        stext += " when you want to continue. "
        stext += '<audio src="' + aURL + '" />  Shall I resume?'
        rtext = "I can pause a little longer. "
        rtext += '<audio src="' + aURL + '" />  Do you want me to continue?'

        return stext, rtext, p_attr, s_attr

    elif s_attr["current_menu"] == "reading-article":
        s_attr["pause_time"] = time.time()

        stext += "Would you like to resume the current article? "
        rtext = "Would you like to resume the current article? "

        s_attr["resuming_from"] = "help-menu"

        s_attr["last_speak"] = stext
        s_attr["last_reprompt"] = rtext

        return stext, rtext, p_attr, s_attr

    else:
        stext += "Try a command to continue, or ask for more help. "
        rtext = "Try a command to continue, or, say Repeat to hear this message again. "
        s_attr["in_help"] = False

    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    return stext, rtext, p_attr, s_attr


##################### more help menu helper #####################
def morehelp_helper(p_attr, s_attr):
    stext = ""
    rtext = ""
    if (s_attr["in_help"] == False) and (s_attr["current_menu"] == "reading-article"):
        s_attr["old_yesno_question"] = s_attr["yesno_question"]
        s_attr["yesno_question"] = "resume-current-article"

    if s_attr["in_help"] == False:
        s_attr["in_help"] = True
        s_attr["help_start"] = time.time()
        s_attr["old_last_speak"] = s_attr["last_speak"]
        s_attr["old_last_reprompt"] = s_attr["last_reprompt"]

    # build help message depending on the current menu
    if p_attr["help_count"] == 1:
        stext += s_attr["help_response"]["help-welcome"][0]

    p_attr["help_count"] += 1

    if s_attr["current_menu"] == "launch":
        stext += s_attr["help_response"]["launch"][0]

    # elif s_attr['current_menu'] == 'list-publications':
    #     stext += s_attr['help_response']['list-publications'][1]

    # elif s_attr['current_menu'] == 'list-regions':
    #     stext += s_attr['help_response']['list-regions'][1]

    # elif s_attr['current_menu'] == 'list-publicationsbyregion':
    #     stext += 'Only publications in ' + p_attr['current_region']['name'] + ' are available in this menu. '
    #     stext += s_attr['help_response']['list-publicationsbyregion'][1]

    elif s_attr["current_menu"] == "list-editions":
        stext += s_attr["help_response"]["list-editions"][1]

    elif s_attr["current_menu"] == "list-articletitles":
        stext += s_attr["help_response"]["list-articletitles"][1]

    elif s_attr["current_menu"] == "list-articlesbygenre":
        stext += (
            "Only articles in "
            + p_attr["current_edition"]["genre_selected"]
            + " are available in this menu. "
        )
        stext += s_attr["help_response"]["list-articlesbygenre"][1]

    elif s_attr["current_menu"] == "list-genres":
        stext += s_attr["help_response"]["list-genres"][1]

    elif s_attr["current_menu"] == "reading-article":
        stext += s_attr["help_response"]["reading-article"][1]

    elif not s_attr["current_menu"] in s_attr["help_response"]:
        stext += (
            "I am not sure which menu you are currently in. "
            "Try saying main menu to return to the launch menu and restart your search. "
        )

    # add the correct prompt depending on users current state
    if s_attr["currently_paused"] == True:
        aURL = "https://bppxmedia.s3.us-west-2.amazonaws.com/Walter_pause.mp3"

        stext += "I will now continue to pause.  Interrupt me and say resume "
        stext += " when you want to continue. "
        stext += '<audio src="' + aURL + '" />  Shall I resume?'
        rtext = "I can pause a little longer. "
        rtext += '<audio src="' + aURL + '" />  Do you want me to continue?'

        return stext, rtext, p_attr, s_attr

    elif s_attr["current_menu"] == "reading-article":
        s_attr["pause_time"] = time.time()

        stext += "Would you like to resume the current article?"
        rtext = "Would you like to resume the current article? "

        s_attr["resuming_from"] = "help-menu"

        s_attr["last_speak"] = stext
        s_attr["last_reprompt"] = rtext

        return stext, rtext, p_attr, s_attr

    else:
        stext += " Try a command to continue. "
        rtext = "Try a command to continue, or, say Repeat to hear this message again"
        s_attr["in_help"] = False

    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    return stext, rtext, p_attr, s_attr


#######################################################################
######## Helper for feedback intent
def feedback_helper(p_attr, s_attr):
    stext = (
        "To send us your feedback, email feedback@l1scientific.com. "
        "Thats spelt: F, E, E, D, B, A, C, K, at L, 1, S, C, I, E, N, T, I, F, I, C dot com. "
    )

    # add the correct prompt depending on users current state
    if s_attr["currently_paused"] == True:
        aURL = "https://bppxmedia.s3.us-west-2.amazonaws.com/Walter_pause.mp3"

        stext += "I will now continue to pause.  Interrupt me and say resume "
        stext += " when you want to continue. "
        stext += '<audio src="' + aURL + '" />  Shall I resume?'
        rtext = "I can pause a little longer. "
        rtext += '<audio src="' + aURL + '" />  Do you want me to continue?'

        return stext, rtext, p_attr, s_attr

    elif s_attr["in_help"] == True:
        s_attr["help_pause"] = time.time()
        return resume_help_helper(p_attr, s_attr, stext)

    elif s_attr["current_menu"] == "reading-article":
        stext += "Lets go back to where we left the article. "
    else:
        stext += "Lets go back to where we left off. "

    stext, rtext, p_attr, s_attr = resume_helper(p_attr, s_attr, stext)
    return stext, rtext, p_attr, s_attr


######################################################################
# yesnohelper
# handle logic for all yes no intents
# YNval = 'YES' or 'NO'
def yesno_helper(p_attr, s_attr, YNval):
    stext = ""  # speech text
    rtext = ""  # reprompt text

    ### User says yes or no but there is no yesno question ###
    if s_attr["yesno_question"] == "NULL":
        stext = (
            "It sounds like you said "
            + YNval
            + ", but I'm not sure what you are referring to. "
        )
        s_attr = s_attr_updater(s_attr)
        stext = stext + s_attr["last_speak"]
        return stext, rtext, p_attr, s_attr
    
    if s_attr['yesno_question'] == 'finish-ad-replay':
        if YNval == "NO":
            stext = "handle no logic  to exit program here"
        stext, rtext, p_attr, s_attr = launch_helper(p_attr, s_attr)
        s_attr['yesno_question'] = "NULL"
        return stext, rtext, p_attr, s_attr
        

    ### User reaches end of article segment ###
    if s_attr["yesno_question"] == "continue-reading":
        # check if user wants another segment
        if YNval == "NO":
            s_attr["is_currently_listening"] = False
            if p_attr["current_edition"]["genre_selected"] == "all_genres":
                s_attr["yesno_question"] = "list-articles"
                stext = "Shall I list all available articles from this edition"
                rtext = stext
                s_attr["last_speak"] = stext
                s_attr["last_reprompt"] = rtext
                return stext, rtext, p_attr, s_attr
            else:
                s_attr["yesno_question"] = "list-articlesbygenre"
                stext = "Shall I list the available articles in the "
                stext += (
                    ph.cleanse_spec_chars(p_attr["current_edition"]["genre_selected"])
                    + " genre. "
                )
                rtext = stext
                s_attr["last_speak"] = stext
                s_attr["last_reprompt"] = rtext
                return stext, rtext, p_attr, s_attr

        # format the next segment
        n = p_attr["current_listen"]["segment"]
        n += 1
        p_attr["current_listen"]["segment"] = n
        # print(f"THIS IS {n}")

        btext, bflag, play_ad = ph.format_body(p_attr, s_attr, p_attr["current_listen"]["segment"])
        stext += btext
        if bflag == False:
            stext = "Error, attempt to exceed document segments. "
            print(
                "*****************EXCEED DOCUMENT SEGMENTS***********************\n "
                "p_attr['current_listen']['segment']: "
                + str(p_attr["current_listen"]["segment"])
                + "\n"
                "p_attr['current_listen']['body']: "
                + str(p_attr["current_listen"]["body"])
                + "\n"
                "s_attr[ 'yesno_question']: " + str(s_attr["yesno_question"]) + "\n"
                "s_attr['old_yesno_question']: "
                + str(s_attr.get("old_yesno_question"))
                + "\n"
            )

            rtext = stext
            return stext, rtext, p_attr, s_attr
        if n < len(p_attr["current_listen"]["body"]):
            stext += "Shall I continue reading? "
            s_attr["is_currently_listening"] = False
            s_attr["yesno_question"] = "continue-reading"
        else:
            s_attr["is_currently_listening"] = False

            # add the correct prompt
            if len(p_attr["current_edition"]["all_genres"]["article_title_list"]) == 1:
                stext += (
                    "That is the only article in this edition. "
                    "Would you like to select another edition from "
                )
                stext += p_attr["current_publication"]["cleansed_title"] + " ? "
                rtext = (
                    "Thats the only article in this editon. "
                    "Would you like to select another edition from "
                )
                rtext += p_attr["current_publication"]["cleansed_title"] + " ? "
                s_attr["yesno_question"] = "list-editions"

            elif not p_attr["current_edition"]["genre_selected"] == "all_genres":
                if (
                    len(
                        p_attr["current_edition"][
                            p_attr["current_edition"]["genre_selected"]
                        ]["article_title_list"]
                    )
                    == 1
                ):
                    
                    stext += (
                        "That is the only article in this genre. "
                        "Would you like to hear a list of the available genres? "
                    )
                    rtext = (
                        "That is the only article in this genre. "
                        "Would you like to hear a list of the available genres? "
                    )
                    s_attr["yesno_question"] = "list-genres"
                else:
                    
                    stext += "Would you like to read another article from the "
                    stext += (
                        ph.cleanse_spec_chars(
                            p_attr["current_edition"]["genre_selected"]
                        )
                        + " genre. "
                    )
                    rtext = "Would you like to read another article from the "
                    rtext += (
                        ph.cleanse_spec_chars(
                            p_attr["current_edition"]["genre_selected"]
                        )
                        + " genre. "
                    )
                    s_attr["yesno_question"] = "list-articlesbygenre"

            else:
                
                stext += (
                    "Would you like to select another article from the "
                    + str(p_attr["current_edition"]["title"])
                    + " edition? "
                )
                rtext = (
                    "Would you like to select another article from the "
                    + str(p_attr["current_edition"]["title"])
                    + " edition? "
                )
                s_attr["yesno_question"] = "list-articles"

        s_attr["current_read"] = stext

        s_attr["t_start"] = time.time()

        s_attr["last_speak"] = stext
        s_attr["last_reprompt"] = rtext

        if (play_ad == True):
            s_attr['should_play_ad'] = True

        return stext, rtext, p_attr, s_attr

    ### User is offered a list of articles bound by a genre ###
    if s_attr["yesno_question"] == "list-articlesbygenre":
        if YNval == "NO":
            s_attr["yesno_question"] = "list-articles"
            s_attr["current_menu"] = "list-articletitles"
            stext = "Shall I list all available articles from the current edition? "
            rtext = stext
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr
        s_attr["yesno_question"] = "NULL"
        return listavailable_helper(p_attr, s_attr, "article", False)

    ### User is offered full list of articles ###
    if s_attr["yesno_question"] == "list-articles":
        if YNval == "NO":
            s_attr["yesno_question"] = "list-editions"
            s_attr["current_menu"] = "list-editions"
            stext = (
                "Shall I list other editions from "
                + p_attr["current_publication"]["cleansed_title"]
            )
            rtext = "Would you like to hear other editions from this publication? "
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr
        s_attr["yesno_question"] = "NULL"
        return listavailable_helper(p_attr, s_attr, "article", True)

    ### User is offered full list of genres ###
    if s_attr["yesno_question"] == "list-genres":
        if YNval == "NO":
            s_attr["yesno_question"] = "list-editions"
            s_attr["current_menu"] = "list-editions"
            stext = (
                "Shall I list other editions from "
                + p_attr["current_publication"]["cleansed_title"]
            )
            rtext = "Would you like to hear other editions from this publication? "
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr
        s_attr["yesno_question"] = "NULL"
        return listavailable_helper(p_attr, s_attr, "genre", True)

    ### User is offered list of editions ###
    if s_attr["yesno_question"] == "list-editions":
        if YNval == "NO":
            # if p_attr['current_region']['name'] == 'NULL':
            # s_attr['yesno_question'] = 'list-publications'
            # s_attr['current_menu'] = 'list-publications'
            s_attr["current_menu"] = "launch"
            # stext = 'Shall I list all available publications from black press?'
            stext = "You have reached the top level menu. "
            rtext = stext
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr

            # else:
            #     s_attr['yesno_question'] = 'list-publicationsbyregion'
            #     s_attr['current_menu'] = 'list-publicationsbyregion'
            #     stext = 'Shall I list the available publications in '
            #     stext += ph.cleanse_spec_chars(p_attr['current_region']['name']) + '. '
            #     rtext = stext
            #     s_attr['last_speak'] = stext
            #     s_attr['last_reprompt'] = rtext
            #     return stext, rtext, p_attr, s_attr

        s_attr["yesno_question"] = "NULL"
        return listeditions_helper(p_attr, s_attr)

    ### user is offered list of publications that is bound by a region ###
    # if s_attr['yesno_question'] == 'list-publicationsbyregion':
    #     if YNval == 'NO':
    #         s_attr['yesno_question'] = 'list-publications'
    #         s_attr['current_menu'] = 'list-publications'
    #         stext = 'Shall I list all available publications from black press? '
    #         rtext = stext
    #         s_attr['last_speak'] = stext
    #         s_attr['last_reprompt'] = rtext
    #         return stext, rtext, p_attr, s_attr
    #     s_attr['yesno_question'] = 'NULL'
    #     return listavailable_helper( p_attr, s_attr, 'publication', False )

    ### User is offered full list of publications ###
    # if s_attr['yesno_question'] == 'list-publications':
    #     if YNval == 'NO':
    #         s_attr['yesno_question'] = 'list-publishers'
    #         stext, rtext, p_attr, s_attr = launch_helper( p_attr, s_attr )
    #         s = 'You have reached the top-level menu. '
    #         stext = s + stext
    #         s_attr['last_speak'] = stext
    #         s_attr['last_reprompt'] = rtext
    #         return stext, rtext, p_attr, s_attr
    #     s_attr['yesno_question'] = 'NULL'
    #     return listavailable_helper( p_attr, s_attr, 'publication', True )

    # ###  User is offered the list of publishers ###
    # if s_attr['yesno_question'] == 'list-publishers':
    #     if YNval == 'NO':
    #         s_attr['yesno_question'] = 'launch'
    #         stext, rtext, p_attr, s_attr = launch_helper( p_attr, s_attr )
    #         s = "You have reached the top-level menu. "
    #         stext = s+stext
    #         s_attr['last_speak'] = stext
    #         s_attr['last_reprompt'] = rtext
    #         return stext, rtext, p_attr, s_attr
    #     s_attr['yesno_question'] = 'NULL'
    #     return listavailable_helper( p_attr, s_attr, 'publisher' )

    ### Pause cycle is completed and system asks user ###
    ### if they'd like to continue on in the system ###
    if s_attr["yesno_question"] == "resume-reading":
        if YNval == "NO":
            # offer the correct list depending on the current menu
            if s_attr["current_menu"] == "reading-article":
                if p_attr["current_edition"]["genre_selected"] == "all_genres":
                    s_attr["yesno_question"] = "list-articles"
                    s_attr["current_menu"] = "list-articletitles"
                    stext = "Shall I list all available articles from this edition"
                    rtext = stext
                    s_attr["last_speak"] = stext
                    s_attr["last_reprompt"] = rtext
                    return stext, rtext, p_attr, s_attr
                else:
                    s_attr["yesno_question"] = "list-articlesbygenre"
                    s_attr["current_menu"] = "list-articlesbygenre"
                    stext = "Shall I list the available articles in the "
                    stext += (
                        ph.cleanse_spec_chars(
                            p_attr["current_edition"]["genre_selected"]
                        )
                        + " genre. "
                    )
                    rtext = stext
                    s_attr["last_speak"] = stext
                    s_attr["last_reprompt"] = rtext
                    return stext, rtext, p_attr, s_attr

            elif s_attr["current_menu"] == "list-genres":
                s_attr["current_menu"] = "list-articletitles"
                if p_attr["current_edition"]["genre_selected"] == "all_genres":
                    s_attr["yesno_question"] = "list-articles"
                    s_attr["current_menu"] = "list-articletitles"
                    stext = (
                        "Shall I list all available articles from the "
                        + str(p_attr["current_edition"]["title"])
                        + " edition?"
                    )
                    rtext = stext
                    s_attr["last_speak"] = stext
                    s_attr["last_reprompt"] = rtext
                    return stext, rtext, p_attr, s_attr
                else:
                    s_attr["yesno_question"] = "list-articlesbygenre"
                    s_attr["current_menu"] = "list-articlesbygenre"
                    stext = "Shall I list the available articles in the "
                    stext += (
                        ph.cleanse_spec_chars(
                            p_attr["current_edition"]["genre_selected"]
                        )
                        + " genre. "
                    )
                    rtext = stext
                    s_attr["last_speak"] = stext
                    s_attr["last_reprompt"] = rtext
                    return stext, rtext, p_attr, s_attr

            elif s_attr["current_menu"] == "list-articletitles":
                s_attr["current_menu"] = "list-editions"
                s_attr["yesno_question"] = "list-editions"
                stext = "Shall I list the other editions? "
                rtext = stext
                s_attr["last_speak"] = stext
                s_attr["last_reprompt"] = rtext
                return stext, rtext, p_attr, s_attr

            elif s_attr["current_menu"] == "list-editions":
                if p_attr["current_region"]["name"] == "NULL":
                    # s_attr['yesno_question'] = 'list-publications'
                    # s_attr['current_menu'] = 'list-publications'
                    # stext = 'Shall I list all available publications from black press?'
                    stext = "You hae reached the top level menu"
                    rtext = stext
                    s_attr["last_speak"] = stext
                    s_attr["last_reprompt"] = rtext
                    return stext, rtext, p_attr, s_attr
                # else:
                #     s_attr['yesno_question'] = 'list-publicationsbyregion'
                #     s_attr['current_menu'] = 'list-publicationsbyregion'
                #     stext = 'Shall I list the available publications in '
                #     stext += ph.cleanse_spec_chars(p_attr['current_region']['name']) + '. '
                #     rtext = stext
                #     s_attr['last_speak'] = stext
                #     s_attr['last_reprompt'] = rtext
                #     return stext, rtext, p_attr, s_attr

            # elif s_attr['current_menu'] == 'list-regions':
            #     if p_attr['current_region']['name'] == 'NULL':
            #         s_attr['yesno_question'] = 'list-publications'
            #         s_attr['current_menu'] = 'list-publications'
            #         stext = 'Shall I list all available publications from black press?'
            #         rtext = stext
            #         s_attr['last_speak'] = stext
            #         s_attr['last_reprompt'] = rtext
            #         return stext, rtext, p_attr, s_attr
            #     else:
            #         s_attr['yesno_question'] = 'list-publicationsbyregion'
            #         stext = 'Shall I list the available publications in '
            #         s_attr['current_menu'] = 'list-publicationsbyregion'
            #         stext += ph.cleanse_spec_chars(p_attr['current_region']['name']) + '. '
            #         rtext = stext
            #         s_attr['last_speak'] = stext
            #         s_attr['last_reprompt'] = rtext
            #         return stext, rtext, p_attr, s_attr

        # s_attr['yesno_question'] = 'NULL'
        return resume_helper(p_attr, s_attr)

    ### The system is launched and asks the user if ###
    ### they'd like to return to the previous publication ###
    if s_attr["yesno_question"] == "resume-last-listen":
        if YNval == "NO":
            stext = "Okay, then just select a paper by name, or ask for a list of publications or a list of regions. "
            rtext = stext
            s_attr["current_menu"] = "launch"
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr
        s_attr["yesno_question"] = "NULL"
        return select_publication_helper(p_attr, s_attr)

    ### There is only one article offered in a list of articles ###
    if s_attr["yesno_question"] == "select-only-article":
        if YNval == "NO":
            stext = " Okay, ask for a list of all available articles, or select another edition. "
            rtext = stext
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr
        s_attr["yesno_question"] = "NULL"
        return selectarticle_helper(p_attr, s_attr, 0)
        return selectnumber_helper(p_attr, s_attr, [], 1)

    ### There is only one genre offered ###
    if s_attr["yesno_question"] == "select-genre":
        if YNval == "NO":
            stext = " Okay, shall I list all available articles. "
            rtext = stext
            s_attr["yesno_question"] = "list-articles"
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr
        s_attr["yesno_question"] = "NULL"
        return selectnumber_helper(p_attr, s_attr, [], 1)

    ### There is only one publication offered in a list of publications ###
    if s_attr["yesno_question"] == "select-publication":
        if YNval == "NO":
            stext = "Okay, then just ask for a list of all publications or a list of regions, or, you can select a paper by name. "
            rtext = stext
            s_attr["current_menu"] = "launch"
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr
        s_attr["yesno_question"] = "NULL"
        return select_publication_helper(p_attr, s_attr, s_attr["one_publication"])

    ### only a best match is found for requested location ###
    if s_attr["yesno_question"] == "select-location-best-match":
        if YNval == "NO":
            stext = (
                "Okay, then just ask for a list of regions or select a paper by name. "
            )
            rtext = stext
            s_attr["current_menu"] = "launch"
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr
        s_attr["yesno_question"] = "NULL"
        return listbylocation_helper(p_attr, s_attr, s_attr["location_best_match"])

    ### user requests a number that is out of bounds of the current list of articles ###
    if s_attr["yesno_question"] == "outofbound-list-articles":
        if YNval == "NO":
            # s_attr['old_yesno_question'] = s_attr['yesno_question']
            s_attr["yesno_question"] = "resume-current-article"
            s_attr["current_menu"] = "reading-article"
            s_attr["resuming_from"] = "outofbound-list-articles"
            stext = "Shall I resume the current article? "
            rtext = stext
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr
        s_attr["yesno_question"] = "NULL"
        return listavailable_helper(p_attr, s_attr, "articles")

    ### User is asked if they'd like to select the article corresponding
    ### to the number they requested mid-article ###
    if s_attr["yesno_question"] == "select-article":
        if YNval == "NO":
            # s_attr['old_yesno_question'] = s_attr['yesno_question']
            s_attr["yesno_question"] = "resume-current-article"
            s_attr["current_menu"] = "reading-article"
            s_attr["resuming_from"] = "select-article"
            stext = "Shall I resume the current article? "
            rtext = stext
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr
        s_attr["yesno_question"] = "NULL"
        return selectarticle_helper(p_attr, s_attr, s_attr["select_article_index"])

    ### User is given list available type best match ###
    if s_attr["yesno_question"] == "list-available":
        if YNval == "NO":
            stext = "Okay, you can ask for help if you are stuck. Lets go back to where we left off. "
            rtext = stext
            s_attr["last_speak"] = s_attr["old_last_speak"]
            s_attr["last_reprompt"] = s_attr["old_last_reprompt"]
            s_attr["yesno_question"] = s_attr["old_yesno_question"]
            return resume_helper(p_attr, s_attr, stext)
        s_attr["yesno_question"] = "NULL"
        return listavailable_helper(p_attr, s_attr, s_attr["list_available"])

    ### User is asked if they'd like to restart an article ###
    if s_attr["yesno_question"] == "restart":
        if YNval == "NO":
            if p_attr["current_edition"]["genre_selected"] == "all_genres":
                s_attr["yesno_question"] = "list-articles"
                s_attr["current_menu"] = "list-articletitles"
                stext = (
                    "Shall I list all available articles from the "
                    + str(p_attr["current_edition"]["title"])
                    + " edition?"
                )
                rtext = stext
                s_attr["last_speak"] = stext
                s_attr["last_reprompt"] = rtext
                return stext, rtext, p_attr, s_attr
            else:
                s_attr["yesno_question"] = "list-articlesbygenre"
                s_attr["current_menu"] = "list-articlesbygenre"
                stext = "Shall I list the available articles in the "
                stext += (
                    ph.cleanse_spec_chars(p_attr["current_edition"]["genre_selected"])
                    + " genre. "
                )
                rtext = stext
                s_attr["last_speak"] = stext
                s_attr["last_reprompt"] = rtext
                return stext, rtext, p_attr, s_attr
        s_attr["yesno_question"] = "NULL"
        return restart_helper(p_attr, s_attr)

    ### User is asked to resume the article they interrupted ###
    if s_attr["yesno_question"] == "resume-current-article":
        if YNval == "NO":
            s_attr["in_help"] = False

        if YNval == "NO" and s_attr["resuming_from"] == "select-article":
            if p_attr["current_edition"]["genre_selected"] == "all_genres":
                s_attr["yesno_question"] = "list-articles"
                s_attr["current_menu"] = "list-articletitles"
                stext = "Shall I list all available articles from this edition"
                rtext = stext
                s_attr["last_speak"] = stext
                s_attr["last_reprompt"] = rtext
                return stext, rtext, p_attr, s_attr
            else:
                s_attr["yesno_question"] = "list-articlesbygenre"
                s_attr["current_menu"] = "list-articlesbygenre"
                stext = "Shall I list the available articles in the "
                stext += (
                    ph.cleanse_spec_chars(p_attr["current_edition"]["genre_selected"])
                    + " genre. "
                )
                rtext = stext
                s_attr["last_speak"] = stext
                s_attr["last_reprompt"] = rtext
                return stext, rtext, p_attr, s_attr

        elif YNval == "NO" and s_attr["resuming_from"] == "outofbound-list-articles":
            s_attr["yesno_question"] = "list-editions"
            s_attr["current_menu"] = "list-edtions"
            stext = (
                "Shall I list other editions from "
                + p_attr["current_publication"]["cleansed_title"]
            )
            rtext = stext
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr

        elif YNval == "NO" and s_attr["resuming_from"] == "resume-current-article":
            if p_attr["current_edition"]["genre_selected"] == "all_genres":
                s_attr["yesno_question"] = "list-articles"
                s_attr["current_menu"] = "list-articletitles"
                stext = "Shall I list all available articles from this edition"
                rtext = stext
                s_attr["last_speak"] = stext
                s_attr["last_reprompt"] = rtext
                return stext, rtext, p_attr, s_attr
            else:
                s_attr["yesno_question"] = "list-articlesbygenre"
                s_attr["current_menu"] = "list-articlesbygenre"
                stext = "Shall I list the available articles in the "
                stext += (
                    ph.cleanse_spec_chars(p_attr["current_edition"]["genre_selected"])
                    + " genre. "
                )
                rtext = stext
                s_attr["last_speak"] = stext
                s_attr["last_reprompt"] = rtext
                return stext, rtext, p_attr, s_attr

        elif YNval == "NO" and s_attr["resuming_from"] == "help-menu":
            stext = "Okay, then try out a command to continue"
            rtext = stext
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr

        s_attr["resuming_from_yesno"] = True
        # s_attr['old_yesno_question'] = s_attr['yesno_question']
        # s_attr['yesno_question'] = 'resume-reading'
        return resume_helper(p_attr, s_attr)

    ### Handle errors ###
    stext = "Error, You said " + YNval + " to the question "
    stext += s_attr["yesno_question"]
    stext += " I cannot currently handle that question. "
    rtext = stext
    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    return stext, rtext, p_attr, s_attr


######################################################################
# help reset the persistent and session attributes
# return user to launch-like state
def resetattr_helper(p_attr, s_attr):
    s_attr = {}


    #last_given_time = p_attr.copy()['sub_period_end']

    p_attr = attr_helper.init_p_attr()
    
    #p_attr['sub_period_end'] = last_given_time

    stext = "Resetting attributes and exiting the program.  Goodbye. "
    rtext = stext

    return stext, rtext, p_attr, s_attr


######################################################################
# respond to request to repeat last response
def repeat_helper(p_attr, s_attr):
    stext = s_attr["last_speak"]
    rtext = s_attr["last_reprompt"]

    return stext, rtext


######################################################################
# respond to select number intent
def selectnumber_helper(p_attr, s_attr, slots, xval=-1, volume=False):
    s_attr["x_entity"] = []
    s_attr["x_slotname"] = ""

    print("CURRENT MENU: " + s_attr["current_menu"])

    if volume == True:
        return volume_helper(p_attr, s_attr)

    s_attr = s_attr_updater(s_attr)

    s_attr["emsg"] = ""
    if xval == -1:
        xnumber = slots["xnumber"].value
    else:
        xnumber = xval
    s_attr["emsg"] = s_attr["current_menu"]

    # select from the correct list depending on the current menu and previous selections
    if s_attr["current_menu"] == "launch":
        stext = (
            "It sounds like you tried to select a number, "
            "but I have not listed any numbers yet. "
            "Try selecting a publication by name, "
            "or ask for a list of publications or a list of regions. "
        )
        rtext = (
            "Try selecting a publication by name, "
            "or ask for a list of publications or a list of regions. "
        )
        s_attr["last_speak"] = stext
        s_attr["last_reprompt"] = rtext
        return stext, rtext, p_attr, s_attr

    # elif s_attr['current_menu'] == 'list-publications':
    #     n_max = len( p_attr['current_publisher']['publication_name_list'] )

    #     if (int(xnumber)<=0) or (int(xnumber) > n_max ):
    #         stext = 'Invalid selection. It sounds like you said ' + str(xnumber)
    #         stext += ', You must choose a number between '
    #         stext += ' one and ' + str(n_max)
    #         rtext = 'Select a publication by name or number. '
    #         s_attr['last_speak'] = stext
    #         s_attr['last_reprompt'] = rtext
    #         return stext, rtext, p_attr, s_attr

    #     xnm1 = int(xnumber) - 1
    #     xname = p_attr['current_publisher']['publication_name_list'][xnm1]
    #     return select_publication_helper( p_attr, s_attr )

    # elif s_attr['current_menu'] == 'list-publicationsbyregion':
    #     n_max = len( p_attr['current_publications_name_list'] )

    #     if (int(xnumber)<=0) or (int(xnumber) > n_max ):
    #         stext = 'Invalid selection. It sounds like you said ' + str(xnumber)
    #         stext += ', You must choose a number between '
    #         stext += ' one and ' + str(n_max)
    #         rtext = 'Select a publication by name or number. '
    #         s_attr['last_speak'] = stext
    #         s_attr['last_reprompt'] = rtext
    #         return stext, rtext, p_attr, s_attr

    #     xnm1 = int(xnumber) - 1
    #     xname = p_attr['current_publications_name_list'][xnm1]
    #     return select_publication_helper( p_attr, s_attr, xname )

    elif s_attr["current_menu"] == "list-editions":
        n_max = p_attr["current_publication"]["presented_edition_list_length"]
        if (int(xnumber) <= 0) or (int(xnumber) > n_max):
            stext = "Invalid selection. It sounds like you said " + str(xnumber)
            stext += ", You must choose a number between "
            stext += " one and " + str(n_max)
            rtext = "Select a publication by name or number. "
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr

        edition_xdate = p_attr["current_publication"]["edition_list"][int(xnumber) - 1]
        return selectdate_helper(p_attr, s_attr, [], edition_xdate)

    elif s_attr["current_menu"] == "list-genres":
        xn = int(xnumber)
        if xn <= 0 or xn > len(p_attr["current_edition"]["genre_key_list"]):
            stext = "You must select a number from within the genre list range. "
            s1, r1, p_attr, s_attr = listgenres_helper(p_attr, s_attr)
            stext += s1
            rtext = s1
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr

        s_attr["current_menu"] = "list-articletitles"
        xgenre = p_attr["current_edition"]["genre_key_list"][xn - 1]
        stext, rtext, p_attr, s_attr = selectgenre_helper(p_attr, s_attr, xgenre)

    elif (
        s_attr["current_menu"] == "list-articletitles"
        or s_attr["current_menu"] == "list-articlesbygenre"
    ):
        xnumber = int(xnumber)
        current_genre = p_attr["current_edition"]["genre_selected"]
        n_max = int(len(p_attr["current_edition"][current_genre]["article_title_list"]))
        if (int(xnumber) <= 0) or (int(xnumber) > n_max):
            stext = "That is an invalid selection. I think you said " + str(xnumber)
            stext += ", You must choose a number within the "
            stext += "list of articles. "
            rtext = "Choose a number corresponding to an article. "
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr

        article_index = xnumber - 1
        return selectarticle_helper(p_attr, s_attr, article_index)

    # elif s_attr['current_menu'] == 'list-regions':
    #     n_max = len( p_attr['current_publisher']['master_region_list'] )
    #     if (int(xnumber)<=0) or (int(xnumber) > n_max ):
    #         stext = 'Invalid selection. It sounds like you said ' + str(xnumber)
    #         stext += ', You must choose a number between '
    #         stext += ' one and ' + str(n_max)
    #         rtext = 'Select a region by name or number. '
    #         s_attr['last_speak'] = stext
    #         s_attr['last_reprompt'] = rtext
    #         return stext, rtext, p_attr, s_attr

    #     xregion = p_attr['current_publisher']['master_region_list'][ int(xnumber)-1 ]
    #     s_attr['current_menu'] = 'list-publicationsbyregion'
    #     return selectregion_helper( p_attr, s_attr, xregion )

    elif s_attr["current_menu"] == "reading-article":
        xnumber = int(xnumber)
        current_genre = p_attr["current_edition"]["genre_selected"]
        n_max = int(len(p_attr["current_edition"][current_genre]["article_title_list"]))

        s_attr["old_last_speak"] = s_attr["last_speak"]
        s_attr["old_last_reprompt"] = s_attr["last_reprompt"]

        s_attr["old_yesno_question"] = s_attr["yesno_question"]

        if (xnumber <= 0) or (xnumber > n_max):
            stext = "There are " + str(n_max)
            stext += " articles in the edition you are currently reading, shall I list them? "
            rtext = "Shall I list the available articles? "
            s_attr["yesno_question"] = "outofbound-list-articles"
            s_attr["current_menu"] = "list-articletitles"
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr

        elif xnumber - 1 == s_attr["current_article_index"]:
            stext = "You are already reading article number " + str(xnumber) + ". "
            stext += " Shall I restart the article?"
            rtext = "Shall I restart the article?"
            s_attr["yesno_question"] = "restart"
            s_attr["current_menu"] = "reading-article"
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr

        else:
            stext = "Shall I read article " + str(xnumber)
            rtext = "Shall I read article " + str(xnumber)
            s_attr["select_article_index"] = xnumber - 1
            s_attr["yesno_question"] = "select-article"
            s_attr["last_speak"] = stext
            s_attr["last_reprompt"] = rtext
            return stext, rtext, p_attr, s_attr

    else:  # don't know how to handle number selection for this current menu
        stext = "I am lost in number selection. "
        stext += "I think the current menu is " + s_attr["current_menu"]
        rtext = "I am lost in number selection. "

    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    return stext, rtext, p_attr, s_attr


########################################################################
# Responds to requests to select an article
def selectarticle_helper(p_attr, s_attr, article_index):
    s_attr = s_attr_updater(s_attr)

    s_attr["x_entity"] = []
    s_attr["x_slotname"] = ""

    if p_attr["current_edition"]["title"] == "most-recent":
        p_attr["current_edition"]["fid"] = p_attr["current_edition"][
            "art_edition_id_list"
        ][article_index]

    s_attr["current_menu"] = "reading-article"
    s_attr["current_article_index"] = article_index

    current_genre = p_attr["current_edition"]["genre_selected"]
    p_attr["current_listen"]["fid"] = p_attr["current_edition"][current_genre][
        "article_id_list"
    ][article_index]
    p_attr["current_listen"]["title"] = p_attr["current_edition"][current_genre][
        "article_title_list"
    ][article_index]
    p_attr["current_listen"]["author"] = p_attr["current_edition"][current_genre][
        "author_list"
    ][article_index]
    p_attr["current_listen"]["date"] = p_attr["current_edition"][current_genre][
        "date_list"
    ][article_index]

    p_attr["current_listen"]["cleansed_title"] = ph.cleanse_spec_chars(
        p_attr["current_listen"]["title"]
    )

    s1, r1, p_attr, s_attr, xdata, error_code = fh.fetch_article(p_attr, s_attr)

    if error_code == 1:
        return s1, r1, p_attr, s_attr

    s0 = "You have selected article " + str(article_index + 1) + ". "
    data_dict = ph.parse_article_obj(xdata, max_seg_size=2000)
    p_attr = attr_helper.update_p_attr(p_attr, data_dict)
    stext, rtext, s_attr, play_ad = ph.build_response(s0, p_attr, s_attr)

    s_attr["current_read"] = stext
    s_attr["is_currently_listening"] = True
    s_attr["t_start"] = time.time()

    if len(p_attr["current_listen"]["body"]) > 1:
        s_attr["yesno_question"] = "continue-reading"
    else:
        if len(p_attr["current_edition"]["all_genres"]["article_title_list"]) == 1:
            s_attr["yesno_question"] = "list-editions"

        elif not p_attr["current_edition"]["genre_selected"] == "all_genres":
            if (
                len(
                    p_attr["current_edition"][
                        p_attr["current_edition"]["genre_selected"]
                    ]["article_title_list"]
                )
                == 1
            ):
                s_attr["yesno_question"] = "list-genres"
            else:
                s_attr["yesno_question"] = "list-articlesbygenre"

        else:
            s_attr["yesno_question"] = "list-articles"

    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    if (play_ad == True):
        s_attr['should_play_ad'] = True

    return stext, rtext, p_attr, s_attr


######################################################################
# respond to select date intent
def selectdate_helper(p_attr, s_attr, slots, tydate=None, wd_value=None):
    s_attr = s_attr_updater(s_attr)

    if slots is None and tydate != None:
        if "today" in tydate:
            xdate = datetime.datetime.today().date()
        elif "yesterday" in tydate:
            xdate = datetime.datetime.today().date() - datetime.timedelta(days=1)

    elif slots is None and wd_value != None:
        xdate = wd_value

    elif tydate is None:
        if "xday" in slots and slots["xday"].value:
            # Slot is filled
            xday = slots["xday"].value
        elif "yday" in slots and slots["yday"].value:
            # Slot is filled
            xday = slots["yday"].value
        else:
            stext = "Make sure to include the day when requesting a date. "
            rtext = stext
            return stext, rtext, p_attr, s_attr

        # xday = slots['xday'].value
        xmonth = slots["xmonth"].value
        # if no year is provided, use the current year
        # and if it is not present, try last year
        xyear = slots["xyear"].value

        if xyear is None:
            xyear = datetime.datetime.now().year
            xstr = str(xyear) + "-" + str(xmonth) + "-" + str(xday)
            xdate = datetime.datetime.strptime(xstr, "%Y-%B-%d")

            if xdate > datetime.datetime.today():
                xyear = datetime.datetime.now().year - 1

        xstr = str(xyear) + "-" + str(xmonth) + "-" + str(xday)
        xdate = datetime.datetime.strptime(xstr, "%Y-%B-%d")

    else:
        xdate = tydate

    if isinstance(xdate, datetime.date):
        xdate = xdate.strftime("%Y-%m-%d")

    # fetch list of publications from the server

    match_found = False
    istar = -1
    stext = ""
    ztext = ""
    for n in range(len(p_attr["current_publication"]["edition_list"])):
        if xdate == p_attr["current_publication"]["edition_list"][n]:
            match_found = True
            istar = n
            break
    if match_found:
        s_attr["is_edition_selected"] = True

        p_attr["current_edition"]["fid"] = p_attr["current_publication"][
            "edition_id_list"
        ][istar]
        p_attr["current_edition"]["title"] = p_attr["current_publication"][
            "edition_list"
        ][istar]
        p_attr["current_edition"]["desc"] = ""
        p_attr["current_edition"]["date"] = ""
        p_attr["current_edition"]["num_articles"] = 0

        # stext = 'You have selected the ' + p_attr['current_edition']['title']
        # stext += ' edition, you can choose an article from the list '
        # stext += 'that follows or request the available genres. '
        # stext = 'From ' + p_attr['current_edition']['title'] + ' '
        rtext = ""

        # sdummy, rdummy, p_attr, s_attr = listarticles_helper( p_attr, s_attr )
        s1, r1, p_attr, s_attr = listgenres_helper(p_attr, s_attr)

        stext = stext + s1
        s_attr["last_speak"] = stext
        s_attr["last_reprompt"] = rtext

        # s_attr['current_menu'] = 'list-articletitles'
        s_attr["current_menu"] = "list-genres"
        return stext, rtext, p_attr, s_attr

    else:
        stext += "No editions of " + p_attr["current_publication"]["cleansed_title"]
        stext += " were found matching the date " + xdate + ". "
        stext += " Please select another edition."
        rtext = "Please select another edition."
        s_attr["current_menu"] = "list-editions"

    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    return stext, rtext, p_attr, s_attr


######################################################################
# Responds to requests to select the most recent edition
# load the titles of the 10 most recent articles
def Xselectrecent_helper(p_attr, s_attr, recent_val, genre="NULL", xtype=None):
    s_attr = s_attr_updater(s_attr)

    if (not xtype == "edition") and (not xtype == None) and (not "article" in xtype):
        return listavailable_helper(p_attr, s_attr, xtype, False)

    if not s_attr["is_publication_selected"]:
        stext = "You must first select a publication. "
        stext += s_attr["last_speak"]
        rtext = s_attr["last_reprompt"]
        return stext, rtext, p_attr, s_attr

    if (
        (xtype == None or "edition" in xtype)
        and recent_val != None
        and recent_val != "recent"
    ):
        return selectdate_helper(p_attr, s_attr, None, recent_val)

    s_attr["is_edition_selected"] = True

    s_attr["current_error"] = ""

    p_attr["current_edition"]["fid"] = p_attr["current_publication"]["edition_id_list"][
        0
    ]
    p_attr["current_edition"]["title"] = "most-recent"
    p_attr["current_edition"]["desc"] = ""
    p_attr["current_edition"]["date"] = ""
    p_attr["current_edition"]["num_articles"] = 0

    stext = ""
    rtext = ""

    s1, r1, p_attr, s_attr, error_code = fh.fetch_recent(p_attr, s_attr)

    if error_code == 1:
        return stext, rtext, p_attr, s_attr

    current_genre = genre  # p_attr['current_edition']['genre_selected']
    if current_genre == "NULL" or current_genre == "null":
        current_genre = "all_genres"
    num_articles = len(p_attr["current_edition"][current_genre]["article_title_list"])

    atext = ""

    for ii in range(1, num_articles + 1):
        atext += (
            str(ii)
            + ": "
            + p_attr["current_edition"][current_genre]["cleansed_article_title_list"][
                ii - 1
            ].strip()
        )
        if not atext[-1] == ".":
            atext += ". "
        else:  # stext ends in period, add space
            atext += " "

    if num_articles > 1:
        stext += (
            " Loading the  " + str(num_articles) + " most recent articles from the "
        )
        stext += p_attr["current_publication"]["cleansed_title"] + ". "
        stext += " You can choose an article from the list that follows or request the available genres. "
        stext += "The titles are: "
        stext += atext

    else:
        stext += " Loading the most recent article from the "
        stext += p_attr["current_publication"]["cleansed_title"] + ". "
        stext += " Would you like to select it? "
        rtext = " Would you like to select it? "
        s_attr["yesno_question"] = "select_only_article"

        s_attr["last_speak"] = stext
        s_attr["last_reprompt"] = rtext

        return stext, rtext, p_attr, s_attr

    stext += " Select an article by number, or say repeat to hear the list again. "
    rtext = " Select an article by number, or say repeat to hear the list again. "

    stext, rtext, p_attr, s_attr = listgenres_helper(p_attr, s_attr)

    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    s_attr["current_menu"] = "list-articletitles"

    return stext, rtext, p_attr, s_attr


######################################################################
# Responds to requests to select a weekday edition
def select_weekday_helper(p_attr, s_attr, d_val):
    s_attr = s_attr_updater(s_attr)

    if "last" in d_val:
        last = True
    else:
        last = False

    day_of_week = re.sub(r"this |last |\'s", "", d_val)

    # Get the current date
    today = datetime.datetime.now().date()

    # Find the current day of the week (0 = Monday, 1 = Tuesday, ..., 6 = Sunday)
    current_day = today.weekday()

    # Find the difference in days between the current day and the target day
    days_to_subtract = (
        current_day
        - [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ].index(day_of_week.lower())
    ) % 7

    # Calculate the date of the last occurrence of the target day
    if last:
        date = today - datetime.timedelta(days=(days_to_subtract + 7))
    else:
        date = today - datetime.timedelta(days=days_to_subtract)

    # Calculate the difference in days
    start_delta = datetime.timedelta(days=current_day, weeks=2)
    start_of_lastweek = today - start_delta - datetime.timedelta(days=2)
    end_of_lastweek = start_of_lastweek + datetime.timedelta(days=6)

    if start_of_lastweek <= date <= end_of_lastweek:
        date = date + datetime.timedelta(days=7)

    # stext = f"Hello Tester, you said {d_val}. This means you asked for a date corresponding to {date}"
    # rtext = "Again, hello world! "

    # return stext, rtext, p_attr, s_attr
    return selectdate_helper(p_attr, s_attr, None, None, date)


# ######################################################################
# # helper to list publications
# def listpublications_helper( p_attr, s_attr, region='NULL' ):

#     s_attr = s_attr_updater(s_attr)

#     s_attr['current_menu'] == 'list-publications'
#     s_attr['is_publication_selected'] = False
#     s_attr['is_edition_selected'] = False
#     stext, rtext, p_attr, s_attr = fh.fetch_publications( p_attr, s_attr, region )

#     stext += ' To select a publication say select and then the number of '
#     stext += 'the publication, or say repeat to hear the list again. '

#     s_attr['last_speak'] = stext
#     s_attr['last_reprompt'] = rtext

#     return stext, rtext, p_attr, s_attr


# ######################################################################
# # helper to select region and then list publications
# def selectregion_helper( p_attr, s_attr, region='NULL' ):
#     #stext, rtext, p_attr, s_attr = fh.fetch_publications( p_attr, s_attr, region )
#     s_attr = s_attr_updater(s_attr)
#     s_attr['current_menu'] = 'list-publicationsbyregion'

#     p_attr['current_region'] = {}
#     p_attr['current_region']['name'] = region
#     p_attr['current_region']['publication_name_list'] = []
#     p_attr['current_region']['publication_id_list'] = []

#     region = region.strip()

#     p_attr = attr_helper.clear_current_pubs( p_attr )
#     stext = ''
#     num_pubs = int( p_attr['current_publisher']['num_publications'] )
#     pcount = 1
#     for n in range( num_pubs ):
#         aa = p_attr['current_publisher']['publication_region_list'][n]

#         if not p_attr['current_publisher']['publication_region_list'][n].lower()==region.lower():
#             continue
#         stext += str(pcount) + ', ' + p_attr['current_publisher']['cleansed_publication_name_list'][n] + '. '
#         p_attr['current_publications_name_list'].append( p_attr['current_publisher']['publication_name_list'][n] )
#         p_attr['current_publications_id_list'].append( p_attr['current_publisher']['publication_id_list'][n] )
#         p_attr['current_publications_edition_count_list'].append( p_attr['current_publisher']['edition_count_list'][n] )

#         #p_attr['current_publications_desc_list'].append( p_attr['current_publisher']['publication_desc_list'][n] )
#         pcount += 1


#     num_regional_pubs = pcount-1

#     if num_regional_pubs == 1:
#         atext = 'Black Press has ' + str( num_regional_pubs ) + ' publication in the '
#         atext += region + ' region. It is '
#         stext = atext + stext
#         stext += ' Would you like to select it? '
#         s_attr['one_publication'] = p_attr['current_publications_name_list'][0]
#         s_attr['yesno_question'] = 'select-publication'

#         rtext = stext

#         s_attr['last_speak'] = stext
#         s_attr['last_reprompt'] = rtext

#         return stext, rtext, p_attr, s_attr
#     else:
#         atext = 'Black Press has ' + str( num_regional_pubs ) + ' publications in the '
#         atext += region + ' region. They are '
#         stext = atext + stext
#         stext += ' Select a publication by name, or by number.'
#     rtext = stext

#     s_attr['last_speak'] = stext
#     s_attr['last_reprompt'] = rtext

#     return stext, rtext, p_attr, s_attr


######################################################################
# respond to request to list available article titles
def listarticles_helper(p_attr, s_attr, genre="NULL"):
    s_attr = s_attr_updater(s_attr)

    stext = ""
    rtext = ""

    # ensure there is a publication and edition selected
    if (
        s_attr["is_publication_selected"] == False
        or s_attr["is_edition_selected"] == False
    ):
        stext = (
            "To hear the list of articles, you must select a publication and an edition. "
            "Request a publication by name, or ask for a list of publications or a list of regions. "
        )
        rtext = stext
        s_attr["last_speak"] = stext
        s_attr["last_reprompt"] = rtext
        s_attr["x_entity"] = []
        s_attr["x_slotname"] = ""
        return stext, rtext, p_attr, s_attr

    if genre == "all_genres" or genre == "NULL":
        s_attr["current_menu"] = "list-articletitles"
    else:
        s_attr["current_menu"] = "list-articlesbygenre"

    t1 = not (p_attr["current_edition"]["title"] == "most-recent")
    if t1:
        stext, rtext, p_attr, s_attr, error_code = fh.fetch_articletitles(
            p_attr, s_attr, genre
        )
        if error_code == 1:
            return stext, rtext, p_attr, s_attr

    current_genre = p_attr["current_edition"]["genre_selected"]
    current_genre = current_genre.lower()
    num_articles = len(p_attr["current_edition"][current_genre]["article_title_list"])

    print("-------------------------------------------------------")
    print(" CURRENT EDITION: " + str(p_attr["current_edition"]))
    print("-------------------------------------------------------")

    if num_articles == 1:
        stext = "There is " + str(num_articles) + " article.  The title is: "
        stext += (
            p_attr["current_edition"][current_genre]["cleansed_article_title_list"][
                0
            ].strip()
            + ". "
        )
        stext += "Would you like to select it? "
        rtext = "Would you like to select it? "
        s_attr["yesno_question"] = "select-only-article"
        s_attr["last_speak"] = stext
        s_attr["last_reprompt"] = rtext

        return stext, rtext, p_attr, s_attr
    else:
        stext = "There are " + str(num_articles) + " articles.  The titles are: "

        ########## for catching 0 articles error ##################
        if num_articles == 0:
            print("XUSER ID: " + str(p_attr["xuserID"]))
            print("CURRENT MENU: " + s_attr["current_menu"])
            print("YES NO QUESTION: " + s_attr["yesno_question"])
            print("OLD YES NO QUESTION: " + s_attr["old_yesno_question"])
            print("PUBLICATION: " + p_attr["current_publication"]["title"])
            print("EDITION: " + p_attr["current_edition"]["title"])
            print("GENRE: " + current_genre)
            print(
                "ARTICLE TITLE LIST: "
                + str(p_attr["current_edition"][current_genre]["article_title_list"])
            )
            print("LAST SPEAK: " + s_attr["last_speak"])
            print("LAST REPROMPT: " + s_attr["last_reprompt"])

    for ii in range(1, num_articles + 1):
        stext += (
            str(ii)
            + ": "
            + p_attr["current_edition"][current_genre]["cleansed_article_title_list"][
                ii - 1
            ].strip()
        )
        if not stext[-1] == ".":
            stext += ". "
        else:  # stext ends in period, add space
            stext += " "

    stext += " Select an article by number, or say repeat to hear the list again. "

    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    return stext, rtext, p_attr, s_attr


######################################################################
# respond to request to list of available editions
def listeditions_helper(p_attr, s_attr):
    stext = ""
    rtext = ""
    s_attr = s_attr_updater(s_attr)

    # s_attr['is_edition_selected'] = False

    if s_attr["is_publication_selected"] == True:
        n_max = min(7, len(p_attr["current_publication"]["edition_list"]))
        p_attr["current_publication"]["presented_edition_list_length"] = n_max
        stext = "The most recent available editions are "
        for ii in range(n_max):
            stext += (
                str(ii + 1)
                + ", "
                + str(p_attr["current_publication"]["edition_list"][ii])
                + ". "
            )
        stext += " You can choose an edition by name or by number."
        rtext = stext
        s_attr["current_menu"] = "list-editions"
    else:
        stext = "To list available editions, you must first select a publication. "
        stext += " You can directly select a publication by name, or ask for a list of regions "
        stext += " and select one from there.  What would you like to do?"
        s_attr["current_menu"] = "launch"
        rtext = stext

    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    return stext, rtext, p_attr, s_attr


######################################################################
# respond to request to list available article titles
def listavailable_helper(p_attr, s_attr, xval, list_all=False):
    s_attr = s_attr_updater(s_attr)

    s_attr["x_entity"] = []
    s_attr["x_slotname"] = ""

    # if 'publisher' in xval:
    #     stext = p_attr['current_publisher']['desc']
    #     stext += ' Just ask for a list of regions, or directly request a publication by name. '
    #     rtext = stext
    #     s_attr['current_menu'] = 'launch'
    #     s_attr['last_speak'] = stext
    #     s_attr['last_reprompt'] = rtext
    #     return stext, rtext, p_attr, s_attr

    # elif 'publication' in xval or 'paper' in xval:

    #     if list_all == True:
    #         p_attr['current_region']['name'] = 'NULL'
    #         region = p_attr['current_region']['name']
    #         s_attr['current_menu'] = 'list-publications'
    #         stext, rtext, p_attr, s_attr = listpublications_helper( p_attr, s_attr, region )
    #     else:
    #         region = p_attr['current_region']['name']
    #         s_attr['current_menu'] = 'list-publicationsbyregion'
    #         if region == 'NULL':
    #             s_attr['current_menu'] = 'list-publications'
    #             stext, rtext, p_attr, s_attr = listpublications_helper( p_attr, s_attr, region )
    #         else:
    #             stext, rtext, p_attr, s_attr = listpublications_byregion_helper( p_attr, s_attr, region )

    if "article" in xval:
        if list_all == True:
            p_attr["current_edition"]["genre_selected"] = "all_genres"
            genre = p_attr["current_edition"]["genre_selected"]
            # s_attr['current_menu'] = 'list-articletitles'
        else:
            genre = p_attr["current_edition"]["genre_selected"]
            # s_attr['current_menu'] = 'list-articlesbygenre'

        stext, rtext, p_attr, s_attr = listarticles_helper(p_attr, s_attr, genre)

    elif (
        "edition" in xval
    ):  # note I am seeking editions here but alexa thinks I am saying 'additions'
        # s_attr['current_menu'] = 'list-editions'
        stext, rtext, p_attr, s_attr = listeditions_helper(p_attr, s_attr)

    # elif ('region' in xval) or ('location' in xval):
    #     s_attr['current_menu'] = 'list-regions'
    #     s_attr['x_slotname'] = "REGION_SLOT"
    #     stext, rtext, p_attr, s_attr, error = listregions_helper(p_attr, s_attr)

    elif "genre" in xval:
        # s_attr['current_menu'] = 'list-genres'
        s_attr["x_slotname"] = "GENRE_SLOT"
        stext, rtext, p_attr, s_attr = listgenres_helper(p_attr, s_attr)

    else:
        types = [
            "editions",
            "genres",
            "articles",
        ]  #'publishers', 'publications', 'regions',
        lrmax = 0
        s_attr["pause_time"] = time.time()

        for curval in types:
            lrval = ph.lev_dist(curval, xval)

            # Save the city with the best match in case no perfect match is found
            if lrval > lrmax:
                lrmax = lrval
                best_match = curval

        stext = "I think you asked for a list of " + str(best_match) + ". "
        stext += "Shall I list the available " + str(best_match) + "? "
        rtext = stext
        s_attr["old_yesno_question"] = s_attr["yesno_question"]
        s_attr["yesno_question"] = "list-available"
        s_attr["list_available"] = best_match

    s_attr["old_last_speak"] = s_attr["last_speak"]
    s_attr["old_last_reprompt"] = s_attr["last_reprompt"]
    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    return stext, rtext, p_attr, s_attr


######################################################################
# respond to request to enter access code
def entercode_helper(p_attr, s_attr, xval):
    # make sure user is in position to enter access code
    if not "enter_xkey" in s_attr or not s_attr["enter_xkey"]:
        stext = "It sounds like you are entering a number. If you are selecting "
        stext += " an item from a list, say select, and then the number. "
        stext += s_attr["last_speak"]
        rtext = s_attr["last_reprompt"]
        return stext, rtext, p_attr, s_attr

    cfid = p_attr["current_publication"]["fid"]
    xval = "X" + str(xval)
    if xval == p_attr["current_publication"]["xkey_val"]:
        stext = "That is a valid access code. "
        # save new key
        p_attr["xkeys"][str(cfid)] = "X" + xval
        rtext = "You can list available articles or select one directly. "
        s0, r0, p_attr, s_attr = fh.fetch_editions(p_attr, s_attr)
        s1, r1, p_attr, s_attr = listeditions_helper(p_attr, s_attr)
        s_attr["current_menu"] = "list-editions"
        stext += s1
        rtext = stext
        s_attr["enter_xkey"] = False

        return stext, rtext, p_attr, s_attr
    stext = "Invalid access code.  "
    z = ""
    for c in xval:
        z += c + ", "
    stext += " It sounds like you said " + z
    stext += " Try entering a new access code. "
    rtext = "Enter a new access code. "
    return stext, rtext, p_attr, s_attr


######################################################################
# respond to user providing the publisher by name
def selectpublisher_helper(p_attr, s_attr, pnslot):
    xpublisher = pnslot["publisher_name"].value
    xpid = (
        pnslot["publisher_name"]
        .resolutions.resolutions_per_authority[1]
        .values[0]
        .value.id
    )

    if xpublisher is None or xpublisher == "" or not xpid.isnumeric():
        stext = " Error.  The publisher name you provided is empty. "
        rtext = stext
        return stext, rtext, p_attr, s_attr

    # need to ensure system is at corect state for selection by number
    s_attr["current_menu"] = "list-publishers"
    # stext = ' You chose publisher ' + xpublisher +', the id number is ' + str(xpid)
    # rtext = stext

    return selectnumber_helper(p_attr, s_attr, [], xpid)


######################################################################
# respond to request to list genres
def listgenres_helper(p_attr, s_attr):
    print(
        "ooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo"
    )
    print(
        "ooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo"
    )
    print(
        "ooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo"
    )

    atext = ""
    s_attr = s_attr_updater(s_attr)

    if (
        s_attr["is_publication_selected"] == False
        or s_attr["is_edition_selected"] == False
    ):
        stext = (
            "To list available genres, you must select a publication and an edition. "
            "Request a publication by name, or ask for a list of publications or a list of regions. "
        )
        rtext = stext
        s_attr["last_speak"] = stext
        s_attr["last_reprompt"] = rtext
        s_attr["x_entity"] = []
        s_attr["x_slotname"] = ""
        return stext, rtext, p_attr, s_attr

    sdummy, rdummy, p_attr, s_attr = listarticles_helper(p_attr, s_attr)

    s_attr["current_menu"] = "list-genres"

    gcount = 1
    print("--")
    print(
        f"{p_attr['current_edition']['genre_key_list']}\n THIS IS THE PATTR FOR GENRES"
    )
    for g in p_attr["current_edition"]["genre_key_list"]:
        num_articles = p_attr["current_edition"]["genre_dict"][g]
        atext += str(gcount) + ": " + g + ", with "
        atext += str(num_articles)
        if num_articles == 1:
            atext += " article. "
        else:
            atext += " articles. "
        gcount += 1

    # update the genre slot dynamically so we can select a region later
    glist = []
    for g in p_attr["current_edition"]["genre_key_list"]:
        if g is None:
            continue
        glist.append(g.replace("&", "").replace(".", ""))
    g_entity = []
    for ii in range(len(glist)):
        print(ii, glist[ii])
        s = EntityValueAndSynonyms(value=glist[ii], synonyms=[])
        g = Entity(id=str(ii + 1), name=s)
        g_entity.append(g)
    s_attr["x_entity"] = g_entity
    s_attr["x_slotname"] = "GENRE_SLOT"

    if gcount == 2:
        stext = " From the " + str(p_attr["current_edition"]["title"]) + " edition "
        stext += "The available genre is: "
        stext += atext
        stext += " Would you like to select it? "
        s_attr["yesno_question"] = "select-genre"
        rtext = stext

        s_attr["last_speak"] = stext
        s_attr["last_reprompt"] = rtext

        return stext, rtext, p_attr, s_attr

    else:
        stext = " From the " + str(p_attr["current_edition"]["title"]) + " edition "
        stext += " the available genres are: "
        stext += atext
        stext += " Select a genre by name, or by number. "
        rtext = stext

    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    return stext, rtext, p_attr, s_attr


######################################################################
# respond to request to select a genre
def selectgenre_helper(p_attr, s_attr, xgenre):
    s_attr = s_attr_updater(s_attr)
    genre = xgenre.lower()

    if not genre in p_attr["current_edition"]["genre_key_list"]:
        # do levensteine stuff
        types = p_attr["current_edition"]["genre_key_list"]
        lrmax = 0

        for curgenre in types:
            lrval = ph.lev_dist(curgenre, genre)

            # Save the genre with the best match in case no perfect match is found
            if lrval > lrmax:
                lrmax = lrval
                best_match = curgenre

        genre = best_match

    stext = "You have selected the genre " + genre + ". "
    p_attr["current_edition"]["genre_selected"] = genre
    s1, r1, p_attr, s_attr = listarticles_helper(p_attr, s_attr, genre)
    s_attr["current_menu"] = "list-articlesbygenre"

    stext = stext + s1
    rtext = stext

    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    return stext, rtext, p_attr, s_attr


######################################################################
# respond to request to list regions
def listregions_helper(p_attr, s_attr):
    s_attr = s_attr_updater(s_attr)
    # s_attr = fh.fetch_regions( p_attr, s_attr )
    s_attr["is_publication_selected"] = False
    s_attr["is_edition_selected"] = False
    stext = " Black Press offers publications in the following regions. "
    # update the region slot dynamically so we can select a region later
    rlist = []
    rcount = 1
    for r in p_attr["current_publisher"]["master_region_list"]:
        if r is None:
            continue
        rlist.append(r)
        stext += str(rcount) + ", " + r + ". "
        rcount += 1

    stext += " Select a region by number or say its name. "
    rtext = stext

    error_code = 0
    if len(rlist) == 0:
        error_code = 1
        stext = "The system experienced an error gathering the regions. "
        rtext = stext
        return stext, rtext, p_attr, s_attr, error_code

    p_entity = []
    for ii in range(len(rlist)):
        s = EntityValueAndSynonyms(value=rlist[ii], synonyms=[])
        p = Entity(id=str(ii + 1), name=s)
        p_entity.append(p)
    s_attr["x_entity"] = p_entity
    s_attr["x_slotname"] = "REGION_SLOT"

    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    s_attr["current_menu"] = "list-regions"

    return stext, rtext, p_attr, s_attr, error_code


################################################################
# respond to request to list publications restricted by region or city
def listpublications_byregion_helper(p_attr, s_attr, region):
    s_attr = s_attr_updater(s_attr)

    if len(p_attr["current_publications_name_list"]) == 0:
        stext = "There are zero publications in " + ph.cleanse_spec_chars(region) + ". "
        stext += "Select a publication by name, or ask for a list of all publications. "
        rtext = "Select a publication by name, or ask for a list of all publications. "

        s_attr["last_speak"] = stext
        s_attr["last_reprompt"] = rtext

        return stext, rtext, p_attr, s_attr

    stext = "In " + ph.cleanse_spec_chars(region) + ", "

    if len(p_attr["current_publications_name_list"]) == 1:
        stext += "there is one publication, it is: "
        stext += p_attr["current_publications_name_list"][0] + ", "
        stext += "Would you like to select it? "
        rtext = "Would you like to select it? "

        s_attr["yesno_question"] = "select-publication"
        s_attr["one_publication"] = p_attr["current_publications_name_list"][0]

        s_attr["last_speak"] = stext
        s_attr["last_reprompt"] = rtext

        return stext, rtext, p_attr, s_attr

    else:
        stext += (
            " there are, "
            + str(len(p_attr["current_publications_name_list"]))
            + " publications. "
        )
        stext += "They are: "

    index = 1
    for publication in p_attr["current_publications_name_list"]:
        stext += str(index) + ", " + ph.cleanse_spec_chars(publication) + ", "
        index += 1

    stext += "Select a publication by name or by number. "
    rtext = "Select a publication by name or by number. "

    return stext, rtext, p_attr, s_attr


# ##################################################################
# ####### Intent helper for listing publications by location #######
# def listbylocation_helper( p_attr, s_attr, xlocation):
#     s_attr = s_attr_updater(s_attr)

#     s_attr['current_menu'] = 'list-publicationsbyregion'

#     # Compare the spoken city to the list of cities
#     lrmax = 0 # Levenstein ratio
#     xlocation = xlocation.strip().lower()
#     xlocation = xlocation.replace( '-', ' ')
#     match_found = False

#     if xlocation in p_attr['xlocations']:
#         best_match = xlocation

#     else:
#         for cur_location in p_attr['xlocations']:

#             cur_location = cur_location.replace( '-', ' ').lower()
#             lrval = ph.lev_dist( cur_location, xlocation )

#             # Break if you find a perfect match
#             if cur_location == xlocation:
#                 match_found = True
#                 best_match = xlocation
#                 break

#             # Save the city with the best match in case no perfect match is found
#             if lrval > lrmax:
#                 lrmax = lrval
#                 best_match = cur_location

#         if not match_found:
#             if lrmax < 0.65: # the best match is not close enough
#                 stext = 'I could not find ' + xlocation + ' in my list of locations. '
#                 stext += 'The best match is ' + ph.cleanse_spec_chars(best_match) + '. '
#                 stext += 'Would you like to select it? '

#                 s_attr['location_best_match'] = best_match
#                 s_attr['yesno_question'] = 'select-location-best-match'
#                 rtext = stext

#                 s_attr['last_speak'] = stext
#                 s_attr['last_reprompt'] = rtext

#                 return stext, rtext, p_attr, s_attr

#     # Load all the publications within selected city and add them to stext
#     num_pubs = 0 # counter for number of publications in a city
#     atext = ''

#     p_attr['current_region']['name'] = best_match
#     p_attr = attr_helper.clear_current_pubs( p_attr )
#     cleansed_best_match= ph.cleanse_spec_chars(best_match)

#     for publication in p_attr['xlocations'][best_match]:
#         if publication in p_attr['current_publisher']['publication_name_list']:
#             num_pubs+=1
#             atext += str(num_pubs) + ', ' + ph.cleanse_spec_chars(publication) + ', '
#             p_attr['current_publications_name_list'].append( publication )

#     if num_pubs == 0:
#         stext = 'Sorry, There are currently no publications in ' + cleansed_best_match + '. '
#         stext += 'Try another location, or ask for a list of all available publications. '
#         rtext = 'Try another location, or ask for a list of all available publications. '

#         s_attr['last_speak'] = stext
#         s_attr['last_reprompt'] = rtext

#         return stext, rtext, p_attr, s_attr

#     elif num_pubs == 1:
#         stext = 'Black Press has one publication in '
#         stext += cleansed_best_match + '. It is '
#         stext += atext
#         stext += 'Would you like to select it? '
#         rtext = 'Would you like to select it?'

#         s_attr['yesno_question'] = 'select-publication'
#         s_attr['one_publication'] =  p_attr['current_publications_name_list'][0]

#         s_attr['last_speak'] = stext
#         s_attr['last_reprompt'] = rtext

#         return stext, rtext, p_attr, s_attr

#     else:
#         stext = 'Black Press has ' + str(num_pubs) + ' publications in '
#         stext += cleansed_best_match + '.  They are, '
#         stext += atext
#         stext += '. Select a publication by name or by number.'

#     rtext = 'Select a publication by name. '

#     s_attr['last_speak'] = stext
#     s_attr['last_reprompt'] = rtext

#     return stext, rtext, p_attr, s_attr


######################################################################
# select publication
# there is only one for CBC
def select_publication_helper(p_attr, s_attr):
    s_attr = s_attr_updater(s_attr)

    s_attr["current_error"] = ""
    s_attr["trouble_matching"] = False

    stext = ""

    num_pubs = int(p_attr["current_publisher"]["num_publications"])

    xn = 0
    p_attr["current_publication"]["fid"] = p_attr["current_publisher"][
        "publication_id_list"
    ][xn]
    p_attr["current_publication"]["title"] = p_attr["current_publisher"][
        "publication_name_list"
    ][xn]
    p_attr["current_publication"]["num_editions"] = p_attr["current_publisher"][
        "edition_count_list"
    ][xn]
    p_attr["current_publication"]["xkey_required"] = False
    p_attr["current_publication"]["xkey_val"] = 0
    s_attr["is_publication_selected"] = True
    s_attr["is_edition_selected"] = True

    p_attr["current_publication"]["cleansed_title"] = ph.cleanse_spec_chars(
        p_attr["current_publication"]["title"]
    )

    p_attr["current_publisher"]["last_listen"] = p_attr["current_publication"]["title"]

    stext = " You have selected " + p_attr["current_publication"]["cleansed_title"]
    sdummy, rdummy, p_attr, s_attr, error_code = fh.fetch_editions(p_attr, s_attr)

    if error_code == 1:
        return sdummy, rdummy, p_attr, s_attr

    stext += " The most recent editions are: "
    n_max = min(3, len(p_attr["current_publication"]["edition_list"]))
    p_attr["current_publication"]["presented_edition_list_length"] = n_max
    for n in range(n_max):
        stext += str(p_attr["current_publication"]["edition_list"][n]) + ", "

    stext += " Select an edition by saying its date. "
    rtext = "Which edition would you like to listen to?"
    s_attr["current_menu"] = "list-editions"

    # map to fetch recent
    # default select most recent
    p_attr["current_edition"]["title"] = "most-recent"
    if p_attr["current_edition"]["title"] == "most-recent":
        stext, rtext, p_attr, s_attr = Xselectrecent_helper(p_attr, s_attr, "recent")
        s_attr["current_menu"] = "list-articletitles"

    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    return stext, rtext, p_attr, s_attr


######################################################################################
def attempt_canval(slots, keyname="xpubname"):
    error_code = 0
    stext = ""
    rtext = ""
    xpub_canval = ""
    try:
        xpub_canval = (
            slots[keyname].resolutions.resolutions_per_authority[0].values[0].value.name
        )
    except:
        stext = "It appears you are requesting a publication, but "
        stext += "I do not recognize the name.  Would you like "
        stext += " to hear a list of our available offerings?"
        rtext = stext
        error_code = 1

    return stext, rtext, xpub_canval, error_code


######################################################################################
# respond to request for most recent edition of a publication
def compound_RecentPub_helper(p_attr, s_attr, slots):
    s_attr = s_attr_updater(s_attr)
    stext = ""
    rtext = ""

    xpubname = slots["xpubname"].value
    s0, r0, xpub_canval, error_code = attempt_canval(slots)
    if error_code == 1:
        s_attr["yesno_question"] = "list-publications"
        return s0, r0, p_attr, s_attr

    s_attr["compound_date_request"] = True
    s0, r0, p_attr, s_attr = select_BlackPress_publication_byname_helper(
        p_attr, s_attr, xpubname, xpub_canval
    )
    if s_attr["trouble_matching"] == True:
        stext = s0
        rtext = r0
        s_attr["last_speak"] = stext
        s_attr["last_reprompt"] = rtext
        return stext, rtext, p_attr, s_attr

    s_attr["current_error"] = ""
    TY_val = slots["RTY_val"].value
    xdate = datetime.datetime.now()

    # check if they requested most recent
    if (not "yesterday" in TY_val) and (not "today" in TY_val):
        return Xselectrecent_helper(p_attr, s_attr)

    if "yesterday" in TY_val:
        tdelta = datetime.timedelta(-1)
        xdate = xdate + tdelta

    s_attr["last_speak"] = stext
    s_attr["last_reprompt"] = rtext

    return selectdate_helper(p_attr, s_attr, [], xdate)


# ######################################################################################
# # helper to compound publication + date request
# def compoundDatePub_helper( p_attr, s_attr, slots ):

#     s_attr = s_attr_updater(s_attr)

#     xpubname = slots['xpubname'].value
#     s0,r0,xpub_canval, error_code = attempt_canval( slots )
#     if error_code == 1:
#         s_attr['yesno_question'] = 'list-publications'
#         return s0, r0, p_attr, s_attr

#     s_attr['compound_date_request' ] = True

#     s0,r0,p_attr, s_attr = select_BlackPress_publication_byname_helper( p_attr, s_attr, xpubname, xpub_canval )

#     if s_attr['trouble_matching'] == True:
#         stext = s0
#         rtext = r0
#         s_attr['last_speak'] = stext
#         s_attr['last_reprompt'] = rtext
#         return stext, rtext, p_attr, s_attr

#     if s_attr['current_error'] == '':
#         stext, rtext, p_attr, s_attr = selectdate_helper( p_attr, s_attr, slots )
#         s0 = 'Loading the ' + xpub_canval + ', '
#         stext = s0 + stext
#     else:
#         stext = 'I was unable to load the publication ' + str(xpubname) + '. '
#         stext += s_attr['last_speak']
#     rtext = stext

#     s_attr['compound_date_request'] = False

#     s_attr['last_speak'] = stext
#     s_attr['last_reprompt'] = rtext

#     return stext, rtext, p_attr, s_attr


#####################################################################
#####################################################################
# respond to request to pause
def pause_helper(p_attr, s_attr):
    aURL = "https://bppxmedia.s3.us-west-2.amazonaws.com/Walter_pause.mp3"

    if s_attr["currently_paused"] == True:
        stext = "I can pause a little longer. "
        stext += '<audio src="' + aURL + '" />  Do you want me to continue?'
        rtext = "I can pause a little longer. "
        rtext += '<audio src="' + aURL + '" />  Do you want me to continue?'
        return stext, rtext, p_attr, s_attr

    s_attr["pause_time"] = time.time()
    s_attr["currently_paused"] = True

    if s_attr["in_help"] == False:
        s_attr["old_yesno_question"] = s_attr["yesno_question"]

    s_attr["yesno_question"] = "resume-reading"

    stext = "Okay, I'll take a break.  Interrupt me and say resume "
    stext += " when you want to continue. "
    stext += '<audio src="' + aURL + '" />  Shall I resume?'
    rtext = "I can pause a little longer. "
    rtext += '<audio src="' + aURL + '" />  Do you want me to continue?'

    return stext, rtext, p_attr, s_attr


#####################################################################
#####################################################################
# respond to request to resume
def resume_helper(p_attr, s_attr, atext=""):
    total_listened = 0
    f_factor = 0.8
    chars_per_sec = {
        "x-slow": 11.4,
        "slow": 13.7,
        "medium": 16.9,
        "fast": 20.0,
        "x-fast": 23.6,
    }

    # if s_attr['yesno_question'] == 'resume-reading':
    #    s_attr['old_yesno_question'] = s_attr['old_yesno_question']
    # else:
    # s_attr['old_yesno_question'] = s_attr['yesno_question']

    if s_attr["resuming_from_yesno"] == True:
        # current_speak = s_attr['current_read']
        current_speak = s_attr["old_last_speak"]
        # s_attr['resuming_from_yesno'] = False
    elif s_attr["in_help"] == True:
        current_speak = s_attr["old_last_speak"]
    else:
        current_speak = s_attr["last_speak"]

    # if not currently listening to an article just return the last speak
    if not s_attr["current_menu"] == "reading-article":
        s_attr["resume_at"] = atext + current_speak

    else:
        if not "pause_time" in s_attr or s_attr["pause_time"] == "NULL":
            s_attr["pause_time"] = time.time()

        if s_attr["speed_changed"] == True:
            multiplier = chars_per_sec[p_attr["previous_speed"]]
            old_speed_tag = '<prosody rate="' + p_attr["previous_speed"] + '"> '
        else:
            multiplier = chars_per_sec[p_attr["current_speed"]]
            old_speed_tag = '<prosody rate="' + p_attr["current_speed"] + '"> '

        new_speed_tag = '<prosody rate="' + p_attr["current_speed"] + '"> '

        # calculate the total time the user was listening
        total_listened += s_attr["pause_time"] - s_attr["t_start"]

        # calculate approximately how many characters the user listened to
        num_chars_read = total_listened * multiplier * f_factor

        # store text that has already been read
        current_speak = current_speak.replace(ph.sfx, ph.sfx_replacement)
        already_read = current_speak[: (int(num_chars_read))]

        # find the last period that was read and save all the speech after that period
        for i in reversed(range(len(already_read))):
            if already_read[i] == ".":
                s_attr["resume_at"] = current_speak[i + 1 :]
                break
            elif i == 0:
                s_attr["resume_at"] = current_speak

        # check if the opening speed tag is in resume at
        # add the new speed tag if not found
        # replace old speed tag with new speed tag if it is found
        if s_attr["resume_at"].find(old_speed_tag) == -1:
            s_attr["resume_at"] = new_speed_tag + s_attr["resume_at"]
        else:
            s_attr["resume_at"] = s_attr["resume_at"].replace(
                old_speed_tag, new_speed_tag
            )

        if s_attr["resume_at"].find("</prosody>") == -1:
            s_attr["resume_at"] = s_attr["resume_at"] + "</prosody>"

    s_attr["resume_at"] = s_attr["resume_at"].replace(ph.sfx_replacement[1:], ph.sfx)
    s_attr["resume_at"] = s_attr["resume_at"].replace(ph.sfx_replacement[2:], ph.sfx)

    if not s_attr["current_menu"] == "reading-article":
        s_attr["last_speak"] = s_attr["resume_at"][len(atext) :]
        stext = s_attr["resume_at"]
    else:
        s_attr["last_speak"] = s_attr["resume_at"]  ##[len(atext):]
        stext = atext + s_attr["resume_at"]

    s_attr["current_read"] = s_attr["resume_at"]

    if "old_yesno_question" in s_attr:
        s_attr["yesno_question"] = s_attr["old_yesno_question"]
    else:
        s_attr["yesno_question"] = s_attr["yesno_question"]

    if s_attr["resuming_from_yesno"] == True:
        rtext = s_attr["old_last_reprompt"]
        s_attr["resuming_from_yesno"] = False
    elif s_attr["in_help"] == True:
        rtext = s_attr["old_last_reprompt"]
        s_attr["in_help"] = False
    else:
        rtext = s_attr["last_reprompt"]

    s_attr["speed_changed"] = False

    # calculate time spent reading atext
    atext_time = len(atext) / chars_per_sec["medium"] * 1.2

    # calculated the total time the current article has been resumed
    s_attr["t_start"] = time.time() + atext_time

    s_attr = s_attr_updater(s_attr)

    return stext, rtext, p_attr, s_attr


######################################################
# Handle when the help menu is interrupted
def resume_help_helper(p_attr, s_attr, atext=""):
    time_listened = s_attr["help_pause"] - s_attr["help_start"]
    num_chars_read = time_listened * 16.5 * 0.8

    current_speak = s_attr["last_speak"]

    already_read = current_speak[: (int(num_chars_read))]

    for i in reversed(range(len(already_read))):
        if already_read[i] == ".":
            resume_at = current_speak[i + 1 :]
            break
        elif i == 0:
            resume_at = current_speak

    stext = atext + resume_at
    rtext = s_attr["last_reprompt"]

    return stext, rtext, p_attr, s_attr


#####################################################################
# handle requests to ontinue
def continue_helper(p_attr, s_attr):
    # s_attr = s_attr_updater(s_attr)

    if s_attr["yesno_question"] == "resume-last-listen":
        if s_attr["in_help"] == True:
            stext, rtext, p_attr, s_attr = resume_helper(p_attr, s_attr)
        else:
            return yesno_helper(p_attr, s_attr, "YES")

    else:
        stext, rtext, p_attr, s_attr = resume_helper(p_attr, s_attr)

    return stext, rtext, p_attr, s_attr


######################################################################
# handle requests to skip
def skip_helper(p_attr, s_attr):
    # if s_attr[ 'current_menu' ] == 'launch':
    #    s_attr[ 'old_yesno_question' ] = s_attr['yesno_question']

    stext = "Sorry, I don't have the ability to skip ahead. "

    # add the correct prompt depending on users current state
    if s_attr["currently_paused"] == True:
        aURL = "https://bppxmedia.s3.us-west-2.amazonaws.com/Walter_pause.mp3"

        stext += "I will now continue to pause.  Interrupt me and say resume "
        stext += " when you want to continue. "
        stext += '<audio src="' + aURL + '" />  Shall I resume?'
        rtext = "I can pause a little longer. "
        rtext += '<audio src="' + aURL + '" />  Do you want me to continue?'

        return stext, rtext, p_attr, s_attr

    elif s_attr["in_help"] == True:
        s_attr["help_pause"] = time.time()
        return resume_help_helper(p_attr, s_attr, stext)

    elif s_attr["current_menu"] == "reading-article":
        stext += "Lets go back to where we left the article. "
    else:
        stext += "Lets go back to where we left off. "

    stext, rtext, p_attr, s_attr = resume_helper(p_attr, s_attr, stext)

    return stext, rtext, p_attr, s_attr


######################################################################
# handle requests to rewind
def rewind_helper(p_attr, s_attr):
    # if s_attr[ 'current_menu' ] == 'launch':
    #    s_attr[ 'old_yesno_question' ] = s_attr['yesno_question']

    stext = "Sorry, I don't have the ability to rewind. "

    # add the correct prompt depending on users current state
    if s_attr["currently_paused"] == True:
        aURL = "https://bppxmedia.s3.us-west-2.amazonaws.com/Walter_pause.mp3"

        stext += "I will now continue to pause.  Interrupt me and say resume "
        stext += " when you want to continue. "
        stext += '<audio src="' + aURL + '" />  Shall I resume?'
        rtext = "I can pause a little longer. "
        rtext += '<audio src="' + aURL + '" />  Do you want me to continue?'

        return stext, rtext, p_attr, s_attr

    elif s_attr["in_help"] == True:
        s_attr["help_pause"] = time.time()
        return resume_help_helper(p_attr, s_attr, stext)

    elif s_attr["current_menu"] == "reading-article":
        stext += "Lets go back to where we left the article. "
    else:
        stext += "Lets go back to where we left off. "

    stext, rtext, p_attr, s_attr = resume_helper(p_attr, s_attr, stext)

    return stext, rtext, p_attr, s_attr


######################################################################
# handle requests to restart
def restart_helper(p_attr, s_attr):
    s_attr = s_attr_updater(s_attr)

    if s_attr["current_menu"] == "reading-article":
        stext, rtext, p_attr, s_attr = selectarticle_helper(
            p_attr, s_attr, s_attr["current_article_index"]
        )

    else:
        stext, rtext = repeat_helper(p_attr, s_attr)

    return stext, rtext, p_attr, s_attr


######################################################################
# respond to change speed intent
def changespeed_helper(p_attr, s_attr, xspeed, volume=False, number=False):
    s_attr["speed_changed"] = False

    if volume == True:
        return volume_helper(p_attr, s_attr)

    if number == True:
        atext = (
            "You cannot adjust the reading speed with that command. "
            "Ask me to read slower or faster, or directly request a speed. "
            "The available speeds are extra slow, slow, medium, fast, and extra fast. "
            "Select one by saying, set the speed to, followed by your desired speed. "
        )

        # add the correct prompt depending on users current state
        if s_attr["currently_paused"] == True:
            aURL = "https://bppxmedia.s3.us-west-2.amazonaws.com/Walter_pause.mp3"

            stext += "I will now continue to pause.  Interrupt me and say resume "
            stext += " when you want to continue. "
            stext += '<audio src="' + aURL + '" />  Shall I resume?'
            rtext = "I can pause a little longer. "
            rtext += '<audio src="' + aURL + '" />  Do you want me to continue?'

            return stext, rtext, p_attr, s_attr

        elif s_attr["in_help"] == True:
            s_attr["help_pause"] = time.time()
            return resume_help_helper(p_attr, s_attr, stext)

        elif s_attr["current_menu"] == "reading-article":
            s_attr = s_attr_updater(s_attr)
            atext += "Lets go back to where we left the article. "
        else:
            s_attr = s_attr_updater(s_attr)
            atext += "Lets go back to where we left off. "

        stext, rtext, p_attr, s_attr = resume_helper(p_attr, s_attr, atext)
        return stext, rtext, p_attr, s_attr

    speeds = ["x-slow", "slow", "medium", "fast", "x-fast"]

    stext = ""

    if s_attr["current_menu"] == "reading-article":
        s_attr["speed_changed"] = True

    # User requests to read faster
    if xspeed == "faster":
        if p_attr["current_speed"] == "x-fast":
            stext += "Sorry, I cant read any faster. "
        else:
            for i in range(len(speeds)):
                if p_attr["current_speed"] == speeds[i]:
                    p_attr["previous_speed"] = p_attr["current_speed"]
                    p_attr["current_speed"] = speeds[i + 1]
                    stext += (
                        "I will now read articles at the "
                        + p_attr["current_speed"]
                        + " speed. "
                    )
                    break
    # User requests to read slower
    elif xspeed == "slower":
        if p_attr["current_speed"] == "x-slow":
            stext += "Sorry, I cant read any slower. "
        else:
            for i in range(len(speeds)):
                if p_attr["current_speed"] == speeds[i]:
                    p_attr["previous_speed"] = p_attr["current_speed"]
                    p_attr["current_speed"] = speeds[i - 1]
                    stext += (
                        "I will now read articles at the "
                        + p_attr["current_speed"]
                        + " speed. "
                    )
                    break
    # User directly requests a speed
    else:
        if xspeed == p_attr["current_speed"]:
            stext += (
                "I am already set to read at the "
                + p_attr["current_speed"]
                + " speed. "
            )
            s_attr["speed_changed"] = False
        else:
            p_attr["previous_speed"] = p_attr["current_speed"]
            p_attr["current_speed"] = xspeed
            stext += (
                "I will now read articles at the "
                + p_attr["current_speed"]
                + " speed. "
            )

    rtext = stext

    if s_attr["currently_paused"] == False:
        if "old_yesno_question" in s_attr:
            del s_attr["old_yesno_question"]

    # add the correct prompt depending on users current state
    if s_attr["currently_paused"] == True:
        aURL = "https://bppxmedia.s3.us-west-2.amazonaws.com/Walter_pause.mp3"

        stext += "I will now continue to pause.  Interrupt me and say resume "
        stext += " when you want to continue. "
        stext += '<audio src="' + aURL + '" />  Shall I resume?'
        rtext = "I can pause a little longer. "
        rtext += '<audio src="' + aURL + '" />  Do you want me to continue?'

        return stext, rtext, p_attr, s_attr

    elif s_attr["in_help"] == True:
        s_attr["help_pause"] = time.time()
        return resume_help_helper(p_attr, s_attr, stext)

    elif s_attr["current_menu"] == "reading-article":
        stext += "Lets go back to where we left the article. "
    else:
        stext += "Lets go back to where we left off. "

    stext, rtext, p_attr, s_attr = resume_helper(p_attr, s_attr, stext)
    return stext, rtext, p_attr, s_attr


##############################################################################
####### Helper for handling requests to change the volume
def volume_helper(p_attr, s_attr):
    atext = (
        "While using this skill you cannot adjust the volume with that command. "
        "Try saying Alexa, quieter, or Alexa, louder, "
        "Or, use the buttons located on your device. "
    )

    # add the correct prompt depending on users current state
    if s_attr["currently_paused"] == True:
        aURL = "https://bppxmedia.s3.us-west-2.amazonaws.com/Walter_pause.mp3"

        stext += "I will now continue to pause.  Interrupt me and say resume "
        stext += " when you want to continue. "
        stext += '<audio src="' + aURL + '" />  Shall I resume?'
        rtext = "I can pause a little longer. "
        rtext += '<audio src="' + aURL + '" />  Do you want me to continue?'

        return stext, rtext, p_attr, s_attr

    elif s_attr["in_help"] == True:
        s_attr["help_pause"] = time.time()
        return resume_help_helper(p_attr, s_attr, stext)

    elif s_attr["current_menu"] == "reading-article":
        atext += "Lets go back to where we left the article. "
    else:
        atext += "Lets go back to where we left off. "

    stext, rtext, p_attr, s_attr = resume_helper(p_attr, s_attr, atext)

    return stext, rtext, p_attr, s_attr


#######################################################################
# helper to go up one menu
def uponemenu_helper(p_attr, s_attr):
    s_attr = s_attr_updater(s_attr)

    if s_attr["current_menu"] == "launch":
        stext = "You are already at the top level menu. "
        stext += s_attr["last_speak"]
        rtext = s_attr["last_reprompt"]

    elif s_attr["current_menu"] == "list-publishers":
        s_attr["reset_pub_list"] = True
        return launch_helper(p_attr, s_attr)

    elif s_attr["current_menu"] == "list-publications":
        return listavailable_helper(p_attr, s_attr, "genre")

    elif s_attr["current_menu"] == "list-publicationsbyregion":
        return listavailable_helper(p_attr, s_attr, "genre")

    elif s_attr["current_menu"] == "list-editions":
        return listavailable_helper(p_attr, s_attr, "genre")

    elif s_attr["current_menu"] == "list-articletitles":
        return listavailable_helper(p_attr, s_attr, "edition")

    elif s_attr["current_menu"] == "list-articlesbygenre":
        return listavailable_helper(p_attr, s_attr, "article", True)

    elif s_attr["current_menu"] == "list-regions":
        return listavailable_helper(p_attr, s_attr, "genre")

    elif s_attr["current_menu"] == "list-genres":
        return listavailable_helper(p_attr, s_attr, "article", True)

    elif s_attr["current_menu"] == "reading-article":
        return listavailable_helper(p_attr, s_attr, "article")

    else:
        stext = "You requested to go back one menu but I don't know where you are."
        rtext = stext

        return stext, rtext, p_attr, s_attr
    return stext, rtext, p_attr, s_attr


###########################################################################
#### Helper for That One intent
def thatone_helper(p_attr, s_attr):
    stext = (
        "Sorry, you cannot use that command to select an item while using this skill. "
        "Try using the index of the item you want to select. "
        "For example, if you want to select article 3, you could say, "
        "Alexa, select 3. "
    )

    # add the correct prompt depending on users current state
    if s_attr["currently_paused"] == True:
        aURL = "https://bppxmedia.s3.us-west-2.amazonaws.com/Walter_pause.mp3"

        stext += "I will now continue to pause.  Interrupt me and say resume "
        stext += " when you want to continue. "
        stext += '<audio src="' + aURL + '" />  Shall I resume?'
        rtext = "I can pause a little longer. "
        rtext += '<audio src="' + aURL + '" />  Do you want me to continue?'

        return stext, rtext, p_attr, s_attr

    elif s_attr["in_help"] == True:
        s_attr["help_pause"] = time.time()
        return resume_help_helper(p_attr, s_attr, stext)

    elif s_attr["current_menu"] == "reading-article":
        stext += "Lets go back to where we left the article. "
    else:
        stext += "Lets go back to where we left off. "

    stext, rtext, p_attr, s_attr = resume_helper(p_attr, s_attr, stext)
    return stext, rtext, p_attr, s_attr


###########################################################################
#### Helper for Open intent
# Users request to launch the system when it has already been launched
def open_helper(p_attr, s_attr):
    stext = (
        "You are already using the CBC narrator. "
        "Say cancel to exit, or ask for help if you are stuck. "
    )

    # add the correct prompt depending on users current state
    if s_attr["currently_paused"] == True:
        aURL = "https://bppxmedia.s3.us-west-2.amazonaws.com/Walter_pause.mp3"

        stext += "I will now continue to pause.  Interrupt me and say resume "
        stext += " when you want to continue. "
        stext += '<audio src="' + aURL + '" />  Shall I resume?'
        rtext = "I can pause a little longer. "
        rtext += '<audio src="' + aURL + '" />  Do you want me to continue?'

        return stext, rtext, p_attr, s_attr

    elif s_attr["in_help"] == True:
        s_attr["help_pause"] = time.time()
        return resume_help_helper(p_attr, s_attr, stext)

    elif s_attr["current_menu"] == "reading-article":
        stext += "Lets go back to where we left the article. "
    else:
        stext += "Lets go back to where we left off. "

    stext, rtext, p_attr, s_attr = resume_helper(p_attr, s_attr, stext)
    return stext, rtext, p_attr, s_attr


###########################################################################
#### Helper for whats new intent
def whatsnew_helper(p_attr, s_attr):
    stext = s_attr["help_response"]["whats-new"][0]

    # add the correct prompt depending on users current state
    if s_attr["currently_paused"] == True:
        aURL = "https://bppxmedia.s3.us-west-2.amazonaws.com/Walter_pause.mp3"

        stext += "I will now continue to pause.  Interrupt me and say resume "
        stext += " when you want to continue. "
        stext += '<audio src="' + aURL + '" />  Shall I resume?'
        rtext = "I can pause a little longer. "
        rtext += '<audio src="' + aURL + '" />  Do you want me to continue?'

        return stext, rtext, p_attr, s_attr

    elif s_attr["in_help"] == True:
        s_attr["help_pause"] = time.time()
        return resume_help_helper(p_attr, s_attr, stext)

    elif s_attr["current_menu"] == "reading-article":
        stext += "Lets go back to where we left the article. "
    else:
        stext += "Lets go back to where we left off. "

    stext, rtext, p_attr, s_attr = resume_helper(p_attr, s_attr, stext)
    return stext, rtext, p_attr, s_attr


##########################################################################
# Helper for updating s_attr
def s_attr_updater(s_attr):
    s_attr["pause_time"] = "NULL"
    s_attr["currently_paused"] = False
    s_attr["in_help"] = False
    s_attr["speed_changed"] = False

    return s_attr


###########################################################################
# helper for unhandled intents
def unhandled_helper(p_attr, s_attr):
    s0 = "Uh Oh, I misunderstood you.  Let's try again. "
    stext, rtext, p_attr, s_attr = launch_helper(p_attr, s_attr)
    stext = s0 + stext
    return stext, rtext, p_attr, s_attr