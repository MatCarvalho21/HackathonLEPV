Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main            | 36/51 [06:01<01:59,  7.94s/lote]
  File "<frozen runpy>", line 88, in _run_code
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/src/rag/indexer.py", line 163, in <module>
    run_indexing(
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/src/rag/indexer.py", line 135, in run_indexing
    embeddings = embedder.encode(
                 ^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/torch/utils/_contextlib.py", line 116, in decorate_context
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/sentence_transformers/util/decorators.py", line 46, in wrapper
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/sentence_transformers/sentence_transformer/model.py", line 895, in encode
    all_embeddings = self._inference(inputs, device=device, **inference_kwargs)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/torch/utils/_contextlib.py", line 116, in decorate_context
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/sentence_transformers/sentence_transformer/model.py", line 963, in _inference
    out_features = self(features, **kwargs)
                   ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1739, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1750, in _call_impl
    return forward_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/sentence_transformers/base/model.py", line 600, in forward
    input = module(input, **module_kwargs)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1739, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1750, in _call_impl
    return forward_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/sentence_transformers/base/modules/transformer.py", line 1647, in forward
    model_output = model_method(**filtered_kwargs)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/transformers/utils/generic.py", line 1081, in wrapper
    output = func(self, *args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/transformers/utils/output_capturing.py", line 287, in wrapper
    outputs = func(self, *args, **kwargs)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/transformers/models/xlm_roberta/modeling_xlm_roberta.py", line 637, in forward
    encoder_outputs = self.encoder(
                      ^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1739, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1750, in _call_impl
    return forward_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/transformers/models/xlm_roberta/modeling_xlm_roberta.py", line 531, in forward
    hidden_states = layer_module(
                    ^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/transformers/modeling_layers.py", line 111, in __call__
    return super().__call__(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1739, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1750, in _call_impl
    return forward_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/transformers/models/xlm_roberta/modeling_xlm_roberta.py", line 430, in forward
    self_attention_output, _ = self.attention(
                               ^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1739, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1750, in _call_impl
    return forward_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/transformers/models/xlm_roberta/modeling_xlm_roberta.py", line 361, in forward
    attention_output, attn_weights = self.self(
                                     ^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1739, in _wrapped_call_impl
    return self._call_impl(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/torch/nn/modules/module.py", line 1750, in _call_impl
    return forward_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/transformers/models/xlm_roberta/modeling_xlm_roberta.py", line 239, in forward
    attn_output, attn_weights = attention_interface(
                                ^^^^^^^^^^^^^^^^^^^^
  File "/mnt/diskSSD2TB/matheus_2/HackathonLEPV/.venv/lib/python3.12/site-packages/transformers/integrations/sdpa_attention.py", line 174, in sdpa_attention_forward
    attn_output = torch.nn.functional.scaled_dot_product_attention(
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 10.12 GiB. GPU 0 has a total capacity of 23.46 GiB of which 2.50 GiB is free. Process 3359131 has 3.75 GiB memory in use. Including non-PyTorch memory, this process has 17.20 GiB memory in use. Of the allocated memory 13.66 GiB is allocated by PyTorch, and 3.35 GiB is reserved by PyTorch but unallocated. If reserved but unallocated memory is large try setting PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True to avoid fragmentation.  See documentation for Memory Management  (https://pytorch.org/docs/stable/notes/cuda.html#environment-variables)


usa a segunda gpu que estava toda livre e faça isso ser incremental, se eu rodar agora não reprocessa tudo
