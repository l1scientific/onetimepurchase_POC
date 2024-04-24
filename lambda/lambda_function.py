#Dylans comment
# lambda_function.py
# manage back-end VUI logic for reading assistant app.
# ** comment Oct 30, 2022 for test download **
#
# The skill is the reading assistant.
# Use dynamoDB to store user session and persistent data


#####################################################################

import random
import datetime
import logging
import os
import time
import requests, json

import boto3

# my script to help dynamoDB processes
import xhelper, intent_helper, parsing_helper, attr_helper

from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_dynamodb.adapter import DynamoDbAdapter


# for dynamic entities
# https://amazon.developer.forums.answerhub.com/questions/210684/dynamic-entities-in-python.html
###   ------
# add modules for dynamic updates to slots
from ask_sdk_model import Response
from ask_sdk_model.dialog import DynamicEntitiesDirective
from ask_sdk_model.er.dynamic import UpdateBehavior, EntityListItem, Entity, EntityValueAndSynonyms
###   ------

# SUBSCRIPTION ISP IMPORTS
from ask_sdk_model.services.monetization import (
    EntitledState, PurchasableState, InSkillProductsResponse, Error,
    InSkillProduct, PurchaseMode)
from ask_sdk_model.interfaces.monetization.v1 import PurchaseResult

from ask_sdk_core.api_client import DefaultApiClient
from ask_sdk_model.interfaces.connections import SendRequestDirective


SKILL_NAME = 'Black Press News Reader'
ddb_region = os.environ.get('DYNAMODB_PERSISTENCE_REGION')
ddb_table_name = os.environ.get('DYNAMODB_PERSISTENCE_TABLE_NAME')
ddb_resource = boto3.resource('dynamodb', region_name=ddb_region)
dynamodb_adapter = DynamoDbAdapter(table_name=ddb_table_name,
                                   create_table=False,
                                   dynamodb_resource=ddb_resource)
api_client = DefaultApiClient()
sb = CustomSkillBuilder(persistence_adapter=dynamodb_adapter, api_client=api_client)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



######################################################################

def in_skill_product_response(handler_input):
    """Get the In-skill product response from monetization service."""
    # type: (HandlerInput) -> Union[InSkillProductsResponse, Error]
    locale = handler_input.request_envelope.request.locale
    ms = handler_input.service_client_factory.get_monetization_service()
    return ms.get_in_skill_products(locale)


def get_all_entitled_products(in_skill_product_list):
    """Get list of in-skill products in ENTITLED state."""
    # type: (List[InSkillProduct]) -> List[InSkillProduct]
    entitled_product_list = [
        l for l in in_skill_product_list if (
                l.entitled == EntitledState.ENTITLED)]
    return entitled_product_list


def get_full_isp_info(handler_input, skill_id):
    api_endpoint = handler_input.request_envelope.context.system.api_endpoint
    access_token = handler_input.request_envelope.context.system.api_access_token
    locale = handler_input.request_envelope.request.locale
    
    token_header = f"Bearer {access_token}"

    print (f"{api_endpoint}, {access_token}m {skill_id}")

    headers = {
        "Accept-Language": locale,
        "Authorization": token_header
    }
    url = f"{api_endpoint}/v1/users/~current/skills/~current/inSkillProducts/{skill_id}"

    response = requests.get(url, headers=headers)
    print(response.status_code)
    print(response.json())




##########################################################################
##########################################################################
# Handler for Skill Launch.
@sb.request_handler(can_handle_func=is_request_type("LaunchRequest"))
def launch_request_handler(handler_input):
    # Get the persistence attributes
    p_attr = handler_input.attributes_manager.persistent_attributes    
    print('*** WELCOME ***')    
    # initialize session attr
    s_attr = attr_helper.init_s_attr()

    in_skill_response = in_skill_product_response(handler_input)
    entitled_prods = get_all_entitled_products(in_skill_response.in_skill_products)
    s_attr['list_of_isps'] = in_skill_response.in_skill_products
    s_attr['purchased_isps'] = entitled_prods


    print(f"LIST OF IN SKILL PRODUCTS: {in_skill_response.in_skill_products}\nLIST OF PURCHASED ISPS: {entitled_prods}")

    stext, rtext, p_attr, s_attr = intent_helper.launch_helper( p_attr, s_attr )


    # IF SUBSCRIPTION IS 'LIVE' THEN TELL THEM HOW MUCH TIME THEY HAVE LEFT
    #if (len(entitled_prods) != 0):
    #    if (entitled_prods[0].purchase_mode == PurchaseMode.LIVE):


    if s_attr['error_code']==1:
        handler_input.response_builder.speak(
        stext).set_should_end_session(True)
        return handler_input.response_builder.response

    print('*** zzz ***')    
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()

    #s0 = EntityValueAndSynonyms( value='zero value', synonyms=[] )
    #p0 = Entity(id='999123', name=s0 )
    #replace_entity_directive = DynamicEntitiesDirective(
    #        update_behavior=UpdateBehavior.REPLACE,
    #        types=[EntityListItem(name="PUBLISHER_NAME_SLOT", values=[p0])],
    #        )

    if s_attr['x_slotname'] != [] and s_attr['x_entity'] != []:
        replace_entity_directive = DynamicEntitiesDirective(
                                  update_behavior=UpdateBehavior.REPLACE,
                                  types=[EntityListItem(name=s_attr['x_slotname'],
                                  values= s_attr['x_entity'] )],
                                  )
        handler_input.response_builder.speak(stext).ask(rtext).add_directive(replace_entity_directive).response
        print ("DYNAMIC ENTITY: " + str(s_attr['x_entity']))
    
    else:
        handler_input.response_builder.speak(stext).ask(rtext).response

    
    
    
    return handler_input.response_builder.response






##########################################################################
##########################################################################
# Handler for Help Intent
@sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
def help_intent_handler(handler_input):
    # load attributes
    p_attr = handler_input.attributes_manager.persistent_attributes    
    s_attr = handler_input.attributes_manager.session_attributes    
    
    # build response
    stext, rtext, p_attr, s_attr = intent_helper.help_helper( p_attr, s_attr )

    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
        
    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response




##########################################################################
##########################################################################
# Handler for Buy
@sb.request_handler(can_handle_func=is_intent_name("BuySubscriptionIntent"))
def buy_subscription_handler(handler_input):
    # load attributes
    p_attr = handler_input.attributes_manager.persistent_attributes    
    s_attr = handler_input.attributes_manager.session_attributes    

    # If they already own a subscription, cannot purchase another
    if len(s_attr["purchased_isps"]) != 0:
        stext = f"Good news, it looks like you already own a subscription. Your subscription plan is {s_attr['purchased_isps'][0]['referenceName']}. {s_attr['last_speak']}"
        rtext = stext
        # save attributes
        handler_input.attributes_manager.session_attributes = s_attr
        handler_input.attributes_manager.persistent_attributes = p_attr
        handler_input.attributes_manager.save_persistent_attributes()
            
        handler_input.response_builder.speak(stext).ask(rtext)
        return handler_input.response_builder.response


    selected_id = ""
    # Get the product id of the specified plan.
    selected_id = s_attr["list_of_isps"][0]["productId"]

    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
    
    return handler_input.response_builder.add_directive(
                SendRequestDirective(
                    name="Buy",
                    payload={
                        "InSkillProduct": {
                            "productId": selected_id
                        }
                    },
                    token="correlationToken")
            ).response


##########################################################################
##########################################################################
# Handler for Cancel
@sb.request_handler(can_handle_func=is_intent_name("CancelSubscriptionIntent"))
def cancel_subscription_handler(handler_input):
    # load attributes
    p_attr = handler_input.attributes_manager.persistent_attributes    
    s_attr = handler_input.attributes_manager.session_attributes    
    

    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
    
    return handler_input.response_builder.add_directive(
                SendRequestDirective(
                    name="Cancel",
                    payload={
                        "InSkillProduct": {
                            "productId": s_attr["purchased_isps"][0]['productId']
                        }
                    },
                    token="correlationToken")
            ).response
    
    
@sb.request_handler(can_handle_func=is_request_type("Connections.Response"))
def handle_isp(handler_input):

    p_attr = handler_input.attributes_manager.persistent_attributes    
    print('*** WELCOME ***')    
    # initialize session attr
    s_attr = attr_helper.init_s_attr( )
    stemp = ""

    if (handler_input.request_envelope.request.name == "Buy"):
        in_skill_response = in_skill_product_response(handler_input)
        entitled_prods = get_all_entitled_products(in_skill_response.in_skill_products)
        s_attr['list_of_isps'] = in_skill_response.in_skill_products
        s_attr['purchased_isps'] = entitled_prods
        product_id = handler_input.request_envelope.request.payload.get(
            "productId")
        purchase_result = handler_input.request_envelope.request.payload.get("purchaseResult")
        
        stemp += "Returning you to the main menu. "

    elif (handler_input.request_envelope.request.name == "Cancel"):
        in_skill_response = in_skill_product_response(handler_input)
        entitled_prods = get_all_entitled_products(in_skill_response.in_skill_products)
        s_attr['list_of_isps'] = in_skill_response.in_skill_products
        s_attr['purchased_isps'] = entitled_prods

    print(f"LIST OF IN SKILL PRODUCTS: {in_skill_response.in_skill_products}\nLIST OF PURCHASED ISPS: {entitled_prods}")
    stext, rtext, p_attr, s_attr = intent_helper.launch_helper( p_attr, s_attr )
    stext = stemp + stext

    if s_attr['error_code']==1:
        handler_input.response_builder.speak(
        stext).set_should_end_session(True)
        return handler_input.response_builder.response

    print('*** zzz ***')    
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()

    #s0 = EntityValueAndSynonyms( value='zero value', synonyms=[] )
    #p0 = Entity(id='999123', name=s0 )
    #replace_entity_directive = DynamicEntitiesDirective(
    #        update_behavior=UpdateBehavior.REPLACE,
    #        types=[EntityListItem(name="PUBLISHER_NAME_SLOT", values=[p0])],
    #        )

    if s_attr['x_slotname'] != [] and s_attr['x_entity'] != []:
        replace_entity_directive = DynamicEntitiesDirective(
                                update_behavior=UpdateBehavior.REPLACE,
                                types=[EntityListItem(name=s_attr['x_slotname'],
                                values= s_attr['x_entity'] )],
                                )
        handler_input.response_builder.speak(stext).ask(rtext).add_directive(replace_entity_directive).response
        print ("DYNAMIC ENTITY: " + str(s_attr['x_entity']))
    
    else:
        handler_input.response_builder.speak(stext).ask(rtext).response

    
    
    
    return handler_input.response_builder.response

    

##########################################################################
##########################################################################
# Handler for More Help Intent
@sb.request_handler(can_handle_func=is_intent_name("MoreHelpIntent"))
def morehelp_intent_handler(handler_input):
    # load attributes
    p_attr = handler_input.attributes_manager.persistent_attributes    
    s_attr = handler_input.attributes_manager.session_attributes    
    
    # build response
    stext, rtext, p_attr, s_attr = intent_helper.morehelp_helper( p_attr, s_attr )

    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
        
    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response



##########################################################################
##########################################################################
# Handler for Feedback Intent
@sb.request_handler(can_handle_func=is_intent_name("FeedbackIntent"))
def feedback_intent_handler(handler_input):
    # load attributes
    p_attr = handler_input.attributes_manager.persistent_attributes    
    s_attr = handler_input.attributes_manager.session_attributes    
    
    # build response
    stext, rtext, p_attr, s_attr = intent_helper.feedback_helper( p_attr, s_attr )

    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
        
    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response






##########################################################################
##########################################################################
# Handler for Cancel
@sb.request_handler(
    can_handle_func=lambda input:
        is_intent_name("AMAZON.CancelIntent")(input) )
def cancel_intent_handler(handler_input):
    
    
    stext = "Thanks for listening!!"

    handler_input.response_builder.speak(
        stext).set_should_end_session(True)
    return handler_input.response_builder.response






##########################################################################
##########################################################################
# Handler for Session End Intent
@sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
def session_ended_request_handler(handler_input):

    # type: (HandlerInput) -> Response
    logger.info(
        "Session ended with reason: {}".format(
            handler_input.request_envelope.request.reason))
    return handler_input.response_builder.response






##########################################################################
##########################################################################
# Handler for Yes Intent
@sb.request_handler(can_handle_func=is_intent_name("AMAZON.YesIntent") )
def yes_handler(handler_input):
    # load attributes    
    p_attr = handler_input.attributes_manager.persistent_attributes
    s_attr = handler_input.attributes_manager.session_attributes

    stext, rtext, p_attr, s_attr = intent_helper.yesno_helper( p_attr, s_attr, 'YES')

    #s_attr['last_speak'] = stext
    #s_attr['last_reprompt'] = rtext
    print(f"S ATTR Q: {s_attr['yesno_question']}")
    
    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()

    if s_attr['x_entity'] == []:
        handler_input.response_builder.speak(stext).ask(rtext)
    elif s_attr['x_slotname'] != [] and s_attr['x_entity'] != []:
        replace_entity_directive = DynamicEntitiesDirective(
                                  update_behavior=UpdateBehavior.REPLACE,
                                  types=[EntityListItem(name=s_attr['x_slotname'],
                                  values= s_attr['x_entity'] )],
                                  )
         
    

        handler_input.response_builder.speak( stext ).ask( rtext ).add_directive(replace_entity_directive).response
    return handler_input.response_builder.response




##########################################################################
##########################################################################
# Handler for No Intent
@sb.request_handler(can_handle_func=is_intent_name("AMAZON.NoIntent") )
def no_handler(handler_input):
    
    # load attributes    
    p_attr = handler_input.attributes_manager.persistent_attributes
    s_attr = handler_input.attributes_manager.session_attributes


    stext, rtext, p_attr, s_attr = intent_helper.yesno_helper( p_attr, s_attr, 'NO')
    if 'exit_flag' in s_attr and s_attr['exit_flag']:
        return stop_handler(handler_input, True)
   

    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()

    
    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response







##########################################################################
# Handler for testing dummy slots etc
@sb.request_handler(can_handle_func=is_intent_name("AMAZON.StopIntent") )
def stop_handler(handler_input, resume_exit=False):

    #return pause_handler(handler_input)
    if resume_exit:
        stext = 'Farewell, thanks for listening.  '
    else:
        stext = 'Now exiting the news reader. Thanks for listening. '
    rtext = stext

    handler_input.response_builder.speak( stext ).set_should_end_session(True)
        
    return handler_input.response_builder.response





##########################################################################
##########################################################################
# handle go back to main menu
# trigger the launch response
@sb.request_handler(can_handle_func=is_intent_name("MainMenuIntent") )
def main_menu_request_handler(handler_input):

    # Get the persistence attributes
    p_attr = handler_input.attributes_manager.persistent_attributes
    # initialize session attr
    s_attr = {}
    in_skill_response = in_skill_product_response(handler_input)
    entitled_prods = get_all_entitled_products(in_skill_response.in_skill_products)
    s_attr['list_of_isps'] = in_skill_response.in_skill_products
    s_attr['purchased_isps'] = entitled_prods
    s_attr['first_time_mainmenu'] = False
    
    # build response
    stext, rtext, p_attr, s_attr = intent_helper.launch_helper( p_attr, s_attr)
    
    #s_attr['last_speak'] = stext
    #s_attr['last_reprompt'] = rtext

    # save attributes    
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()

    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response






##########################################################################
##########################################################################
# handle request to go up one menu level
@sb.request_handler(can_handle_func=is_intent_name("UpOneMenuIntent") )
def up_one_menu_request_handler(handler_input):
    # Get the persistence attributes
    p_attr = handler_input.attributes_manager.persistent_attributes
    s_attr = handler_input.attributes_manager.session_attributes
    
    # build response
    stext, rtext, p_attr, s_attr = intent_helper.uponemenu_helper( p_attr, s_attr)
    if 'reset_pub_list' in s_attr and s_attr['reset_pub_list'] == True:
        return launch_request_handler( handler_input )
    # save attributes    
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
    
    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response




##########################################################################
##########################################################################
# handler to reset attributes
# this is only used for testing
@sb.request_handler(can_handle_func=is_intent_name("ResetAttrIntent") )
def reset_attr_request_handler(handler_input):

    # Get the persistence attributes
    p_attr = handler_input.attributes_manager.persistent_attributes
    s_attr = handler_input.attributes_manager.session_attributes

    stext, rtext, p_attr, s_attr = intent_helper.resetattr_helper( p_attr, s_attr)

    # save attributes    
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
    
    
    handler_input.response_builder.speak(
        stext).set_should_end_session(True)
    return handler_input.response_builder.response







##########################################################################
##########################################################################
# handle request to reload the most recent listen
@sb.request_handler(can_handle_func=is_intent_name("ReloadLastIntent") )
def reload_previous_request_handler(handler_input):

    # Get the persistence attributes
    p_attr = handler_input.attributes_manager.persistent_attributes
    s_attr = handler_input.attributes_manager.session_attributes
    
    # build response
    stext, rtext, p_attr, s_attr = intent_helper.reload_previous_helper( p_attr, s_attr)

    # save attributes    
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
        
    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response






##########################################################################
##########################################################################
# Handler for Changing speed Intent.
@sb.request_handler(can_handle_func=is_intent_name("ChangeSpeedIntent"))
def changespeed_intent_handler(handler_input):

    slots = handler_input.request_envelope.request.intent.slots
    if not slots['xspeed'].value == None:
        xspeed = slots['xspeed'].resolutions.resolutions_per_authority[0].values[0].value.name
    else:
        xspeed = slots['xspeed'].value
    volume = slots['volume'].value
    number = slots['xnumber'].value

    if volume == None:
        adjust_volume = False
    else:
        adjust_volume = True

    if number == None:
        selecting_number = False
    else:
        selecting_number = True

    # load attributes
    p_attr = handler_input.attributes_manager.persistent_attributes    
    s_attr = handler_input.attributes_manager.session_attributes    
    
    # build response
    stext, rtext, p_attr, s_attr = intent_helper.changespeed_helper( p_attr, s_attr, xspeed, adjust_volume, selecting_number )

    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
        
    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response








##########################################################################
##########################################################################
# handle request to pause a listen
@sb.request_handler(  can_handle_func= is_intent_name("PauseIntent") )
def pause_intent_handler(handler_input):
    
    # load attributes    
    p_attr = handler_input.attributes_manager.persistent_attributes
    s_attr = handler_input.attributes_manager.session_attributes


    stext, rtext, p_attr, s_attr = intent_helper.pause_helper( p_attr, s_attr )

    # don't update last speech
    #s_attr['last_speak'] = stext
    # s_attr['last_reprompt'] = rtext

    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
    
    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response





##########################################################################
##########################################################################
# handle request to resume a listen
@sb.request_handler( can_handle_func=is_intent_name("ResumeIntent") )
def resume_intent_handler(handler_input):
    
    s_attr = handler_input.attributes_manager.session_attributes
    p_attr = handler_input.attributes_manager.persistent_attributes
    
    stext, rtext, p_attr, s_attr = intent_helper.resume_helper( p_attr, s_attr )
    
    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
        
    handler_input.response_builder.speak( stext ).ask( rtext )
        
    return handler_input.response_builder.response





##########################################################################
##########################################################################
# handle request to continue
@sb.request_handler( can_handle_func=is_intent_name("ContinueIntent") )
def continue_intent_handler(handler_input):
    
    s_attr = handler_input.attributes_manager.session_attributes
    p_attr = handler_input.attributes_manager.persistent_attributes
    
    stext, rtext, p_attr, s_attr = intent_helper.continue_helper( p_attr, s_attr )
    
    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
        
    handler_input.response_builder.speak( stext ).ask( rtext )
        
    return handler_input.response_builder.response







##########################################################################
##########################################################################
# skip intent
@sb.request_handler( can_handle_func=is_intent_name("SkipIntent") )
def skip_intent_handler(handler_input):
    
    s_attr = handler_input.attributes_manager.session_attributes
    p_attr = handler_input.attributes_manager.persistent_attributes
    
    stext, rtext, p_attr, s_attr = intent_helper.skip_helper( p_attr, s_attr )
        
    handler_input.response_builder.speak( stext ).ask( rtext )
        
    return handler_input.response_builder.response














##########################################################################
##########################################################################
# rewind intent
@sb.request_handler( can_handle_func=is_intent_name("RewindIntent") )
def rewind_intent_handler(handler_input):

    s_attr = handler_input.attributes_manager.session_attributes
    p_attr = handler_input.attributes_manager.persistent_attributes
    
    stext, rtext, p_attr, s_attr = intent_helper.rewind_helper( p_attr, s_attr )

    handler_input.response_builder.speak( stext ).ask( rtext )
        
    return handler_input.response_builder.response







##########################################################################
##########################################################################
# restart intent
@sb.request_handler( can_handle_func=is_intent_name("RestartIntent") )
def restart_intent_handler(handler_input):

    s_attr = handler_input.attributes_manager.session_attributes
    p_attr = handler_input.attributes_manager.persistent_attributes
    
    stext, rtext, p_attr, s_attr = intent_helper.restart_helper( p_attr, s_attr )
    
    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
    
    handler_input.response_builder.speak( stext ).ask( rtext )
        
    return handler_input.response_builder.response






##########################################################################
##########################################################################
# handle request to list publishers 
# this connects to the back end and grabs data
@sb.request_handler(can_handle_func=is_intent_name("ListAvailableIntent") )
def list_available_intent_handler(handler_input):

    slots = handler_input.request_envelope.request.intent.slots
    xval = slots['xtype'].value
    print('****************')
    print('****************')
    print('****************')
    print( 'you asked for', xval )
    print('****************')
    print('****************')
    print('****************')

    


    
    
    if slots['list_all'].value == None:
        list_all = False
    else:
        list_all = True

    # load attributes    
    p_attr = handler_input.attributes_manager.persistent_attributes
    s_attr = handler_input.attributes_manager.session_attributes

    stext, rtext, p_attr, s_attr = intent_helper.listavailable_helper( p_attr, s_attr,
                                                                       xval, list_all )


    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()

    
    if s_attr['x_entity'] == []:
        handler_input.response_builder.speak(stext).ask(rtext)
    elif s_attr['x_slotname'] != [] and s_attr['x_entity'] != []:
        replace_entity_directive = DynamicEntitiesDirective(
                                  update_behavior=UpdateBehavior.REPLACE,
                                  types=[EntityListItem(name=s_attr['x_slotname'],
                                  values= s_attr['x_entity'] )],
                                  )
         
        handler_input.response_builder.speak( stext ).ask( rtext ).add_directive(replace_entity_directive).response
    return handler_input.response_builder.response

 









######################################################################
##########################################################################
# handle request to select the regions
@sb.request_handler(can_handle_func=is_intent_name("SelectGenreIntent") )
def selectgenre_intent_handler(handler_input):
    
    slots = handler_input.request_envelope.request.intent.slots
    xgenre = slots['xgenre'].value
        
    p_attr = handler_input.attributes_manager.persistent_attributes
    s_attr = handler_input.attributes_manager.session_attributes
    
    stext, rtext, p_attr, s_attr = intent_helper.selectgenre_helper( p_attr, s_attr, xgenre )    

    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
       
    handler_input.response_builder.speak( stext ).ask( rtext )
        
    return handler_input.response_builder.response






# ######################################################################
# ##########################################################################
# # handle request to select the regions
# @sb.request_handler(can_handle_func=is_intent_name("SelectRegionIntent") )
# def selectregion_intent_handler(handler_input):
    
#     slots = handler_input.request_envelope.request.intent.slots
#     xregion = slots['xregion'].value
    
    
#     p_attr = handler_input.attributes_manager.persistent_attributes
#     s_attr = handler_input.attributes_manager.session_attributes

    
#     stext = 'You have selected region ' + xregion
#     rtext = stext
#     stext, rtext, p_attr, s_attr = intent_helper.selectregion_helper( p_attr, s_attr, xregion )
    

#     # save attributes
#     handler_input.attributes_manager.session_attributes = s_attr
#     handler_input.attributes_manager.persistent_attributes = p_attr
#     handler_input.attributes_manager.save_persistent_attributes()
    
       
#     handler_input.response_builder.speak( stext ).ask( rtext )
        
#     return handler_input.response_builder.response










##########################################################################
##########################################################################
# handle request to fetch an article
@sb.request_handler(can_handle_func=is_intent_name("FetchArticleIntent") )
def fetcharticle_intent_handler(handler_input):

    slots = handler_input.request_envelope.request.intent.slots
    article_id = slots['article_num'].value
                       
    baseURL = "https://www.viabolical.com"
    url = baseURL + '/fetch_article'
    

    
    headers = {'Authorization':'abc',
           'Xkey':'123464321',
           'Access-Code':'X000123',
           'Action':'List-Publishers',
           'Article-Id':str(article_id)}

    r = requests.get( url, headers=headers )

    x = r.json()
    logger.info('*** Calling ddb parser ***')
    X = xhelper.parse_article_obj( x['xdata' ], max_seg_size=2000 )
    p_attr = handler_input.attributes_manager.persistent_attributes
    p_attr['previous_listen_title'] = p_attr['current_listen_id']
    p_attr['current_listen_id'] = article_id
    p_attr['current_listen_title'] = X['title' ]
    n_segments = len(X['body'])
    p_attr['body'] = X['body']
    p_attr['author'] = X['author']
    
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()

    logger.info('===== updated persistent attributes =====' )

    
    speech_text = 'I have fetched the article titled: ' + X['title']
    reprompt = 'This is the fetch article intent.'
    
    handler_input.response_builder.speak( speech_text ).ask( reprompt )
        
    return handler_input.response_builder.response


 






##########################################################################
# Handler Repeat Intent 
# user is requesting a repeat, usually last list
@sb.request_handler(can_handle_func=is_intent_name("RepeatIntent") )
def repeat_handler(handler_input):

    # load attributes    
    p_attr = handler_input.attributes_manager.persistent_attributes
    s_attr = handler_input.attributes_manager.session_attributes

    stext, rtext = intent_helper.repeat_helper( p_attr, s_attr )
    
    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response








##########################################################################
# Handler SelectNumber Intent 
# user is making generic selection
# I need to figure out the context
@sb.request_handler(can_handle_func=is_intent_name("SelectNumberIntent") )
def select_number_handler(handler_input):

    slots = handler_input.request_envelope.request.intent.slots
    volume = slots['volume'].value

    if volume == None:
        adjust_volume = False

    else:
        adjust_volume = True

    # load attributes    
    p_attr = handler_input.attributes_manager.persistent_attributes
    s_attr = handler_input.attributes_manager.session_attributes

    stext, rtext, p_attr, s_attr = intent_helper.selectnumber_helper( p_attr, s_attr, slots, -1, adjust_volume )

    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()

    if s_attr['x_entity'] == []:
        handler_input.response_builder.speak(stext).ask(rtext)
    elif s_attr['x_slotname'] != [] and s_attr['x_entity'] != []:
        replace_entity_directive = DynamicEntitiesDirective(
                                  update_behavior=UpdateBehavior.REPLACE,
                                  types=[EntityListItem(name=s_attr['x_slotname'],
                                  values= s_attr['x_entity'] )],
                                  )
         
        handler_input.response_builder.speak( stext ).ask( rtext ).add_directive(replace_entity_directive).response

    print(f"selectnumber intent: {stext}")

    return handler_input.response_builder.response



##########################################################################
# Handler Select Ordinal Intent 
# clone of number selection with ordinal words
@sb.request_handler(can_handle_func=is_intent_name("SelectOrdinalIntent") )
def select_ordinal_handler(handler_input):

    slots = handler_input.request_envelope.request.intent.slots
    slots[ 'xnumber' ] = slots[ 'xordinal']
    
    # load attributes    
    p_attr = handler_input.attributes_manager.persistent_attributes
    s_attr = handler_input.attributes_manager.session_attributes

    stext, rtext, p_attr, s_attr = intent_helper.selectnumber_helper( p_attr, s_attr, slots )

    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
    
    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response










# ##########################################################################
# # Handler SelectBlackPressPubIntent 
# # user is making name request from black press list
# # Black Press is a challenge because they have > 100 pubs
# # so I can't use dynamic entities to juggle the slots
# @sb.request_handler(can_handle_func=is_intent_name("SelectBlackPressPubIntent") )
# def select_BP_pub_handler(handler_input):

#     slots = handler_input.request_envelope.request.intent.slots
#     bppub_name = slots['bppub_name'].value
#     #bppub_canval = slots['bppub_name'].resolutions.resolutions_per_authority[0].values[0].value.name

#     bppub_name = bppub_name.lower()

#     # load attributes    
#     p_attr = handler_input.attributes_manager.persistent_attributes
#     s_attr = handler_input.attributes_manager.session_attributes

    
#     stext, rtext, p_attr, s_attr = intent_helper.select_BlackPress_publication_byname_helper( p_attr, s_attr, bppub_name, '', slots )
    

#     # save attributes
#     handler_input.attributes_manager.session_attributes = s_attr
#     handler_input.attributes_manager.persistent_attributes = p_attr
#     handler_input.attributes_manager.save_persistent_attributes()
    
#     handler_input.response_builder.speak(stext).ask(rtext)
#     return handler_input.response_builder.response









##########################################################################
# Handler Select date Intent 
# user is making generic selection
@sb.request_handler(can_handle_func=is_intent_name("SelectDateIntent") )
def select_date_handler(handler_input):

    slots = handler_input.request_envelope.request.intent.slots
        
    # load attributes    
    p_attr = handler_input.attributes_manager.persistent_attributes
    s_attr = handler_input.attributes_manager.session_attributes

    stext, rtext, p_attr, s_attr = intent_helper.selectdate_helper( p_attr, s_attr, slots )


    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
    
    #s_attr['x_slotname'] = "GENRE_SLOT"
    
    if s_attr['x_entity'] == []:
        handler_input.response_builder.speak(stext).ask(rtext)
    elif s_attr['x_slotname'] != [] and s_attr['x_entity'] != []:
        replace_entity_directive = DynamicEntitiesDirective(
                                  update_behavior=UpdateBehavior.REPLACE,
                                  types=[EntityListItem(name=s_attr['x_slotname'],
                                  values= s_attr['x_entity'] )],
                                  )
         
        handler_input.response_builder.speak( stext ).ask( rtext ).add_directive(replace_entity_directive).response
    return handler_input.response_builder.response








##########################################################################
# Handler Select today or yesterday Intent 
# user is making date based request using today or yesterday
@sb.request_handler(can_handle_func=is_intent_name("SelectRecentIntent") )
def select_recent_handler(handler_input):

    slots = handler_input.request_envelope.request.intent.slots
    xtype = slots['xtype'].value
    recent_val = slots['RTY_val'].value
    
        
    # load attributes    
    p_attr = handler_input.attributes_manager.persistent_attributes
    s_attr = handler_input.attributes_manager.session_attributes

    
    stext, rtext, p_attr, s_attr = intent_helper.Xselectrecent_helper( p_attr, s_attr, recent_val, 'NULL', xtype )
 
    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
    
    #s_attr['x_slotname'] = "GENRE_SLOT"
    
    if s_attr['x_entity'] == []:
        handler_input.response_builder.speak(stext).ask(rtext)
    elif s_attr['x_slotname'] != [] and s_attr['x_entity'] != []:
        replace_entity_directive = DynamicEntitiesDirective(
                                  update_behavior=UpdateBehavior.REPLACE,
                                  types=[EntityListItem(name=s_attr['x_slotname'],
                                  values= s_attr['x_entity'] )],
                                  )
         
        handler_input.response_builder.speak( stext ).ask( rtext ).add_directive(replace_entity_directive).response
    return handler_input.response_builder.response




##########################################################################
##########################################################################
# Handler to select a recent day of the week
# Ex: "last wednesday's edition"
@sb.request_handler(can_handle_func=is_intent_name("SelectRecentWeekdayIntent") )
def select_weekday_handler(handler_input):

    slots = handler_input.request_envelope.request.intent.slots
    d_val = slots['date_value'].value

    # load attributes    
    p_attr = handler_input.attributes_manager.persistent_attributes
    s_attr = handler_input.attributes_manager.session_attributes
    
    # build response
    stext, rtext, p_attr, s_attr = intent_helper.select_weekday_helper( p_attr, s_attr, d_val)
    
    #s_attr['last_speak'] = stext
    #s_attr['last_reprompt'] = rtext

    # save attributes    
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()

    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response




# ##########################################################################
# # Handler CompoundEPIntent
# # handle compound request for publication and edition all at once
# @sb.request_handler(can_handle_func=is_intent_name("CompoundRecentPubIntent") )
# def compound_RecentPub_handler(handler_input):

#     slots = handler_input.request_envelope.request.intent.slots

#     # load attributes    
#     p_attr = handler_input.attributes_manager.persistent_attributes
#     s_attr = handler_input.attributes_manager.session_attributes

#     stext, rtext, p_attr, s_attr = intent_helper.compound_RecentPub_helper( p_attr, s_attr, slots )



#     # save attributes
#     handler_input.attributes_manager.session_attributes = s_attr
#     handler_input.attributes_manager.persistent_attributes = p_attr
#     handler_input.attributes_manager.save_persistent_attributes()
    
#     handler_input.response_builder.speak(stext).ask(rtext)
#     return handler_input.response_builder.response






# ##########################################################################
# # Handler CompoundDPIntent
# # handle compound request for publication and specific dated edition all at once
# @sb.request_handler(can_handle_func=is_intent_name("CompoundDatePubIntent") )
# def compound_DatePub_handler(handler_input):

#     slots = handler_input.request_envelope.request.intent.slots

#     # load attributes    
#     p_attr = handler_input.attributes_manager.persistent_attributes
#     s_attr = handler_input.attributes_manager.session_attributes

#     stext, rtext, p_attr, s_attr = intent_helper.compoundDatePub_helper( p_attr, s_attr, slots )

#     # save attributes
#     handler_input.attributes_manager.session_attributes = s_attr
#     handler_input.attributes_manager.persistent_attributes = p_attr
#     handler_input.attributes_manager.save_persistent_attributes()
    
#     handler_input.response_builder.speak(stext).ask(rtext)
#     return handler_input.response_builder.response




 



# ##########################################################################
# # Handler for requested list of locations
# @sb.request_handler(can_handle_func=is_intent_name("ListByLocationIntent") )
# def listbylocation_handler(handler_input):

#     slots = handler_input.request_envelope.request.intent.slots
#     xloc = slots['xlocation'].value

#     # load attributes    
#     p_attr = handler_input.attributes_manager.persistent_attributes
#     s_attr = handler_input.attributes_manager.session_attributes

#     stext, rtext, p_attr, s_attr = intent_helper.listbylocation_helper( p_attr, s_attr, xloc)
    
#     # save attributes
#     handler_input.attributes_manager.session_attributes = s_attr
#     handler_input.attributes_manager.persistent_attributes = p_attr
#     handler_input.attributes_manager.save_persistent_attributes()
    
#     handler_input.response_builder.speak(stext).ask(rtext)
#     return handler_input.response_builder.response
    
    
    
    
    
    
    
    
##########################################################################
##########################################################################
# Handler for That One Intent
@sb.request_handler(can_handle_func=is_intent_name("ThatOneIntent"))
def thatone_intent_handler(handler_input):
    # load attributes
    p_attr = handler_input.attributes_manager.persistent_attributes    
    s_attr = handler_input.attributes_manager.session_attributes    
    
    # build response
    stext, rtext, p_attr, s_attr = intent_helper.thatone_helper( p_attr, s_attr )

    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
        
    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response
    
    
    
    



##########################################################################
##########################################################################
# Handler for Open Intent
@sb.request_handler(can_handle_func=is_intent_name("OpenIntent"))
def open_intent_handler(handler_input):
    # load attributes
    p_attr = handler_input.attributes_manager.persistent_attributes    
    s_attr = handler_input.attributes_manager.session_attributes    
    
    # build response
    stext, rtext, p_attr, s_attr = intent_helper.open_helper( p_attr, s_attr )

    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
        
    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response






##########################################################################
##########################################################################
# Handler for whats new Intent
@sb.request_handler(can_handle_func=is_intent_name("WhatsNewIntent"))
def whatsnew_intent_handler(handler_input):
    # load attributes
    p_attr = handler_input.attributes_manager.persistent_attributes    
    s_attr = handler_input.attributes_manager.session_attributes    
    
    # build response
    stext, rtext, p_attr, s_attr = intent_helper.whatsnew_helper( p_attr, s_attr )

    # save attributes
    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()
        
    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response






##########################################################################
##########################################################################
# fallback intent
@sb.request_handler(can_handle_func=lambda input:
                    is_intent_name("AMAZON.FallbackIntent")(input) or
                    is_intent_name("AMAZON.YesIntent")(input) or
                    is_intent_name("AMAZON.NoIntent")(input))
def fallback_handler(handler_input):
    

    s_attr = handler_input.attributes_manager.session_attributes
    
    
    stext = "This is embarrasing, but I must have misunderstood. "
    stext += " Let's try again. "
    stext += s_attr['last_speak']
    rtext = s_attr['last_reprompt']

    
    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response








##########################################################################
##########################################################################
# handle unhandled intents
@sb.request_handler(can_handle_func=lambda input: True)
def unhandled_intent_handler(handler_input):
    
    p_attr = handler_input.attributes_manager.persistent_attributes        
    # initialize session attr
    s_attr = attr_helper.init_s_attr( )

    stext, rtext, p_attr, s_attr = intent_helper.unhandled_helper( p_attr, s_attr )    
    

    handler_input.attributes_manager.session_attributes = s_attr
    handler_input.attributes_manager.persistent_attributes = p_attr
    handler_input.attributes_manager.save_persistent_attributes()

    handler_input.response_builder.speak(stext).ask(rtext)
    return handler_input.response_builder.response




##########################################################################
##########################################################################

@sb.exception_handler(can_handle_func=lambda i, e: True)
def all_exception_handler(handler_input, exception):
    # load attributes
    p_attr = handler_input.attributes_manager.persistent_attributes    
    s_attr = handler_input.attributes_manager.session_attributes    

    # type: (HandlerInput, Exception) -> Response
    logger.error(exception, exc_info=True)
    stext = "Sorry, I didn't understand that. Please make sure you're speaking clearly, or try another command. "
    
    print('XUSER ID: ' + str(p_attr['xuserID' ]))
    print('CURRENT MENU: ' + s_attr['current_menu'])
    print('YES NO QUESTION: ' + s_attr['yesno_question'])
    print('LAST SPEAK: ' + s_attr['last_speak'])
    
    handler_input.response_builder.speak(stext).ask(stext)
    return handler_input.response_builder.response






##########################################################################
##########################################################################

@sb.global_response_interceptor()
def log_response(handler_input, response):
    """Response logger."""
    # type: (HandlerInput, Response) -> None
    logger.info("Response: {}".format(response))


lambda_handler = sb.lambda_handler()