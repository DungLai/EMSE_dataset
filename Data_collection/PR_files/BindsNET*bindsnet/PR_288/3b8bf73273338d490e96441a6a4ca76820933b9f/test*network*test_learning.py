import torch

from bindsnet.network import Network
from bindsnet.network.nodes import Input, LIFNodes, SRM0Nodes
from bindsnet.network.topology import Connection, Conv2dConnection
from bindsnet.learning import (
    Hebbian,
    PostPre,
    WeightDependentPostPre,
    MSTDP,
    MSTDPET,
    Rmax,
)


class TestLearningRules:
    """
    Tests all stable learning rules for compatible ``Connection`` types.
    """

    def test_hebbian(self):
        # Connection test
        network = Network(dt=1.0)
        network.add_layer(Input(n=100, traces=True), name="input")
        network.add_layer(LIFNodes(n=100, traces=True), name="output")
        network.add_connection(
            Connection(
                source=network.layers["input"],
                target=network.layers["output"],
                nu=1e-2,
                update_rule=Hebbian,
            ),
            source="input",
            target="output",
        )
        network.run(
            inpts={"input": torch.bernoulli(torch.rand(250, 100)).byte()}, time=250
        )

        # Conv2dConnection test
        network = Network(dt=1.0)
        network.add_layer(Input(shape=[1, 10, 10], traces=True), name="input")
        network.add_layer(LIFNodes(shape=[32, 8, 8], traces=True), name="output")
        network.add_connection(
            Conv2dConnection(
                source=network.layers["input"],
                target=network.layers["output"],
                kernel_size=3,
                stride=1,
                nu=1e-2,
                update_rule=Hebbian,
            ),
            source="input",
            target="output",
        )
        network.run(
            inpts={"input": torch.bernoulli(torch.rand(1, 250, 1, 10, 10)).byte()},
            time=250,
        )

    def test_post_pre(self):
        # Connection test
        network = Network(dt=1.0)
        network.add_layer(Input(n=100, traces=True), name="input")
        network.add_layer(LIFNodes(n=100, traces=True), name="output")
        network.add_connection(
            Connection(
                source=network.layers["input"],
                target=network.layers["output"],
                nu=1e-2,
                update_rule=PostPre,
            ),
            source="input",
            target="output",
        )
        network.run(
            inpts={"input": torch.bernoulli(torch.rand(250, 100)).byte()}, time=250
        )

        # Conv2dConnection test
        network = Network(dt=1.0)
        network.add_layer(Input(shape=[1, 10, 10], traces=True), name="input")
        network.add_layer(LIFNodes(shape=[32, 8, 8], traces=True), name="output")
        network.add_connection(
            Conv2dConnection(
                source=network.layers["input"],
                target=network.layers["output"],
                kernel_size=3,
                stride=1,
                nu=1e-2,
                update_rule=PostPre,
            ),
            source="input",
            target="output",
        )
        network.run(
            inpts={"input": torch.bernoulli(torch.rand(1, 250, 1, 10, 10)).byte()},
            time=250,
        )

    def test_weight_dependent_post_pre(self):
        # Connection test
        network = Network(dt=1.0)
        network.add_layer(Input(n=100, traces=True), name="input")
        network.add_layer(LIFNodes(n=100, traces=True), name="output")
        network.add_connection(
            Connection(
                source=network.layers["input"],
                target=network.layers["output"],
                nu=1e-2,
                update_rule=WeightDependentPostPre,
                wmin=-1,
                wmax=1,
            ),
            source="input",
            target="output",
        )
        network.run(
            inpts={"input": torch.bernoulli(torch.rand(250, 100)).byte()}, time=250
        )

        # Conv2dConnection test
        network = Network(dt=1.0)
        network.add_layer(Input(shape=[1, 10, 10], traces=True), name="input")
        network.add_layer(LIFNodes(shape=[32, 8, 8], traces=True), name="output")
        network.add_connection(
            Conv2dConnection(
                source=network.layers["input"],
                target=network.layers["output"],
                kernel_size=3,
                stride=1,
                nu=1e-2,
                update_rule=WeightDependentPostPre,
                wmin=-1,
                wmax=1,
            ),
            source="input",
            target="output",
        )
        network.run(
            inpts={"input": torch.bernoulli(torch.rand(1, 250, 1, 10, 10)).byte()},
            time=250,
        )

    def test_mstdp(self):
        # Connection test
        network = Network(dt=1.0)
        network.add_layer(Input(n=100), name="input")
        network.add_layer(LIFNodes(n=100), name="output")
        network.add_connection(
            Connection(
                source=network.layers["input"],
                target=network.layers["output"],
                nu=1e-2,
                update_rule=MSTDP,
            ),
            source="input",
            target="output",
        )
        network.run(
            inpts={"input": torch.bernoulli(torch.rand(250, 100)).byte()},
            time=250,
            reward=1.0,
        )

        # Conv2dConnection test
        network = Network(dt=1.0)
        network.add_layer(Input(shape=[1, 10, 10]), name="input")
        network.add_layer(LIFNodes(shape=[32, 8, 8]), name="output")
        network.add_connection(
            Conv2dConnection(
                source=network.layers["input"],
                target=network.layers["output"],
                kernel_size=3,
                stride=1,
                nu=1e-2,
                update_rule=MSTDP,
            ),
            source="input",
            target="output",
        )

        network.run(
            inpts={"input": torch.bernoulli(torch.rand(1, 250, 1, 10, 10)).byte()},
            time=250,
            reward=1.0,
        )

    def test_mstdpet(self):
        # Connection test
        network = Network(dt=1.0)
        network.add_layer(Input(n=100), name="input")
        network.add_layer(LIFNodes(n=100), name="output")
        network.add_connection(
            Connection(
                source=network.layers["input"],
                target=network.layers["output"],
                nu=1e-2,
                update_rule=MSTDPET,
            ),
            source="input",
            target="output",
        )
        network.run(
            inpts={"input": torch.bernoulli(torch.rand(250, 100)).byte()},
            time=250,
            reward=1.0,
        )

        # Conv2dConnection test
        network = Network(dt=1.0)
        network.add_layer(Input(shape=[1, 10, 10]), name="input")
        network.add_layer(LIFNodes(shape=[32, 8, 8]), name="output")
        network.add_connection(
            Conv2dConnection(
                source=network.layers["input"],
                target=network.layers["output"],
                kernel_size=3,
                stride=1,
                nu=1e-2,
                update_rule=MSTDPET,
            ),
            source="input",
            target="output",
        )

        network.run(
            inpts={"input": torch.bernoulli(torch.rand(1, 250, 1, 10, 10)).byte()},
            time=250,
            reward=1.0,
        )

    def test_rmax(self):
        # Connection test
        network = Network(dt=1.0)
        network.add_layer(Input(n=100, traces=True, traces_additive=True), name="input")
        network.add_layer(SRM0Nodes(n=100), name="output")
        network.add_connection(
            Connection(
                source=network.layers["input"],
                target=network.layers["output"],
                nu=1e-2,
                update_rule=Rmax,
            ),
            source="input",
            target="output",
        )
        network.run(
            inpts={"input": torch.bernoulli(torch.rand(250, 100)).byte()},
            time=250,
            reward=1.0,
        )
