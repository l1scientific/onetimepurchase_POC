# fetch_helper.py
# this script has helper functions for building headers
# and making requests to the server

#####################################################################

import requests
import json
import datetime
import attr_helper
import parsing_helper as ph
from decimal import Decimal

baseURL = "https://viabolical.com"
AD_BASE_URL = "https://blackpress-media.s3.amazonaws.com/"


baseHeader = {
    "App-Name": "CBCNarrator",
    "Authorization": "abc",
    "Xkey": "123464321",
    "Access-Code": "X000123",
    "Xuser-Id": "",
    "Doc-Type": "news",
    "Host": "null",
    "Device-Type": "AmazonEcho",
    "Action": "null",
    "User-Agent": "null",
    "Accept-Encoding": "null",
    "Accept": "null",
    "Connection": "null",
    "Publisher-Id": "null",
    "Region": "null",
    "Publication-Id": "null",
    "Genre": "NULL",
    "Edition-Id": "null",
    "Article-Id": "null",
    "Version": "1.0",
    "Ads": "True",
}


def reset_header():
    baseHeader = {
        "App-Name": "CBCNarrator",
        "Authorization": "abc",
        "Xkey": "123464321",
        "Access-Code": "X000123",
        "Xuser-Id": "",
        "Doc-Type": "news",
        "Host": "null",
        "Device-Type": "AmazonEcho",
        "Action": "null",
        "User-Agent": "null",
        "Accept-Encoding": "null",
        "Accept": "null",
        "Connection": "null",
        "Publisher-Id": "null",
        "Region": "null",
        "Publication-Id": "null",
        "Genre": "NULL",
        "Edition-Id": "null",
        "Article-Id": "null",
        "Version": "1.0",
        "Ads": "True",
    }


############################################################################
############################################################################
def fetch_init(p_attr, s_attr):
    reset_header()

    url = baseURL + "/fetch_init"
    myheader = baseHeader
    myheader["Action"] = "Init"
    myheader["Xuser-Id"] = str(p_attr["xuserID"])

    if 1:  # try:
        r = requests.get(url, headers=myheader)
        x = r.json()
        error_code = 0
        if not x["valid_request"]:
            stext = "There was an error initializing the system."
            rtext = stext
            error_code = 1
            return stext, rtext, p_attr, s_attr, error_code

        p_attr["xuserID"] = str(x["xuserID"])

        p_attr = attr_helper.clear_current_pubs(p_attr)
        # set key attributes
        p_attr["current_publisher"]["fid"] = x["publisher_id"]
        p_attr["current_publisher"]["name"] = x["publisher_name"]
        p_attr["current_publisher"]["desc"] = x["publisher_description"]
        p_attr["current_publisher"]["num_publications"] = int(
            len(x["publication_id_list"])
        )
        p_attr["current_publisher"]["publication_name_list"] = x[
            "publication_name_list"
        ]
        p_attr["current_publisher"]["publication_id_list"] = x["publication_id_list"]
        p_attr["current_publisher"]["publication_region_list"] = x[
            "publication_region_list"
        ]
        p_attr["current_publisher"]["edition_count_list"] = x["edition_count_list"]

        get_ads(p_attr=p_attr)
        print(f"publisher ads: {p_attr['current_publisher']['publisher_ads']}")
        print(f"weights ads: {p_attr['ad_weights']}")
        print(f"publisher ad ids: {p_attr['current_publisher']['publisher_ad_ids']}")
        print(f"types ads: {p_attr['ad_types']}")

        p_attr["num_of_ads"] = len(p_attr["current_publisher"]["publisher_ads"])
        p_attr["ad_frequency"] = Decimal(str(x["ad_frequency"]))

        # store the list of publications in a current list
        # that gets updated as we select regions
        p_attr["current_publications_name_list"] = x["publication_name_list"]

        # Create a cleansed list for output
        p_attr["current_publisher"]["cleansed_publication_name_list"] = p_attr[
            "current_publisher"
        ]["publication_name_list"].copy()
        for i in range(
            len(p_attr["current_publisher"]["cleansed_publication_name_list"])
        ):
            p_attr["current_publisher"]["cleansed_publication_name_list"][
                i
            ] = ph.cleanse_spec_chars(
                p_attr["current_publisher"]["cleansed_publication_name_list"][i]
            )

        p_attr["current_publications_id_list"] = x["publication_id_list"]
        p_attr["current_publications_edition_count_list"] = x["edition_count_list"]

        # p_attr['current_publications_desc_list'] = x[ 'publication_description_list' ]

        # temp fix for regions
        region_set = set({})
        for region in p_attr["current_publisher"]["publication_region_list"]:
            if not region is None:
                region_set.add(region)
        region_list = sorted(list(region_set))
        p_attr["current_publisher"]["master_region_list"] = region_list

        p_attr["xlocations"] = {}
        # for c in x['regions']['City']:
        #    cx = c.lower().strip()
        #    p_attr['xlocations'][cx] = x['regions']['City'][c]

        s_attr["help_response"] = x["help_response"]

        if p_attr["launch_count"] == 1:
            # stext = x['publisher_description']
            stext = "Hello, welcome message. "
        else:
            stext = ""
        rtext = stext

    else:  # except:   # we had an error
        stext = "Sorry, the system is currently not available. Please check  back again later. "
        rtext = stext
        error_code = 1

    return stext, rtext, p_attr, s_attr, error_code


############################################################################
def reduce_ad_credits(p_attr: dict, ad_id: str):
    # Create the request url and headers to send to the backend
    credit_req_url = "https://viabolical.com/ad_credit"
    headers = {
        "publisher-id": str(p_attr["current_publisher"]["fid"]),
        "publication-id": str(p_attr["current_publication"]["fid"]),
        "ad-id": ad_id,
    }
    # Send the request to reduce the ad credit of {ad_url} by 1
    send_adcredit_reduce_req = requests.get(credit_req_url, headers=headers)
    play_ad = True

    get_ads(p_attr=p_attr)


def get_ads(p_attr: dict):
    # View new ads request
    view_ads_req_url = "https://viabolical.com/view_ads"
    headers = {
        "publisher-id": str(p_attr["current_publisher"]["fid"]),
    }

    # Get the updated ads
    response_new_ads = requests.get(view_ads_req_url, headers=headers)
    ads_data = response_new_ads.json()["publisher"]
    print(f"STATUS AD FETCH: {response_new_ads.status_code}")
    print("################################################################\n"+str(ads_data))

    ids = []
    urls = []
    priorities = []
    types = []
    for url_dict in ads_data:
        ids.append(url_dict["id"])
        urls.append(url_dict["url"])
        priorities.append(url_dict["priority"])
        types.append(url_dict["type"])

    p_attr["current_publisher"]["publisher_ad_ids"] = ids
    p_attr["current_publisher"]["publisher_ads"] = urls
    p_attr["ad_weights"] = priorities
    p_attr["ad_types"] = types


############################################################################
# fetch the list of book or news publishers
# this call requires no prior selections
def fetch_publishers(p_attr, s_attr):
    reset_header()

    url = baseURL + "/fetch_publishers"
    myheader = baseHeader
    myheader["Doc-Type"] = "news"  # s_attr['booknews_val'] #p_attr['document_type']
    myheader["Action"] = "List-Publishers"
    myheader["Xuser-Id"] = p_attr["xuserID"]

    r = requests.get(url, headers=myheader)

    x = r.json()
    if not x["is_valid"]:
        stext = "There was an error: "
        stext += x["error_msg"]
        rtext = "An error occurred while contacting the server. "
        rtext += "What would you like to do? "

        return stext, rtext, s_attr

    pubname_list = x["pubname_list"]
    pubid_list = x["pubid_list"]
    pubdesc_list = x["pubdesc_list"]

    pubcount_list = x["pubcount_list"]
    Npublishers = len(pubname_list)
    stext = "There are {} available publishers, ".format(Npublishers)
    stext += " they are "
    pub_id_map = {}
    for n in range(1, Npublishers + 1):
        stext += str(n) + ": " + str(pubname_list[n - 1]) + ". "
        pub_id_map[str(n)] = [
            pubid_list[n - 1],
            pubname_list[n - 1],
            pubdesc_list[n - 1],
            pubcount_list[n - 1],
        ]

    stext += " To select a publisher say select and then the name or number of the publisher. "
    stext += " or say repeat to hear the list again. "
    s_attr["publishers_id_map"] = pub_id_map
    rtext = (
        "Select the number of the desired publisher or say repeat to hear them again. "
    )
    # s_attr['yesno_question'] = 'list_publishers'

    return stext, rtext, s_attr


############################################################################
############################################################################
# present listener with available publications
# this call requires a publisher selection
def fetch_publications(p_attr, s_attr, region="NULL"):
    reset_header()

    url = baseURL + "/fetch_publications"
    myheader = baseHeader
    myheader["Doc-Type"] = p_attr["document_type"]
    myheader["Publisher-Id"] = str(p_attr["current_publisher"]["fid"])
    myheader["Action"] = "List-Publications"
    myheader["Xuser-Id"] = str(p_attr["xuserID"])
    myheader["Region"] = region

    r = requests.get(url, headers=myheader)
    x = r.json()
    if "valid_request" in x:
        if not x["valid_request"]:
            stext = "Error in response to list publications. "
            rtext = stext
            return stext, rtext, p_attr, s_attr

    stext = ""

    # p_attr['current_publisher']['fid'] = x[ 'publisher_id' ]
    # p_attr['current_publisher']['name'] = x[ 'publisher_name' ]
    # p_attr['current_publisher']['desc'] = x[ 'publisher_description' ]
    p_attr["current_publisher"]["publication_name_list"] = x["publication_name_list"]
    p_attr["current_publisher"]["publication_id_list"] = x["publication_id_list"]
    p_attr["current_publisher"]["num_publications"] = len(x["publication_id_list"])
    p_attr["current_publisher"]["region_list"] = x["publication_region_list"]

    # Create a cleansed list for output
    p_attr["current_publisher"]["cleansed_publication_name_list"] = p_attr[
        "current_publisher"
    ]["publication_name_list"].copy()
    for i in range(len(p_attr["current_publisher"]["cleansed_publication_name_list"])):
        p_attr["current_publisher"]["cleansed_publication_name_list"][
            i
        ] = ph.cleanse_spec_chars(
            p_attr["current_publisher"]["cleansed_publication_name_list"][i]
        )

    stext = "Alright, here is the list.  You can interrupt me at any time to say the name or "
    stext += " number of the publication you are seeking.  The available publications are as follows. "
    for k in range(len(p_attr["current_publisher"]["region_list"])):
        stext += (
            str(k + 1)
            + ": "
            + str(p_attr["current_publisher"]["cleansed_publication_name_list"][k])
            + ". "
        )
        # + ', ' + str(p_attr['current_publisher']['region_list'][k] ) + '  '

    rtext = stext
    return stext, rtext, p_attr, s_attr
    accesskey_req_list = x["accesskey_req_list"]
    accesskey_true = x["accesskey_true"]

    Npubs = p_attr["current_publisher"]["num_publications"]
    if region == "NULL":
        stext = tpub_name + " has {} available publications, ".format(Npubs)
        stext += " they are "
    else:
        stext = tpub_name + " has {} available publications, ".format(Npubs)
        stext += " in the " + region + " region. they are "

    pub_id_map = {}
    for n in range(1, Npubs + 1):
        stext += str(n) + ": " + pubname_list[n - 1]
        stext += ". "
        pub_id_map[str(n)] = [
            x["publication_id_list"][n - 1],
            x["publication_name_list"][n - 1],
            x["publication_desc_list"][n - 1],
            x["publication_date_list"][n - 1],
            x["publication_region_list"][n - 1],
            x["publisher_name"],
            accesskey_req_list[n - 1],
            accesskey_true[n - 1],
        ]

    s_attr["publication_id_map"] = pub_id_map

    rtext = "Select the number of the desired publication or say repeat to hear them again. "

    return stext, rtext, p_attr, s_attr


# ***


############################################################################
############################################################################
# present listener with available editions
def fetch_editions(p_attr, s_attr, region="NULL"):
    reset_header()

    url = baseURL + "/fetch_editions"
    myheader = baseHeader
    myheader["Accept"] = "null"
    myheader["User-Agent"] = "xxx"
    myheader["Publication-Id"] = str(p_attr["current_publication"]["fid"])
    myheader["Region"] = "null"
    myheader["Accept-Encoding"] = "null"
    myheader["Connection"] = "null"
    myheader["Authorization"] = "null"

    myheader["Action"] = "List-Editions"
    myheader["Xuser-Id"] = p_attr["xuserID"]

    error_code = 0
    r = requests.get(url, headers=myheader)

    # try:
    x = r.json()
    # except:
    # error_code = 1
    # stext = 'Error code: ' + str(r)
    # rtext = stext
    # return stext, rtext, p_attr, s_attr, error_code
    publication_name = x["publication_name"]
    edition_list = x["edname_list"]
    edid_list = x["edid_list"]
    artcount_list = x["artcount_list"]
    eddesc_list = x["eddesc_list"]
    eddate_list = x["date_list"]

    p_attr["current_publication"]["edition_list"] = edition_list
    p_attr["current_publication"]["edition_id_list"] = edid_list

    stext = ""
    stext += "The first edition is " + str(edition_list[0])
    stext += ", the last edition is " + str(edition_list[-1])

    stext += " To select an edition say select and then the date of the edition. "
    stext += " or say repeat to hear the list again. "

    rtext = "Select the date of the desired edition or say repeat to hear them again. "

    return stext, rtext, p_attr, s_attr, error_code


############################################################################
############################################################################
# present listener with list of available articles by title
# this call requires a publisher and publication selection
def fetch_articletitles(p_attr, s_attr, genre="NULL"):
    reset_header()

    url = baseURL + "/fetch_articletitles"

    myheader = baseHeader
    myheader["Action"] = "List-ArticleTitles"
    myheader["Doc-Type"] = p_attr["document_type"]
    myheader["Publisher-Id"] = str(p_attr["current_publisher"]["fid"])
    myheader["Publication-Id"] = str(p_attr["current_publication"]["fid"])
    myheader["Edition-Id"] = str(p_attr["current_edition"]["fid"])
    myheader["Xuser-Id"] = p_attr["xuserID"]
    myheader["Accept-Encoding"] = "null"
    myheader["Connection"] = "null"
    myheader["Authorization"] = "null"

    myheader["Access-Code"] = "abc"
    myheader["Accept"] = "null"
    # myheader['Genre'] = genre

    # p_attr['current_edition'] = {}
    error_code = 0
    r = requests.get(url, headers=myheader)
    # print(str(r))
    # print(str(r.content ) )

    x = r.json()
    if not "artitle_list" in x:
        stext = x["error_msg"]
        stext += " the value I passed was: " + myheader["Publisher-Id"]
        rtext = ""
        return stext, rtext, s_attr

    art_title_list = x["artitle_list"]
    art_id_list = x["artid_list"]
    art_desc_list = x["artdesc_list"]
    author_list = x["author_list"]
    date_list = x["date_list"]
    genre_list = x["genre_list"]
    gcdict = {}
    num_articles = len(art_title_list)

    p_attr["current_edition"]["num_articles"] = num_articles

    p_attr["current_edition"]["all_genres"] = {}
    p_attr["current_edition"]["all_genres"]["article_title_list"] = art_title_list

    p_attr["current_edition"]["all_genres"][
        "cleansed_article_title_list"
    ] = art_title_list.copy()

    for i in range(
        len(p_attr["current_edition"]["all_genres"]["cleansed_article_title_list"])
    ):
        p_attr["current_edition"]["all_genres"]["cleansed_article_title_list"][
            i
        ] = ph.cleanse_spec_chars(
            p_attr["current_edition"]["all_genres"]["cleansed_article_title_list"][i]
        )

    p_attr["current_edition"]["all_genres"]["article_id_list"] = art_id_list
    p_attr["current_edition"]["all_genres"]["author_list"] = author_list
    p_attr["current_edition"]["all_genres"]["date_list"] = date_list

    p_attr["current_edition"]["genre_key_list"] = []
    for ii in range(1, num_articles + 1):
        g = genre_list[ii - 1]
        if g in gcdict:
            gcdict[g] += 1
        else:
            gcdict[g] = 1
            p_attr["current_edition"][g] = {}
            p_attr["current_edition"]["genre_key_list"].append(g)
            p_attr["current_edition"][g]["article_title_list"] = []
            p_attr["current_edition"][g]["cleansed_article_title_list"] = []
            p_attr["current_edition"][g]["article_id_list"] = []
            p_attr["current_edition"][g]["author_list"] = []
            p_attr["current_edition"][g]["date_list"] = []

        p_attr["current_edition"][g]["article_title_list"].append(
            art_title_list[ii - 1]
        )
        p_attr["current_edition"][g]["cleansed_article_title_list"].append(
            ph.cleanse_spec_chars(art_title_list[ii - 1])
        )
        p_attr["current_edition"][g]["article_id_list"].append(art_id_list[ii - 1])
        p_attr["current_edition"][g]["author_list"].append(author_list[ii - 1])
        p_attr["current_edition"][g]["date_list"].append(date_list[ii - 1])

    p_attr["current_edition"]["genre_list"] = genre_list
    p_attr["current_edition"]["genre_dict"] = gcdict

    if genre == "NULL":
        p_attr["current_edition"]["genre_selected"] = "all_genres"
    else:
        p_attr["current_edition"]["genre_selected"] = genre

    stext = ""
    rtext = ""  # "Select the number of the article you'd like to read. "

    return stext, rtext, p_attr, s_attr, error_code


############################################################################
# getch recent articles for a publication
# this is very similar to fetching article titles.
def fetch_recent(p_attr, s_attr, genre="NULL"):
    reset_header()

    url = baseURL + "/fetch_recent"

    myheader = baseHeader
    myheader["Action"] = "List-ArticleTitles"
    myheader["Doc-Type"] = p_attr["document_type"]
    myheader["Publisher-Id"] = str(p_attr["current_publisher"]["fid"])
    myheader["Publication-Id"] = str(p_attr["current_publication"]["fid"])
    #####################################
    myheader["Genre"] = "NULL"

    print(f"publisher id: {myheader[ 'Publisher-Id' ]}")
    print(f"publication id: {myheader[ 'Publication-Id' ]}")

    # myheader['Genre'] = 'news' #genre

    error_code = 0
    r = requests.get(url, headers=myheader)
    # print(str(r))
    # print(str(r.content ) )

    x = r.json()
    if not "artitle_list" in x:
        # stext = x['error_msg']
        # stext += ' the value I passed was: ' + myheader[ 'Publisher-Id' ]
        stext = ""
        for k in x:
            stext += str(k) + " "
        rtext = ""
        return stext, rtext, p_attr, s_attr

    art_title_list = x["artitle_list"]
    art_id_list = x["artid_list"]
    art_desc_list = x["artdesc_list"]
    author_list = x["author_list"]
    date_list = x["date_list"]
    art_edition_id_list = []
    genre_list = x["genre_list"]
    print("GENRE LIST: " + str(genre_list))
    gcdict = {}
    num_articles = len(art_title_list)

    p_attr["current_edition"]["num_articles"] = num_articles

    p_attr["current_edition"]["all_genres"] = {}
    p_attr["current_edition"]["all_genres"]["article_title_list"] = art_title_list

    p_attr["current_edition"]["all_genres"][
        "cleansed_article_title_list"
    ] = art_title_list.copy()

    for i in range(
        len(p_attr["current_edition"]["all_genres"]["cleansed_article_title_list"])
    ):
        p_attr["current_edition"]["all_genres"]["cleansed_article_title_list"][
            i
        ] = ph.cleanse_spec_chars(
            p_attr["current_edition"]["all_genres"]["cleansed_article_title_list"][i]
        )

    p_attr["current_edition"]["all_genres"]["article_id_list"] = art_id_list
    p_attr["current_edition"]["all_genres"]["author_list"] = author_list
    p_attr["current_edition"]["all_genres"]["date_list"] = date_list

    p_attr["current_edition"]["title"] = "most-recent"
    p_attr["current_edition"]["art_edition_id_list"] = []
    # chagne this once we properly pass in editions
    edition_id_list = []
    for v in x["edition"]:
        for i in range(len(p_attr["current_publication"]["edition_list"])):
            if v == p_attr["current_publication"]["edition_list"][i]:
                ed_id = p_attr["current_publication"]["edition_id_list"][i]
                break
        edition_id_list.append(ed_id)
    p_attr["current_edition"]["art_edition_id_list"] = edition_id_list

    p_attr["current_edition"]["genre_key_list"] = []
    for ii in range(1, num_articles + 1):
        g = genre_list[ii - 1]
        if g in gcdict:
            gcdict[g] += 1
        else:
            gcdict[g] = 1
            p_attr["current_edition"][g] = {}
            p_attr["current_edition"]["genre_key_list"].append(g)
            p_attr["current_edition"][g]["article_title_list"] = []
            p_attr["current_edition"][g]["cleansed_article_title_list"] = []
            p_attr["current_edition"][g]["article_id_list"] = []
            p_attr["current_edition"][g]["author_list"] = []
            p_attr["current_edition"][g]["date_list"] = []

        p_attr["current_edition"][g]["article_title_list"].append(
            art_title_list[ii - 1]
        )
        p_attr["current_edition"][g]["cleansed_article_title_list"].append(
            ph.cleanse_spec_chars(art_title_list[ii - 1])
        )
        p_attr["current_edition"][g]["article_id_list"].append(art_id_list[ii - 1])
        p_attr["current_edition"][g]["author_list"].append(author_list[ii - 1])
        p_attr["current_edition"][g]["date_list"].append(date_list[ii - 1])

    p_attr["current_edition"]["genre_list"] = genre_list
    p_attr["current_edition"]["genre_dict"] = gcdict

    if genre == "NULL":
        p_attr["current_edition"]["genre_selected"] = "all_genres"
    else:
        p_attr["current_edition"]["genre_selected"] = genre

    """
    # Create a cleansed list for output
    for g in gcdict:
        p_attr['current_edition'][g]['cleansed_article_title_list'] = p_attr['current_edition'][g]['article_title_list'].copy
        for i in range(len(p_attr['current_edition'][g]['cleansed_article_title_list'])):
            p_attr['current_edition'][g]['cleansed_article_title_list'][i] = ph.cleanse_spec_chars(p_attr['current_edition'][g]['cleansed_article_title_list'][i])
    """

    stext = ""
    rtext = ""  # "Select the number of the article you'd like to read. "

    # for g in gcdict:
    #   print('****',g,'****')
    #  for t in p_attr['current_edition'][g]['article_title_list']:
    #     print('===',g,t,'===')

    return stext, rtext, p_attr, s_attr, error_code


############################################################################
# fetch an article from the server
def fetch_article(p_attr, s_attr):
    reset_header()

    url = baseURL + "/fetch_article"

    myheader = baseHeader
    myheader["Action"] = "Fetch-Article"
    myheader["Doc-Type"] = "news"
    myheader["Publisher-Id"] = str(p_attr["current_publisher"]["fid"])
    myheader["Publication-Id"] = str(p_attr["current_publication"]["fid"])
    myheader["Edition-Id"] = str(p_attr["current_edition"]["fid"])
    myheader["Article-Id"] = str(p_attr["current_listen"]["fid"])
    myheader["Xuser-Id"] = p_attr["xuserID"]

    r = requests.get(url, headers=myheader)
    # print(str(r))
    # print( str(r.content) )
    x = r.json()

    stext = ""
    rtext = ""
    error_code = 0
    xdata = {}
    if "xdata" in x:
        xtext = "Successfully fetched article. "
        xdata = x["xdata"]

    else:
        error_code = 1
        stext = "Error, unable to fetch content from that article. "
        rtext = stext

    return stext, rtext, p_attr, s_attr, xdata, error_code


############################################################################
############################################################################
# present listener with available regions from publisher
# this call requires a publisher selection
def fetch_regions(p_attr, s_attr):
    reset_header()

    url = baseURL + "/fetch_regions"
    myheader = baseHeader
    myheader["Doc-Type"] = p_attr["document_type"]
    myheader["Publisher-Id"] = str(p_attr["current_publisher"]["fid"])
    myheader["Action"] = "Fetch-Regions"
    myheader["Xuser-Id"] = p_attr["xuserID"]

    r = requests.get(url, headers=myheader)

    x = r.json()
    s_attr["region_list"] = []

    for r in x["regions"]:
        s_attr["region_list"].append(r)

    return s_attr
