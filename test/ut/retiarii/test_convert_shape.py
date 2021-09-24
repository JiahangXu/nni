import unittest
import torch

import nni.retiarii.nn.pytorch as nn

from .convert_mixin import ConvertWithShapeMixin


class TestShape(unittest.TestCase, ConvertWithShapeMixin):
    def test_simple_convnet(self):
        class ConvNet(nn.Module):
            def __init__(self):
                super().__init__()
                self.conv = nn.Conv2d(3, 1, 3)
                self.relu = nn.ReLU()
                self.pool = nn.MaxPool2d(kernel_size=2)
            def forward(self, x):
                return self.pool(self.relu(self.conv(x)))

        net = ConvNet()
        input = torch.randn((1, 3, 224, 224))
        model_ir = self._convert_model(net, input)

        conv_node = model_ir.get_nodes_by_type('__torch__.torch.nn.modules.conv.Conv2d')[0]
        relu_node = model_ir.get_nodes_by_type('__torch__.torch.nn.modules.activation.ReLU')[0]
        pool_node = model_ir.get_nodes_by_type('__torch__.torch.nn.modules.pooling.MaxPool2d')[0]
        self.assertEqual(conv_node.input_shape, [[1, 3, 224, 224]])
        self.assertEqual(conv_node.output_shape, [[1, 1, 222, 222]])
        self.assertEqual(relu_node.input_shape, [[1, 1, 222, 222]])
        self.assertEqual(relu_node.output_shape, [[1, 1, 222, 222]])
        self.assertEqual(pool_node.input_shape, [[1, 1, 222, 222]])
        self.assertEqual(pool_node.output_shape, [[1, 1, 111, 111]])

    def test_nested_module(self):
        class ConvRelu(nn.Module):
            def __init__(self):
                super().__init__()
                self.conv = nn.Conv2d(3, 1, 3)
                self.relu = nn.ReLU()
            def forward(self, x):
                return self.relu(self.conv(x))

        class ConvNet(nn.Module):
            def __init__(self):
                super().__init__()
                self.conv = ConvRelu()
                self.pool = nn.MaxPool2d(kernel_size=2)
            def forward(self, x):
                return self.pool(self.conv(x))

        net = ConvNet()
        input = torch.randn((1, 3, 224, 224))
        model_ir = self._convert_model(net, input)

        # check if shape propagation works
        cell_node = model_ir.get_nodes_by_type('_cell')[0]
        self.assertEqual(cell_node.operation.parameters.get('input_shape'), [[1, 3, 224, 224]])
        self.assertEqual(cell_node.operation.parameters.get('output_shape'), [[1, 1, 222, 222]])

    def test_layerchoice(self):
        class ConvNet(nn.Module):
            def __init__(self):
                super().__init__()
                self.conv = nn.LayerChoice([
                    nn.Conv2d(3, 1, 3),
                    nn.Conv2d(3, 1, 5, padding=1),
                ])
                self.pool = nn.MaxPool2d(kernel_size=2)
            def forward(self, x):
                return self.pool(self.conv(x))

        net = ConvNet()
        input = torch.randn((1, 3, 224, 224))
        model_ir = self._convert_model(net, input)

        # check shape info of each candidates
        conv_nodes = model_ir.get_nodes_by_type('__torch__.torch.nn.modules.conv.Conv2d')
        self.assertEqual(conv_nodes[0].operation.parameters.get('output_shape'), [[1, 1, 222, 222]])
        self.assertEqual(conv_nodes[1].operation.parameters.get('output_shape'), [[1, 1, 222, 222]])
