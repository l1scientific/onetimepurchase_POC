# ddb_helper.py
# this is my helper function for dealing with dynamoDB


import datetime
import dateutil.parser
import re
import html
import random
import requests
import fetch_helper

# sfx = '<audio src="soundbank://soundlibrary/musical/amzn_sfx_bell_short_chime_01"/>'
# sfx = '<audio src="soundbank://soundlibrary/musical/amzn_sfx_electronic_beep_02"/>'
sfx = '<audio src="https://bppxmedia.s3.us-west-2.amazonaws.com/xf4.mp3"/>'
sfx_replacement = " .8257320147526194759487503487549843572034975439730347. "
ad_fx = "<audio src=\"https://bppxmedia.s3.us-west-2.amazonaws.com/xf6.mp3\"/>"
random.seed()

AD_BASE_URL = "https://blackpress-media.s3.amazonaws.com/"


############################################################################
def cleanhtml(raw_html):
    cleanr = re.compile("<.*?>")
    cleantext = re.sub(cleanr, "", raw_html)
    return cleantext


############################################################################
# remove special characters
def cleanse_spec_chars(s):
    z = html.unescape(s)
    z = z.replace("&", " and ")
    z = z.replace("<", " less than ")
    z = z.replace(">", " greater than ")
    z = fix_pronunciations(z)
    # z = z.replace('&#8230', '...')
    # z = cleanhtml( z )
    return z


#############################################################################
########## Replace commonly mispronouced words with phonemes #################
def fix_pronunciations(speech):
    result = speech.lower()

    # dictionary containing the mispronounced words and their phonemes
    fix_dict = {
        "chilliwack": '<phoneme alphabet="ipa" ph="t͡ʃɪlɪwæk">chilliwack</phoneme>',
        "comox valley record": 'comox valley <phoneme alphabet="ipa" ph="ˈɹɛkɚd">record</phoneme>',
        "kokanee": '<phoneme alphabet="ipa" ph="koʊkəni">kokanee</phoneme>',
        "kootenay": '<phoneme alphabet="ipa" ph="kutni">kootenay</phoneme>',
        "kootenays": '<phoneme alphabet="ipa" ph="kutnis">kootenays</phoneme>',
        "métis": '<phoneme alphabet="ipa" ph="meɪti">métis</phoneme>',
        "quesnel": '<phoneme alphabet="ipa" ph="kwɛnɛl">quesnel</phoneme>',
        "vanderhoof": '<phoneme alphabet="ipa" ph="vændɜrhuf">vanderhoof</phoneme>',
        "saanichnews.com": " saanich news dot com ",
    }

    tofix = re.compile(r"\b(" + "|".join(fix_dict.keys()) + r")\b")
    result = tofix.sub(lambda x: fix_dict[x.group()], result)

    return result


############################################################################
def format_body(p_attr, s_attr, seg_num, start_text=""):
    print(f"AD FREQ: {p_attr['ad_frequency']}")
    AD_FREQUENCY = float(p_attr["ad_frequency"])
    ad_text = ""
    play_ad = False
    ad_rv = random.random()
    # ONLY PLAY AN AD IF THEY ARE NOT SUBSCRIBED
    if (len(s_attr['purchased_isps']) == 0) and ((p_attr['sub_period_end'] == "") or (datetime.datetime.strptime(p_attr['sub_period_end'], '%Y-%m-%d') < datetime.datetime.now())):
        if ad_rv < AD_FREQUENCY:
            if p_attr["num_of_ads"] != 0:
                # Changed this to use ad ids
                # population = p_attr["current_publisher"]["publisher_ads"]
                population = p_attr["current_publisher"]["publisher_ad_ids"]
                weights = p_attr["ad_weights"]

                for i in range(0, len(weights)):
                    weights[i] = int(weights[i])

                print(f"population: {population}")
                print(f"weights: {weights}")
                
                try:
                    ad_to_play_id = random.choices(population=population, weights=weights, k=1)[0]
                    
                    # get the inde of the chosen ad to use for url and type
                    index_of_ad = p_attr["current_publisher"]["publisher_ad_ids"].index(ad_to_play_id)

                    ad_to_play = p_attr["current_publisher"]["publisher_ads"][index_of_ad]
                    ad_to_play_type = p_attr["ad_types"][index_of_ad]

                    # handle text ads
                    if ad_to_play_type == "Text":
                        ad_text = f'Before you can continue, a short ad will play. {ad_fx} {ad_to_play} '
                    # handle audio ads
                    else:
                        ad_text = f'Before you can continue, a short ad will play. {ad_fx} <audio src="{AD_BASE_URL}{ad_to_play}"/> '

                    fetch_helper.reduce_ad_credits(p_attr=p_attr, ad_id=str(ad_to_play_id))

                # Exception cases as per https://docs.python.org/3/library/random.html
                except IndexError as e:
                    # Likely that the population list is empty, meaning that there are ads in the system, but none of them have no credits
                    print(e)

                except ValueError as e:
                    # Likely that every element in the weights list is 0, meaning that there are ads in the system, but none of them have any priority
                    print(e)


    bflag = True
    nfx = '<prosody rate="' + p_attr["current_speed"] + '"> '
    nfxc = "</prosody>"
    btext = ""

    if seg_num > 0 and seg_num <= len(p_attr["current_listen"]["body"]):
        z = p_attr["current_listen"]["body"][str(seg_num)]
        z = cleanhtml(z)
        z = cleanse_spec_chars(z)

        if p_attr["current_listen"]["segment"] == 1:
            btext = start_text + z
        else:
            btext = z

        btext = nfx + btext + nfxc
        # if seg_num > 1: # len( p_attr['current_listen']['body']):

        btext += sfx
        # btext += ' The passage length was ' + str( len(z)) + ' characters. '

    else:
        btext = "You have requested a segment beyond the document scope. "
        bflag = False

    btext = ad_text + btext
    return btext, bflag, play_ad


############################################################################
def build_response(s0, p_attr, s_attr):
    # stext =  ' <break time="1s"/> '
    stext = sfx
    stext += cleanse_spec_chars(p_attr["current_listen"]["title"])
    stext += ". "
    author = cleanse_spec_chars(p_attr["current_listen"]["author"])

    if author == "cbc ca":
        author = "cbc"

    if (not author == "") and (not author == "NULL"):
        stext += ", by: " + author
    stext += ", published: " + p_attr["current_listen"]["date"]
    # stext += ' <break time="1s"/> '
    stext += sfx

    btext, bflag, play_ad = format_body(p_attr, s_attr, 1, stext)
    stext = s0 + btext

    if len(p_attr["current_listen"]["body"]) > 1:
        rtext = " Shall I continue reading?"
        stext += rtext
    else:
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
            else:
                stext += "Would you like to read another article from the "
                stext += (
                    cleanse_spec_chars(p_attr["current_edition"]["genre_selected"])
                    + " genre. "
                )
                rtext = "Would you like to read another article from the "
                rtext += (
                    cleanse_spec_chars(p_attr["current_edition"]["genre_selected"])
                    + " genre. "
                )

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

    return stext, rtext, s_attr, play_ad


############################################################################
# parse the article dictionary returned by my server
# segment the body and return a useful dict
def parse_article_obj(data_dict, max_seg_size=2000):
    body = data_dict["body"]
    body = body.replace("\n\n", "\n")
    text_array = body.split("\n")  # \n' )

    # convert date to datetime object
    if "date" in data_dict:
        s = data_dict["date"]
        c0 = s.find(":")
        c1 = s.find("|")
        s = s[c0 + 1 : c1]

        dval = dateutil.parser.parse(s)
        data_dict["date"] = dval

    # now check if we need to segment the body
    # and use text_array to do it
    # data_dict['text_array'] = text_array
    # split data into segments
    seg_num = 1
    data_dict["body"] = {"1": text_array[0]}
    for ii in range(1, len(text_array)):
        x = text_array[ii]  # .strip()
        if x.strip() == "":
            continue
        clen = len(data_dict["body"][str(seg_num)])
        xlen = len(x)
        if xlen + clen > max_seg_size:
            seg_num += 1
            data_dict["body"][str(seg_num)] = x + " \n "
        else:
            data_dict["body"][str(seg_num)] += x + " \n "

    if (seg_num > 1) and (len(data_dict["body"][str(seg_num)]) < 300):
        to_split = data_dict["body"][str(seg_num - 1)] + data_dict["body"][str(seg_num)]
        total_chars = len(to_split)
        center = int(total_chars / 2)
        last_half = to_split[center:]

        for i in range(len(last_half)):
            if last_half[i] == "\n":
                cut_index = i + 1 + center
                break

        data_dict["body"][str(seg_num - 1)] = to_split[:cut_index]
        data_dict["body"][str(seg_num)] = to_split[cut_index:]

    # adjust empty author field
    if "author" in data_dict:
        a = data_dict["author"]
        a = a.strip().rstrip()
        data_dict["author"] = a
    return data_dict


#######################################################################
# calc the Levenstein distance of two strings
def lev_dist(s, t, ratio_calc=True):
    rows = len(s) + 1
    cols = len(t) + 1
    distance = [[0.0 for i in range(cols)] for j in range(rows)]

    # Populate matrix of zeros with the indeces of each character of both strings
    for i in range(1, rows):
        for k in range(1, cols):
            distance[i][0] = i
            distance[0][k] = k

    # Iterate over the matrix to compute the cost of deletions,insertions and/or substitutions
    for col in range(1, cols):
        for row in range(1, rows):
            if s[row - 1] == t[col - 1]:
                cost = 0  # If the characters are the same in the two strings in a given position [i,j] then the cost is 0
            else:
                # In order to align the results with those of the Python
                # Levenshtein package, if we choose to calculate the ratio
                # the cost of a substitution is 2. If we calculate just distance, then the cost of a substitution is 1.
                if ratio_calc == True:
                    cost = 2
                else:
                    cost = 1
            distance[row][col] = min(
                distance[row - 1][col] + 1,  # Cost of deletions
                distance[row][col - 1] + 1,  # Cost of insertions
                distance[row - 1][col - 1] + cost,
            )  # Cost of substitutions

    if ratio_calc == True:
        # Computation of the Levenshtein Distance Ratio
        Ratio = ((len(s) + len(t)) - distance[row][col]) / (len(s) + len(t))
        return Ratio


def next_monthly_occurrence(day):
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    target_day = today.replace(day=day)
    
    if target_day <= today:
        # If the target day has already passed in this month, move to the next month
        target_day = target_day.replace(month=target_day.month + 1, day=day)
    
    return target_day

def next_yearly_occurrence(month, day):
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    target_date = today.replace(month=month, day=day)
    
    if target_date <= today:
        # If the target date has already passed this year, move to the next year
        target_date = target_date.replace(year=target_date.year + 1)
    
    return target_date

