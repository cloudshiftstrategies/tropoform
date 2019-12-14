from troposphere import Template
from troposphere import iam, Output, Parameter, Ref


def get_template():
    template = Template()
    template.add_parameter(
        Parameter(
            "Parm1",
            Type="String"
        )
    )
    template.add_parameter(
        Parameter(
            "Parm2",
            Type="Number"
        )
    )
    template.add_parameter(
        Parameter(
            "Parm3",
            Type="String"
        )
    )
    template.add_parameter(
        Parameter(
            "Parm4",
            Type="String"
        )
    )
    test_user = template.add_resource(
        iam.User(
            "testIamUser",
            UserName="tropoform_test_user"
        )
    )
    template.add_output(
        Output(
            "output",
            Value=Ref(test_user)
        )

    )

    return template


if __name__ == "__main__":
    print(get_template().to_json())
