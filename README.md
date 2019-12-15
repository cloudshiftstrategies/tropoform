# Tropoform

Tropoform is a tool that provides a [terraform](https://terraform.io) like interface for deploying 
standalone AWS Cloud Formation stacks or stacks created 
by [troposphere](https://github.com/cloudtools/troposphere). Tropoform provides plan, apply, list, 
output & destroy operations on cloudformation stacks.

### Requirements
* Python3.6+

### Installation
To install the latest version of tropoform
```
pip install tropoform --user --upgrade
```

For development projects, it is advised to install in a python
[virtual environment](https://virtualenv.pypa.io/en/latest/)


Or you can install from source https://github.com/cloudshiftstrategies/tropoform

### Usage

use `tropoform -h` for help
```
$ tropform -h
usage: tropoform [-h] [-v]
                    {apply,plan,destroy,list,output,parameters,reason} ...

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         get DEBUG logging

operation:
  {apply,plan,destroy,list,output,parameters,reason}
    apply               create or update stack
    plan                view change plan
    destroy             remove stack
    list                list stacks
    output              view stack outputs
    parameters          list parameters used in a stack
    reason              list reasons for failed stack
```

see detailed usage help for an operation  `tropoform apply -h`
```
usage: tropoform.py apply [-h] (-m MODULE_NAME | -t TEMPLATE_FILE)
                          [-p PARAMETER_FILES] [-c CAPABILITIES] [-r REGION]
                          [--auto_approve]
                          stack_name

positional arguments:
  stack_name            The name of the cloud formation stack on which to
                        perform operation. If a module exists in the current
                        working directory that matches the stack_name and has
                        a get_template() method, module_name is not required

optional arguments:
  -h, --help            show this help message and exit
  -m MODULE_NAME, --module_name MODULE_NAME
                        The name of the python troposphere module that will
                        create the template. Module must have a get_template()
                        method that returns a valid troposphere.Template
                        object
  -t TEMPLATE_FILE, --template_file TEMPLATE_FILE
                        The path to a cloud formation template file.
  -p PARAMETER_FILES, --parameter_files PARAMETER_FILES
                        Comma separated yaml parameter files that will be
                        passed to cloud formation as parameters
  -c CAPABILITIES, --capabilities CAPABILITIES
                        Comma separated list of AWS capabilities. default:
                        CAPABILITY_NAMED_IAM
  -r REGION, --region REGION
                        The name of the AWS region to perform operations.
                        default is the env variable: AWS_DEFAULT_REGION
  --auto_approve        If set, user will not be prompted to approve changes.
                        default=False
```

### Usage Example

1. Create a cloud formation template using yaml or json formation

   OR

   Create a python module (script) using [troposphere](https://github.com/cloudtools/troposphere) 
   that has at least one method called get_template() which returns the un-rendered troposphere.
   Template() object. 

    In the `example.py` script below, we create an IAM user inside the function get_template() and return
    the completed template object
    
    example.py
    ```python
    from troposphere import Template
    from troposphere import iam

    def get_template():
        template = Template()
        template.add_resource(
            iam.User(
                "testIamUser",
                UserName="tropoform_test_user"
            )
        )
        return template
    ```

2. Configure your AWS credentials
   https://docs.aws.amazon.com/sdk-for-java/v1/developer-guide/setup-credentials.html
   so that you can make API / CLI calls.
    * Test your credentials with an awscli command like `aws s3 ls`
    * or you can test the boto3 python api `python3 -c "import boto3; client = boto3.client('s3'); print(client.list_buckets())"`
    
3. Run a `tropoform plan` on the stack and see that one IAM User resource will be created

    Using a cloud formation template
    ```
    $ tropoform plan myStack -t example_cfn_template.yaml
    STACK: myStack is not yet deployed
    STACK: myStack creates 1
    # ) action   logical_id                resource_type
     1) Create   testIamUser               AWS::IAM::User
    ```

    Or using a troposphere module
    ```
    $ tropoform plan myStack -m example.py
    STACK: myStack is not yet deployed
    STACK: myStack creates 1
    # ) action   logical_id                resource_type
     1) Create   testIamUser               AWS::IAM::User
    ```
    
4. Use `tropofrom apply` (create) the stack

    Using a cloud formation template
    ```
    $ tropoform apply myStack -t example_template.json
    STACK: myStack, Current Status: None
    CREATING Stack: myStack with 1 resources
    Are you sure? [yes|no] yes
    STACK: myStack, Status: CREATE_IN_PROGRESS - 16:36:10
    STACK: myStack, Status: CREATE_IN_PROGRESS - 16:36:25
    STACK: myStack, Status: CREATE_COMPLETE - 16:36:41
    STACK: myStack deployed 1 resources in 00:00:48
    STACK OUTPUTS:
    ```
    
    Or using a troposphere module
    ```
    $ tropoform apply myStack -m example.py
    STACK: myStack, Current Status: None
    CREATING Stack: myStack with 1 resources
    Are you sure? [yes|no] yes
    STACK: myStack, Status: CREATE_IN_PROGRESS - 16:36:10
    STACK: myStack, Status: CREATE_IN_PROGRESS - 16:36:25
    STACK: myStack, Status: CREATE_COMPLETE - 16:36:41
    STACK: myStack deployed 1 resources in 00:00:48
    STACK OUTPUTS:
    ```
   
5. Use `tropoform list` to see stacks that are applied. Notice it is in status CREATE_COMPLETE
    ```
    $ tropoform list
    stack_name           stack_status         drift_status         stack_description
    myStack              CREATE_COMPLETE      NOT_CHECKED  
    ```

6. Update the example.template and add another resource

    example.py
    ```python
    from troposphere import Template
    from troposphere import iam

    def get_template():
        template = Template()
        template.add_resource(
            iam.User(
                "testIamUser",
                UserName="tropoform_test_user"
            )
        )
        template.add_resource(
            iam.User(
                "testIamUser2",
                UserName="tropoform_test_user2"
            )
        )
        return template
    ```
    
    and run a new `tropoform plan`. Notice that it will add one new resource.
    ```
    $ tropoform plan myStack -m example.py
    STACK: myStack has 1 detected changes
    # ) action   logical_id           resource_id               resource_type                  scope      Replace?
     1) Add      testIamUser2                                   AWS::IAM::User                 [] 
    ```

7. `tropoform apply` the changes and then use a `tropoform list` to verify
    ```
    $ tropoform apply myStack -m example.py
    STACK: myStack, Current Status: CREATE_COMPLETE
    UPDATING Stack: myStack
    Are you sure? [yes|no] yes
    STACK: myStack, Status: UPDATE_IN_PROGRESS - 16:42:38
    STACK: myStack, Status: UPDATE_IN_PROGRESS - 16:42:54
    STACK: myStack, Status: UPDATE_COMPLETE - 16:43:09
    STACK: myStack updated 2 resources in 00:00:48
    STACK OUTPUTS:
    
    $ tropoform list
    stack_name           stack_status         drift_status         stack_description
    myStack              UPDATE_COMPLETE      NOT_CHECKED   
    ```
   
8. `destroy` the stack when you are done with it
    ```
    $ tropoform destroy myStack
    DELETING STACK: myStack with 2 resources
    Are you sure? [yes|no] yes
    STACK: myStack, Status: UPDATE_COMPLETE - 16:44:37
    STACK: myStack deleted in 00:00:15

    ```
       
#### Additional features 
1. Parameter files

    Often cloudformation templates will require parameters so that they can be easily
    reusable. You can create yaml based files with key: value pairs and add them as 
    arguments to the `tropoform plan` and `tropoform apply` operations
    
    example_parms1.yaml
    ```yaml
    Parm1: Parameter 1
    Parm2: "2"
    ```
    
    example_parms2.yaml
    ```yaml
    Parm3: Parameter 3
    Parm4: "4"
    ```
    
    Using the parameter files in an apply
    ```
    $ tropoform apply myStack -m example.py -p example_parms1.yaml,example_parms2.yaml

    ```
    
2. Capabilities

    Cloud formation stacks may require acknowledgement that it will create resources of
    certain types. The most common is CAPABILITIES_NAMED_IAM which authorizes cloud formation
    to create IAM resources. This is included by default in tropoform. But if your stack
    requires additional capabilities, you can include them with the `-c` argument. See more
    information about capabilities in this documentation:
    https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_CreateStack.html
    
    Using additional capabilities in an apply
    ```
    $ tropoform apply myStack -m example.py -c CAPABILITY_NAMED_IAM,CAPABILITY_AUTO_EXPAND

    ```
    
3. Regions

    By default, troposphere will read the environment variable AWS_DEFAULT_REGION to determine
    where to manage stacks. But if you want to specify a different region for an operation
    pass the '-r' or '--region' argument
    
    Specifying a region in a list command
    ```
    $ tropoform list -r us-east-2

    ```
    
4. Stack Names and Module Name

    If the name you want to specify for your cloudformation stack is in the current
    working directory and has the same name as the troposphere script, then you can omit
    the module_name parameter
    
    Example of creating a cloud formation stack called "example" when "example.py" troposphere
    script exists in the current working directory
    ```
    $ tropoform apply example

    ```
    
    Example of creating a cloud formation stack called "myStack" when "example.py" troposphere
    script exists in some filesystem location
    ```
    $ tropoform apply myStack -m ../scripts/example.py

    ```
    
5. Auto Approve

    Sometimes when running tropoform in automated scripts, you dont want to be prompted to say
    yes to confirm the `apply` or `destroy` operation
    
    Example `--auto_approve`
    ```
    $ tropoform apply example --auto_approve
    ```
    
6. Reason for failures

    If your cloudformation stack fails to apply for some reason, the cloudformation event(s)
    that caused the will be printed.
    
    In the example below, we tried to attach a ManagedIamPolicy that is intentionally misspelled
    ```
    $ tropoform apply myStack -m example.py
    STACK: myStack, Current Status: None
    CREATING Stack: myStack with 1 resources
    Are you sure? [yes|no] yes
    STACK: myStack, Status: CREATE_IN_PROGRESS - 17:32:22
    STACK: myStack, Status: CREATE_IN_PROGRESS - 17:32:38
    STACK: myStack, Status: ROLLBACK_COMPLETE - 17:32:54
    STACK: myStack not deployed and is in status ROLLBACK_COMPLETE
    STACK myStack create/update FAILED due to the following stack events:
    UTC time   ResourceStatus  ResourceType                        LogicalResourceId              ResourceStatusReason
    22:32:47   CREATE_FAILED   AWS::IAM::User                      testIamUser                    Policy arn:aws:iam::aws:policy/AdministratorAcces does not exist or is not attachable. 
    ```
    
    You can use the `tropoform reason` operation to look up the status of a failed stack
    ```
    $ tropoform reason myStack
    STACK myStack create/update FAILED due to the following stack events:
    UTC time   ResourceStatus  ResourceType                        LogicalResourceId              ResourceStatusReason
    22:32:47   CREATE_FAILED   AWS::IAM::User                      testIamUser                    Policy arn:aws:iam::aws:policy/AdministratorAcces does not exist or is not attachable.
    ```
    
7. Parameters

    If your stack was deployed with parameters, you can check those paramaters with the 
    `tropoform parameters` operation
    ``` 
    $ tropoform parameters myStack
    STACK: myStack Parameters: 
    Parm1                = value1 
    ```
    
8. Outputs

    If your stack specifies Output parameters, when the stack is done deploying, the outputs
    will be printed.
    ``` 
    $ tropoform apply myStack -m example.py --auto_approve
    STACK: myStack, Current Status: None
    CREATING Stack: myStack with 1 resources
    STACK: myStack, Status: CREATE_IN_PROGRESS - 17:40:44
    STACK: myStack, Status: CREATE_IN_PROGRESS - 17:40:59
    STACK: myStack, Status: CREATE_COMPLETE - 17:41:15
    STACK: myStack deployed 1 resources in 00:00:48
    STACK OUTPUTS:
    userArn              = arn:aws:iam::357849880876:user/tropoform_test_user
    ```
    
    If you want to access those outputs later, you can run `tropoform output`
    ``` 
    $ tropoform output myStack
    STACK OUTPUTS:
    userArn              = arn:aws:iam::357849880876:user/tropoform_test_user
    ```


### Contributions welcome!
Open issues and send pull requests via the github repo https://github.com/cloudshiftstrategies/tropoform

### Build Instructions

```
# Clone the repo
git clone https://github.com/cloudshiftstrategies/tropoform
cd tropoform

# Setup virtual environment
pipenv shell
pipenv install --dev

# Edit code. Main script is in: tropoform/tropoform.py

# Test (requires current AWS credentials in an account where test stack can create/delete
python3 -m unittest test

# Create new version
 # edit __version__ in tropoform/tropoform.py
 # edit version in setup.py
 
# Build
python3 setup.py sdist bdist_wheel

# Test local install
python3 setup.py install

# tag release
git add .
git commit -m "xxx"
gitchangelog > Changelog.rst 
# update version in Changelog.rst
git commit -am "updated changelog"
git tag X.Y.Z -m "xxx"
git push && git push --tags

# Publish to PyPy
twine upload --repository test dist/tropoform-X.Y.Z*
twine upload --repository pypi dist/tropoform-X.Y.Z*
```
