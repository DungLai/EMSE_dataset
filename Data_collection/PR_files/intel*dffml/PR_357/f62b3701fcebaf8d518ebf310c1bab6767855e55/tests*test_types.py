from dffml.df.base import op
from dffml.df.types import DataFlow, Input, Definition
from dffml.operation.output import GetSingle
from dffml.util.asynctestcase import AsyncTestCase
from dffml.df.memory import MemoryOrchestrator
from dffml.operation.mapping import MAPPING
from dffml.df.exceptions import InputValidationError


def pie_validation(x):
    if x == 3.14:
        return x
    raise InputValidationError()


Pie = Definition(name="pie", primitive="float", validate=pie_validation)
Radius = Definition(name="radius", primitive="float")
Area = Definition(name="area", primitive="float")
ShapeName = Definition(
    name="shape_name", primitive="str", validate=lambda x: x.upper()
)


@op(
    inputs={"name": ShapeName, "radius": Radius, "pie": Pie},
    outputs={"shape": MAPPING},
)
async def get_circle(name: str, radius: float, pie: float):
    return {
        "shape": {
            "name": name,
            "radius": radius,
            "area": pie * radius * radius,
        }
    }


class TestDefintion(AsyncTestCase):
    async def setUp(self):
        self.dataflow = DataFlow(
            operations={
                "get_circle": get_circle.op,
                "get_single": GetSingle.imp.op,
            },
            seed=[
                Input(
                    value=[get_circle.op.outputs["shape"].name],
                    definition=GetSingle.op.inputs["spec"],
                )
            ],
            implementations={"get_circle": get_circle.imp},
        )

    async def test_validate(self):
        test_inputs = {
            "area": [
                Input(value="unitcircle", definition=ShapeName),
                Input(value=1, definition=Radius),
                Input(value=3.14, definition=Pie),
            ]
        }
        async with MemoryOrchestrator.withconfig({}) as orchestrator:
            async with orchestrator(self.dataflow) as octx:
                async for ctx_str, results in octx.run(test_inputs):
                    self.assertIn("mapping", results)
                    results = results["mapping"]
                    self.assertEqual(results["name"], "UNITCIRCLE")
                    self.assertEqual(results["area"], 3.14)
                    self.assertEqual(results["radius"], 1)

    async def test_0_validation_error(self):
        with self.assertRaises(InputValidationError):
            test_inputs = {
                "area": [
                    Input(value="unitcircle", definition=ShapeName),
                    Input(value=1, definition=Radius),
                    Input(
                        value=4, definition=Pie
                    ),  # this should raise validation eror
                ]
            }
            pass
