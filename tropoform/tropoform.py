#!/usr/bin/env python
"""
Script to manage troposphere templates like terraform
"""
__version__ = '0.3.6'

import boto3
from datetime import datetime
import time
import yaml
import logging
from botocore.exceptions import ClientError
import os
import sys
import argparse
from boto3 import client
from typing import Optional, Union
from colorlog import colorlog

# Configure the global logger
# global logger
logger = logging.getLogger()
# Set these extra verbose loggers to INFO or WARNING (even when app is in debug)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.INFO)

# Get the default region from the environment variables if it exists
default_region = None
if 'AWS_DEFAULT_REGION' in os.environ:
    default_region = os.environ['AWS_DEFAULT_REGION']

# Many cloud formation stacks require capability to add IAM resources. Set it by default
default_capabilities = 'CAPABILITY_NAMED_IAM'


# create a base class for a Tropoform Stack Module
class TropoformStackBase:
    def get_template(self):
        pass


def _get_logger(verbose: bool = False) -> logging:
    """
        Setup the logging environment
    """
    logger = logging.getLogger()  # root logger
    if verbose:
        logger.setLevel(logging.DEBUG)
        format_str = '%(asctime)s - %(levelname)-8s - %(module)s:%(funcName)-20s - %(message)s'
    else:
        logger.setLevel(logging.INFO)
        format_str = '%(message)s'

    date_format = '%Y-%m-%d %H:%M:%S'
    if os.isatty(2):
        color_format = '%(log_color)s' + format_str
        colors = {'DEBUG': 'green',
                  'INFO': 'reset',
                  'WARNING': 'bold_yellow',
                  'ERROR': 'bold_red',
                  'CRITICAL': 'bold_red'}
        formatter = colorlog.ColoredFormatter(color_format, date_format, log_colors=colors)
    else:
        formatter = logging.Formatter(format_str, date_format)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logging.getLogger(__name__)


def _create_cfn_parameters(parameters_dict: dict) -> list:
    """
    Converts a dict of key/value pairs into cloud formation list of dicts
    :parm dict parameters_dict: parameters_dict dictionary to be converted to cfn parameters_dict
    :return: list of dicts formatted for cloud formation Parameters
    """
    result = list()
    if not parameters_dict:
        return result
    for key in parameters_dict.keys():
        result.append({'ParameterKey': key, 'ParameterValue': parameters_dict[key]})
    return result


def _get_cfn_client(region: str, profile: str = None) -> boto3.client:
    """
    Returns a boto3 cloud formation client in specified region
    :param str region: AWS region name
    :param str profile: Name of an AWS named profile to use for credentials
    :return boto3.client
    """
    logger.debug(f"Creating Cloudformation client in region {region}")
    if profile:
        session = boto3.Session(profile_name=profile)
    else:
        session = boto3.Session()
    try:
        cfn_client: client = session.client("cloudformation", region_name=region)
    except Exception as e:
        logger.error("unable to create a cloud formation client resource")
        logger.error(e)
        if __name__ == "__main__":
            sys.exit(1)
        else:
            raise e
    return cfn_client


def _get_stack_status(stack_name: str, region: str, profile: str = None) -> Optional[str]:
    """
    Returns the status of a stack. None if not deployed
    :param str stack_name: Name of the stack to check
    :param str region: Name of the aws region
    :param str profile: Name of an AWS named profile to use for credentials
    :return: str : Status of stack, None if not deployed
    """
    logger.debug(f"Getting stack status for {stack_name} in {region}")
    cfn_client = _get_cfn_client(region=region, profile=profile)
    try:
        result = cfn_client.describe_stacks(StackName=stack_name)
    except ClientError as e:
        if 'does not exist' in e.__str__():
            logger.debug(f"Stack {stack_name} has no status. Is it deployed?")
            return None
        else:
            raise e
    return result['Stacks'][0]['StackStatus']


def _stack_is_complete(stack_name: str, region: str, profile: str = None) -> bool:
    """
    Returns true if stack is in completed state, else returns false
    :param str stack_name: Name of the stack
    :param str region: Name of the region to perform operation
    :return: True if is in completed state, else false
    """
    logger.debug(f"Checking if stack {stack_name} in region {region} is in completed state")
    stack_status = _get_stack_status(stack_name, region=region, profile=profile)
    if not stack_status:
        logger.debug(f"STACK: {stack_name} has no status. not complete")
        return False
    if stack_status[-9:] == "_COMPLETE" or stack_status[-7:] == "_FAILED":
        logger.debug(f"STACK: {stack_name} status: {stack_status} is complete in region {region}")
        return True
    logger.debug(f"STACK: {stack_name} status: {stack_status} is not complete in region {region}")
    return False


def _get_stack_outputs(stack_name: str, region: str, profile: str = None) -> list:
    """
    Returns list stack outputs
    :param str stack_name: Name of the stack to query
    :param str region: Name of the region to perform operation
    :param str profile: Name of an AWS named profile to use for credentials
    :return: list of stack outputs
    """
    logger.debug(f"Getting stack {stack_name} outputs in region {region}")
    cfn_client = _get_cfn_client(region=region, profile=profile)
    try:
        result = cfn_client.describe_stacks(StackName=stack_name)
    except ClientError as e:
        if 'does not exist' in e.__str__():
            logger.warning(f"Stack f{stack_name} has no status. Is it deployed?")
            return []
        else:
            raise e
    if 'Outputs' not in result['Stacks'][0]:
        logger.debug(f"stack {stack_name} has no outputs")
        return list()
    else:
        logger.debug(f"stack {stack_name} has outputs: {result['Stacks'][0]['Outputs']}")
        return result['Stacks'][0]['Outputs']


def _get_stack_resources(stack_name: str, region: str, profile: str = None) -> list:
    """
    Returns list stack resources
    :param str stack_name: Name of the stack to query
    :param str region: Name of the region to perform operation
    :param str profile: Name of an AWS named profile to use for credentials
    :return: list of stack resources
    """
    logger.debug(f"Getting stack {stack_name} resources in region {region}")
    cfn_client = _get_cfn_client(region=region, profile=profile)
    try:
        result = cfn_client.describe_stack_resources(StackName=stack_name)
    except Exception as e:
        if 'does not exist' in e.__str__():
            logger.warning(f"Stack f{stack_name} does not exits. Is it deployed?")
            return []
        else:
            raise e
    logger.debug(f"stack {stack_name} resource:{result['StackResources']}")
    return result['StackResources']


def _load_parameter_files(parameter_files: str) -> Optional[dict]:
    """
    :param str parameter_files: comma separated list of file names
    :return: dictionary of parameters, None of no params
    """
    logger.debug(f"loading parameter files: {parameter_files}")
    result = dict()
    if not parameter_files:
        return result
    parameter_files = parameter_files.split(",")
    logger.debug(f"Parameter file list: {parameter_files}")
    for parameter_file in parameter_files:
        logger.debug(f"loading parameter file: {parameter_file}")
        try:
            data = yaml.load(open(parameter_file, "r"), Loader=yaml.BaseLoader)
        except Exception as e:
            logger.error(f"unable to load yaml file: {parameter_file}")
            logger.error(e)
            raise e
        # combine the dictionaries
        result = {**result, **data}
    logger.debug(f"parameter file parameters: {result}")
    return result


def _template_isvalid(template_body: str, region: str, profile: str = None) -> bool:
    """
    Validates whether template body is valid
    :param str template_body:
    :param str region: Name of the region to perform operation
    :param str profile: Name of an AWS named profile to use for credentials
    :return: bool True if valid
    """
    logger.debug(f"checking if template is valid in region {region}")
    cfn_client = _get_cfn_client(region=region, profile=profile)
    try:
        cfn_client.validate_template(TemplateBody=template_body)
    except Exception as e:
        if 'Template format error' in e.__str__():
            logger.warning(e)
            return False
        else:
            raise e
    logger.debug(f"template is valid")
    return True


def _fmt_timedelta(time_delta: datetime.time):
    """
    Formats a timedelta object into hours:minutes:seconds string
    :param timedelta time_delta:
    :return: string
    """
    hours, rem = divmod(time_delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    hours = str(hours).zfill(2)
    minutes = str(minutes).zfill(2)
    seconds = str(seconds).zfill(2)
    return f"{hours}:{minutes}:{seconds}"


def _get_failed_stack_events(stack_name: str, region: str, profile: str = None) -> list:
    """
    Returns a list of stack events that have status that includes FAILED
    :param str stack_name:
    :param str region: Name of the region in which to perform the operation
    :param str profile: Name of an AWS named profile to use for credentials
    :return: list of failed events
    """
    logger.debug(f"getting stack {stack_name} failure events in region {region}")
    cfn_client = _get_cfn_client(region=region, profile=profile)
    try:
        events = cfn_client.describe_stack_events(StackName=stack_name)
    except Exception as e:
        logger.error(f"unable to get stack events")
        logger.error(e)
        raise e
    result = list()
    for event in events['StackEvents']:
        if "FAILED" in event['ResourceStatus']:
            result.append(event)
    if len(result) == 0:
        # There were no FAILED events. Look for ROLLBACK_IN_PROGRESS
        for event in events['StackEvents']:
            if "ROLLBACK_IN_PROGRESS" in event['ResourceStatus']:
                result.append(event)
    logger.debug(f"failure events {result}")
    return result


def _import_tropo_module(stack_name: str, module_name: str = None) -> Union[object, TropoformStackBase]:
    """
    Import a troppsphere module
    :param stack_name:
    :param module_name:
    :return: troposphere module object
    """
    if module_name:
        logger.debug(f"importing troposphere module: {module_name}")
        sys.path.append(os.path.dirname(module_name))
        module_name = os.path.basename(module_name).replace(".py", "")
        stack = __import__(module_name)
    else:
        logger.debug(f"importing troposphere module: {stack_name}")
        sys.path.append(os.getcwd())
        try:
            stack = __import__(stack_name)
        except Exception as e:
            logger.critical(f"failed to import troposphere module: {stack_name}")
            logger.critical(e)
            raise e
    return stack


def _load_template(template_file: str = None, module_name: str = None, stack_name: str = None) -> str:
    """
    gets a string of template body from either template_file or module_name or stack_name
    :param stack_name
    :param template_file
    :param module_name
    """
    if template_file:
        # read the template file
        with open(template_file, 'r') as fh:
            template_body = fh.read()
    else:
        # Import the troposphere module
        stack = _import_tropo_module(stack_name, module_name)
        # Get the yaml template file
        template_body = stack.get_template().to_json()
    return template_body


def list_stacks(stack_name: str = None, region: str = None, profile: str = None, **kwargs) -> bool:
    """
    Logs deployed stacks and their status
    :param str stack_name: optional stack name. Default is none
    :param region: optional region. Default is default_region
    :param str profile: Name of an AWS named profile to use for credentials
    :return: True if successful
    """
    cfn_client = _get_cfn_client(region=region, profile=profile)
    if stack_name:
        logger.debug(f"Logging stack {stack_name} in region {region}")
        if not _stack_is_complete(stack_name=stack_name, region=region, profile=profile):
            logger.error(f"STACK: {stack_name} "
                         f"in status: {_get_stack_status(stack_name=stack_name, region=region, profile=profile)}. Exiting")
            return False
        try:
            stacks = cfn_client.describe_stacks(StackName=stack_name)
        except Exception as e:
            logger.error(f"unable to retrieve stack list")
            logger.error(e)
            return False
    else:
        logger.debug(f"Logging stacks in region {region}")
        try:
            stacks = cfn_client.describe_stacks()
        except Exception as e:
            logger.error(f"unable to retrieve stack list")
            logger.error(e)
            return False
    logger.info(f"{'stack_name':{20}} {'stack_status':{20}} {'drift_status':{20}} {'stack_description'}")
    for stack in stacks['Stacks']:
        stack_name = stack['StackName']
        stack_status = stack['StackStatus']
        drift_status = stack['DriftInformation']['StackDriftStatus']
        if 'Description' in stack:
            stack_description = stack['Description']
        else:
            stack_description = ''
        logger.info(f"{stack_name:{20}} {stack_status:{20}} {drift_status:{20}} {stack_description}")

    return True


def parameters(stack_name: str, region: str, profile: str = None, **kwargs) -> bool:
    """
    Logs the parameters deployed with a stack
    :param str stack_name:
    :param str region: Name of the region in which to perform the operation
    :param str profile: Name of an AWS named profile to use for credentials
    :return: True if successful
    """
    logger.debug(f"Logging stack {stack_name} parameters in region {region}")
    if not _stack_is_complete(stack_name=stack_name, region=region, profile=profile):
        logger.error(f"STACK: {stack_name} not in completed status. "
                     f"{_get_stack_status(stack_name=stack_name, region=region, profile=profile)}")
        return False
    cfn_client = _get_cfn_client(region=region, profile=profile)
    try:
        stack = cfn_client.describe_stacks(StackName=stack_name)['Stacks'][0]
    except Exception as e:
        logger.error(f"unable to describe stack {stack_name}")
        logger.error(e)
        return False
    logger.info(f"STACK: {stack_name} Parameters: ")
    for parameter in stack['Parameters']:
        logger.info(f"{parameter['ParameterKey']:{20}} = {parameter['ParameterValue']} ")
    return True


def output(stack_name: str, region: str, profile: str = None, **kwargs) -> bool:
    """
    Logs outputs of a cloud formation stack
    :param str stack_name:
    :param str region: Name of the region to perform operation
    :param str profile: Name of an AWS named profile to use for credentials
    :return: bool True if successful
    """
    logger.debug(f"Logging stack {stack_name} outputs in region {region}")
    if not _stack_is_complete(stack_name=stack_name, region=region, profile=profile):
        logger.error(f"STACK: {stack_name} "
                     f"in status: {_get_stack_status(stack_name=stack_name, region=region, profile=profile)}. Exiting")
        return False
    logger.info("STACK OUTPUTS:")
    for stack_output in _get_stack_outputs(stack_name=stack_name, region=region, profile=profile):
        logger.info(f"{stack_output['OutputKey']:{20}} = {stack_output['OutputValue']}")
    return True


def reason(stack_name: str, region: str, profile: str = None, **kwargs) -> bool:
    """
    Logs the reason for a failed stack to info
    :param str stack_name:
    :param str region: Name of the region in which to perform the operation
    :return: True if successful
    """
    logger.debug(f"Logging stack {stack_name} failure reason in region {region}")
    events = _get_failed_stack_events(stack_name=stack_name, region=region, profile=profile)
    logger.info(f"STACK {stack_name} create/update FAILED due to the following stack events:")
    if len(events) > 0:
        logger.info(f"{'UTC time':{10}} {'ResourceStatus':{15}} {'ResourceType':{35}} "
                    f"{'LogicalResourceId':{30}} {'ResourceStatusReason'}")
        for event in events:
            timestamp = event['Timestamp'].strftime("%H:%M:%S")
            status_reason = event['ResourceStatusReason']  # .split("(")[0]
            if "Resource update cancelled" not in status_reason:
                logger.info(f"{timestamp:{10}} {event['ResourceStatus']:{15}} {event['ResourceType']:{35}} "
                            f"{event['LogicalResourceId']:{30}} {status_reason}")
    return True


def apply(stack_name: str, region: str, module_name: str = None, template_file: str = None,
          parameter_files: str = None, capabilities: str = default_capabilities, auto_approve: bool = False,
          role_arn: str = None, profile: str = None, **kwargs
          ) -> bool:
    """
    Creates/Updates a cloud formation stack. Logs output
    :param str stack_name: name of stack to create. If module_name not given, uses python module by same name in cwd
    :param str module_name: name of the python troposphere module to import (if different than stack_name)
    :param str template_file: optional name of cloud formation template file to deploy
    :param str capabilities: comma separated list of capabilities
    :param str region: Name of the region in which to perform the operation
    :param str parameter_files: optional comma separated list of parameter files
    :param bool auto_approve: to eliminate user prompt set to True, default = False
    :param str role_arn: the role cloudformation will assume for create/update stack operations
    :param str profile: Name of an AWS named profile to use for credentials
    :return: True if successful
    """
    logger.debug(f"applying stack: {stack_name}. module_name: {module_name}, parameter_files: {parameter_files} "
                 f"capabilities: {capabilities}, auto_approve: {auto_approve}, region: {region}")

    # Import the troposphere module
    template_body = _load_template(template_file=template_file, module_name=module_name, stack_name=stack_name)
    template_dict = yaml.load(template_body, Loader=yaml.BaseLoader)
    # stack = _import_tropo_module(stack_name, module_name)

    # Generate cloud formation parameters from supplied input files
    cfn_parameters = _create_cfn_parameters(_load_parameter_files(parameter_files))
    # Split incoming capabilities string
    capabilities = capabilities.split(",")

    # Get the current stack status
    stack_status = _get_stack_status(stack_name=stack_name, region=region, profile=profile)
    logger.info(f"STACK: {stack_name}, Current Status: {stack_status}")

    # Create a cloud formation client
    cfn_client = _get_cfn_client(region=region, profile=profile)

    # See if Stack is deployed
    if stack_status is None:
        # Stack not yet deployed
        # template = stack.get_template()
        logger.info(f"CREATING Stack: {stack_name} with {len(template_dict['Resources'])} resources")
        # Check for approval
        if not auto_approve:
            response = input("Are you sure? [yes|no] ")
            if response.lower() != "yes":
                logger.error(f"Exiting")
                return False
        # Start the timer
        start = datetime.now()

        # Create the stack
        try:
            if role_arn:
                cfn_client.create_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Parameters=cfn_parameters,
                    Capabilities=capabilities,
                    RoleARN=role_arn
                )
            else:
                cfn_client.create_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Parameters=cfn_parameters,
                    Capabilities=capabilities,
                )
        except Exception as e:
            logger.error(f"STACK {stack_name} NOT CREATED. Error occurred")
            logger.error(e)
            return False
        action = "deployed"

    # See if stack is already in a deployed (*_COMPLETE) status
    elif _stack_is_complete(stack_name=stack_name, region=region, profile=profile):
        # Stack is already deployed and ready for update
        # Generate the yaml file
        # template = stack.get_template().to_yaml()
        logger.info(f"UPDATING Stack: {stack_name}")
        # get approval
        if not auto_approve:
            response = input("Are you sure? [yes|no] ")
            if response.lower() != "yes":
                logger.error(f"Exiting")
                return False
        # start the timer
        start = datetime.now()
        # Update the stack
        try:
            if role_arn:
                cfn_client.update_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Parameters=cfn_parameters,
                    Capabilities=capabilities,
                    RoleARN=role_arn
                )
            else:
                cfn_client.update_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Parameters=cfn_parameters,
                    Capabilities=capabilities,
                )
        except Exception as e:
            if 'No updates are to be performed' in e.__str__():
                # No updates required. Continue without error
                logger.warning(f"STACK {stack_name} NOT UPDATED. No updates were required")
            else:
                # If this isn't a no updates required warning, bail out
                logger.error(f"STACK {stack_name} NOT UPDATED. Error occurred")
                logger.error(e)
                return False
        action = 'updated'

    # Stack is in error state
    else:
        logger.info(f"ERROR: Stack not in a complete status. Exiting")
        return False

    # Wait for stack to enter complete status
    while not _stack_is_complete(stack_name=stack_name, region=region, profile=profile):
        time.sleep(15)
        stack_status = _get_stack_status(stack_name=stack_name, region=region, profile=profile)
        logger.info(f"STACK: {stack_name}, Status: {stack_status} - {datetime.now().strftime('%H:%M:%S')}")

    # Stop the timer
    end = datetime.now()
    duration = _fmt_timedelta((end - start))

    # If stack_status is in FAILED state or ROLLBACK, determine reason from events
    if "FAILED" in stack_status or "ROLLBACK" in stack_status:
        logger.warning(f"STACK: {stack_name} not {action} and is in status {stack_status}")
        reason(stack_name=stack_name, region=region, profile=profile)
        return False

    # Print number of resources deployed
    logger.info(f"STACK: {stack_name} {action} "
                f"{len(_get_stack_resources(stack_name=stack_name, region=region, profile=profile))} resources "
                f"in {duration}")

    # Print outputs
    output(stack_name=stack_name, region=region, profile=profile)

    return True


def plan(stack_name: str, region: str, module_name: str = None, template_file: str = None, parameter_files: str = None,
         capabilities: str = default_capabilities, output_type: str = 'text', delete_change_set: bool = True,
         profile: str = None, **kwargs
         ) -> bool:
    """
    Creates a Change Plan for a cloud formation stack and logs the results
    :param str stack_name: stack name
    :param str module_name: optional name of troposphere stack module (if different than stack name)
    :param str template_file: optional name of cloud formation template file to deploy
    :param str region: Name of the region in which to perform the operation
    :param str parameter_files: optional list of yaml parameter files to include
    :param str capabilities: option list of comma separated capabilities to allow
    :param str output_type: optional [text|yaml|json], default is text
    :param bool delete_change_set: optional delete change set? Default=False
    :param str profile: Name of an AWS named profile to use for credentials
    :return:
    """
    logger.debug(f"planning stack: {stack_name}. module_name: {module_name}, template_file: {template_file}, "
                 f"parameter_files: {parameter_files}, capabilities: {capabilities}, region: {region}")

    template_body = _load_template(template_file=template_file, module_name=module_name, stack_name=stack_name)
    template_dict = yaml.load(template_body, Loader=yaml.BaseLoader)

    if _template_isvalid(template_body, region=region, profile=profile):
        logger.debug(f"Template body is valid")
    else:
        logger.error(f"template body is invalid. Exiting")
        return False

    # See if the stack is already deployed
    if not _stack_is_complete(stack_name=stack_name, region=region, profile=profile):
        # Stack is not deployed yet
        logger.info(f"STACK: {stack_name} is not yet deployed")
        # If the user wants a dump of the template in json or yaml, do that then exit
        if output_type in ['yaml', 'json']:
            logger.info(f"{output_type} TEMPLATE START ------------------------")
            if output_type == "yaml":
                logger.info(template_body)
            elif output_type == "json":
                logger.info(template_dict.to_json())
            logger.info(f"{output_type} TEMPLATE END ------------------------")
            return True
        # If the user wants text output
        elif output_type in ['text']:
            logger.info(f"STACK: {stack_name} creates {len(template_dict['Resources'])}")
            logger.info(f"{'#':{2}}) {'action':{8}} {'logical_id':{25}} {'resource_type'}")
            # Go through each resource in the stack
            i = 0
            for resource in template_dict['Resources']:
                logger.info(
                    f"{i + 1:{2}}) {'Create':{8}} {resource:{25}} {template_dict['Resources'][resource]['Type']}")
                i += 1
        # invalid output type
        else:
            logger.error(f"invalid output type {output_type}. Must be text, json or yaml")
            return False

    # Template is already deployed
    else:
        # Generate cfn parameters from input files
        cfn_parameters = _create_cfn_parameters(_load_parameter_files(parameter_files))
        # split supplied capabilities string
        capabilities = capabilities.split(",")
        # Create a cfn client
        cfn_client = _get_cfn_client(region=region, profile=profile)
        # Generate a unique change set name
        change_set_name = 'change-' + datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        # Create a change stack set
        try:
            change_set_id = cfn_client.create_change_set(
                StackName=stack_name,
                TemplateBody=template_body,
                Parameters=cfn_parameters,
                Capabilities=capabilities,
                ChangeSetName=change_set_name
            )['Id']
        except Exception as e:
            logger.error(f"unable to creat stack: {stack_name} change set {change_set_name}")
            logger.error(e)
            return False
        # Wait for the status of the change set to be CREATE_COMPLETE
        change_set = cfn_client.describe_change_set(ChangeSetName=change_set_id)
        while change_set['Status'] != "CREATE_COMPLETE":
            if change_set['Status'] == "FAILED":
                # Uh oh, the change set failed
                if "The submitted information didn't contain changes" in change_set['StatusReason']:
                    # If no changes, stack set will error, let the user know
                    logger.info(f"No Changes Detected for Stack: {stack_name}")
                    # Delete the failed stack set
                    try:
                        cfn_client.delete_change_set(ChangeSetName=change_set_id)
                    except Exception as e:
                        logger.error(f"unable to delete stack {stack_name} change set {change_set_name}")
                        logger.error(e)
                        return False
                    return True
                else:
                    # the stack set failed for some other reason than no changes
                    logger.error(f"Stack set creation status failed for reason: {change_set['StatusReason']}. Exiting")
                    # Try to delete the failed stack set
                    try:
                        cfn_client.delete_change_set(ChangeSetName=change_set_id)
                    except Exception as e:
                        logger.error(f"unable to delete stack {stack_name} change set {change_set_name}")
                        logger.error(e)
                    return False
            time.sleep(5)
            change_set = cfn_client.describe_change_set(ChangeSetName=change_set_id)
            logger.debug(f"Change set status: {change_set['Status']}")

        # Ok, stack change set is complete, lets get the results
        logger.info(f"STACK: {stack_name} has {len(change_set['Changes'])} detected changes")
        logger.info(f"{'#':{2}}) {'action':{8}} {'logical_id':{20}} {'resource_id':{25}} "
                    f"{'resource_type':{30}} {'scope':{10}} Replace?")
        for i in range(len(change_set['Changes'])):
            # For each change item, print the details
            action = change_set['Changes'][i]['ResourceChange']['Action']
            if action not in ['Add', 'Remove']:
                replacement = change_set['Changes'][i]['ResourceChange']['Replacement']
                resource_id = change_set['Changes'][i]['ResourceChange']['PhysicalResourceId']
            else:
                replacement = ''
                resource_id = ''
            logical_id = change_set['Changes'][i]['ResourceChange']['LogicalResourceId']
            resource_type = change_set['Changes'][i]['ResourceChange']['ResourceType']
            scope = change_set['Changes'][i]['ResourceChange']['Scope']
            logger.info(f"{i + 1:{2}}) {action:{8}} {logical_id:{20}} {resource_id:{25}} "
                        f"{resource_type:{30}} {str(scope):{10}} {replacement}")
            # print(json.dumps(change_set['Changes'][i], indent=2))
        # If the user requested to delete change set (default = True)
        if delete_change_set:
            # try deleting the stack change set
            try:
                cfn_client.delete_change_set(ChangeSetName=change_set_id)
            except Exception as e:
                logger.error(e)
                return False
        else:
            logger.info(f"Stack {stack_name}, changeSet: {change_set_name} saved")
        return True


def destroy(stack_name: str, region: str, auto_approve: bool = False, profile: str = None, **kwargs) -> bool:
    """
    Deletes a cloud formation stack and logs the resulting output
    :param str stack_name:
    :param str region: Name of the region to perform operation
    :param bool auto_approve: If True, prompt user for approval
    :param str profile: Name of an AWS named profile to use for credentials
    :return: True if successful
    """
    logger.debug(f"destroying stack: {stack_name}, region: {region}, auto_approve: {auto_approve}")
    # Get a cfn client
    cfn_client = _get_cfn_client(region=region, profile=profile)
    # Get the stack status
    stack_status = _get_stack_status(stack_name=stack_name, region=region)
    # If it is not in a *_COMPLETE state, bail out
    if not _stack_is_complete(stack_name=stack_name, region=region, profile=profile):
        logger.error(f"STACK: {stack_name} in status {stack_status}. Cant delete now. Exiting")
        return False
    # See how many resources are deployed
    resource_count = len(_get_stack_resources(stack_name=stack_name, region=region, profile=profile))
    logger.info(f"DELETING STACK: {stack_name} with {resource_count} resources")
    # Get user approval
    if not auto_approve:
        response = input("Are you sure? [yes|no] ")
        if response.lower() != "yes":
            logger.error(f"Exiting")
            return False
    # Start the timer
    start = datetime.now()
    # Delete the stack
    try:
        cfn_client.delete_stack(StackName=stack_name)
    except Exception as e:
        logger.error(e)
        return False

    while not _stack_is_complete(stack_name=stack_name, region=region, profile=profile):
        time.sleep(15)
        stack_status = _get_stack_status(stack_name=stack_name, region=region, profile=profile)
        logger.info(f"STACK: {stack_name}, Status: {stack_status} - {datetime.now().strftime('%H:%M:%S')}")
        if not stack_status:
            break

    # Stop the timer
    end = datetime.now()
    duration = _fmt_timedelta((end - start))
    logger.info(f"STACK: {stack_name} ended in {duration}")

    # If stack_status is in FAILED state or ROLLBACK, determine reason from events
    if stack_status and ("FAILED" in stack_status or "ROLLBACK" in stack_status):
        logger.warning(f"STACK: {stack_name} not deleted and is in status {stack_status}")
        reason(stack_name=stack_name, region=region, profile=profile)
        return False

    return True


def _parse_args(*args, **kwargs):
    """
    Parse input logs
    :param args:
    :return:
    """
    # help strings
    stack_help = "The name of the cloud formation stack on which to perform operation. "
    stack_help_2 = "If a module exists in the current working directory that matches " \
                   "the stack_name and has a get_template() method, module_name is not required"
    module_help = "The name of the python troposphere module that will create the template. " \
                  "Module must have a get_template() method that returns a valid troposphere.Template object"
    template_help = "The path to a cloud formation template file."
    region_help = f"The name of the AWS region to perform operations. default is the env variable: AWS_DEFAULT_REGION"
    capabilities_help = f"Comma separated list of AWS capabilities. default: {default_capabilities}"
    approve_help = "If set, user will not be prompted to approve changes. default=False"
    output_type_help = "The format of the logging output [text|yaml|json]. default=text"
    param_files_help = "Comma separated yaml parameter files that will be passed to cloud formation as parameters"
    role_arn = "The arn of an AWS IAM role that AWS CloudFormation assumes to create/update the stack"
    profile = "Name of an AWS named profile to use for credentials"
    # Create parser
    parser = argparse.ArgumentParser()
    # universal arguments
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=__version__))
    parser.add_argument("--profile", help=profile)
    parser.add_argument('-v', '--verbose', action='store_true', help="get DEBUG logging")
    subparsers = parser.add_subparsers(title='operation')
    # apply arguments
    apply_parser = subparsers.add_parser('apply', help="create or update stack")
    apply_parser.add_argument('stack_name', help=stack_help + stack_help_2)
    apply_me_group = apply_parser.add_mutually_exclusive_group(required=True)
    apply_me_group.add_argument('-m', '--module_name', help=module_help)
    apply_me_group.add_argument('-t', '--template_file', help=template_help)
    apply_parser.add_argument('-p', '--parameter_files', help=param_files_help)
    apply_parser.add_argument('-c', '--capabilities', default=default_capabilities, help=capabilities_help)
    apply_parser.add_argument('-r', '--region', default=default_region, help=region_help)
    apply_parser.add_argument('-a', '--role_arn', default=None, help=role_arn)
    apply_parser.add_argument('--auto_approve', action='store_true', help=approve_help)
    apply_parser.set_defaults(func=apply)
    # plan arguments
    plan_parser = subparsers.add_parser('plan', help="view change plan")
    plan_parser.add_argument('stack_name', help=stack_help + stack_help_2)
    plan_me_group = plan_parser.add_mutually_exclusive_group(required=True)
    plan_me_group.add_argument('-m', '--module_name', help=module_help)
    plan_me_group.add_argument('-t', '--template_file', help=template_help)
    plan_parser.add_argument('-p', '--parameter_files', help=param_files_help)
    plan_parser.add_argument('-c', '--capabilities', default=default_capabilities, help=capabilities_help)
    plan_parser.add_argument('-o', '--output_type', default='text', help=output_type_help)
    plan_parser.add_argument('-r', '--region', default=default_region, help=region_help)
    plan_parser.set_defaults(func=plan)
    # destroy arguments
    destroy_parser = subparsers.add_parser('destroy', help="remove stack")
    destroy_parser.add_argument('stack_name', help=stack_help)
    destroy_parser.add_argument('--auto_approve', action='store_true', help=approve_help)
    destroy_parser.add_argument('-r', '--region', default=default_region, help=region_help)
    destroy_parser.set_defaults(func=destroy)
    # list arguments
    list_parser = subparsers.add_parser('list', help="list stacks")
    list_parser.add_argument('stack_name', nargs='?', default=None, help=stack_help)
    list_parser.add_argument('-r', '--region', default=default_region, help=region_help)
    list_parser.set_defaults(func=list_stacks)
    # output arguments
    output_parser = subparsers.add_parser('output', help="view stack outputs")
    output_parser.set_defaults(func=output)
    output_parser.add_argument('stack_name', help=stack_help)
    output_parser.add_argument('-r', '--region', default=default_region, help=region_help)
    output_parser.set_defaults(func=output)
    # parameters arguments
    parameters_parser = subparsers.add_parser('parameters', help="list parameters used in a stack")
    parameters_parser.set_defaults(func=parameters)
    parameters_parser.add_argument('stack_name')
    parameters_parser.add_argument('-r', '--region', default=default_region, help=region_help)
    parameters_parser.set_defaults(func=parameters)
    # reason arguments
    reason_parser = subparsers.add_parser('reason', help="list reasons for failed stack")
    reason_parser.set_defaults(func=reason)
    reason_parser.add_argument('stack_name')
    reason_parser.add_argument('-r', '--region', default=default_region, help=region_help)
    reason_parser.set_defaults(func=reason)

    # parse logs
    args = parser.parse_args()

    # Make sure a func attribute is set, else throw an exception

    return parser, args


def main() -> bool:
    """
    Main Entry Point
    :return: True if operation successful
    """
    # parse the arguments
    parser, args = _parse_args()

    # Modify the global logger
    global logger
    logger = _get_logger(args.verbose)

    # Run the function defined in the args
    result = args.func(**vars(args))
    return 0 if result is True else 1


if __name__ == "__main__":
    # Call the main function with command line arguments
    sys.exit(main())
