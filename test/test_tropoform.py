import unittest
from tropoform import tropoform
import logging
import warnings
import datetime
import os
import sys


class TestHelpers(unittest.TestCase):

    def test_create_cfn_parameters(self):
        # def create_cfn_parameters(parameters) -> list:
        data = {'key1': 'value1', 'key2': 2}
        desired = [{'ParameterKey': 'key1', 'ParameterValue': 'value1'}, {'ParameterKey': 'key2', 'ParameterValue': 2}]
        result = tropoform.create_cfn_parameters(data)
        self.assertEqual(result, desired)

    def test_get_cfn_client(self):
        # def get_cfn_client(region=default_region) -> boto3.client:
        cfn_client = tropoform.get_cfn_client()
        self.assertIsNot(cfn_client, False)

    def test_load_parameter_files(self):
        # def load_parameter_files(parameter_files):
        result = tropoform.load_parameter_files('./test/sample.parms.yaml,./test/sample.parms2.yaml')
        desired = {'Parm1': 'Parameter 1', 'Parm2': "2", 'Parm3': 'Parameter 3', 'Parm4': "4"}
        self.assertEqual(result, desired)

    def test_fmt_timedelta(self):
        # def fmt_timedelta(time_delta):
        result = tropoform.fmt_timedelta(datetime.timedelta(seconds=60))
        self.assertEqual(result, '00:01:00')


class TestCfn(unittest.TestCase):

    stack_name = None
    module_name = None
    template = None
    tropo_module = None
    param_files = None

    @classmethod
    def setUpClass(TestCfn) -> None:
        # disable warnings the request module creates in unittest
        warnings.simplefilter("ignore", ResourceWarning)
        # Use the stack name:
        TestCfn.stack_name = 'sampleTropoformStack'
        # Use the module_name in remote path
        TestCfn.module_name = './test/sample_tropo_module.py'
        # Load the sample troposphere module
        sys.path.append(os.path.dirname(TestCfn.module_name))
        tropo_module = __import__(os.path.basename(TestCfn.module_name.replace('.py', '')))
        # Generate the template body from the sample tropo module
        TestCfn.template = tropo_module.get_template()
        # Parameter files
        TestCfn.param_files = './test/sample.parms.yaml,./test/sample.parms2.yaml'
        # Create a sample stack that we can test
        tropoform.apply(stack_name=TestCfn.stack_name,
                        module_name=TestCfn.module_name,
                        parameter_files=TestCfn.param_files,
                        auto_approve=True)

    @classmethod
    def tearDownClass(TestCfn) -> None:
        # destroy sample stack that we can test
        tropoform.destroy(stack_name=TestCfn.stack_name, auto_approve=True)

    def test_get_stack_status(self):
        # def get_stack_status(stack_name, region=default_region) -> str:
        result = tropoform.get_stack_status(stack_name=TestCfn.stack_name)
        self.assertEqual(result, 'CREATE_COMPLETE')

    def test_stack_is_complete(self):
        # def stack_is_complete(stack_name, region=default_region) -> bool:
        result = tropoform.stack_is_complete(stack_name=TestCfn.stack_name)
        self.assertTrue(result)

    def test_get_stack_outputs(self):
        # def get_stack_outputs(stack_name, region=default_region) -> list:
        result = tropoform.get_stack_outputs(stack_name=TestCfn.stack_name)
        self.assertIsInstance(result, list)

    def test_get_stack_resources(self):
        # def get_stack_resources(stack_name, region=default_region) -> list:
        result = tropoform.get_stack_resources(stack_name=TestCfn.stack_name)
        self.assertIsInstance(result, list)

    def test_template_isvalid(self):
        # def template_isvalid(template_body, region=default_region) -> bool:
        result = tropoform.template_isvalid(template_body=TestCfn.template.to_yaml())
        self.assertTrue(result)

    def test_output(self):
        # def output(stack_name, region=default_region) -> bool:
        with self.assertLogs(level='INFO') as logs:
            result = tropoform.output(stack_name=TestCfn.stack_name)
        self.assertTrue(result)
        self.assertIn('INFO:root:output               = tropoform_test_user', logs.output)

    def test_list_stacks(self):
        # def list_stacks(stack_name=None, region=default_region) -> bool:
        with self.assertLogs(level='INFO') as logs:
            result = tropoform.list_stacks(stack_name=TestCfn.stack_name)
        self.assertTrue(result)
        self.assertIn('INFO:root:sampleTropoformStack CREATE_COMPLETE      NOT_CHECKED          ', logs.output)
        result = tropoform.list_stacks()
        self.assertTrue(result)

    def test_get_failed_stack_events(self):
        # def get_failed_stack_events(stack_name, region=default_region) -> list:
        result = tropoform.get_failed_stack_events(stack_name=TestCfn.stack_name)
        self.assertIsInstance(result, list)

    def test_parameters(self):
        # def parameters(stack_name, region=default_region) -> bool:
        with self.assertLogs(level='INFO') as logs:
            result = tropoform.parameters(stack_name=TestCfn.stack_name)
        self.assertTrue(result)
        self.assertIn('INFO:root:Parm1                = Parameter 1 ', logs.output)

    def test_reason(self):
        # def reason(stack_name, region=default_region) -> bool:
        with self.assertLogs(level='INFO') as logs:
            result = tropoform.reason(stack_name=TestCfn.stack_name)
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
                                    parameter_files=TestCfn.param_files)
        self.assertTrue(result)
        self.assertIn('INFO:root:No Changes Detected for Stack: sampleTropoformStack', logs.output)

    def test_destroy(self):
        # def destroy(stack_name, region=default_region, auto_approve=False):
        # tested in class setup
        pass
