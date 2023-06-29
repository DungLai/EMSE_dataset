import pytest
import torch

from ludwig.encoders import text_encoders


@pytest.mark.parametrize('use_pretrained', [True, False])
@pytest.mark.parametrize('reduce_output', [None, 'cls_pooled', 'sum'])
@pytest.mark.parametrize('max_sequence_length', [20])
def test_bert_encoder(
        use_pretrained: bool,
        reduce_output: str,
        max_sequence_length: int
):
    bert = text_encoders.BERTEncoder(
        use_pretrained=use_pretrained,
        reduce_output=reduce_output,
        max_sequence_length=max_sequence_length
    )
    inputs = torch.rand((2, max_sequence_length)).type(bert.input_dtype)
    outputs = bert(inputs)
    assert outputs['encoder_output'].shape[1:] == bert.output_shape


@pytest.mark.parametrize('use_pretrained', [True, False])
@pytest.mark.parametrize('reduce_output', ['last', 'sum', 'mean'])
@pytest.mark.parametrize('max_sequence_length', [20])
def test_xlm_encoder(
        use_pretrained: bool,
        reduce_output: str,
        max_sequence_length: int
):
    xlm_encoder = text_encoders.XLMEncoder(
        use_pretrained=use_pretrained,
        reduce_output=reduce_output,
        max_sequence_length=max_sequence_length
    )
    inputs = torch.rand((2, max_sequence_length)).type(xlm_encoder.input_dtype)
    outputs = xlm_encoder(inputs)
    assert outputs['encoder_output'].shape[1:] == xlm_encoder.output_shape


@pytest.mark.parametrize('use_pretrained', [True, False])
@pytest.mark.parametrize('reduce_output', [None, 'sum'])
@pytest.mark.parametrize('max_sequence_length', [20])
def test_gpt_encoder(
        use_pretrained: bool,
        reduce_output: str,
        max_sequence_length: int
):
    gpt_encoder = text_encoders.GPTEncoder(
        use_pretrained=use_pretrained,
        reduce_output=reduce_output,
        max_sequence_length=max_sequence_length
    )
    inputs = torch.rand((2, max_sequence_length)).type(gpt_encoder.input_dtype)
    outputs = gpt_encoder(inputs)
    assert outputs['encoder_output'].shape[1:] == gpt_encoder.output_shape


@pytest.mark.parametrize('use_pretrained', [True, False])
@pytest.mark.parametrize('reduce_output', [None, 'sum'])
@pytest.mark.parametrize('max_sequence_length', [20])
def test_gpt2_encoder(
        use_pretrained: bool,
        reduce_output: str,
        max_sequence_length: int
):
    gpt_encoder = text_encoders.GPT2Encoder(
        use_pretrained=use_pretrained,
        reduce_output=reduce_output,
        max_sequence_length=max_sequence_length)
    inputs = torch.rand((2, max_sequence_length)).type(gpt_encoder.input_dtype)
    outputs = gpt_encoder(inputs)
    assert outputs['encoder_output'].shape[1:] == gpt_encoder.output_shape


@pytest.mark.parametrize('use_pretrained', [True, False])
@pytest.mark.parametrize('reduce_output', [None, 'sum'])
@pytest.mark.parametrize('max_sequence_length', [20])
def test_distil_bert(
        use_pretrained: bool,
        reduce_output: str,
        max_sequence_length: int
):
    distil_bert_encoder = text_encoders.DistilBERTEncoder(
        use_pretrained=use_pretrained,
        reduce_output=reduce_output,
        max_sequence_length=max_sequence_length
    )
    inputs = torch.rand((2, max_sequence_length)).type(
        distil_bert_encoder.input_dtype)
    outputs = distil_bert_encoder(inputs)
    assert outputs['encoder_output'].shape[1:] == distil_bert_encoder.output_shape


@pytest.mark.parametrize('use_pretrained', [True, False])
@pytest.mark.parametrize('reduce_output', [None, 'sum'])
@pytest.mark.parametrize('max_sequence_length', [20])
def test_transfoxl_encoder(
        use_pretrained: bool,
        reduce_output: str,
        max_sequence_length: int
):
    transfo = text_encoders.TransformerXLEncoder(
        use_pretrained=use_pretrained,
        reduce_output=reduce_output,
        max_sequence_length=max_sequence_length)
    inputs = torch.randint(10, (2, max_sequence_length)).type(transfo.input_dtype)
    outputs = transfo(inputs)
    assert outputs['encoder_output'].shape[1:] == transfo.output_shape


@pytest.mark.parametrize('use_pretrained', [True, False])
@pytest.mark.parametrize('reduce_output', [None, 'sum'])
@pytest.mark.parametrize('max_sequence_length', [20])
def test_xlnet_encoder(
        use_pretrained: bool,
        reduce_output: str,
        max_sequence_length: int
):
    xlnet = text_encoders.XLNetEncoder(
        use_pretrained=use_pretrained,
        reduce_output=reduce_output,
        max_sequence_length=max_sequence_length)
    inputs = torch.randint(10, (2, max_sequence_length)).type(xlnet.input_dtype)
    outputs = xlnet(inputs)
    assert outputs['encoder_output'].shape[1:] == xlnet.output_shape
