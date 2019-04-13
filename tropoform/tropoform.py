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

# Get the default region from the environment variables if it exists
default_region = None
if 'AWS_DEFAULT_REGION' in os.environ:
    default_region = os.environ['AWS_DEFAULT_REGION']

# Many cloud formation stacks require capability to add IAM resources. Set it by default
default_capabilities = 'CAPABILITY_NAMED_IAM'

# Set these extra verbose loggers to INFO or WARNING (even when app is in debug)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.INFO)


def create_cfn_parameters(parameters, **kwargs) -> list:
    """
    Converts a dict of key/value pairs into cloud formation list of dicts
    :parm dict parameters: parameters to be converted to cfn parameters
    :return: list of dicts formatted for cloud formation Parameters
    """
    result = list()
    if not parameters:
        return result
    for key in parameters.keys():
        result.append({'ParameterKey': key, 'ParameterValue': parameters[key]})
    return result


def get_cfn_client(region=default_region, **kwargs) -> boto3.client:
    """
    Returns a boto3 cloud formation client in specified region
    :param str region: AWS region name
    :return boto3.client
    """
    try:
        cfn_client: client = boto3.client("cloudformation", region_name=region)
    except Exception as e:
        logging.error("unable to create a cloud formation client resource")
        logging.error(e)
        if __name__ == "__main__":
            sys.exit(1)
        else:
            raise e
    return cfn_client


def get_stack_status(stack_name, region=default_region, **kwargs) -> str:
    """
    Returns the status of a stack. None if not deployed
    :param str stack_name: Name of the stack to check
    :param str region: Name of the aws region
    :return: str : Status of stack, None if not deployed
    """
    cfn_client = get_cfn_client(region=region)
    try:
        result = cfn_client.describe_stacks(StackName=stack_name)
    except ClientError as e:
        if 'does not exist' in e.__str__():
            logging.debug(f"Stack f{stack_name} has no status. Is it deployed?")
            return None
        else:
            raise e
    return result['Stacks'][0]['StackStatus']


def stack_is_complete(stack_name, region=default_region, **kwargs) -> bool:
    """
    Returns true if stack is in completed state, else returns false
    :param string stack_name: Name of the stack
    :param string region: Name of the region to perform operation
    :return: True if is in completed state, else false
    """
    stack_status = get_stack_status(stack_name, region=region)
    if not stack_status:
        return False
    if stack_status[-9:] == "_COMPLETE" or stack_status[-7:] == "_FAILED":
        return True
    logging.debug(f"STACK: {stack_name} status: {stack_status} is not complete")
    return False


def get_stack_outputs(stack_name, region=default_region, **kwargs) -> list:
    """
    Returns list stack outputs
    :param string stack_name: Name of the stack to query
    :param string region: Name of the region to perform operation
    :return: list of stack outputs
    """
    cfn_client = get_cfn_client(region=region)
    try:
        result = cfn_client.describe_stacks(StackName=stack_name)
    except ClientError as e:
        if 'does not exist' in e.__str__():
            logging.warning(f"Stack f{stack_name} has no status. Is it deployed?")
            return []
        else:
            raise e
    if 'Outputs' not in result['Stacks'][0]:
        return list()
    else:
        return result['Stacks'][0]['Outputs']


def get_stack_resources(stack_name, region=default_region, **kwargs) -> list:
    """
    Returns list stack resources
    :param string stack_name: Name of the stack to query
    :param string region: Name of the region to perform operation
    :return: list of stack resources
    """
    cfn_client = get_cfn_client(region=region)
    try:
        result = cfn_client.describe_stack_resources(StackName=stack_name)
    except Exception as e:
        if 'does not exist' in e.__str__():
            logging.warning(f"Stack f{stack_name} does not exits. Is it deployed?")
            return []
        else:
            raise e
    return result['StackResources']


def load_parameter_files(parameter_files, **kwargs):
    """
    :param str parameter_files: comma separated list of file names
    :return: dictionary of parameters
    """
    result = dict()
    if not parameter_files:
        return result
    parameter_files = parameter_files.split(",")
    logging.debug(f"Parameter files: {parameter_files}")
    for parameter_file in parameter_files:
        logging.debug(f"loading parameter file: {parameter_file}")
        try:
            data = yaml.load(open(parameter_file, "r"), Loader=yaml.Loader)
        except Exception as e:
            logging.error(f"unable to load yaml file: {parameter_file}")
            logging.error(e)
            return False
        # combine the dictionaries
        result = {**result, **data}
    logging.debug(f"parameter file parameters: {result}")
    return result


def template_isvalid(template_body, region=default_region, **kwargs) -> bool:
    """
    Validates whether template body is valid
    :param string template_body:
    :param string region:
    :return: bool True if valid
    """
    cfn_client = get_cfn_client(region=region)
    try:
        cfn_client.validate_template(TemplateBody=template_body)
    except Exception as e:
        if 'Template format error' in e.__str__():
            logging.warning(e)
            return False
        else:
            raise e
    return True


def fmt_timedelta(time_delta, **kwargs):
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


def output(stack_name, region=default_region, **kwargs) -> bool:
    """
    Lists outputs of a cloud formation stack
    :param string stack_name:
    :param string region:
    :return: bool True if successful
    """

    if not stack_is_complete(stack_name=stack_name, region=region):
        logging.error(f"STACK: {stack_name} "
                      f"in status: {get_stack_status(stack_name=stack_name, region=region)}. Exiting")
        return False
    logging.info("STACK OUTPUTS:")
    for stack_output in get_stack_outputs(stack_name=stack_name, region=region):
        logging.info(f"{stack_output['OutputKey']:{20}} = {stack_output['OutputValue']}")
    return True


def list_stacks(stack_name=None, region=default_region, **kwargs) -> bool:
    """
    Lists deployed stacks and thier status
    :param string stack_name: optional stack name. Default is none
    :param region: optional region. Default is default_region
    :return:
    """
    cfn_client = get_cfn_client(region=region)
    if stack_name:
        if not stack_is_complete(stack_name=stack_name, region=region):
            logging.error(f"STACK: {stack_name} "
                          f"in status: {get_stack_status(stack_name=stack_name, region=region)}. Exiting")
            return False
        try:
            stacks = cfn_client.describe_stacks(StackName=stack_name)
        except Exception as e:
            logging.error(f"unable to retrieve stack list")
            logging.error(e)
            return False
    else:
        try:
            stacks = cfn_client.describe_stacks()
        except Exception as e:
            logging.error(f"unable to retrieve stack list")
            logging.error(e)
            return False
    logging.info(f"{'stack_name':{20}} {'stack_status':{20}} {'drift_status':{20}} {'stack_description'}")
    for stack in stacks['Stacks']:
        stack_name = stack['StackName']
        stack_status = stack['StackStatus']
        drift_status = stack['DriftInformation']['StackDriftStatus']
        if 'Description' in stack:
            stack_description = stack['Description']
        else:
            stack_description = ''
        logging.info(f"{stack_name:{20}} {stack_status:{20}} {drift_status:{20}} {stack_description}")

    return True


def get_failed_stack_events(stack_name, region=default_region, **kwargs) -> list:
    """
    Returns a list of stack events that have status that includes FAILED
    :param string stack_name:
    :param string region:
    :return: list of failed events
    """
    cfn_client = get_cfn_client(region=region)
    try:
        events = cfn_client.describe_stack_events(StackName=stack_name)
    except Exception as e:
        logging.error(f"unable to get stack events")
        logging.error(e)
        return False
    result = list()
    for event in events['StackEvents']:
        if "FAILED" in event['ResourceStatus']:
            result.append(event)
    if len(result) == 0:
        # There were no FAILED events. Look for ROLLBACK_IN_PROGRESS
        for event in events['StackEvents']:
            if "ROLLBACK_IN_PROGRESS" in event['ResourceStatus']:
                result.append(event)
    return result


def parameters(stack_name, region=default_region, **kwargs) -> bool:
    """
    Logs the parameters deployed with a stack
    :param string stack_name:
    :param string region:
    :return: True
    """
    if not stack_is_complete(stack_name=stack_name, region=region):
        logging.error(f"STACK: {stack_name} not in completed status. "
                      f"{get_stack_status(stack_name=stack_name, region=region)}")
        return False
    cfn_client = get_cfn_client(region=region)
    try:
        stack = cfn_client.describe_stacks(StackName=stack_name)['Stacks'][0]
    except Exception as e:
        logging.error(f"unable to describe stack {stack_name}")
        logging.error(e)
        return False
    logging.info(f"STACK: {stack_name} Parameters: ")
    for parameter in stack['Parameters']:
        logging.info(f"{parameter['ParameterKey']:{20}} = {parameter['ParameterValue']} ")
    return True


def reason(stack_name, region=default_region, **kwargs) -> bool:
    """
    Logs the reason for a failed stack to info
    :param string stack_name:
    :param string region:
    :return: True
    """
    events = get_failed_stack_events(stack_name=stack_name, region=region)
    logging.info(f"STACK {stack_name} create/update FAILED due to the following stack events:")
    if len(events) > 0:
        logging.info(f"{'UTC time':{10}} {'ResourceStatus':{15}} {'ResourceType':{35}} "
                     f"{'LogicalResourceId':{30}} {'ResourceStatusReason'}")
        for event in events:
            timestamp = event['Timestamp'].strftime("%H:%M:%S")
            status_reason = event['ResourceStatusReason'].split("(")[0]
            if "Resource update cancelled" not in status_reason:
                logging.info(f"{timestamp:{10}} {event['ResourceStatus']:{15}} {event['ResourceType']:{35}} "
                             f"{event['LogicalResourceId']:{30}} {status_reason}")
    return True


def apply(stack_name, module_name=None, parameter_files=None, capabilities=default_capabilities,
          region=default_region, auto_approve=False, **kwargs) -> bool:
    """
    :param string stack_name: name of stack to create. If module_name not given, uses python module by same name in cwd
    :param string module_name: name of the python troposphere module to import (if different than stack_name)
    :param string capabilities: comma separated list of capabilities
    :param string region: AWS region to perform operations
    :param string parameter_files: optional comma separated list of parameter files
    :param bool auto_approve: to eliminate user prompt set to True, default = False
    """

    # Import the troposphere module
    if module_name:
        sys.path.append(os.path.dirname(module_name))
        module_name = os.path.basename(module_name).replace(".py", "")
        stack = __import__(module_name)
    else:
        sys.path.append(os.getcwd())
        stack = __import__(stack_name)

    # Generate cloud formation parameters from supplied input files
    cfn_parameters = create_cfn_parameters(load_parameter_files(parameter_files))
    # Split incoming capabilities string
    capabilities = capabilities.split(",")

    # Get the current stack status
    stack_status = get_stack_status(stack_name=stack_name, region=region)
    logging.info(f"STACK: {stack_name}, Current Status: {stack_status}")

    # Create a cloud formation client
    cfn_client = get_cfn_client(region=region)

    # See if Stack is deployed
    if stack_status is None:
        # Stack not yet deployed
        template = stack.get_template()
        logging.info(f"CREATING Stack: {stack_name} with {len(template.resources)} resources")
        # Check for approval
        if not auto_approve:
            response = input("Are you sure? [yes|no] ")
            if response.lower() != "yes":
                logging.error(f"Exiting")
                return False
        # Start the timer
        start = datetime.now()

        # Create the stack
        try:
            cfn_client.create_stack(
                StackName=stack_name,
                TemplateBody=template.to_yaml(),
                Parameters=cfn_parameters,
                Capabilities=capabilities,
            )
        except Exception as e:
            logging.error(f"STACK {stack_name} NOT CREATED. Error occurred")
            logging.error(e)
            return False
        action = "deployed"

    # See if stack is already in a deployed (*_COMPLETE) status
    elif stack_is_complete(stack_name=stack_name, region=region):
        # Stack is already deployed and ready for update
        # Generate the yaml file
        template = stack.get_template().to_yaml()
        logging.info(f"UPDATING Stack: {stack_name}")
        # get approval
        if not auto_approve:
            response = input("Are you sure? [yes|no] ")
            if response.lower() != "yes":
                logging.error(f"Exiting")
                return False
        # start the timer
        start = datetime.now()
        # Update the stack
        try:
            cfn_client.update_stack(
                StackName=stack_name,
                TemplateBody=template,
                Parameters=cfn_parameters,
                Capabilities=capabilities,
            )
        except Exception as e:
            if 'No updates are to be performed' in e.__str__():
                # No updates required. Continue without error
                logging.warning(f"STACK {stack_name} NOT UPDATED. No updates were required")
            else:
                # If this isn't a no updates required warning, bail out
                logging.error(f"STACK {stack_name} NOT UPDATED. Error occurred")
                logging.error(e)
                return False
        action = 'updated'

    # Stack is in error state
    else:
        logging.info(f"ERROR: Stack not in a complete status. Exiting")
        return False

    # Wait for stack to enter complete status
    while not stack_is_complete(stack_name=stack_name, region=region):
        time.sleep(15)
        stack_status = get_stack_status(stack_name=stack_name, region=region)
        logging.info(f"STACK: {stack_name}, Status: {stack_status} - {datetime.now().strftime('%H:%M:%S')}")

    # Stop the timer
    end = datetime.now()
    duration = fmt_timedelta((end - start))

    # If stack_status is in FAILED state or ROLLBACK, determine reason from events
    if "FAILED" in stack_status or "ROLLBACK" in stack_status:
        logging.warning(f"STACK: {stack_name} not {action} and is in status {stack_status}")
        reason(stack_name=stack_name, region=region)
        return False

    # Print number of resources deployed
    logging.info(f"STACK: {stack_name} {action} {len(get_stack_resources(stack_name=stack_name))} resources "
                 f"in {duration}")

    # Print outputs
    output(stack_name=stack_name, region=region)

    return True


def plan(stack_name, module_name=None, region=default_region, parameter_files=None,
         capabilities=default_capabilities, output='text', delete_change_set=True, **kwargs) -> bool:
    """

    :param string stack_name: stack name
    :param string module_name: optional name of troposphere stack module (if different than stack name)
    :param string region: optional name of region to deploy stack
    :param string parameter_files: optional list of yaml parameter files to include
    :param string capabilities: option list of comma separated capabilities to allow
    :param string output: optional [text|yaml|json], default is text
    :param bool delete_change_set: optional delete change set? Default=False
    :return:
    """
    # Import the troposphere module
    if module_name:
        sys.path.append(os.path.dirname(module_name))
        module_name = os.path.basename(module_name).replace(".py", "")
        stack = __import__(module_name)
    else:
        sys.path.append(os.getcwd())
        stack = __import__(stack_name)

    # Get the yaml template file
    template = stack.get_template()

    # Validate the template to make sure it's valid
    if template_isvalid(template.to_yaml()):
        logging.debug(f"Template body is valid")
    else:
        logging.error(f"template body is invalid. Exiting")
        return False

    # See if the stack is already deployed
    if not stack_is_complete(stack_name=stack_name, region=region):
        # Stack is not deployed yet
        logging.info(f"STACK: {stack_name} is not yet deployed")
        # If the user wants a dump of the template in json or yaml, do that then exit
        if output in ['yaml', 'json']:
            logging.info(f"{output} TEMPLATE START ------------------------")
            if output == "yaml":
                logging.info(template.to_yaml())
            elif output == "json":
                logging.info(template.to_json())
            logging.info(f"{output} TEMPLATE END ------------------------")
            return True
        # If the user wants text output
        elif output in ['text']:
            logging.info(f"STACK: {stack_name} creates {len(template.resources)}")
            logging.info(f"{'#':{2}}) {'action':{8}} {'logical_id':{25}} {'resource_type'}")
            # Go through each resource in the stack
            i = 0
            for resource in template.resources:
                logging.info(
                    f"{i + 1:{2}}) {'Create':{8}} {resource:{25}} {template.resources[resource].resource_type}")
                i += 1
        # invalid output type
        else:
            logging.error(f"invalid output type {output}. Must be text, json or yaml")
            return False

    # Template is already deployed
    else:
        # Generate cfn parameters from input files
        cfn_parameters = create_cfn_parameters(load_parameter_files(parameter_files))
        # split supplied capabilities string
        capabilities = capabilities.split(",")
        # Create a cfn client
        cfn_client = get_cfn_client(region=region)
        # Generate a unique change set name
        change_set_name = 'change-' + datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        # Create a change stack set
        try:
            change_set_id = cfn_client.create_change_set(
                StackName=stack_name,
                TemplateBody=template.to_yaml(),
                Parameters=cfn_parameters,
                Capabilities=capabilities,
                ChangeSetName=change_set_name
            )['Id']
        except Exception as e:
            logging.error(f"unable to creat stack: {stack_name} change set {change_set_name}")
            logging.error(e)
            return False
        # Wait for the status of the change set to be CREATE_COMPLETE
        change_set = cfn_client.describe_change_set(ChangeSetName=change_set_id)
        while change_set['Status'] != "CREATE_COMPLETE":
            if change_set['Status'] == "FAILED":
                # Uh oh, the change set failed
                if "The submitted information didn't contain changes" in change_set['StatusReason']:
                    # If no changes, stack set will error, let the user know
                    logging.info(f"No Changes Detected for Stack: {stack_name}")
                    # Delete the failed stack set
                    try:
                        cfn_client.delete_change_set(ChangeSetName=change_set_id)
                    except Exception as e:
                        logging.error(f"unable to delete stack {stack_name} change set {change_set_name}")
                        logging.error(e)
                        return False
                    return True
                else:
                    # the stack set failed for some other reason than no changes
                    logging.error(f"Stack set creation status failed for reason: {change_set['StatusReason']}. Exiting")
                    # Try to delete the failed stack set
                    try:
                        cfn_client.delete_change_set(ChangeSetName=change_set_id)
                    except Exception as e:
                        logging.error(f"unable to delete stack {stack_name} change set {change_set_name}")
                        logging.error(e)
                    return False
            time.sleep(5)
            change_set = cfn_client.describe_change_set(ChangeSetName=change_set_id)
            logging.debug(f"Change set status: {change_set['Status']}")

        # Ok, stack change set is complete, lets get the results
        logging.info(f"STACK: {stack_name} has {len(change_set['Changes'])} detected changes")
        logging.info(f"{'#':{2}}) {'action':{8}} {'logical_id':{20}} {'resource_id':{25}} "
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
            logging.info(f"{i + 1:{2}}) {action:{8}} {logical_id:{20}} {resource_id:{25}} "
                         f"{resource_type:{30}} {str(scope):{10}} {replacement}")
            # print(json.dumps(change_set['Changes'][i], indent=2))
        # If the user requested to delete change set (default = True)
        if delete_change_set:
            # try deleting the stack change set
            try:
                cfn_client.delete_change_set(ChangeSetName=change_set_id)
            except Exception as e:
                logging.error(e)
                return False
        else:
            logging.info(f"Stack {stack_name}, changeSet: {change_set_name} saved")
        return True


def destroy(stack_name, region=default_region, auto_approve=False, **kwargs):
    """
    Deletes a Cloudformation Stack
    :param string stack_name:
    :param string region:
    :param bool auto_approve:
    :return:
    """
    # Get a cfn client
    cfn_client = get_cfn_client(region=region)
    # Get the stack status
    stack_status = get_stack_status(stack_name=stack_name, region=region)
    # If it is not in a *_COMPLETE state, bail out
    if not stack_is_complete(stack_name=stack_name):
        logging.error(f"STACK: {stack_name} in status {stack_status}. Cant delete now. Exiting")
        return False
    # See how many resources are deployed
    resource_count = len(get_stack_resources(stack_name=stack_name))
    logging.info(f"DELETING STACK: {stack_name} with {resource_count} resources")
    # Get user approval
    if not auto_approve:
        response = input("Are you sure? [yes|no] ")
        if response.lower() != "yes":
            logging.error(f"Exiting")
            return False
    # Start the timer
    start = datetime.now()
    # Delete the stack
    try:
        cfn_client.delete_stack(StackName=stack_name)
    except Exception as e:
        logging.error(e)
        return False
    # Wait for deletion to complete (when stack_status is null)
    while stack_status:
        logging.info(f"STACK: {stack_name}, Status: {stack_status} - {datetime.now().strftime('%H:%M:%S')}")
        time.sleep(15)
        stack_status = get_stack_status(stack_name=stack_name, region=region)
    # Stop the timer
    end = datetime.now()
    duration = fmt_timedelta((end - start))
    logging.info(f"STACK: {stack_name} deleted in {duration}")
    return True


def main():
    stack_help = "name of the cloud formation stack"
    module_help = "name of the python troposphere module"
    region_help = f"comma separated list of AWS capabilities. default: {default_region}"
    capabilities_help = f"comma separated list of AWS capabilities. default: {default_capabilities}"
    approve_help = "auto approve changes"
    param_files_help = "comma separated yaml parameter files"

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title='operation')
    parser.add_argument('-v', '--verbose', action='store_true', help="get DEBUG logging")

    apply_parser = subparsers.add_parser('apply', help="create or update stack")
    apply_parser.add_argument('stack_name', help=stack_help)
    apply_parser.add_argument('-m', '--module_name', help=module_help)
    apply_parser.add_argument('-p', '--parameter_files', help=param_files_help)
    apply_parser.add_argument('-c', '--capabilities', default=default_capabilities, help=capabilities_help)
    apply_parser.add_argument('-r', '--region', default=default_region, help=region_help)
    apply_parser.add_argument('-auto-approve', action='store_true', help=approve_help)
    apply_parser.set_defaults(func=apply)

    plan_parser = subparsers.add_parser('plan', help="view change plan")
    plan_parser.add_argument('stack_name')
    plan_parser.add_argument('-m', '--module_name', help=module_help)
    plan_parser.add_argument('-p', '--parameter_files', help=param_files_help)
    plan_parser.add_argument('-c', '--capabilities', default=default_capabilities, help=capabilities_help)
    plan_parser.add_argument('-r', '--region', default=default_region, help=region_help)
    plan_parser.set_defaults(func=plan)

    destroy_parser = subparsers.add_parser('destroy', help="remove stack")
    destroy_parser.set_defaults(func=destroy)
    destroy_parser.add_argument('stack_name')
    destroy_parser.add_argument('-auto-approve', action='store_true', help=approve_help)
    destroy_parser.add_argument('-r', '--region', default=default_region, help=region_help)
    destroy_parser.set_defaults(func=destroy)

    list_parser = subparsers.add_parser('list', help="list stacks")
    list_parser.add_argument('-r', '--region', default=default_region, help=region_help)
    list_parser.set_defaults(func=list_stacks)

    output_parser = subparsers.add_parser('output')
    output_parser.set_defaults(func=output)
    output_parser.add_argument('stack_name')
    output_parser.add_argument('-r', '--region', default=default_region, help=region_help)
    output_parser.set_defaults(func=output)

    parameters_parser = subparsers.add_parser('parameters', help="list parameters for a stack")
    parameters_parser.set_defaults(func=parameters)
    parameters_parser.add_argument('stack_name')
    parameters_parser.add_argument('-r', '--region', default=default_region, help=region_help)
    parameters_parser.set_defaults(func=parameters)

    reason_parser = subparsers.add_parser('reason', help="least reasons for failed stack")
    reason_parser.set_defaults(func=reason)
    reason_parser.add_argument('stack_name')
    reason_parser.add_argument('-r', '--region', default=default_region, help=region_help)
    reason_parser.set_defaults(func=reason)

    args = parser.parse_args()
    if not hasattr(args, 'func'):
        parser.print_help()
        sys.exit(0)

    logging.getLogger().setLevel('INFO')
    if args.verbose:
        logging.getLogger().setLevel('DEBUG')
    args.func(**vars(args))


if __name__ == "__main__":
    main()
