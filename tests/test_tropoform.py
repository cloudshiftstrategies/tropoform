import unittest
import warnings
import datetime
import os
import sys
from tropoform import tropoform


class TestHelpers(unittest.TestCase):

    def setUp(self) -> None:
        self.region = 'us-east-1'
        if 'AWS_DEFAULT_REGION' in os.environ:
            self.region = os.environ['AWS_DEFAULT_REGION']

    def test_create_cfn_parameters(self):
        # def _create_cfn_parameters(parameters) -> list:
        data = {'key1': 'value1', 'key2': 2}
        desired = [{'ParameterKey': 'key1', 'ParameterValue': 'value1'}, {'ParameterKey': 'key2', 'ParameterValue': 2}]
        result = tropoform._create_cfn_parameters(parameters_dict=data)
        self.assertEqual(result, desired)

    def test_get_cfn_client(self):
        # def _get_cfn_client(region=default_region) -> boto3.client:
        cfn_client = tropoform._get_cfn_client(region=self.region)
        self.assertIsNot(cfn_client, False)

    def test_load_parameter_files(self):
        # def _load_parameter_files(parameter_files):
        result = tropoform._load_parameter_files(
            parameter_files='./tests/fixtures/sample.parms.yaml,./tests/fixtures/sample.parms2.yaml')
        desired = {'Parm1': 'Parameter 1', 'Parm2': "2", 'Parm3': 'Parameter 3', 'Parm4': "4"}
        self.assertEqual(result, desired)

    def test_fmt_timedelta(self):
        # def _fmt_timedelta(time_delta):
        result = tropoform._fmt_timedelta(datetime.timedelta(seconds=60))
        self.assertEqual(result, '00:01:00')


class TestCfn(unittest.TestCase):
    stack_name = None
    module_name = None
    template = None
    tropo_module = None
    param_files = None
    region = None

    @classmethod
    def setUpClass(TestCfn) -> None:
        TestCfn.region = 'us-east-1'
        if 'AWS_DEFAULT_REGION' in os.environ:
            TestCfn.region = os.environ['AWS_DEFAULT_REGION']
        # disable warnings the request module creates in unittest
        warnings.simplefilter("ignore", ResourceWarning)
        # Use the stack name:
        TestCfn.stack_name = 'sampleTropoformStack'
        # Use the module_name in remote path
        TestCfn.module_name = './tests/fixtures/sample_tropo_module.py'
        # Load the sample troposphere module
        sys.path.append(os.path.dirname(TestCfn.module_name))
        tropo_module = __import__(os.path.basename(TestCfn.module_name.replace('.py', '')))
        # Generate the template body from the sample tropo module
        TestCfn.template = tropo_module.get_template()
        # Parameter files
        TestCfn.param_files = './tests/fixtures/sample.parms.yaml,./tests/fixtures/sample.parms2.yaml'
        # Create a sample stack that we can test
        result = tropoform.apply(stack_name=TestCfn.stack_name,
                                 module_name=TestCfn.module_name,
                                 parameter_files=TestCfn.param_files,
                                 region=TestCfn.region,
                                 auto_approve=True)
        if not result:
            raise Exception("Unable to create sample stack")

    @classmethod
    def tearDownClass(TestCfn) -> None:
        # destroy sample stack that we can test
        tropoform.destroy(stack_name=TestCfn.stack_name,
                          region=TestCfn.region,
                          auto_approve=True)

    def test_get_stack_status(self):
        # def _get_stack_status(stack_name, region=default_region) -> str:
        result = tropoform._get_stack_status(stack_name=TestCfn.stack_name, region=TestCfn.region)
        self.assertEqual('CREATE_COMPLETE', result)

    def test_stack_is_complete(self):
        # def _stack_is_complete(stack_name, region=default_region) -> bool:
        result = tropoform._stack_is_complete(stack_name=TestCfn.stack_name, region=TestCfn.region)
        self.assertTrue(result)

    def test_get_stack_outputs(self):
        # def _get_stack_outputs(stack_name, region=default_region) -> list:
        result = tropoform._get_stack_outputs(stack_name=TestCfn.stack_name, region=TestCfn.region)
        self.assertIsInstance(result, list)

    def test_get_stack_resources(self):
        # def _get_stack_resources(stack_name, region=default_region) -> list:
        result = tropoform._get_stack_resources(stack_name=TestCfn.stack_name, region=TestCfn.region)
        self.assertIsInstance(result, list)

    def test_template_isvalid(self):
        # def _template_isvalid(template_body, region=default_region) -> bool:
        result = tropoform._template_isvalid(template_body=TestCfn.template.to_yaml(), region=TestCfn.region)
        self.assertTrue(result)

    def test_output(self):
        # def output(stack_name, region=default_region) -> bool:
        with self.assertLogs(level='INFO') as logs:
            result = tropoform.output(stack_name=TestCfn.stack_name, region=TestCfn.region)
        self.assertTrue(result)
        self.assertIn('INFO:root:output               = tropoform_test_user', logs.output)

    def test_list_stacks(self):
        # def list_stacks(stack_name=None, region=default_region) -> bool:
        with self.assertLogs(level='INFO') as logs:
            result = tropoform.list_stacks(stack_name=TestCfn.stack_name, region=TestCfn.region)
        self.assertTrue(result)
        self.assertIn('INFO:root:sampleTropoformStack CREATE_COMPLETE      NOT_CHECKED          ', logs.output)
        result = tropoform.list_stacks()
        self.assertTrue(result)

    def test_get_failed_stack_events(self):
        # def _get_failed_stack_events(stack_name, region=default_region) -> list:
        result = tropoform._get_failed_stack_events(stack_name=TestCfn.stack_name, region=TestCfn.region)
        self.assertIsInstance(result, list)

    def test_parameters(self):
        # def parameters(stack_name, region=default_region) -> bool:
        with self.assertLogs(level='INFO') as logs:
            result = tropoform.parameters(stack_name=TestCfn.stack_name, region=TestCfn.region)
        self.assertTrue(result)
        self.assertIn('INFO:root:Parm1                = Parameter 1 ', logs.output)

    def test_reason(self):
        # def reason(stack_name, region=default_region) -> bool:
        with self.assertLogs(level='INFO') as logs:
            result = tropoform.reason(stack_name=TestCfn.stack_name, region=TestCfn.region)
        self.assertTrue(result)
        self.assertIn('INFO:root:STACK sampleTropoformStack create/update FAILED due to the following stack events:',
                      logs.output)

    def test_apply(self):
        # def apply(stack_name, module_name=None, parameter_files=None, capabilities=default_capabilities,
        # tested in class setup
        pass

    def test_plan(self):
        # def plan(stack_name, module_name=None, region=default_region, parameter_files=None,
        with self.assertLogs(level='INFO') as logs:
            result = tropoform.plan(stack_name=TestCfn.stack_name,
                                    module_name=TestCfn.module_name,
                                    parameter_files=TestCfn.param_files,
                                    region=TestCfn.region)
        self.assertTrue(result)
        self.assertIn('INFO:root:No Changes Detected for Stack: sampleTropoformStack', logs.output)

    def test_destroy(self):
        # def destroy(stack_name, region=default_region, auto_approve=False):
        # tested in class setup
        pass


# Cant make this work with v0.2.0 tropoform._parse_args.function TODO fix this
"""
class TestParser(unittest.TestCase):

    stack_name = None
    module_name = None
    template = None
    tropo_module = None
    param_files = None
    region = None
    capabilities = None

    @classmethod
    def setUpClass(TestParser) -> None:
        TestParser.region = 'us-east-1'
        if 'AWS_DEFAULT_REGION' in os.environ:
            TestParser.region = os.environ['AWS_DEFAULT_REGION']
        # Use the stack name
        TestParser.stack_name = 'sampleTropoformStack'
        # Use the module_name in remote path
        TestParser.module_name = './tests/sample_tropo_module.py'
        TestParser.capabilities = 'CAPABILITY_NAMED_IAM'

    # CANNOT get this test to run.. TODO: fix this
    #def test_version(self):
    #    args = ['--version']
    #    parser = tropoform._parse_args(args)
    #    self.assertIsInstance(parser, str)

    def test_list_parameters_reason(self):
        parameters = ['func', 'region', 'stack_name', 'verbose']
        funcs = ['list', 'parameters', 'reason']

        for func in funcs:
            args = [func]
            if func == 'list':
                # Test list without a stack_name (others require a stack name)
                parser, pargs = tropoform._parse_args(args)
                for parameter in parameters:
                    self.assertIn(parameter, pargs)

            args.append(TestParser.stack_name)
            parser, pargs = tropoform._parse_args(args)
            for parameter in parameters:
                self.assertIn(parameter, pargs)

            args.insert(0, '-v')
            parser, pargs = tropoform._parse_args(args)
            for parameter in parameters:
                self.assertIn(parameter, pargs)

            args.extend(['-r', TestParser.region])
            parser, pargs = tropoform._parse_args(args)
            for parameter in parameters:
                self.assertIn(parameter, pargs)

    def test_output_parameters(self):
        parameters = ['func', 'region', 'stack_name', 'verbose']
        funcs = ['output', 'parameters']
        for func in funcs:
            args = [func, TestParser.stack_name]
            parser, pargs = tropoform._parse_args(args)
            for parameter in parameters:
                self.assertIn(parameter, pargs)

            args.insert(0, '-v')
            parser, pargs = tropoform._parse_args(args)
            for parameter in parameters:
                self.assertIn(parameter, pargs)

            args.extend(['-r', TestParser.region])
            parser, pargs = tropoform._parse_args(args)
            for parameter in parameters:
                self.assertIn(parameter, pargs)

    def test_plan_apply(self):
        parameters = ['func', 'region', 'stack_name', 'verbose', 'capabilities']
        funcs = ['plan', 'apply']

        for func in funcs:
            args = [func, TestParser.stack_name]
            parser, pargs = tropoform._parse_args(args)
            for parameter in parameters:
                self.assertIn(parameter, pargs)

            args.insert(0, '-v')
            parser, pargs = tropoform._parse_args(args)
            for parameter in parameters:
                self.assertIn(parameter, pargs)

            args.extend(['-r', TestParser.region])
            parser, pargs = tropoform._parse_args(args)
            for parameter in parameters:
                self.assertIn(parameter, pargs)

            args.extend(['-m', TestParser.module_name])
            parser, pargs = tropoform._parse_args(args)
            for parameter in parameters:
                self.assertIn(parameter, pargs)

            args.extend(['-c', TestParser.capabilities])
            parser, pargs = tropoform._parse_args(args)
            for parameter in parameters:
                self.assertIn(parameter, pargs)

            if func == 'apply':
                args.extend(['--auto_approve'])
                parser, pargs = tropoform._parse_args(args)
                for parameter in parameters:
                    self.assertIn(parameter, pargs)

    def test_destroy_apply(self):
        parameters = ['func', 'region', 'stack_name', 'verbose']
        func = 'destroy'

        args = [func, TestParser.stack_name]
        parser, pargs = tropoform._parse_args(args)
        for parameter in parameters:
            self.assertIn(parameter, pargs)

        args.insert(0, '-v')
        parser, pargs = tropoform._parse_args(args)
        for parameter in parameters:
            self.assertIn(parameter, pargs)

        args.append('--auto_approve')
        parser, pargs = tropoform._parse_args(args)
        for parameter in parameters:
            self.assertIn(parameter, pargs)
"""
