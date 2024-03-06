import torch
torch.set_num_threads(1)

from transformers import BertTokenizer, BertModel
tokenizer = BertTokenizer.from_pretrained('model/')
model = BertModel.from_pretrained('model/').eval()


def handler(handler_context):
    # tokenizer.src_lang = 'en_XX'
    # handler_context['input_en'] = "Hello I'm a [MASK] model."
    encoded_input = tokenizer(handler_context['input_en'] + '[MASK]', return_tensors='pt')
    output = model(**encoded_input)
    # print(output)
